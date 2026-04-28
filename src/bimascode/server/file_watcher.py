"""File system watcher for live-reload functionality.

Uses watchdog to monitor Python files for changes and triggers
callbacks when changes are detected.
"""

import threading
import time
from collections.abc import Callable
from pathlib import Path

try:
    from watchdog.events import FileModifiedEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class FileWatcher:
    """Watches a Python file and its directory for changes.

    Uses debouncing to avoid triggering multiple callbacks for rapid
    file saves (common with editors that perform multiple writes).

    Attributes:
        script_path: Path to the main script being watched
        debounce_ms: Milliseconds to wait before triggering callback
        on_change: Callback function when file changes
    """

    def __init__(
        self,
        script_path: str | Path,
        on_change: Callable[[], None],
        debounce_ms: int = 100,
    ):
        """Initialize the file watcher.

        Args:
            script_path: Path to the Python script to watch
            on_change: Callback function to call when file changes
            debounce_ms: Milliseconds to wait for edits to settle
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog is required for file watching. "
                "Install it with: pip install bimascode[server]"
            )

        self.script_path = Path(script_path).resolve()
        self.on_change = on_change
        self.debounce_ms = debounce_ms

        self._observer: Observer | None = None
        self._last_change_time: float = 0
        self._debounce_timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start watching for file changes."""
        if self._observer is not None:
            return

        handler = _ChangeHandler(self._on_file_change, self.script_path)

        self._observer = Observer()
        # Watch the directory containing the script (catches imports too)
        watch_dir = self.script_path.parent
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.start()

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None

    def _on_file_change(self, path: Path) -> None:
        """Handle a file change event with debouncing.

        Args:
            path: Path to the changed file
        """
        with self._lock:
            # Cancel any pending timer
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()

            # Update last change time
            self._last_change_time = time.time()

            # Start a new timer
            self._debounce_timer = threading.Timer(
                self.debounce_ms / 1000.0,
                self._trigger_callback,
            )
            self._debounce_timer.start()

    def _trigger_callback(self) -> None:
        """Trigger the on_change callback after debounce period."""
        with self._lock:
            self._debounce_timer = None

        # Call the callback
        self.on_change()


class _ChangeHandler(FileSystemEventHandler):
    """Watchdog event handler that filters for relevant file changes."""

    def __init__(self, callback: Callable[[Path], None], script_path: Path):
        """Initialize the handler.

        Args:
            callback: Function to call when a relevant file changes
            script_path: Main script path (for filtering)
        """
        self.callback = callback
        self.script_path = script_path

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modified events.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Only watch Python files
        if path.suffix != ".py":
            return

        # Trigger callback
        self.callback(path)

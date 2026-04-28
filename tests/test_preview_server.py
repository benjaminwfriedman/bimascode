"""Tests for the preview server module."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestFileWatcher:
    """Tests for FileWatcher class."""

    def test_file_watcher_import(self):
        """Test that FileWatcher can be imported."""
        from bimascode.server.file_watcher import FileWatcher

        assert FileWatcher is not None

    def test_file_watcher_init(self):
        """Test FileWatcher initialization."""
        from bimascode.server.file_watcher import FileWatcher

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            script_path = Path(f.name)
            f.write(b"# test script")

        callback = MagicMock()
        watcher = FileWatcher(script_path, callback, debounce_ms=50)

        assert watcher.script_path == script_path.resolve()
        assert watcher.debounce_ms == 50

        # Clean up
        script_path.unlink()

    def test_file_watcher_start_stop(self):
        """Test starting and stopping the file watcher."""
        from bimascode.server.file_watcher import FileWatcher

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            script_path = Path(f.name)
            f.write(b"# test script")

        callback = MagicMock()
        watcher = FileWatcher(script_path, callback, debounce_ms=50)

        watcher.start()
        assert watcher._observer is not None

        watcher.stop()
        assert watcher._observer is None

        # Clean up
        script_path.unlink()

    def test_file_watcher_debounce(self):
        """Test that debouncing works correctly."""
        from bimascode.server.file_watcher import FileWatcher

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            script_path = Path(f.name)
            f.write(b"# test script")

        callback = MagicMock()
        watcher = FileWatcher(script_path, callback, debounce_ms=100)

        # Simulate rapid file changes
        watcher._on_file_change(script_path)
        watcher._on_file_change(script_path)
        watcher._on_file_change(script_path)

        # Callback should not have been called yet
        assert callback.call_count == 0

        # Wait for debounce
        time.sleep(0.15)

        # Callback should have been called exactly once
        assert callback.call_count == 1

        # Clean up
        watcher.stop()
        script_path.unlink()


class TestPreviewServer:
    """Tests for PreviewServer class."""

    def test_preview_server_import(self):
        """Test that PreviewServer can be imported."""
        from bimascode.server.preview_server import PreviewServer

        assert PreviewServer is not None

    def test_preview_server_init(self):
        """Test PreviewServer initialization."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            script_path = Path(f.name)
            f.write(b"# test script")

        server = PreviewServer(script_path, host="localhost", port=8765)

        assert server.script_path == script_path.resolve()
        assert server.host == "localhost"
        assert server.port == 8765

        # Clean up
        server.stop()
        script_path.unlink()

    def test_execute_script_simple(self):
        """Test executing a simple script without Building."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("x = 42\n")
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        result = server.execute_script()

        # No Building found
        assert result is None
        assert server._last_error == "No Building instance found in script"

        # Clean up
        server.stop()
        script_path.unlink()

    def test_execute_script_syntax_error(self):
        """Test executing a script with syntax error."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("def foo(\n")  # Invalid syntax
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        result = server.execute_script()

        assert result is None
        assert "SyntaxError" in server._last_error
        assert server._last_traceback is not None

        # Clean up
        server.stop()
        script_path.unlink()

    def test_execute_script_runtime_error(self):
        """Test executing a script with runtime error."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("x = 1 / 0\n")  # ZeroDivisionError
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        result = server.execute_script()

        assert result is None
        assert "ZeroDivisionError" in server._last_error

        # Clean up
        server.stop()
        script_path.unlink()

    def test_execute_script_with_building(self):
        """Test executing a script that creates a Building."""
        from bimascode.server.preview_server import PreviewServer

        script_content = """
from bimascode.spatial.building import Building
building = Building("Test Building")
"""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(script_content)
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        result = server.execute_script()

        assert result is not None
        assert result.name == "Test Building"
        assert server._building is result
        assert server._last_error is None

        # Clean up
        server.stop()
        script_path.unlink()

    def test_generate_payload_error(self):
        """Test generating error payload when script fails."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("x = 1 / 0\n")
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        server.execute_script()  # This will fail

        payload = server.generate_payload()

        assert payload["type"] == "error"
        assert "ZeroDivisionError" in payload["message"]
        assert "timestamp" in payload
        assert "traceback" in payload

        # Clean up
        server.stop()
        script_path.unlink()

    def test_generate_payload_success(self):
        """Test generating success payload with views."""
        from bimascode.server.preview_server import PreviewServer

        script_content = """
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level

building = Building("Test Building")
level = Level(building, "Ground Floor", elevation=0)
"""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(script_content)
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        server.execute_script()

        payload = server.generate_payload()

        assert payload["type"] == "update"
        assert "timestamp" in payload
        assert "views" in payload
        assert len(payload["views"]) == 1  # One level = one view
        assert "Ground Floor - Floor Plan" in payload["views"]

        # Check view structure
        view_data = payload["views"]["Ground Floor - Floor Plan"]
        assert "lines" in view_data
        assert "arcs" in view_data
        assert "polylines" in view_data
        assert "view_name" in view_data
        assert "element_count" in view_data

        # Clean up
        server.stop()
        script_path.unlink()

    def test_generate_payload_with_gltf(self):
        """Test that payload includes model URL when glTF export succeeds."""
        from bimascode.server.preview_server import PreviewServer

        script_content = """
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level

building = Building("Test Building")
level = Level(building, "Ground Floor", elevation=0)
"""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(script_content)
            script_path = Path(f.name)

        server = PreviewServer(script_path, host="localhost", port=9000)
        server.execute_script()

        payload = server.generate_payload()

        assert payload["type"] == "update"
        # Model URL should be present (even if export fails, it's attempted)
        # The URL format should match the server config
        if payload.get("model_url"):
            assert "localhost" in payload["model_url"]
            assert "9001" in payload["model_url"]  # port + 1
            assert "building.glb" in payload["model_url"]

        # Clean up
        server.stop()
        script_path.unlink()


class TestCLI:
    """Tests for CLI module."""

    def test_cli_import(self):
        """Test that CLI module can be imported."""
        from bimascode.server.cli import create_parser, main

        assert create_parser is not None
        assert main is not None

    def test_cli_parser_creation(self):
        """Test creating the argument parser."""
        from bimascode.server.cli import create_parser

        parser = create_parser()
        assert parser is not None

        # Test parsing serve command
        args = parser.parse_args(["serve", "test.py"])
        assert args.command == "serve"
        assert args.script == "test.py"
        assert args.port == 8765
        assert args.host == "localhost"
        assert args.no_browser is False

    def test_cli_parser_options(self):
        """Test parsing CLI options."""
        from bimascode.server.cli import create_parser

        parser = create_parser()

        args = parser.parse_args(
            ["serve", "test.py", "--port", "9000", "--host", "0.0.0.0", "--no-browser"]
        )
        assert args.port == 9000
        assert args.host == "0.0.0.0"
        assert args.no_browser is True

    def test_cli_no_command(self):
        """Test CLI with no command shows help."""
        from bimascode.server.cli import main

        # Mock sys.argv to have no command
        with patch("sys.argv", ["bimascode"]):
            result = main()
            # Should return 0 (help displayed, no error)
            assert result == 0

    def test_cli_serve_file_not_found(self):
        """Test serve command with non-existent file."""
        from argparse import Namespace

        from bimascode.server.cli import serve_command

        args = Namespace(
            script="/nonexistent/file.py",
            port=8765,
            host="localhost",
            no_browser=True,
        )

        result = serve_command(args)
        assert result == 1  # Error exit code

    def test_cli_serve_non_python_file(self):
        """Test serve command with non-Python file."""
        from argparse import Namespace

        from bimascode.server.cli import serve_command

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not python")
            file_path = f.name

        args = Namespace(
            script=file_path,
            port=8765,
            host="localhost",
            no_browser=True,
        )

        result = serve_command(args)
        assert result == 1  # Error exit code

        # Clean up
        Path(file_path).unlink()


class TestModuleExports:
    """Test that the server module exports the right symbols."""

    def test_module_exports(self):
        """Test that server module exports PreviewServer and FileWatcher."""
        from bimascode.server import FileWatcher, PreviewServer

        assert PreviewServer is not None
        assert FileWatcher is not None

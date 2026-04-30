"""Preview server for live-reload BIM viewing.

Provides WebSocket server that executes Python scripts, generates
2D view JSON and 3D glTF, and pushes updates to connected clients.
"""

import asyncio
import http.server
import json
import socketserver
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bimascode.server.file_watcher import FileWatcher

if TYPE_CHECKING:
    from bimascode.spatial.building import Building

try:
    import websockets
    from websockets.server import serve as websocket_serve

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class PreviewServer:
    """Live preview server for BIM as Code scripts.

    Watches a Python script for changes, re-executes it, and pushes
    updated 2D views (JSON) and 3D model (glTF URL) to connected
    WebSocket clients.

    Attributes:
        script_path: Path to the Python script
        host: Server host address
        port: Server port
    """

    def __init__(
        self,
        script_path: str | Path,
        host: str = "localhost",
        port: int = 8765,
    ):
        """Initialize the preview server.

        Args:
            script_path: Path to the Python script to watch
            host: Host address to bind to
            port: Port to listen on
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets is required for preview server. "
                "Install it with: pip install bimascode[server]"
            )

        self.script_path = Path(script_path).resolve()
        self.host = host
        self.port = port

        # Connected WebSocket clients
        self._clients: set = set()
        self._clients_lock = asyncio.Lock()

        # Current state
        self._building: Building | None = None
        self._last_error: str | None = None
        self._last_traceback: str | None = None
        self._last_update_time: float = 0

        # Temp directory for glTF files
        self._temp_dir = tempfile.mkdtemp(prefix="bimascode_preview_")
        self._model_path = Path(self._temp_dir) / "building.glb"

        # File watcher (created on serve)
        self._watcher: FileWatcher | None = None

        # HTTP server for static files and model
        self._http_server: socketserver.TCPServer | None = None
        self._http_thread: threading.Thread | None = None

        # Event loop reference
        self._loop: asyncio.AbstractEventLoop | None = None

    def execute_script(self) -> "Building | None":
        """Execute the Python script in an isolated namespace.

        Returns:
            Building instance found in the script namespace, or None if
            execution failed or no Building was found.

        Note:
            Errors are captured in self._last_error and self._last_traceback
        """
        # Reset error state
        self._last_error = None
        self._last_traceback = None

        # Create isolated namespace
        namespace: dict[str, Any] = {
            "__name__": "__main__",
            "__file__": str(self.script_path),
        }

        try:
            # Read and compile the script
            script_content = self.script_path.read_text()
            compiled = compile(script_content, str(self.script_path), "exec")

            # Execute the script
            exec(compiled, namespace)

            # Find Building instance by type inspection
            building = self._find_building(namespace)
            if building is None:
                self._last_error = "No Building instance found in script"
                return None

            self._building = building
            return building

        except SyntaxError as e:
            self._last_error = f"SyntaxError on line {e.lineno}: {e.msg}"
            self._last_traceback = traceback.format_exc()
            return None

        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            self._last_traceback = traceback.format_exc()
            return None

    def _find_building(self, namespace: dict[str, Any]) -> "Building | None":
        """Find a Building instance in the script namespace.

        Searches the namespace for Building instances. Also checks if there's
        a `get_building()` or `create_building()` function that returns one.

        Args:
            namespace: The executed script's namespace

        Returns:
            Building instance or None if not found
        """
        # Import Building class for isinstance check
        from bimascode.spatial.building import Building

        # First, search namespace for Building instances directly
        for value in namespace.values():
            if isinstance(value, Building):
                return value

        # Check for common factory function patterns
        for func_name in ["get_building", "create_building", "make_building", "build"]:
            if func_name in namespace and callable(namespace[func_name]):
                try:
                    result = namespace[func_name]()
                    if isinstance(result, Building):
                        return result
                except Exception:
                    pass  # Function failed, continue searching

        # Check if Building class was imported and has instances via levels
        # This catches cases where Building is created inside main()
        if "Building" in namespace:
            building_cls = namespace["Building"]
            # Building tracks all instances - check if any exist
            # This is a fallback - ideally scripts expose building at module level

        return None

    def generate_payload(self) -> dict:
        """Generate JSON payload with views and model URL.

        Returns:
            Dictionary containing view data, model URL, or error info.
        """
        timestamp = int(time.time() * 1000)

        # Return error payload if last execution failed
        if self._last_error is not None:
            return {
                "type": "error",
                "timestamp": timestamp,
                "message": self._last_error,
                "traceback": self._last_traceback or "",
            }

        # Return empty payload if no building
        if self._building is None:
            return {
                "type": "error",
                "timestamp": timestamp,
                "message": "No building available",
                "traceback": "",
            }

        # Generate views for all levels
        views = {}
        try:
            views = self._generate_views()
        except Exception as e:
            return {
                "type": "error",
                "timestamp": timestamp,
                "message": f"Error generating views: {e}",
                "traceback": traceback.format_exc(),
            }

        # Generate glTF model
        model_url = None
        try:
            self._export_gltf()
            model_url = f"http://{self.host}:{self.port + 1}/model/building.glb"
        except Exception as e:
            # Model export failure is non-fatal, just log it
            print(f"Warning: glTF export failed: {e}")

        return {
            "type": "update",
            "timestamp": timestamp,
            "views": views,
            "model_url": model_url,
        }

    def _generate_views(self) -> dict[str, dict]:
        """Generate floor plan views for all levels.

        Returns:
            Dictionary mapping view names to ViewResult.to_dict() data
        """
        from bimascode.drawing.floor_plan_view import FloorPlanView
        from bimascode.drawing.view_base import ViewRange
        from bimascode.performance.representation_cache import RepresentationCache
        from bimascode.performance.spatial_index import SpatialIndex

        if self._building is None:
            return {}

        views = {}
        cache = RepresentationCache()

        for level in self._building.levels:
            # Build spatial index for this level
            spatial_index = SpatialIndex()
            for element in level.elements:
                spatial_index.insert(element)

            # Create floor plan view
            view_name = f"{level.name} - Floor Plan"
            view_range = ViewRange(cut_height=1200, top=3000, bottom=0, view_depth=0)
            floor_plan = FloorPlanView(
                name=view_name,
                level=level,
                view_range=view_range,
            )

            # Generate view
            result = floor_plan.generate(spatial_index, cache)
            views[view_name] = result.to_dict()

        return views

    def _export_gltf(self) -> None:
        """Export building to glTF file."""
        from bimascode.export.gltf_exporter import GLTFExporter

        if self._building is None:
            return

        exporter = GLTFExporter()
        exporter.export(self._building, self._model_path)

    async def handle_client(self, websocket) -> None:
        """Handle a WebSocket client connection.

        Args:
            websocket: The WebSocket connection
        """
        # Add client to set
        async with self._clients_lock:
            self._clients.add(websocket)

        try:
            # Send initial state
            payload = self.generate_payload()
            await websocket.send(json.dumps(payload))

            # Keep connection open and handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, data)
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Remove client from set
            async with self._clients_lock:
                self._clients.discard(websocket)

    async def _handle_message(self, websocket, data: dict) -> None:
        """Handle a message from a client.

        Args:
            websocket: The WebSocket connection
            data: Parsed JSON message
        """
        msg_type = data.get("type")

        if msg_type == "refresh":
            # Re-execute script and send update
            self.execute_script()
            payload = self.generate_payload()
            await websocket.send(json.dumps(payload))

        elif msg_type == "export_ifc":
            # Export IFC file (future feature)
            pass

    async def _broadcast(self, payload: dict) -> None:
        """Broadcast a payload to all connected clients.

        Args:
            payload: JSON-serializable dictionary to send
        """
        message = json.dumps(payload)
        async with self._clients_lock:
            # Send to all connected clients
            dead_clients = set()
            for client in self._clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    dead_clients.add(client)

            # Clean up dead connections
            self._clients -= dead_clients

    def _on_file_change(self) -> None:
        """Handle file change event from watcher."""
        print(f"[{time.strftime('%H:%M:%S')}] File changed, reloading...")

        # Re-execute script
        self.execute_script()
        self._last_update_time = time.time()

        # Generate payload
        payload = self.generate_payload()

        if payload["type"] == "error":
            print(f"  Error: {payload['message']}")
        else:
            view_count = len(payload.get("views", {}))
            print(f"  Generated {view_count} view(s)")

        # Broadcast to clients (thread-safe)
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    def _start_http_server(self) -> None:
        """Start HTTP server for static files and model serving."""
        # Create handler with access to temp dir and viewer path
        temp_dir = self._temp_dir
        viewer_dir = Path(__file__).parent / "viewer"

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.temp_dir = temp_dir
                self.viewer_dir = viewer_dir
                super().__init__(*args, **kwargs)

            def do_GET(self):
                # Serve model files from temp dir
                if self.path.startswith("/model/"):
                    file_name = self.path[7:]  # Remove "/model/"
                    file_path = Path(self.temp_dir) / file_name
                    if file_path.exists():
                        self.send_response(200)
                        self.send_header("Content-Type", "model/gltf-binary")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(file_path.read_bytes())
                        return
                    else:
                        self.send_error(404, "File not found")
                        return

                # MIME type mapping for viewer files
                mime_types = {
                    ".html": "text/html",
                    ".css": "text/css",
                    ".js": "application/javascript",
                    ".json": "application/json",
                    ".png": "image/png",
                    ".svg": "image/svg+xml",
                }

                # Serve viewer files
                if self.path == "/":
                    self.path = "/index.html"

                # Clean path and resolve file
                clean_path = self.path.lstrip("/")
                file_path = self.viewer_dir / clean_path

                if file_path.exists() and file_path.is_file():
                    self.send_response(200)
                    ext = file_path.suffix.lower()
                    content_type = mime_types.get(ext, "application/octet-stream")
                    self.send_header("Content-Type", content_type)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(file_path.read_bytes())
                    return

                # Fall back to placeholder if index.html doesn't exist
                if self.path == "/index.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(self._get_placeholder_html().encode())
                    return

                self.send_error(404, "File not found")

            def _get_placeholder_html(self) -> str:
                return (
                    """<!DOCTYPE html>
<html>
<head>
    <title>BIM Preview</title>
    <style>
        body { font-family: system-ui; margin: 40px; background: #1a1a2e; color: #eee; }
        h1 { color: #0f3460; }
        .status { padding: 20px; background: #16213e; border-radius: 8px; }
        pre { background: #0f3460; padding: 15px; border-radius: 4px; overflow: auto; }
    </style>
</head>
<body>
    <h1>BIM as Code Preview Server</h1>
    <div class="status" id="status">Connecting...</div>
    <h2>Latest View Data</h2>
    <pre id="data">Waiting for data...</pre>
    <script>
        const ws = new WebSocket('ws://' + location.hostname + ':"""
                    + str(self.port)
                    + """/ws');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            document.getElementById('status').textContent =
                data.type === 'error' ? 'Error: ' + data.message : 'Connected - ' + Object.keys(data.views || {}).length + ' views';
            document.getElementById('data').textContent = JSON.stringify(data, null, 2);
        };
        ws.onopen = () => document.getElementById('status').textContent = 'Connected';
        ws.onclose = () => document.getElementById('status').textContent = 'Disconnected';
    </script>
</body>
</html>"""
                )

            def log_message(self, format, *args):
                # Suppress HTTP logs
                pass

        # Start HTTP server on port + 1
        http_port = self.port + 1

        try:
            self._http_server = socketserver.TCPServer(
                (self.host, http_port),
                Handler,
            )
            self._http_server.allow_reuse_address = True

            self._http_thread = threading.Thread(
                target=self._http_server.serve_forever,
                daemon=True,
            )
            self._http_thread.start()
        except OSError as e:
            print(f"Warning: Could not start HTTP server on port {http_port}: {e}")

    async def serve(self) -> None:
        """Start the preview server with file watcher.

        This is the main entry point for running the server. It:
        1. Executes the script initially
        2. Starts the file watcher
        3. Starts HTTP server for static files
        4. Starts WebSocket server for live updates

        Runs until interrupted (Ctrl+C).
        """
        # Store event loop reference
        self._loop = asyncio.get_running_loop()

        # Initial script execution
        print(f"Executing {self.script_path.name}...")
        building = self.execute_script()
        if building is not None:
            print(f"  Found building: {building.name}")
            print(f"  Levels: {len(building.levels)}")
        else:
            print(f"  Error: {self._last_error}")

        # Start HTTP server
        self._start_http_server()

        # Start file watcher
        self._watcher = FileWatcher(
            self.script_path,
            self._on_file_change,
            debounce_ms=100,
        )
        self._watcher.start()
        print(f"Watching {self.script_path.name} for changes...")

        # Start WebSocket server
        print("\nServer running:")
        print(f"  WebSocket: ws://{self.host}:{self.port}/ws")
        print(f"  HTTP:      http://{self.host}:{self.port + 1}/")
        print("\nPress Ctrl+C to stop.\n")

        async with websocket_serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
        ):
            # Run forever
            await asyncio.Future()

    def stop(self) -> None:
        """Stop the server and clean up resources."""
        # Stop file watcher
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

        # Stop HTTP server
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server = None

        # Clean up temp directory
        import shutil

        if Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)

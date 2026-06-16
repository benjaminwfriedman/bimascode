"""Preview server for live-reload BIM viewing.

Provides WebSocket server that executes Python scripts and serves
the exported DXF/IFC files to connected clients.
"""

import asyncio
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

from bimascode.server.dxf_reader import read_dxf_to_view_data
from bimascode.server.file_watcher import FileWatcher

try:
    import websockets
    from websockets.server import serve as websocket_serve

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class PreviewServer:
    """Live preview server for BIM as Code scripts.

    Watches a Python script for changes, re-executes it, and pushes
    updated 2D views (from DXF files) and 3D model (glTF from IFC) to
    connected WebSocket clients.

    The script is expected to export IFC and DXF files to the output
    directory. The server reads these files and serves them to the viewer.

    Attributes:
        script_path: Path to the Python script
        output_dir: Directory where script exports files
        host: Server host address
        port: Server port
    """

    def __init__(
        self,
        script_path: str | Path,
        host: str = "localhost",
        port: int = 8765,
        output_dir: str | Path | None = None,
    ):
        """Initialize the preview server.

        Args:
            script_path: Path to the Python script to watch
            host: Host address to bind to
            port: Port to listen on
            output_dir: Directory for exported files. If None, uses a temp directory.
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets is required for preview server. "
                "Install it with: pip install bimascode[server]"
            )

        self.script_path = Path(script_path).resolve()
        self.host = host
        self.port = port

        # Output directory for exports
        if output_dir is not None:
            self.output_dir = Path(output_dir).resolve()
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._temp_output = False
        else:
            self._temp_output = True
            self.output_dir = Path(tempfile.mkdtemp(prefix="bimascode_preview_"))

        # Connected WebSocket clients
        self._clients: set = set()
        self._clients_lock = asyncio.Lock()

        # Current state
        self._last_error: str | None = None
        self._last_traceback: str | None = None
        self._last_update_time: float = 0
        self._dxf_files: list[Path] = []
        self._ifc_files: list[Path] = []
        self._glb_files: list[Path] = []

        # Temp directory for glTF conversion
        self._gltf_dir = Path(tempfile.mkdtemp(prefix="bimascode_gltf_"))

        # File watcher (created on serve)
        self._watcher: FileWatcher | None = None

        # HTTP server for static files and model
        self._http_server: socketserver.TCPServer | None = None
        self._http_thread: threading.Thread | None = None

        # Event loop reference
        self._loop: asyncio.AbstractEventLoop | None = None

    def _create_patched_script(self) -> Path:
        """Create a temp copy of the script with export paths redirected.

        Monkey-patches all bimascode export methods to redirect output files
        to the server's output directory, preserving original filenames.

        Returns:
            Path to the temporary patched script.
        """
        preamble = f'''\
# === BIMASCODE PREVIEW SERVER PATCHS ===
# Redirects all exports to server output directory
import os as _os
from pathlib import Path as _Path

_BIMASCODE_OUTPUT_DIR = _Path({repr(str(self.output_dir))})

def _redirect_path(original_path):
    """Redirect a path to the server output directory, keeping filename."""
    p = _Path(original_path)
    return str(_BIMASCODE_OUTPUT_DIR / p.name)

# Patch Building.export_ifc
try:
    from bimascode.spatial.building import Building as _Building
    _original_export_ifc = _Building.export_ifc
    def _patched_export_ifc(self, filepath, *args, **kwargs):
        return _original_export_ifc(self, _redirect_path(filepath), *args, **kwargs)
    _Building.export_ifc = _patched_export_ifc
except (ImportError, AttributeError):
    pass

# Patch DXFExporter.export
try:
    from bimascode.drawing.dxf_exporter import DXFExporter as _DXFExporter
    _original_dxf_export = _DXFExporter.export
    def _patched_dxf_export(self, result, filepath, *args, **kwargs):
        return _original_dxf_export(self, result, _redirect_path(filepath), *args, **kwargs)
    _DXFExporter.export = _patched_dxf_export
except (ImportError, AttributeError):
    pass

# Patch DXFExporter.export_multiple
try:
    from bimascode.drawing.dxf_exporter import DXFExporter as _DXFExporter2
    _original_dxf_export_multiple = _DXFExporter2.export_multiple
    def _patched_dxf_export_multiple(self, results, filepath, *args, **kwargs):
        return _original_dxf_export_multiple(self, results, _redirect_path(filepath), *args, **kwargs)
    _DXFExporter2.export_multiple = _patched_dxf_export_multiple
except (ImportError, AttributeError):
    pass

# Patch DXFSheetExporter.export_sheet
try:
    from bimascode.drawing.dxf_exporter import DXFSheetExporter as _DXFSheetExporter
    _original_dxf_export_sheet = _DXFSheetExporter.export_sheet
    def _patched_dxf_export_sheet(self, sheet, filepath, *args, **kwargs):
        return _original_dxf_export_sheet(self, sheet, _redirect_path(filepath), *args, **kwargs)
    _DXFSheetExporter.export_sheet = _patched_dxf_export_sheet
except (ImportError, AttributeError):
    pass

# Patch DXFSheetExporter.export_sheet_flat
try:
    from bimascode.drawing.dxf_exporter import DXFSheetExporter as _DXFSheetExporter2
    _original_dxf_export_sheet_flat = _DXFSheetExporter2.export_sheet_flat
    def _patched_dxf_export_sheet_flat(self, sheet, filepath, *args, **kwargs):
        return _original_dxf_export_sheet_flat(self, sheet, _redirect_path(filepath), *args, **kwargs)
    _DXFSheetExporter2.export_sheet_flat = _patched_dxf_export_sheet_flat
except (ImportError, AttributeError):
    pass

# Patch Sheet.export_dxf
try:
    from bimascode.drawing.sheet import Sheet as _Sheet
    _original_sheet_export_dxf = _Sheet.export_dxf
    def _patched_sheet_export_dxf(self, filepath, *args, **kwargs):
        return _original_sheet_export_dxf(self, _redirect_path(filepath), *args, **kwargs)
    _Sheet.export_dxf = _patched_sheet_export_dxf
except (ImportError, AttributeError):
    pass

# Patch Sheet.export_pdf
try:
    from bimascode.drawing.sheet import Sheet as _Sheet2
    _original_sheet_export_pdf = _Sheet2.export_pdf
    def _patched_sheet_export_pdf(self, filepath, *args, **kwargs):
        return _original_sheet_export_pdf(self, _redirect_path(filepath), *args, **kwargs)
    _Sheet2.export_pdf = _patched_sheet_export_pdf
except (ImportError, AttributeError):
    pass

# Patch PDFExporter.export
try:
    from bimascode.drawing.pdf_exporter import PDFExporter as _PDFExporter
    _original_pdf_export = _PDFExporter.export
    def _patched_pdf_export(self, result, filepath, *args, **kwargs):
        return _original_pdf_export(self, result, _redirect_path(filepath), *args, **kwargs)
    _PDFExporter.export = _patched_pdf_export
except (ImportError, AttributeError):
    pass

# Patch PDFExporter.export_sheet
try:
    from bimascode.drawing.pdf_exporter import PDFExporter as _PDFExporter2
    _original_pdf_export_sheet = _PDFExporter2.export_sheet
    def _patched_pdf_export_sheet(self, sheet, filepath, *args, **kwargs):
        return _original_pdf_export_sheet(self, sheet, _redirect_path(filepath), *args, **kwargs)
    _PDFExporter2.export_sheet = _patched_pdf_export_sheet
except (ImportError, AttributeError):
    pass

# Patch PDFExporter.export_sheets
try:
    from bimascode.drawing.pdf_exporter import PDFExporter as _PDFExporter3
    _original_pdf_export_sheets = _PDFExporter3.export_sheets
    def _patched_pdf_export_sheets(self, sheets, filepath, *args, **kwargs):
        return _original_pdf_export_sheets(self, sheets, _redirect_path(filepath), *args, **kwargs)
    _PDFExporter3.export_sheets = _patched_pdf_export_sheets
except (ImportError, AttributeError):
    pass

# Patch GLTFExporter.export
try:
    from bimascode.export.gltf_exporter import GLTFExporter as _GLTFExporter
    _original_gltf_export = _GLTFExporter.export
    def _patched_gltf_export(self, building, filepath, *args, **kwargs):
        return _original_gltf_export(self, building, _redirect_path(filepath), *args, **kwargs)
    _GLTFExporter.export = _patched_gltf_export
except (ImportError, AttributeError):
    pass

# === END BIMASCODE PREVIEW SERVER PATCHES ===

'''
        # Read original script
        original_content = self.script_path.read_text()

        # Create temp file in same directory (for relative imports to work)
        temp_script = self.script_path.parent / f".bimascode_preview_{self.script_path.name}"
        temp_script.write_text(preamble + original_content)

        return temp_script

    def execute_script(self) -> bool:
        """Execute the Python script as a subprocess.

        Creates a patched copy of the script that redirects all export calls
        to the server's output directory, then executes it.

        Returns:
            True if script executed successfully, False otherwise.

        Note:
            Errors are captured in self._last_error and self._last_traceback
        """
        # Reset error state
        self._last_error = None
        self._last_traceback = None

        # Create patched script with export redirects
        patched_script = self._create_patched_script()

        try:
            # Run patched script as subprocess
            env = {
                **dict(__import__("os").environ),
                "BIMASCODE_OUTPUT_DIR": str(self.output_dir),
            }

            result = subprocess.run(
                [sys.executable, str(patched_script)],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                env=env,
                cwd=self.script_path.parent,
            )

            if result.returncode != 0:
                self._last_error = f"Script exited with code {result.returncode}"
                self._last_traceback = result.stderr or result.stdout
                return False

            # Find exported files
            self._scan_output_files()
            return True

        except subprocess.TimeoutExpired:
            self._last_error = "Script timed out after 120 seconds"
            self._last_traceback = ""
            return False

        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            self._last_traceback = traceback.format_exc()
            return False

        finally:
            # Clean up patched script
            if patched_script.exists():
                patched_script.unlink()

    def _scan_output_files(self) -> None:
        """Scan output directory for DXF, IFC, and GLB files."""
        self._dxf_files = sorted(self.output_dir.glob("**/*.dxf"))
        self._ifc_files = sorted(self.output_dir.glob("**/*.ifc"))
        self._glb_files = sorted(self.output_dir.glob("**/*.glb"))

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

        # Return empty payload if no files found
        if not self._dxf_files and not self._ifc_files:
            return {
                "type": "error",
                "timestamp": timestamp,
                "message": "No DXF or IFC files found in output directory",
                "traceback": f"Output directory: {self.output_dir}",
            }

        # Read DXF files and convert to view data
        views = {}
        dxf_files_list = []
        try:
            for dxf_file in self._dxf_files:
                view_name = dxf_file.stem
                view_data = read_dxf_to_view_data(dxf_file)
                views[view_name] = view_data
                dxf_files_list.append(view_name)
        except Exception as e:
            return {
                "type": "error",
                "timestamp": timestamp,
                "message": f"Error reading DXF files: {e}",
                "traceback": traceback.format_exc(),
            }

        # Get 3D model URL
        # Prefer pre-generated GLB files (from GLTFExporter) over IFC conversion
        # because IfcOpenShell's gltf serializer has vertex data corruption bugs
        model_url = None
        if self._glb_files:
            # Use pre-generated GLB file directly (copy to gltf_dir for serving)
            glb_src = self._glb_files[0]
            glb_dest = self._gltf_dir / glb_src.name
            shutil.copy(glb_src, glb_dest)
            model_url = f"http://{self.host}:{self.port + 1}/model/{glb_dest.name}"
        elif self._ifc_files:
            # Fall back to IFC conversion (has known bugs with some geometry)
            try:
                gltf_path = self._convert_ifc_to_gltf(self._ifc_files[0])
                if gltf_path:
                    model_url = f"http://{self.host}:{self.port + 1}/model/{gltf_path.name}"
            except Exception as e:
                print(f"Warning: IFC to glTF conversion failed: {e}")

        return {
            "type": "update",
            "timestamp": timestamp,
            "views": views,
            "dxf_files": dxf_files_list,
            "model_url": model_url,
        }

    def _convert_ifc_to_gltf(self, ifc_path: Path) -> Path | None:
        """Convert IFC file to glTF for 3D viewing.

        Uses ifcopenshell to extract geometry from IFC, then tessellates
        with correct face winding using trimesh.

        Args:
            ifc_path: Path to IFC file

        Returns:
            Path to generated glTF file, or None if conversion failed.
        """
        try:
            import ifcopenshell
            import ifcopenshell.geom
            import numpy as np
            import trimesh

            # Open IFC file
            ifc_file = ifcopenshell.open(str(ifc_path))

            # Set up geometry settings
            geom_settings = ifcopenshell.geom.settings()
            geom_settings.set(geom_settings.USE_WORLD_COORDS, True)
            geom_settings.set(geom_settings.WELD_VERTICES, False)

            # Output path
            output_path = self._gltf_dir / "building.glb"

            # Create trimesh scene
            scene = trimesh.Scene()

            # Element type to color mapping (RGB 0-1)
            element_colors = {
                "IfcWall": [0.78, 0.78, 0.78, 1.0],
                "IfcWallStandardCase": [0.78, 0.78, 0.78, 1.0],
                "IfcSlab": [0.59, 0.59, 0.59, 1.0],
                "IfcRoof": [0.39, 0.39, 0.39, 1.0],
                "IfcCovering": [0.94, 0.94, 0.94, 1.0],
                "IfcDoor": [0.55, 0.35, 0.17, 1.0],
                "IfcWindow": [0.68, 0.85, 0.90, 0.7],
                "IfcColumn": [0.63, 0.63, 0.67, 1.0],
                "IfcBeam": [0.63, 0.63, 0.67, 1.0],
                "IfcSpace": [0.78, 0.78, 1.0, 0.3],
            }
            default_color = [0.7, 0.7, 0.7, 1.0]

            # Iterate through elements
            iterator = ifcopenshell.geom.iterator(geom_settings, ifc_file)
            if iterator.initialize():
                while True:
                    shape = iterator.get()
                    element = ifc_file.by_id(shape.id)
                    ifc_type = element.is_a()

                    # Get geometry data
                    geom = shape.geometry
                    verts = np.array(geom.verts).reshape(-1, 3)
                    faces = np.array(geom.faces).reshape(-1, 3)

                    if len(verts) == 0 or len(faces) == 0:
                        if not iterator.next():
                            break
                        continue

                    # Create mesh
                    mesh = trimesh.Trimesh(vertices=verts, faces=faces)

                    # Fix face winding for consistent normals
                    mesh.fix_normals()

                    # Apply color
                    color = element_colors.get(ifc_type, default_color)
                    mesh.visual.face_colors = [
                        [int(c * 255) for c in color] for _ in range(len(mesh.faces))
                    ]

                    # Get element name
                    name = getattr(element, "Name", None) or f"{ifc_type}_{shape.id}"

                    # Add to scene
                    scene.add_geometry(mesh, node_name=name)

                    if not iterator.next():
                        break

            # Handle empty scenes
            if len(scene.geometry) == 0:
                placeholder = trimesh.creation.box(extents=[1, 1, 1])
                scene.add_geometry(placeholder, node_name="placeholder")

            # Export to GLB
            glb_data = scene.export(file_type="glb")
            output_path.write_bytes(glb_data)

            return output_path

        except Exception as e:
            print(f"IFC to glTF conversion error: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _fix_gltf_asset_version(self, glb_path: Path) -> None:
        """Fix issues in GLB file from ifcopenshell.

        ifcopenshell's glTF serializer has several bugs:
        1. Missing required asset.version field
        2. Binary chunk is truncated (header claims more bytes than written)
        3. When USE_WORLD_COORDS=True, vertices already have world coords baked in,
           but ifcopenshell still adds Z-up to Y-up rotation matrices to each node,
           which corrupts the geometry (double transformation)

        This fixes all issues by adding asset.version, padding binary data,
        and removing redundant node transformation matrices.
        """
        import struct

        with open(glb_path, "rb") as f:
            data = bytearray(f.read())

        if len(data) < 20 or data[:4] != b"glTF":
            return

        # Parse original structure
        orig_json_length = struct.unpack("<I", data[12:16])[0]
        if data[16:20] != b"JSON":
            return

        json_end = 20 + orig_json_length

        # Extract and parse JSON
        json_bytes = data[20:json_end]
        try:
            gltf = json.loads(json_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            # ifcopenshell sometimes writes truncated/malformed JSON
            # Try to find the actual JSON end by looking for closing brace
            json_str = json_bytes.decode("utf-8", errors="replace")
            # Find last valid closing brace
            last_brace = json_str.rfind("}")
            if last_brace > 0:
                try:
                    gltf = json.loads(json_str[: last_brace + 1])
                except json.JSONDecodeError:
                    print("Warning: Could not parse GLB JSON, skipping fixes")
                    return
            else:
                print("Warning: Could not parse GLB JSON, skipping fixes")
                return

        # Fix 1: Add asset.version if missing
        if "asset" not in gltf:
            gltf["asset"] = {}
        if "version" not in gltf["asset"]:
            gltf["asset"]["version"] = "2.0"
            gltf["asset"]["generator"] = "bimascode"

        # Fix 3: Remove redundant Z-up to Y-up rotation matrices from nodes
        # When USE_WORLD_COORDS=True, vertices already have world coordinates
        # baked in. ifcopenshell incorrectly adds rotation matrices anyway,
        # causing geometry corruption (beams appear diagonal, etc.)
        for node in gltf.get("nodes", []):
            if "matrix" in node:
                del node["matrix"]

        # Re-encode JSON (padded to 4-byte boundary with spaces)
        new_json_str = json.dumps(gltf, separators=(",", ":"))
        while len(new_json_str) % 4 != 0:
            new_json_str += " "
        new_json_bytes = new_json_str.encode("utf-8")

        # Fix 2: Pad binary data to match claimed buffer size
        # ifcopenshell truncates the binary data, so we need to pad it
        bin_chunk_start = json_end
        if bin_chunk_start + 8 <= len(data):
            actual_bin_data = bytearray(data[bin_chunk_start + 8 :])

            # Get the claimed buffer size from JSON
            buffers = gltf.get("buffers", [])
            if buffers:
                claimed_size = buffers[0].get("byteLength", len(actual_bin_data))
                # Pad with zeros if truncated
                if len(actual_bin_data) < claimed_size:
                    actual_bin_data.extend(b"\x00" * (claimed_size - len(actual_bin_data)))
        else:
            actual_bin_data = bytearray()

        # Build corrected GLB
        total_length = 12 + 8 + len(new_json_bytes)
        if len(actual_bin_data) > 0:
            total_length += 8 + len(actual_bin_data)

        new_glb = bytearray()

        # GLB Header
        new_glb.extend(b"glTF")
        new_glb.extend(struct.pack("<I", 2))  # version 2
        new_glb.extend(struct.pack("<I", total_length))

        # JSON chunk
        new_glb.extend(struct.pack("<I", len(new_json_bytes)))
        new_glb.extend(b"JSON")
        new_glb.extend(new_json_bytes)

        # Binary chunk (padded to match claimed size)
        if len(actual_bin_data) > 0:
            new_glb.extend(struct.pack("<I", len(actual_bin_data)))
            new_glb.extend(b"BIN\x00")
            new_glb.extend(actual_bin_data)

        with open(glb_path, "wb") as f:
            f.write(new_glb)

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
            print(f"  Found {view_count} DXF file(s)")

        # Broadcast to clients (thread-safe)
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    def _start_http_server(self) -> None:
        """Start HTTP server for static files and model serving."""
        # Create handler with access to directories
        gltf_dir = self._gltf_dir
        output_dir = self.output_dir
        viewer_dir = Path(__file__).parent / "viewer"

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.gltf_dir = gltf_dir
                self.output_dir = output_dir
                self.viewer_dir = viewer_dir
                super().__init__(*args, **kwargs)

            def do_GET(self):
                # Serve model files from gltf dir
                if self.path.startswith("/model/"):
                    file_name = self.path[7:]  # Remove "/model/"
                    file_path = Path(self.gltf_dir) / file_name
                    print(f"[HTTP] Model request: {file_path}, exists: {file_path.exists()}")
                    if file_path.exists():
                        self.send_response(200)
                        self.send_header("Content-Type", "model/gltf-binary")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(file_path.read_bytes())
                        return
                    else:
                        print(
                            f"[HTTP] 404: gltf_dir contents: {list(Path(self.gltf_dir).iterdir()) if Path(self.gltf_dir).exists() else 'dir not exist'}"
                        )
                        self.send_error(404, "File not found")
                        return

                # Serve DXF files from output dir
                if self.path.startswith("/dxf/"):
                    file_name = self.path[5:]  # Remove "/dxf/"
                    file_path = Path(self.output_dir) / file_name
                    if file_path.exists() and file_path.suffix.lower() == ".dxf":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/octet-stream")
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
                    # Disable caching for development
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
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
        print(f"Output directory: {self.output_dir}")
        success = self.execute_script()

        if success:
            print(f"  Found {len(self._dxf_files)} DXF file(s)")
            print(f"  Found {len(self._ifc_files)} IFC file(s)")
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

        # Clean up temp directories
        if self._temp_output and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)

        if self._gltf_dir.exists():
            shutil.rmtree(self._gltf_dir, ignore_errors=True)

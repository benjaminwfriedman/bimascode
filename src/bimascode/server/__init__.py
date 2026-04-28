"""Preview server for live-reload BIM viewing.

This module provides a WebSocket server that watches Python files,
re-executes them when changed, and pushes updated 2D views (JSON)
and 3D models (glTF) to connected web clients.

Usage:
    bimascode serve examples/example_office_building.py
"""

from bimascode.server.file_watcher import FileWatcher
from bimascode.server.preview_server import PreviewServer

__all__ = ["PreviewServer", "FileWatcher"]

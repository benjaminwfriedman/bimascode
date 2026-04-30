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

    def test_preview_server_init_with_output_dir(self):
        """Test PreviewServer initialization with custom output directory."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            script_path = Path(f.name)
            f.write(b"# test script")

        with tempfile.TemporaryDirectory() as output_dir:
            server = PreviewServer(script_path, host="localhost", port=8765, output_dir=output_dir)

            assert server.output_dir == Path(output_dir).resolve()
            assert server._temp_output is False

            # Clean up
            server.stop()

        script_path.unlink()

    def test_execute_script_simple(self):
        """Test executing a simple script that succeeds."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("x = 42\n")
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        result = server.execute_script()

        # Script executes successfully (returns True)
        assert result is True
        assert server._last_error is None

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

        # Script fails
        assert result is False
        assert server._last_error is not None
        assert "exited with code" in server._last_error or "SyntaxError" in str(
            server._last_traceback
        )

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

        # Script fails
        assert result is False
        assert server._last_error is not None

        # Clean up
        server.stop()
        script_path.unlink()

    def test_generate_payload_no_files(self):
        """Test generating payload when no DXF/IFC files exist."""
        from bimascode.server.preview_server import PreviewServer

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("x = 42\n")  # Script that doesn't export anything
            script_path = Path(f.name)

        server = PreviewServer(script_path)
        server.execute_script()

        payload = server.generate_payload()

        # No files found, returns error
        assert payload["type"] == "error"
        assert "No DXF or IFC files found" in payload["message"]
        assert "timestamp" in payload

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
        assert server._last_error is not None
        assert "timestamp" in payload
        assert "traceback" in payload

        # Clean up
        server.stop()
        script_path.unlink()

    def test_generate_payload_with_dxf_files(self):
        """Test generating success payload when DXF files exist."""
        from bimascode.server.preview_server import PreviewServer

        # Create a script that creates a DXF file
        with tempfile.TemporaryDirectory() as output_dir:
            script_content = f"""
import sys
from pathlib import Path
# Create a simple DXF file
output = Path("{output_dir}") / "test.dxf"
output.write_text("0\\nSECTION\\n0\\nENDSEC\\n0\\nEOF\\n")
"""
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
                f.write(script_content)
                script_path = Path(f.name)

            server = PreviewServer(script_path, output_dir=output_dir)
            server.execute_script()

            # Create a valid DXF file manually for the test
            import ezdxf

            doc = ezdxf.new()
            msp = doc.modelspace()
            msp.add_line((0, 0), (100, 100))
            dxf_path = Path(output_dir) / "test.dxf"
            doc.saveas(str(dxf_path))

            # Re-scan output files
            server._scan_output_files()

            payload = server.generate_payload()

            assert payload["type"] == "update"
            assert "timestamp" in payload
            assert "views" in payload
            assert "dxf_files" in payload
            assert "test" in payload["dxf_files"]

            # Clean up
            server.stop()
            script_path.unlink()


class TestDXFReader:
    """Tests for DXF reader module."""

    def test_dxf_reader_import(self):
        """Test that DXF reader can be imported."""
        from bimascode.server.dxf_reader import read_dxf_to_view_data

        assert read_dxf_to_view_data is not None

    def test_read_simple_dxf(self):
        """Test reading a simple DXF file."""
        import ezdxf

        from bimascode.server.dxf_reader import read_dxf_to_view_data

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple DXF file
            doc = ezdxf.new()
            msp = doc.modelspace()
            msp.add_line((0, 0), (100, 100))
            msp.add_circle((50, 50), 25)

            dxf_path = Path(temp_dir) / "test.dxf"
            doc.saveas(str(dxf_path))

            # Read it back
            view_data = read_dxf_to_view_data(dxf_path)

            assert view_data["view_name"] == "test"
            assert len(view_data["lines"]) == 1
            assert len(view_data["arcs"]) == 1  # Circle becomes arc
            assert view_data["lines"][0]["start"]["x"] == 0
            assert view_data["lines"][0]["end"]["x"] == 100

    def test_read_dxf_with_polylines(self):
        """Test reading DXF with polylines."""
        import ezdxf

        from bimascode.server.dxf_reader import read_dxf_to_view_data

        with tempfile.TemporaryDirectory() as temp_dir:
            doc = ezdxf.new()
            msp = doc.modelspace()
            msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)

            dxf_path = Path(temp_dir) / "test.dxf"
            doc.saveas(str(dxf_path))

            view_data = read_dxf_to_view_data(dxf_path)

            assert len(view_data["polylines"]) == 1
            assert view_data["polylines"][0]["closed"] is True
            assert len(view_data["polylines"][0]["points"]) == 4


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

    def test_cli_parser_output_option(self):
        """Test parsing --output option."""
        from bimascode.server.cli import create_parser

        parser = create_parser()

        args = parser.parse_args(["serve", "test.py", "--output", "/tmp/output"])
        assert args.output == "/tmp/output"

        # Also test short form
        args = parser.parse_args(["serve", "test.py", "-o", "/tmp/output2"])
        assert args.output == "/tmp/output2"

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
            output=None,
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
            output=None,
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

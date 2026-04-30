"""Command-line interface for BIM as Code preview server.

Usage:
    bimascode serve <script.py> [--port PORT] [--host HOST] [--no-browser]
"""

import argparse
import asyncio
import sys
import webbrowser
from pathlib import Path


def serve_command(args: argparse.Namespace) -> int:
    """Run the serve command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    from bimascode.server.preview_server import PreviewServer

    script_path = Path(args.script)

    # Validate script exists
    if not script_path.exists():
        print(f"Error: File not found: {script_path}", file=sys.stderr)
        return 1

    if not script_path.suffix == ".py":
        print(f"Error: File must be a Python script: {script_path}", file=sys.stderr)
        return 1

    # Resolve output directory
    output_dir = Path(args.output) if args.output else None

    # Create server
    server = PreviewServer(
        script_path=script_path,
        host=args.host,
        port=args.port,
        output_dir=output_dir,
    )

    # Open browser if requested
    if not args.no_browser:
        url = f"http://{args.host}:{args.port + 1}/"
        # Open browser after a short delay to let server start
        import threading

        def open_browser():
            import time

            time.sleep(0.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    # Run server
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="bimascode",
        description="BIM as Code - Programmatic Building Information Modeling",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start live preview server for a BIM script",
        description="Watch a Python script and serve live 2D/3D previews to a web browser.",
    )
    serve_parser.add_argument(
        "script",
        help="Path to the Python script to watch and execute",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket port (HTTP server uses port+1). Default: 8765",
    )
    serve_parser.add_argument(
        "--host",
        default="localhost",
        help="Host address to bind to. Use 0.0.0.0 for remote access. Default: localhost",
    )
    serve_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open browser on start",
    )
    serve_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output directory for exported files. If not specified, uses a temp directory.",
    )

    return parser


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "serve":
        return serve_command(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())

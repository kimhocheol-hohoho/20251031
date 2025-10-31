"""Simple development server for the analysis dashboard.

This module exposes a tiny HTTP server that serves the static dashboard
contained under the ``web/`` directory alongside the generated figures.
It is intended for local exploration only and relies entirely on the
Python standard library, so no additional dependencies are required.
"""

from __future__ import annotations

import argparse
import contextlib
import http.server
import os
import socket
import socketserver
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("DASHBOARD_PORT", "8000"))


class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serve the repository's dashboard assets.

    The handler anchors all requests at ``PROJECT_ROOT`` and rewrites the
    root path to ``web/index.html`` so that visiting ``/`` immediately
    renders the dashboard.
    """

    # Silence the overly chatty default logging.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - match signature
        sys.stdout.write("[HTTP] " + (format % args) + "\n")

    def translate_path(self, path: str) -> str:
        """Map URL paths onto files inside the repository.

        ``SimpleHTTPRequestHandler`` normally serves files relative to the
        current working directory. Overriding ``translate_path`` allows us to
        anchor the handler to the repository root and redirect requests for
        ``/`` to the dashboard's entry point.
        """

        # ``SimpleHTTPRequestHandler`` expects a filesystem path, so strip any
        # query parameters before rewriting the route.
        path = path.split("?", 1)[0].split("#", 1)[0]

        if path in {"", "/"}:
            path = "/web/index.html"

        # Ensure there is exactly one leading slash before combining with the
        # project root.
        normalized = "/" + path.lstrip("/")
        return str(PROJECT_ROOT.joinpath(normalized.lstrip("/")))


def find_available_port(host: str, port: int) -> tuple[str, int]:
    """Return ``(host, port)`` ensuring the port is available.

    If the requested port is unavailable, fall back to a random ephemeral
    port on the provided host.
    """

    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            sock.bind((host, 0))
        return sock.getsockname()


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the dashboard HTTP server until interrupted."""

    host, port = find_available_port(host, port)
    handler = DashboardRequestHandler
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    with socketserver.ThreadingTCPServer((host, port), handler) as httpd:
        address = f"http://{host}:{port}/"
        print(f"Serving dashboard at {address}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the analysis dashboard")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host interface to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

"""Command-line entry point for the local imagegen web application."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from imagegen.app import create_app


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="imagegen-web")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="enable Flask debug mode",
    )
    parser.add_argument(
        "--secure-network",
        action="store_true",
        help="listen on all network interfaces",
    )
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)

    app = create_app()
    app.run(
        debug=arguments.dev,
        host="0.0.0.0" if arguments.secure_network else "127.0.0.1",
        port=5002,
    )
    return 0

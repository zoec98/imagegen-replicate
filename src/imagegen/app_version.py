"""Application UI asset versioning."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
APP_VERSION_FILES = (
    PACKAGE_ROOT / "templates" / "index.html",
    PACKAGE_ROOT / "static" / "app.js",
    PACKAGE_ROOT / "static" / "app.css",
)


def app_checksum(paths: Iterable[Path] = APP_VERSION_FILES) -> str:
    """Return a deterministic checksum for UI assets relevant to loaded pages."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]

"""Small image headers used to exercise pre-decode limits without large rasters."""

from __future__ import annotations

import struct
import zlib
from io import BytesIO

from PIL import Image


def oversized_png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buffer, "PNG")
    payload = bytearray(buffer.getvalue())
    struct.pack_into(">II", payload, 16, 8193, 8193)
    struct.pack_into(">I", payload, 29, zlib.crc32(payload[12:29]) & 0xFFFFFFFF)
    return bytes(payload)

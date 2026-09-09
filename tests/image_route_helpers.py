"""Shared helpers for image route tests."""

from io import BytesIO

import httpx
from PIL import Image


def write_sample_png(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(path, "PNG")


def route_image_bytes(image_format):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buffer, image_format)
    return buffer.getvalue()


def import_response_client(response):
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))

"""Shared helpers for Flask route tests."""

import json
from html.parser import HTMLParser


class _ElementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self._open_elements = []

    def handle_starttag(self, tag, attrs):
        element = {"tag": tag, "attrs": dict(attrs), "text": ""}
        self.elements.append(element)
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self._open_elements.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self._open_elements and self._open_elements[-1]["tag"] == tag:
            self._open_elements.pop()

    def handle_endtag(self, tag):
        for index in range(len(self._open_elements) - 1, -1, -1):
            if self._open_elements[index]["tag"] == tag:
                del self._open_elements[index:]
                return

    def handle_data(self, data):
        if self._open_elements:
            self._open_elements[-1]["text"] += data


def parse_html(response):
    parser = _ElementParser()
    parser.feed(response.data.decode("utf-8"))
    return parser.elements


def extract_csrf_token(response):
    marker = b'<meta name="csrf-token" content="'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_app_checksum(response):
    marker = b'<meta name="app-build" content="'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_attribute(response, marker):
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_model_registry(response):
    marker = b'<script id="model-registry-data" type="application/json">'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b"</script>", start)
    return json.loads(response.data[start:end].decode("utf-8"))


def extract_palette_data(response):
    marker = b'<script id="palette-data" type="application/json">'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b"</script>", start)
    return json.loads(response.data[start:end].decode("utf-8"))

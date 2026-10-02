"""Offline regressions for the fal.ai schema helper's HTML contracts."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "get_schema_falai"
source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
schema = ModuleType("get_schema_falai")
sys.modules[schema.__name__] = schema
# Execute only the trusted, checked-in Python section of the shell helper.
exec(  # noqa: S102
    compile(source.replace("raise SystemExit(main())", ""), str(SCRIPT), "exec"),
    schema.__dict__,
)


@pytest.mark.parametrize("mode", ["text-to-image", "edit-image"])
def test_flux3_model_urls_normalize_to_api_docs(mode):
    url = f"https://fal.ai/models/blackforestlabs/flux-3/{mode}"
    for suffix in ("", "/", "/api", "/api/"):
        assert schema.validate_api_url(url + suffix) == url + "/api"


@pytest.mark.parametrize("mode", ["text-to-image", "edit-image"])
def test_flux3_script_jsonld_extracts_endpoint_and_schema(mode, monkeypatch, capsys):
    endpoint = f"blackforestlabs/flux-3/{mode}"
    metadata = {"@type": "WebAPI", "identifier": endpoint, "name": "Flux 3 Image"}
    properties = {"prompt": {"type": "string"}}
    if mode == "edit-image":
        properties["image_urls"] = {"type": "array", "items": {"type": "string"}}
    openapi = {
        "openapi": "3.1.0",
        "paths": {
            f"/{mode}": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Input"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Output"}
                                }
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "Input": {"required": list(properties), "properties": properties},
                "Output": {
                    "properties": {
                        "images": {"type": "array", "items": {"type": "object"}}
                    }
                },
            }
        },
    }
    # fal.ai serves JSON-LD in script tags and OpenAPI in escaped Next.js data.
    flight = json.dumps({"metadata": {"openapi": openapi}}, separators=(",", ":"))
    page = (
        '<script type="application/ld+json">'
        + json.dumps(metadata)
        + "</script>"
        + "<script>self.__next_f.push([1,"
        + json.dumps(flight)
        + "]);</script>"
    )
    monkeypatch.setattr(schema, "fetch", lambda url: page)
    monkeypatch.setattr(schema, "fetch_platform_pricing", lambda endpoint: None)
    parsed = schema.fetch_endpoint_page(f"https://fal.ai/models/{endpoint}/api")
    assert parsed.endpoint == endpoint
    extracted = schema.extract_endpoint_schema(parsed.page, parsed.endpoint)
    assert extracted.input_schema["properties"] == properties
    assert "images" in extracted.output_schema["properties"]
    schema.print_page_summary(parsed, paired=mode == "edit-image")
    output = capsys.readouterr().out
    assert "Input schema: `Input`" in output
    assert "`prompt`" in output
    assert (
        "`image_urls`" in output
        if mode == "edit-image"
        else "`image_urls`" not in output
    )
    assert "no embedded OpenAPI schema" not in output


def test_legacy_meta_jsonld_still_supported():
    metadata = {"@type": "WebAPI", "identifier": "fal-ai/example"}
    page = (
        '<meta name="application/ld+json" content="'
        + html.escape(json.dumps(metadata), quote=True)
        + '">'
    )
    assert schema.jsonld_metadata(page) == metadata


def test_jsonld_ignores_unrelated_and_malformed_scripts():
    page = """<script type='application/ld+json'>{invalid}</script>
    <script type='application/ld+json'>{"@type":"Organization"}</script>
    <script data-extra='yes' type='application/ld+json'>
    {"@type":"WebAPI","identifier":"fal-ai/example","name":"Café & light"}
    </script>"""
    assert schema.jsonld_endpoint(page) == "fal-ai/example"
    assert schema.jsonld_metadata(page)["name"] == "Café & light"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/models/fal-ai/example",
        "https://fal.ai/not-models/example",
        "https://fal.ai/models/",
    ],
)
def test_invalid_model_urls_still_rejected(url):
    with pytest.raises(SystemExit):
        schema.validate_api_url(url)

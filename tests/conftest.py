"""Shared test fixtures.

Behaviors protected:
- Test apps use isolated configuration and data directories.
- Route tests do not start real generation work unless they explicitly inject it.
"""

import pytest

from imagegen.app import create_app
from imagegen.config import AppConfig
from imagegen.model_registry import MODEL_REGISTRY


class NoopGenerationWorker:
    def start(self, request_record):
        pass


@pytest.fixture
def app_config(tmp_path):
    return AppConfig(
        replicate_api_token="test-token",
        fal_key="",
        enabled_providers=("replicate",),
        selected_provider="replicate",
        data_dir=tmp_path,
        author="Test Author",
        immich_url="",
        immich_upload_album_id="",
        immich_api_key="",
        model_alias="seedream45",
        model=MODEL_REGISTRY["seedream45"],
        flask_secret_key="test-secret",
        replicate_poll_seconds=1.0,
        replicate_timeout_seconds=60.0,
        trashcan_hold_limit_days=7,
    )


@pytest.fixture
def app_factory(app_config):
    def make_app(**config):
        config.setdefault("IMAGEGEN_WORKER", NoopGenerationWorker())
        return create_app(
            {
                "IMAGEGEN_APP_CONFIG": app_config,
                "TESTING": True,
                **config,
            }
        )

    return make_app

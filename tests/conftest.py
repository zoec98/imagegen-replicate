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
        replicate_api_token="",
        data_dir=tmp_path,
        immich_url="",
        immich_gallery_id="",
        immich_api_key="",
        model_alias="seedream45",
        model=MODEL_REGISTRY["seedream45"],
        flask_secret_key="test-secret",
        replicate_poll_seconds=1.0,
        replicate_timeout_seconds=60.0,
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

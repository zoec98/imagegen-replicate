import pytest

from imagegen.app import create_app
from imagegen.config import AppConfig
from imagegen.model_registry import MODEL_REGISTRY


@pytest.fixture
def app_factory(tmp_path):
    def make_app(**config):
        app_config = AppConfig(
            replicate_api_token="",
            output_dir=tmp_path,
            model_alias="seedream45",
            model=MODEL_REGISTRY["seedream45"],
            flask_secret_key="test-secret",
            replicate_poll_seconds=1.0,
            replicate_timeout_seconds=60.0,
        )
        return create_app(
            {
                "IMAGEGEN_APP_CONFIG": app_config,
                "IMAGEGEN_OUTPUT_DIR": tmp_path,
                "TESTING": True,
                **config,
            }
        )

    return make_app

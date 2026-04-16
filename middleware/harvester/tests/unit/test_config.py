"""Unit tests for the Harvester orchestrator configuration."""

import pytest
from pydantic import ValidationError

from middleware.api_client.config import Config as ApiClientConfig
from middleware.harvester.config import Config, RepositoryConfig
from middleware.inspire.config import Config as InspireConfig


def test_harvester_config_loading() -> None:
    """Test loading and validating the root harvester config using the keyed-map format."""
    raw_config = {
        "api_client": {
            "api_url": "https://api.example.com",
        },
        "repositories": [
            {
                "rdi": "test-import",
                "inspire": {
                    "csw_url": "https://csw.example.com",
                },
            }
        ],
    }

    config = Config.model_validate(raw_config)
    assert isinstance(config.api_client, ApiClientConfig)
    assert str(config.api_client.api_url).rstrip("/") == "https://api.example.com"

    assert len(config.repositories) == 1
    repo: RepositoryConfig = config.repositories[0]
    assert repo.plugin_type == "inspire"
    assert isinstance(repo.plugin_config, InspireConfig)
    assert repo.rdi == "test-import"
    assert repo.plugin_config.csw_url == "https://csw.example.com"


def test_repository_config_rejects_no_plugin() -> None:
    """RepositoryConfig must reject an entry with no plugin key set."""
    with pytest.raises(ValidationError):
        RepositoryConfig.model_validate({})


def test_repository_config_rejects_unknown_plugin() -> None:
    """RepositoryConfig must reject an entry with an unrecognised plugin key."""
    with pytest.raises(ValidationError):
        RepositoryConfig.model_validate({"unknown_plugin": {"some_field": "value"}})

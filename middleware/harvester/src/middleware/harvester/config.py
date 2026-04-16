"""Configuration module for the Middleware Harvester core orchestrator."""

from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, model_validator

from middleware.api_client.config import Config as ApiClientConfig
from middleware.harvester.plugin_config import PluginConfig
from middleware.inspire.config import Config as InspireConfig
from middleware.shared.config.config_base import ConfigBase


class RepositoryConfig(BaseModel):
    """Configuration for an individual harvesting plugin/repository.

    Exactly one plugin key must be set per entry. The YAML format is:

        repositories:
          - inspire:
              csw_url: "https://..."
              rdi: "my-rdi"
    """

    _PLUGIN_FIELDS: ClassVar[frozenset[str]] = frozenset({"inspire"})
    # When adding a new plugin, add its field name here AND as an optional field below.

    rdi: Annotated[
        str,
        Field(description="RDI identifier (e.g. inspire-import)"),
    ]
    inspire: Annotated[
        InspireConfig | None,
        Field(description="INSPIRE CSW plugin configuration"),
    ] = None

    @model_validator(mode="after")
    def exactly_one_plugin(self) -> "RepositoryConfig":
        """Ensure exactly one plugin key is set."""
        set_fields = [f for f in self._PLUGIN_FIELDS if getattr(self, f) is not None]
        if len(set_fields) != 1:
            raise ValueError(f"Each repository entry must have exactly one plugin key; got: {set_fields or 'none'}")
        return self

    @property
    def plugin_type(self) -> str:
        """Return the active plugin type name."""
        if self.inspire is not None:
            return "inspire"
        raise RuntimeError("No plugin key set — did model validation run?")  # pragma: no cover

    @property
    def plugin_config(self) -> PluginConfig:
        """Return the active plugin configuration object."""
        if self.inspire is not None:
            return self.inspire
        raise RuntimeError("No plugin config set — did model validation run?")  # pragma: no cover


class Config(ConfigBase):
    """Configuration model for the Middleware Harvester."""

    api_client: Annotated[
        ApiClientConfig,
        Field(description="API Client configuration for FAIRagro Middleware API"),
    ]
    repositories: Annotated[
        list[RepositoryConfig],
        Field(description="List of repositories to harvest from, mapped to plugins"),
    ]

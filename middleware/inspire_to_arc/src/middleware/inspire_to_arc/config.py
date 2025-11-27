"""Configuration module for the Inspire to ARC middleware."""

from typing import Annotated

from pydantic import Field

from middleware.api_client.config import Config as ApiClientConfig
from middleware.shared.config.config_base import ConfigBase


class Config(ConfigBase):
    """Configuration model for the Inspire to ARC middleware."""

    csw_url: Annotated[str, Field(description="URL of the CSW endpoint")]
    rdi: Annotated[str, Field(description="RDI identifier (e.g. inspire-import)")] = "inspire-import"
    batch_size: Annotated[int, Field(description="Batch size for ARC uploads", gt=0)] = 10
    query: Annotated[str | None, Field(description="CQL query string for filtering records")] = None
    api_client: Annotated[ApiClientConfig, Field(description="API Client configuration")]

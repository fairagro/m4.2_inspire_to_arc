"""Configuration module for the Inspire to ARC middleware."""

from typing import Annotated

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration model for the Inspire to ARC middleware."""

    csw_url: Annotated[str, Field(description="URL of the CSW endpoint")]
    query: Annotated[str | None, Field(description="CQL query string for filtering records")] = None
    xml_request: Annotated[str | None, Field(description="Raw XML request for advanced queries")] = None

"""Configuration module for the Inspire to ARC middleware."""

from typing import Annotated

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration model for the Inspire to ARC middleware."""

    csw_url: Annotated[str, Field(description="URL of the CSW endpoint")]
    cql_query: Annotated[
        str | None,
        Field(description="CQL filter string, e.g. \"AnyText LIKE '%agriculture%'\""),
    ] = None
    xml_query: Annotated[str | None, Field(description="Raw GetRecords XML body (overrides cql_query)")] = None
    chunk_size: Annotated[
        int,
        Field(description="Number of records to fetch per paginated request.", ge=1),
    ] = 50

    max_records: Annotated[
        int | None,
        Field(description="Maximum number of records to harvest (None = all records). Debug option."),
    ] = None

    timeout: Annotated[
        int,
        Field(description="CSW connection timeout in seconds.", ge=1),
    ] = 30

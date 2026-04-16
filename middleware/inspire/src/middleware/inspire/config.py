"""Configuration module for the Inspire to ARC middleware."""

from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def _check_mutually_exclusive_filters(self) -> Self:
        """Ensure at most one of cql_query and xml_query is set."""
        if self.cql_query is not None and self.xml_query is not None:
            raise ValueError(
                "Config conflict: cql_query and xml_query are mutually exclusive. Provide at most one of them."
            )
        return self

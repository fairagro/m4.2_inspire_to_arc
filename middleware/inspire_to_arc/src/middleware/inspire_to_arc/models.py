"""Domain models for INSPIRE metadata records.

These Pydantic models represent the data structures parsed from ISO 19139 XML
by the CSW client and consumed by the mapper.
"""

from typing import Annotated

from pydantic import BaseModel, Field


class ResourceIdentifier(BaseModel):
    """Resource identifier (DOI, ISBN, etc.)."""

    code: str
    codespace: str | None = None
    url: str | None = None


class InspireDate(BaseModel):
    """Date with type (creation, publication, revision)."""

    date: str
    datetype: str | None = None  # "creation", "publication", "revision"


class SpatialResolutionDistance(BaseModel):
    """Spatial resolution as distance with unit."""

    value: float
    uom: str  # Unit of measure (e.g., "m", "km")


class DistributionFormat(BaseModel):
    """Data distribution format information."""

    name: str
    version: str | None = None
    specification: str | None = None
    name_url: str | None = None
    version_url: str | None = None
    specification_url: str | None = None


class OnlineResource(BaseModel):
    """Online resource (download link, service endpoint, etc.)."""

    url: str
    protocol: str | None = None
    protocol_url: str | None = None
    name: str | None = None
    name_url: str | None = None
    description: str | None = None
    description_url: str | None = None
    function: str | None = None  # "download", "information", etc.


class ConformanceResult(BaseModel):
    """Data quality conformance result."""

    specification_title: str
    specification_title_url: str | None = None
    specification_date: str | None = None
    specification_datetype: str | None = None
    degree: str | None = None  # "true"/"false" or pass/fail


class ReferenceSystem(BaseModel):
    """Coordinate reference system information."""

    code: str
    code_url: str | None = None
    codespace: str | None = None
    codespace_url: str | None = None
    version: str | None = None
    version_url: str | None = None


class Contact(BaseModel):
    """Enhanced contact information with full CI_ResponsibleParty details."""

    # Core fields (existing)
    name: str | None = None
    name_url: str | None = None
    organization: str | None = None
    organization_url: str | None = None
    email: str | None = None
    role: str | None = None
    type: str | None = None  # "metadata" or "resource"

    # Extended fields (new)
    position: str | None = None
    phone: str | None = None
    fax: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    postcode: str | None = None
    country: str | None = None
    online_resource_url: str | None = None
    online_resource_protocol: str | None = None
    online_resource_name: str | None = None
    online_resource_description: str | None = None


class InspireRecord(BaseModel):
    """Comprehensive representation of an INSPIRE metadata record."""

    # Core identification (existing fields)
    identifier: str
    title: str
    abstract: str
    date_stamp: str | None = None
    keywords: Annotated[list[str], Field(default_factory=list)]
    topic_categories: Annotated[list[str], Field(default_factory=list)]
    contacts: Annotated[list[Contact], Field(default_factory=list)]
    lineage: str | None = None
    spatial_extent: list[float] | None = None  # [minx, miny, maxx, maxy]
    temporal_extent: tuple[str | None, str | None] | None = None  # (start, end)
    constraints: Annotated[list[str], Field(default_factory=list)]

    # Metadata-level fields (new)
    parent_identifier: str | None = None
    language: str | None = None
    charset: str | None = None
    hierarchy: str | None = None
    metadata_standard_name: str | None = None
    metadata_standard_version: str | None = None
    dataset_uri: str | None = None

    # Identification - Core (new)
    alternate_title: str | None = None
    resource_identifiers: Annotated[list[ResourceIdentifier], Field(default_factory=list)]
    edition: str | None = None
    purpose: str | None = None
    status: str | None = None
    resource_language: Annotated[list[str], Field(default_factory=list)]
    graphic_overviews: Annotated[list[str], Field(default_factory=list)]  # thumbnail URLs

    # Identification - Dates (new)
    dates: Annotated[list[InspireDate], Field(default_factory=list)]

    # Identification - Resolution (new)
    spatial_resolution_denominators: Annotated[list[int], Field(default_factory=list)]
    spatial_resolution_distances: Annotated[list[SpatialResolutionDistance], Field(default_factory=list)]

    # Identification - Contacts by role (new)
    creators: Annotated[list[Contact], Field(default_factory=list)]  # role=originator
    publishers: Annotated[list[Contact], Field(default_factory=list)]  # role=publisher
    contributors: Annotated[list[Contact], Field(default_factory=list)]  # role=author

    # Constraints (detailed, new)
    access_constraints: Annotated[list[str], Field(default_factory=list)]
    use_constraints: Annotated[list[str], Field(default_factory=list)]
    classification: Annotated[list[str], Field(default_factory=list)]
    other_constraints: Annotated[list[str], Field(default_factory=list)]
    other_constraints_url: Annotated[list[str], Field(default_factory=list)]

    # Distribution (new)
    distribution_formats: Annotated[list[DistributionFormat], Field(default_factory=list)]
    online_resources: Annotated[list[OnlineResource], Field(default_factory=list)]

    # Data Quality (new)
    conformance_results: Annotated[list[ConformanceResult], Field(default_factory=list)]
    lineage_url: str | None = None  # if lineage uses gmx:Anchor

    # Reference System (new)
    reference_systems: Annotated[list[ReferenceSystem], Field(default_factory=list)]

    # Supplemental (new)
    supplemental_information: str | None = None

    # Raw XML for archival
    raw_xml: bytes | None = None

    # Note: acquisition and contentinfo are complex nested objects that will be
    # handled separately if needed (mapped as Assay Protocols in the mapper)

"""CSW Harvester for INSPIRE metadata records."""

import contextlib
import logging
from collections.abc import Iterator
from typing import Annotated, cast

from owslib.csw import CatalogueServiceWeb  # type: ignore
from owslib.iso import MD_DataIdentification, MD_Metadata  # type: ignore
from pydantic import BaseModel, Field

from .errors import SemanticError

logger = logging.getLogger(__name__)


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
    abstract: str | None = None
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

    # Note: acquisition and contentinfo are complex nested objects that will be
    # handled separately if needed (mapped as Assay Protocols in the mapper)


class CSWClient:
    """Client for harvesting metadata from a CSW endpoint."""

    def __init__(self, url: str, timeout: int = 30):
        """
        Initialize the CSWClient with the CSW endpoint URL and optional timeout.

        Args:
            url: The CSW endpoint URL.
            timeout: Timeout in seconds for the connection (default: 30).
        """
        self._url = url
        self._timeout = timeout
        self._csw = None  # type: ignore

    def connect(self) -> None:
        """Connect to the CSW service."""
        try:
            self._csw = CatalogueServiceWeb(self._url, timeout=self._timeout)
            csw_title = None
            if self._csw and hasattr(self._csw, "identification") and self._csw.identification:
                csw_title = getattr(self._csw.identification, "title", None)
            logger.info("Connected to CSW: %s", csw_title)
        except Exception as e:
            logger.error("Failed to connect to CSW at %s: %s", self._url, e)
            raise

    def get_records(self, _query: str | None = None, max_records: int = 10) -> Iterator[InspireRecord]:
        """
        Retrieve records from the CSW.

        Args:
            query: Optional CQL query string (not fully implemented yet).
            max_records: Maximum number of records to retrieve.

        Yields:
            InspireRecord objects.
        """
        if self._csw is None:
            self.connect()
        if self._csw is None:
            logger.error("CSW client is not initialized.")
            return

        # Simple implementation: get all records (paged) up to max_records
        # For GDI-DE, we might need specific constraints to get INSPIRE data
        # outputschema="http://www.isotc211.org/2005/gmd" is standard for ISO 19139

        start_position = 0
        records_yielded = 0

        while records_yielded < max_records:
            batch_size = min(10, max_records - records_yielded)
            if batch_size <= 0:
                break

            self._csw.getrecords(
                maxrecords=batch_size,
                startposition=start_position,
                esn="full",
                outputschema="http://www.isotc211.org/2005/gmd",
            )

            if not self._csw.records:
                break

            for _uuid, record in self._csw.records.items():
                if records_yielded >= max_records:
                    break

                if isinstance(record, MD_Metadata):
                    yield self._parse_iso_record(record)
                    records_yielded += 1

            start_position += len(self._csw.records)
            matches = self._csw.results.get("matches")
            if isinstance(matches, int) and start_position >= matches:
                break

    def _parse_iso_record(self, iso: MD_Metadata) -> InspireRecord:
        """Parse an OWSLib MD_Metadata object into an InspireRecord."""
        # Ensure identifier is always a string, fallback to "unknown" if None or not a string
        identifier = iso.identifier if isinstance(iso.identifier, str) and iso.identifier else "unknown"
        identification = self._extract_identification(iso)

        return InspireRecord(
            # Core identification (existing fields)
            identifier=identifier,
            title=self._extract_title(identification),
            abstract=self._extract_identification_str("abstract", identification),
            date_stamp=iso.datestamp,
            keywords=self._extract_identification_list("keywords", identification),
            topic_categories=self._extract_identification_list("topiccategory", identification),
            contacts=self._extract_contacts(iso),
            lineage=self._extract_lineage(iso),
            spatial_extent=self._extract_spatial_extent(iso),
            temporal_extent=self._extract_temporal_extent(iso),
            constraints=self._extract_constraints(iso),
            # Metadata-level fields (new)
            parent_identifier=getattr(iso, "parentidentifier", None),
            language=getattr(iso, "language", None) or getattr(iso, "languagecode", None),
            charset=getattr(iso, "charset", None),
            hierarchy=getattr(iso, "hierarchy", None),
            metadata_standard_name=getattr(iso, "stdname", None),
            metadata_standard_version=getattr(iso, "stdver", None),
            dataset_uri=getattr(iso, "dataseturi", None),
            # Identification - Core (new)
            alternate_title=self._extract_identification_str("alternatetitle", identification),
            resource_identifiers=self._extract_resource_identifiers(identification),
            edition=self._extract_identification_str("edition", identification),
            purpose=self._extract_identification_str("purpose", identification),
            status=self._extract_identification_str("status", identification),
            resource_language=self._extract_resource_language(identification),
            graphic_overviews=self._extract_graphic_overviews(identification),
            # Identification - Dates (new)
            dates=self._extract_dates(identification),
            # Identification - Resolution (new)
            spatial_resolution_denominators=self._extract_resolution_denominators(identification),
            spatial_resolution_distances=self._extract_resolution_distances(identification),
            # Identification - Contacts by role (new)
            creators=self._extract_contacts_by_role(identification, "originator"),
            publishers=self._extract_contacts_by_role(identification, "publisher"),
            contributors=self._extract_contacts_by_role(identification, "author"),
            # Constraints (detailed, new)
            access_constraints=self._extract_access_constraints(identification),
            use_constraints=self._extract_use_constraints(identification),
            classification=self._extract_classification(identification),
            other_constraints=self._extract_other_constraints(identification),
            other_constraints_url=self._extract_other_constraints_url(identification),
            # Distribution (new)
            distribution_formats=self._extract_distribution_formats(iso),
            online_resources=self._extract_online_resources(iso),
            # Data Quality (new)
            conformance_results=self._extract_conformance_results(iso),
            lineage_url=self._extract_lineage_url(iso),
            # Reference System (new)
            reference_systems=self._extract_reference_systems(iso),
            # Supplemental (new)
            supplemental_information=self._extract_identification_str("supplementalinformation", identification),
        )

    def _extract_identification(self, iso: MD_Metadata) -> MD_DataIdentification | None:
        """Extract identification info from ISO record."""
        if isinstance(iso.identification, list) and iso.identification:
            return cast(MD_DataIdentification, iso.identification[0])
        elif iso.identification:
            return cast(MD_DataIdentification, iso.identification)
        return None

    def _extract_title(self, identification: MD_DataIdentification | None) -> str:
        """Extract title from ISO record."""
        if identification is None or getattr(identification, "title", None) is None:
            raise SemanticError("Record is missing a title in its identification section.")
        if not isinstance(identification.title, str):
            raise SemanticError("Record title is not a string.")
        return identification.title

    def _extract_identification_str(self, item: str, identification: MD_DataIdentification | None) -> str | None:
        """Extract a string attribute from ISO record."""
        if identification is None:
            return None
        value = getattr(identification, item, None)
        # Ensure we only return actual strings, not MagicMock or other objects
        if value and isinstance(value, str):
            return value  # type: ignore[no-any-return]
        return None

    def _extract_identification_list(self, item: str, identification: MD_DataIdentification | None) -> list[str]:
        """Extract a list attribute from ISO record."""
        result: list[str] = []
        if identification is None:
            return result
        if hasattr(identification, item):
            attr = getattr(identification, item)
            if isinstance(attr, list):
                result.extend([str(i) for i in attr if isinstance(i, str)])
            elif isinstance(attr, str):
                result.append(attr)
        return result

    def _extract_contacts(self, iso: MD_Metadata) -> list[Contact]:
        """Extract contacts from ISO record."""
        contacts = []
        if iso.contact:
            contacts.extend(self._format_contacts(iso.contact, "metadata"))
        identification = self._extract_identification(iso)
        if identification and identification.contact:
            contacts.extend(self._format_contacts(identification.contact, "resource"))
        return contacts

    def _format_contacts(self, contact_list: list, contact_type: str) -> list[Contact]:
        """Format contact list."""
        return [
            Contact(
                name=c.name,
                organization=c.organization,
                email=c.email,
                role=c.role,
                type=contact_type,
            )
            for c in contact_list
        ]

    def _extract_lineage(self, iso: MD_Metadata) -> str | None:
        """Extract lineage from ISO record."""
        if iso.dataquality and iso.dataquality.lineage:
            lineage = iso.dataquality.lineage
            if isinstance(lineage, str):
                return lineage
            if hasattr(lineage, "statement"):
                statement = lineage.statement
                return statement if isinstance(statement, str) else None
        return None

    def _extract_spatial_extent(self, iso: MD_Metadata) -> list[float] | None:
        """Extract spatial extent from ISO record."""
        identification = self._extract_identification(iso)
        if identification and identification.bbox:
            bbox = identification.bbox
            if bbox and all(hasattr(bbox, attr) for attr in ["minx", "miny", "maxx", "maxy"]):
                try:
                    minx = getattr(bbox, "minx", None)
                    miny = getattr(bbox, "miny", None)
                    maxx = getattr(bbox, "maxx", None)
                    maxy = getattr(bbox, "maxy", None)
                    if all(v is not None for v in [minx, miny, maxx, maxy]):
                        return [
                            float(cast(float, minx)),
                            float(cast(float, miny)),
                            float(cast(float, maxx)),
                            float(cast(float, maxy)),
                        ]
                except (ValueError, TypeError):
                    return None
        return None

    def _extract_temporal_extent(self, iso: MD_Metadata) -> tuple[str | None, str | None] | None:
        """Extract temporal extent from ISO record."""
        identification = self._extract_identification(iso)
        if identification and hasattr(identification, "temporalextent_start") and identification.temporalextent_start:
            return (identification.temporalextent_start, getattr(identification, "temporalextent_end", None))
        return None

    def _extract_constraints(self, iso: MD_Metadata) -> list[str]:
        """Extract constraints from ISO record."""
        constraints = []
        identification = self._extract_identification(iso)
        if identification:
            # Check for resourceconstraint (singular) which is the standard OWSLib attribute
            resource_constraints = getattr(identification, "resourceconstraint", None)
            if resource_constraints:
                if isinstance(resource_constraints, list):
                    for c in resource_constraints:
                        if hasattr(c, "use_limitation") and c.use_limitation:
                            constraints.extend(c.use_limitation)
                elif hasattr(resource_constraints, "use_limitation") and resource_constraints.use_limitation:
                    constraints.extend(resource_constraints.use_limitation)
        return constraints

    # === New Extraction Methods for Extended INSPIRE Fields ===

    def _extract_resource_identifiers(self, identification: MD_DataIdentification | None) -> list[ResourceIdentifier]:
        """Extract resource identifiers (DOI, ISBN, etc.) from citation/identifier."""
        identifiers: list[ResourceIdentifier] = []
        if identification is None:
            return identifiers

        # uricode and uricodespace are lists in OWSLib
        uricode_list = getattr(identification, "uricode", [])
        uricodespace_list = getattr(identification, "uricodespace", [])

        # Zip them together, padding shorter list with None
        max_len = max(len(uricode_list), len(uricodespace_list))
        for i in range(max_len):
            code = uricode_list[i] if i < len(uricode_list) else None
            codespace = uricodespace_list[i] if i < len(uricodespace_list) else None
            if code:
                identifiers.append(
                    ResourceIdentifier(code=code, codespace=codespace, url=code if code.startswith("http") else None)
                )
        return identifiers

    def _extract_dates(self, identification: MD_DataIdentification | None) -> list[InspireDate]:
        """Extract citation dates with types (creation, publication, revision)."""
        dates: list[InspireDate] = []
        if identification is None:
            return dates

        ci_dates = getattr(identification, "date", [])
        for ci_date in ci_dates:
            if hasattr(ci_date, "date") and hasattr(ci_date, "type"):
                dates.append(InspireDate(date=ci_date.date, datetype=ci_date.type))
        return dates

    def _extract_resource_language(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract resource language(s)."""
        langs: list[str] = []
        if identification is None:
            return langs

        # OWSLib has both resourcelanguage and resourcelanguagecode
        langs.extend(getattr(identification, "resourcelanguagecode", []))
        langs.extend(getattr(identification, "resourcelanguage", []))
        return [lang for lang in langs if lang]  # Filter out None/empty

    def _extract_graphic_overviews(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract thumbnail/preview image URLs."""
        if identification is None:
            return []
        return getattr(identification, "graphicoverview", [])

    def _extract_resolution_denominators(self, identification: MD_DataIdentification | None) -> list[int]:
        """Extract spatial resolution as scale denominators."""
        if identification is None:
            return []
        denoms = getattr(identification, "denominators", [])
        return [int(d) for d in denoms if d]

    def _extract_resolution_distances(
        self, identification: MD_DataIdentification | None
    ) -> list[SpatialResolutionDistance]:
        """Extract spatial resolution as distances with units."""
        if identification is None:
            return []

        distances = []
        distance_vals = getattr(identification, "distance", [])
        uom_vals = getattr(identification, "uom", [])

        for i, dist in enumerate(distance_vals):
            uom = uom_vals[i] if i < len(uom_vals) else "m"
            if dist:
                with contextlib.suppress(ValueError, TypeError):
                    distances.append(SpatialResolutionDistance(value=float(dist), uom=uom or "m"))
        return distances

    def _extract_contacts_by_role(self, identification: MD_DataIdentification | None, role_name: str) -> list[Contact]:
        """Extract contacts filtered by specific role."""
        contacts: list[Contact] = []
        if identification is None:
            return contacts

        # Get role-specific lists from OWSLib
        if role_name == "originator":
            contact_list = getattr(identification, "creator", [])
        elif role_name == "publisher":
            contact_list = getattr(identification, "publisher", [])
        elif role_name == "author":
            contact_list = getattr(identification, "contributor", [])
        else:
            return contacts

        return self._format_contacts(contact_list, "resource")

    def _extract_access_constraints(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract access constraints."""
        if identification is None:
            return []
        return getattr(identification, "accessconstraints", [])

    def _extract_use_constraints(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract use constraints."""
        if identification is None:
            return []
        return getattr(identification, "useconstraints", [])

    def _extract_classification(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract classification constraints."""
        if identification is None:
            return []
        return getattr(identification, "classification", [])

    def _extract_other_constraints(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract other constraints text."""
        if identification is None:
            return []
        return getattr(identification, "otherconstraints", [])

    def _extract_other_constraints_url(self, identification: MD_DataIdentification | None) -> list[str]:
        """Extract other constraints URLs."""
        if identification is None:
            return []
        return getattr(identification, "otherconstraints_url", [])

    def _extract_distribution_formats(self, iso: MD_Metadata) -> list[DistributionFormat]:
        """Extract distribution format information."""
        formats = []  # type: list[DistributionFormat]
        dist = getattr(iso, "distribution", None)
        if dist is None:
            return formats

        if hasattr(dist, "format") and dist.format:
            formats.append(
                DistributionFormat(
                    name=dist.format,
                    version=getattr(dist, "version", None),
                    specification=getattr(dist, "specification", None),
                    name_url=getattr(dist, "format_url", None),
                    version_url=getattr(dist, "version_url", None),
                    specification_url=getattr(dist, "specification_url", None),
                )
            )
        return formats

    def _extract_online_resources(self, iso: MD_Metadata) -> list[OnlineResource]:
        """Extract online resources (download links, service endpoints)."""
        resources = []  # type: list[OnlineResource]
        dist = getattr(iso, "distribution", None)
        if dist is None:
            return resources

        online_list = getattr(dist, "online", [])
        for ol in online_list:
            if hasattr(ol, "url") and ol.url:
                resources.append(
                    OnlineResource(
                        url=ol.url,
                        protocol=getattr(ol, "protocol", None),
                        protocol_url=getattr(ol, "protocol_url", None),
                        name=getattr(ol, "name", None),
                        name_url=getattr(ol, "name_url", None),
                        description=getattr(ol, "description", None),
                        description_url=getattr(ol, "description_url", None),
                        function=getattr(ol, "function", None),
                    )
                )
        return resources

    def _extract_conformance_results(self, iso: MD_Metadata) -> list[ConformanceResult]:
        """Extract data quality conformance results."""
        results = []  # type: list[ConformanceResult]
        dq = getattr(iso, "dataquality", None)
        if dq is None:
            return results

        titles = getattr(dq, "conformancetitle", [])
        title_urls = getattr(dq, "conformancetitle_url", [])
        dates = getattr(dq, "conformancedate", [])
        datetypes = getattr(dq, "conformancedatetype", [])
        degrees = getattr(dq, "conformancedegree", [])

        max_len = max(len(titles), len(dates), len(degrees)) if titles or dates or degrees else 0
        for i in range(max_len):
            title = titles[i] if i < len(titles) else None
            if title:
                results.append(
                    ConformanceResult(
                        specification_title=title,
                        specification_title_url=title_urls[i] if i < len(title_urls) else None,
                        specification_date=dates[i] if i < len(dates) else None,
                        specification_datetype=datetypes[i] if i < len(datetypes) else None,
                        degree=degrees[i] if i < len(degrees) else None,
                    )
                )
        return results

    def _extract_lineage_url(self, iso: MD_Metadata) -> str | None:
        """Extract lineage URL if lineage uses gmx:Anchor."""
        dq = getattr(iso, "dataquality", None)
        if dq is None:
            return None
        value = getattr(dq, "lineage_url", None)
        # Ensure we only return actual strings, not MagicMock or other objects
        if value and isinstance(value, str):
            return value  # type: ignore[no-any-return]
        return None

    def _extract_reference_systems(self, iso: MD_Metadata) -> list[ReferenceSystem]:
        """Extract coordinate reference system(s)."""
        systems = []  # type: list[ReferenceSystem]
        rs = getattr(iso, "referencesystem", None)
        if rs is None:
            return systems

        if hasattr(rs, "code") and rs.code:
            systems.append(
                ReferenceSystem(
                    code=rs.code,
                    code_url=getattr(rs, "code_url", None),
                    codespace=getattr(rs, "codeSpace", None),
                    codespace_url=getattr(rs, "codeSpace_url", None),
                    version=getattr(rs, "version", None),
                    version_url=getattr(rs, "version_url", None),
                )
            )
        return systems

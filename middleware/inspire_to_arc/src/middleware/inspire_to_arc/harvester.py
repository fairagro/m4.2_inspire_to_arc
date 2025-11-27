"""CSW Harvester for INSPIRE metadata records."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import cast

from owslib.csw import CatalogueServiceWeb  # type: ignore
from owslib.iso import MD_DataIdentification, MD_Metadata  # type: ignore

from .errors import SemanticError

logger = logging.getLogger(__name__)


@dataclass
class InspireRecord:  # pylint: disable=too-many-instance-attributes
    """Intermediate representation of an INSPIRE metadata record."""

    identifier: str
    title: str
    abstract: str | None
    date_stamp: str | None
    keywords: list[str] = field(default_factory=list)
    topic_categories: list[str] = field(default_factory=list)
    contacts: list[dict] = field(default_factory=list)
    lineage: str | None = None
    spatial_extent: list[float] | None = None  # [minx, miny, maxx, maxy]
    temporal_extent: tuple[str | None, str | None] | None = None  # (start, end)
    constraints: list[str] = field(default_factory=list)
    # Add more fields as needed


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
            identifier=identifier,
            title=self._extract_title(identification),
            abstract=self._extract_identication_str("abstract", identification),
            date_stamp=iso.datestamp,
            keywords=self.__extract_identification_list("keywords", identification),
            topic_categories=self.__extract_identification_list("topiccategory", identification),
            contacts=self._extract_contacts(iso),
            lineage=self._extract_lineage(iso),
            spatial_extent=self._extract_spatial_extent(iso),
            temporal_extent=self._extract_temporal_extent(iso),
            constraints=self._extract_constraints(iso),
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

    def _extract_identication_str(self, item: str, identification: MD_DataIdentification | None) -> str | None:
        """Extract a string attribute from ISO record."""
        if identification is None:
            return None
        return getattr(identification, item, None)

    def __extract_identification_list(self, item: str, identification: MD_DataIdentification | None) -> list[str]:
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

    def _extract_contacts(self, iso: MD_Metadata) -> list[dict]:
        """Extract contacts from ISO record."""
        contacts = []
        if iso.contact:
            contacts.extend(self._format_contacts(iso.contact, "metadata"))
        identification = self._extract_identification(iso)
        if identification and identification.contact:
            contacts.extend(self._format_contacts(identification.contact, "resource"))
        return contacts

    def _format_contacts(self, contact_list: list, contact_type: str) -> list[dict]:
        """Format contact list."""
        return [
            {
                "name": c.name,
                "organization": c.organization,
                "email": c.email,
                "role": c.role,
                "type": contact_type,
            }
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

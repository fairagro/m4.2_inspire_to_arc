import logging
from typing import Iterator, Optional
from dataclasses import dataclass, field
from owslib.csw import CatalogueServiceWeb  # type: ignore
from owslib.iso import MD_Metadata  # type: ignore

logger = logging.getLogger(__name__)

@dataclass
class InspireRecord:
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
    temporal_extent: tuple[str | None, str | None] | None = None # (start, end)
    constraints: list[str] = field(default_factory=list)
    # Add more fields as needed

class CSWClient:
    """Client for harvesting metadata from a CSW endpoint."""

    def __init__(self, url: str, timeout: int = 30):
        self.url = url
        self.timeout = timeout
        self.csw: CatalogueServiceWeb | None = None

    def connect(self) -> None:
        """Connect to the CSW service."""
        try:
            self.csw = CatalogueServiceWeb(self.url, timeout=self.timeout)
            logger.info(f"Connected to CSW: {self.csw.identification.title}")
        except Exception as e:
            logger.error(f"Failed to connect to CSW at {self.url}: {e}")
            raise

    def get_records(self, query: str | None = None, max_records: int = 10) -> Iterator[InspireRecord]:
        """
        Retrieve records from the CSW.
        
        Args:
            query: Optional CQL query string (not fully implemented yet).
            max_records: Maximum number of records to retrieve.
        
        Yields:
            InspireRecord objects.
        """
        if not self.csw:
            self.connect()
        
        # Simple implementation: get all records (paged) up to max_records
        # For GDI-DE, we might need specific constraints to get INSPIRE data
        # outputschema="http://www.isotc211.org/2005/gmd" is standard for ISO 19139
        
        start_position = 0
        records_yielded = 0
        
        while records_yielded < max_records:
            batch_size = min(10, max_records - records_yielded)
            if batch_size <= 0:
                break
                
            self.csw.getrecords2(
                maxrecords=batch_size,
                startposition=start_position,
                esn='full',
                outputschema='http://www.isotc211.org/2005/gmd'
            )
            
            if not self.csw.records:
                break
                
            for uuid, record in self.csw.records.items():
                if records_yielded >= max_records:
                    break
                
                if isinstance(record, MD_Metadata):
                    yield self._parse_iso_record(record)
                    records_yielded += 1
            
            start_position += len(self.csw.records)
            if start_position >= self.csw.results['matches']:
                break

    def _parse_iso_record(self, iso: MD_Metadata) -> InspireRecord:
        """Parse an OWSLib MD_Metadata object into an InspireRecord."""
        
        # Extract basic fields
        identifier = iso.identifier
        # Title can be None in OWSLib if missing
        title = iso.identification.title if iso.identification and iso.identification.title else "Untitled"
        abstract = iso.identification.abstract if iso.identification else None
        date_stamp = iso.datestamp
        
        # Keywords
        keywords = []
        if iso.identification and iso.identification.keywords:
            for kw_list in iso.identification.keywords:
                keywords.extend(kw_list.keywords)
        
        # Topic Categories
        topics = iso.identification.topiccategory if iso.identification else []
        
        # Contacts
        contacts = []
        # Metadata contact
        if iso.contact:
            for c in iso.contact:
                contacts.append({
                    "name": c.name,
                    "organization": c.organization,
                    "email": c.email,
                    "role": c.role,
                    "type": "metadata"
                })
        # Resource contact
        if iso.identification and iso.identification.contact:
            for c in iso.identification.contact:
                contacts.append({
                    "name": c.name,
                    "organization": c.organization,
                    "email": c.email,
                    "role": c.role,
                    "type": "resource"
                })

        # Lineage
        lineage = None
        if iso.dataquality and iso.dataquality.lineage:
            lineage = iso.dataquality.lineage.statement

        # Spatial Extent (Bounding Box)
        spatial_extent = None
        if iso.identification and iso.identification.bbox:
             # OWSLib bbox: minx, miny, maxx, maxy
             bbox = iso.identification.bbox
             if bbox:
                 spatial_extent = [bbox.minx, bbox.miny, bbox.maxx, bbox.maxy]

        # Temporal Extent
        temporal_extent = None
        if iso.identification and iso.identification.temporalextent_start:
             start = iso.identification.temporalextent_start
             end = iso.identification.temporalextent_end
             temporal_extent = (start, end)

        # Constraints
        constraints = []
        if iso.identification and iso.identification.resourceconstraints:
            for c in iso.identification.resourceconstraints:
                # OWSLib might have different structure for constraints
                # Checking generic constraint text
                if hasattr(c, 'use_limitation') and c.use_limitation:
                    constraints.extend(c.use_limitation)
        
        return InspireRecord(
            identifier=identifier,
            title=title,
            abstract=abstract,
            date_stamp=date_stamp,
            keywords=keywords,
            topic_categories=topics,
            contacts=contacts,
            lineage=lineage,
            spatial_extent=spatial_extent,
            temporal_extent=temporal_extent,
            constraints=constraints
        )

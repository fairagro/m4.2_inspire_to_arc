"""Comprehensive unit tests for the Inspire Harvester."""

from typing import Iterator
from unittest.mock import MagicMock, patch
import pytest
from owslib.iso import MD_Metadata  # type: ignore

from middleware.inspire_to_arc.harvester import CSWClient, InspireRecord, Contact

@pytest.fixture
def mock_csw_cls() -> Iterator[MagicMock]:
    with patch("middleware.inspire_to_arc.harvester.CatalogueServiceWeb") as mock:
        yield mock

@pytest.fixture
def mock_iso_record() -> MagicMock:
    """Create a mock ISO record with all fields populated."""
    record = MagicMock(spec=MD_Metadata)
    record.identifier = "uuid-123"
    record.datestamp = "2023-01-01"
    
    # Identification
    ident = MagicMock()
    ident.title = "Test Title"
    ident.abstract = "Test Abstract"
    ident.keywords = ["keyword1", "keyword2"]
    ident.topiccategory = ["biota"]
    ident.language = "eng"
    ident.status = "completed"
    
    # Contacts
    contact = MagicMock()
    contact.name = "Test Person"
    contact.organization = "Test Org"
    contact.email = "test@example.com"
    contact.role = "author"
    ident.contact = [contact]
    record.contact = []  # Metadata contacts
    
    # Spatial
    bbox = MagicMock()
    bbox.minx = "10.0"
    bbox.miny = "48.0"
    bbox.maxx = "11.0"
    bbox.maxy = "49.0"
    ident.bbox = bbox
    
    # Temporal
    ident.temporalextent_start = "2020-01-01"
    ident.temporalextent_end = "2020-12-31"
    
    record.identification = ident
    
    # Data Quality / Lineage
    dq = MagicMock()
    lineage = MagicMock()
    lineage.statement = "Test Lineage"
    dq.lineage = lineage
    record.dataquality = dq
    
    # Distribution
    dist = MagicMock()
    fmt = MagicMock()
    fmt.format = "CSV"
    # Explicitly set optional fields to None to avoid MagicMock leaking
    dist.version = None
    dist.specification = None
    dist.format_url = None
    dist.version_url = None
    dist.specification_url = None
    dist.online = []
    
    dist.format = fmt.format # Fix: assign string directly if that's what the code expects, or fix the mock structure
    # Actually, looking at code: dist.format is accessed. 
    # If dist.format is a string in OWSLib, we should set it as string.
    dist.format = "CSV"
    
    record.distribution = dist
    
    return record

def test_csw_client_init() -> None:
    client = CSWClient("http://example.com/csw")
    assert client._url == "http://example.com/csw"  # pylint: disable=protected-access
    assert client._timeout == 30  # pylint: disable=protected-access

def test_csw_client_connect(mock_csw_cls: MagicMock) -> None:
    client = CSWClient("http://example.com/csw")
    client.connect()
    mock_csw_cls.assert_called_with("http://example.com/csw", timeout=30)

def test_get_records_success(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    # Setup mock
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {"uuid-123": mock_iso_record}
    mock_instance.results = {"matches": 1}
    
    client = CSWClient("http://example.com/csw")
    records = list(client.get_records(max_records=1))
    
    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, InspireRecord)
    assert rec.identifier == "uuid-123"
    assert rec.title == "Test Title"
    assert rec.abstract == "Test Abstract"
    assert rec.keywords == ["keyword1", "keyword2"]
    assert rec.spatial_extent == [10.0, 48.0, 11.0, 49.0]
    assert rec.temporal_extent == ("2020-01-01", "2020-12-31")
    assert rec.lineage == "Test Lineage"

def test_get_records_empty(mock_csw_cls: MagicMock) -> None:
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {}
    mock_instance.results = {"matches": 0}
    
    client = CSWClient("http://example.com/csw")
    records = list(client.get_records())
    assert len(records) == 0

def test_parse_iso_record_minimal(mock_iso_record: MagicMock) -> None:
    """Test parsing a record with minimal fields."""
    # Remove optional fields
    mock_iso_record.identification.abstract = None
    mock_iso_record.identification.keywords = []
    mock_iso_record.identification.bbox = None
    mock_iso_record.identification.temporalextent_start = None
    mock_iso_record.dataquality = None
    mock_iso_record.distribution = None
    
    client = CSWClient("http://dummy")
    rec = client._parse_iso_record(mock_iso_record)  # pylint: disable=protected-access
    
    assert rec.identifier == "uuid-123"
    assert rec.title == "Test Title"
    assert rec.abstract is None
    assert rec.spatial_extent is None
    assert rec.temporal_extent is None
    assert rec.lineage is None

def test_extract_contacts(mock_iso_record: MagicMock) -> None:
    client = CSWClient("http://dummy")
    rec = client._parse_iso_record(mock_iso_record)  # pylint: disable=protected-access
    
    assert len(rec.contacts) == 1
    contact = rec.contacts[0]
    assert contact.name == "Test Person"
    assert contact.organization == "Test Org"
    assert contact.email == "test@example.com"
    assert contact.role == "author"
    assert contact.type == "resource"

def test_extract_spatial_extent_invalid(mock_iso_record: MagicMock) -> None:
    # Set invalid bbox values
    mock_iso_record.identification.bbox.minx = "invalid"
    
    client = CSWClient("http://dummy")
    rec = client._parse_iso_record(mock_iso_record)  # pylint: disable=protected-access
    assert rec.spatial_extent is None

def test_extract_resource_identifiers(mock_iso_record: MagicMock) -> None:
    # Add resource identifiers
    mock_iso_record.identification.uricode = ["10.1234/doi"]
    mock_iso_record.identification.uricodespace = ["DOI"]
    
    client = CSWClient("http://dummy")
    rec = client._parse_iso_record(mock_iso_record)  # pylint: disable=protected-access
    
    assert len(rec.resource_identifiers) == 1
    res_id = rec.resource_identifiers[0]
    assert res_id.code == "10.1234/doi"
    assert res_id.codespace == "DOI"

def test_extract_distribution_formats(mock_iso_record: MagicMock) -> None:
    client = CSWClient("http://dummy")
    rec = client._parse_iso_record(mock_iso_record)  # pylint: disable=protected-access
    
    assert len(rec.distribution_formats) == 1
    fmt = rec.distribution_formats[0]
    assert fmt.name == "CSV"

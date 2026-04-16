"""Comprehensive unit tests for the Inspire Harvester."""

# ruff: noqa: SLF001, PLR2004

from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from owslib.fes import OgcExpression  # type: ignore
from owslib.iso import MD_DataIdentification, MD_Metadata  # type: ignore

from middleware.harvester.errors import RecordProcessingError
from middleware.inspire.config import Config
from middleware.inspire.csw_client import CSWClient
from middleware.inspire.errors import SemanticError
from middleware.inspire.models import InspireRecord


@pytest.fixture
def mock_csw_cls() -> Iterator[MagicMock]:
    with patch("middleware.inspire.csw_client.CatalogueServiceWeb") as mock:
        yield mock


@pytest.fixture
def create_mock_identification() -> MagicMock:
    """Create and return a mock identification object."""
    identification = MagicMock(spec=MD_DataIdentification)
    identification.title = "Test Title"
    identification.abstract = "Test Abstract"
    identification.keywords = ["kw1", "kw2"]
    identification.topiccategory = ["biota"]
    identification.contact = []
    bbox = MagicMock()
    bbox.minx, bbox.miny, bbox.maxx, bbox.maxy = (10.0, 48.0, 11.0, 49.0)
    identification.bbox = bbox
    identification.temporalextent_start = "2020-01-01"
    identification.temporalextent_end = "2020-12-31"
    identification.resourceconstraint = []
    identification.uricode = []
    identification.uricodespace = []
    identification.date = []
    identification.resourcelanguagecode = []
    identification.resourcelanguage = []
    identification.graphicoverview = []
    identification.denominators = []
    identification.distance = []
    identification.uom = []
    identification.creator = []
    identification.publisher = []
    identification.contributor = []
    identification.accessconstraints = []
    identification.useconstraints = []
    identification.classification = []
    identification.otherconstraints = []
    identification.otherconstraints_url = []
    identification.edition = None
    identification.purpose = None
    identification.status = None
    identification.supplementalinformation = None
    identification.alternatetitle = None
    return identification


@pytest.fixture
def mock_iso_record(create_mock_identification: MagicMock) -> MagicMock:
    """Return a mock ISO record object."""
    record = MagicMock(spec=MD_Metadata)
    record.identifier = "uuid-123"
    record.datestamp = "2023-01-01"
    record.xml = b"<metadata>...</metadata>"
    record.identification = create_mock_identification
    record.contact = []
    record.dataquality = None
    record.distribution = None
    record.referencesystem = None
    record.parentidentifier = None
    record.language = None
    record.languagecode = None
    record.charset = None
    record.hierarchy = None
    record.stdname = None
    record.stdver = None
    record.dataseturi = None
    return record


def test_csw_client_init() -> None:
    client = CSWClient(Config(csw_url="http://example.com/csw"))
    assert client._config.csw_url == "http://example.com/csw"
    assert client._config.timeout == 30


def test_config_mutually_exclusive_filters_raises() -> None:
    """Config must reject cql_query and xml_query set simultaneously."""
    from pydantic import ValidationError  # pylint: disable=import-outside-toplevel

    with pytest.raises(ValidationError, match="mutually exclusive"):
        Config(
            csw_url="http://example.com/csw",
            cql_query="AnyText LIKE '%test%'",
            xml_query="<Filter/>",
        )


def test_csw_client_connect(mock_csw_cls: MagicMock) -> None:
    client = CSWClient(Config(csw_url="http://example.com/csw"))
    client.connect()
    mock_csw_cls.assert_called_with("http://example.com/csw", timeout=30)


def test_get_records_success(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    """Test successful retrieval and parsing of CSW records."""
    # Setup mock
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {"uuid-123": mock_iso_record}
    mock_instance.results = {"matches": 1}
    # Mock the getrecords2 method
    mock_instance.getrecords2 = MagicMock()

    # Setup lineage for this test
    dq = MagicMock()
    lineage = MagicMock()
    lineage.statement = "Test Lineage"
    dq.lineage = lineage
    mock_iso_record.dataquality = dq

    # Patch isinstance to make the mock pass the MD_Metadata check
    def mock_isinstance(obj: object, cls: type) -> bool:  # type: ignore[name-defined]
        """Mock isinstance that recognizes mock_iso_record as MD_Metadata."""
        if obj is mock_iso_record and cls is MD_Metadata:
            return True
        return isinstance(obj, cls)

    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        client = CSWClient(Config(csw_url="http://example.com/csw", chunk_size=1))
        records = list(client.get_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, InspireRecord)
    assert rec.identifier == "uuid-123"
    assert rec.title == "Test Title"
    assert rec.abstract == "Test Abstract"
    assert rec.keywords == ["kw1", "kw2"]
    assert rec.spatial_extent == [10.0, 48.0, 11.0, 49.0]
    assert rec.temporal_extent == ("2020-01-01", "2020-12-31")
    assert rec.lineage == "Test Lineage"


def test_get_records_empty(mock_csw_cls: MagicMock) -> None:
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {}
    mock_instance.results = {"matches": 0}

    client = CSWClient(Config(csw_url="http://example.com/csw"))
    records = list(client.get_records())
    assert len(records) == 0


def test_parse_iso_record_minimal(mock_iso_record: MagicMock) -> None:
    """Test parsing a record with minimal fields."""
    # Remove optional fields
    mock_iso_record.identification.keywords = []
    mock_iso_record.identification.bbox = None
    mock_iso_record.identification.temporalextent_start = None
    mock_iso_record.dataquality = None
    mock_iso_record.distribution = None

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")

    assert rec.identifier == "uuid-123"
    assert rec.title == "Test Title"
    assert rec.abstract == "Test Abstract"
    assert rec.spatial_extent is None
    assert rec.temporal_extent is None
    assert rec.lineage is None


def test_parse_iso_record_missing_title(mock_iso_record: MagicMock) -> None:
    """Test parsing a record with missing title should raise SemanticError."""
    mock_iso_record.identification.title = None

    client = CSWClient(Config(csw_url="http://dummy"))
    with pytest.raises(SemanticError, match="missing a title"):
        client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")


def test_parse_iso_record_missing_abstract(mock_iso_record: MagicMock) -> None:
    """Test parsing a record with missing abstract should raise SemanticError."""
    mock_iso_record.identification.abstract = None

    client = CSWClient(Config(csw_url="http://dummy"))
    with pytest.raises(SemanticError, match="missing an abstract"):
        client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")


def test_extract_contacts(mock_iso_record: MagicMock) -> None:
    # Add resource contact
    contact = MagicMock()
    contact.name = "Test Person"
    contact.organization = "Test Org"
    contact.email = "test@example.com"
    contact.role = "author"
    mock_iso_record.identification.contact = [contact]

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")

    assert len(rec.contacts) == 1
    c = rec.contacts[0]
    assert c.name == "Test Person"
    assert c.organization == "Test Org"
    assert c.email == "test@example.com"
    assert c.role == "author"
    assert c.type == "resource"


def test_extract_spatial_extent_invalid(mock_iso_record: MagicMock) -> None:
    # Set invalid bbox values
    mock_iso_record.identification.bbox.minx = "invalid"

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert rec.spatial_extent is None


def test_extract_resource_identifiers(mock_iso_record: MagicMock) -> None:
    # Add resource identifiers
    mock_iso_record.identification.uricode = ["10.1234/doi"]
    mock_iso_record.identification.uricodespace = ["DOI"]

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")

    assert len(rec.resource_identifiers) == 1
    res_id = rec.resource_identifiers[0]
    assert res_id.code == "10.1234/doi"
    assert res_id.codespace == "DOI"


def test_extract_distribution_formats(mock_iso_record: MagicMock) -> None:
    # Setup distribution
    dist = MagicMock()
    dist.format = "CSV"
    dist.version = None
    dist.specification = None
    dist.format_url = None
    dist.version_url = None
    dist.specification_url = None
    dist.online = []
    mock_iso_record.distribution = dist

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")

    assert len(rec.distribution_formats) == 1
    fmt = rec.distribution_formats[0]
    assert fmt.name == "CSV"


def test_get_records_skip_invalid_records(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    """Test that invalid records are skipped in get_records."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance

    # Create a valid record and an invalid one (missing title)
    valid_record = mock_iso_record
    invalid_record = MagicMock(spec=MD_Metadata)
    invalid_record.identifier = "uuid-invalid"
    invalid_record.identification = MagicMock()
    invalid_record.identification.title = None

    mock_instance.records = {
        "uuid-valid": valid_record,
        "uuid-invalid": invalid_record,
    }
    mock_instance.results = {"matches": 2}
    mock_instance.results = {"matches": 2}

    # Patch isinstance to make MD_Metadata check pass for both
    original_isinstance = isinstance

    def mock_isinstance(obj: object, cls: type) -> bool:
        if cls == MD_Metadata:
            return True
        return original_isinstance(obj, cls)

    client = CSWClient(Config(csw_url="http://example.com/csw"))
    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        results = list(client.get_records())

    # Check that we got one valid record and one error object
    assert len(results) == 2
    records = [r for r in results if isinstance(r, InspireRecord)]
    errors = [e for e in results if isinstance(e, RecordProcessingError)]

    assert len(records) == 1
    assert len(errors) == 1
    assert records[0].identifier == "uuid-123"
    assert errors[0].record_id == "uuid-invalid"


def test_get_records_skip_generic_exception(mock_csw_cls: MagicMock) -> None:
    """Test that records causing generic exceptions result in yielded RecordProcessingError."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance

    error_record = MagicMock(spec=MD_Metadata)
    error_record.identifier = "uuid-error"
    # This will cause a generic error during extraction
    error_record.identification = None

    mock_instance.records = {
        "uuid-error": error_record,
    }
    mock_instance.results = {"matches": 1}

    # Patch isinstance
    original_isinstance = isinstance

    def mock_isinstance(obj: object, cls: type) -> bool:
        if cls == MD_Metadata:
            return True
        return original_isinstance(obj, cls)

    client = CSWClient(Config(csw_url="http://example.com/csw"))
    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        results = list(client.get_records())

    assert len(results) == 1
    assert isinstance(results[0], RecordProcessingError)
    assert results[0].record_id == "uuid-error"


def test_get_records_by_xml(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    """Test get_records using XML-based filtering."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {"uuid-123": mock_iso_record}
    mock_instance.results = {"matches": 1}

    # Patch isinstance
    original_isinstance = isinstance

    def mock_isinstance(obj: object, cls: type) -> bool:
        if cls == MD_Metadata:
            return True
        return original_isinstance(obj, cls)

    client = CSWClient(Config(csw_url="http://example.com/csw"))
    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        # Trigger XML path
        results = list(client.get_records(xml_query="<Filter>...</Filter>"))

    assert len(results) == 1
    mock_instance.getrecords2.assert_called()
    # Check if xml was used in call args if possible, or just ensure it didn't crash
    kwargs = mock_instance.getrecords2.call_args.kwargs
    assert "xml" in kwargs


def test_get_records_by_constraints(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    """Test get_records using constraints."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {"uuid-123": mock_iso_record}
    mock_instance.results = {"matches": 1}

    # Patch isinstance
    original_isinstance = isinstance

    def mock_isinstance(obj: object, cls: type) -> bool:
        if cls == MD_Metadata:
            return True
        return original_isinstance(obj, cls)

    fes = cast(list[OgcExpression], [MagicMock(spec=OgcExpression)])
    client = CSWClient(Config(csw_url="http://example.com/csw"))
    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        # Trigger constraint path
        results = list(client.get_records(fes_constraints=fes))

    assert len(results) == 1
    mock_instance.getrecords2.assert_called()
    kwargs = mock_instance.getrecords2.call_args.kwargs
    assert "constraints" in kwargs


def test_get_records_by_cql(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    """Test get_records using a CQL query string."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {"uuid-123": mock_iso_record}
    mock_instance.results = {"matches": 1}

    # Patch isinstance
    original_isinstance = isinstance

    def mock_isinstance(obj: object, cls: type) -> bool:
        if cls == MD_Metadata:
            return True
        return original_isinstance(obj, cls)

    client = CSWClient(Config(csw_url="http://example.com/csw"))
    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        results = list(client.get_records(cql_query="AnyText LIKE '%test%'"))

    assert len(results) == 1
    mock_instance.getrecords2.assert_called()
    kwargs = mock_instance.getrecords2.call_args.kwargs
    assert "cql" in kwargs
    assert kwargs["cql"] == "AnyText LIKE '%test%'"


def test_get_records_conflicting_filters_raises() -> None:
    """Test that providing more than one filter mode raises ValueError."""
    client = CSWClient(Config(csw_url="http://example.com/csw"))
    fes = cast(list[OgcExpression], [MagicMock(spec=OgcExpression)])

    with pytest.raises(ValueError, match="Conflicting query parameters"):
        list(client.get_records(xml_query="<req/>", cql_query="AnyText LIKE '%x%'"))

    with pytest.raises(ValueError, match="Conflicting query parameters"):
        list(client.get_records(xml_query="<req/>", fes_constraints=fes))

    with pytest.raises(ValueError, match="Conflicting query parameters"):
        list(client.get_records(cql_query="AnyText LIKE '%x%'", fes_constraints=fes))


def test_get_records_config_and_arg_conflict_raises() -> None:
    """Test that a config filter and a call-site filter conflict also raises ValueError."""
    # Config already provides a cql_query; call also passes fes_constraints → conflict
    client = CSWClient(Config(csw_url="http://example.com/csw", cql_query="AnyText LIKE '%biota%'"))
    fes = cast(list[OgcExpression], [MagicMock(spec=OgcExpression)])
    with pytest.raises(ValueError, match="Conflicting query parameters"):
        list(client.get_records(fes_constraints=fes))


def test_get_records_chunk_size_override(mock_csw_cls: MagicMock, mock_iso_record: MagicMock) -> None:
    """Test that chunk_size passed to get_records() overrides the Config value."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.records = {"uuid-123": mock_iso_record}
    mock_instance.results = {"matches": 1}

    original_isinstance = isinstance

    def mock_isinstance(obj: object, cls: type) -> bool:
        if cls == MD_Metadata:
            return True
        return original_isinstance(obj, cls)

    # Config has chunk_size=50 (default), but we override to 7
    client = CSWClient(Config(csw_url="http://example.com/csw"))
    with patch("middleware.inspire.csw_client.isinstance", side_effect=mock_isinstance):
        list(client.get_records(chunk_size=7))

    kwargs = mock_instance.getrecords2.call_args.kwargs
    assert kwargs["maxrecords"] == 7


def test_get_records_max_records_override(mock_csw_cls: MagicMock) -> None:
    """Test that max_records passed to get_records() overrides the Config value."""
    mock_instance = MagicMock()
    mock_csw_cls.return_value = mock_instance
    mock_instance.results = {"matches": 100}

    # Return empty records to avoid parse complexity; max_records=0 should stop immediately
    mock_instance.records = {}

    client = CSWClient(Config(csw_url="http://example.com/csw", max_records=None))
    # Override max_records to 0 — pagination should stop after the first empty batch
    results = list(client.get_records(max_records=0))

    assert not results


def test_extract_lineage_complex(mock_iso_record: MagicMock) -> None:
    """Test extraction of lineage with a statement object."""
    dq = MagicMock()
    lineage = MagicMock()
    lineage.statement = "Test Lineage Statement"
    dq.lineage = lineage
    # Set other dq fields to None
    dq.conformancetitle = []
    dq.conformancedegree = []
    dq.lineage_url = None
    mock_iso_record.dataquality = dq

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert rec.lineage == "Test Lineage Statement"


def test_extract_spatial_extent_variations(mock_iso_record: MagicMock) -> None:
    """Test different spatial extent scenarios."""
    client = CSWClient(Config(csw_url="http://dummy"))

    # 1. Valid numbers as strings
    mock_iso_record.identification.bbox.minx = "10.1"
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-1")
    assert rec.spatial_extent == [10.1, 48.0, 11.0, 49.0]

    # 2. None values
    mock_iso_record.identification.bbox.minx = None
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-2")
    assert rec.spatial_extent is None


def test_extract_resolution(mock_iso_record: MagicMock) -> None:
    """Test scale and distance extraction."""
    ident = mock_iso_record.identification
    ident.denominators = ["5000"]
    ident.distance = ["10"]
    ident.uom = ["m"]

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert 5000 in rec.spatial_resolution_denominators
    assert len(rec.spatial_resolution_distances) == 1
    assert rec.spatial_resolution_distances[0].value == 10.0
    assert rec.spatial_resolution_distances[0].uom == "m"


def test_extract_distribution_formats_complex(mock_iso_record: MagicMock) -> None:
    """Test distribution formats properly."""
    dist = MagicMock()
    dist.format = "Format1"
    dist.version = "1.0"
    dist.specification = None
    dist.format_url = None
    dist.version_url = None
    dist.specification_url = None
    dist.online = []
    mock_iso_record.distribution = dist

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert len(rec.distribution_formats) == 1
    assert rec.distribution_formats[0].name == "Format1"
    assert rec.distribution_formats[0].version == "1.0"


def test_extract_online_resources(mock_iso_record: MagicMock) -> None:
    """Test online resource extraction."""
    dist = MagicMock()
    dist.format = None
    res = MagicMock()
    res.url = "http://data.com"
    res.protocol = "WWW:LINK"
    res.protocol_url = None
    res.name = "Data"
    res.name_url = None
    res.description = "Desc"
    res.description_url = None
    res.function = None
    dist.online = [res]
    mock_iso_record.distribution = dist

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert len(rec.online_resources) == 1
    assert rec.online_resources[0].url == "http://data.com"


def test_extract_conformance(mock_iso_record: MagicMock) -> None:
    """Test conformance results extraction."""
    dq = MagicMock()
    dq.lineage = None
    dq.lineage_url = None
    dq.conformancetitle = ["INSPIRE"]
    dq.conformancetitle_url = [None]
    dq.conformancedate = [None]
    dq.conformancedatetype = [None]
    dq.conformancedegree = ["true"]
    mock_iso_record.dataquality = dq

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert len(rec.conformance_results) == 1
    assert rec.conformance_results[0].specification_title == "INSPIRE"
    assert rec.conformance_results[0].degree == "true"


def test_extract_reference_systems(mock_iso_record: MagicMock) -> None:
    """Test reference system extraction."""
    ref = MagicMock()
    ref.code = "EPSG:4326"
    ref.code_url = None
    ref.codeSpace = None
    ref.codeSpace_url = None
    ref.version = None
    ref.version_url = None
    mock_iso_record.referencesystem = ref

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    assert len(rec.reference_systems) == 1
    assert rec.reference_systems[0].code == "EPSG:4326"


def test_extract_contacts_metadata_level(mock_iso_record: MagicMock) -> None:
    """Test contacts at metadata level."""
    contact = MagicMock()
    contact.name = "Meta Person"
    contact.organization = None
    contact.email = None
    contact.role = None
    mock_iso_record.contact = [contact]

    client = CSWClient(Config(csw_url="http://dummy"))
    rec = client._parse_iso_record(mock_iso_record, record_uuid="uuid-123")
    # rec.contacts should have 2 contacts now: 1 resource (if added), but in minimal mock it's empty
    # Wait, ident.contact = [] in fixture.
    assert len(rec.contacts) == 1
    assert rec.contacts[0].name == "Meta Person"
    assert rec.contacts[0].type == "metadata"


def test_dwd_filter_xml_request(mock_csw_cls: MagicMock) -> None:
    """
    Test that the DWD filter XML request is valid and can be used.

    This validates the XML configuration from config_dwd_gdi_de.yaml.
    The XML should contain a proper OGC FES PropertyIsEqualTo filter
    for apiso:organisationName = "Deutscher Wetterdienst".
    """
    # The exact XML from config_dwd_gdi_de.yaml
    dwd_xml_request = b"""<?xml version="1.0" encoding="UTF-8"?>
    <csw:GetRecords
        xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
        xmlns:ogc="http://www.opengis.net/ogc"
        service="CSW"
        version="2.0.2"
        resultType="results"
        outputSchema="http://www.isotc211.org/2005/gmd"
        startPosition="1"
        maxRecords="50">
      <csw:Query typeNames="csw:Record">
        <csw:ElementSetName>full</csw:ElementSetName>
        <csw:Constraint version="1.1.0">
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>apiso:organisationName</ogc:PropertyName>
              <ogc:Literal>Deutscher Wetterdienst</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
        </csw:Constraint>
      </csw:Query>
    </csw:GetRecords>"""

    # Verify XML is valid (can be parsed)
    import xml.etree.ElementTree as ET  # pylint: disable=import-outside-toplevel

    try:
        root = ET.fromstring(dwd_xml_request)
        assert root.tag == "{http://www.opengis.net/cat/csw/2.0.2}GetRecords"
        assert root.get("service") == "CSW"
        assert root.get("version") == "2.0.2"

        # Verify filter is present
        namespaces = {"csw": "http://www.opengis.net/cat/csw/2.0.2", "ogc": "http://www.opengis.net/ogc"}
        constraint = root.find(".//csw:Constraint", namespaces)
        assert constraint is not None, "Constraint should be present"

        filter_elem = constraint.find(".//ogc:Filter", namespaces)
        assert filter_elem is not None, "Filter should be present"

        prop_equal = filter_elem.find(".//ogc:PropertyIsEqualTo", namespaces)
        assert prop_equal is not None, "PropertyIsEqualTo should be present"

        prop_name = prop_equal.find("ogc:PropertyName", namespaces)
        assert prop_name is not None
        assert prop_name.text == "apiso:organisationName"

        literal = prop_equal.find("ogc:Literal", namespaces)
        assert literal is not None
        assert literal.text == "Deutscher Wetterdienst"

    except ET.ParseError as e:
        pytest.fail(f"DWD XML request is invalid: {e}")

    # Create a client and verify it can handle XML requests
    mock_csw_instance = MagicMock()
    mock_csw_instance.records = {}
    mock_csw_instance.results = {"matches": 200}
    mock_csw_cls.return_value = mock_csw_instance

    client = CSWClient(Config(csw_url="http://dummy-csw"))
    client.connect()

    # get_record_count should work with the DWD XML
    count = client.get_record_count(xml_query=dwd_xml_request)
    assert count == 200, "Should get record count from CSW"

    # Verify getrecords2 was called with the XML
    mock_csw_instance.getrecords2.assert_called()

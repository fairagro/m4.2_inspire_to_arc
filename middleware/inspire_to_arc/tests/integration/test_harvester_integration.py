"""Integration tests for the INSPIRE harvester with mocked CSW server.

These are true integration tests - they test multiple components (harvester + mapper)
working together, but with all external dependencies (CSW service) mocked.

For system tests against real external services (GDI-DE), see the verification script
in docs/DWD_FILTER_VERIFICATION.md or create a manual integration test script.
"""

# ruff: noqa: SLF001, PLR2004

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from owslib.fes import PropertyIsLike  # type: ignore
from owslib.iso import MD_Metadata  # type: ignore

from middleware.inspire_to_arc.errors import RecordProcessingError
from middleware.inspire_to_arc.harvester import CSWClient, InspireRecord


def _set_attrs(target: MagicMock, attrs: dict[str, Any]) -> None:
    """Populate attributes on a MagicMock from a mapping."""
    for key, value in attrs.items():
        setattr(target, key, value)


def _build_mock_identification() -> MagicMock:
    """Build a minimal mock ISO identification object."""
    ident = MagicMock()
    _set_attrs(
        ident,
        {
            "title": "Test Dataset",
            "abstract": "A test dataset for integration testing",
            "keywords": ["test", "sample"],
            "topiccategory": ["biota"],
            "contact": [],
            "resourceconstraint": [],
            "uricode": [],
            "uricodespace": [],
            "date": [],
            "resourcelanguagecode": [],
            "resourcelanguage": [],
            "graphicoverview": [],
            "denominators": [],
            "distance": [],
            "uom": [],
            "creator": [],
            "publisher": [],
            "contributor": [],
            "accessconstraints": [],
            "useconstraints": [],
            "classification": [],
            "otherconstraints": [],
            "otherconstraints_url": [],
            "alternatetitle": None,
            "edition": None,
            "purpose": None,
            "status": None,
            "supplementalinformation": None,
            "temporalextent_start": None,
            "temporalextent_end": None,
        },
    )
    bbox = MagicMock()
    _set_attrs(bbox, {"minx": 10.0, "miny": 48.0, "maxx": 11.0, "maxy": 49.0})
    ident.bbox = bbox
    return ident


def _build_mock_iso_record() -> MagicMock:
    """Build a minimal mock MD_Metadata object with nested identification."""
    mock_iso_record = MagicMock(spec=MD_Metadata)
    _set_attrs(
        mock_iso_record,
        {
            "identifier": "test-record-001",
            "datestamp": "2026-01-01",
            "parentidentifier": None,
            "language": "de",
            "languagecode": "deu",
            "charset": "utf-8",
            "hierarchy": "dataset",
            "stdname": "ISO 19115",
            "stdver": "2003",
            "dataseturi": "http://example.com/dataset",
            "identification": [_build_mock_identification()],
            "distribution": None,
            "referencesystem": None,
            "contact": [],
            "xml": b"<test>xml</test>",
        },
    )
    mock_iso_record.dataquality = MagicMock()
    mock_iso_record.dataquality.lineage = None
    return mock_iso_record


@pytest.fixture
def mock_csw() -> MagicMock:
    """Create a mock CSW service that returns sample records."""
    mock_csw = MagicMock()

    mock_iso_record = _build_mock_iso_record()
    mock_csw.records = {"test-record-001": mock_iso_record}
    mock_csw.results = {"matches": 1}

    return mock_csw


@pytest.fixture
def csw_client_with_mock(mock_csw: MagicMock) -> CSWClient:
    """Create CSW client with mocked service."""
    with patch("middleware.inspire_to_arc.harvester.CatalogueServiceWeb", return_value=mock_csw):
        client = CSWClient("http://mock-csw.example.com/csw")
        client._csw = mock_csw
        return client


@pytest.mark.integration
def test_harvester_with_mocked_csw(csw_client_with_mock: CSWClient) -> None:
    """Integration test: harvester can fetch and parse mocked CSW records."""
    records = list(csw_client_with_mock.get_records(max_records=1))

    assert len(records) == 1
    assert isinstance(records[0], InspireRecord)
    assert not isinstance(records[0], RecordProcessingError)
    assert records[0].identifier == "test-record-001"
    assert records[0].title == "Test Dataset"
    assert records[0].abstract == "A test dataset for integration testing"


@pytest.mark.integration
def test_xml_request_with_mocked_csw(csw_client_with_mock: CSWClient) -> None:
    """Integration test: XML requests work with mocked CSW."""
    xml_request = b"""<?xml version="1.0" encoding="UTF-8"?>
    <csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                    service="CSW" version="2.0.2">
      <csw:Query typeNames="csw:Record">
        <csw:ElementSetName>full</csw:ElementSetName>
      </csw:Query>
    </csw:GetRecords>"""

    records = list(csw_client_with_mock.get_records(xml_request=xml_request, max_records=1))

    assert len(records) == 1
    assert isinstance(records[0], InspireRecord)
    assert not isinstance(records[0], RecordProcessingError)
    assert records[0].title == "Test Dataset"

    # Verify getrecords2 was called with the XML
    assert csw_client_with_mock._csw is not None
    mock_csw = cast(MagicMock, csw_client_with_mock._csw)
    mock_csw.getrecords2.assert_called()


@pytest.mark.integration
def test_get_records_with_fes_constraints(csw_client_with_mock: CSWClient) -> None:
    """Integration test: FES constraints are passed through and records are parsed."""
    constraints = [PropertyIsLike("AnyText", "*wetter*")]

    records = list(csw_client_with_mock.get_records(constraints=constraints, max_records=1))

    assert len(records) == 1
    assert isinstance(records[0], InspireRecord)
    assert not isinstance(records[0], RecordProcessingError)
    assert records[0].title == "Test Dataset"

    # Verify getrecords2 was called with constraints in paged mode.
    assert csw_client_with_mock._csw is not None
    mock_csw = cast(MagicMock, csw_client_with_mock._csw)
    _, kwargs = mock_csw.getrecords2.call_args
    assert kwargs["constraints"] == constraints


@pytest.mark.integration
def test_record_count_with_mocked_csw(csw_client_with_mock: CSWClient) -> None:
    """Integration test: record counting works with mocked CSW."""
    count = csw_client_with_mock.get_record_count()

    assert count == 1
    assert csw_client_with_mock._csw is not None
    mock_csw = cast(MagicMock, csw_client_with_mock._csw)
    assert mock_csw.getrecords2.called

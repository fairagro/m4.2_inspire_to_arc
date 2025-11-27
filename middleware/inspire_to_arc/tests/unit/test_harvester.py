"""Unit tests for the CSWClient and InspireRecord classes in the inspire_to_arc.harvester module."""

from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from owslib.iso import MD_Metadata  # type: ignore[import-untyped]

from middleware.inspire_to_arc.harvester import CSWClient, InspireRecord


@pytest.fixture
def mock_csw_cls() -> Iterator[MagicMock]:
    with patch("middleware.inspire_to_arc.harvester.CatalogueServiceWeb") as mock:
        yield mock


def test_connect(mock_csw_cls: MagicMock) -> None:
    client = CSWClient("http://example.com/csw")
    client.connect()
    mock_csw_cls.assert_called_with("http://example.com/csw", timeout=30)
    assert client._csw is not None


def test_get_records(mock_csw_cls: MagicMock) -> None:
    # Setup mock CSW
    mock_csw_instance = MagicMock()
    mock_csw_cls.return_value = mock_csw_instance

    # Mock records
    mock_record = MagicMock(spec=MD_Metadata)
    mock_record.identifier = "uuid-123"
    # Configure nested mocks
    mock_identification = MagicMock()
    mock_identification.title = "Test Title"
    mock_identification.abstract = "Test Abstract"
    mock_identification.keywords = []
    mock_identification.topiccategory = ["biota"]
    mock_identification.contact = []
    mock_identification.bbox = None
    mock_identification.temporalextent_start = None
    mock_record.identification = mock_identification

    mock_record.datestamp = "2023-01-01"
    mock_record.contact = []

    mock_dataquality = MagicMock()
    mock_lineage = MagicMock()
    mock_lineage.statement = "Test Lineage"
    mock_dataquality.lineage = mock_lineage
    mock_record.dataquality = mock_dataquality

    mock_csw_instance.records = {"uuid-123": mock_record}
    mock_csw_instance.results = {"matches": 1}

    client = CSWClient("http://example.com/csw")
    records = list(client.get_records(max_records=1))

    assert len(records) == 1
    assert isinstance(records[0], InspireRecord)
    assert records[0].identifier == "uuid-123"
    assert records[0].title == "Test Title"
    assert records[0].lineage == "Test Lineage"

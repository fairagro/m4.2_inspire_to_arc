"""Unit tests for the inspire plugin generator and config modules."""

# ruff: noqa: SLF001, PLR2004

from unittest.mock import MagicMock, patch

import pytest

from middleware.harvester.errors import RecordProcessingError
from middleware.inspire.config import Config
from middleware.inspire.models import InspireRecord
from middleware.inspire.plugin import run_plugin


def test_config_loading() -> None:
    # PluginConfig is a pure data container; instantiate directly
    config = Config(csw_url="https://csw.example.com")
    assert config.csw_url == "https://csw.example.com"


@pytest.mark.asyncio
async def test_run_plugin_success() -> None:
    mock_config = MagicMock(spec=Config)
    mock_config.csw_url = "https://csw.example.com"
    mock_config.cql_query = None
    mock_config.xml_query = None
    mock_config.chunk_size = 10

    mock_record = MagicMock(spec=InspireRecord)
    mock_record.identifier = "rec-1"
    mock_record.hierarchy = "dataset"
    mock_record.title = "Test"

    mock_records = [mock_record]

    with (
        patch("middleware.inspire.plugin.CSWClient") as mock_csw_class,
        patch("middleware.inspire.plugin.InspireMapper") as mock_mapper_class,
    ):
        mock_csw = mock_csw_class.return_value
        mock_csw.get_records.return_value = mock_records
        mock_csw.get_record_url.return_value = "http://url"

        mock_mapper = mock_mapper_class.return_value
        mock_mapper.map_record.return_value = MagicMock()

        # Consume the generator
        results = [arc async for arc in run_plugin(mock_config)]

        assert mock_csw.get_records.called
        assert len(results) == 1


@pytest.mark.asyncio
async def test_run_plugin_with_error() -> None:
    mock_config = MagicMock(spec=Config)
    mock_config.csw_url = "https://csw.example.com"
    mock_config.cql_query = None
    mock_config.xml_query = None
    mock_config.chunk_size = 10

    mock_error = RecordProcessingError("Failed", record_id="err-1")
    mock_records = [mock_error]

    with patch("middleware.inspire.plugin.CSWClient") as mock_csw_class:
        mock_csw = mock_csw_class.return_value
        mock_csw.get_records.return_value = mock_records
        mock_csw.get_record_url.return_value = "http://url"

        results = [item async for item in run_plugin(mock_config)]
        # Should yield the error object explicitly to the orchestrator
        assert len(results) == 1
        assert isinstance(results[0], RecordProcessingError)

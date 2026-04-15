"""Unit tests for the inspire_to_arc plugin generator and config modules."""

# ruff: noqa: SLF001, PLR2004

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from middleware.inspire_to_arc.config import Config
from middleware.inspire_to_arc.errors import RecordProcessingError
from middleware.inspire_to_arc.models import InspireRecord
from middleware.inspire_to_arc.plugin import run_plugin


def test_config_loading(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
csw_url: https://csw.example.com
rdi: test-rdi
""")

    config = Config.from_yaml_file(config_file)
    assert config.csw_url == "https://csw.example.com"
    assert config.rdi == "test-rdi"


@pytest.mark.asyncio
async def test_run_plugin_success() -> None:
    mock_config = MagicMock(spec=Config)
    mock_config.csw_url = "https://csw.example.com"
    mock_config.rdi = "test-rdi"
    mock_config.query = None
    mock_config.xml_request = None

    mock_record = MagicMock(spec=InspireRecord)
    mock_record.identifier = "rec-1"
    mock_record.hierarchy = "dataset"
    mock_record.title = "Test"

    mock_records = [mock_record]

    with (
        patch("middleware.inspire_to_arc.plugin.CSWClient") as mock_csw_class,
        patch("middleware.inspire_to_arc.plugin.InspireMapper") as mock_mapper_class,
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
    mock_config.query = None
    mock_config.xml_request = None

    mock_error = RecordProcessingError("Failed", record_id="err-1")
    mock_records = [mock_error]

    with patch("middleware.inspire_to_arc.plugin.CSWClient") as mock_csw_class:
        mock_csw = mock_csw_class.return_value
        mock_csw.get_records.return_value = mock_records
        mock_csw.get_record_url.return_value = "http://url"

        results = [arc async for arc in run_plugin(mock_config)]
        # Should log error and continue (no exception raised)
        assert len(results) == 0

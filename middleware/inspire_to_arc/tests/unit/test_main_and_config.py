"""
Unit tests for main and config modules in the INSPIRE-to-ARC harvester.

This module includes tests for:
- Configuration loading and validation.
- The main entry point and CLI functionality.
- The run_harvest function, including success and error scenarios.
"""

# ruff: noqa: SLF001, PLR2004

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from middleware.inspire_to_arc.config import Config
from middleware.inspire_to_arc.errors import RecordProcessingError
from middleware.inspire_to_arc.harvester import InspireRecord
from middleware.inspire_to_arc.main import main, run_harvest


def test_config_loading(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
csw_url: https://csw.example.com
rdi: test-rdi
api_client:
  api_url: https://api.example.com
""")

    config = Config.from_yaml_file(config_file)
    assert config.csw_url == "https://csw.example.com"
    assert config.rdi == "test-rdi"
    assert str(config.api_client.api_url).rstrip("/") == "https://api.example.com"


@pytest.mark.asyncio
async def test_run_harvest_success() -> None:
    mock_config = MagicMock(spec=Config)
    mock_config.csw_url = "https://csw.example.com"
    mock_config.rdi = "test-rdi"
    mock_config.query = None
    mock_config.xml_request = None
    mock_config.api_client = MagicMock()

    mock_record = MagicMock(spec=InspireRecord)
    mock_record.identifier = "rec-1"
    mock_record.hierarchy = "dataset"
    mock_record.title = "Test"

    mock_records = [mock_record]

    with (
        patch("middleware.inspire_to_arc.main.CSWClient") as mock_csw_class,
        patch("middleware.inspire_to_arc.main.ApiClient") as mock_api_class,
        patch("middleware.inspire_to_arc.main.InspireMapper") as mock_mapper_class,
    ):
        mock_csw = mock_csw_class.return_value
        mock_csw.get_records.return_value = mock_records
        mock_csw.get_record_url.return_value = "http://url"

        mock_api = mock_api_class.return_value
        mock_api.__aenter__.return_value = mock_api
        mock_api.create_or_update_arc = AsyncMock()
        mock_api.create_or_update_arc.return_value = MagicMock(arc_id="arc-1")

        mock_mapper = mock_mapper_class.return_value
        mock_mapper.map_record.return_value = MagicMock()

        await run_harvest(mock_config)

        assert mock_api.create_or_update_arc.called
        assert mock_csw.get_records.called


@pytest.mark.asyncio
async def test_run_harvest_with_error() -> None:
    mock_config = MagicMock(spec=Config)
    mock_config.csw_url = "https://csw.example.com"
    mock_config.api_client = MagicMock()
    mock_config.query = None
    mock_config.xml_request = None

    mock_error = RecordProcessingError("Failed", record_id="err-1")
    mock_records = [mock_error]

    with (
        patch("middleware.inspire_to_arc.main.CSWClient") as mock_csw_class,
        patch("middleware.inspire_to_arc.main.ApiClient") as mock_api_class,
    ):
        mock_csw = mock_csw_class.return_value
        mock_csw.get_records.return_value = mock_records
        mock_csw.get_record_url.return_value = "http://url"

        mock_api = mock_api_class.return_value
        mock_api.__aenter__.return_value = mock_api

        await run_harvest(mock_config)
        # Should log error and continue (no exception raised)


def test_main_cli(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("csw_url: https://csw.example.com\napi_client: {api_url: 'https://api.example.com'}")

    with (
        patch("sys.argv", ["prog", "-c", str(config_file)]),
        patch("middleware.inspire_to_arc.main.asyncio.run") as mock_run,
        patch("middleware.inspire_to_arc.main.Config.from_yaml_file") as mock_load,
    ):
        mock_run.side_effect = lambda coro: coro.close() if hasattr(coro, "close") else None
        mock_load.return_value = MagicMock(spec=Config)
        main()
        assert mock_run.called


def test_main_cli_load_fail() -> None:
    with patch("sys.argv", ["prog", "-c", "nonexistent.yaml"]), pytest.raises(RuntimeError):
        main()

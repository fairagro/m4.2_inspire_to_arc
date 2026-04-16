"""Unit tests for the Harvester orchestrator main module."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from middleware.harvester.errors import HarvesterError
from middleware.harvester.main import run_orchestrator


def _make_repo(plugin_type: str = "inspire") -> MagicMock:
    repo = MagicMock()
    repo.plugin_type = plugin_type
    repo.plugin_config = MagicMock()
    repo.rdi = f"{plugin_type}-rdi"
    return repo


def _make_mock_client() -> AsyncMock:
    client = AsyncMock()
    client.create_or_update_arc.return_value = MagicMock(arc_id="arc-1")
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_plugin_factory_exception_skips_repo_and_continues() -> None:
    """If plugin_runner() itself raises on call, that repo is skipped and the next is processed."""
    repos = [_make_repo(), _make_repo()]
    mock_config = MagicMock()
    mock_config.repositories = repos
    mock_config.api_client = MagicMock()

    call_count = 0

    def runner(_config: object) -> AsyncGenerator[str, None]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("CSW endpoint unreachable")

        async def _gen() -> AsyncGenerator[str, None]:
            yield "arc-json"

        return _gen()

    mock_client = _make_mock_client()

    with (
        patch("middleware.harvester.main._PLUGIN_RUNNERS", {"inspire": runner}),
        patch("middleware.harvester.main.ApiClient", return_value=mock_client),
        patch("middleware.harvester.main.ARC.from_rocrate_json_string", return_value=MagicMock()),
    ):
        await run_orchestrator(mock_config)

    assert mock_client.create_or_update_arc.call_count == 1


@pytest.mark.asyncio
async def test_plugin_iteration_exception_skips_repo_and_continues() -> None:
    """If the async generator raises mid-iteration, that repo is skipped and the next is processed."""
    repos = [_make_repo(), _make_repo()]
    mock_config = MagicMock()
    mock_config.repositories = repos
    mock_config.api_client = MagicMock()

    call_count = 0

    def runner(_config: object) -> AsyncGenerator[str, None]:
        nonlocal call_count
        call_count += 1

        async def _failing_gen() -> AsyncGenerator[str, None]:
            raise RuntimeError("Network error during iteration")
            yield  # pragma: no cover  # makes this an async generator function

        async def _ok_gen() -> AsyncGenerator[str, None]:
            yield "arc-json"

        return _failing_gen() if call_count == 1 else _ok_gen()

    mock_client = _make_mock_client()

    with (
        patch("middleware.harvester.main._PLUGIN_RUNNERS", {"inspire": runner}),
        patch("middleware.harvester.main.ApiClient", return_value=mock_client),
        patch("middleware.harvester.main.ARC.from_rocrate_json_string", return_value=MagicMock()),
    ):
        await run_orchestrator(mock_config)

    assert mock_client.create_or_update_arc.call_count == 1


@pytest.mark.asyncio
async def test_harvester_error_yields_logged_and_skipped() -> None:
    """HarvesterError items yielded by the generator are logged and skipped, not uploaded."""
    repos = [_make_repo()]
    mock_config = MagicMock()
    mock_config.repositories = repos
    mock_config.api_client = MagicMock()

    async def runner(_config: object) -> AsyncGenerator[str | HarvesterError, None]:
        yield HarvesterError("record failed")
        yield "arc-json"

    mock_client = _make_mock_client()

    with (
        patch("middleware.harvester.main._PLUGIN_RUNNERS", {"inspire": runner}),
        patch("middleware.harvester.main.ApiClient", return_value=mock_client),
        patch("middleware.harvester.main.ARC.from_rocrate_json_string", return_value=MagicMock()),
    ):
        await run_orchestrator(mock_config)

    # Only the valid ARC is uploaded, not the error
    assert mock_client.create_or_update_arc.call_count == 1

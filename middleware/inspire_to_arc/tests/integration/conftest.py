"""Pytest fixtures for integration tests."""

import pytest

from middleware.inspire_to_arc.harvester import CSWClient


@pytest.fixture
def gdi_de_csw_url() -> str:
    """GDI-DE CSW endpoint URL."""
    return "https://gdk.gdi-de.org/gdi-de/srv/eng/csw"


@pytest.fixture
def csw_client(gdi_de_csw_url: str) -> CSWClient:
    """Create a CSW client for integration tests."""
    return CSWClient(gdi_de_csw_url, timeout=30)

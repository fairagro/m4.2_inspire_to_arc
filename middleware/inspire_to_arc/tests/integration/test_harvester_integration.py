"""Integration tests for the INSPIRE harvester against real GDI-DE CSW server."""

import pytest

from middleware.inspire_to_arc.harvester import CSWClient, InspireRecord
from owslib.fes import And, PropertyIsEqualTo, PropertyIsLike

@pytest.mark.integration
def test_connect_to_gdi_de(csw_client: CSWClient) -> None:
    """Test connection to real GDI-DE CSW server."""
    csw_client.connect()
    # Verify connection by getting record count (requires successful connection)
    count = csw_client.get_record_count()
    assert count > 0  # GDI-DE should have records


@pytest.mark.integration
def test_get_records_basic(csw_client: CSWClient) -> None:
    """Test fetching records from real CSW."""
    records = list(csw_client.get_records(max_records=2))

    # Verify we got records
    assert len(records) > 0

    # Verify structure (not content)
    for record in records:
        assert isinstance(record, InspireRecord)
        assert record.identifier  # Has an ID
        assert record.title  # Has a title


@pytest.mark.integration
def test_get_records_with_xml_query(csw_client: CSWClient) -> None:
    """Test XML-based query against real CSW."""
    xml_request = b"""<?xml version="1.0" encoding="UTF-8"?>
    <csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                    service="CSW" version="2.0.2" resultType="results"
                    outputSchema="http://www.isotc211.org/2005/gmd"
                    startPosition="1" maxRecords="2">
      <csw:Query typeNames="csw:Record">
        <csw:ElementSetName>full</csw:ElementSetName>
      </csw:Query>
    </csw:GetRecords>"""

    records = list(csw_client.get_records(xml_request=xml_request))

    assert len(records) > 0
    assert all(isinstance(r, InspireRecord) for r in records)


@pytest.mark.integration
def test_get_records_with_fes_constraints(csw_client: CSWClient) -> None:
    """Test FES constraint-based query against real CSW.
    
    This demonstrates the cleaner FES API vs raw XML.
    """
    # Query for records containing "wetter" (weather)
    constraints = [PropertyIsLike("AnyText", "*wetter*")]
    
    records = list(csw_client.get_records(constraints=constraints, max_records=2))

    assert len(records) > 0
    assert all(isinstance(r, InspireRecord) for r in records)


@pytest.mark.integration
def test_record_count_matches_web_gui(csw_client: CSWClient) -> None:
    """Verify CSW count for specific query is reasonable.

    This query should match the Web GUI:
    https://www.geoportal.de/search.html?q=radar&filter.datenanbieter=Deutscher%20Wetterdienst%20%28DWD%29
    
    As of 2025-12-01, the web GUI shows ~205 results.
    We allow for reasonable variation as data changes over time.
    """


    # Build query using FES - much more readable than raw XML!
    constraints = [
        And(
            [
                PropertyIsLike("AnyText", "*radar*"),
                PropertyIsEqualTo("OrganisationName", "Deutscher Wetterdienst"),
            ]
        )
    ]

    # Get count from GDI-DE CSW
    csw_count = csw_client.get_record_count(constraints=constraints)

    # Reference value from web GUI (as of 2025-12-01: ~205 results)
    # Allow ±20% tolerance for data changes over time
    reference_count = 205
    tolerance_percent = 20
    min_expected = int(reference_count * (1 - tolerance_percent / 100))  # 164
    max_expected = int(reference_count * (1 + tolerance_percent / 100))  # 246

    assert csw_count >= min_expected, (
        f"Count too low: {csw_count} (expected {min_expected}-{max_expected}, reference: {reference_count})"
    )
    assert csw_count <= max_expected, (
        f"Count too high: {csw_count} (expected {min_expected}-{max_expected}, reference: {reference_count})"
    )
    
    # Log the actual count for manual verification if needed
    print(f"✓ CSW returned {csw_count} records (reference: {reference_count}, range: {min_expected}-{max_expected})")

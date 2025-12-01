"""Integration tests for the INSPIRE harvester against real GDI-DE CSW server."""

import pytest

from middleware.inspire_to_arc.harvester import CSWClient, InspireRecord


@pytest.mark.integration
def test_connect_to_gdi_de(csw_client: CSWClient) -> None:
    """Test connection to real GDI-DE CSW server."""
    csw_client.connect()
    assert csw_client._csw is not None  # pylint: disable=protected-access


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
def test_record_count_matches_web_gui(csw_client: CSWClient) -> None:
    """Verify CSW count matches Web GUI for specific query.

    This query should match the Web GUI:
    https://www.geoportal.de/search.html?q=radar&filter.datenanbieter=Deutscher%20Wetterdienst%20%28DWD%29
    """
    xml_request = b"""<?xml version="1.0" encoding="UTF-8"?>
    <csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                    xmlns:ogc="http://www.opengis.net/ogc"
                    service="CSW" version="2.0.2" resultType="results"
                    outputSchema="http://www.isotc211.org/2005/gmd"
                    startPosition="1" maxRecords="1">
      <csw:Query typeNames="csw:Record">
        <csw:ElementSetName>full</csw:ElementSetName>
        <csw:Constraint version="1.1.0">
          <ogc:Filter>
            <ogc:And>
              <ogc:PropertyIsLike wildCard="*" singleChar="?" escapeChar="\\">
                <ogc:PropertyName>AnyText</ogc:PropertyName>
                <ogc:Literal>*radar*</ogc:Literal>
              </ogc:PropertyIsLike>
              <ogc:PropertyIsEqualTo>
                <ogc:PropertyName>OrganisationName</ogc:PropertyName>
                <ogc:Literal>Deutscher Wetterdienst</ogc:Literal>
              </ogc:PropertyIsEqualTo>
            </ogc:And>
          </ogc:Filter>
        </csw:Constraint>
      </csw:Query>
    </csw:GetRecords>"""

    csw_client.connect()
    csw_client._csw.getrecords2(xml=xml_request)  # pylint: disable=protected-access

    # Get total matches from CSW
    csw_count = csw_client._csw.results.get("matches", 0)  # pylint: disable=protected-access

    # Expected count from Web GUI (update this manually after checking the GUI)
    # Note: This is a reference value that may need periodic updates
    expected_count_min = 100  # Set a minimum threshold
    expected_count_max = 200  # Set a maximum threshold

    assert csw_count >= expected_count_min, f"Too few records: {csw_count}"
    assert csw_count <= expected_count_max, f"Too many records: {csw_count}"

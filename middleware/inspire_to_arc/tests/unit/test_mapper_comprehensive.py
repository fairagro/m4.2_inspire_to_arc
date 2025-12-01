"""Comprehensive unit tests for the Inspire Mapper."""

import pytest
from arctrl import ARC, ArcAssay, ArcInvestigation, ArcStudy  # type: ignore[import]

from middleware.inspire_to_arc.harvester import Contact, InspireRecord, ResourceIdentifier
from middleware.inspire_to_arc.mapper import InspireMapper


@pytest.fixture
def sample_record() -> InspireRecord:
    """Create a sample InspireRecord for testing."""
    return InspireRecord(  # type: ignore[call-arg]
        identifier="uuid-123",
        title="Test Dataset",
        abstract="A test dataset description",
        date_stamp="2023-10-27",
        keywords=["keyword1", "keyword2"],
        topic_categories=["biota"],
        contacts=[
            Contact(
                name="John Doe",
                organization="Test Org",
                email="john@example.com",
                role="author",
                type="resource",
                address="123 Test St",
                city="Test City",
                country="Test Country",
            )
        ],
        lineage="Processed using algorithm X",
        spatial_extent=[10.0, 48.0, 11.0, 49.0],
        temporal_extent=("2020-01-01", "2020-12-31"),
        constraints=["Public Domain"],
        access_constraints=["Public Domain"],
        resource_identifiers=[
            ResourceIdentifier(code="10.1234/doi", codespace="DOI", url="http://doi.org/10.1234/doi")
        ],
        language="eng",
        metadata_standard_name="ISO 19115",
        metadata_standard_version="2003/Cor.1:2006",
    )


@pytest.fixture
def mapper() -> InspireMapper:
    """Fixture that returns an instance of InspireMapper for testing."""
    return InspireMapper()


def test_map_record_e2e(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test end-to-end mapping from InspireRecord to ARC."""
    arc = mapper.map_record(sample_record)

    assert isinstance(arc, ARC)
    assert arc.Identifier == "uuid-123"
    assert arc.Title == "Test Dataset"
    assert arc.Description == "A test dataset description"

    # Check structure
    assert len(arc.Studies) == 1
    assert len(arc.Assays) == 1

    # Check linkage
    study = arc.Studies[0]
    assay = arc.Assays[0]
    assert assay.Identifier in study.RegisteredAssayIdentifiers


def test_map_investigation(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test mapping to ArcInvestigation."""
    inv = mapper.map_investigation(sample_record)

    assert isinstance(inv, ArcInvestigation)
    assert inv.Identifier == "uuid-123"
    assert inv.Title == "Test Dataset"
    assert inv.SubmissionDate == "2023-10-27"

    # Check Contacts
    assert len(inv.Contacts) == 1
    contact = inv.Contacts[0]
    assert contact.LastName == "Doe"
    assert contact.FirstName == "John"
    assert contact.Affiliation == "Test Org"
    assert contact.Address == "123 Test St, Test City, Test Country"

    # Check Publications (DOI)
    assert len(inv.Publications) == 1
    pub = inv.Publications[0]
    assert pub.DOI == "10.1234/doi"

    # Check Comments (Metadata fields)
    comments = [c.Name for c in inv.Comments]
    assert "Language: eng" in comments
    assert "Metadata Standard: ISO 19115 v2003/Cor.1:2006" in comments
    assert "Access Constraints: Public Domain" in comments


def test_map_study(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test mapping to ArcStudy."""
    study = mapper.map_study(sample_record)

    assert isinstance(study, ArcStudy)
    assert study.Identifier == "uuid-123_study"
    assert study.Title == "Study for: Test Dataset"
    assert study.Description is not None and "Lineage: Processed using algorithm X" in study.Description

    # Check Tables (Protocols)
    table_names = [t.Name for t in study.Tables]
    assert "Spatial Sampling" in table_names
    assert "Data Acquisition" in table_names
    assert "Data Processing" in table_names


def test_map_assay(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test mapping to ArcAssay."""
    assay = mapper.map_assay(sample_record)

    assert isinstance(assay, ArcAssay)
    assert assay.Identifier == "uuid-123_assay"
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.Name == "biota"


def test_map_person(mapper: InspireMapper) -> None:
    """Test mapping of Contact to Person."""
    contact = Contact(
        name="Jane Smith",
        organization="Acme Corp",
        email="jane@acme.com",
        role="principalInvestigator",
        phone="+1-555-0199",
    )

    person = mapper.map_person(contact)

    assert person is not None, "map_person returned None"
    assert person.FirstName == "Jane"
    assert person.LastName == "Smith"
    assert person.Affiliation == "Acme Corp"
    assert person.EMail == "jane@acme.com"
    assert person.Phone == "+1-555-0199"

    # Check Role annotation
    assert len(person.Roles) == 1
    assert person.Roles[0].Name == "principalInvestigator"


def test_spatial_sampling_protocol(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test creation of Spatial Sampling protocol."""
    table = mapper._create_spatial_sampling_protocol(sample_record)  # pylint: disable=protected-access

    assert table is not None
    assert table.Name == "Spatial Sampling"

    # Check Bounding Box column
    headers = [col.Header.ToTerm().Name for col in table.Columns]
    assert "Bounding Box" in headers

    # Check value
    bbox_col = next(col for col in table.Columns if col.Header.ToTerm().Name == "Bounding Box")
    assert bbox_col.Cells[0].AsTerm.Name == "[10.0, 48.0, 11.0, 49.0]"


def test_data_acquisition_protocol(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test creation of Data Acquisition protocol."""
    table = mapper._create_data_acquisition_protocol(sample_record)  # pylint: disable=protected-access

    assert table is not None
    assert table.Name == "Data Acquisition"

    # Check Temporal Extent
    headers = [col.Header.ToTerm().Name for col in table.Columns]
    assert "Temporal Extent" in headers

    # Check value
    temp_col = next(col for col in table.Columns if col.Header.ToTerm().Name == "Temporal Extent")
    assert temp_col.Cells[0].AsTerm.Name == "2020-01-01 to 2020-12-31"

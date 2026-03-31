"""Comprehensive unit tests for the Inspire Mapper."""

# ruff: noqa: SLF001, PLR2004

import os
import tempfile

import pytest
from arctrl import ARC, ArcAssay, ArcInvestigation, ArcStudy, Person  # type: ignore[import]
from arctrl.py.Contract.contract import DTO  # type: ignore[import]
from arctrl.py.ContractIO.contract_io import full_fill_contract_batch_async  # type: ignore[import]
from arctrl.py.fable_modules.fable_library.async_ import run_synchronously  # type: ignore[import]

from middleware.inspire_to_arc.harvester import (
    ConformanceResult,
    Contact,
    DistributionFormat,
    InspireDate,
    InspireRecord,
    OnlineResource,
    ReferenceSystem,
    ResourceIdentifier,
    SpatialResolutionDistance,
)
from middleware.inspire_to_arc.mapper import InspireMapper


@pytest.fixture
def sample_record() -> InspireRecord:
    """Create a sample InspireRecord for testing."""
    return InspireRecord(
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
        creators=[
            Contact(
                name="Jane Doe",
                organization="Test Org",
                email="jane@example.com",
                role="creator",
                type="resource",
            )
        ],
        publishers=[Contact(name="Test Publisher", organization="Test Org")],
        contributors=[Contact(name="Contributor Name", organization="Test Org")],
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
        raw_xml=b"<test/>",
        resource_language=["en"],
        graphic_overviews=["https://example.com/graphic.png"],
        dates=[InspireDate(date="2023-10-27", datetype="creation")],
        spatial_resolution_denominators=[10000],
        spatial_resolution_distances=[SpatialResolutionDistance(value=100.0, uom="m")],
        use_constraints=["No restrictions"],
        classification=["Unclassified"],
        other_constraints=["None"],
        other_constraints_url=["https://example.com/constraints"],
        distribution_formats=[DistributionFormat(name="GeoJSON", version="1.0")],
        online_resources=[OnlineResource(name="Resource", url="https://example.com/resource")],
        conformance_results=[ConformanceResult(specification_title="INSPIRE", degree="true")],
        reference_systems=[ReferenceSystem(code="4326", codespace="EPSG")],
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
    assert len(inv.Contacts) == 4
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
    comment_names = [c.Name for c in inv.Comments]
    assert "Language" in comment_names
    assert "Metadata Standard" in comment_names
    assert "Access Constraints" in comment_names

    lang_comment = next(c for c in inv.Comments if c.Name == "Language")
    assert lang_comment.Value == "eng"


def test_map_study(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test mapping to ArcStudy."""
    study = mapper.map_study(sample_record)

    assert isinstance(study, ArcStudy)
    assert study.Identifier == "test_dataset"
    assert study.Title == "Test Dataset"
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
    assert assay.Identifier == "test_dataset"
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

    assert person is not None
    assert person.FirstName == "Jane"
    assert person.LastName == "Smith"
    assert person.Affiliation == "Acme Corp"
    assert person.EMail == "jane@acme.com"
    assert person.Phone == "+1-555-0199"

    # Check Role annotation
    assert len(person.Roles) == 1
    assert person.Roles[0].Name == "principalInvestigator"


def test_map_person_without_name(mapper: InspireMapper) -> None:
    """Test that map_person returns None when contact has no name."""
    contact = Contact(organization="Acme Corp", email="contact@acme.com", role="pointOfContact")

    person = mapper.map_person(contact)

    assert person is None


def test_spatial_sampling_protocol(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test creation of Spatial Sampling protocol."""
    table = mapper._create_spatial_sampling_protocol(sample_record)

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
    table = mapper._create_data_acquisition_protocol(sample_record)

    assert table is not None
    assert table.Name == "Data Acquisition"

    # Check Temporal Extent
    headers = [col.Header.ToTerm().Name for col in table.Columns]
    assert "Temporal Extent" in headers

    # Check value
    temp_col = next(col for col in table.Columns if col.Header.ToTerm().Name == "Temporal Extent")
    assert temp_col.Cells[0].AsTerm.Name == "2020-01-01 to 2020-12-31"


def test_map_assay_with_table(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    # Add data for the assay table
    sample_record.dataset_uri = "https://data.example.com/api"

    sample_record.online_resources = [OnlineResource(name="Download", url="https://data.example.com/download")]
    sample_record.graphic_overviews = ["https://data.example.com/preview.png"]

    assay = mapper.map_assay(sample_record)

    assert len(assay.Tables) == 1
    table = assay.Tables[0]
    assert table.Name == "Measurement"
    # Headers: Input, Resource Name (Parameter), Output
    assert table.ColumnCount == 3
    assert table.RowCount == 3

    # Check table content
    param_col = table.Columns[1]
    output_col = table.Columns[2]

    assert param_col.Cells[0].AsTerm.Name == "Dataset URI"
    assert output_col.Cells[0].AsData.Name == "https://data.example.com/api"

    assert param_col.Cells[1].AsTerm.Name == "Download"
    assert output_col.Cells[1].AsData.Name == "https://data.example.com/download"

    assert param_col.Cells[2].AsTerm.Name == "Graphic Overview"
    assert output_col.Cells[2].AsData.Name == "https://data.example.com/preview.png"

    # Assay comments should now be empty (moved to table)
    assert len(assay.Comments) == 0


def test_create_spatial_sampling_complex(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    sample_record.reference_systems = [ReferenceSystem(code="4326", codespace="EPSG")]
    sample_record.spatial_resolution_denominators = [5000]
    sample_record.spatial_resolution_distances = [SpatialResolutionDistance(value=10.0, uom="m")]

    table = mapper._create_spatial_sampling_protocol(sample_record)

    assert table is not None
    # Input, BBox, CRS, Scale, Distance, Output
    assert table.ColumnCount == 6


def test_create_data_processing_complex(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    sample_record.conformance_results = [ConformanceResult(specification_title="INSPIRE", degree="true")]
    sample_record.distribution_formats = [DistributionFormat(name="GeoJSON", version="1.0")]
    sample_record.dates = [InspireDate(date="2023-01-01", datetype="publication")]

    table = mapper._create_data_processing_protocol(sample_record)

    assert table is not None
    assert table.Name == "Data Processing"
    # Input, Lineage, Conformance, Format, Processing Date, Output
    assert table.ColumnCount == 6


def test_add_person_comments_branches(mapper: InspireMapper) -> None:
    """Test branches in _add_person_comments (missing fields)."""
    person_obj = Person.create(last_name="Doe")
    contact = Contact(
        name="John Doe",
        position="Manager",
        online_resource_url="http://doe.com",
    )

    mapper._add_person_comments(person_obj, contact)

    names = [c.Name for c in person_obj.Comments]
    assert "Position" in names
    assert "Online Resource" in names


def test_generate_comments_branches(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test branches in _generate_comments."""
    sample_record.alternate_title = "Alt"
    sample_record.purpose = "Purpose"
    sample_record.supplemental_information = "Extra"

    comments = mapper._generate_comments(sample_record)

    names = [c.Name for c in comments]
    assert "Alternate Title" in names
    assert "Purpose" in names
    assert "Supplemental Information" in names


def test_map_record_adds_xml_file(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test that mapping a record with raw_xml adds the iso19115.xml file to the ARC with correct content."""
    sample_record.raw_xml = b"<xml>test content</xml>"
    arc = mapper.map_record(sample_record)

    # Check that the file is in the FileSystem tree
    assert "iso19115.xml" in arc.FileSystem.Tree.ToFilePaths()

    # Verify that we can write the ARC with content
    with tempfile.TemporaryDirectory() as tmpdir:
        # Get all write contracts
        contracts = list(arc.GetWriteContracts())

        # Set the content for the XML file
        xml_contract = next((c for c in contracts if c.Path == "iso19115.xml"), None)
        assert xml_contract is not None
        xml_contract.DTO = DTO(1, sample_record.raw_xml.decode("utf-8"))

        # Write the ARC to the temporary directory
        run_synchronously(full_fill_contract_batch_async(tmpdir, contracts))

        xml_file_path = os.path.join(tmpdir, "iso19115.xml")
        assert os.path.exists(xml_file_path)
        with open(xml_file_path, encoding="utf-8") as f:
            assert f.read() == "<xml>test content</xml>"

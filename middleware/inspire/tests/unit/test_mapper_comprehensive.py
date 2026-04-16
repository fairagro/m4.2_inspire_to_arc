"""Comprehensive unit tests for the Inspire Mapper."""

# ruff: noqa: SLF001, PLR2004

import os
import tempfile
from pathlib import Path

import pytest
from arctrl import ARC, ArcAssay, ArcInvestigation, ArcStudy, OntologyAnnotation, Person  # type: ignore[import]
from arctrl.py.Contract.contract import DTO  # type: ignore[import]
from arctrl.py.ContractIO.contract_io import full_fill_contract_batch_async  # type: ignore[import]
from arctrl.py.fable_modules.fable_library.async_ import run_synchronously  # type: ignore[import]

from middleware.inspire.mapper import InspireMapper
from middleware.inspire.models import (
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


def _create_minimal_record(
    **kwargs: list
    | str
    | None
    | list[Contact]
    | list[ResourceIdentifier]
    | list[InspireDate]
    | list[DistributionFormat]
    | list[OnlineResource]
    | list[ConformanceResult]
    | list[ReferenceSystem]
    | list[float]
    | list[SpatialResolutionDistance]
    | tuple[str | None, str | None]
    | bytes,
) -> InspireRecord:
    """Create a minimal InspireRecord with default values for all required fields."""
    defaults: dict = {
        "identifier": "test",
        "title": "Test",
        "abstract": "Test abstract",
        "keywords": [],
        "topic_categories": [],
        "contacts": [],
        "constraints": [],
        "resource_identifiers": [],
        "resource_language": [],
        "graphic_overviews": [],
        "dates": [],
        "spatial_resolution_denominators": [],
        "spatial_resolution_distances": [],
        "creators": [],
        "publishers": [],
        "contributors": [],
        "access_constraints": [],
        "use_constraints": [],
        "classification": [],
        "other_constraints": [],
        "other_constraints_url": [],
        "distribution_formats": [],
        "online_resources": [],
        "conformance_results": [],
        "reference_systems": [],
    }
    # Update defaults with provided kwargs
    defaults.update(kwargs)
    return InspireRecord(**defaults)


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
    assert assay.MeasurementType.Name == "Biological Measurement"
    assert assay.MeasurementType.TermAccessionNumber == "http://purl.obolibrary.org/obo/NCIT_C19026"
    assert assay.MeasurementType.TermSourceREF == "NCIT"


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
    # Columns: Input, Output[URI], Comment[Online Resource], Comment[Online Resource Name],
    # Comment[Graphic Overview] — protocol/description/function omitted (all empty)
    assert table.ColumnCount == 5
    assert table.RowCount == 1

    # Output[URI] = dataSetURI (preferred over online resource)
    output_col = table.Columns[1]
    assert output_col.Cells[0].AsFreeText == "https://data.example.com/api"

    # Comment[Online Resource] = URL
    online_url_col = next(col for col in table.Columns if str(col.Header) == "Comment [Online Resource]")
    assert online_url_col.Cells[0].AsFreeText == "https://data.example.com/download"

    online_name_col = next(col for col in table.Columns if str(col.Header) == "Comment [Online Resource Name]")
    assert online_name_col.Cells[0].AsFreeText == "Download"

    graphic_col = next(col for col in table.Columns if str(col.Header) == "Comment [Graphic Overview]")
    assert graphic_col.Cells[0].AsFreeText == "https://data.example.com/preview.png"

    # Assay-level Comments must NOT contain resource URLs (they live in the table)
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


def test_add_role_with_ontology_mapping(mapper: InspireMapper) -> None:
    """Test that roles are mapped to proper ontology annotations."""
    # Test known role with ontology mapping
    contact = Contact(role="author", name="John Doe")
    person = mapper.map_person(contact)

    assert person is not None
    assert len(person.Roles) == 1
    role_annotation = person.Roles[0]
    assert role_annotation.Name == "Author"
    assert role_annotation.TermAccessionNumber == "http://purl.obolibrary.org/obo/NCIT_C70909"
    assert role_annotation.TermSourceREF == "NCIT"

    # Test another known role
    contact = Contact(role="publisher", name="Jane Smith")
    person = mapper.map_person(contact)

    assert person is not None
    assert len(person.Roles) == 1
    role_annotation = person.Roles[0]
    assert role_annotation.Name == "Publisher"
    assert role_annotation.TermAccessionNumber == "http://purl.obolibrary.org/obo/NCIT_C70908"
    assert role_annotation.TermSourceREF == "NCIT"

    # Test unknown role (fallback)
    contact = Contact(role="unknownRole", name="Empty Role")
    person = mapper.map_person(contact)

    assert person is not None
    assert len(person.Roles) == 1
    assert person.Roles[0].Name == "unknownRole"
    assert person.Roles[0].TermAccessionNumber is None
    assert person.Roles[0].TermSourceREF is None

    # Test empty role
    contact = Contact(role=None, name="No Role")
    person = mapper.map_person(contact)
    assert person is not None
    assert len(person.Roles) == 0


def test_hierarchy_level_handling(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test hierarchy level handling in comment generation and protocol creation."""
    # Test standard dataset (no comment, with spatial protocol)
    sample_record.hierarchy = "dataset"
    comments = mapper._generate_comments(sample_record)
    assert not any(c.Name == "Hierarchy Level" for c in comments)

    spatial_protocol = mapper._create_spatial_sampling_protocol(sample_record)
    assert spatial_protocol is not None

    # Test nonGeographicDataset (no comment, no spatial protocol)
    sample_record.hierarchy = "nonGeographicDataset"
    comments = mapper._generate_comments(sample_record)
    assert not any(c.Name == "Hierarchy Level" for c in comments)

    spatial_protocol = mapper._create_spatial_sampling_protocol(sample_record)
    assert spatial_protocol is None

    # Test series (comment, with spatial protocol)
    sample_record.hierarchy = "series"
    comments = mapper._generate_comments(sample_record)
    hierarchy_comments = [c for c in comments if c.Name == "Hierarchy Level"]
    assert len(hierarchy_comments) == 1
    assert hierarchy_comments[0].Value is not None and "series" in hierarchy_comments[0].Value

    spatial_protocol = mapper._create_spatial_sampling_protocol(sample_record)
    assert spatial_protocol is not None

    # Test tile (comment, with spatial protocol)
    sample_record.hierarchy = "tile"
    comments = mapper._generate_comments(sample_record)
    hierarchy_comments = [c for c in comments if c.Name == "Hierarchy Level"]
    assert len(hierarchy_comments) == 1
    assert hierarchy_comments[0].Value is not None and "tile" in hierarchy_comments[0].Value

    # Test service (comment, with spatial protocol)
    sample_record.hierarchy = "service"
    comments = mapper._generate_comments(sample_record)
    hierarchy_comments = [c for c in comments if c.Name == "Hierarchy Level"]
    assert len(hierarchy_comments) == 1
    assert hierarchy_comments[0].Value is not None and "service" in hierarchy_comments[0].Value


def test_add_ontology_sources(mapper: InspireMapper) -> None:
    """Test that ontology sources are properly added to investigation."""
    record = _create_minimal_record(
        metadata_standard_name="ISO 19115",
        metadata_standard_version="2003",
    )

    inv = mapper.map_investigation(record)

    # Check that metadata standard is added
    metadata_sources = [osr for osr in inv.OntologySourceReferences if osr.Name == "ISO 19115"]
    assert len(metadata_sources) == 1

    # Check that common ontologies are added
    common_ontologies = ["NCIT", "GEMET", "EDAM", "ISO"]
    for ontology in common_ontologies:
        sources = [osr for osr in inv.OntologySourceReferences if osr.Name == ontology]
        assert len(sources) == 1, f"Missing ontology source: {ontology}"


def test_dataset_uri_and_lineage_url_mapping(mapper: InspireMapper, sample_record: InspireRecord) -> None:
    """Test dataset URI and lineage URL mapping in assay table and data processing protocol."""
    # Test dataset URI in assay table — single row, Output[URI] column
    sample_record.dataset_uri = "https://example.com/dataset"
    sample_record.online_resources = []
    sample_record.graphic_overviews = []
    assay = mapper.map_assay(sample_record)

    assert len(assay.Tables) == 1
    assay_table = assay.Tables[0]
    # Only Input + Output[URI] — no online resources or overviews in this record
    assert assay_table.ColumnCount == 2

    output_col = assay_table.Columns[1]  # Output [URI]
    assert output_col.Cells[0].AsFreeText == "https://example.com/dataset"

    # Test lineage URL in data processing protocol
    sample_record.lineage_url = "https://example.com/lineage"
    study = mapper.map_study(sample_record)

    processing_protocols = [t for t in study.Tables if t.Name == "Data Processing"]
    assert len(processing_protocols) == 1

    protocol = processing_protocols[0]
    lineage_url_params = [col for col in protocol.Columns if col.Header.ToTerm().Name == "Lineage Documentation URL"]

    assert len(lineage_url_params) == 1
    assert lineage_url_params[0].Cells[0].AsTerm.Name == "https://example.com/lineage"


def test_to_identifier_slug(mapper: InspireMapper) -> None:
    """Test conversion of titles to identifier slugs."""
    test_cases = [
        ("Test Dataset", "test_dataset"),
        ("Dataset with Spaces", "dataset_with_spaces"),
        ("Dataset-with-dashes", "dataset_with_dashes"),
        ("Dataset_with_underscores", "dataset_with_underscores"),
        ("Dataset with numbers 123", "dataset_with_numbers_123"),
        ("Dataset with special chars!@#", "dataset_with_special_chars"),
        ("", "untitled"),
        ("http://example.com/dataset", "http_example_com_dataset"),  # URL should be converted
        ("dataset/with/slashes", "dataset_with_slashes"),  # Slashes should be converted
    ]

    for title, expected in test_cases:
        result = mapper._to_identifier_slug(title)
        assert result == expected
        assert len(result) <= 80  # Should be truncated to 80 chars


def test_split_name(mapper: InspireMapper) -> None:
    """Test splitting of full names into first and last name."""
    test_cases = [
        ("John Doe", ("John", "Doe")),
        ("Doe, John", ("Doe,", "John")),  # Handle comma format - current implementation doesn't handle this
        ("Jane", ("", "Jane")),  # Single name
        ("", ("", "")),  # Empty name
        ("Dr. John Michael Doe", ("Dr. John Michael", "Doe")),  # Multiple middle names (current implementation)
    ]

    for full_name, expected in test_cases:
        first, last = mapper._split_name(full_name)
        assert (first, last) == expected


def test_format_address(mapper: InspireMapper) -> None:
    """Test formatting of contact address components."""
    contact = Contact(
        name="Test", address="123 Main St", city="Berlin", region="Berlin", postcode="10115", country="Germany"
    )

    address = mapper._format_address(contact)
    assert address == "123 Main St, Berlin, Berlin, 10115, Germany"

    # Test missing components
    contact = Contact(name="Test", address="123 Main St")
    address = mapper._format_address(contact)
    assert address == "123 Main St"

    # Test empty contact
    contact = Contact(name="Test")
    address = mapper._format_address(contact)
    assert address is None


def test_add_person_comments(mapper: InspireMapper) -> None:
    """Test adding comments to person from contact information."""
    person = Person.create(last_name="Doe", first_name="John")
    contact = Contact(
        name="John Doe",
        position="Researcher",
        online_resource_url="https://orcid.org/0000-0000-0000-0000",
        online_resource_name="ORCID",
    )

    mapper._add_person_comments(person, contact)

    assert len(person.Comments) == 2
    comment_names = [c.Name for c in person.Comments]
    assert "Position" in comment_names
    assert "ORCID" in comment_names

    # Test with missing fields
    person = Person.create(last_name="Doe")
    contact = Contact(name="John Doe")
    mapper._add_person_comments(person, contact)
    assert len(person.Comments) == 0


def test_add_contacts(mapper: InspireMapper) -> None:
    """Test adding multiple contacts to investigation."""
    record = _create_minimal_record(
        contacts=[Contact(name="Contact 1", role="author")],
        creators=[Contact(name="Creator 1", role="creator")],
        publishers=[Contact(name="Publisher 1", role="publisher")],
        contributors=[Contact(name="Contributor 1", role="contributor")],
    )

    inv = ArcInvestigation.create(identifier="test", title="Test")
    mapper._add_contacts(inv, record)

    assert len(inv.Contacts) == 4

    # Check that roles are properly mapped
    roles = [role.Name for contact in inv.Contacts for role in contact.Roles]
    assert "Author" in roles
    # Note: creator, publisher, contributor roles are not mapped to ontology terms in current implementation
    assert "creator" in roles
    assert "Publisher" in roles
    assert "contributor" in roles


def test_add_publications(mapper: InspireMapper) -> None:
    """Test adding publications from resource identifiers."""
    # Create investigation with author contacts
    inv = ArcInvestigation.create(identifier="test", title="Test")
    author = Person.create(last_name="Doe", first_name="John")
    author.Roles.append(OntologyAnnotation(name="Author"))
    inv.Contacts.append(author)

    record = _create_minimal_record(
        title="Test Dataset",
        resource_identifiers=[
            ResourceIdentifier(code="10.1234/doi", codespace="DOI"),
            ResourceIdentifier(code="ISBN:123456789", codespace="ISBN"),
            ResourceIdentifier(code="not-a-doi", codespace="OTHER"),
        ],
    )

    mapper._add_publications(inv, record)

    # Current implementation creates publications for all identifiers
    assert len(inv.Publications) == 3

    # Check DOI publication
    doi_pub = next(p for p in inv.Publications if p.DOI == "10.1234/doi")
    assert doi_pub.Title == "Test Dataset"
    # Note: Authors field is not set in current implementation
    assert doi_pub.Authors is None

    # Check ISBN publication
    isbn_pub = next(p for p in inv.Publications if p.DOI == "ISBN:123456789")
    assert isbn_pub.Title == "Test Dataset"

    # Check OTHER publication
    other_pub = next(p for p in inv.Publications if p.DOI == "not-a-doi")
    assert other_pub.Title == "Test Dataset"


def test_generate_comments(mapper: InspireMapper) -> None:
    """Test generation of investigation comments from record fields."""
    record = _create_minimal_record(
        parent_identifier="parent-123",
        language="eng",
        edition="1.0",
        status="completed",
        alternate_title="Alternative Title",
        purpose="Test purpose",
        supplemental_information="Extra info",
        hierarchy="series",
    )

    comments = mapper._generate_comments(record)

    comment_names = [c.Name for c in comments]
    assert "Parent Identifier" in comment_names
    assert "Language" in comment_names
    assert "Edition" in comment_names
    assert "Status" in comment_names
    assert "Alternate Title" in comment_names
    assert "Purpose" in comment_names
    assert "Supplemental Information" in comment_names
    assert "Hierarchy Level" in comment_names


def test_add_constraint_comments(mapper: InspireMapper) -> None:
    """Test adding constraint-related comments."""
    record = _create_minimal_record(
        access_constraints=["restricted"],
        use_constraints=["license"],
        classification=["confidential"],
        other_constraints=["None"],
        other_constraints_url=["https://example.com/constraints"],
    )

    comments: list = []
    mapper._add_constraint_comments(comments, record)

    assert len(comments) == 5
    comment_names = [c.Name for c in comments]
    assert "Access Constraints" in comment_names
    assert "Use Constraints" in comment_names
    assert "Classification" in comment_names
    assert "Other Constraints" in comment_names
    assert "Other Constraints URLs" in comment_names


def test_measurement_type_ontology_mapping(mapper: InspireMapper) -> None:
    """Test topic category to measurement type ontology mapping."""
    # Test known topic categories
    test_cases = [
        ("biota", "Biological Measurement", "http://purl.obolibrary.org/obo/NCIT_C19026", "NCIT"),
        ("farming", "Agricultural Measurement", "http://purl.obolibrary.org/obo/AGRO_00000001", "AGRO"),
        ("oceans", "Oceanographic Measurement", "http://purl.obolibrary.org/obo/ENVO_00000015", "ENVO"),
        (
            "climatologyMeteorologyAtmosphere",
            "Atmospheric Measurement",
            "http://purl.obolibrary.org/obo/ENVO_01000818",
            "ENVO",
        ),
        ("environment", "Environmental Measurement", "http://purl.obolibrary.org/obo/ENVO_01000819", "ENVO"),
    ]

    for topic, expected_name, expected_tan, expected_tsr in test_cases:
        record = _create_minimal_record(topic_categories=[topic])

        measurement_type = mapper._get_measurement_type(record)
        assert measurement_type.Name == expected_name
        assert measurement_type.TermAccessionNumber == expected_tan
        assert measurement_type.TermSourceREF == expected_tsr

    # Test unknown topic category: name only, no TAN/TSR
    record = _create_minimal_record(topic_categories=["unknownTopic"])

    measurement_type = mapper._get_measurement_type(record)
    assert measurement_type.Name == "unknownTopic"
    assert measurement_type.TermAccessionNumber is None
    assert measurement_type.TermSourceREF is None

    # Test empty topic categories
    record = _create_minimal_record(topic_categories=[])

    measurement_type = mapper._get_measurement_type(record)
    assert measurement_type.Name == "Spatial Data Acquisition"
    assert measurement_type.TermAccessionNumber == "http://purl.obolibrary.org/obo/NCIT_C19026"
    assert measurement_type.TermSourceREF == "NCIT"


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


# ---------------------------------------------------------------------------
# ARC directory structure tests
# ---------------------------------------------------------------------------

_ALLOWED_TOP_LEVEL_ARC_DIRS = {"studies", "assays", "workflows", "runs", ".arc"}


def _collect_dir_names(root: str) -> set[str]:
    """Return the names (not paths) of every directory under *root*."""
    names: set[str] = set()
    for _dirpath, dirnames, _ in os.walk(root):
        for d in dirnames:
            names.add(d)
    return names


def test_arc_write_no_url_directories(mapper: InspireMapper, sample_record: InspireRecord, tmp_path: Path) -> None:
    """Written ARC must not contain any URL-based subdirectories.

    Before the https:-directory fix, arctrl's WriteAsync would interpret a
    URL stored as an IOType.data() ``@id`` as a filesystem path and create
    directories such as ``https:/``, ``example.com``, etc.
    """
    sample_record.dataset_uri = "https://data.example.com/dataset"
    sample_record.online_resources = [
        OnlineResource(url="https://example.com/download/resource", name="Download"),
    ]
    sample_record.graphic_overviews = ["https://example.com/thumb.png"]

    arc = mapper.map_record(sample_record)
    contracts = list(arc.GetWriteContracts())
    run_synchronously(full_fill_contract_batch_async(str(tmp_path), contracts))

    all_dir_names = _collect_dir_names(str(tmp_path))

    for d in all_dir_names:
        assert not d.startswith("https:"), f"URL directory created on disk: {d!r}"
        assert not d.startswith("http:"), f"URL directory created on disk: {d!r}"

    top_level_dirs = {p.name for p in tmp_path.iterdir() if p.is_dir()}
    unexpected = top_level_dirs - _ALLOWED_TOP_LEVEL_ARC_DIRS
    assert not unexpected, f"Unexpected top-level directories in written ARC: {unexpected}"


def test_arc_write_expected_top_level_structure(
    mapper: InspireMapper, sample_record: InspireRecord, tmp_path: Path
) -> None:
    """Written ARC must contain the standard top-level ARC directories."""
    arc = mapper.map_record(sample_record)
    contracts = list(arc.GetWriteContracts())
    run_synchronously(full_fill_contract_batch_async(str(tmp_path), contracts))

    top_level_dirs = {p.name for p in tmp_path.iterdir() if p.is_dir()}
    assert "studies" in top_level_dirs, "ARC is missing 'studies' directory"
    assert "assays" in top_level_dirs, "ARC is missing 'assays' directory"


def test_arc_write_no_url_dirs_multiple_resources(
    mapper: InspireMapper, sample_record: InspireRecord, tmp_path: Path
) -> None:
    """URL directories must not appear even with multiple online resources and overviews."""
    sample_record.dataset_uri = "https://doi.org/10.1234/dataset"
    sample_record.online_resources = [
        OnlineResource(url="https://service.example.org/wms?SERVICE=WMS", name="WMS"),
        OnlineResource(url="ftp://ftp.example.org/data.zip", name="FTP Download"),
        OnlineResource(url="http://example.org/metadata", name="Metadata"),
    ]
    sample_record.graphic_overviews = [
        "https://example.org/thumb1.png",
        "https://example.org/thumb2.png",
    ]

    arc = mapper.map_record(sample_record)
    contracts = list(arc.GetWriteContracts())
    run_synchronously(full_fill_contract_batch_async(str(tmp_path), contracts))

    all_dir_names = _collect_dir_names(str(tmp_path))

    for d in all_dir_names:
        assert not d.startswith("https:"), f"URL directory created: {d!r}"
        assert not d.startswith("http:"), f"URL directory created: {d!r}"
        assert not d.startswith("ftp:"), f"URL directory created: {d!r}"
        assert "example.org" not in d, f"Domain directory created: {d!r}"
        assert "doi.org" not in d, f"Domain directory created: {d!r}"

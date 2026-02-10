"""Unit tests for the mapper module."""

import datetime
from typing import Any

from arctrl import ArcAssay, ArcInvestigation, ArcStudy, Person, Publication  # type: ignore[import-untyped]

from middleware.sql_to_arc.mapper import map_assay, map_contact, map_investigation, map_publication, map_study


def test_map_investigation() -> None:
    """Test mapping of investigation data."""
    now = datetime.datetime.now()
    row: dict[str, Any] = {
        "id": 123,
        "title": "Test Investigation",
        "description": "Test Description",
        "submission_time": now,
        "release_time": now,
    }

    arc = map_investigation(row)

    assert isinstance(arc, ArcInvestigation)
    assert arc.Identifier == "123"
    assert arc.Title == "Test Investigation"
    assert arc.Description == "Test Description"
    assert arc.SubmissionDate == now.isoformat()
    assert arc.PublicReleaseDate == now.isoformat()


def test_map_investigation_defaults() -> None:
    """Test mapping of investigation data with missing optional fields."""
    row: dict[str, Any] = {
        "id": 456,
    }

    arc = map_investigation(row)

    assert arc.Identifier == "456"
    assert arc.Title == ""
    assert arc.Description == ""
    assert arc.SubmissionDate is None
    assert arc.PublicReleaseDate is None


def test_map_study() -> None:
    """Test mapping of study data."""
    now = datetime.datetime.now()
    row: dict[str, Any] = {
        "id": 1,
        "title": "Test Study",
        "description": "Study Description",
        "submission_time": now,
        "release_time": now,
    }

    study = map_study(row)

    assert isinstance(study, ArcStudy)
    assert study.Identifier == "1"
    assert study.Title == "Test Study"
    assert study.Description == "Study Description"
    assert study.SubmissionDate == now.isoformat()
    assert study.PublicReleaseDate == now.isoformat()


def test_map_assay() -> None:
    """Test mapping of assay data."""
    row: dict[str, Any] = {
        "id": 1,
        "measurement_type": "Proteomics",
        "technology_type": "Mass Spectrometry",
    }

    assay = map_assay(row)

    assert isinstance(assay, ArcAssay)
    assert assay.Identifier == "1"
    # Note: measurement_type and technology_type are not set yet
    # as they require proper OntologyTerm objects from the database


def test_map_contact() -> None:
    """Test mapping of contact data."""
    row: dict[str, Any] = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "affiliation": "University of Research",
        "roles": (
            '[{"term": "Principal Investigator", "uri": "http://purl.obolibrary.org/obo/MS_1001271", "version": "1.0"}]'
        ),
    }

    person = map_contact(row)

    assert isinstance(person, Person)
    assert person.FirstName == "John"
    assert person.LastName == "Doe"
    assert person.EMail == "john@example.com"
    assert person.Affiliation == "University of Research"
    assert len(person.Roles) == 1
    assert person.Roles[0].Name == "Principal Investigator"


def test_map_publication() -> None:
    """Test mapping of publication data."""
    row: dict[str, Any] = {
        "pub_med_id": "12345678",
        "doi": "10.1000/123",
        "authors": "Author A, Author B",
        "title": "Title of Publication",
    }

    pub = map_publication(row)

    assert isinstance(pub, Publication)
    assert pub.PubMedID == "12345678"
    assert pub.DOI == "10.1000/123"
    assert pub.Authors == "Author A, Author B"
    assert pub.Title == "Title of Publication"

"""Mapper module to convert database rows to ARCTRL objects."""

import json
from datetime import datetime
from typing import Any, cast

from arctrl import (  # type: ignore[import-untyped]
    ArcAssay,
    ArcInvestigation,
    ArcStudy,
    OntologyAnnotation,
    Person,
    Publication,
)


def map_investigation(row: dict[str, Any]) -> ArcInvestigation:
    """Map a database row to an ArcInvestigation object.

    Args:
        row: Dictionary containing investigation data from DB

    Returns:
        ArcInvestigation object
    """
    # Handle potential None values for dates
    submission_date = cast(datetime, row.get("submission_time")).isoformat() if row.get("submission_time") else None
    public_release_date = cast(datetime, row.get("release_time")).isoformat() if row.get("release_time") else None

    # Validate ID (mandatory per DB view spec, but we enforce it here to be safe)
    identifier = str(row["id"]) if row.get("id") is not None else ""
    if not identifier.strip():
        raise ValueError(f"Investigation ID cannot be empty (row={row})")

    return ArcInvestigation.create(
        identifier=identifier,
        title=row.get("title", ""),
        description=row.get("description", ""),
        submission_date=submission_date,
        public_release_date=public_release_date,
    )


def map_study(row: dict[str, Any]) -> ArcStudy:
    """Map a database row to an ArcStudy object.

    Args:
        row: Dictionary containing study data from DB

    Returns:
        ArcStudy object
    """
    # Handle potential None values for dates
    submission_date = cast(datetime, row.get("submission_time")).isoformat() if row.get("submission_time") else None
    public_release_date = cast(datetime, row.get("release_time")).isoformat() if row.get("release_time") else None

    return ArcStudy.create(
        identifier=str(row["id"]),
        title=row.get("title", ""),
        description=row.get("description", ""),
        submission_date=submission_date,
        public_release_date=public_release_date,
    )


def map_assay(row: dict[str, Any]) -> ArcAssay:
    """Map a database row to an ArcAssay object.

    Args:
        row: Dictionary containing assay data from DB

    Returns:
        ArcAssay object

    Note:
        TODO: Currently measurement_type and technology_type from DB are simple strings,
        but ArcAssay expects OntologyTerm objects. Once the database schema is updated to
        provide full ontology information (term accession, ontology name, etc.), these
        should be converted to proper OntologyTerm objects instead of being omitted.
    """
    # TODO: Convert measurement_type and technology_type to OntologyTerms
    # once the database provides the necessary ontology information
    return ArcAssay.create(
        identifier=str(row["id"]),
    )


def map_contact(row: dict[str, Any]) -> Person:
    """Map a database row to a Person object.

    Args:
        row: Dictionary containing contact data from DB

    Returns:
        Person object
    """
    roles = []
    if row.get("roles"):
        try:
            roles_data = json.loads(row["roles"])
            if isinstance(roles_data, list):
                for r in roles_data:
                    roles.append(
                        OntologyAnnotation(
                            name=r.get("term"),
                            tsr=r.get("version"),
                            tan=r.get("uri"),
                        )
                    )
        except (json.JSONDecodeError, TypeError):
            # Fallback for invalid JSON or type mismatch
            pass

    return Person.create(
        first_name=row.get("first_name"),
        last_name=row.get("last_name"),
        mid_initials=row.get("mid_initials"),
        email=row.get("email"),
        phone=row.get("phone"),
        fax=row.get("fax"),
        address=row.get("address"),
        affiliation=row.get("affiliation"),
        roles=roles if roles else None,
    )


def map_publication(row: dict[str, Any]) -> Publication:
    """Map a database row to a Publication object.

    Args:
        row: Dictionary containing publication data from DB

    Returns:
        Publication object
    """
    return Publication.create(
        pub_med_id=row.get("pub_med_id"),
        doi=row.get("doi"),
        authors=row.get("authors"),
        title=row.get("title"),
    )

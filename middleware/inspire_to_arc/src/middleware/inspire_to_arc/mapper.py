"""Mapper module for converting InspireRecord objects to ARC objects.

This module provides the InspireMapper class, which maps InspireRecord data
to ARC Investigation, Study, Assay, and related objects.
"""

from arctrl import (  # type: ignore[import-untyped]
    ARC,
    ArcAssay,
    ArcInvestigation,
    ArcStudy,
    ArcTable,
    CompositeCell,
    CompositeHeader,
    OntologyAnnotation,
    Person,
)

from .harvester import InspireRecord


class InspireMapper:
    """Maps InspireRecord to ARC objects."""

    def map_record(self, record: InspireRecord) -> ARC:
        """Map InspireRecord to ARC."""
        # 1. Create Investigation
        investigation = self.map_investigation(record)

        # 2. Create Study
        study = self.map_study(record)
        investigation.AddStudy(study)

        # 3. Create Assay
        assay = self.map_assay(record)
        investigation.AddAssay(assay)
        study.RegisterAssay(assay.Identifier)

        # 4. Wrap in ARC
        return ARC.from_arc_investigation(investigation)

    def map_investigation(self, record: InspireRecord) -> ArcInvestigation:
        """Map to ArcInvestigation."""
        # Identifier
        identifier = record.identifier

        # Title
        title = record.title

        # Description
        description = record.abstract

        # Submission Date
        submission_date = record.date_stamp

        inv = ArcInvestigation.create(
            identifier=identifier, title=title, description=description, submission_date=submission_date
        )

        # Contacts
        for contact_dict in record.contacts:
            person = self.map_person(contact_dict)
            inv.Contacts.append(person)

        return inv

    def map_study(self, record: InspireRecord) -> ArcStudy:
        """Map to ArcStudy."""
        identifier = f"{record.identifier}_study"
        title = f"Study for: {record.title}"
        description = record.lineage if record.lineage else "Imported from INSPIRE metadata"

        study = ArcStudy.create(
            identifier=identifier, title=title, description=description, submission_date=record.date_stamp
        )

        # Map Extended Metadata to Table (Protocol)
        table = self.map_extended_metadata_table(record)
        if table:
            study.AddTable(table)

        return study

    def map_assay(self, record: InspireRecord) -> ArcAssay:
        """Map to ArcAssay."""
        identifier = f"{record.identifier}_assay"

        # Measurement Type from Topic Category
        measurement_type = OntologyAnnotation(
            name="Spatial Data Acquisition",
            tan="http://purl.obolibrary.org/obo/NCIT_C19026",  # Example URI
            tsr="NCIT",
        )
        if record.topic_categories:
            # Simple mapping for now
            topic = record.topic_categories[0]
            measurement_type = OntologyAnnotation(
                name=topic,
                tan="http://purl.obolibrary.org/obo/NCIT_C19026",  # Example URI
                tsr="NCIT",
            )

        technology_type = OntologyAnnotation(name="Data Collection", tan="", tsr="")

        assay = ArcAssay.create(
            identifier=identifier, measurement_type=measurement_type, technology_type=technology_type
        )

        return assay

    def map_person(self, contact_dict: dict) -> Person:
        """Map contact dictionary to Person."""
        # Name splitting
        name_parts = (contact_dict.get("name") or "Unknown").split(" ")
        last_name = name_parts[-1]
        first_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""

        person = Person.create(
            last_name=last_name,
            first_name=first_name,
            email=contact_dict.get("email"),
            affiliation=contact_dict.get("organization"),
            address=None,
        )

        # Role
        role = contact_dict.get("role")
        if role:
            person.Roles.append(OntologyAnnotation(name=role))

        return person

    def map_extended_metadata_table(self, record: InspireRecord) -> ArcTable | None:
        """Map extended metadata (Extent, Constraints) to an ArcTable (Protocol)."""
        table = ArcTable.init("Metadata Characteristics")
        has_data = False

        # We create a single row for the metadata values
        cells = []
        headers = []

        # Spatial Extent
        if record.spatial_extent:
            # Format: [minx, miny, maxx, maxy]
            bbox_str = f"{record.spatial_extent}"

            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Spatial Extent")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=bbox_str)))
            has_data = True

        # Temporal Extent
        if record.temporal_extent:
            start, end = record.temporal_extent
            time_str = f"{start} to {end}"

            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Temporal Extent")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=time_str)))
            has_data = True

        # Constraints
        if record.constraints:
            const_str = "; ".join(record.constraints)

            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Access Constraints")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=const_str)))
            has_data = True

        if has_data:
            # Add columns and the single row
            for i, header in enumerate(headers):
                table.AddColumn(header, [cells[i]])
            return table

        return None

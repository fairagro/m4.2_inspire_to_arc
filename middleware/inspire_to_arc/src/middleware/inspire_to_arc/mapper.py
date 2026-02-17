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
    Comment,
    CompositeCell,
    CompositeHeader,
    OntologyAnnotation,
    Person,
    Publication,
)

from .harvester import Contact, InspireRecord


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

    def map_person(self, contact: Contact) -> Person | None:
        """Map contact object to Person with full CI_ResponsibleParty details."""
        if not contact.name:
            return None  # Skip contacts without name

        first_name, last_name = self._split_name(contact.name)
        full_address = self._format_address(contact)
        person = Person.create(
            last_name=last_name,
            first_name=first_name,
            email=contact.email,
            affiliation=contact.organization,
            address=full_address,
            phone=contact.phone,
            fax=contact.fax,
        )

        self._add_role(person, contact)
        self._add_person_comments(person, contact)

        return person

    def _split_name(self, name: str) -> tuple[str, str]:
        """Split full name into first name and last name."""
        name_parts = name.split(" ")
        last_name = name_parts[-1]
        first_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
        return first_name, last_name

    def _format_address(self, contact: Contact) -> str | None:
        """Format full address from contact components."""
        address_parts = []
        if contact.address:
            address_parts.append(contact.address)
        if contact.city:
            address_parts.append(contact.city)
        if contact.region:
            address_parts.append(contact.region)
        if contact.postcode:
            address_parts.append(contact.postcode)
        if contact.country:
            address_parts.append(contact.country)
        return ", ".join(address_parts) if address_parts else None

    def _add_role(self, person: Person, contact: Contact) -> None:
        """Add role to person if available."""
        if contact.role:
            person.Roles.append(OntologyAnnotation(name=contact.role))

    def _add_person_comments(self, person: Person, contact: Contact) -> None:
        """Add comments to person from position and online resources."""
        comments = []
        if contact.position:
            comments.append(f"Position: {contact.position}")
        if contact.online_resource_url:
            if contact.online_resource_name:
                comments.append(f"{contact.online_resource_name}: {contact.online_resource_url}")
            else:
                comments.append(contact.online_resource_url)
        if comments:
            person.Comments.extend(comments)

    def map_investigation(self, record: InspireRecord) -> ArcInvestigation:
        """Map to ArcInvestigation with enhanced metadata-level fields."""
        identifier = record.identifier
        title = record.title
        description = record.abstract
        submission_date = record.date_stamp

        inv = ArcInvestigation.create(
            identifier=identifier, title=title, description=description, submission_date=submission_date
        )

        self._add_contacts(inv, record)
        self._add_publications(inv, record)
        self._add_comments(inv, record)

        return inv

    def _add_contacts(self, inv: ArcInvestigation, record: InspireRecord) -> None:
        """Add all contacts to the investigation."""
        all_contacts = list(record.contacts)
        all_contacts.extend(record.creators)
        all_contacts.extend(record.publishers)
        all_contacts.extend(record.contributors)
        for contact in all_contacts:
            person = self.map_person(contact)
            if person:
                inv.Contacts.append(person)

    def _add_publications(self, inv: ArcInvestigation, record: InspireRecord) -> None:
        """Add publications from resource_identifiers, enriching with investigation metadata."""
        # Get authors from the investigation's contacts and format them as a string
        authors_list = [
            p for p in inv.Contacts if any(hasattr(role, "Name") and role.Name == "author" for role in p.Roles)
        ]
        author_strings = []
        for p in authors_list:
            first_initial = f"{p.FirstName[0]}." if p.FirstName else ""
            author_strings.append(f"{p.LastName}, {first_initial}")
        authors_str = "; ".join(author_strings) if author_strings else None

        for res_id in record.resource_identifiers:
            codespace_str = str(res_id.codespace) if res_id.codespace else ""
            if res_id.code and (
                res_id.code.startswith("10.") or "doi" in res_id.code.lower() or "isbn" in codespace_str.lower()
            ):
                # Create a Publication object with DOI, title, and formatted authors string
                pub = Publication.create(
                    title=record.title,
                    authors=authors_str,
                    doi=res_id.code,
                    # status and pub_date could be added if available
                )
                inv.Publications.append(pub)

    def _add_comments(self, inv: ArcInvestigation, record: InspireRecord) -> None:
        """Add metadata-level comments to the investigation."""
        comments = self._generate_comments(record)
        for comment in comments:
            inv.Comments.append(Comment(comment))

    def _generate_comments(self, record: InspireRecord) -> list[str]:
        """Generate metadata-level comments from record fields."""
        comments = []

        # Simple string-based fields
        fields = [
            ("Parent Identifier", record.parent_identifier),
            ("Hierarchy Level", record.hierarchy),
            ("Dataset URI", record.dataset_uri),
            ("Language", record.language),
            ("Character Set", record.charset),
            ("Edition", record.edition),
            ("Status", record.status),
        ]
        for label, value in fields:
            if value:
                comments.append(f"{label}: {value}")

        # Metadata Standard (with version)
        if record.metadata_standard_name:
            std = record.metadata_standard_name
            if record.metadata_standard_version:
                std += f" v{record.metadata_standard_version}"
            comments.append(f"Metadata Standard: {std}")

        self._add_constraint_comments(comments, record)
        return comments

    def _add_constraint_comments(self, comments: list[str], record: InspireRecord) -> None:
        """Add constraint-related comments."""
        if record.access_constraints:
            comments.append(f"Access Constraints: {', '.join(record.access_constraints)}")
        if record.use_constraints:
            comments.append(f"Use Constraints: {', '.join(record.use_constraints)}")
        if record.classification:
            comments.append(f"Classification: {', '.join(record.classification)}")
        if record.other_constraints:
            comments.append(f"Other Constraints: {'; '.join(record.other_constraints[:3])}")

    def map_study(self, record: InspireRecord) -> ArcStudy:
        """Map to ArcStudy with process-oriented protocols."""
        identifier = f"{record.identifier}_study"
        title = f"Study for: {record.title}"

        # Enhanced description with lineage, purpose, and supplemental info
        desc_parts = []
        if record.lineage:
            desc_parts.append(f"Lineage: {record.lineage}")
        if record.purpose:
            desc_parts.append(f"Purpose: {record.purpose}")
        if record.supplemental_information:
            desc_parts.append(f"Supplemental: {record.supplemental_information}")
        description = " | ".join(desc_parts) if desc_parts else "Imported from INSPIRE metadata"

        study = ArcStudy.create(
            identifier=identifier, title=title, description=description, submission_date=record.date_stamp
        )

        # Add Process-Oriented Protocols (max 3)
        # Protocol 1: Spatial Sampling (if spatial info available)
        sampling_protocol = self._create_spatial_sampling_protocol(record)
        if sampling_protocol:
            study.AddTable(sampling_protocol)

        # Protocol 2: Data Acquisition (if temporal or acquisition info available)
        acquisition_protocol = self._create_data_acquisition_protocol(record)
        if acquisition_protocol:
            study.AddTable(acquisition_protocol)

        # Protocol 3: Data Processing (always created from lineage)
        processing_protocol = self._create_data_processing_protocol(record)
        if processing_protocol:
            study.AddTable(processing_protocol)

        return study

    def _create_spatial_sampling_protocol(self, record: InspireRecord) -> ArcTable | None:
        """Create Spatial Sampling protocol if spatial information is available.

        Represents: Selection of geographic location(s) for data collection.
        Input: Geographic Region / Area of Interest
        Output: Selected Location(s)
        """
        if not (record.spatial_extent or record.spatial_resolution_denominators or record.spatial_resolution_distances):
            return None

        table = ArcTable.init("Spatial Sampling")
        headers = []
        cells = []

        # Bounding Box
        if record.spatial_extent:
            bbox_str = f"[{', '.join(map(str, record.spatial_extent))}]"
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Bounding Box")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=bbox_str)))

        # Spatial Resolution - Denominators (Scale)
        if record.spatial_resolution_denominators:
            scale_str = ", ".join(f"1:{d}" for d in record.spatial_resolution_denominators)
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Spatial Resolution (Scale)")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=scale_str)))

        # Spatial Resolution - Distance
        if record.spatial_resolution_distances:
            dist_str = ", ".join(f"{rd.value} {rd.uom}" for rd in record.spatial_resolution_distances)
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Spatial Resolution (Distance)")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=dist_str)))

        if headers:
            for i, header in enumerate(headers):
                table.AddColumn(header, [cells[i]])
            return table
        return None

    def _create_data_acquisition_protocol(self, record: InspireRecord) -> ArcTable | None:
        """Create Data Acquisition protocol if temporal/acquisition metadata available.

        Represents: Actual data collection/sensing process.
        Input: Selected Location(s) + Temporal Period
        Output: Raw Sensor Data / Observations
        """
        if not (record.temporal_extent or record.dates):
            return None

        table = ArcTable.init("Data Acquisition")
        headers = []
        cells = []

        # Temporal Extent
        if record.temporal_extent:
            start, end = record.temporal_extent
            time_str = f"{start or 'unknown'} to {end or 'unknown'}"
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Temporal Extent")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=time_str)))

        # Acquisition/Creation Dates
        creation_dates = [d.date for d in record.dates if d.datetype == "creation"]
        if creation_dates:
            dates_str = ", ".join(creation_dates)
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Acquisition Date")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=dates_str)))

        # Platform/Sensor (from acquisition metadata - would need to be extracted)
        # NOTE: acquisition is complex nested - not implemented in extraction phase

        if headers:
            for i, header in enumerate(headers):
                table.AddColumn(header, [cells[i]])
            return table
        return None

    def _create_data_processing_protocol(self, record: InspireRecord) -> ArcTable | None:
        """Create Data Processing protocol (always created if lineage or quality info available).

        Represents: Processing from raw data to final published dataset.
        Input: Raw Sensor Data
        Output: Processed/Published Dataset
        """
        table = ArcTable.init("Data Processing")
        headers = []
        cells = []

        # Lineage (processing description)
        if record.lineage:
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Processing Description")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=record.lineage[:500])))  # Truncate if too long

        # Quality/Conformance Results
        if record.conformance_results:
            for conf in record.conformance_results:
                spec_name = conf.specification_title
                pass_str = (
                    "PASS"
                    if conf.degree and conf.degree.lower() in ["true", "pass"]
                    else "FAIL"
                    if conf.degree
                    else "Unknown"
                )
                conf_str = f"{spec_name}: {pass_str}"
                headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Conformance")))
                cells.append(CompositeCell.term(OntologyAnnotation(name=conf_str)))

        # Data Format
        if record.distribution_formats:
            for fmt in record.distribution_formats:
                fmt_str = f"{fmt.name}" + (f" v{fmt.version}" if fmt.version else "")
                headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Output Format")))
                cells.append(CompositeCell.term(OntologyAnnotation(name=fmt_str)))

        # Processing/Publication Dates
        pub_dates = [d.date for d in record.dates if d.datetype in ["publication", "revision"]]
        if pub_dates:
            dates_str = ", ".join(pub_dates)
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Processing Date")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=dates_str)))

        if headers:
            for i, header in enumerate(headers):
                table.AddColumn(header, [cells[i]])
            return table

        # If no headers, create minimal protocol with just a note
        if record.lineage or record.dates:
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Note")))
            cells.append(CompositeCell.term(OntologyAnnotation(name="Data processing details from INSPIRE metadata")))
            table.AddColumn(headers[0], [cells[0]])
            return table

        return None

    def map_assay(self, record: InspireRecord) -> ArcAssay:
        """Map to ArcAssay with reference systems as TechnologyPlatform."""
        identifier = f"{record.identifier}_assay"

        measurement_type = self._get_measurement_type(record)
        technology_type = OntologyAnnotation(name="Data Collection", tan="", tsr="")

        assay = ArcAssay.create(
            identifier=identifier, measurement_type=measurement_type, technology_type=technology_type
        )

        tech_platform = self._get_technology_platform(record)
        assay.TechnologyPlatform = OntologyAnnotation(name=tech_platform) if tech_platform else None
        self._add_assay_comments(assay, record)

        return assay

    def _get_measurement_type(self, record: InspireRecord) -> OntologyAnnotation:
        """Get measurement type from topic category."""
        if record.topic_categories:
            topic = record.topic_categories[0]
            return OntologyAnnotation(
                name=topic,
                tan="http://purl.obolibrary.org/obo/NCIT_C19026",
                tsr="NCIT",
            )
        return OntologyAnnotation(
            name="Spatial Data Acquisition",
            tan="http://purl.obolibrary.org/obo/NCIT_C19026",
            tsr="NCIT",
        )

    def _get_technology_platform(self, record: InspireRecord) -> str | None:
        """Get TechnologyPlatform from Reference Systems (CRS)."""
        if record.reference_systems:
            for ref_sys in record.reference_systems:
                if ref_sys.code:
                    return ref_sys.code
        return None

    def _add_assay_comments(self, assay: ArcAssay, record: InspireRecord) -> None:
        """Add comments to assay from graphic overviews and online resources."""
        comments = []
        if record.graphic_overviews:
            for url in record.graphic_overviews:
                comments.append(f"Preview: {url}")
        if record.online_resources:
            for res in record.online_resources:
                if res.name:
                    comments.append(f"{res.name}: {res.url}")
                else:
                    comments.append(res.url)
        for comment in comments:
            assay.Comments.append(Comment(comment))

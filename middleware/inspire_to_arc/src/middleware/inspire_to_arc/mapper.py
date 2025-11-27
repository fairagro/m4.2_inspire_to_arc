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

    def map_person(self, contact: Contact) -> Person:
        """Map contact object to Person with full CI_ResponsibleParty details."""
        # Name splitting - prefer full name over just last name
        if not contact.name:
            return None  # Skip contacts without name
        name_parts = contact.name.split(" ")
        last_name = name_parts[-1]
        first_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""

        # Format full address from components
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
        full_address = ", ".join(address_parts) if address_parts else None

        person = Person.create(
            last_name=last_name,
            first_name=first_name,
            email=contact.email,
            affiliation=contact.organization,
            address=full_address,
            phone=contact.phone,
            fax=contact.fax,
        )

        # Role
        if contact.role:
            person.Roles.append(OntologyAnnotation(name=contact.role))

        # Comments: position and online resources
        comments = []
        if contact.position:
            comments.append(f"Position: {contact.position}")
        if contact.online_resource_url:
            if contact.online_resource_name:
                comments.append(f"{contact.online_resource_name}: {contact.online_resource_url}")
            else:
                comments.append(contact.online_resource_url)
        
        if comments:
            person.Comments.extend([OntologyAnnotation(name=c) for c in comments])

        return person

    def map_investigation(self, record: InspireRecord) -> ArcInvestigation:
        """Map to ArcInvestigation with enhanced metadata-level fields."""
        # Core fields
        identifier = record.identifier
        title = record.title
        description = record.abstract
        submission_date = record.date_stamp

        inv = ArcInvestigation.create(
            identifier=identifier, title=title, description=description, submission_date=submission_date
        )

        # Contacts (all contacts - general, creators, publishers, contributors)
        all_contacts = list(record.contacts)
        all_contacts.extend(record.creators)
        all_contacts.extend(record.publishers)
        all_contacts.extend(record.contributors)
        
        for contact in all_contacts:
            person = self.map_person(contact)
            if person:  # Skip contacts without name
                inv.Contacts.append(person)

        # Publications from resource_identifiers (DOI, ISBN, etc.)
        for res_id in record.resource_identifiers:
            # Only add as Publication if it looks like a DOI or ISBN
            codespace_str = str(res_id.codespace) if res_id.codespace else ""
            if res_id.code and (res_id.code.startswith("10.") or "doi" in res_id.code.lower() or "isbn" in codespace_str.lower()):
                pub = OntologyAnnotation(
                    name=res_id.code,
                    tan=res_id.url if res_id.url else None,
                    tsr=res_id.codespace if res_id.codespace else None
                )
                inv.Publications.append(pub)

        # Comments: Metadata-level fields
        comments = []
        
        # Parent/Hierarchy information
        if record.parent_identifier:
            comments.append(f"Parent Identifier: {record.parent_identifier}")
        if record.hierarchy:
            comments.append(f"Hierarchy Level: {record.hierarchy}")
        
        # Dataset URI
        if record.dataset_uri:
            comments.append(f"Dataset URI: {record.dataset_uri}")
        
        # Metadata Standard
        if record.metadata_standard_name:
            std = record.metadata_standard_name
            if record.metadata_standard_version:
                std += f" v{record.metadata_standard_version}"
            comments.append(f"Metadata Standard: {std}")
        
        # Language and Charset
        if record.language:
            comments.append(f"Language: {record.language}")
        if record.charset:
            comments.append(f"Character Set: {record.charset}")
        
        # Constraints (all types)
        if record.access_constraints:
            comments.append(f"Access Constraints: {', '.join(record.access_constraints)}")
        if record.use_constraints:
            comments.append(f"Use Constraints: {', '.join(record.use_constraints)}")
        if record.classification:
            comments.append(f"Classification: {', '.join(record.classification)}")
        if record.other_constraints:
            comments.append(f"Other Constraints: {'; '.join(record.other_constraints[:3])}")  # Limit to 3
        
        # Edition, Status, Purpose (if not already in description)
        if record.edition:
            comments.append(f"Edition: {record.edition}")
        if record.status:
            comments.append(f"Status: {record.status}")
        
        # Add all comments to Investigation
        for comment in comments:
            inv.Comments.append(OntologyAnnotation(name=comment))

        return inv

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
                pass_str = "PASS" if conf.degree and conf.degree.lower() in ["true", "pass"] else "FAIL" if conf.degree else "Unknown"
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

        # Measurement Type from Topic Category
        measurement_type = OntologyAnnotation(
            name="Spatial Data Acquisition",
            tan="http://purl.obolibrary.org/obo/NCIT_C19026",
            tsr="NCIT",
        )
        if record.topic_categories:
            topic = record.topic_categories[0]
            measurement_type = OntologyAnnotation(
                name=topic,
                tan="http://purl.obolibrary.org/obo/NCIT_C19026",
                tsr="NCIT",
            )

        technology_type = OntologyAnnotation(name="Data Collection", tan="", tsr="")

        assay = ArcAssay.create(
            identifier=identifier, measurement_type=measurement_type, technology_type=technology_type
        )

        # TechnologyPlatform from Reference Systems (CRS)
        if record.reference_systems:
            for ref_sys in record.reference_systems:
                if ref_sys.code:
                    assay.TechnologyPlatform = ref_sys.code
                    break  # Use first reference system with code

        # Comments: Graphic Overviews and Online Resources
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
        
        if comments:
            for comment in comments:
                assay.Comments.append(OntologyAnnotation(name=comment))

        return assay

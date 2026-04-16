"""Mapper module for converting InspireRecord objects to ARC objects.

This module provides the InspireMapper class, which maps InspireRecord data
to ARC Investigation, Study, Assay, and related objects.
"""

import re

from arctrl import (  # type: ignore[import-untyped]
    ARC,
    ArcAssay,
    ArcInvestigation,
    ArcStudy,
    ArcTable,
    Comment,
    CompositeCell,
    CompositeHeader,
    IOType,
    OntologyAnnotation,
    Person,
    Publication,
)
from arctrl.py.Core.ontology_source_reference import OntologySourceReference  # type: ignore[import-untyped]

from .models import Contact, InspireRecord


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
        arc = ARC.from_arc_investigation(investigation)

        # 5. Add raw XML as file
        if record.raw_xml:
            arc.FileSystem = arc.FileSystem.AddFile("iso19115.xml")

        return arc

    def _to_identifier_slug(self, title: str) -> str:
        """Convert a title to a machine-readable identifier slug."""
        if not title:
            return "untitled"
        # Lowercase, replace non-alphanumeric with underscores
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower())
        # Remove leading/trailing underscores
        slug = slug.strip("_")
        # Truncate to a reasonable length
        return slug[:80]

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
        """Add role to person with ontology mapping if available."""
        if not contact.role:
            return

        # Map INSPIRE role codes to ontology terms
        role_mapping = {
            "pointOfContact": ("Point of Contact", "http://purl.obolibrary.org/obo/NCIT_C70902", "NCIT"),
            "custodian": ("Custodian", "http://purl.obolibrary.org/obo/NCIT_C70903", "NCIT"),
            "owner": ("Owner", "http://purl.obolibrary.org/obo/NCIT_C70904", "NCIT"),
            "user": ("User", "http://purl.obolibrary.org/obo/NCIT_C70905", "NCIT"),
            "distributor": ("Distributor", "http://purl.obolibrary.org/obo/NCIT_C70906", "NCIT"),
            "originator": ("Originator", "http://purl.obolibrary.org/obo/NCIT_C70907", "NCIT"),
            "publisher": ("Publisher", "http://purl.obolibrary.org/obo/NCIT_C70908", "NCIT"),
            "author": ("Author", "http://purl.obolibrary.org/obo/NCIT_C70909", "NCIT"),
            "principalInvestigator": ("Principal Investigator", "http://purl.obolibrary.org/obo/NCIT_C70910", "NCIT"),
            "processor": ("Processor", "http://purl.obolibrary.org/obo/NCIT_C70911", "NCIT"),
            "metadataContact": ("Metadata Contact", "http://purl.obolibrary.org/obo/NCIT_C70912", "NCIT"),
        }

        # Use mapped role or fall back to original
        mapped_role = role_mapping.get(contact.role.lower(), (contact.role, None, None))
        role_name, tan, tsr = mapped_role

        if tan and tsr:
            person.Roles.append(OntologyAnnotation(name=role_name, tan=tan, tsr=tsr))
        else:
            person.Roles.append(OntologyAnnotation(name=role_name))

    def _add_person_comments(self, person: Person, contact: Contact) -> None:
        """Add comments to person from position and online resources."""
        if contact.position:
            person.Comments.append(Comment.create("Position", contact.position))
        if contact.online_resource_url:
            name = contact.online_resource_name or "Online Resource"
            person.Comments.append(Comment.create(name, contact.online_resource_url))

    def map_investigation(self, record: InspireRecord) -> ArcInvestigation:
        """Map to ArcInvestigation with enhanced metadata-level fields."""
        # Sanitize identifier: use a slug if it looks like a URL to avoid filesystem issues
        identifier = record.identifier
        if identifier and ("://" in identifier or "/" in identifier):
            identifier = self._to_identifier_slug(record.title) or identifier.split("/")[-1]

        title = record.title
        description = record.abstract
        submission_date = record.date_stamp

        inv = ArcInvestigation.create(
            identifier=identifier, title=title, description=description, submission_date=submission_date
        )

        self._add_contacts(inv, record)
        self._add_publications(inv, record)
        self._add_comments(inv, record)
        self._add_ontology_sources(inv, record)

        return inv

    def _add_ontology_sources(self, inv: ArcInvestigation, record: InspireRecord) -> None:
        """Add ontology source references from metadata standard and common ontologies."""
        # Add metadata standard as ontology source
        if record.metadata_standard_name:
            inv.OntologySourceReferences.append(
                OntologySourceReference.create(
                    name=record.metadata_standard_name,
                    version=record.metadata_standard_version or "",
                    description="INSPIRE Metadata Standard",
                )
            )

        # Add common ontology sources for proper referencing
        common_ontologies = [
            ("NCIT", "http://purl.obolibrary.org/obo/ncit.owl", "NCI Thesaurus"),
            ("GEMET", "http://www.eionet.europa.eu/gemet", "GEMET Thesaurus"),
            ("EDAM", "http://edamontology.org", "EDAM Bioinformatics Ontology"),
            ("ISO", "http://www.isotc211.org/2005/gco", "ISO Geospatial Metadata"),
        ]

        for name, url, desc in common_ontologies:
            inv.OntologySourceReferences.append(
                OntologySourceReference.create(
                    name=name,
                    file=url,
                    version="",
                    description=desc,
                )
            )

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
            inv.Comments.append(comment)

    def _generate_comments(self, record: InspireRecord) -> list[Comment]:
        """Generate metadata-level comments from record fields."""
        comments = []

        # Simple string-based fields
        fields = [
            ("Metadata Standard", record.metadata_standard_name),
            ("Parent Identifier", record.parent_identifier),
            ("Language", record.language),
            ("Edition", record.edition),
            ("Status", record.status),
            ("Alternate Title", record.alternate_title),
            ("Purpose", record.purpose),
            ("Supplemental Information", record.supplemental_information),
        ]
        for label, value in fields:
            if value:
                comments.append(Comment.create(label, value))

        self._add_hierarchy_comments(comments, record)
        self._add_constraint_comments(comments, record)
        return comments

    def _add_hierarchy_comments(self, comments: list[Comment], record: InspireRecord) -> None:
        """Add hierarchy level information as comments if not standard dataset."""
        if not record.hierarchy:
            return

        # Ignore standard dataset types
        hierarchy_lower = record.hierarchy.lower()
        if hierarchy_lower in ["dataset", "nongeographicdataset"]:
            return

        # Document non-standard hierarchy levels
        comments.append(Comment.create("Hierarchy Level", record.hierarchy))

    def _add_constraint_comments(self, comments: list[Comment], record: InspireRecord) -> None:
        """Add constraint-related comments."""
        if record.access_constraints:
            comments.append(Comment.create("Access Constraints", ", ".join(record.access_constraints)))
        if record.use_constraints:
            comments.append(Comment.create("Use Constraints", ", ".join(record.use_constraints)))
        if record.classification:
            comments.append(Comment.create("Classification", ", ".join(record.classification)))
        if record.other_constraints:
            comments.append(Comment.create("Other Constraints", "; ".join(record.other_constraints[:3])))
        if record.other_constraints_url:
            comments.append(Comment.create("Other Constraints URLs", "; ".join(record.other_constraints_url[:3])))

    def map_study(self, record: InspireRecord) -> ArcStudy:
        """Map to ArcStudy with process-oriented protocols."""
        identifier = self._to_identifier_slug(record.title)
        title = record.title

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

        Note: Only created for geographic datasets, not for nonGeographicDataset hierarchy level.
        """
        # Skip for non-geographic datasets
        if record.hierarchy and record.hierarchy.lower() == "nongeographicdataset":
            return None

        if not (
            record.spatial_extent
            or record.spatial_resolution_denominators
            or record.spatial_resolution_distances
            or record.reference_systems
        ):
            return None

        table = ArcTable.init("Spatial Sampling")
        headers = []
        cells = []

        # Bounding Box
        if record.spatial_extent:
            bbox_str = f"[{', '.join(map(str, record.spatial_extent))}]"
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Bounding Box")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=bbox_str)))

        # CRS (Coordinate Reference System)
        if record.reference_systems:
            crs_list = []
            for rs in record.reference_systems:
                crs_str = f"{rs.codespace}:{rs.code}" if rs.codespace else rs.code
                crs_list.append(crs_str)
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Coordinate Reference System")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=", ".join(crs_list))))

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
            # Add Input Column
            table.AddColumn(
                CompositeHeader.input(IOType.source()),
                [CompositeCell.free_text("Geographic Region")],
            )
            for i, header in enumerate(headers):
                table.AddColumn(header, [cells[i]])
            # Add Output Column
            table.AddColumn(
                CompositeHeader.output(IOType.sample()),
                [CompositeCell.free_text("Selected Location")],
            )
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

        # NOTE: acquisition is complex nested - not implemented in extraction phase

        if headers:
            # Add Input Column
            table.AddColumn(
                CompositeHeader.input(IOType.sample()),
                [CompositeCell.free_text("Selected Location")],
            )
            for i, header in enumerate(headers):
                table.AddColumn(header, [cells[i]])
            # Add Output Column
            table.AddColumn(
                CompositeHeader.output(IOType.data()),
                [CompositeCell.create_data_from_string("Raw Data")],
            )
            return table
        return None

    def _create_data_processing_protocol(self, record: InspireRecord) -> ArcTable | None:
        """Create Data Processing protocol (always created if lineage or quality info available).

        Represents: Processing from raw data to final published dataset.
        Input: Raw Sensor Data
        Output: Processed/Published Dataset
        """
        headers, cells = self._build_processing_protocol_columns(record)

        if headers:
            return self._assemble_processing_table_with_headers(headers, cells)

        if record.lineage or record.dates:
            return self._create_minimal_processing_table()

        return None

    def _build_processing_protocol_columns(
        self, record: InspireRecord
    ) -> tuple[list[CompositeHeader], list[CompositeCell]]:
        """Build headers and cells for data processing protocol."""
        headers: list[CompositeHeader] = []
        cells: list[CompositeCell] = []

        self._add_lineage_columns(record, headers, cells)
        self._add_conformance_columns(record, headers, cells)
        self._add_format_columns(record, headers, cells)
        self._add_date_columns(record, headers, cells)

        return headers, cells

    def _add_lineage_columns(self, record: InspireRecord, headers: list[CompositeHeader], cells: list) -> None:
        """Add lineage-related columns to processing protocol."""
        if record.lineage:
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Processing Description")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=record.lineage[:500])))

        if record.lineage_url:
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Lineage Documentation URL")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=record.lineage_url)))

    def _add_conformance_columns(self, record: InspireRecord, headers: list[CompositeHeader], cells: list) -> None:
        """Add conformance result columns to processing protocol."""
        if not record.conformance_results:
            return

        for conf in record.conformance_results:
            spec_name = conf.specification_title
            pass_str = self._format_conformance_status(conf.degree)
            conf_str = f"{spec_name}: {pass_str}"
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Conformance")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=conf_str)))

    def _format_conformance_status(self, degree: str | None) -> str:
        """Format conformance degree to PASS/FAIL/Unknown."""
        if degree and degree.lower() in ["true", "pass"]:
            return "PASS"
        if degree:
            return "FAIL"
        return "Unknown"

    def _add_format_columns(self, record: InspireRecord, headers: list[CompositeHeader], cells: list) -> None:
        """Add data format columns to processing protocol."""
        if not record.distribution_formats:
            return

        for fmt in record.distribution_formats:
            fmt_str = f"{fmt.name}" + (f" v{fmt.version}" if fmt.version else "")
            headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Output Format")))
            cells.append(CompositeCell.term(OntologyAnnotation(name=fmt_str)))

    def _add_date_columns(self, record: InspireRecord, headers: list[CompositeHeader], cells: list) -> None:
        """Add processing date columns to processing protocol."""
        pub_dates = [d.date for d in record.dates if d.datetype in ["publication", "revision"]]
        if not pub_dates:
            return

        dates_str = ", ".join(pub_dates)
        headers.append(CompositeHeader.parameter(OntologyAnnotation(name="Processing Date")))
        cells.append(CompositeCell.term(OntologyAnnotation(name=dates_str)))

    def _assemble_processing_table_with_headers(self, headers: list[CompositeHeader], cells: list) -> ArcTable:
        """Assemble processing table with input, parameter, and output columns."""
        table = ArcTable.init("Data Processing")
        table.AddColumn(
            CompositeHeader.input(IOType.data()),
            [CompositeCell.create_data_from_string("Raw Data")],
        )
        for i, header in enumerate(headers):
            table.AddColumn(header, [cells[i]])
        table.AddColumn(
            CompositeHeader.output(IOType.data()),
            [CompositeCell.create_data_from_string("Processed Data")],
        )
        return table

    def _create_minimal_processing_table(self) -> ArcTable:
        """Create minimal processing table with just a note."""
        table = ArcTable.init("Data Processing")
        table.AddColumn(
            CompositeHeader.input(IOType.data()),
            [CompositeCell.create_data_from_string("Raw Data")],
        )
        table.AddColumn(
            CompositeHeader.parameter(OntologyAnnotation(name="Note")),
            [CompositeCell.term(OntologyAnnotation(name="Data processing details from INSPIRE metadata"))],
        )
        table.AddColumn(
            CompositeHeader.output(IOType.data()),
            [CompositeCell.create_data_from_string("Processed Data")],
        )
        return table

    def map_assay(self, record: InspireRecord) -> ArcAssay:
        """Map to ArcAssay with enhanced technology platform and annotation table."""
        identifier = self._to_identifier_slug(record.title)
        title = record.title

        measurement_type = self._get_measurement_type(record)
        technology_type = OntologyAnnotation(name="Data Collection")

        assay = ArcAssay.create(
            identifier=identifier,
            title=title,
            measurement_type=measurement_type,
            technology_type=technology_type,
        )

        # Set Technology Platform (user suggested acquisitionInformation)
        assay.TechnologyPlatform = OntologyAnnotation(name="Satellite/Sensor Acquisition")

        # Add the annotation table.
        assay.AddTable(self._create_assay_table(record))

        return assay

    def _create_assay_table(self, record: InspireRecord) -> ArcTable:
        """Create the assay annotation table (always exactly one row).

        Columns:
        - Input [Source Name]                : "Dataset Source" (always present)
        - Output [URI]                       : dataSetURI (preferred) → first online-resource URL
                                               → fallback slug "<id>_dataset"
        - Comment [Online Resource]          : semicolon-joined online-resource URLs, if any
                                               (first URL omitted when used as Output[URI] fallback)
        - Comment [Online Resource Name]     : semicolon-joined resource names, if any
        - Comment [Online Resource Protocol] : semicolon-joined protocols, if any
        - Comment [Online Resource Description]: semicolon-joined descriptions, if any
        - Comment [Online Resource Function] : semicolon-joined function codes, if any
        - Comment [Graphic Overview]         : semicolon-joined graphic-overview URLs, if any

        Columns whose values are all empty are omitted.  Output[URI] uses
        IOType.of_string("URI") (FreeType tag 4), which is side-effect-free.
        """
        # Determine primary Output URI: dataSetURI > first online resource > slug
        fallback_used = False
        if record.dataset_uri:
            output_uri: str = record.dataset_uri
        elif record.online_resources:
            output_uri = record.online_resources[0].url
            fallback_used = True
        else:
            output_uri = f"{self._to_identifier_slug(record.title)}_dataset"

        table = ArcTable.init("Measurement")
        table.AddColumn(CompositeHeader.input(IOType.source()), [CompositeCell.free_text("Dataset Source")])
        table.AddColumn(
            CompositeHeader.output(IOType.of_string("URI")),
            [CompositeCell.free_text(output_uri)],
        )

        # Online-resource URLs (skip index 0 when it was used as the Output fallback)
        online_urls = [res.url for i, res in enumerate(record.online_resources) if not (fallback_used and i == 0)]
        if online_urls:
            table.AddColumn(
                CompositeHeader.comment("Online Resource"),
                [CompositeCell.free_text(";".join(online_urls))],
            )

        # Additional CI_OnlineResource fields — each as a separate Comment column,
        # omitted entirely when all resources have no value for that field.
        def _joined(attr: str) -> str:
            return ";".join(
                getattr(res, attr) or ""
                for i, res in enumerate(record.online_resources)
                if not (fallback_used and i == 0)
            )

        for col_name, attr in [
            ("Online Resource Name", "name"),
            ("Online Resource Protocol", "protocol"),
            ("Online Resource Description", "description"),
            ("Online Resource Function", "function"),
        ]:
            value = _joined(attr)
            if value.replace(";", "").strip():
                table.AddColumn(
                    CompositeHeader.comment(col_name),
                    [CompositeCell.free_text(value)],
                )

        # Graphic-overview URLs
        if record.graphic_overviews:
            table.AddColumn(
                CompositeHeader.comment("Graphic Overview"),
                [CompositeCell.free_text(";".join(record.graphic_overviews))],
            )

        return table

    def _get_measurement_type(self, record: InspireRecord) -> OntologyAnnotation:
        """Get measurement type from topic category with ontology mapping."""
        # Topic category to ontology mapping
        topic_mapping = {
            "biota": ("Biological Measurement", "http://purl.obolibrary.org/obo/NCIT_C19026", "NCIT"),
            "boundaries": ("Boundary Measurement", "http://purl.obolibrary.org/obo/NCIT_C19027", "NCIT"),
            "climatologyMeteorologyAtmosphere": (
                "Atmospheric Measurement",
                "http://purl.obolibrary.org/obo/ENVO_01000818",
                "ENVO",
            ),
            "economy": ("Economic Measurement", "http://purl.obolibrary.org/obo/NCIT_C19029", "NCIT"),
            "elevation": ("Elevation Measurement", "http://purl.obolibrary.org/obo/ENVO_00002001", "ENVO"),
            "environment": ("Environmental Measurement", "http://purl.obolibrary.org/obo/ENVO_01000819", "ENVO"),
            "farming": ("Agricultural Measurement", "http://purl.obolibrary.org/obo/AGRO_00000001", "AGRO"),
            "geoscientificInformation": (
                "Geoscientific Measurement",
                "http://purl.obolibrary.org/obo/ENVO_01000820",
                "ENVO",
            ),
            "health": ("Health Measurement", "http://purl.obolibrary.org/obo/NCIT_C19034", "NCIT"),
            "imageryBaseMapsEarthCover": (
                "Remote Sensing Measurement",
                "http://purl.obolibrary.org/obo/ENVO_01000817",
                "ENVO",
            ),
            "inlandWaters": ("Hydrological Measurement", "http://purl.obolibrary.org/obo/ENVO_01000821", "ENVO"),
            "intelligenceMilitary": ("Military Measurement", "http://purl.obolibrary.org/obo/NCIT_C19037", "NCIT"),
            "location": ("Location Measurement", "http://purl.obolibrary.org/obo/NCIT_C19038", "NCIT"),
            "oceans": ("Oceanographic Measurement", "http://purl.obolibrary.org/obo/ENVO_00000015", "ENVO"),
            "planningCadastre": ("Cadastre Measurement", "http://purl.obolibrary.org/obo/NCIT_C19040", "NCIT"),
            "society": ("Social Measurement", "http://purl.obolibrary.org/obo/NCIT_C19041", "NCIT"),
            "structure": ("Structural Measurement", "http://purl.obolibrary.org/obo/NCIT_C19042", "NCIT"),
            "transportation": ("Transportation Measurement", "http://purl.obolibrary.org/obo/NCIT_C19043", "NCIT"),
            "utilitiesCommunication": ("Utility Measurement", "http://purl.obolibrary.org/obo/NCIT_C19044", "NCIT"),
        }

        if record.topic_categories:
            topic = record.topic_categories[0]
            mapped_topic = topic_mapping.get(topic)
            if mapped_topic:
                return OntologyAnnotation(name=mapped_topic[0], tan=mapped_topic[1], tsr=mapped_topic[2])
            return OntologyAnnotation(name=topic)

        return OntologyAnnotation(
            name="Spatial Data Acquisition",
            tan="http://purl.obolibrary.org/obo/NCIT_C19026",
            tsr="NCIT",
        )

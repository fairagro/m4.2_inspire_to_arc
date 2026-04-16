# INSPIRE to ARC Mapping Documentation

This document describes how INSPIRE-compliant geospatial metadata (ISO 19139 XML) is mapped to the ISA (Investigation, Study, Assay) model used by ARC.

## Concept

The goal is to map geospatial metadata (INSPIRE) to the ISA model. Since INSPIRE metadata describes *datasets* (results), while ARC describes the *research process* (investigation/study/assay), we apply a mapping strategy that preserves provenance.

### Protocol-Based Mapping Philosophy

> [!IMPORTANT]
> **Protocols are central to ARC**: They describe exactly how data was created. Every process step—whether sample collection, chemical analysis, sensor acquisition, or data processing—can be modeled as a Protocol with Parameters.
>
> This applies equally to earth observation and laboratory experiments. **The more protocols we capture from INSPIRE metadata, the better the research provenance documentation.**

## Available INSPIRE Metadata Fields

The ISO 19139 standard (via OWSLib) provides **50+ metadata fields** organized across multiple classes. This section documents all available fields and their proposed ARC mappings.

### 1. MD_Metadata (Top-Level Metadata)

Metadata about the metadata record itself.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **fileIdentifier** | `identifier` | UUID of the metadata record | `Investigation.Identifier` |
| **parentIdentifier** | `parentidentifier` | Parent metadata record UUID (for hierarchies) | `Investigation.Description` (comment) |
| **language** | `language` / `languagecode` | Language of the metadata | `Investigation` comment/remark |
| **characterSet** | `charset` | Character encoding (UTF-8, etc.) | `Investigation` comment |
| **hierarchyLevel** | `hierarchy` | Scope: dataset, series, service, etc. | `Investigation` comment (non-standard levels documented) |
| **dateStamp** | `datestamp` / `datetimestamp` | When metadata was created/updated | `Investigation.SubmissionDate` |
| **metadataStandardName** | `stdname` | Standard name (ISO 19115, etc.) | `Investigation` comment (provenance) |
| **metadataStandardVersion** | `stdver` | Standard version | `Investigation` comment (provenance) |
| **dataSetURI** | `dataseturi` | Direct URI to the dataset | **Assay Annotation Table** `Output [URI]` (preferred Output value) |
| **contact** | `contact` | Metadata point of contact | `Investigation.Contacts` (Person with role="metadata_contact") |
| **referenceSystemInfo** | `referencesystem` | Coordinate Reference System (CRS) | **Spatial Sampling Protocol** parameter "CRS" |
| **contentInfo** | `contentinfo` | Feature catalogue or image description | **Assay Protocol** "Feature Catalogue" or "Image Description" |
| **distributionInfo** | `distribution` | How to obtain the data | **Assay Annotation Table** `Comment [Online Resource]` (semicolon-joined URLs; if no `dataSetURI`, first URL promoted to `Output [URI]`) |
| **dataQualityInfo** | `dataquality` | Data quality and lineage | **Protocol** "Data Processing" (conformance as parameters) |
| **acquisitionInformation** | `acquisition` | Sensor/platform metadata (remote sensing) | **Assay Technology Platform** |

### 2. MD_DataIdentification (Resource Identification)

Core descriptive metadata about the dataset.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **citation/title** | `title` | Dataset title | `Investigation.Title` |
| **citation/alternateTitle** | `alternatetitle` | Alternative title | `Investigation` comment |
| **citation/identifier** | `uricode`, `uricodespace` | Resource identifiers (DOI, ISBN, etc.) | `Investigation.Publications` (if DOI/ISBN) |
| **citation/date** | `date` (list of `CI_Date`) | Creation, publication, revision dates | **Study Protocol** parameter "Data Citation" |
| **citation/edition** | `edition` | Version/edition of the dataset | `Investigation` comment or `Study.Description` |
| **abstract** | `abstract` | Abstract/summary | `Investigation.Description` |
| **purpose** | `purpose` | Why the dataset was created | `Study.Description` (in addition to lineage) |
| **status** | `status` | Progress: completed, onGoing, planned, etc. | `Study` comment or Protocol parameter |
| **pointOfContact** | `contact`, `creator`, `publisher`, `contributor` | Resource contacts by role | `Investigation.Contacts` (Person) split by role |
| **graphicOverview** | `graphicoverview` | Thumbnail/preview image URLs | **Assay Annotation Table** `Comment [Graphic Overview]` (semicolon-joined URLs) |
| **resourceConstraints** | Various constraint fields (see below) | Legal and security constraints | **Investigation Comments** |
| **spatialRepresentationType** | `spatialrepresentationtype` | Vector, grid, TIN, etc. | `Assay.TechnologyType` or comment |
| **spatialResolution** | `denominators`, `distance`, `uom` | Resolution (scale or distance) | **Study Protocol** "Spatial Resolution" with parameters |
| **language** | `resourcelanguage`, `resourcelanguagecode` | Language of the dataset | `Investigation` comment |
| **topicCategory** | `topiccategory` | ISO topic category (biota, environment, etc.) | `Assay.MeasurementType` (via ontology mapping to domain-specific ontologies) |
| **extent/geographicElement** | `bbox`, `boundingPolygon`, `description_code` | Spatial extent (bounding box or polygon) | **Study Protocol** "Data Collection" parameter "Spatial Extent" |
| **extent/temporalElement** | `temporalextent_start`, `temporalextent_end` | Temporal extent (start/end dates) | **Study Protocol** "Data Collection" parameter "Temporal Extent" |
| **supplementalInformation** | `supplementalinformation` | Additional free text | `Study.Description` or comment |
| **aggregationInfo** | `aggregationinfo` | Links to related datasets/papers | `Investigation.Publications` + README comment |

### 3. MD_Keywords (Keywords and Thesauri)

Descriptive keywords with optional thesaurus information.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **keyword** | `keywords[].name` | Keyword text | `OntologyAnnotation` (TAG) |
| **keyword@xlink:href** | `keywords[].url` | Keyword URI (if gmx:Anchor) | `OntologyAnnotation.TermAccessionNumber` |
| **type** | `type` | Keyword type (theme, place, temporal, etc.) | `OntologyAnnotation` comment or custom field |
| **thesaurusName** | `thesaurus['title']`, `thesaurus['url']`, `thesaurus['date']` | Source vocabulary (e.g., GEMET) | `OntologyAnnotation.TermSourceREF` |

### 4. CI_ResponsibleParty (Contacts)

Detailed contact information for persons and organizations.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **individualName** | `name` | Person name | `Person.LastName` (split to First/Last if possible) |
| **organisationName** | `organization` | Organization name | `Person.Affiliation` |
| **positionName** | `position` | Job title | `Person` comment or custom field |
| **contactInfo/phone** | `phone` | Telephone number | `Person.Phone` |
| **contactInfo/fax** | `fax` | Fax number | `Person.Fax` |
| **contactInfo/address** | `address`, `city`, `region`, `postcode`, `country` | Full postal address | `Person.Address` (formatted) |
| **contactInfo/electronicMailAddress** | `email` | Email address | `Person.Email` |
| **contactInfo/onlineResource** | `onlineresource` (CI_OnlineResource) | Website URL | `Person` comment (ORCID or website) |
| **role** | `role` | Role code (custodian, owner, author, etc.) | `Person.Roles` (via ontology mapping to NCIT terms) |

### 5. MD_Constraints (Legal and Security Constraints)

Access and use restrictions.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **useLimitation** | `uselimitation`, `uselimitation_url` | Usage limitations | **Investigation Comments** |
| **accessConstraints** | `accessconstraints` | Legal access restrictions (e.g., "restricted") | **Investigation Comments** |
| **useConstraints** | `useconstraints` | Legal use restrictions (e.g., "license") | **Investigation Comments** |
| **otherConstraints** | `otherconstraints`, `otherconstraints_url` | Other constraint text | **Investigation Comments** |
| **classification** | `classification` | Security classification | **Investigation Comments** |
| **securityConstraints** | `securityconstraints` | Security-specific constraints | **Investigation Comments** |

### 6. MD_Distribution (Distribution Information)

Information about how to obtain the dataset.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **distributionFormat/name** | `format`, `format_url` | Data format (GeoTIFF, Shapefile, etc.) | **Protocol** "Data Processing" parameter "Output Format" |
| **distributionFormat/version** | `version`, `version_url` | Format version | **Protocol** "Data Processing" parameter "Output Format" |
| **distributionFormat/specification** | `specification`, `specification_url` | Format specification | **Protocol** "Data Processing" parameter "Output Format" |
| **distributor/contact** | `distributor[].contact` | Distributor contact information | `Person` with role="distributor" |
| **transferOptions/onLine** | `online` (list of CI_OnlineResource) | Download/access URLs | **Assay Annotation Table** `Comment [Online Resource]` (semicolon-joined URLs) |

### 7. CI_OnlineResource (Online Resources)

URLs for data access, services, or documentation.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **linkage** | `url` | URL | **Assay Annotation Table** `Comment [Online Resource]` (or `Output [URI]` fallback) |
| **protocol** | `protocol`, `protocol_url` | Protocol (HTTP, FTP, OGC:WMS, etc.) | **Assay Annotation Table** `Comment [Online Resource Protocol]` (semicolon-joined; column omitted if all empty) |
| **name** | `name`, `name_url` | Resource name | **Assay Annotation Table** `Comment [Online Resource Name]` (semicolon-joined; column omitted if all empty) |
| **description** | `description`, `description_url` | Resource description | **Assay Annotation Table** `Comment [Online Resource Description]` (semicolon-joined; column omitted if all empty) |
| **function** | `function` | Function code (download, information, etc.) | **Assay Annotation Table** `Comment [Online Resource Function]` (semicolon-joined; column omitted if all empty) |

### 8. DQ_DataQuality (Data Quality)

Quality and conformance information.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **lineage/statement** | `lineage`, `lineage_url` | Lineage statement (provenance) | `Study.Description` and **Data Processing Protocol** parameter |
| **conformanceResult/specification** | `conformancetitle`, `conformancetitle_url` | INSPIRE/ISO specification title | **Protocol** "Data Processing" parameter "Conformance" |
| **conformanceResult/date** | `conformancedate`, `conformancedatetype` | Specification date | **Protocol** "Data Processing" parameter "Conformance" |
| **conformanceResult/pass** | `conformancedegree` | Pass/fail (true/false) | **Protocol** "Data Processing" parameter "Conformance" |

### 9. MD_ReferenceSystem (Coordinate Reference System)

Spatial reference system information.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **referenceSystemIdentifier/code** | `code`, `code_url` | CRS code (e.g., "EPSG:4326") | `Assay.TechnologyPlatform` or Protocol parameter |
| **referenceSystemIdentifier/codeSpace** | `codeSpace`, `codeSpace_url` | Authority (e.g., "EPSG") | Protocol parameter "CRS Authority" |
| **referenceSystemIdentifier/version** | `version`, `version_url` | CRS version | Protocol parameter "CRS Version" |

### 10. MI_AcquisitionInformation (Acquisition/Sensor Metadata)

Remote sensing specific: platform, instrument, operation metadata.

> [!NOTE]
> This is mapped via OWSLib `acquisition` attribute as an `MI_AcquisitionInformation` object. The exact structure depends on the metadata, but typically includes platform, instrument, operation, and event information.

**Proposed Mapping**: Create an **Assay Protocol** named "Sensor Acquisition" with parameters for:

- Platform name/type
- Instrument/sensor name/type
- Operation type/status
- Acquisition date/time

### 11. MD_ContentInfo (Feature Catalogue / Image Description)

Technical schema information for feature data or imagery.

> [!NOTE]
> Mapped via OWSLib `contentinfo` (list) as `MD_FeatureCatalogueDescription` or `MD_ImageDescription` objects.

**Proposed Mapping**: Create an **Assay Protocol** named:

- "Feature Catalogue" for vector data (with feature type names, attribute definitions)
- "Image Description" for raster data (with band information, cloud cover, etc.)

### 12. SV_ServiceIdentification (OGC Service Metadata)

Metadata specific to OGC web services (WMS, WFS, WCS, etc.).

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
| --- | --- | --- | --- |
| **serviceType** | `type` | Service type (WMS, WFS, CSW, etc.) | **No clear mapping** (see note) |
| **serviceTypeVersion** | `version` | Service version | **No clear mapping** (see note) |
| **fees** | `fees` | Cost information | Investigation comment |
| **couplingType** | `couplingtype` | How service couples to data | **No clear mapping** |
| **operations** | `operations` | Service operation metadata | **No clear mapping** |
| **operatesOn** | `operateson` | Datasets the service operates on | **No clear mapping** |

> [!IMPORTANT]
> **Service Metadata Consideration**: If this metadata denotes hierarchical metadata harvesting (upstream CSW source), it could be relevant for provenance. However, there is no clear ARC equivalent for OGC service-specific metadata. **Recommendation**: Document in Investigation comments if present, but do not create dedicated structures.

## Mapping Strategy Summary

### Investigation (Dataset Context)

- **Identifier**: fileIdentifier
- **Title**: citation/title
- **Description**: abstract + purpose
- **SubmissionDate**: dateStamp
- **Contacts**: All CI_ResponsibleParty objects (metadata contacts, creators, publishers, contributors) with appropriate roles
- **Publications**: Resource identifiers (DOIs, ISBNs) from citation/identifier and aggregationInfo
- **Comments/Remarks**:
  - All comments are stored as **Name/Value pairs** (using `Comment.create(name, value)`)
  - parentIdentifier (if hierarchy)
  - Metadata standard (name + version)
  - Language, charset, hierarchy level
  - Service metadata (if present)
  - Constraints (access, use, classification)

### Study (Research Unit / Data Processing Workflow)

One INSPIRE record = One Study representing the data creation workflow.

- **Identifier**: `[Investigation_ID]_study`
- **Title**: "Study for: " + [Investigation Title]
- **Description**: Lineage statement + purpose + supplementalInformation

**Process-Oriented Protocols**:

#### Protocol 1: "Spatial Sampling"

- **Input**: Geographic Region / Area of Interest
- **Output**: Selected Location(s)
- **Parameters**:
  - Bounding Box
  - Coordinate Reference System (CRS)
  - Spatial Resolution

#### Protocol 2: "Data Acquisition"

- **Input**: Selected Location(s)
- **Output**: Raw Sensor Data / Observations
- **Parameters**:
  - Platform/Sensor (from acquisition metadata)
  - Temporal Extent

#### Protocol 3: "Data Processing"

- **Input**: Raw Sensor Data
- **Output**: Processed/Published Dataset
- **Parameters**:
  - Lineage, Conformance, Output Format

### Assay (Measurement / Data Output)

- **Identifier**: `[Investigation_ID]_assay`
- **MeasurementType**: Derived from topicCategory with ontology mapping (e.g., "biota" → "Biological Measurement" [NCIT:C19026])
- **TechnologyType**: "Data Collection"
- **TechnologyPlatform**: `acquisitionInformation` (Satellite/Sensor platform)
- **Annotation Table** (always exactly one row):
  - **Input [Source Name]**: `"Dataset Source"`
  - **Output [URI]**: `dataSetURI` (preferred) → `online_resources[0].url` (fallback) → `"<slug>_dataset"` (last resort)
  - **Comment [Online Resource]**: semicolon-joined online-resource URLs (present only if any exist; first URL omitted when used as `Output [URI]` fallback)
  - **Comment [Online Resource Name]**: semicolon-joined resource names (omitted if all empty)
  - **Comment [Online Resource Protocol]**: semicolon-joined protocol codes (omitted if all empty)
  - **Comment [Online Resource Description]**: semicolon-joined descriptions (omitted if all empty)
  - **Comment [Online Resource Function]**: semicolon-joined function codes (omitted if all empty)
  - **Comment [Graphic Overview]**: semicolon-joined thumbnail URLs (present only if any exist)
- **Comments/Remarks**: none (all resource URLs live in the table)

### Person (Contacts)

Map all CI_ResponsibleParty objects with full details:

- **FirstName / LastName**: Split individualName if possible
- **Email**: electronicMailAddress
- **Phone / Fax**: contact phone/fax
- **Address**: Formatted from address, city, region, postcode, country
- **Affiliation**: organisationName
- **Roles**: Map role codes to ontology terms (via NCIT ontology mapping):
  - pointOfContact → NCIT:C70902 (Point of Contact)
  - author → NCIT:C70909 (Author)
  - publisher → NCIT:C70908 (Publisher)
  - custodian → NCIT:C70903 (Custodian)
  - distributor → NCIT:C70906 (Distributor)
  - originator → NCIT:C70907 (Originator)
  - principalInvestigator → NCIT:C70910 (Principal Investigator)
  - processor → NCIT:C70911 (Processor)
  - metadataContact → NCIT:C70912 (Metadata Contact)
- **Comments**: positionName, onlineResource (ORCID or website URL)

### OntologyAnnotation (Keywords)

- **AnnotationValue**: Keyword name
- **TermAccessionNumber**: Keyword URL (if gmx:Anchor)
- **TermSourceREF**: Thesaurus title/URI (e.g., "GEMET")
- **Comments**: Keyword type (theme, place, temporal, etc)

### Topic Category Ontology Mapping

INSPIRE topic categories are mapped to specific ontology terms for precise semantic annotation:

| Topic Category | Measurement Type | Ontology Term | Ontology Source |
| -------------- | ----------------- | ------------- | --------------- |
| biota | Biological Measurement | NCIT:C19026 | NCIT |
| boundaries | Boundary Measurement | NCIT:C19027 | NCIT |
| climatologyMeteorologyAtmosphere | Atmospheric Measurement | ENVO:01000818 | ENVO |
| economy | Economic Measurement | NCIT:C19029 | NCIT |
| elevation | Elevation Measurement | ENVO:00002001 | ENVO |
| environment | Environmental Measurement | ENVO:01000819 | ENVO |
| farming | Agricultural Measurement | AGRO:00000001 | AGRO |
| geoscientificInformation | Geoscientific Measurement | ENVO:01000820 | ENVO |
| health | Health Measurement | NCIT:C19034 | NCIT |
| imageryBaseMapsEarthCover | Remote Sensing Measurement | ENVO:01000817 | ENVO |
| inlandWaters | Hydrological Measurement | ENVO:01000821 | ENVO |
| intelligenceMilitary | Military Measurement | NCIT:C19037 | NCIT |
| location | Location Measurement | NCIT:C19038 | NCIT |
| oceans | Oceanographic Measurement | ENVO:00000015 | ENVO |
| planningCadastre | Cadastre Measurement | NCIT:C19040 | NCIT |
| society | Social Measurement | NCIT:C19041 | NCIT |
| structure | Structural Measurement | NCIT:C19042 | NCIT |
| transportation | Transportation Measurement | NCIT:C19043 | NCIT |
| utilitiesCommunication | Utility Measurement | NCIT:C19044 | NCIT |

> [!NOTE]
> Keywords are currently mapped as Investigation comments with ontology references (e.g., "keyword [GEMET]") due to limitations in the ARC OntologyAnnotation collection structure.

### Publication (Related Resources)

- Extract from citation/identifier (DOIs, ISBNs)
- Extract from aggregationInfo (related datasets/papers)
- **Title**: From citation or aggregationInfo
- **DOI**: Extracted from identifier
- **Comments**: Explain if from aggregationInfo (link to related dataset)

## Special Cases and Limitations

### 1. Hierarchy Level Handling

**hierarchyLevel**: The following hierarchy levels are handled specifically:

- **dataset** (default): Normal mapping to Investigation/Study/Assay
- **nonGeographicDataset**: Normal mapping, but without Spatial Sampling protocol
- **series, collection**: Currently ignored (will be implemented in future versions)
- **tile**: Ignored (spatial tiles are not harvested as individual datasets)
- **service, model, application**: Ignored (no scientific relevance)

> [!NOTE]
> Series and collection handling is planned for future implementation to support hierarchical dataset relationships.

### 2. Dataset URI and Lineage URL

**dataSetURI**: Mapped to `Output [URI]` column in the Assay Annotation Table (single row). If absent, the first `online_resources` URL is used as fallback; if that is also absent, a slug fallback (`<id>_dataset`) is used.

**lineage_url**: Added as parameter "Lineage Documentation URL" to Data Processing protocol.

### 3. Opaque Fields

**aggregationInfo**: OWSLib returns this as raw XML text. We will attempt to parse it for citations/identifiers, create Publications, and add a comment explaining the relationship.

### 4. Service Metadata

**SV_ServiceIdentification**: Primarily relevant for OGC web services. If present in a dataset record, it may indicate hierarchical metadata or linked services. We document this in Investigation comments but do not create dedicated ARC structures.

### 5. Complex Nested Structures

**acquisition** and **contentinfo**: These are complex nested objects. We map them as Assay Protocols with parameters extracted from the nested structure (platform name, sensor type, band information, etc.). The exact parameters depend on the metadata content.

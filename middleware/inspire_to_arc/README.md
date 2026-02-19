# INSPIRE to ARC Converter

This tool converts INSPIRE-compliant metadata (ISO 19139 XML) into ARC (ARChival Research & Data) objects.
It is designed to harvest metadata from GDI-DE (Geodateninfrastruktur Deutschland) and other INSPIRE-compatible catalogs via CSW (Catalogue Service for the Web).

## Usage Examples

### Basic Querying

```python
from middleware.inspire_to_arc.harvester import CSWClient

# Connect to GDI-DE CSW
client = CSWClient("https://gdk.gdi-de.org/gdi-de/srv/eng/csw")
client.connect()

# Fetch records
records = list(client.get_records(max_records=10))
```

### Advanced Filtering with FES

Use OWSLib's Filter Encoding Specification (FES) for readable, type-safe queries:

```python
from owslib.fes import And, PropertyIsEqualTo, PropertyIsLike

# Query for weather radar data from DWD
constraints = [
    And([
        PropertyIsLike("AnyText", "*radar*"),
        PropertyIsEqualTo("OrganisationName", "Deutscher Wetterdienst"),
    ])
]

records = list(client.get_records(constraints=constraints, max_records=100))
```

### Raw XML Queries

For complex queries, you can also use raw XML:

```python
xml_request = b"""<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                service="CSW" version="2.0.2">
  <csw:Query typeNames="csw:Record">
    <csw:ElementSetName>full</csw:ElementSetName>
  </csw:Query>
</csw:GetRecords>"""

records = list(client.get_records(xml_request=xml_request))
```

## Concept

The goal is to map geospatial metadata (INSPIRE) to the ISA (Investigation, Study, Assay) model used by ARC.
Since INSPIRE metadata describes *datasets* (results), while ARC describes the *research process* (investigation/study/assay), we apply the following mapping strategy:

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
|---|---|---|---|
| **fileIdentifier** | `identifier` | UUID of the metadata record | `Investigation.Identifier` |
| **parentIdentifier** | `parentidentifier` | Parent metadata record UUID (for hierarchies) | `Investigation.Description` (comment) |
| **language** | `language` / `languagecode` | Language of the metadata | `Investigation` comment/remark |
| **characterSet** | `charset` | Character encoding (UTF-8, etc.) | `Investigation` comment |
| **hierarchyLevel** | `hierarchy` | Scope: dataset, series, service, etc. | `Investigation` comment |
| **dateStamp** | `datestamp` / `datetimestamp` | When metadata was created/updated | `Investigation.SubmissionDate` |
| **metadataStandardName** | `stdname` | Standard name (ISO 19115, etc.) | `Investigation` comment (provenance) |
| **metadataStandardVersion** | `stdver` | Standard version | `Investigation` comment (provenance) |
| **dataSetURI** | `dataseturi` | Direct URI to the dataset | `Investigation` comment/remark |
| **contact** | `contact` | Metadata point of contact | `Investigation.Contacts` (Person with role="metadata_contact") |
| **referenceSystemInfo** | `referencesystem` | Coordinate Reference System (CRS) | Assay Technology Platform (e.g., "EPSG:4326") |
| **contentInfo** | `contentinfo` | Feature catalogue or image description | **Assay Protocol** "Feature Catalogue" or "Image Description" |
| **distributionInfo** | `distribution` | How to obtain the data | **Study/Assay Protocol** "Data Distribution" |
| **dataQualityInfo** | `dataquality` | Data quality and lineage | **Protocol** "Data Processing" (conformance as parameters) |
| **acquisitionInformation** | `acquisition` | Sensor/platform metadata (remote sensing) | **Assay Protocol** "Sensor Acquisition" |

### 2. MD_DataIdentification (Resource Identification)

Core descriptive metadata about the dataset.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **citation/title** | `title` | Dataset title | `Investigation.Title` |
| **citation/alternateTitle** | `alternatetitle` | Alternative title | `Investigation` comment |
| **citation/identifier** | `uricode`, `uricodespace` | Resource identifiers (DOI, ISBN, etc.) | `Investigation.Publications` (if DOI/ISBN) |
| **citation/date** | `date` (list of `CI_Date`) | Creation, publication, revision dates | **Study Protocol** parameter "Data Citation" |
| **citation/edition** | `edition` | Version/edition of the dataset | `Investigation` comment or `Study.Description` |
| **abstract** | `abstract` | Abstract/summary | `Investigation.Description` |
| **purpose** | `purpose` | Why the dataset was created | `Study.Description` (in addition to lineage) |
| **status** | `status` | Progress: completed, onGoing, planned, etc. | `Study` comment or Protocol parameter |
| **pointOfContact** | `contact`, `creator`, `publisher`, `contributor` | Resource contacts by role | `Investigation.Contacts` (Person) split by role |
| **graphicOverview** | `graphicoverview` | Thumbnail/preview image URLs | `Assay` comment/remark |
| **resourceConstraints** | Various constraint fields (see below) | Legal and security constraints | **Investigation Comments** |
| **spatialRepresentationType** | `spatialrepresentationtype` | Vector, grid, TIN, etc. | `Assay.TechnologyType` or comment |
| **spatialResolution** | `denominators`, `distance`, `uom` | Resolution (scale or distance) | **Study Protocol** "Spatial Resolution" with parameters |
| **language** | `resourcelanguage`, `resourcelanguagecode` | Language of the dataset | `Investigation` comment |
| **topicCategory** | `topiccategory` | ISO topic category (biota, environment, etc.) | `Assay.MeasurementType` (via ontology mapping) |
| **extent/geographicElement** | `bbox`, `boundingPolygon`, `description_code` | Spatial extent (bounding box or polygon) | **Study Protocol** "Data Collection" parameter "Spatial Extent" |
| **extent/temporalElement** | `temporalextent_start`, `temporalextent_end` | Temporal extent (start/end dates) | **Study Protocol** "Data Collection" parameter "Temporal Extent" |
| **supplementalInformation** | `supplementalinformation` | Additional free text | `Study.Description` or comment |
| **aggregationInfo** | `aggregationinfo` | Links to related datasets/papers | `Investigation.Publications` + README comment |

### 3. MD_Keywords (Keywords and Thesauri)

Descriptive keywords with optional thesaurus information.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **keyword** | `keywords[].name` | Keyword text | `OntologyAnnotation` (TAG) |
| **keyword@xlink:href** | `keywords[].url` | Keyword URI (if gmx:Anchor) | `OntologyAnnotation.TermAccessionNumber` |
| **type** | `type` | Keyword type (theme, place, temporal, etc.) | `OntologyAnnotation` comment or custom field |
| **thesaurusName** | `thesaurus['title']`, `thesaurus['url']`, `thesaurus['date']` | Source vocabulary (e.g., GEMET) | `OntologyAnnotation.TermSourceREF` |

### 4. CI_ResponsibleParty (Contacts)

Detailed contact information for persons and organizations.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **individualName** | `name` | Person name | `Person.LastName` (split to First/Last if possible) |
| **organisationName** | `organization` | Organization name | `Person.Affiliation` |
| **positionName** | `position` | Job title | `Person` comment or custom field |
| **contactInfo/phone** | `phone` | Telephone number | `Person.Phone` |
| **contactInfo/fax** | `fax` | Fax number | `Person.Fax` |
| **contactInfo/address** | `address`, `city`, `region`, `postcode`, `country` | Full postal address | `Person.Address` (formatted) |
| **contactInfo/electronicMailAddress** | `email` | Email address | `Person.Email` |
| **contactInfo/onlineResource** | `onlineresource` (CI_OnlineResource) | Website URL | `Person` comment (ORCID or website) |
| **role** | `role` | Role code (custodian, owner, author, etc.) | `Person.Roles` (via ontology mapping) |

### 5. MD_Constraints (Legal and Security Constraints)

Access and use restrictions.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **useLimitation** | `uselimitation`, `uselimitation_url` | Usage limitations | **Investigation Comments** |
| **accessConstraints** | `accessconstraints` | Legal access restrictions (e.g., "restricted") | **Investigation Comments** |
| **useConstraints** | `useconstraints` | Legal use restrictions (e.g., "license") | **Investigation Comments** |
| **otherConstraints** | `otherconstraints`, `otherconstraints_url` | Other constraint text | **Investigation Comments** |
| **classification** | `classification` | Security classification | **Investigation Comments** |
| **securityConstraints** | `securityconstraints` | Security-specific constraints | **Investigation Comments** |

### 6. MD_Distribution (Distribution Information)

Information about how to obtain the dataset.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **distributionFormat/name** | `format`, `format_url` | Data format (GeoTIFF, Shapefile, etc.) | **Protocol** "Data Processing" parameter "Output Format" |
| **distributionFormat/version** | `version`, `version_url` | Format version | **Protocol** "Data Processing" parameter "Output Format" |
| **distributionFormat/specification** | `specification`, `specification_url` | Format specification | **Protocol** "Data Processing" parameter "Output Format" |
| **distributor/contact** | `distributor[].contact` | Distributor contact information | `Person` with role="distributor" |
| **transferOptions/onLine** | `online` (list of CI_OnlineResource) | Download/access URLs | **Assay Comments** (Online Resources) |

### 7. CI_OnlineResource (Online Resources)

URLs for data access, services, or documentation.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **linkage** | `url` | URL | **Assay Comments** (Online Resources) |
| **protocol** | `protocol`, `protocol_url` | Protocol (HTTP, FTP, OGC:WMS, etc.) | **Assay Comments** (Online Resources) |
| **name** | `name`, `name_url` | Resource name | **Assay Comments** (Online Resources) |
| **description** | `description`, `description_url` | Resource description | **Assay Comments** (Online Resources) |
| **function** | `function` | Function code (download, information, etc.) | **Assay Comments** (Online Resources) |

### 8. DQ_DataQuality (Data Quality)

Quality and conformance information.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
| **lineage/statement** | `lineage`, `lineage_url` | Lineage statement (provenance) | `Study.Description` |
| **conformanceResult/specification** | `conformancetitle`, `conformancetitle_url` | INSPIRE/ISO specification title | **Protocol** "Data Processing" parameter "Conformance" |
| **conformanceResult/date** | `conformancedate`, `conformancedatetype` | Specification date | **Protocol** "Data Processing" parameter "Conformance" |
| **conformanceResult/pass** | `conformancedegree` | Pass/fail (true/false) | **Protocol** "Data Processing" parameter "Conformance" |

### 9. MD_ReferenceSystem (Coordinate Reference System)

Spatial reference system information.

| INSPIRE Field | OWSLib Attribute | Description | ARC Mapping |
|---|---|---|---|
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
|---|---|---|---|
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
- **Description**: abstract + purposepx
- **SubmissionDate**: dateStamp
- **Contacts**: All CI_ResponsibleParty objects (metadata contacts, creators, publishers, contributors) with appropriate roles
- **Publications**: Resource identifiers (DOIs, ISBNs) from citation/identifier and aggregationInfo
- **Comments/Remarks**:
  - parentIdentifier (if hierarchy)
  - dataSetURI
  - Metadata standard (name + version)
  - Language, charset, hierarchy level
  - Service metadata (if present)

### Study (Research Unit / Data Processing Workflow)

One INSPIRE record = One Study representing the data creation workflow.

- **Identifier**: `[Investigation_ID]_study`
- **Title**: "Study for: " + [Investigation Title]
- **Description**: Lineage statement + purpose + supplementalInformation

**Process-Oriented Protocols** (representing actual workflow steps):

#### Protocol 1: "Spatial Sampling" (if spatial information available)

Represents the selection of geographic location(s) for data collection.

- **Input**: Geographic Region / Area of Interest
- **Output**: Selected Location(s)
- **Parameters**:
  - Bounding Box (spatial_extent)
  - Spatial Resolution (denominators or distance + uom)
  - Geographic Description (if available)

#### Protocol 2: "Data Acquisition" (if acquisition metadata or temporal extent available)

Represents the actual data collection/sensing process.

- **Input**: Selected Location(s) + Temporal Period
- **Output**: Raw Sensor Data / Observations
- **Parameters**:
  - Platform (from acquisition metadata)
  - Sensor/Instrument (from acquisition metadata)
  - Temporal Extent (start/end dates)
  - Acquisition Dates (from dates with type="creation")
  - Image/Feature Description (from contentinfo if available)

#### Protocol 3: "Data Processing" (always created, from lineage)

Represents processing from raw data to final published dataset.

- **Input**: Raw Sensor Data (or previous output)
- **Output**: Processed/Published Dataset
- **Parameters**:
  - Lineage (processing description)
  - Quality/Conformance Results (specification, pass/fail)
  - Data Format (distribution format)
  - Processing Date (from dates with type="revision" or "publication")

**Metadata stored as Investigation/Study-level** (not as protocols):

- Constraints (access, use, classification) → Investigation Comments
- Distribution/Access Info → Investigation Comments or Study Description
- Reference Systems → Assay TechnologyPlatform

### Assay (Measurement / Data Output)

- **Identifier**: `[Investigation_ID]_assay`
- **MeasurementType**: Derived from topicCategory (e.g., "biota" → "Biological Measurement")
- **TechnologyType**: spatialRepresentationType (vector, raster, etc.) or "Spatial Data Acquisition"
- **TechnologyPlatform**: Reference system code (EPSG:4326, etc.) from reference_systems
- **Protocols**: Links to Study protocols (same workflow)
- **Comments/Remarks**:
  - graphicOverview (thumbnail URLs)
  - Online Resources (download URLs) for data access

### Person (Contacts)

Map all CI_ResponsibleParty objects with full details:

- **FirstName / LastName**: Split individualName if possible
- **Email**: electronicMailAddress
- **Phone / Fax**: contact phone/fax
- **Address**: Formatted from address, city, region, postcode, country
- **Affiliation**: organisationName
- **Roles**: Map role codes to ontology terms (custodian, owner, author, originator, publisher, etc.)
- **Comments**: positionName, onlineResource (ORCID or website URL)

### OntologyAnnotation (Keywords)

- **AnnotationValue**: Keyword name
- **TermAccessionNumber**: Keyword URL (if gmx:Anchor)
- **TermSourceREF**: Thesaurus title/URI (e.g., "GEMET")
- **Comments**: Keyword type (theme, place, temporal, etc.)

### Publication (Related Resources)

- Extract from citation/identifier (DOIs, ISBNs)
- Extract from aggregationInfo (related datasets/papers)
- **Title**: From citation or aggregationInfo
- **DOI**: Extracted from identifier
- **Comments**: Explain if from aggregationInfo (link to related dataset)

## Special Cases and Limitations

### 1. Opaque Fields

**aggregationInfo**: OWSLib returns this as raw XML text. We will attempt to parse it for citations/identifiers, create Publications, and add a comment explaining the relationship.

### 2. Service Metadata

**SV_ServiceIdentification**: Primarily relevant for OGC web services. If present in a dataset record, it may indicate hierarchical metadata or linked services. We document this in Investigation comments but do not create dedicated ARC structures.

### 3. Complex Nested Structures

**acquisition** and **contentinfo**: These are complex nested objects. We map them as Assay Protocols with parameters extracted from the nested structure (platform name, sensor type, band information, etc.). The exact parameters depend on the metadata content.

### 4. Multiple Language Support

**locales** (PT_Locale): OWSLib supports alternate languages. Currently not mapped to ARC, but could be added as Investigation comments if needed.

### 5. Bounding Polygons

**EX_BoundingPolygon**: More precise than bounding boxes. Currently we extract bounding boxes. Polygons could be serialized (e.g., WKT) and added as Protocol parameters if needed.

## Architecture

- **Source**: CSW (Catalogue Service for the Web) endpoint (e.g., GDI-DE).
- **Parser**: `OWSLib` for ISO 19139 XML.
- **Mapper**: Converts `InspireRecord` (Pydantic model) to `arctrl` objects.
- **Output**: ARC objects sent to the Middleware API (using `api_client`).

## Implementation Status

**Current**: ~10 fields mapped (basic identification, contacts, lineage, extent, constraints)

**Planned**: 50+ fields mapped with comprehensive protocol-based approach as documented above.

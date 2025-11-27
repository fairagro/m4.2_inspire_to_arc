# INSPIRE to ARC Converter

This tool converts INSPIRE-compliant metadata (ISO 19139 XML) into ARC (ARChival Research & Data) objects.
It is designed to harvest metadata from GDI-DE (Geodateninfrastruktur Deutschland) and other INSPIRE-compatible catalogs via CSW (Catalogue Service for the Web).

## Concept

The goal is to map geospatial metadata (INSPIRE) to the ISA (Investigation, Study, Assay) model used by ARC.
Since INSPIRE metadata describes *datasets* (results), while ARC describes the *research process* (investigation/study/assay), we apply the following mapping strategy:

### 1. Investigation (The Context)

The Investigation represents the overall context of the dataset.

- **Identifier**: `gmd:fileIdentifier` (UUID of the metadata record)
- **Title**: `gmd:identificationInfo/*/gmd:citation/*/gmd:title`
- **Description**: `gmd:identificationInfo/*/gmd:abstract`
- **Submission Date**: `gmd:dateStamp`
- **Contacts**: Mapped from `gmd:contact` and `gmd:pointOfContact`.
  - Roles like "author", "custodian", "owner" are preserved and mapped to ARC Person roles.

### 2. Study (The Research Unit)

We assume a 1:1 relationship: One INSPIRE Metadata Record = One Study within the Investigation.

- **Identifier**: `[Investigation_ID]_study`
- **Title**: "Study for: " + [Investigation Title]
- **Description**: `gmd:dataQualityInfo/*/gmd:lineage/gmd:statement` (Lineage).
  - The Lineage statement is crucial as it describes *how* the data was created (the "study" part).

### 3. Assay (The Measurement)

The Assay describes the specific measurement or data collection process.

- **Identifier**: `[Investigation_ID]_assay`
- **Measurement Type**: Derived from `gmd:topicCategory` or `gmd:descriptiveKeywords`.
  - Example: "biota" -> Ontology Term for Biological Measurement.
  - We will map INSPIRE Themes to specific Ontology Terms.
- **Technology Type**: "Spatial Data Acquisition" (Generic) or specific if available.
- **Protocols**: Derived from `gmd:processStep` in Lineage if available.

### 4. Person (Contacts)

INSPIRE distinguishes between "Metadata Contact" (`gmd:contact`) and "Resource Contact" (`gmd:pointOfContact`). Both will be mapped to ARC `Person` objects attached to the Investigation.

- **Name**: `gmd:individualName` (Split into First/Last Name if possible, otherwise Last Name).
- **Affiliation**: `gmd:organisationName`.
- **Email**: `gmd:contactInfo/*/gmd:electronicMailAddress`.
- **Address**: `gmd:contactInfo/*/gmd:address`.
- **Roles**: `gmd:role` (e.g., "custodian", "owner", "author") mapped to Ontology Terms.

### 5. Publication

External resources linked via `gmd:aggregationInfo` (e.g., related papers, cross-references) will be mapped to ARC `Publication` objects.

- **Title**: `gmd:citation/*/gmd:title`.
- **DOI**: Extracted from `gmd:citation` identifiers if available.

### 6. Linked Data (Ontologies)

INSPIRE relies heavily on thesauri (e.g., GEMET).

- **Keywords**: `gmd:descriptiveKeywords` are mapped to `OntologyAnnotation`.
- **URIs**: If `gmx:Anchor` is used, the URI (xlink:href) is preserved as the Term Accession Number/URI.

### 7. Extended Metadata (Protocols & Parameters)

Instead of generic comments, we will map extended metadata to structured **Protocols** and **Parameters** within the Study or Assay.

- **Spatial Extent**: Mapped to a "Data Collection" Protocol Parameter.
  - Parameter Name: "Spatial Extent" (Ontology Term)
  - Value: Bounding Box coordinates.
- **Temporal Extent**: Mapped to a "Data Collection" Protocol Parameter.
  - Parameter Name: "Temporal Extent" (Ontology Term)
  - Value: Date range.
- **Constraints**: Mapped to a "Data Governance" Protocol or directly as Investigation properties if applicable.
  - Parameter Name: "Access Constraints"
  - Value: Constraint text.
- **Maintenance**: Mapped to a Protocol Parameter.
  - Parameter Name: "Maintenance Frequency"
  - Value: Frequency code/text.

This approach leverages the ISA model's flexibility where Assays/Studies describe *processes* (Protocols) with specific *characteristics* (Parameters).

## Mapping Table

| INSPIRE Element | ARC Element | Logic |
|---|---|---|
| `fileIdentifier` | `Investigation.Identifier` | Direct mapping |
| `citation/title` | `Investigation.Title` | Direct mapping |
| `abstract` | `Investigation.Description` | Direct mapping |
| `dateStamp` | `Investigation.SubmissionDate` | Direct mapping |
| `contact` / `pointOfContact` | `Investigation.Contacts` (Person) | Map Name, Email, Org, Role |
| `lineage` | `Study.Description` | Describes history/processing |
| `topicCategory` | `Assay.MeasurementType` | Map "biota" -> "Biological measurement", etc. |
| `descriptiveKeywords` | `OntologyAnnotation` | Use `gmx:Anchor` for URI |
| `aggregationInfo` | `Investigation.Publications` | Linked resources |
| `resourceConstraints` | `Study.Protocol.Parameter` | Protocol: "Data Governance", Param: "Access Constraints" |
| `geographicElement` | `Study.Protocol.Parameter` | Protocol: "Data Collection", Param: "Spatial Extent" |

## Architecture

- **Source**: CSW (Catalogue Service for the Web) endpoint (e.g., GDI-DE).
- **Parser**: `OWSLib` or `lxml` for ISO 19139 XML.
- **Mapper**: Converts parsed XML to `arctrl` objects.
- **Output**: ARC objects sent to the Middleware API (using `api_client`).

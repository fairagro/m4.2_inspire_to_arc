# Implementation Plan: INSPIRE to ARC

## Goal
Implement a tool to harvest INSPIRE metadata from CSW endpoints (e.g., GDI-DE) and convert it to ARC objects for the Middleware API.

## User Review Required
- [ ] Confirm mapping of "Extended Metadata" to Comments.
- [ ] Confirm dependency on `OWSLib` for CSW interaction.

## Proposed Changes

### [NEW] Project Structure
#### [NEW] middleware/inspire_to_arc/pyproject.toml
- Dependencies: `OWSLib`, `lxml`, `arctrl`, `pydantic`.

### [NEW] Harvester Component
#### [NEW] middleware/inspire_to_arc/src/middleware/inspire_to_arc/harvester.py
- `CSWClient`: Connects to CSW, handles pagination, filters by query (optional).
- `ISOParser`: Parses ISO 19139 XML into a Pydantic model `InspireRecord`.

### [NEW] Mapper Component
#### [NEW] middleware/inspire_to_arc/src/middleware/inspire_to_arc/mapper.py
- `InspireMapper`:
    - `map_investigation(record) -> ArcInvestigation`
    - `map_study(record) -> ArcStudy`
    - `map_assay(record) -> ArcAssay`
    - `map_person(contact) -> Person`
    - `map_publication(citation) -> Publication`
    - `map_protocol(record) -> Protocol` (for extended metadata like Spatial/Temporal extent)

### [NEW] Main Application
#### [NEW] middleware/inspire_to_arc/src/middleware/inspire_to_arc/main.py
- CLI entry point.
- Loads config (CSW URL, API Client config).
- Orchestrates: Harvest -> Map -> Upload (via `ApiClient`).

## Verification Plan
### Automated Tests
- Unit tests for `ISOParser` with sample XMLs.
- Unit tests for `InspireMapper` with mock `InspireRecord` objects.
- Integration test with a mock CSW server (using `respx` or similar if possible, or just mocking `OWSLib`).

### Manual Verification
- Run against GDI-DE test endpoint.
- Verify created ARCs in the API.

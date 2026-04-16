# INSPIRE-to-ARC Mapping — Design

> All conceptual mapping decisions — why spatial elements become protocols, why online resources flatten into Assay tables — are documented in [docs/inspire_mapping.md](../../../../docs/inspire_mapping.md). This file captures only the architectural decisions made during implementation.

## Key Decisions

1. **Use `arctrl` objects directly, not intermediate dicts**
   — Building intermediate JSON/dict representations before serializing would require maintaining a parallel schema. Constructing `ArcInvestigation`, `ArcStudy`, `ArcAssay`, and `ArcTable` objects directly keeps the code as the single source of truth and allows type-checking to catch structural errors at development time.

2. **Hierarchy level controls which protocols are generated**
   — `nonGeographicDataset` has no spatial component, so the Spatial Sampling protocol is omitted for it. Hierarchy levels outside `["dataset", "series", "nonGeographicDataset"]` (service, tile, application, model) carry no scientific data content and are filtered out in the plugin before the mapper is called.

3. **OWSLib is dropped at the `CSWClient` boundary**
   — `InspireMapper` receives only `InspireRecord` (a fully typed Pydantic model). It never imports or inspects OWSLib types. This isolates the mapper from OWSLib API changes and keeps mapping logic testable without a live CSW connection.

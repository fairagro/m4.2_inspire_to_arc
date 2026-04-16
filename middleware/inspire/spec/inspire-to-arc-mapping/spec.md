# INSPIRE-to-ARC Mapping

Transforms the fully populated `InspireRecord` object into ARC investigation components (ISA).

**Authoritative Mapping Source:** [docs/inspire_mapping.md](../../../../docs/inspire_mapping.md) defines the conceptual mapping rules. This spec captures the implementation contract.

**Skill Reference:** Agents must load `.agents/skills/arctrl/SKILL.md` when writing or modifying code that constructs `ArcInvestigation`, `ArcStudy`, or `ArcAssay` objects.

## Requirements

- [ ] Map each `InspireRecord` to exactly one `ArcInvestigation` with title, description, contacts, publications, and ontology annotations as defined in the authoritative mapping source.
- [ ] Create one `ArcStudy` per record containing a Spatial Sampling protocol (omitted for `nonGeographicDataset`) and a Data Acquisition protocol.
- [ ] Create one `ArcAssay` per record containing a Data Processing protocol.
- [ ] Attach the raw ISO 19139 XML as a file named `iso19115.xml` inside the ARC.
- [ ] Serialize the resulting ARC via `arc.ToROCrateJsonString()` and return the JSON string.
- [ ] Skip the Spatial Sampling protocol when `record.hierarchy == "nonGeographicDataset"`.
- [ ] Skip records whose hierarchy is not in `["dataset", "series", "nonGeographicDataset"]`.

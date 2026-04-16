# CSW Harvesting

Query the Catalogue Service for Web (CSW) endpoints and parse ISO 19139 XML into the `InspireRecord` object.

## Requirements

- [ ] Connect securely to the configured `csw_url` and retrieve all available metadata records.
- [ ] Support four mutually exclusive query modes per call:
  - **standard** — no filter; paginated fetch of all records.
  - **cql_query** — CQL text filter (e.g. `AnyText LIKE '%agriculture%'`); paginated.
  - **fes_constraints** — list of OWSLib `OgcExpression` objects; paginated.
  - **xml_query** — raw `GetRecords` XML body passed through verbatim; no pagination.
- [ ] Enforce mutual exclusion: activating more than one query mode (combining call-site arguments with Config defaults) must raise `ValueError` immediately, before any network call.
- [ ] Fetch stable record identifiers before loading full ISO metadata to ensure consistent pagination across CSW servers.
- [ ] Parse ISO 19139 `MD_Metadata` into a fully typed `InspireRecord`, extracting: temporal extent, spatial resolution, contacts, reference formats, spatial extents, graphic overviews, and dataset URLs.
- [ ] Yield a `RecordProcessingError` for any record whose identifier cannot be aligned or whose XML cannot be parsed.

## Edge Cases

- Some CSW servers yield random identifiers under pagination; the stable identifier obtained in the pre-fetch step must override any such value.
- Broken XML responses or invalid attribute access → yield `RecordProcessingError`, continue iteration.
- `fes_constraints` has no Config-level equivalent because OWSLib `OgcExpression` objects are runtime-only and not YAML-serializable; it can only be supplied at call time.
- An XML query with an encoding declaration must be converted to `bytes` before being passed to OWSLib to avoid an lxml `Unicode strings with encoding declaration` error.

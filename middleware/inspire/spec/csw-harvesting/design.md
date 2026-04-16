# CSW Harvesting — Design

## Key Decisions

1. **Dual-pass stable ID mechanism (Dublin Core pre-fetch before full ISO fetch)**
   — Some CSW servers yield records in unpredictable order under pagination when sort order is ambiguous. By locking onto the Dublin Core identifier strings obtained in the first pass, mismatches between the pre-fetch and the full ISO response are detected; the record is skipped with a `RecordProcessingError` instead of silently producing wrong data.

2. **Yield `RecordProcessingError` instead of raising from the generator**
   — OWSLib fetching can throw arbitrary network and XML parse exceptions mid-iteration. Raising would terminate the entire generator and abort the harvest run. Yielding the error lets the orchestrator log it and continue to the next record, satisfying the failure-isolation principle.

3. **Convert `MD_Metadata` to `InspireRecord` immediately after parsing**
   — OWSLib returns `MD_Metadata` with attributes typed as `str | list | ElementMap`. Mapping to `InspireRecord` (a fully typed Pydantic model) at the boundary of `CSWClient` means `mapper.py` never has to deal with OWSLib internals or ambiguous types.

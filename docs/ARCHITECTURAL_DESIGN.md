# Architecture Documentation: INSPIRE-to-ARC Harvester

## 1. Overview

The INSPIRE-to-ARC Harvester is responsible for collecting geospatial metadata from INSPIRE-compliant CSW (Catalogue Service for the Web) endpoints and converting it into the **ARC (Annotated Research Context)** format.

## 2. Core Components

The middleware consists of three main layers:

1. **Orchestrator (main.py):** Manages the processing loop, configuration loading, and interaction with the API Client.
2. **Harvester (harvester.py):** Interactive layer with CSW endpoints using `owslib`. It parses ISO 19139 XML records into an internal `InspireRecord` Pydantic model.
3. **Mapper (mapper.py):** Specialized logic for translating INSPIRE/ISO fields into ARC objects (Investigation, Study, Assay) using `arctrl`.

---

## 3. Data Flow

1. **Discovery:** The `CSWClient` connects to the configured CSW URL and retrieves a list of metadata records (ISO 19139).
2. **Parsing:** `harvester.py` extracts relevant fields (Title, Abstract, Contacts, Dates, Spatial/Temporal Extents, Lineage, etc.) from the XML.
3. **Mapping:** `InspireMapper` takes the `InspireRecord` and builds an `ARC` object:
    * **Investigation:** Created from the main record metadata.
    * **Study:** Represents the research focus described in the record.
    * **Assay:** Describes the technical measurements (e.g., sensor types, platforms).
    * **Protocols:** Lineage and quality information are mapped to ISA protocols.
4. **Submission:** The `ApiClient` sends the generated ARC to the FAIRagro Middleware API using the single ARC interface (`create_or_update_arc`).

---

## 4. Performance & Scale

The current implementation is designed for simplicity and reliability:

* **Sequential Processing:** Records are processed one-by-one to ensure accurate error tracking and avoid overwhelming the target API.
* **Memory Efficiency:** Metadata records are streamed from the CSW endpoint.
* **Error Isolation:** Mapping or upload errors for a single record do not stop the entire harvesting process.

---

## 5. Design Decisions

| Requirement | Solution | Decision Rationale |
| :--- | :--- | :--- |
| **mTLS Auth** | `api_client` with httpx | Secure communication with Middleware API using client certificates. |
| **Data Validation** | Pydantic v2 | Robust validation of both configuration and harvested records. |
| **Standard Compliance** | ISO 19139 / INSPIRE | Focus on the most common geospatial metadata standard in Europe. |
| **Decoupled API** | External `api_client` | Maintenance of the API client is centralized in a separate repository. |

---

## 6. Future Enhancements

* **Parallel Processing:** If throughput becomes a bottleneck, the processing loop could be parallelized using `asyncio.gather` with limited concurrency.
* **Enhanced Filtering:** Implementing more complex CSW queries (FES/CQL) to harvest specific subsets of data.
* **Incremental Harvesting:** Support for `datestamp` based filtering to only fetch new or updated records.

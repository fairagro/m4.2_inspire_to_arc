# FAIRagro INSPIRE-to-ARC Middleware

This repository contains the INSPIRE-to-ARC harvesting middleware. It harvests geospatial metadata from INSPIRE-compliant CSW (Catalogue Service for the Web) endpoints and converts them into ARC objects, which are then uploaded to the FAIRagro Middleware API.

## Project Structure

- `middleware/inspire_to_arc`: The core harvesting and mapping logic.
- `api_client`: (External dependency) Client for communicating with the Middleware API.
- `shared`: (External dependency) Shared models and configuration bases.

## Documentation

Comprehensive documentation of the mapping strategy and usage can be found in [middleware/inspire_to_arc/README.md](middleware/inspire_to_arc/README.md).

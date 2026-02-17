# AGENTS.md - Instructions for AI Assistants

This file contains critical context about the FAIRagro INSPIRE-to-ARC Harvester project for AI assistants (GitHub Antigravity, Claude, etc.).

## 📋 Tech Stack

| Component | Version | Details |
| --------- | ------- | ------- |
| Python | 3.12+ | Primary language |
| CSW | 2.0.2 | Source protocol (Catalogue Service for the Web) |
| Docker | Latest | Containerization |
| uv | Latest | Python package manager |
| arctrl | Latest | ARC manipulation library |
| owslib | Latest | CSW client library |

## 📁 Project Structure

```text
middleware/
└── inspire_to_arc/        # INSPIRE to ARC harvester (Core logic)
    ├── src/middleware/inspire_to_arc/
    │   ├── main.py        # Entry point & processing loop
    │   ├── harvester.py   # CSW client and ISO 19139 parser
    │   ├── mapper.py      # INSPIRE to ARC mapping logic
    │   ├── config.py      # Configuration model
    │   └── errors.py      # Custom exceptions
    └── tests/
        ├── unit/          # Unit tests for mapper and harvester
        └── integration/   # Integration tests with real CSW endpoints
```

## 🔧 Important Commands

### Always use `uv` for Python

```bash
# Run tests for the harvester
uv run pytest middleware/inspire_to_arc/tests/ -v

# Install/Update all dependencies
uv sync --dev --all-packages
```

### Execution

```bash
# Run the harvester with a config file
uv run python -m middleware.inspire_to_arc.main -c config.yaml
```

## 📝 Key Implementation Details

### External Dependencies

This project depends on `shared` and `api_client` libraries, which are hosted in a separate repository (`m4.2_advanced_middleware_api`). They are included via `uv` workspace sources pointing to Git.

### INSPIRE-to-ARC Mapping (`middleware/inspire_to_arc/src/middleware/inspire_to_arc/mapper.py`)

**Purpose**: Transforms INSPIRE-compliant metadata (ISO 19139 XML) into standardized Annotated Research Context (ARC) objects using the `arctrl` library.

**Philosophy**:

- Every INSPIRE record is mapped to an ISA Investigation.
- Metadata is translated into Protocols, Parameters, and Ontology Annotations.
- Lineage information is preserved in Study and Assay descriptions.

### API Client Integration

The harvester uses the `api_client` to upload ARCs to the FAIRagro Middleware API.
**Note**: The current `api_client` does NOT support batching. ARCs are uploaded individually and sequentially using `client.create_or_update_arc`.

## 🧪 Testing Strategy

### Test Locations

- `middleware/inspire_to_arc/tests/unit/` - Isolated logic tests with mocked CSW records.
- `middleware/inspire_to_arc/tests/integration/` - End-to-end workflow tests using sample CSW endpoints.

## ✨ Code Quality Standards

Agents are expected to maintain high code quality by addressing issues reported by the project's configured tools: **Ruff, MyPy, Pylint, and Bandit**.

---

**Last Updated**: 2026-02-12
**Maintainer Notes**: This repository is the standalone INSPIRE harvester. It is decoupled from the main Middleware API.

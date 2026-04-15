# AGENTS.md - Instructions for AI Assistants

This file contains critical context about the FAIRagro Middleware Harvester project for AI assistants (GitHub Copilot, Google Antigravity, Claude, etc.).

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
.agents/
└── skills/                # Agent Skills (agentskills.io standard)
    ├── arctrl/            # arctrl Python library reference
    ├── config-wrapper/    # ConfigWrapper / ConfigBase pattern
    └── create-specifica-feature/  # How to create a new Specifica feature

docs/
└── ai_workflow.md         # AI agent workflow documentation

spec/                      # Project-level architecture & design
└── principles.md          # Project principles and foundation contract

middleware/
├── harvester/             # Central orchestrator and configuration
│   └── spec/              # Component-level architecture & design
│       ├── harvester-orchestration/  # Orchestration loop and plugin contract
│       ├── configuration/            # Config loading, env overrides, secrets
│       └── demo-environment/         # Local demo / deployment setup
├── inspire_to_arc/        # INSPIRE to ARC harvester (Core logic)
│   ├── spec/              # Component-level architecture & design
    │   ├── csw-harvesting/          # CSW connections and logic
    │   ├── inspire-to-arc-mapping/  # Mapping to ARC concepts
    │   ├── api-upload/              # API upload semantics
    │   └── workflow-execution/      # The processing loop
    ├── src/middleware/inspire_to_arc/
    │   ├── plugin.py      # Plugin generator (run_plugin AsyncGenerator)
    │   ├── csw_client.py  # CSW client and ISO 19139 parser
    │   ├── mapper.py      # INSPIRE to ARC mapping logic
    │   ├── models.py      # Pydantic domain models (InspireRecord, Contact, etc.)
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

# Run individual quality tools
uv run ruff check .
uv run ruff format .
uv run mypy middleware/inspire_to_arc/
uv run pylint middleware/inspire_to_arc/
uv run bandit -r middleware/inspire_to_arc/src/

# Install/Update all dependencies
uv sync --dev --all-packages
```

### Execution

```bash
# Run the harvester with a config file
uv run python -m middleware.inspire_to_arc.main -c config.yaml
```

## Architecture & Design

Before generating or modifying code, read the relevant spec folders.

**Project-level** (`spec/`) — cross-cutting concerns:

- **[`spec/principles.md`](spec/principles.md)** — Project principles and foundation contract (start here).

**Harvester component** (`middleware/harvester/spec/`) — orchestrator internals:

- **[`middleware/harvester/spec/harvester-orchestration/`](middleware/harvester/spec/harvester-orchestration/)** — Orchestration loop and plugin `AsyncGenerator` contract.
- **[`middleware/harvester/spec/configuration/`](middleware/harvester/spec/configuration/)** — Config loading, env overrides, secrets, and typed-config rules.
- **[`middleware/harvester/spec/demo-environment/`](middleware/harvester/spec/demo-environment/)** — Local demo / deployment setup.

**Component-level** (`middleware/inspire_to_arc/spec/`) — inspire_to_arc internals:

- **[`middleware/inspire_to_arc/spec/csw-harvesting/`](middleware/inspire_to_arc/spec/csw-harvesting/)** — Polling standard CSW endpoints and ISO 19139 batch fetching logic.
- **[`middleware/inspire_to_arc/spec/inspire-to-arc-mapping/`](middleware/inspire_to_arc/spec/inspire-to-arc-mapping/)** — Rules transforming InspireRecord to ArcInvestigation/Study/Assay/Protocols.

---

## 📝 Key Implementation Details

### External Dependencies

This project depends on `shared` and `api_client` libraries, which are hosted in a separate repository (`m4.2_advanced_middleware_api`). They are included via `uv` workspace sources pointing to Git.

### Plugin Architecture (`middleware/inspire_to_arc/src/middleware/inspire_to_arc/`)

**Purpose**: Transforms INSPIRE-compliant metadata (ISO 19139 XML) into standardized Annotated Research Context (ARC) objects using the `arctrl` library.

**Module responsibilities**:

- `plugin.py` — `run_plugin(config)` AsyncGenerator integration point; no CLI entry point.
- `csw_client.py` — `CSWClient` class; connects to CSW endpoints, paginates, parses ISO 19139 XML.
- `models.py` — Pydantic domain models (`InspireRecord`, `Contact`, etc.); imported by both `csw_client` and `mapper`.
- `mapper.py` — `InspireMapper`; maps `InspireRecord` → `ARC` (Investigation / Study / Assay).

**Philosophy**:

- Every INSPIRE record is mapped to an ISA Investigation.
- Metadata is translated into Protocols, Parameters, and Ontology Annotations.
- Lineage information is preserved in Study and Assay descriptions.

### API Client Integration

The central `harvester` uses the `api_client` to upload ARCs to the FAIRagro Middleware API. The inner plugins (`inspire_to_arc`) do not communicate with the API directly; they yield serialized ARCs.

## 🧪 Testing Strategy

### Test Locations

- `middleware/inspire_to_arc/tests/unit/` - Isolated logic tests with mocked CSW records.
- `middleware/inspire_to_arc/tests/integration/` - End-to-end workflow tests using sample CSW endpoints.

## ✨ Code Quality Standards

Agents are expected to maintain high code quality by addressing issues reported by the project's configured tools: **Ruff, MyPy, Pylint, and Bandit**.

- **Automatic Fixes**: Actively check for and fix code smells, warnings, and notices.
- **Real Fixes vs. Suppression**: Issues must be resolved with actual code changes. Using comments to suppress warnings (e.g., `# noqa`, `# type: ignore`, `# pylint: disable`) is an **option of last resort**.
- **When to Suppress**: Only suppress if a fix is technically impossible or would result in unnecessarily complex or unreadable code.

## 📚 File Modifications Pattern

When editing files:

1. **Always check current state** - Use file viewing tools to see current content.
2. **Review for quality** - Check the VS Code **Problems** tab.
3. **Format and test after changes** - Run `uv run ruff format .` to auto-format, then `uv run pytest` to verify.

---

**Last Updated**: 2026-04-14
**Maintainer Notes**: This repository is the standalone Middleware Harvester. It is decoupled from the main Middleware API.

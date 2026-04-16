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
│       └── configuration/            # Configuration file structure
├── inspire/        # INSPIRE to ARC harvester (Core logic)
│   ├── spec/              # Component-level architecture & design
    │   ├── csw-harvesting/          # CSW connections and logic
    │   ├── inspire-to-arc-mapping/  # Mapping to ARC concepts
    │   └── workflow-execution/      # The processing loop
    ├── src/middleware/inspire/
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
# Run tests
uv run pytest middleware/ -v

# Quality checks (all read config from pyproject.toml — see spec/principles.md)
uv run ruff format --check middleware/
uv run ruff check middleware/
uv run mypy middleware/
uv run pylint middleware/
uv run bandit -r middleware/ -c .bandit -ll

# Install/Update all dependencies
uv sync --dev --all-packages
```

### Execution

```bash
uv run python -m middleware.harvester.main -c config.yaml
```

## Architecture & Design

**Read [`spec/principles.md`](spec/principles.md) first.** It defines the plugin contract, module dependency rules, values, constraints, and code quality requirements. Do not restate what is there.

Before generating or modifying code, read the relevant spec folders:

**Project-level** (`spec/`) — cross-cutting concerns:

- **[`spec/principles.md`](spec/principles.md)** — Authoritative project principles (start here).
- **[`spec/error-handling/`](spec/error-handling/)** — Centralized exception hierarchy and generator yielding patterns.
- **[`spec/demo-environment/`](spec/demo-environment/)** — One-command local demo environment (mock API + harvester).

**Harvester component** (`middleware/harvester/spec/`) — orchestrator internals:

- **[`middleware/harvester/spec/harvester-orchestration/`](middleware/harvester/spec/harvester-orchestration/)** — Orchestration loop and plugin `AsyncGenerator` contract.
- **[`middleware/harvester/spec/configuration/`](middleware/harvester/spec/configuration/)** — Configuration file structure, plugin field typing, and mutual-exclusion validation.

**Component-level** (`middleware/inspire/spec/`) — inspire internals:

- **[`middleware/inspire/spec/csw-harvesting/`](middleware/inspire/spec/csw-harvesting/)** — Polling standard CSW endpoints and ISO 19139 batch fetching logic.
- **[`middleware/inspire/spec/inspire-to-arc-mapping/`](middleware/inspire/spec/inspire-to-arc-mapping/)** — Rules transforming InspireRecord to ArcInvestigation/Study/Assay/Protocols.

---

## 📝 Key Implementation Details

### External Dependencies

This project depends on `shared` and `api_client` libraries, which are hosted in a separate repository (`m4.2_advanced_middleware_api`). They are included via `uv` workspace sources pointing to Git.

## 📚 File Modifications Pattern

When editing files:

1. **Always check current state** - Use file viewing tools to see current content.
2. **Review for quality** - Check the VS Code **Problems** tab.
3. **Format and test after changes** - Run `uv run ruff format middleware/` to auto-format, then `uv run pytest` to verify.

---

**Last Updated**: 2026-04-16
**Maintainer Notes**: This repository is the standalone Middleware Harvester. It is decoupled from the main Middleware API.

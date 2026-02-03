# AGENTS.md - Instructions for AI Assistants

This file contains critical context about the FAIRagro SQL-to-ARC Converter project for AI assistants (GitHub Copilot, Claude, etc.).

## 📋 Tech Stack

| Component | Version | Details |
| --------- | ------- | ------- |
| Python | 3.12.12 | Primary language |
| PostgreSQL | 15.15 | Database |
| Docker | Latest | Containerization |
| Git LFS | 3.3.0+ | Large file storage |
| uv | Latest | Python package manager |
| arctrl | Latest | ARC manipulation library |

## 📁 Project Structure

```text
middleware/
└── sql_to_arc/            # SQL to ARC converter (Core logic)
    ├── src/middleware/sql_to_arc/
    │   ├── main.py        # Entry point
    │   ├── mapper.py      # Database to ARC mapping logic
    │   └── config.py      # Configuration model
    └── tests/
        ├── unit/          # Unit tests for mapper and business logic
        └── integration/   # Integration tests with database

scripts/
├── load-env.sh           # Environment setup (MAIN ENTRY POINT for hooks)
├── setup-git-lfs.sh      # Git LFS installation
├── quality-check.sh      # Run all quality checks (ruff, mypy, pylint, bandit)
├── quality-fix.sh        # Run auto-formatters (ruff)
└── git-hooks/            # Version-controlled hooks
    ├── pre-push          # Combined: Git LFS + pre-commit
    ├── post-checkout
    ├── post-commit
    └── post-merge

dev_environment/
├── start.sh              # Start Docker Compose (Postgres + Converter)
├── compose.yaml          # Docker services definition
└── config.yaml           # Development configuration for the converter
```

## 🔧 Important Commands

### Always use `uv` for Python

```bash
# Run tests for the converter
uv run pytest middleware/sql_to_arc/tests/ -v

# Run quality checks
./scripts/quality-check.sh

# Install all dependencies (including external shared/api_client via git)
uv sync --dev --all-packages
```

### Development Environment

```bash
# Start local database and run converter
cd dev_environment
./start.sh --build

# View logs
docker compose logs -f

# Cleanup
docker compose down
```

## 📝 Key Implementation Details

### External Dependencies

This project depends on `shared` and `api_client` libraries, which are hosted in a separate repository (`m4.2_advanced_middleware_api`). They are included via `uv` workspace sources pointing to Git.

### SQL-to-ARC Mapping (`middleware/sql_to_arc/src/middleware/sql_to_arc/mapper.py`)

**Purpose**: Transforms relational database rows into standardized Annotated Research Context (ARC) objects using the `arctrl` library.

**Features**:

- Mapping of Persons (Contacts) with JSON-encoded roles.
- Mapping of Publications.
- Metadata extraction for ISA (Investigation, Study, Assay) structures.
- CLI support: `--version` provides the current package version (via `importlib.metadata`).

### Git LFS Integration

**Setup Process**:

1. `scripts/load-env.sh` is sourced during development.
2. This script calls `scripts/setup-git-lfs.sh`.
3. Git LFS hooks are installed from `scripts/git-hooks/`.

**Files Tracked by LFS**: `*.sql` (configured in `.gitattributes`).

## 🐳 Docker Compose Services

```yaml
services:
  postgres:           # PostgreSQL database serving Edaphobase data
  db-init:            # Downloads and imports the Edaphobase SQL dump
  sql_to_arc:         # The converter component (this repo)
```

**Configuration**: `dev_environment/config.yaml`

- Connects to `postgres` service on port 5432.
- Uses `api_url` pointing to an external Middleware API if needed.

## 🧪 Testing Strategy

### Test Locations

- `middleware/sql_to_arc/tests/unit/` - Isolated logic tests.
- `middleware/sql_to_arc/tests/integration/` - End-to-end workflow tests.

### Running Tests with uv

```bash
# Run all tests
uv run pytest middleware/sql_to_arc/

# Run with coverage
uv run pytest --cov=middleware/sql_to_arc middleware/sql_to_arc/tests/
```

## 🔐 Security Notes

- DB passwords and API secrets should be managed via environment variables or `.env`.
- `client.key` is dynamically handled in container secrets (`tmpfs`).

## 📚 File Modifications Pattern

When editing files:

1. **Always check current state** - Use `read_file` to see current content.
2. **Review for quality** - Run `./scripts/quality-check.sh` before committing.
3. **Never modify `.git/` directly** - Use scripts instead.
4. **Test after changes** - Always run `uv run pytest`.

---

**Last Updated**: 2026-02-03
**Current Branch**: feature/workflow_fixes
**Maintainer Notes**: This repository is now decoupled from the main Middleware API. High-level architecture involves converting SQL views into ARC files.

# FAIRagro Middleware Harvester — Principles

## Foundation Contract

The authoritative contract for each harvesting plugin is the mapping document
in the respective component's `spec/` folder (e.g.
[middleware/inspire/spec/inspire-to-arc-mapping/](../middleware/inspire/spec/inspire-to-arc-mapping/)).
Each document defines the source metadata fields, how they map to ARC concepts,
and required/optional semantics. **All feature specs assume these documents as
given.** Feature specs do not restate mapping rules; they reference the relevant
spec when they need to cite a field or constraint.

The central orchestrator (`middleware/harvester`) never parses source-format
records directly. Each plugin owns its own parsing, modelling, and mapping logic
entirely.

## Purpose

Harvest metadata from heterogeneous external sources, translate the records into
the Annotated Research Context (ARC) format, and publish the results to the
FAIRagro Middleware API.

The system is built around a **plugin architecture**: each input format (currently
INSPIRE/CSW) is implemented as a self-contained async-generator plugin. The
central orchestrator loads a unified configuration, dispatches to the appropriate
plugins, consumes their ARC output, and uploads it to the API. Adding a new input
format means adding a new plugin — the orchestrator requires no changes.

## Values

**Correctness over speed** — Valid ARC output matters more than throughput.
If a record cannot be mapped cleanly it must fail with a clear error, not produce
silent garbage.

**Memory-safe by design** — Source endpoints can contain millions of records.
Each plugin must use pagination or streaming; the in-memory footprint per batch
must be bounded and predictable.

**Failure isolation** — One bad record must not abort the entire harvest run.
Plugins `yield` `HarvesterError` instances to the orchestrator instead of raising.
The orchestrator is solely responsible for logging and telemetry.

**Stateless harvest process** — The harvester stores no state between runs.
No cache, no lock files, no local database writes. The only persistent output is
what the Middleware API receives.

**Security by default** — Inputs from external sources (endpoints, API, config)
are treated as untrusted. Follow OWASP best practices: validate before use, fail
closed, apply least privilege.

## Constraints

- Python 3.12. No type-unsafe workarounds; all public APIs are fully typed.
- `uv` for dependency management. Never call `pip` directly in production code.
- `os.environ` must never be accessed directly; use `Config` / `ConfigWrapper`.
- Each plugin owns its source-format access exclusively. The orchestrator and
  other plugins must not reach into another plugin's internals.
- The plugin `AsyncGenerator` contract is `AsyncGenerator[str | HarvesterError, None]`.
  Plugins yield serialized ARC JSON strings on success and `HarvesterError`
  subclasses on record-level failures — never raise for expected failures.
- All plugin-specific exceptions inherit from `HarvesterError`
  (defined in `middleware.harvester.errors`).
- Code quality gates: Ruff (lint + format), mypy, pylint, bandit, pytest —
  all must pass before merge. Every new feature requires matching tests.
- **All quality tool invocations (VS Code, pre-commit, CI) must produce identical
  results.** This is achieved by having each tool read its configuration exclusively
  from a single shared config file — normally `pyproject.toml` (`[tool.ruff]`,
  `[tool.mypy]`, `[tool.pylint.*]`). Tools that cannot be configured via
  `pyproject.toml` (e.g. bandit) must have a dedicated config file (e.g. `.bandit`)
  shared by all invocations. Individual invocations must contain no extra CLI flags
  that override shared config; the only acceptable flags are those that cannot be
  expressed in a config file. The tool version used in every context must be the one
  locked in `uv.lock` — use `uv run <tool>` everywhere.
- No `noqa` / `type: ignore` suppressions unless technically unavoidable.
- Validation belongs in Pydantic models where possible. Use `Literal` types or
  `@field_validator` to enforce valid values — a `ValidationError` triggers the
  standard skip-with-yield-error path. Only write custom error code outside
  Pydantic when a spec violation should log a warning but NOT skip the record.

## Module Dependency Graph

```text
# Orchestrator
harvester/main.py  →  harvester/config.py
harvester/main.py  →  harvester/errors.py
harvester/main.py  →  <plugin>/plugin.py  (dynamic dispatch by plugin key)
harvester/main.py  →  api_client (shared lib)

# INSPIRE plugin (example; all plugins follow this pattern)
inspire/plugin.py  →  inspire/csw_client.py  →  inspire/models.py
inspire/plugin.py  →  inspire/mapper.py      →  inspire/models.py
inspire/plugin.py  →  inspire/config.py
inspire/plugin.py  →  harvester/errors.py

config  ←── all modules (read-only)
```

Circular imports are forbidden. Within a plugin, the mapper must not import the
source client and vice versa. Plugins must not import each other.

## Extension Points

| Need | Where to change |
| --- | --- |
| New input format / source type | Add a new plugin package under `middleware/`, implement `run_plugin(config) → AsyncGenerator` |
| New config value (orchestrator) | Extend `HarvesterConfig` in `middleware/harvester/config.py` |
| New config value (plugin) | Extend the plugin's `Config` class in its own `config.py` |
| New source field (existing plugin) | Add field to the plugin's record model, extract in client, map in mapper |
| New ARC structure | Add helper method to the plugin's mapper; reference arctrl skill |

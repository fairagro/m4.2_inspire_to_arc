# Harvester Error Handling

Defines a project-wide, standardized exception hierarchy for the core orchestrator and all harvesting plugins, as well as the paradigm of "yielding" errors to the orchestrator.

## Requirements

- [ ] Provide a central base exception class `HarvesterError` in `middleware.harvester.errors`.
- [ ] Provide a global `RecordProcessingError` inheriting from `HarvesterError` inside `middleware.harvester.errors` that standardizes errors containing record context strings (e.g. `record_id`, `record_url`).
- [ ] Ensure all plugin-specific base exceptions (e.g., `InspireError`) inherit directly from `HarvesterError`.
- [ ] Update the `AsyncGenerator` contract of plugins from `AsyncGenerator[str, None]` to `AsyncGenerator[str | HarvesterError, None]`.
- [ ] Plugins MUST NOT swallow or locally log expected record-level parsing or mapping failures. Instead, they must `yield` the `HarvesterError` to the orchestrator.
- [ ] Ensure the central orchestrator is fully responsible for consuming, interpreting, and logging the yielded `HarvesterError`s (or `RecordProcessingError`s), ensuring centralized telemetry and logging output.

# Harvester Orchestration

The central harvester acts as an orchestrator that loads a unified configuration, executes multiple pluggable `xxx_to_arc` components, and publishes the resulting ARCs to the FAIRagro Middleware API.

## Requirements

- [ ] Load a centralized configuration that inherits from `ConfigBase`.
- [ ] Parse a `repositories` list from the configuration, where each item is a single-key dict whose key is the plugin type (e.g., `inspire`) and whose value is the plugin-specific configuration object.
- [ ] Parse `api_client` settings globally within the harvester configuration, rather than within localized plugins.
- [ ] Instantiate and invoke the appropriate `xxx_to_arc` plugin based on the plugin type key in the repository configuration.
- [ ] Consume the output of each plugin via an `AsyncGenerator[str, None]` that yields serialized ARC representations (JSON strings).
- [ ] Upload the yielded ARCs to the target Remote Data Infrastructure (RDI) using the configured `api_client`.
- [ ] Handle plugin-level and record-level exceptions robustly, continuing to process remaining records and repositories upon failure.

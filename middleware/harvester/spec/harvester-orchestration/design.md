# Harvester Orchestration — Design

## Architecture

The project consists of a core orchestrator module (`middleware/harvester`) and several plugin modules (like `middleware/inspire_to_arc`). The orchestrator translates unified configuration into specific plugin invocations, completely separating the metadata extraction logic from the publishing logic.

## Key Decisions

1. **Decoupling data extraction into separate plugins**
   — Because different sources (e.g., CSW vs. Schema.org) employ fundamentally different fetching protocols and metadata standards, the specific fetch and map responsibilities stay inside isolated `xxx_to_arc` modules.

2. **Using an `AsyncGenerator` yielding JSON strings as the plugin interface**
   — We require plugins to yield serialized ARCs asynchronously to the orchestrator. This decouples the memory footprint of `arctrl` objects from the global upload step, enables the orchestrator to upload concurrently while the plugin fetches the next record, and ensures a uniform, purely text-based contract between the orchestrator and plugins.

3. **Moving `api_client` configuration to the Harvester core**
   — Individual plugins should not know about or be responsible for uploading data to the FAIRagro Middleware API. By lifting `api_client` into the central harvester configuration, we ensure single-point authentication, unified connection handling, and centralized error logging for all uploads.

4. **Keyed-map format for repository entries instead of `{type, config}`**
   — Each repository entry in the YAML is a single-key dict (`{plugin_type: {plugin_config}}`). This avoids the untyped `config` field that would otherwise require `dict[str, Any]`, and instead maps directly to a concrete Pydantic field per plugin type. Adding a future plugin is an additive change (new optional field on `RepositoryConfig`) with no schema ambiguity.

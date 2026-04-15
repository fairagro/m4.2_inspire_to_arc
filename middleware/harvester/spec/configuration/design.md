# Harvester Configuration — Design

## Key Decisions

1. **Strongly typed config classes over `dict[str, Any]`**
   — All `ConfigBase`/`BaseModel` subclasses use concrete types for every field. Where a field holds a plugin-specific config, the concrete config class (e.g., `InspireToArcConfig`) is used directly. This moves schema validation to startup rather than inside the processing loop, making invalid configurations fail fast with clear Pydantic error messages.

2. **Using `ConfigWrapper` and Pydantic models for the config parser over untyped `dict` loads**
   — Strongly typing configuration flags makes configuration a secure schema. Instead of validating at the usage site (like inside the loop), the app fails immediately on startup if an invalid config file is run.

3. **No environment variable bindings for passwords natively**
   — Security is deferred to `middleware.shared.config.config_base` or injected at runtime. By avoiding `os.environ` in component `config.py` files, the core codebase abstracts away whether it's running in Docker or natively.

4. **Treating `ApiClientConfig` as a passed-through block**
   — The `Config` parses an `api_client` map, but leaves its core interpretation to `middleware.api_client.config`. Harvester logic knows nothing of auth or retry delays directly.

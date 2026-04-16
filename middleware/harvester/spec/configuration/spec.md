# Harvester Configuration

Defines the structure of the harvester configuration file. The configuration
is validated at startup via Pydantic; an invalid config aborts the process
before any harvesting begins.

The top-level `Config` class follows the `ConfigWrapper / ConfigBase` pattern —
see skill [`config-wrapper`](../../../../.agents/skills/config-wrapper/SKILL.md).
Plugin configs (nested under each repository entry) are plain Pydantic `BaseModel`
subclasses; they are populated by the same YAML loading but do not extend `ConfigBase`.

## Requirements

- [ ] The configuration must contain exactly one `api_client` section.
- [ ] The configuration must contain a non-empty `repositories` list.
- [ ] Each repository entry must contain a shared `rdi` field (string, required).
- [ ] Each repository entry must contain exactly one plugin field (e.g. `inspire`); zero or two or more plugin fields are rejected with a validation error.
- [ ] Plugin field types are statically typed Pydantic models; no `dict[str, Any]` is used for plugin config.

## Edge Cases

Repository entry with no plugin field → `ValidationError` at startup, process aborts.

Repository entry with two plugin fields set → `ValidationError` at startup, process aborts.

Repository entry with an unrecognised key → Pydantic ignores extra fields by default; no silent data loss because `_PLUGIN_FIELDS` drives dispatch, not raw dict keys.

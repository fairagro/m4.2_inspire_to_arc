# Harvester Configuration — Design

## Structure

`Config` extends `ConfigBase` (see skill
[`config-wrapper`](../../../../.agents/skills/config-wrapper/SKILL.md))
and contains `api_client` and a list of `RepositoryConfig` entries. Each
`RepositoryConfig` holds shared fields (currently only `rdi`) and exactly one
optional plugin field whose Pydantic type is the plugin's own config model.

## Key Decisions

1. **Each plugin type is a named, typed optional field on `RepositoryConfig`**
   — The field name is the plugin key (e.g. `inspire`), the field type is the
   plugin's own Pydantic config model. This gives full static typing, IDE
   completion, and schema validation without any `dict[str, Any]` or string
   dispatch. Adding a future plugin requires three additive changes: one new
   optional field on `RepositoryConfig`, one entry in `_PLUGIN_FIELDS`
   (mutual-exclusion validation), and one entry in `_PLUGIN_RUNNERS` (dispatch).

2. **`_PLUGIN_FIELDS` class attribute as the authoritative set of mutually exclusive plugin fields**
   — `RepositoryConfig` carries a `ClassVar[frozenset[str]]` listing every optional
   plugin field by name. The `@model_validator` iterates only over that set when
   enforcing the "exactly one plugin key" invariant, rather than filtering `__dict__`
   or hardcoding non-plugin field names. This makes the intent explicit
   ("these fields are mutually exclusive") and keeps shared fields like `rdi` out of
   the validation logic entirely — adding a new shared field needs no validator change,
   and adding a new plugin field requires exactly one registration point
   (`_PLUGIN_FIELDS`) in addition to the field declaration itself.

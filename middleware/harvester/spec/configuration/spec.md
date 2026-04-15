# Harvester Configuration

The harvester relies on standard YAML configuration via the `ConfigWrapper` / `ConfigBase` pattern.

**Skill Reference:** Agents must load and follow [`.agents/skills/config-wrapper/SKILL.md`](../../../../.agents/skills/config-wrapper/SKILL.md) when extending or working with configuration.

## Requirements

- [ ] Load configuration from a specified YAML file (e.g., `-c config.yaml`).
- [ ] Expose `api_client` configuration natively at the root configuration level, passing it to the shared Middleware API library.
- [ ] Parse a `repositories` list where each entry is a single-key dict: the key is the plugin type (e.g., `inspire`) and the value is the plugin-specific configuration object.
- [ ] For `inspire` entries, the config value must be validated as `Config` from `middleware/inspire_to_arc/src/middleware/inspire_to_arc/config.py`.
- [ ] All config class fields must use concrete Pydantic types — `dict[str, Any]` or bare `Any` is forbidden.
- [ ] A `model_validator` on `RepositoryConfig` must enforce that exactly one plugin key is present per entry.

## Usage

No `os.environ` fallback is explicitly encoded in this layer — everything originates from the `ConfigWrapper` loading logic (inherited transparently from `middleware.shared.config.config_base`).

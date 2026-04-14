# Configuration

The harvester relies on standard YAML configuration via the `ConfigWrapper` / `ConfigBase` pattern.

**Skill Reference:** Agents must load and follow [`.agents/skills/config-wrapper/SKILL.md`](../../.agents/skills/config-wrapper/SKILL.md) when extending or working with configuration.

## Requirements

- [ ] Load configuration from a specified YAML file (e.g., `-c config.yaml`).
- [ ] Define settings for `csw_url` (where to harvest).
- [ ] Allow a `query` or `xml_request` for advanced CQL or raw XML query filtering.
- [ ] Expose `api_client` configurations natively, passing them over to the shared Middleware API library.
- [ ] Supply the target Research Data Infrastructure (RDI) identifier (`rdi`, default: `"inspire-import"`).

## Usage

No `os.environ` fallback is explicitly encoded in this layer—everything originates from the `ConfigWrapper` loading logic (inherited transparently from `middleware.shared.config.config_base`).

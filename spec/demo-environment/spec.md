# Demo Environment

Provide a one-command, self-contained local environment that demonstrates
the full INSPIRE-to-ARC pipeline end-to-end without requiring production
credentials or mTLS certificates.

## Requirements

- [ ] Start with a single command:
      `docker compose -f dev_environment/compose.demo.yaml up --build`
- [ ] Run a mock Middleware API (`middleware-api`) that accepts ARC RO-Crate
      uploads and writes them to a local `dev_environment/demo_output/` directory.
- [ ] Run the `harvester` against the public GeoNode demo CSW endpoint
      (`https://stable.demo.geonode.org/catalogue/csw`).
- [ ] Limit the harvest to 5 records via `max_records` so the demo completes quickly.
- [ ] Harvester exits 0 when all records are processed; compose exits with
      the harvester's exit code (`--exit-code-from harvester`).
- [ ] Written ARC files are accessible on the host via a bind-mounted
      `dev_environment/demo_output/` volume.
- [ ] File ownership of output files matches the host user (via
      `LOCAL_UID`/`LOCAL_GID` environment variables).
- [ ] No credentials, encrypted files, or mTLS certificates required.

## Out of Scope

Production credentials, sops-encrypted secrets, mTLS, and full-size CSW
harvesting are the responsibility of the dev environment (`compose.yaml`),
not this demo.

The demo requires outbound network access to the public GeoNode demo CSW
endpoint. No local CSW mock is provided.

## Edge Cases

ARC identifier in payload is unsafe (path traversal attempt) → mock API
falls back to a random ID, logs to console, does not write outside
`demo_output/`.

`demo_output/` doesn't exist → mock API creates it on first request.

CSW endpoint is unavailable → harvester exits non-zero with a clear log message
from the `ConnectionError` raised by `CSWClient.connect()`.

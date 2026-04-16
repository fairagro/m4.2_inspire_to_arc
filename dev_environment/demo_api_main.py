"""Demo API Mock for the FAIRagro INSPIRE-to-ARC harvester.

This module provides a lightweight FastAPI server that simulates the Middleware
API. It receives ARC RO-Crate payloads, deserialises them using the arctrl
library, and writes the resulting ARC directory structure to the local file
system.
"""

import json
import os
import re
import traceback
from datetime import UTC, datetime
from pathlib import Path

from arctrl import ARC
from arctrl.py.fable_modules.fable_library.async_ import start_as_task  # type: ignore[import-untyped]
from fastapi import FastAPI, Request

app = FastAPI()

# Root directory under which all ARC data and error logs are stored.
OUTPUT_ROOT = Path("/data/arcs")


def _get_target_owner() -> tuple[int, int] | None:
    uid_value = os.environ.get("LOCAL_UID")
    gid_value = os.environ.get("LOCAL_GID")
    if uid_value is None or gid_value is None:
        return None
    try:
        return int(uid_value), int(gid_value)
    except ValueError:
        print(f"Invalid LOCAL_UID/LOCAL_GID: {uid_value}/{gid_value}")
        return None


def _chown_tree(path: Path) -> None:
    owner = _get_target_owner()
    if owner is None or not path.exists():
        return
    uid, gid = owner

    def apply_ownership(target: Path) -> None:
        os.chown(target, uid, gid)

    apply_ownership(path)
    if path.is_dir():
        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            apply_ownership(root_path)
            for name in dirs:
                apply_ownership(root_path / name)
            for name in files:
                apply_ownership(root_path / name)


def _handle_error(arc_dir: Path, rdi: str, arc_id: str, exc: Exception) -> None:
    tb = traceback.format_exc()
    print(f"Error writing ARC for {rdi}/{arc_id} (dir={arc_dir}): {exc}\n{tb}")


# Pre-compiled pattern for safe ARC directory names (no path traversal, predictable charset).
_SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def _generate_random_arc_id() -> str:
    return f"arc_{os.urandom(4).hex()}"


def _derive_safe_arc_id(base_dir: Path, raw_id: object) -> tuple[str, Path]:
    """Derive a safe ARC identifier and corresponding directory path.

    Always returns a valid (arc_id, path) pair that is guaranteed to be
    contained within base_dir. Falls back to a random ID when the provided
    raw_id cannot be used safely.
    """
    # Resolve symlinks on the base directory once so all comparisons are stable.
    base_real = Path(os.path.realpath(base_dir))

    def _fallback() -> tuple[str, Path]:
        rid = _generate_random_arc_id()
        return rid, base_real / rid

    if not (isinstance(raw_id, str) and raw_id.strip()):
        return _fallback()

    safe_name = os.path.normpath(Path(raw_id.strip()).name)
    if not safe_name or safe_name in {".", ".."} or not _SAFE_NAME_PATTERN.match(safe_name):
        return _fallback()

    # Normalize with realpath and verify containment *before* returning the path.
    # This is the CodeQL-recommended pattern for preventing path traversal:
    # construct → realpath → startswith-check.
    candidate_real = Path(os.path.realpath(base_real / safe_name))
    if not str(candidate_real).startswith(str(base_real) + os.sep):
        return _fallback()

    return safe_name, candidate_real


@app.post("/v3/arcs")
async def upload_arc(request: Request) -> dict[str, object]:
    """Handle the submission of an ARC RO-Crate.

    Receives the RO-Crate JSON-LD payload as ``{"rdi": "...", "arc": {...}}``,
    validates it, and uses the arctrl library to reconstruct the ARC directory
    structure. Results are saved to the local ``demo_output`` volume.
    """
    data = await request.json()
    rdi: str = data.get("rdi", "unknown")
    arc_payload: dict = data.get("arc", data)

    output_path = OUTPUT_ROOT
    output_path.mkdir(parents=True, exist_ok=True)
    _chown_tree(output_path)

    now = datetime.now(UTC).isoformat()

    arc_id, arc_dir = _derive_safe_arc_id(output_path, arc_payload.get("identifier"))

    payload_path = arc_dir.with_suffix(".payload.json")
    with open(payload_path, "w", encoding="utf-8") as handle:
        json.dump(arc_payload, handle, indent=2)
    _chown_tree(payload_path)

    try:
        arc_json = json.dumps(arc_payload)
        arc = ARC.from_rocrate_json_string(arc_json)
        await start_as_task(arc.WriteAsync(str(arc_dir)))
        _chown_tree(arc_dir)
        print(f"Saved ARC structure for {rdi} as {arc_id} using arctrl")
    except (json.JSONDecodeError, OSError, RuntimeError) as exc:
        _handle_error(arc_dir, rdi, arc_id, exc)
    except Exception as exc:  # noqa: BLE001
        _handle_error(arc_dir, rdi, arc_id, exc)

    return {
        "arc_id": arc_id,
        "status": "created",
        "metadata": {
            "arc_hash": "demo_hash",
            "status": "ACTIVE",
            "first_seen": now,
            "last_seen": now,
        },
        "events": [],
    }


@app.get("/live")
def live() -> dict[str, str]:
    """Liveness probe for the demo API."""
    return {"status": "ok"}

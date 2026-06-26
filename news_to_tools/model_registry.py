from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import now, read_json, state_path, write_json

REGISTRY_FILE = "model-candidates.json"


def load(path: Path | None = None) -> dict[str, Any]:
    path = path or state_path(REGISTRY_FILE)
    data = read_json(path, {"version": 1, "models": {}})
    if not isinstance(data.get("models"), dict):
        raise ValueError(f"invalid model registry: {path}")
    return data


def save(data: dict[str, Any], path: Path | None = None) -> None:
    path = path or state_path(REGISTRY_FILE)
    write_json(path, data)


def add_candidate(
    data: dict[str, Any],
    model_id: str,
    *,
    source_url: str,
    requirements: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    record = {
        "id": model_id,
        "source_url": source_url,
        "requirements": requirements or [],
        "status": "candidate",
        "auto_route_allowed": False,
        "notes": notes,
        "created_at": now(),
        "updated_at": now(),
        "verification": [],
    }
    data["models"][model_id] = record
    return record


def verify(
    data: dict[str, Any],
    model_id: str,
    *,
    command: str,
    passed: bool,
    notes: str = "",
) -> None:
    record = data["models"][model_id]
    record.setdefault("verification", []).append(
        {"at": now(), "command": command, "passed": passed, "notes": notes}
    )
    record["updated_at"] = now()
    record["status"] = "verified" if passed else "candidate"
    record["auto_route_allowed"] = bool(passed)

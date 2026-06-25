from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import DEFAULT_STATE_DIR, now, read_json, write_json

DEFAULT_INCIDENTS = DEFAULT_STATE_DIR / "model-security-incidents.json"
VALID_SEVERITY = {"low", "medium", "high", "critical"}


def load(path: Path = DEFAULT_INCIDENTS) -> dict[str, Any]:
    data = read_json(path, {"version": 1, "incidents": []})
    if not isinstance(data.get("incidents"), list):
        raise ValueError(f"invalid incidents file: {path}")
    return data


def save(data: dict[str, Any], path: Path = DEFAULT_INCIDENTS) -> None:
    write_json(path, data)


def add(
    data: dict[str, Any],
    *,
    model: str,
    title: str,
    source_url: str = "",
    severity: str,
    mitigation: str,
) -> dict[str, Any]:
    if severity not in VALID_SEVERITY:
        raise ValueError(f"invalid severity: {severity}")
    record = {
        "id": f"{model}:{len(data['incidents']) + 1}",
        "model": model,
        "title": title,
        "source_url": source_url,
        "severity": severity,
        "mitigation": mitigation,
        "created_at": now(),
        "route_allowed": severity in {"low", "medium"},
    }
    data["incidents"].append(record)
    return record


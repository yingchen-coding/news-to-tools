from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import DEFAULT_STATE_DIR, now, read_json, write_json

DEFAULT_POLICY = DEFAULT_STATE_DIR / "team-policy.json"


def load(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    data = read_json(path, {"version": 1, "contexts": {}})
    if not isinstance(data.get("contexts"), dict):
        raise ValueError(f"invalid team policy: {path}")
    return data


def save(data: dict[str, Any], path: Path = DEFAULT_POLICY) -> None:
    write_json(path, data)


def add_context(
    data: dict[str, Any],
    name: str,
    *,
    owner: str,
    memory_path: str,
    token_budget: int,
    tools: list[str] | None = None,
    repos: list[str] | None = None,
) -> dict[str, Any]:
    record = {
        "name": name,
        "owner": owner,
        "memory_path": memory_path,
        "monthly_token_budget": token_budget,
        "tokens_used": 0,
        "allowed_tools": sorted(set(tools or [])),
        "allowed_repos": sorted(set(repos or [])),
        "created_at": now(),
        "updated_at": now(),
    }
    data["contexts"][name] = record
    return record


def check_access(context: dict[str, Any], *, tool: str = "", repo: str = "") -> tuple[bool, str]:
    if tool and tool not in context.get("allowed_tools", []):
        return False, f"tool not allowed: {tool}"
    if repo and repo not in context.get("allowed_repos", []):
        return False, f"repo not allowed: {repo}"
    if not tool and not repo:
        return False, "at least one access target is required"
    return True, "allowed"


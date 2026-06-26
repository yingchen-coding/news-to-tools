from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .utils import now, read_json, slug, state_path, write_json

VALID_STATUS = {"queued", "running", "blocked", "review", "done", "dropped"}
WORKBOARD_FILE = "workboard.json"


@dataclass
class Task:
    title: str
    source: str = ""
    source_url: str = ""
    status: str = "queued"
    priority: int = 3
    acceptance: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def record(self) -> dict[str, Any]:
        if self.status not in VALID_STATUS:
            raise ValueError(f"invalid status: {self.status}")
        stamp = now()
        return {
            "id": slug(self.title),
            "title": self.title,
            "source": self.source,
            "source_url": self.source_url,
            "status": self.status,
            "priority": self.priority,
            "acceptance": self.acceptance,
            "evidence": self.evidence,
            "artifacts": self.artifacts,
            "blockers": self.blockers,
            "created_at": stamp,
            "updated_at": stamp,
            "history": [{"at": stamp, "event": "created", "status": self.status}],
        }


def load(path: Path | None = None) -> dict[str, Any]:
    path = path or state_path(WORKBOARD_FILE)
    data = read_json(path, {"version": 1, "tasks": []})
    if not isinstance(data.get("tasks"), list):
        raise ValueError(f"invalid workboard: {path}")
    return data


def save(data: dict[str, Any], path: Path | None = None) -> None:
    path = path or state_path(WORKBOARD_FILE)
    write_json(path, data)


def add_task(data: dict[str, Any], task: Task) -> dict[str, Any]:
    record = task.record()
    existing = {item.get("id") for item in data["tasks"] if isinstance(item, dict)}
    base = record["id"]
    suffix = 2
    while record["id"] in existing:
        record["id"] = f"{base}-{suffix}"
        suffix += 1
    data["tasks"].append(record)
    return record


def set_status(task: dict[str, Any], status: str, details: str = "") -> None:
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status: {status}")
    task["status"] = status
    stamp = now()
    task["updated_at"] = stamp
    entry = {"at": stamp, "event": "status", "status": status}
    if details:
        entry["details"] = details
    task.setdefault("history", []).append(entry)


def find_task(data: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in data["tasks"]:
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    raise KeyError(f"task not found: {task_id}")


def render(data: dict[str, Any]) -> str:
    tasks = sorted(data["tasks"], key=lambda item: (item.get("priority", 9), item.get("id", "")))
    if not tasks:
        return "No tasks."
    lines = []
    for task in tasks:
        lines.append(f"{task['id']} [{task['status']}] p{task['priority']} {task['title']}")
        if task.get("blockers"):
            lines.append(f"  blocker: {task['blockers'][-1]}")
    return "\n".join(lines)

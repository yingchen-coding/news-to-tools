from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import workboard

DEFAULT_ACTIONABLE_STATUSES = {"", "new", "queued", "todo", "pending", "latest", "urgent", "hot"}
TITLE_FIELDS = ("title", "title_ocr", "headline", "name")
URL_FIELDS = ("source_url", "url", "article_url", "link")


def import_queue(
    path: Path,
    *,
    include_statuses: set[str] | None = None,
    source: str = "queue-import",
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = _items_from_payload(payload)
    included_statuses = include_statuses or DEFAULT_ACTIONABLE_STATUSES
    data = workboard.load()
    imported = []
    existing = []
    skipped = 0

    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        item_status = str(item.get("status") or "").lower()
        if item_status not in included_statuses:
            skipped += 1
            continue
        title = _first_text(item, TITLE_FIELDS)
        if not title:
            skipped += 1
            continue
        task_title = f"Implement article: {title}"
        source_url = _first_text(item, URL_FIELDS)
        duplicate = workboard.find_existing_task(
            data,
            title=task_title,
            source_url=source_url,
        )
        if duplicate is not None:
            existing.append(duplicate)
            continue
        task = workboard.Task(
            title=task_title,
            source=str(item.get("source") or source),
            source_url=source_url,
            status="queued",
            priority=_priority(item),
            acceptance=[
                "Article claim is verified against a source before implementation.",
                "Implementation produces concrete local behavior, not just a summary.",
                "Validation command or evidence artifact is recorded.",
            ],
            evidence=_evidence(item),
        )
        imported.append(workboard.add_task(data, task))

    workboard.save(data)
    return {
        "source_file": path.name,
        "items": len(items),
        "imported": len(imported),
        "existing": len(existing),
        "skipped": skipped,
        "task_ids": [item["id"] for item in imported],
        "existing_task_ids": [item["id"] for item in existing],
    }


def _items_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("queue JSON must be an object or list")
    for key in ("items", "queue", "cards", "articles"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ValueError("queue JSON object must contain items, queue, cards, or articles")


def _first_text(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _priority(item: dict[str, Any]) -> int:
    raw = item.get("priority")
    if isinstance(raw, int):
        return min(max(raw, 1), 5)
    if isinstance(raw, str) and raw.strip().isdigit():
        return min(max(int(raw), 1), 5)
    status = str(item.get("status") or "").lower()
    if status in {"latest", "urgent", "hot"}:
        return 1
    return 3


def _evidence(item: dict[str, Any]) -> list[str]:
    evidence = []
    for field in ("source_url", "url", "article_url", "link"):
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            evidence.append(value.strip())
            break
    for field in ("summary", "notes", "why"):
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            evidence.append(value.strip())
    return evidence

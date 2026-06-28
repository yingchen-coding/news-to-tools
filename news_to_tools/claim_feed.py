from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import claim_diligence

TITLE_FIELDS = ("title", "headline", "name", "title_ocr")
URL_FIELDS = ("source_url", "url", "article_url", "link")
SUMMARY_FIELDS = ("summary", "notes", "why")
MODEL_TERMS = (
    "GPT",
    "Claude",
    "Fable",
    "GLM",
    "Gemma",
    "DeepSeek",
    "Gemini",
    "Cursor",
    "Kimi",
    "Qwen",
    "Llama",
    "Mistral",
    "Grok",
    "Seed",
)


def import_claim_feed(
    path: Path,
    *,
    feed: str = "model_claim_diligence_feed",
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = _claim_items(payload, feed)
    data = claim_diligence.load()
    imported = 0
    updated = 0
    skipped = 0
    claim_ids: list[str] = []

    existing_ids = {
        str(raw.get("id"))
        for raw in data.get("claims", [])
        if isinstance(raw, dict) and raw.get("id")
    }
    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        title = _first_text(item, TITLE_FIELDS)
        if not title:
            skipped += 1
            continue
        record = _record_from_item(item, title)
        stored = claim_diligence.upsert(data, record)
        claim_ids.append(stored["id"])
        if stored["id"] in existing_ids:
            updated += 1
        else:
            imported += 1
            existing_ids.add(stored["id"])

    claim_diligence.save(data)
    return {
        "source_file": path.name,
        "feed": feed,
        "items": len(items),
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "claim_ids": claim_ids,
    }


def _claim_items(payload: Any, feed: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("claim feed JSON must be an object or list")
    product_ideas = payload.get("product_ideas")
    if isinstance(product_ideas, dict):
        selected = product_ideas.get(feed)
        if isinstance(selected, dict) and isinstance(selected.get("items"), list):
            return selected["items"]
    for key in ("claims", "items", "queue", "cards", "articles"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ValueError("claim feed JSON does not contain a supported item list")


def _record_from_item(item: dict[str, Any], title: str) -> claim_diligence.ClaimRecord:
    summary = _first_text(item, SUMMARY_FIELDS)
    source_url = _first_text(item, URL_FIELDS)
    claim_type = _claim_type(title, summary)
    return claim_diligence.make_record(
        subject=_subject(title, summary),
        domain=_domain(claim_type),
        claim_type=claim_type,
        claim=_claim_text(title, summary),
        source_url=source_url,
        benchmark="",
        cost_evidence="",
        safety_evidence="",
        reproduction_evidence="",
        adoption_evidence="",
        risk=_risk(claim_type, title, summary),
        status="needs-review",
    )


def _claim_type(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(term in text for term in ("token", "price", "cost", "成本", "价格", "买单", "费用")):
        return "cost"
    if any(term in text for term in ("安全", "攻击", "封号", "jailbreak", "risk", "ban")):
        return "security"
    if any(term in text for term in ("benchmark", "实测", "榜", "超过", "追近", "wins", "beats")):
        return "benchmark"
    if any(term in text for term in ("发布", "上线", "release", "launch", "开源")):
        return "release"
    if any(term in text for term in ("企业", "adoption", "用户", "逃离", "客户")):
        return "adoption"
    if any(term in text for term in ("发疯", "failure", "失控", "事故")):
        return "safety"
    return "demo"


def _domain(claim_type: str) -> str:
    if claim_type in {"security", "safety"}:
        return "security"
    if claim_type == "cost":
        return "cost"
    return "model"


def _risk(claim_type: str, title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if claim_type in {"security", "safety"}:
        return "high"
    if any(term in text for term in ("medical", "癌症", "诊断", "clinical")):
        return "high"
    if claim_type in {"benchmark", "cost", "adoption"}:
        return "medium"
    return "low"


def _subject(title: str, summary: str) -> str:
    text = f"{title} {summary}"
    for term in MODEL_TERMS:
        match = re.search(rf"\b{re.escape(term)}[A-Za-z0-9_.-]*\b", text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    cleaned = re.sub(r"\s+", " ", title).strip()
    return f"Model claim: {cleaned[:60]}"


def _claim_text(title: str, summary: str) -> str:
    if summary:
        return f"{title}\n\n{summary}"
    return title


def _first_text(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""

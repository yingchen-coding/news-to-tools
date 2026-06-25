from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .utils import DEFAULT_STATE_DIR, now, read_json, write_json

DEFAULT_CLAIMS = DEFAULT_STATE_DIR / "medical-ai-claims.json"
HIGH_RISK_TERMS = {
    "诊断",
    "用药",
    "影像",
    "病历",
    "癌",
    "doctor",
    "clinical",
    "diagnosis",
    "medication",
}


def load(path: Path = DEFAULT_CLAIMS) -> dict[str, Any]:
    data = read_json(path, {"version": 1, "claims": []})
    if not isinstance(data.get("claims"), list):
        raise ValueError(f"invalid claims file: {path}")
    return data


def save(data: dict[str, Any], path: Path = DEFAULT_CLAIMS) -> None:
    write_json(path, data)


def assess(
    title: str,
    *,
    source_url: str,
    text: str,
    independent_validation: bool = False,
) -> dict[str, Any]:
    lowered = text.lower()
    high_risk = any(term.lower() in lowered or term in text for term in HIGH_RISK_TERMS)
    rates = re.findall(r"\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(?:亿|万)?次", text)
    allowed = bool(high_risk and source_url and independent_validation)
    return {
        "title": title,
        "source_url": source_url,
        "created_at": now(),
        "high_risk_medical_domain": high_risk,
        "reported_rates": rates,
        "independent_validation": independent_validation,
        "local_clinical_use_allowed": allowed,
        "decision": "review-required" if allowed else "blocked",
    }

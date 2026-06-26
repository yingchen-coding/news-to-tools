from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .utils import now, read_json, slug, state_path, write_json

CLAIMS_FILE = "ai-claims.json"

VALID_DOMAINS = {
    "agent",
    "coding",
    "cost",
    "enterprise",
    "hiring",
    "medical",
    "model",
    "open-source",
    "physical",
    "security",
    "other",
}
VALID_CLAIM_TYPES = {
    "adoption",
    "architecture",
    "benchmark",
    "cost",
    "dataset",
    "demo",
    "deployment",
    "hiring",
    "productivity",
    "release",
    "safety",
    "security",
}
VALID_RISKS = {"low", "medium", "high", "critical"}
VALID_STATUS = {"needs-review", "tracking", "rejected", "validated"}
HIGH_RISK_DOMAINS = {"medical", "physical", "security"}
HIGH_RISK_CLAIMS = {"deployment", "safety", "security"}


@dataclass(frozen=True)
class ClaimRecord:
    id: str
    subject: str
    domain: str
    claim_type: str
    claim: str
    source_url: str
    benchmark: str = ""
    deployment_evidence: str = ""
    safety_evidence: str = ""
    cost_evidence: str = ""
    reproduction_evidence: str = ""
    adoption_evidence: str = ""
    risk: str = "medium"
    status: str = "needs-review"
    recommendation: str = "verify-first"
    missing_evidence: list[str] | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["missing_evidence"] = self.missing_evidence or []
        stamp = now()
        data["created_at"] = self.created_at or stamp
        data["updated_at"] = self.updated_at or stamp
        return data


@dataclass(frozen=True)
class Finding:
    code: str
    record_id: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load(path: Path | None = None) -> dict[str, Any]:
    path = path or state_path(CLAIMS_FILE)
    data = read_json(path, {"version": 1, "claims": []})
    if not isinstance(data.get("claims"), list):
        raise ValueError(f"invalid AI claims file: {path}")
    return data


def save(data: dict[str, Any], path: Path | None = None) -> None:
    path = path or state_path(CLAIMS_FILE)
    write_json(path, data)


def infer_risk(domain: str, claim_type: str, *, safety_evidence: str = "") -> str:
    if domain == "medical" and claim_type in {"deployment", "safety", "productivity"}:
        return "critical"
    if claim_type in {"safety", "security"} and not safety_evidence.strip():
        return "critical"
    if domain in HIGH_RISK_DOMAINS and claim_type in HIGH_RISK_CLAIMS:
        return "high"
    if claim_type in {"benchmark", "cost", "adoption", "productivity"}:
        return "medium"
    return "low"


def required_evidence(raw: dict[str, Any]) -> list[str]:
    claim_type = str(raw.get("claim_type", "")).strip()
    domain = str(raw.get("domain", "")).strip()
    risk = str(raw.get("risk", "")).strip()
    missing: list[str] = []

    if claim_type == "benchmark" and not _present(raw, "benchmark", "reproduction_evidence"):
        missing.append("benchmark or reproduction_evidence")
    if claim_type == "deployment" and not _present(raw, "deployment_evidence"):
        missing.append("deployment_evidence")
    if claim_type == "cost" and not _present(raw, "cost_evidence"):
        missing.append("cost_evidence")
    if claim_type == "adoption" and not _present(raw, "adoption_evidence", "deployment_evidence"):
        missing.append("adoption_evidence or deployment_evidence")
    if domain in HIGH_RISK_DOMAINS and not _present(raw, "safety_evidence"):
        missing.append("safety_evidence")
    if risk in {"high", "critical"} and not _present(
        raw, "reproduction_evidence", "safety_evidence"
    ):
        missing.append("reproduction_evidence or safety_evidence")
    return missing


def recommendation_for(raw: dict[str, Any]) -> str:
    missing = required_evidence(raw)
    source_url = str(raw.get("source_url", "")).strip()
    risk = str(raw.get("risk", "")).strip()
    status = str(raw.get("status", "")).strip()
    if not source_url.startswith(("https://", "http://")):
        return "reject"
    if missing:
        return "verify-first"
    if status == "validated" and risk in {"low", "medium"}:
        return "implement"
    return "track"


def make_record(
    *,
    subject: str,
    domain: str,
    claim_type: str,
    claim: str,
    source_url: str,
    benchmark: str = "",
    deployment_evidence: str = "",
    safety_evidence: str = "",
    cost_evidence: str = "",
    reproduction_evidence: str = "",
    adoption_evidence: str = "",
    risk: str = "",
    status: str = "needs-review",
) -> ClaimRecord:
    domain = domain.strip()
    claim_type = claim_type.strip()
    if domain not in VALID_DOMAINS:
        raise ValueError(f"invalid domain {domain!r}; expected one of {sorted(VALID_DOMAINS)}")
    if claim_type not in VALID_CLAIM_TYPES:
        raise ValueError(
            f"invalid claim_type {claim_type!r}; expected one of {sorted(VALID_CLAIM_TYPES)}"
        )
    chosen_risk = risk.strip() or infer_risk(
        domain, claim_type, safety_evidence=safety_evidence
    )
    if chosen_risk not in VALID_RISKS:
        raise ValueError(f"invalid risk {chosen_risk!r}; expected one of {sorted(VALID_RISKS)}")
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status {status!r}; expected one of {sorted(VALID_STATUS)}")

    raw = {
        "domain": domain,
        "claim_type": claim_type,
        "source_url": source_url.strip(),
        "benchmark": benchmark.strip(),
        "deployment_evidence": deployment_evidence.strip(),
        "safety_evidence": safety_evidence.strip(),
        "cost_evidence": cost_evidence.strip(),
        "reproduction_evidence": reproduction_evidence.strip(),
        "adoption_evidence": adoption_evidence.strip(),
        "risk": chosen_risk,
        "status": status,
    }
    missing = required_evidence(raw)
    return ClaimRecord(
        id=slug(f"{subject}-{claim_type}-{source_url or claim}")[:80],
        subject=subject.strip(),
        domain=domain,
        claim_type=claim_type,
        claim=claim.strip(),
        source_url=source_url.strip(),
        benchmark=benchmark.strip(),
        deployment_evidence=deployment_evidence.strip(),
        safety_evidence=safety_evidence.strip(),
        cost_evidence=cost_evidence.strip(),
        reproduction_evidence=reproduction_evidence.strip(),
        adoption_evidence=adoption_evidence.strip(),
        risk=chosen_risk,
        status=status,
        recommendation=recommendation_for(raw),
        missing_evidence=missing,
        created_at=now(),
        updated_at=now(),
    )


def upsert(data: dict[str, Any], record: ClaimRecord) -> dict[str, Any]:
    claims = data.setdefault("claims", [])
    if not isinstance(claims, list):
        raise ValueError("state claims must be a list")
    record_dict = record.to_dict()
    for index, existing in enumerate(claims):
        if isinstance(existing, dict) and existing.get("id") == record.id:
            record_dict["created_at"] = str(existing.get("created_at") or record_dict["created_at"])
            record_dict["updated_at"] = now()
            claims[index] = record_dict
            return record_dict
    claims.append(record_dict)
    return record_dict


def import_claims(data: dict[str, Any], imported: dict[str, Any]) -> int:
    records = imported.get("claims") or imported.get("records")
    if not isinstance(records, list):
        raise ValueError("import file must contain claims or records list")
    before = len(data.get("claims", []))
    for raw in records:
        if not isinstance(raw, dict):
            continue
        record = make_record(
            subject=str(raw.get("subject") or raw.get("system") or ""),
            domain=str(raw.get("domain", "other")),
            claim_type=str(raw.get("claim_type", "demo")),
            claim=str(raw.get("claim", "")),
            source_url=str(raw.get("source_url", "")),
            benchmark=str(raw.get("benchmark", "")),
            deployment_evidence=str(
                raw.get("deployment_evidence") or raw.get("deployment_signal") or ""
            ),
            safety_evidence=str(raw.get("safety_evidence") or raw.get("safety_note") or ""),
            cost_evidence=str(raw.get("cost_evidence", "")),
            reproduction_evidence=str(raw.get("reproduction_evidence", "")),
            adoption_evidence=str(raw.get("adoption_evidence", "")),
            risk=str(raw.get("risk", "")),
            status=str(raw.get("status", "needs-review")),
        )
        upsert(data, record)
    return len(data.get("claims", [])) - before


def validate_record(raw: dict[str, Any]) -> list[Finding]:
    rid = str(raw.get("id") or "(missing-id)")
    findings: list[Finding] = []
    for key in ("subject", "domain", "claim_type", "claim"):
        if not str(raw.get(key, "")).strip():
            findings.append(Finding("CLAIM001", rid, f"missing required field: {key}"))
    domain = str(raw.get("domain", "")).strip()
    claim_type = str(raw.get("claim_type", "")).strip()
    risk = str(raw.get("risk", "")).strip()
    status = str(raw.get("status", "")).strip()
    if domain and domain not in VALID_DOMAINS:
        findings.append(Finding("CLAIM002", rid, f"invalid domain: {domain}"))
    if claim_type and claim_type not in VALID_CLAIM_TYPES:
        findings.append(Finding("CLAIM003", rid, f"invalid claim_type: {claim_type}"))
    if risk and risk not in VALID_RISKS:
        findings.append(Finding("CLAIM004", rid, f"invalid risk: {risk}"))
    if status and status not in VALID_STATUS:
        findings.append(Finding("CLAIM005", rid, f"invalid status: {status}"))
    if not str(raw.get("source_url", "")).startswith(("https://", "http://")):
        findings.append(Finding("CLAIM101", rid, "claim needs a public source URL"))
    for missing in required_evidence(raw):
        findings.append(Finding("CLAIM102", rid, f"missing evidence: {missing}"))
    if risk in {"high", "critical"} and status == "validated":
        findings.append(
            Finding("CLAIM103", rid, "high-risk claim cannot be validated by assertion")
        )
    return findings


def validate_state(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for raw in data.get("claims", []):
        if not isinstance(raw, dict):
            findings.append(Finding("CLAIM000", "(unknown)", "claim must be an object"))
            continue
        rid = str(raw.get("id") or "")
        if rid in seen:
            findings.append(Finding("CLAIM104", rid, "duplicate claim id"))
        seen.add(rid)
        findings.extend(validate_record(raw))
    return findings


def render(data: dict[str, Any]) -> str:
    claims = [raw for raw in data.get("claims", []) if isinstance(raw, dict)]
    if not claims:
        return "No AI claims."
    lines: list[str] = []
    for raw in claims:
        missing = raw.get("missing_evidence") or required_evidence(raw)
        missing_text = f" missing={'; '.join(missing)}" if missing else ""
        lines.append(
            f"{raw.get('id', '')} [{raw.get('risk', '')}/{raw.get('status', '')}] "
            f"{raw.get('recommendation', recommendation_for(raw))}{missing_text}"
        )
        lines.append(f"  {raw.get('subject', '')}: {raw.get('claim', '')}")
        lines.append(f"  source: {raw.get('source_url', '')}")
    return "\n".join(lines)


def render_markdown(data: dict[str, Any]) -> str:
    claims = [raw for raw in data.get("claims", []) if isinstance(raw, dict)]
    lines = ["# AI Claim Diligence", "", f"Claims: {len(claims)}", ""]
    for raw in claims:
        missing = raw.get("missing_evidence") or required_evidence(raw)
        lines.append(f"## {raw.get('subject', '(unknown)')}")
        lines.append(f"- ID: `{raw.get('id', '')}`")
        lines.append(f"- Domain: {raw.get('domain', '')}")
        lines.append(f"- Claim type: {raw.get('claim_type', '')}")
        lines.append(f"- Risk: {raw.get('risk', '')}")
        lines.append(f"- Status: {raw.get('status', '')}")
        lines.append(f"- Recommendation: {raw.get('recommendation', recommendation_for(raw))}")
        lines.append(f"- Source: {raw.get('source_url', '')}")
        if missing:
            lines.append(f"- Missing evidence: {'; '.join(missing)}")
        for key, label in (
            ("benchmark", "Benchmark"),
            ("deployment_evidence", "Deployment evidence"),
            ("safety_evidence", "Safety evidence"),
            ("cost_evidence", "Cost evidence"),
            ("reproduction_evidence", "Reproduction evidence"),
            ("adoption_evidence", "Adoption evidence"),
        ):
            value = str(raw.get(key, "")).strip()
            if value:
                lines.append(f"- {label}: {value}")
        lines.append("")
        lines.append(str(raw.get("claim", "")).strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _present(raw: dict[str, Any], *keys: str) -> bool:
    return any(str(raw.get(key, "")).strip() for key in keys)

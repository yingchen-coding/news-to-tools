from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TITLE_FIELDS = ("title", "title_ocr", "headline", "name")
URL_FIELDS = ("source_url", "url", "article_url", "link")
TEXT_FIELDS = ("title", "summary", "notes", "theme", "lane")


@dataclass(frozen=True)
class PromotionRule:
    product: str
    route: str
    action: str
    rationale: str
    keywords: tuple[str, ...]


RULES: tuple[PromotionRule, ...] = (
    PromotionRule(
        product="modelbroker",
        route="existing_public_repo",
        action="track cost, quota, failover, and routing pressure",
        rationale=(
            "Model-price, token, and provider-switching news belongs in routing/cost control."
        ),
        keywords=(
            "token",
            "quota",
            "cost",
            "成本",
            "计费",
            "价格",
            "claude",
            "anthropic",
            "deepseek",
        ),
    ),
    PromotionRule(
        product="agent-auto-dogfood",
        route="existing_public_repo",
        action="turn runtime/eval claims into dogfood metrics and harness checks",
        rationale="Agent success/failure claims should become trace-backed evaluation loops.",
        keywords=("harness", "评估", "benchmark", "框架", "close the loop", "生产环境", "runtime"),
    ),
    PromotionRule(
        product="agentguard",
        route="existing_public_repo",
        action="turn security and tool-risk claims into guard checks",
        rationale="Cyber, vulnerability, and tool-use risk belongs in the agent security gate.",
        keywords=("security", "安全", "漏洞", "mythos", "jailbreak", "攻防", "网络安全", "风险"),
    ),
    PromotionRule(
        product="agentskill",
        route="existing_private_repo",
        action="promote reusable memory, context, MCP, A2A, and skill patterns",
        rationale="General repeatable operating patterns should become cleaned reusable skills.",
        keywords=("skill", "memory", "记忆", "context", "上下文", "mcp", "a2a", "adk"),
    ),
    PromotionRule(
        product="claim-gate",
        route="existing_public_repo",
        action="gate model, medical, physical-AI, adoption, and deployment claims",
        rationale=(
            "Unverified performance/deployment claims need evidence requirements before "
            "implementation."
        ),
        keywords=(
            "claim",
            "声称",
            "部署",
            "采用",
            "medical",
            "医疗",
            "物理ai",
            "机器人",
            "自动驾驶",
        ),
    ),
    PromotionRule(
        product="ai-lab-talent-radar",
        route="existing_private_repo",
        action="track public talent, hiring, interview, and org-movement signals",
        rationale=(
            "Hiring and lab/team movement should become job-search intelligence, not generic tasks."
        ),
        keywords=("hiring", "扩招", "talent", "人才", "面试", "linkedin", "团队", "部门"),
    ),
)


def build_plan(path: Path, *, evidence_limit: int = 6) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = _items_from_payload(payload)
    routes: dict[str, dict[str, Any]] = {}
    unmatched = []

    for item in items:
        if not isinstance(item, dict):
            continue
        title = _first_text(item, TITLE_FIELDS)
        if not title:
            continue
        rule = _match_rule(item)
        evidence = _evidence(item)
        if rule is None:
            unmatched.append(evidence)
            continue
        bucket = routes.setdefault(
            rule.product,
            {
                "product": rule.product,
                "route": rule.route,
                "action": rule.action,
                "rationale": rule.rationale,
                "count": 0,
                "evidence": [],
            },
        )
        bucket["count"] += 1
        if len(bucket["evidence"]) < evidence_limit:
            bucket["evidence"].append(evidence)

    ordered = sorted(routes.values(), key=lambda route: (-route["count"], route["product"]))
    return {
        "source_file": path.name,
        "items": len(items),
        "routes": ordered,
        "unmatched_count": len(unmatched),
        "unmatched_evidence": unmatched[:evidence_limit],
        "decision": (
            "Promote into existing products first; create a new repo only when no existing route "
            "owns the behavior."
        ),
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Product Promotion Plan",
        "",
        f"Source: `{plan['source_file']}`",
        f"Items: {plan['items']}",
        "",
        str(plan["decision"]),
        "",
    ]
    for route in plan["routes"]:
        lines.extend(
            [
                f"## {route['product']}",
                "",
                f"- Route: `{route['route']}`",
                f"- Count: {route['count']}",
                f"- Action: {route['action']}",
                f"- Rationale: {route['rationale']}",
                "- Evidence:",
            ]
        )
        for item in route["evidence"]:
            url = f" ({item['source_url']})" if item.get("source_url") else ""
            lines.append(f"  - {item['title']}{url}")
        lines.append("")
    if plan["unmatched_count"]:
        lines.extend(["## Unmatched", "", f"Count: {plan['unmatched_count']}", ""])
        for item in plan["unmatched_evidence"]:
            lines.append(f"- {item['title']}")
        lines.append("")
    return "\n".join(lines)


def _items_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("promotion input must be a JSON object or list")
    for key in ("items", "queue", "cards", "articles", "selected"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ValueError("promotion input must contain items, queue, cards, articles, or selected")


def _match_rule(item: dict[str, Any]) -> PromotionRule | None:
    text = " ".join(str(item.get(field) or "") for field in TEXT_FIELDS).lower()
    theme = str(item.get("theme") or "").lower()
    lane = str(item.get("lane") or "").lower()
    if "claim" in theme or "claim" in lane:
        claim_rule = next(rule for rule in RULES if rule.product == "claim-gate")
        if any(word in text for word in ("cost", "成本", "token", "quota", "计费")):
            return next(rule for rule in RULES if rule.product == "modelbroker")
        if any(word in text for word in ("安全", "漏洞", "mythos", "security")):
            return next(rule for rule in RULES if rule.product == "agentguard")
        return claim_rule
    for rule in RULES:
        if any(keyword.lower() in text for keyword in rule.keywords):
            return rule
    return None


def _first_text(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _evidence(item: dict[str, Any]) -> dict[str, str]:
    return {
        "title": _first_text(item, TITLE_FIELDS),
        "source_url": _first_text(item, URL_FIELDS),
        "theme": str(item.get("theme") or ""),
    }

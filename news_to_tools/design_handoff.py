from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import workboard
from .utils import now, slug, state_path, write_json

HANDOFF_DIR = "design-handoffs"


@dataclass(frozen=True)
class ComponentRule:
    component: str
    keywords: tuple[str, ...]


COMPONENT_RULES = (
    ComponentRule("SearchFilter", ("search", "filter", "query", "搜索", "筛选", "查询")),
    ComponentRule("FileUpload", ("upload", "pdf", "file", "import", "上传", "文件", "导入")),
    ComponentRule("DataList", ("table", "list", "row", "card", "列表", "表格", "卡片")),
    ComponentRule(
        "MetricsPanel",
        ("chart", "metric", "dashboard", "score", "图表", "指标", "评分"),
    ),
    ComponentRule("AccessControl", ("login", "auth", "permission", "role", "权限", "登录", "角色")),
    ComponentRule("ActionPanel", ("submit", "approve", "send", "export", "生成", "提交", "导出")),
)


def split_requirements(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text)
    parts = re.split(r"\n+|(?<=[。！？.!?])\s+|(?:^|\n)\s*[-*]\s+", normalized)
    requirements = [re.sub(r"\s+", " ", part).strip(" -\t") for part in parts]
    return [item for item in requirements if item]


def infer_component(requirement: str) -> str:
    lowered = requirement.lower()
    for rule in COMPONENT_RULES:
        if any(keyword in lowered for keyword in rule.keywords):
            return rule.component
    return "FeatureSection"


def build_handoff(text: str, *, source_name: str = "brief") -> dict[str, Any]:
    requirements = split_requirements(text)
    components: list[dict[str, Any]] = []
    for index, requirement in enumerate(requirements, start=1):
        component = infer_component(requirement)
        components.append(
            {
                "id": f"{component}-{index}",
                "component": component,
                "requirement": requirement,
                "states": ["default", "loading", "empty", "error"],
                "acceptance": [
                    "Matches the stated user-facing requirement.",
                    "Handles loading, empty, and error states.",
                    "Has a deterministic test, story, or screenshot/manual acceptance note.",
                ],
                "developer_task": f"Implement {component}: {requirement}",
            }
        )
    return {
        "version": 1,
        "source_name": Path(source_name).name,
        "created_at": now(),
        "components": components,
        "review_questions": [
            "What is the primary user action on this screen?",
            "What data must exist before rendering?",
            "Which states need design approval before implementation is complete?",
            "What should happen when the backend or agent action fails?",
        ],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = ["# Design Dev Handoff", "", f"Source: {packet.get('source_name', 'brief')}", ""]
    for item in packet.get("components", []):
        lines.append(f"## {item['id']}")
        lines.append(f"- Requirement: {item['requirement']}")
        lines.append(f"- Developer task: {item['developer_task']}")
        lines.append(f"- States: {', '.join(item['states'])}")
        lines.append("- Acceptance:")
        for criterion in item["acceptance"]:
            lines.append(f"  - {criterion}")
        lines.append("")
    lines.append("## Review Questions")
    for question in packet.get("review_questions", []):
        lines.append(f"- {question}")
    return "\n".join(lines).rstrip() + "\n"


def write_handoff(packet: dict[str, Any], output_root: Path | None = None) -> Path:
    root = output_root or state_path(HANDOFF_DIR)
    out = root / slug(packet.get("source_name", "handoff"), default="handoff")
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "handoff.json", packet)
    (out / "handoff.md").write_text(render_markdown(packet), encoding="utf-8")
    return out


def import_to_workboard(
    packet: dict[str, Any],
    board: dict[str, Any] | None = None,
    *,
    source: str = "design-handoff",
) -> dict[str, int]:
    data = board if board is not None else workboard.load()
    imported = 0
    existing = 0
    for item in packet.get("components", []):
        title = item["developer_task"]
        found = workboard.find_existing_task(data, title=title)
        if found:
            existing += 1
            continue
        workboard.add_task(
            data,
            workboard.Task(
                title=title,
                source=source,
                status="queued",
                priority=2,
                acceptance=list(item["acceptance"]),
                evidence=[f"Design source: {packet.get('source_name', 'brief')}"],
            ),
        )
        imported += 1
    if board is None:
        workboard.save(data)
    return {"imported": imported, "existing": existing}


def build_from_file(path: Path, output_root: Path | None = None) -> tuple[dict[str, Any], Path]:
    text = path.read_text(encoding="utf-8", errors="replace")
    packet = build_handoff(text, source_name=path.name)
    return packet, write_handoff(packet, output_root)


def packet_json(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2) + "\n"

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import (
    claim_diligence,
    claim_feed,
    design_handoff,
    medical_claim_gate,
    model_registry,
    pdf_triage,
    queue_import,
    security_incidents,
    usage_bank,
    workboard,
)
from .utils import STATE_DIR_ENV


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn AI/news items into evidence-gated tools.")
    parser.add_argument(
        "--state-dir",
        type=Path,
        help=f"state directory; defaults to .news-to-tools or ${STATE_DIR_ENV}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_task = sub.add_parser("task-add", help="add a workboard task")
    add_task.add_argument("title")
    add_task.add_argument("--source", default="")
    add_task.add_argument("--source-url", default="")
    add_task.add_argument("--status", default="queued")

    sub.add_parser("task-list", help="list workboard tasks")

    queue = sub.add_parser("queue-import", help="import an article/news queue into tasks")
    queue.add_argument("path", type=Path)
    queue.add_argument(
        "--include-status",
        action="append",
        default=[],
        help="status to import; repeatable. Defaults to new/queued/todo/pending/missing.",
    )
    queue.add_argument("--source", default="queue-import")

    model_add = sub.add_parser("model-add", help="add guarded model candidate")
    model_add.add_argument("model_id")
    model_add.add_argument("--source-url", required=True)
    model_add.add_argument("--requirement", action="append", default=[])
    model_add.add_argument("--notes", default="")

    grant = sub.add_parser("usage-grant", help="grant usage quota")
    grant.add_argument("account")
    grant.add_argument("amount", type=int)
    grant.add_argument("--reason", required=True)
    grant.add_argument("--expires-on", default="")

    spend = sub.add_parser("usage-spend", help="spend usage quota")
    spend.add_argument("account")
    spend.add_argument("amount", type=int)
    spend.add_argument("--reason", required=True)

    pdf = sub.add_parser("pdf-triage", help="triage a PDF/TXT/Markdown file")
    pdf.add_argument("path", type=Path)

    med = sub.add_parser("medical-claim", help="gate a medical AI claim")
    med.add_argument("title")
    med.add_argument("--source-url", required=True)
    med.add_argument("--text", required=True)
    med.add_argument("--independent-validation", action="store_true")

    incident = sub.add_parser("security-incident", help="record model security incident")
    incident.add_argument("--model", required=True)
    incident.add_argument("--title", required=True)
    incident.add_argument("--severity", required=True)
    incident.add_argument("--mitigation", required=True)
    incident.add_argument("--source-url", default="")

    claim_add = sub.add_parser("claim-add", help="record an evidence-gated AI claim")
    claim_add.add_argument("--subject", required=True)
    claim_add.add_argument("--domain", required=True, choices=sorted(claim_diligence.VALID_DOMAINS))
    claim_add.add_argument(
        "--claim-type", required=True, choices=sorted(claim_diligence.VALID_CLAIM_TYPES)
    )
    claim_add.add_argument("--claim", required=True)
    claim_add.add_argument("--source-url", required=True)
    claim_add.add_argument("--benchmark", default="")
    claim_add.add_argument("--deployment-evidence", default="")
    claim_add.add_argument("--safety-evidence", default="")
    claim_add.add_argument("--cost-evidence", default="")
    claim_add.add_argument("--reproduction-evidence", default="")
    claim_add.add_argument("--adoption-evidence", default="")
    claim_add.add_argument("--risk", default="", choices=[""] + sorted(claim_diligence.VALID_RISKS))
    claim_add.add_argument(
        "--status", default="needs-review", choices=sorted(claim_diligence.VALID_STATUS)
    )

    claim_import = sub.add_parser("claim-import", help="import AI claim diligence records")
    claim_import.add_argument("path", type=Path)

    claim_feed_import = sub.add_parser(
        "claim-feed-import",
        help="import a news/product-map feed into AI claim diligence",
    )
    claim_feed_import.add_argument("path", type=Path)
    claim_feed_import.add_argument("--feed", default="model_claim_diligence_feed")

    sub.add_parser("claim-list", help="list AI claim diligence records")

    claim_validate = sub.add_parser("claim-validate", help="validate AI claim diligence state")
    claim_validate.add_argument("--json", action="store_true")

    claim_export = sub.add_parser("claim-export", help="export AI claim diligence state")
    claim_export.add_argument("--format", choices=["json", "markdown"], default="markdown")
    claim_export.add_argument("--output", type=Path)

    handoff = sub.add_parser("design-handoff", help="turn a design brief into build tasks")
    handoff.add_argument("path", type=Path)
    handoff.add_argument("--output-root", type=Path)
    handoff.add_argument("--format", choices=["json", "markdown"], default="markdown")
    handoff.add_argument("--add-to-workboard", action="store_true")

    args = parser.parse_args(argv)
    previous_state_dir = os.environ.get(STATE_DIR_ENV)
    if args.state_dir:
        os.environ[STATE_DIR_ENV] = str(args.state_dir)
    try:
        return _run_command(args)
    finally:
        if args.state_dir:
            if previous_state_dir is None:
                os.environ.pop(STATE_DIR_ENV, None)
            else:
                os.environ[STATE_DIR_ENV] = previous_state_dir


def _run_command(args: argparse.Namespace) -> int:
    if args.command == "task-add":
        data = workboard.load()
        record = workboard.add_task(
            data,
            workboard.Task(
                title=args.title,
                source=args.source,
                source_url=args.source_url,
                status=args.status,
            ),
        )
        workboard.save(data)
        print(record["id"])
        return 0
    if args.command == "task-list":
        print(workboard.render(workboard.load()))
        return 0
    if args.command == "queue-import":
        statuses = {status.lower() for status in args.include_status} or None
        print(
            json.dumps(
                queue_import.import_queue(args.path, include_statuses=statuses, source=args.source),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "model-add":
        data = model_registry.load()
        record = model_registry.add_candidate(
            data,
            args.model_id,
            source_url=args.source_url,
            requirements=args.requirement,
            notes=args.notes,
        )
        model_registry.save(data)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    if args.command == "usage-grant":
        data = usage_bank.load()
        account = usage_bank.account(data, args.account)
        usage_bank.grant(account, args.amount, reason=args.reason, expires_on=args.expires_on)
        usage_bank.save(data)
        print(f"{args.account}: balance={usage_bank.balance(account)}")
        return 0
    if args.command == "usage-spend":
        data = usage_bank.load()
        account = usage_bank.account(data, args.account)
        ok = usage_bank.spend(account, args.amount, reason=args.reason)
        usage_bank.save(data)
        result = "spent" if ok else "denied"
        print(f"{args.account}: {result} balance={usage_bank.balance(account)}")
        return 0 if ok else 3
    if args.command == "pdf-triage":
        print(pdf_triage.triage(args.path))
        return 0
    if args.command == "medical-claim":
        data = medical_claim_gate.load()
        claim = medical_claim_gate.assess(
            args.title,
            source_url=args.source_url,
            text=args.text,
            independent_validation=args.independent_validation,
        )
        data["claims"].append(claim)
        medical_claim_gate.save(data)
        print(json.dumps(claim, ensure_ascii=False, indent=2))
        return 0
    if args.command == "security-incident":
        data = security_incidents.load()
        record = security_incidents.add(
            data,
            model=args.model,
            title=args.title,
            source_url=args.source_url,
            severity=args.severity,
            mitigation=args.mitigation,
        )
        security_incidents.save(data)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    if args.command == "claim-add":
        data = claim_diligence.load()
        record = claim_diligence.make_record(
            subject=args.subject,
            domain=args.domain,
            claim_type=args.claim_type,
            claim=args.claim,
            source_url=args.source_url,
            benchmark=args.benchmark,
            deployment_evidence=args.deployment_evidence,
            safety_evidence=args.safety_evidence,
            cost_evidence=args.cost_evidence,
            reproduction_evidence=args.reproduction_evidence,
            adoption_evidence=args.adoption_evidence,
            risk=args.risk,
            status=args.status,
        )
        stored = claim_diligence.upsert(data, record)
        claim_diligence.save(data)
        print(json.dumps(stored, ensure_ascii=False, indent=2))
        return 0
    if args.command == "claim-import":
        data = claim_diligence.load()
        imported = json.loads(args.path.read_text(encoding="utf-8"))
        if not isinstance(imported, dict):
            raise ValueError(f"expected JSON object: {args.path}")
        count = claim_diligence.import_claims(data, imported)
        claim_diligence.save(data)
        print(json.dumps({"imported": count}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "claim-feed-import":
        print(
            json.dumps(
                claim_feed.import_claim_feed(args.path, feed=args.feed),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "claim-list":
        print(claim_diligence.render(claim_diligence.load()))
        return 0
    if args.command == "claim-validate":
        findings = claim_diligence.validate_state(claim_diligence.load())
        if args.json:
            print(
                json.dumps(
                    [finding.to_dict() for finding in findings], ensure_ascii=False, indent=2
                )
            )
        else:
            print("\n".join(f"{f.code} {f.record_id}: {f.message}" for f in findings) or "OK")
        return 0 if not findings else 2
    if args.command == "claim-export":
        data = claim_diligence.load()
        if args.format == "json":
            output = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        else:
            output = claim_diligence.render_markdown(data)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    if args.command == "design-handoff":
        packet, out = design_handoff.build_from_file(args.path, args.output_root)
        result: dict[str, int] | None = None
        if args.add_to_workboard:
            result = design_handoff.import_to_workboard(packet)
        if args.format == "json":
            payload: dict[str, object] = {"output": str(out), "handoff": packet}
            if result is not None:
                payload["workboard"] = result
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(design_handoff.render_markdown(packet), end="")
            print(f"\nOutput: {out}")
            if result is not None:
                print(f"Workboard: imported={result['imported']} existing={result['existing']}")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

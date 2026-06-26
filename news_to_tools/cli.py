from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import (
    medical_claim_gate,
    model_registry,
    pdf_triage,
    queue_import,
    security_incidents,
    usage_bank,
    workboard,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn AI/news items into evidence-gated tools.")
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

    args = parser.parse_args(argv)

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
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

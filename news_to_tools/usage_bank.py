from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .utils import DEFAULT_STATE_DIR, now, read_json, write_json

DEFAULT_USAGE_BANK = DEFAULT_STATE_DIR / "usage-bank.json"


def today() -> str:
    return date.today().isoformat()


def load(path: Path = DEFAULT_USAGE_BANK) -> dict[str, Any]:
    data = read_json(path, {"version": 1, "accounts": {}})
    if not isinstance(data.get("accounts"), dict):
        raise ValueError(f"invalid usage bank: {path}")
    return data


def save(data: dict[str, Any], path: Path = DEFAULT_USAGE_BANK) -> None:
    write_json(path, data)


def account(data: dict[str, Any], name: str) -> dict[str, Any]:
    return data["accounts"].setdefault(name, {"name": name, "grants": [], "audit": []})


def balance(account_record: dict[str, Any], on_date: str | None = None) -> int:
    on_date = on_date or today()
    total = 0
    for grant in account_record.get("grants", []):
        if grant.get("expires_on") and grant["expires_on"] < on_date:
            continue
        total += int(grant.get("remaining", 0))
    return total


def grant(account_record: dict[str, Any], amount: int, *, reason: str, expires_on: str = "") -> None:
    if amount <= 0:
        raise ValueError("grant amount must be positive")
    account_record.setdefault("grants", []).append(
        {"created_at": now(), "amount": amount, "remaining": amount, "reason": reason, "expires_on": expires_on}
    )
    account_record.setdefault("audit", []).append({"at": now(), "event": "grant", "amount": amount, "reason": reason})


def spend(account_record: dict[str, Any], amount: int, *, reason: str, on_date: str | None = None) -> bool:
    if amount <= 0:
        raise ValueError("spend amount must be positive")
    on_date = on_date or today()
    if balance(account_record, on_date) < amount:
        account_record.setdefault("audit", []).append(
            {"at": now(), "event": "spend-denied", "amount": amount, "reason": reason}
        )
        return False
    left = amount
    grants = sorted(
        account_record.get("grants", []),
        key=lambda item: item.get("expires_on") or "9999-12-31",
    )
    for grant_record in grants:
        if grant_record.get("expires_on") and grant_record["expires_on"] < on_date:
            continue
        take = min(left, int(grant_record.get("remaining", 0)))
        grant_record["remaining"] -= take
        left -= take
        if left == 0:
            break
    account_record.setdefault("audit", []).append({"at": now(), "event": "spend", "amount": amount, "reason": reason})
    return True


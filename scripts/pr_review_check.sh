#!/usr/bin/env bash
set -euo pipefail

python -m ruff check .
python -m compileall -q news_to_tools tests
pytest -q
agentguard --publish-check --score --no-color .

python - <<'PY'
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from news_to_tools.cli import main

with TemporaryDirectory() as tmp:
    cwd = Path.cwd()
    os.chdir(tmp)
    try:
        assert main(["task-add", "Implement article", "--source", "review"]) == 0
        assert main(["task-list"]) == 0
        assert main(["usage-grant", "agent", "5", "--reason", "review"]) == 0
        assert main(["usage-spend", "agent", "9", "--reason", "overspend"]) == 3
    finally:
        os.chdir(cwd)
PY

python - <<'PY'
from pathlib import Path

blocked = [
    "/" + "Users" + "/",
    "ghp" + "_",
    "BEGIN " + "RSA" + " KEY",
    "BEGIN " + "OPENSSH" + " KEY",
    "BEGIN " + "PRIVATE" + " KEY",
    "private-user" + "-images",
    "Temporary" + "Items",
]
skip_dirs = {".git", ".pytest_cache", "__pycache__"}
findings: list[str] = []

for path in Path(".").rglob("*"):
    if not path.is_file():
        continue
    if any(part in skip_dirs for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for needle in blocked:
        if needle in text:
            findings.append(f"{path}: contains blocked public-surface marker")
            break

if findings:
    print("\n".join(findings))
    raise SystemExit("public-surface scan failed")
PY

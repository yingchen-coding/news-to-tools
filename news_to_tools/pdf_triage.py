from __future__ import annotations

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from .utils import now, slug, state_path, write_json

PDF_TRIAGE_DIR = "pdf-triage"


def extract_text(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() != ".pdf":
        raise ValueError("input must be PDF, TXT, or Markdown")
    if shutil.which("pdftotext"):
        return subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    raise RuntimeError("pdftotext is required for PDF extraction")


def keywords(text: str, limit: int = 20) -> list[dict[str, Any]]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text)
    stop = {"the", "and", "for", "that", "with", "这个", "我们", "可以", "以及"}
    counts = Counter(word.lower() for word in words if word.lower() not in stop)
    return [{"term": term, "count": count} for term, count in counts.most_common(limit)]


def triage(path: Path, output_root: Path | None = None) -> Path:
    output_root = output_root or state_path(PDF_TRIAGE_DIR)
    text = extract_text(path)
    pages = [page.strip() for page in text.split("\f") if page.strip()] or [text]
    report = {
        "source": str(path),
        "created_at": now(),
        "pages": len(pages),
        "characters": len(text),
        "keywords": keywords(text),
        "warning": "Extraction and triage only. Verify cited pages before decisions.",
    }
    out = output_root / slug(path.stem, "document")
    out.mkdir(parents=True, exist_ok=True)
    (out / "extracted.txt").write_text(text, encoding="utf-8")
    write_json(out / "triage.json", report)
    return out

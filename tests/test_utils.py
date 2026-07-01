"""Tests for the shared state-store primitives (usage bank + idea ledger plumbing)."""
import json

import pytest

from news_to_tools.utils import read_json, write_json


def test_write_json_round_trips(tmp_path):
    p = tmp_path / "state.json"
    write_json(p, {"grants": [{"remaining": 3}]})
    assert read_json(p, {}) == {"grants": [{"remaining": 3}]}


def test_write_json_is_atomic_no_temp_left(tmp_path):
    p = tmp_path / "state.json"
    write_json(p, {"a": 1})
    assert [f.name for f in tmp_path.iterdir() if ".tmp." in f.name] == []
    assert json.loads(p.read_text())["a"] == 1


def test_read_json_missing_returns_default(tmp_path):
    assert read_json(tmp_path / "no.json", {"d": 1}) == {"d": 1}


def test_read_json_corrupt_raises_clear_error(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{ half written", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        read_json(p, {})

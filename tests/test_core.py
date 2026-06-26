from pathlib import Path

from news_to_tools import (
    medical_claim_gate,
    model_registry,
    pdf_triage,
    queue_import,
    security_incidents,
    usage_bank,
    workboard,
)
from news_to_tools.utils import state_dir, state_path


def test_workboard_add_and_render():
    data = {"version": 1, "tasks": []}
    task = workboard.add_task(
        data,
        workboard.Task(
            title="Implement article",
            source="example",
            status="queued",
            acceptance=["tests pass"],
        ),
    )
    assert task["id"] == "Implement-article"
    assert "Implement-article [queued]" in workboard.render(data)


def test_model_candidate_blocks_auto_route_until_verified():
    data = {"version": 1, "models": {}}
    model = model_registry.add_candidate(
        data,
        "example/model",
        source_url="https://example.com",
        requirements=["independent_benchmark"],
    )
    assert model["auto_route_allowed"] is False
    model_registry.verify(data, "example/model", command="pytest benchmark", passed=True)
    assert data["models"]["example/model"]["auto_route_allowed"] is True


def test_usage_bank_denies_overspend():
    data = {"version": 1, "accounts": {}}
    acct = usage_bank.account(data, "agent")
    usage_bank.grant(acct, 100, reason="monthly")
    assert usage_bank.spend(acct, 40, reason="task")
    assert usage_bank.balance(acct) == 60
    assert not usage_bank.spend(acct, 70, reason="too much")


def test_medical_claim_blocks_without_validation():
    claim = medical_claim_gate.assess(
        "Medical AI claim",
        source_url="https://example.com",
        text="Claims 91% doctor adoption for diagnosis.",
    )
    assert claim["decision"] == "blocked"
    assert claim["local_clinical_use_allowed"] is False
    assert "91%" in claim["reported_rates"]


def test_security_incident_high_severity_blocks_route():
    data = {"version": 1, "incidents": []}
    incident = security_incidents.add(
        data,
        model="example",
        title="jailbreak",
        severity="high",
        mitigation="disable auto-route",
    )
    assert incident["route_allowed"] is False


def test_pdf_triage_text_file(tmp_path: Path):
    source = tmp_path / "report.txt"
    source.write_text("Agent workflow evidence evidence.", encoding="utf-8")
    out = pdf_triage.triage(source, tmp_path / "out")
    assert (out / "extracted.txt").exists()
    assert (out / "triage.json").exists()


def test_queue_import_adds_actionable_items(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    queue = tmp_path / "queue.json"
    queue.write_text(
        """
        {
          "items": [
            {"title": "Agent workflow adds background task board", "source_url": "https://example.com/a"},
            {"title_ocr": "Already shipped", "status": "done"},
            {"headline": "Dropped hype", "status": "dropped"}
          ]
        }
        """,
        encoding="utf-8",
    )
    result = queue_import.import_queue(queue)
    assert result["items"] == 3
    assert result["imported"] == 1
    assert result["source_file"] == "queue.json"
    assert str(tmp_path) not in str(result)
    assert result["skipped"] == 2
    rendered = workboard.render(workboard.load())
    assert "Implement article: Agent workflow adds background task board" in rendered


def test_state_path_respects_environment(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NEWS_TO_TOOLS_STATE_DIR", str(tmp_path / "state"))
    assert state_dir() == tmp_path / "state"
    assert state_path("workboard.json") == tmp_path / "state" / "workboard.json"

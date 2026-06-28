from pathlib import Path

from news_to_tools import (
    claim_diligence,
    design_handoff,
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


def test_queue_import_is_idempotent_and_preserves_evidence(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    queue = tmp_path / "queue.json"
    queue.write_text(
        """
        {
          "items": [
            {
              "title": "Latest graph search technique",
              "status": "latest",
              "source_url": "https://example.com/graph",
              "summary": "Use entity links for fast incident search."
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    first = queue_import.import_queue(queue)
    second = queue_import.import_queue(queue)

    assert first["imported"] == 1
    assert first["existing"] == 0
    assert second["imported"] == 0
    assert second["existing"] == 1
    data = workboard.load()
    assert len(data["tasks"]) == 1
    task = data["tasks"][0]
    assert task["priority"] == 1
    assert "https://example.com/graph" in task["evidence"]
    assert "Use entity links" in task["evidence"][1]


def test_design_handoff_builds_component_tasks():
    packet = design_handoff.build_handoff(
        "Users can search camps by zipcode.\nUpload a PDF schedule and show a table."
    )

    assert [item["component"] for item in packet["components"]] == [
        "SearchFilter",
        "FileUpload",
    ]
    assert packet["components"][0]["developer_task"].startswith("Implement SearchFilter")
    assert "loading" in packet["components"][0]["states"]
    assert "backend or agent action fails" in packet["review_questions"][-1]


def test_design_handoff_import_to_workboard_is_idempotent():
    packet = design_handoff.build_handoff("Show a dashboard metric for model spend.")
    board = {"version": 1, "tasks": []}

    first = design_handoff.import_to_workboard(packet, board)
    second = design_handoff.import_to_workboard(packet, board)

    assert first == {"imported": 1, "existing": 0}
    assert second == {"imported": 0, "existing": 1}
    assert board["tasks"][0]["priority"] == 2
    assert "Design source: brief" in board["tasks"][0]["evidence"]


def test_ai_claim_diligence_blocks_unverified_high_risk_claim():
    record = claim_diligence.make_record(
        subject="Example robot agent",
        domain="physical",
        claim_type="deployment",
        claim="Can handle warehouse tasks safely in production.",
        source_url="https://example.com/robot",
        deployment_evidence="vendor launch post",
    )
    raw = record.to_dict()

    assert raw["risk"] == "high"
    assert raw["recommendation"] == "verify-first"
    assert "safety_evidence" in raw["missing_evidence"]
    findings = claim_diligence.validate_record(raw)
    assert any(finding.code == "CLAIM102" for finding in findings)


def test_ai_claim_diligence_allows_low_risk_validated_claim():
    record = claim_diligence.make_record(
        subject="Example code model",
        domain="coding",
        claim_type="benchmark",
        claim="Improves repository issue resolution on a public benchmark.",
        source_url="https://example.com/code-model",
        benchmark="Public issue-resolution benchmark",
        reproduction_evidence="local harness command passed",
        status="validated",
    )
    raw = record.to_dict()

    assert raw["recommendation"] == "implement"
    assert claim_diligence.validate_record(raw) == []


def test_state_path_respects_environment(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NEWS_TO_TOOLS_STATE_DIR", str(tmp_path / "state"))
    assert state_dir() == tmp_path / "state"
    assert state_path("workboard.json") == tmp_path / "state" / "workboard.json"

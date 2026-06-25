from pathlib import Path

from news_to_tools import (
    medical_claim_gate,
    model_registry,
    pdf_triage,
    security_incidents,
    usage_bank,
    workboard,
)


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

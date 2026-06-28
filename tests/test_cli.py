import subprocess
import sys
from pathlib import Path

from news_to_tools.cli import main


def test_cli_task_add_and_list(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["task-add", "Implement article", "--source", "test"]) == 0
    assert main(["task-list"]) == 0
    output = capsys.readouterr().out
    assert "Implement-article" in output


def test_cli_usage_denies_overspend(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["usage-grant", "agent", "10", "--reason", "test"]) == 0
    assert main(["usage-spend", "agent", "20", "--reason", "too much"]) == 3
    output = capsys.readouterr().out
    assert "denied" in output


def test_cli_queue_import(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    queue = tmp_path / "queue.json"
    queue.write_text(
        '{"items":[{"title":"Implement latest agent article","status":"new"}]}',
        encoding="utf-8",
    )
    assert main(["queue-import", str(queue)]) == 0
    output = capsys.readouterr().out
    assert '"imported": 1' in output
    assert str(tmp_path) not in output
    assert main(["task-list"]) == 0
    assert "Implement-latest-agent-article" in capsys.readouterr().out


def test_cli_state_dir_is_scoped(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    explicit_state = tmp_path / "explicit-state"

    assert main(["--state-dir", str(explicit_state), "task-add", "Explicit task"]) == 0
    assert (explicit_state / "workboard.json").exists()
    assert not (tmp_path / ".news-to-tools" / "workboard.json").exists()
    capsys.readouterr()

    assert main(["task-list"]) == 0
    assert capsys.readouterr().out.strip() == "No tasks."


def test_cli_uses_state_dir_environment(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    env_state = tmp_path / "env-state"
    monkeypatch.setenv("NEWS_TO_TOOLS_STATE_DIR", str(env_state))

    assert main(["task-add", "Env task"]) == 0
    assert (env_state / "workboard.json").exists()
    assert main(["task-list"]) == 0
    assert "Env-task" in capsys.readouterr().out


def test_cli_claim_diligence_lifecycle(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "claim-add",
                "--subject",
                "Example coding model",
                "--domain",
                "coding",
                "--claim-type",
                "benchmark",
                "--claim",
                "Solves more coding issues on a public benchmark.",
                "--source-url",
                "https://example.com/coding-model",
                "--benchmark",
                "Public issue benchmark",
                "--reproduction-evidence",
                "local reproduction passed",
                "--status",
                "validated",
            ]
        )
        == 0
    )
    assert main(["claim-validate"]) == 0
    assert "OK" in capsys.readouterr().out

    assert main(["claim-list"]) == 0
    assert "Example-coding-model-benchmark" in capsys.readouterr().out

    export_path = tmp_path / "claims.md"
    assert main(["claim-export", "--output", str(export_path)]) == 0
    assert "AI Claim Diligence" in export_path.read_text(encoding="utf-8")


def test_cli_claim_diligence_returns_nonzero_for_missing_evidence(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "claim-add",
                "--subject",
                "Example physical agent",
                "--domain",
                "physical",
                "--claim-type",
                "deployment",
                "--claim",
                "Runs safely around people.",
                "--source-url",
                "https://example.com/physical-agent",
            ]
        )
        == 0
    )
    assert main(["claim-validate"]) == 2


def test_cli_bio_claim_gate_lifecycle(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "bio-claim-add",
                "--subject",
                "Example bio model",
                "--claim",
                "Classifies public benchmark images for literature triage.",
                "--source-url",
                "https://example.com/bio-model",
                "--hazard-class",
                "low",
                "--validation",
                "public benchmark",
                "--independent-reproduction",
                "third-party reproduction",
                "--safety-review",
                "no wet-lab or construction output",
                "--limitations",
                "literature triage only",
                "--status",
                "validated",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"recommendation": "track"' in output
    assert "biological construction guidance" in output

    assert main(["bio-claim-validate"]) == 0
    assert "OK" in capsys.readouterr().out

    assert main(["bio-claim-list"]) == 0
    assert "Example-bio-model" in capsys.readouterr().out

    export_path = tmp_path / "bio-claims.md"
    assert main(["bio-claim-export", "--output", str(export_path)]) == 0
    exported = export_path.read_text(encoding="utf-8")
    assert "Bio-AI Claim Gate" in exported
    assert "not biological construction guidance" in exported


def test_cli_bio_claim_gate_rejects_protocol_claim(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "bio-claim-add",
                "--subject",
                "Unsafe request",
                "--claim",
                "Generate a wet-lab protocol for sequence design.",
                "--source-url",
                "https://example.com/bio-risk",
                "--hazard-class",
                "high",
            ]
        )
        == 0
    )
    assert '"recommendation": "reject"' in capsys.readouterr().out
    assert main(["bio-claim-validate"]) == 2
    assert "BIO201" in capsys.readouterr().out


def test_cli_design_handoff_writes_packet_and_workboard(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    brief = tmp_path / "brief.txt"
    brief.write_text(
        "Search by zipcode and filter by price.\nExport selected camps as a table.",
        encoding="utf-8",
    )

    assert main(["design-handoff", str(brief), "--add-to-workboard", "--format", "json"]) == 0
    output = capsys.readouterr().out
    assert '"component": "SearchFilter"' in output
    assert '"imported": 2' in output
    assert (tmp_path / ".news-to-tools" / "design-handoffs" / "brief.txt" / "handoff.json").exists()

    assert main(["task-list"]) == 0
    tasks = capsys.readouterr().out
    assert "Implement-SearchFilter" in tasks
    assert "Implement-DataList" in tasks


def test_module_entrypoint_help():
    result = subprocess.run(
        [sys.executable, "-m", "news_to_tools", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Turn AI/news items into evidence-gated tools." in result.stdout

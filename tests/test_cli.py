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
    assert main(["task-list"]) == 0
    assert "Implement-latest-agent-article" in capsys.readouterr().out


def test_module_entrypoint_help():
    result = subprocess.run(
        [sys.executable, "-m", "news_to_tools", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Turn AI/news items into evidence-gated tools." in result.stdout

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


def test_module_entrypoint_help():
    result = subprocess.run(
        [sys.executable, "-m", "news_to_tools", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Turn AI/news items into evidence-gated tools." in result.stdout

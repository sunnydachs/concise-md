import json
import subprocess
import sys

from concise.cli import main


def test_stdin_input(capsys):
    text = "## Verification\n\nRun this command and check the output.\n" * 12
    sys.stdin = type("Stdin", (), {"read": lambda self: text})()

    assert main(["-"]) == 0

    assert "## Conclusion" in capsys.readouterr().out


def test_json_output_shape(capsys):
    text = "## Verification\n\nRun the example and check the result.\n" * 12

    assert main(["-", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"input_lines", "output_lines", "conclusion", "code_blocks", "verify"}
    assert payload["conclusion"]
    assert payload["verify"]


def test_cli_exit_code_zero(tmp_path):
    path = tmp_path / "input.md"
    path.write_text("## Verification\n\nRun this command and check the output.\n" * 12, encoding="utf-8")

    completed = subprocess.run([sys.executable, "-m", "concise.cli", str(path)], capture_output=True, text=True, check=False)

    assert completed.returncode == 0

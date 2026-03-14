import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_outputs_valid_json():
    cmd = ["uv", "run", "agent.py", "What does REST stand for?"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )

    # The agent should not crash.
    assert proc.returncode == 0, proc.stderr

    line = proc.stdout.strip()
    data = json.loads(line)

    # Required fields.
    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)

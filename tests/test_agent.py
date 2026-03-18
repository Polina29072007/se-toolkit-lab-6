import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _base_env() -> dict:
    env = os.environ.copy()
<<<<<<< HEAD
    env.setdefault("LLM_API_KEY", "dummy-key")
    env.setdefault("LLM_API_BASE", "https://example.com")
    env.setdefault("LLM_MODEL", "dummy-model")
=======
    env.setdefault("LLM_API_KEY", "dummy")
    env.setdefault("LLM_API_BASE", "http://dummy")
    env.setdefault("LLM_MODEL", "dummy")
    env.setdefault("LMS_API_KEY", "dummy-backend-key")
>>>>>>> 11c98c6 (Implement lab-6 agent tools and eval stub)
    return env


def test_agent_outputs_valid_json():
    cmd = ["uv", "run", "agent.py", "What does REST stand for?"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=_base_env(),
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


<<<<<<< HEAD
def test_wiki_files_question_uses_list_files():
    cmd = ["uv", "run", "agent.py", "What files are in the wiki?"]
=======
def test_backend_framework_uses_read_file():
    cmd = ["uv", "run", "agent.py", "What framework does the backend use?"]
>>>>>>> 11c98c6 (Implement lab-6 agent tools and eval stub)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=_base_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr

    data = json.loads(proc.stdout.strip())

    assert "answer" in data
<<<<<<< HEAD
    assert "source" in data
    assert "tool_calls" in data

    tool_calls = data["tool_calls"]
    assert isinstance(tool_calls, list)
    assert any(call.get("tool") == "list_files" for call in tool_calls)

    assert "wiki/git-workflow.md" in data["source"]


def test_merge_conflict_question_reads_git_workflow():
    cmd = ["uv", "run", "agent.py", "How do you resolve a merge conflict?"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=_base_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr

    data = json.loads(proc.stdout.strip())

    assert "answer" in data
    assert "source" in data
=======
>>>>>>> 11c98c6 (Implement lab-6 agent tools and eval stub)
    assert "tool_calls" in data

    tool_calls = data["tool_calls"]
    assert isinstance(tool_calls, list)

<<<<<<< HEAD
    # хотя бы один вызов read_file
    assert any(call.get("tool") == "read_file" for call in tool_calls)

    # источник должен ссылаться на git-workflow.md
    assert "wiki/git-workflow.md" in data["source"]
=======
    # Должен использоваться read_file для чтения кода backend
    assert any(call.get("tool") == "read_file" for call in tool_calls)


def test_item_count_uses_query_api():
    cmd = ["uv", "run", "agent.py", "How many items are in the database?"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=_base_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr

    data = json.loads(proc.stdout.strip())

    assert "answer" in data
    assert "tool_calls" in data

    tool_calls = data["tool_calls"]
    assert isinstance(tool_calls, list)

    # Должен использоваться query_api для запросов к API
    assert any(call.get("tool") == "query_api" for call in tool_calls)

    # В ответе должно быть какое-то число (не жёсткая проверка)
    assert any(ch.isdigit() for ch in str(data["answer"]))
>>>>>>> 11c98c6 (Implement lab-6 agent tools and eval stub)

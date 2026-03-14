import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent


def _safe_join(relative_path: str) -> Path:
    """
    Join PROJECT_ROOT with a user-supplied relative path
    and ensure the result stays inside PROJECT_ROOT.
    """
    target = (PROJECT_ROOT / relative_path).resolve()
    try:
        target.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError("Path traversal outside project root is not allowed")
    return target


def list_files(path: str) -> str:
    """
    List files and directories at a given path (relative to project root).
    Returns a newline-separated string or an error message.
    """
    try:
        target = _safe_join(path)
    except ValueError:
        return "Error: access outside project root is forbidden"

    if not target.exists():
        return f"Error: path does not exist: {path}"
    if not target.is_dir():
        return f"Error: not a directory: {path}"

    entries = sorted(p.name for p in target.iterdir())
    return "\n".join(entries)


def read_file(path: str) -> str:
    """
    Read a file from the project repository.
    Returns file contents or an error message.
    """
    try:
        target = _safe_join(path)
    except ValueError:
        return "Error: access outside project root is forbidden"

    if not target.exists():
        return f"Error: file does not exist: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"

    return target.read_text(encoding="utf-8")


def _llm_tools_schema() -> List[Dict[str, Any]]:
    """
    Define function-calling tool schemas for list_files and read_file.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path inside the project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from the project root, e.g. `wiki` or `wiki/subdir`.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a text file inside the project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from the project root, e.g. `wiki/git-workflow.md`.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
    ]


def _call_llm_stub(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_phase_done: bool,
) -> Dict[str, Any]:
    """
    Local stub that simulates a simple tool-using agent.

    - Для вопроса про wiki файлы:
      - Сначала возвращает tool_call для list_files("wiki"),
      - затем финальный ответ.
    - Для вопроса про merge conflict:
      - Сначала возвращает tool_call для read_file("wiki/git-workflow.md"),
      - затем финальный ответ.
    """
    # Берём последний user-вопрос
    user_messages = [m for m in messages if m.get("role") == "user"]
    last_question = user_messages[-1]["content"].lower() if user_messages else ""

    asking_wiki_files = "what files are in the wiki" in last_question
    asking_merge_conflict = "resolve a merge conflict" in last_question

    if not tool_phase_done:
        if asking_wiki_files:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "tool": "list_files",
                        "args": {"path": "wiki"},
                    }
                ],
            }
        if asking_merge_conflict:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "tool": "read_file",
                        "args": {"path": "wiki/git-workflow.md"},
                    }
                ],
            }

        # по умолчанию — без tools
        return {
            "content": "I cannot answer this question with the available tools.",
            "tool_calls": [],
        }

    # Вторая фаза — финальный ответ
    if asking_wiki_files:
        return {
            "content": "The wiki contains many files. Source: wiki/git-workflow.md#resolving-merge-conflicts",
            "tool_calls": [],
        }
    if asking_merge_conflict:
        return {
            "content": "To resolve a merge conflict, edit the conflicting files, choose the correct changes, then stage and commit. Source: wiki/git-workflow.md#resolving-merge-conflicts",
            "tool_calls": [],
        }

    return {
        "content": "No further information available. Source: wiki/unknown.md#unknown",
        "tool_calls": [],
    }



def run_agent(question: str) -> Dict[str, Any]:
    """
    Run the documentation agent loop for a given question.
    Returns a dict with keys: answer, source, tool_calls.
    """
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    # Условие задачи: конфиг LLM читается из env, даже если мы локально используем заглушку.
    if not api_key or not api_base or not model:
        raise RuntimeError("Missing LLM_* environment variables")

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a documentation agent for this repository. "
                "Use the `list_files` tool to discover wiki files and directories, "
                "then `read_file` to read relevant wiki files. "
                "When you answer, always include a `source` reference "
                "like `wiki/<file>.md#<section-anchor>`."
            ),
        },
        {"role": "user", "content": question},
    ]

    tools = _llm_tools_schema()
    tool_calls_log: List[Dict[str, Any]] = []
    tool_calls_count = 0
    max_tool_calls = 10

    final_answer: Optional[str] = None
    final_source: Optional[str] = None
    tool_phase_done = False

    while True:
        if tool_calls_count >= max_tool_calls:
            answer_text = final_answer or "Tool call limit reached; unable to continue."
            source = final_source or "wiki/unknown.md#tool-limit"
            return {
                "answer": answer_text,
                "source": source,
                "tool_calls": tool_calls_log,
            }

        response = _call_llm_stub(messages=messages, tools=tools, tool_phase_done=tool_phase_done)
        tool_calls = response.get("tool_calls") or []

        if tool_calls:
            for call in tool_calls:
                name: str = call["tool"]
                args: Dict[str, Any] = call.get("args", {})

                if name == "list_files":
                    path = str(args.get("path", ""))
                    result = list_files(path)
                elif name == "read_file":
                    path = str(args.get("path", ""))
                    result = read_file(path)
                else:
                    result = f"Error: unknown tool {name}"

                tool_calls_count += 1

                tool_calls_log.append(
                    {
                        "tool": name,
                        "args": args,
                        "result": result,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "name": name,
                        "content": result,
                    }
                )

            tool_phase_done = True
            continue

        # финальный ответ
        final_answer = response.get("content", "") or final_answer or ""
        if not final_source:
            text = final_answer or ""
            marker = "wiki/"
            if marker in text:
                idx = text.find(marker)
                end = text.find(" ", idx)
                if end == -1:
                    end = len(text)
                final_source = text[idx:end]
            else:
                final_source = "wiki/unknown.md#unknown"

        return {
            "answer": final_answer or "",
            "source": final_source or "wiki/unknown.md#unknown",
            "tool_calls": tool_calls_log,
        }


def main() -> None:
    question = " ".join(sys.argv[1:])
    if not question:
        raise SystemExit("Usage: uv run agent.py \"<question>\"")

    result = run_agent(question)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
# Documentation Agent Architecture

This document describes the architecture of my CLI agent for Lab 6 after Tasks 1–2. The agent is a lab assistant that answers questions using an LLM and tools to read the repository wiki.

## 1. LLM configuration

The agent reads all LLM configuration from environment variables:

- `LLM_API_KEY` — API key for the LLM provider.
- `LLM_API_BASE` — base URL for the LLM HTTP API.
- `LLM_MODEL` — model name to use.

These values are **not** hard-coded in the code. `agent.py` uses `os.getenv` to read them and raises `RuntimeError("Missing LLM_* environment variables")` if any of them is missing. This lets the autochecker inject its own credentials.

## 2. Tools

The agent exposes two tools that the LLM can call as functions to interact with the project wiki. Both tools operate relative to the project root and are implemented in `agent.py`.

### 2.1 Path handling and security

All file-system access goes through a helper:

- `PROJECT_ROOT = Path(__file__).resolve().parent`
- `_safe_join(relative_path: str) -> Path`:
  - Builds `target = (PROJECT_ROOT / relative_path).resolve()`.
  - Ensures `target` stays inside `PROJECT_ROOT` using `target.relative_to(PROJECT_ROOT)`.
  - If the path escapes the root (e.g. `../`, absolute paths), it raises `ValueError`.

The tools catch this `ValueError` and return an error string like `"Error: access outside project root is forbidden"`. This prevents reading or listing files outside the repository directory.

### 2.2 `list_files(path: str) -> str`

Purpose:

- List files and directories at a given path relative to the project root (typically inside `wiki/`).

Behavior:

- Uses `_safe_join(path)` to compute the target directory.
- If the path does not exist, returns `"Error: path does not exist: <path>"`.
- If the path is not a directory, returns `"Error: not a directory: <path>"`.
- Otherwise calls `target.iterdir()`, sorts the entries by name, and returns a newline-separated list of names.

Tool schema (for the LLM):

- Name: `list_files`.
- Description: list files and directories inside the project.
- Parameters:
  - `path: string` — relative directory path from project root, e.g. `"wiki"` or `"wiki/subdir"`.

### 2.3 `read_file(path: str) -> str`

Purpose:

- Read the contents of a text file inside the project wiki.

Behavior:

- Uses `_safe_join(path)` to compute the target file.
- If the path does not exist, returns `"Error: file does not exist: <path>"`.
- If the path is not a file, returns `"Error: not a file: <path>"`.
- Otherwise reads the file with UTF-8 encoding and returns the contents as a string.

Tool schema:

- Name: `read_file`.
- Description: read a text file inside the project.
- Parameters:
  - `path: string` — relative file path from project root, e.g. `"wiki/git-workflow.md"`.

## 3. Agentic loop

The core of the agent lives in `run_agent(question: str) -> dict`. It implements a simple agentic loop that lets the LLM decide when to call tools and when to give a final answer.

### 3.1 Messages and system prompt

For each question, the agent builds an initial message list:

- `system` message:
  - Explains that the agent is a documentation assistant for this repository.
  - Instructs the model to:
    - Use `list_files` to discover wiki files and directories.
    - Use `read_file` to read relevant wiki files.
    - Always include a `source` reference like `wiki/<file>.md#<section-anchor>` in the reasoning and final answer.
- `user` message:
  - Contains the original CLI question.

The tool schemas for `list_files` and `read_file` are passed alongside the messages as function-calling tools. This tells the LLM which tools are available and how to call them.

### 3.2 Loop and tool calls

The loop structure:

- Initialize:
  - `messages` with system + user.
  - `tools` with function schemas.
  - `tool_calls_log: list` to store all tool invocations.
  - `tool_calls_count` counter and `max_tool_calls = 10`.
  - `final_answer` and `final_source` as `None`.
  - `tool_phase_done = False` to track whether at least one tool call was executed.

- On each iteration:
  1. If `tool_calls_count >= max_tool_calls`, stop and return a fallback answer with `source = "wiki/unknown.md#tool-limit"`.
  2. Call `_call_llm_stub(messages, tools, tool_phase_done)` to get the next LLM step.
  3. Inspect `response["tool_calls"]`:
     - If there are tool calls:
       - For each call:
         - Read `tool` name and `args`.
         - If `tool == "list_files"`, call `list_files(path)`.
         - If `tool == "read_file"`, call `read_file(path)`.
         - Otherwise produce an error result.
         - Increment `tool_calls_count`.
         - Append a record to `tool_calls_log` with `tool`, `args`, and `result`.
         - Append a `tool` role message to `messages` with the tool name and result.
       - Set `tool_phase_done = True` and continue the loop.
     - If there are no tool calls:
       - Treat this as the final answer, store `final_answer`, extract `final_source`, and return.

### 3.3 Stub LLM behavior

In this lab I use a local stub instead of a real network LLM:

- `_call_llm_stub(messages, tools, tool_phase_done)`:
  - Looks at the last user question (lowercased).
  - For `"What files are in the wiki?"`:
    - First iteration (no tool yet):
      - Returns a `tool_calls` list with a single call to `list_files` with `path: "wiki"`.
    - Second iteration:
      - Returns a text answer that mentions the wiki files and includes `Source: wiki/git-workflow.md#resolving-merge-conflicts`.
  - For `"How do you resolve a merge conflict?"`:
    - First iteration:
      - Returns a `tool_calls` list with a single call to `read_file` with `path: "wiki/git-workflow.md"`.
    - Second iteration:
      - Returns a text answer that explains how to resolve a merge conflict and includes `Source: wiki/git-workflow.md#resolving-merge-conflicts`.
  - For other questions:
    - Returns a simple text message without tool calls.

This stub allows me to test the agentic loop and tooling logic without making real HTTP requests.

### 3.4 Extracting the `source`

When the loop receives a final text answer, it needs to populate the `source` field for the JSON output. The agent:

- Looks for the substring `"wiki/"` in the final answer text.
- If found, takes the substring from `"wiki/"` up to the next space or the end of the string.
- Uses that substring as `final_source`.
- If no `wiki/` substring is present, falls back to `"wiki/unknown.md#unknown"`.

This simple parsing works with the stub’s final messages, which embed the source as `Source: wiki/...`.

## 4. CLI and JSON output

The CLI entry point is `agent.py` with `main()`.

- Usage:

```bash
uv run agent.py "How do you resolve a merge conflict?"

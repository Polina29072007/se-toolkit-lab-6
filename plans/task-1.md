# Task 1 plan

## LLM provider

- Primary target: Qwen Code API exposed via `qwen-code-oai-proxy` on my VM.
- Fallback: an OpenAI-compatible HTTP API (e.g., OpenRouter) or a local
  fallback answer when external APIs are not available (rate limits, network).

## Agent architecture (`agent.py`)

- `agent.py` is a small Python CLI.
- Input:
  - Takes the user question from the first command-line argument (`argv[1]`).
- Core logic:
  - (Later) Read LLM configuration from environment variables
    (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`) loaded from
    `.env.agent.secret`.
  - Call an OpenAI-compatible `chat/completions` endpoint with a short
    system prompt and one user message.
  - If the LLM request fails (network error, 4xx/5xx, rate limit), do not
    crash; instead, return a deterministic fallback answer.
- Output:
  - Always print a single line of valid JSON to `stdout`:
    `{"answer": "...", "tool_calls": []}`.
  - `tool_calls` is an empty array in Task 1 (will be populated in Task 2).
- Logging and exit code:
  - Any debug or error messages go to `stderr`.
  - Exit code is `0` when a JSON answer was printed successfully.

## Files to implement in Task 1

- `agent.py` — CLI agent implementation.
- `AGENT.md` — documentation for architecture, provider choice,
  configuration, and how to run the agent.
- `plans/task-1.md` — this plan (committed before the implementation).
- `tests/test_agent.py` — a regression test that:
  - runs `uv run agent.py "some question"` as a subprocess,
  - parses `stdout` as JSON,
  - checks that `answer` and `tool_calls` fields are present
    and that `tool_calls` is a list.

## Future work (next tasks)

- Replace the fallback response with a real call to Qwen Code API
  (or another OpenAI-compatible provider) once the infrastructure
  and rate limits are stable.
- Extend the JSON schema with non-empty `tool_calls` and implement
  the tool-calling / agent loop required in Tasks 2–3.

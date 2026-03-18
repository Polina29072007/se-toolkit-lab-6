## 1. query_api tool schema

I will add a third tool, `query_api`, alongside `list_files` and `read_file`.

- Name: `query_api`
- Description: "Call the deployed backend API and return the HTTP status code and JSON body."
- Parameters (JSON Schema):
  - type: object
  - properties:
    - method:
        type: string
        description: "HTTP method (GET, POST, etc.)."
    - path:
        type: string
        description: "Relative API path starting with '/', e.g. '/items/' or '/analytics/completion-rate'."
    - body:
        type: string
        description: "Optional JSON request body as a string for POST/PUT requests."
  - required: ["method", "path"]

The tool will return a JSON string with two top-level fields:

- `status_code`: integer HTTP status code from the backend response.
- `body`: string containing the response body (JSON-encoded).

In the LLM request I will register `query_api` as a function-calling tool together with `list_files` and `read_file`, so the model can choose between wiki tools, code reading, and live API queries depending on the question.

## 2. Python implementation of query_api

I will implement a new Python function in `agent.py`:

```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    ...
```

Behavior:

- Read backend configuration from environment variables:
  - `AGENT_API_BASE_URL` — base URL for the backend API (default to `"http://localhost:42002"` if not set).
  - `LMS_API_KEY` — backend API key used for authentication.
- Build the full URL by concatenating `AGENT_API_BASE_URL` and the `path` argument (ensuring there is exactly one `/` between them).
- Construct HTTP headers:
  - `Authorization: Bearer <LMS_API_KEY>` (or the expected auth scheme from the lab).
  - `Content-Type: application/json` when a request body is present.
- For the request body:
  - If `body` is not `None` and not empty, pass it as the raw JSON string in the request (no extra serialization).
  - For GET requests, ignore the `body` parameter.
- Use a simple HTTP client (e.g. `requests` or `httpx`) to send the request:
  - Map `method` to the corresponding HTTP verb (GET, POST, etc.).
  - Apply a reasonable timeout so the agent does not hang forever.
- On success:
  - Capture the integer status code.
  - Capture the response body as text.
  - Return a JSON string like:
    ```json
    {"status_code": 200, "body": "<raw-response-body>"}
    ```
- On error (e.g. network errors, invalid method, timeout):
  - Return a JSON string with:
    - `status_code`: 0
    - `body`: an error message describing what went wrong.

I will keep all sensitive values (LMS_API_KEY, AGENT_API_BASE_URL) outside the code and only read them from `os.getenv`, so the autochecker can inject its own backend URL and API key.

## 3. System prompt and tool selection strategy

I will extend the system prompt so that the LLM understands which tool to use for each type of question:

- Use `list_files` and `read_file` (wiki docs) when:
  - The question explicitly mentions the wiki or documentation.
  - The answer is about conceptual explanations, workflows, or static instructions that live in `wiki/*.md`
    (e.g. branch protection, SSH setup, VM connection).

- Use `read_file` (source code) when:
  - The question is about implementation details of the backend, Docker configuration, or ETL logic
    (e.g. which framework the backend uses, how idempotency is implemented, which routers exist).
  - The answer must be derived from code files (e.g. `backend/`, `docker-compose.yml`, `backend/Dockerfile`).

- Use `query_api` when:
  - The question depends on the **current state** of the running system or HTTP behavior:
    - counts in the database (e.g. "How many items are in the database?"),
    - HTTP status codes for specific requests (e.g. unauthorized `/items/`),
    - analytics values and errors (e.g. `/analytics/completion-rate`, `/analytics/top-learners`).
  - The answer cannot be trusted from docs alone and must be confirmed by calling the live API.

I will explicitly instruct the LLM in the system prompt to:
- Prefer `query_api` for any data-dependent or HTTP-status questions.
- Prefer `read_file` for questions about code structure, bugs, or implementation details.
- Prefer `list_files` + `read_file` in the wiki for questions explicitly referencing the project wiki.
- Chain tools when needed (e.g. call `query_api` to observe an error, then `read_file` on the relevant backend module to diagnose the bug).

## 4. Agent updates and env config

I will keep the overall agentic loop from Task 2, but extend it to include `query_api`:

- Add `query_api` to the tools schema array passed to the LLM, alongside `list_files` and `read_file`.
- Implement a new branch in the tool-execution loop:
  - When the LLM returns a tool call with `tool == "query_api"`, call the local `query_api` function with the provided `method`, `path`, and `body`.
  - Append the result to the `tool_calls` log and to the `messages` list as a `tool` role message, just like for the other tools.

Environment variables:

- LLM config (already implemented in Task 2, kept as-is):
  - `LLM_API_KEY`
  - `LLM_API_BASE`
  - `LLM_MODEL`
- Backend config for `query_api`:
  - `LMS_API_KEY` — required, must be read from `os.getenv`; no hardcoded default.
  - `AGENT_API_BASE_URL` — read from `os.getenv` with a default of `"http://localhost:42002"` if not set.

I will update `run_agent` so that:
- It still raises an error if any of the `LLM_*` variables is missing.
- It reads `LMS_API_KEY` and `AGENT_API_BASE_URL` inside `query_api` when the tool is used, so the function can be tested in isolation.
- The JSON output remains:

```json
{
  "answer": "<string>",
  "source": "<string or null>",
  "tool_calls": [ ... ]
}
```

but `source` will become optional in practice:
- For wiki/code questions, the agent will still try to extract a `wiki/*.md#anchor` or relevant file path.
- For pure system/API questions, `source` may be `null` or a non-wiki reference (e.g. an endpoint name).

## 5. Tests and benchmark iterations

I will extend `tests/test_agent.py` with at least two new regression tests for the system agent:

- Test 1: backend framework question
  - Question: `"What framework does the backend use?"`.
  - The test will run the CLI (`uv run agent.py ...`) and parse the JSON output.
  - Assertions:
    - `answer` contains `"FastAPI"` (based on the backend code).
    - `tool_calls` contains at least one entry with `tool == "read_file"`.

- Test 2: database item count question
  - Question: `"How many items are in the database?"`.
  - The test will mock or control the environment so that `query_api` is called (for local tests I may stub the HTTP call).
  - Assertions:
    - `tool_calls` contains at least one entry with `tool == "query_api"`.
    - The `answer` contains a number (I will keep the check flexible so it does not depend on an exact count).

Benchmark iterations (`uv run run_eval.py`):

- After implementing `query_api` and the new system prompt, I will run `uv run run_eval.py` to get an initial score.
- I will record in `plans/task-3.md`:
  - The initial score (e.g. `3/10`).
  - The first failing questions and the feedback hints from the script.
  - My hypothesis for why each failure happens (wrong tool, wrong path, wrong prompt, etc.).
- For each failing question I will:
  - Re-run the specific scenario manually by calling `agent.py` with that question.
  - Inspect `tool_calls` in the JSON to see which tools and arguments were used.
  - Fix either:
    - the `query_api` implementation,
    - the tool descriptions,
    - or the system prompt.
- I will iterate (run `uv run run_eval.py` again) until all 10 local questions pass, then update `AGENT.md` with the final score and lessons learned.## 5. Tests and benchmark iterations

I will extend `tests/test_agent.py` with at least two new regression tests for the system agent:

- Test 1: backend framework question
  - Question: `"What framework does the backend use?"`.
  - The test will run the CLI (`uv run agent.py ...`) and parse the JSON output.
  - Assertions:
    - `answer` contains `"FastAPI"` (based on the backend code).
    - `tool_calls` contains at least one entry with `tool == "read_file"`.

- Test 2: database item count question
  - Question: `"How many items are in the database?"`.
  - The test will mock or control the environment so that `query_api` is called (for local tests I may stub the HTTP call).
  - Assertions:
    - `tool_calls` contains at least one entry with `tool == "query_api"`.
    - The `answer` contains a number (I will keep the check flexible so it does not depend on an exact count).

Benchmark iterations (`uv run run_eval.py`):

- After implementing `query_api` and the new system prompt, I will run `uv run run_eval.py` to get an initial score.
- I will record in `plans/task-3.md`:
  - The initial score (e.g. `3/10`).
  - The first failing questions and the feedback hints from the script.
  - My hypothesis for why each failure happens (wrong tool, wrong path, wrong prompt, etc.).
- For each failing question I will:
  - Re-run the specific scenario manually by calling `agent.py` with that question.
  - Inspect `tool_calls` in the JSON to see which tools and arguments were used.
  - Fix either:
    - the `query_api` implementation,
    - the tool descriptions,
    - or the system prompt.
- I will iterate (run `uv run run_eval.py` again) until all 10 local questions pass, then update `AGENT.md` with the final score and lessons learned.
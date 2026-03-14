# Task 2: The Documentation Agent — Plan

## 1. Tool schemas

I will define two tools as function-calling schemas for the LLM:

- `list_files`
  - Name: `"list_files"`
  - Description: "List files and directories at a given path inside the project."
  - Parameters:
    - `path`: string, required. Relative directory path from the project root (e.g., `"wiki"` or `"wiki/subdir"`).

- `read_file`
  - Name: `"read_file"`
  - Description: "Read the contents of a text file inside the project."
  - Parameters:
    - `path`: string, required. Relative file path from the project root (e.g., `"wiki/git-workflow.md"`).

Both tools will be registered in the LLM request as function tools with JSON schema for their parameters.

## 2. Python tools implementation

I will implement two Python functions in `agent.py`:

- `list_files(path: str) -> str`:
  - Determine the project root directory (e.g., based on `Path(__file__).resolve()`).
  - Build the target path using `project_root / path` and normalize it (e.g., `.resolve()`).
  - Enforce security: if the resolved path is not inside `project_root` (path traversal with `..` or absolute paths), return an error string.
  - If the path is not an existing directory, return an error string.
  - Otherwise, list entries in the directory and return them as a newline-separated string.

- `read_file(path: str) -> str`:
  - Build and normalize the target path in the same way.
  - Enforce the same security check (must stay inside `project_root`).
  - If the path does not exist or is a directory, return an error string.
  - Otherwise, open the file with UTF-8 encoding and return its contents as a string.

## 3. Agentic loop

I will implement the agentic loop in `agent.py`:

- Input:
  - System message that explains:
    - Use `list_files` to discover wiki files.
    - Use `read_file` to read relevant wiki files.
    - In the final answer, always include a `source` string in the format
      `wiki/<file>.md#<section-anchor>`.
  - User message with the original question from the CLI.

- Loop (up to 10 tool calls total):
  1. Call the LLM with:
     - Model, base URL, and API key read from environment variables (`LLM_MODEL`, `LLM_API_BASE`, `LLM_API_KEY`).
     - Current list of messages.
     - Registered tools (`list_files`, `read_file`) as function-calling schemas.
  2. Inspect the response:
     - If the response contains `tool_calls`:
       - For each tool call:
         - Parse the `arguments` JSON.
         - Call the corresponding local Python function (`list_files` or `read_file`).
         - Append a `tool` role message with the tool name and result back to the messages list.
         - Record this call in an in-memory `tool_calls` list (with `tool`, `args`, `result`) for the final JSON output.
       - Continue the loop.
     - If the response is a normal text message with no tool calls:
       - Treat it as the final answer and break the loop.

- Safety limit:
  - Track the total number of tool calls.
  - If the number exceeds 10, stop looping and use the latest text answer from the LLM (if any) as the final answer.

## 4. CLI + JSON output

The CLI interface will stay consistent with Task 1:

- Entry point: `agent.py` with a `main()` function.
- Run via: `uv run agent.py "some question"`.

`main()` will:

1. Read the user question from command-line arguments.
2. Read `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` from environment variables.
3. Run the agentic loop and obtain:
   - `answer`: final text answer from the LLM.
   - `source`: a string pointing to the wiki section (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`).
   - `tool_calls`: the list of all tool calls made during the loop.
4. Print a JSON object to stdout with the shape:

   ```json
   {
     "answer": "<string>",
     "source": "<string>",
     "tool_calls": [
       {
         "tool": "<string>",
         "args": { "path": "<string>" },
         "result": "<string>"
       }
     ]
   }
## 5. Tests

I will extend `tests/test_agent.py` with at least two new regression tests for the documentation agent:

- Test 1: merge conflict question
  - Question: `"How do you resolve a merge conflict?"`.
  - The test will mock the LLM so that it:
    - First returns a `tool_call` for `read_file` with `path: "wiki/git-workflow.md"`.
    - Then returns a final text answer that includes an explanation.
  - The test will assert that:
    - `tool_calls` in the JSON output contains at least one entry with `tool == "read_file"`.
    - `source` contains `"wiki/git-workflow.md"`.

- Test 2: list wiki files
  - Question: `"What files are in the wiki?"`.
  - The test will mock the LLM so that it:
    - Returns a `tool_call` for `list_files` with `path: "wiki"`.
    - Then returns a final text answer using the tool result.
  - The test will assert that:
    - `tool_calls` contains at least one entry with `tool == "list_files"`.
    - The final `answer` mentions some file names from the mocked `list_files` result.

In both tests I will:
- Mock the LLM client so that tests do not perform real network calls.
- Invoke the CLI or the main agent entry function and parse its JSON output.
- Check that `answer`, `source`, and `tool_calls` fields are present and correctly populated.

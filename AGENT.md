# Agent

## Overview

`agent.py` is a small Python CLI program that takes a question as a
command-line argument and prints a single line of JSON to `stdout`.

The JSON schema is:

```json
{"answer": "...", "tool_calls": []}


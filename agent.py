import os
import sys
import json


def main() -> None:
    question = " ".join(sys.argv[1:])

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key or not api_base or not model:
        raise RuntimeError("Missing LLM_* environment variables")

    # пока заглушка, главное — корректный JSON
    result = {
        "question": question,
        "answer": "stub",
        "model": model,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()

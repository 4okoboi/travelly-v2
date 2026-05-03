import json
import shutil
import subprocess
from typing import Any, Optional


DEFAULT_MEMORY_QUERY = (
    "travel preferences, activity interests, hotel preferences, flight constraints, "
    "budget style, dietary needs, and preferred currency"
)


def _mem0_not_ready(message: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "message": message,
    }


def _run_mem0_cli(args: list[str]) -> dict[str, Any]:
    executable = shutil.which("mem0")
    if not executable:
        return _mem0_not_ready(
            "mem0 CLI is not installed. Install `mem0-cli` or `@mem0/cli` and run `mem0 init`."
        )

    try:
        result = subprocess.run(
            [executable, "--agent", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "mem0 CLI timed out.",
        }
    except OSError as exc:
        return {
            "status": "error",
            "message": f"Failed to start mem0 CLI: {exc}",
        }

    raw_output = result.stdout.strip() or result.stderr.strip()
    if not raw_output:
        return {
            "status": "error",
            "message": "mem0 CLI returned no output.",
        }

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "mem0 CLI returned non-JSON output.",
            "raw_output": raw_output,
        }

    if result.returncode != 0:
        return {
            "status": "error",
            "message": payload.get("message", "mem0 CLI request failed."),
            "details": payload,
        }

    return payload


def get_user_interests(
    user_id: str,
    query: Optional[str] = None,
    top_k: int = 5,
) -> dict[str, Any]:
    normalized_user_id = user_id.strip()
    if not normalized_user_id:
        return {
            "status": "error",
            "message": "user_id is required.",
        }

    search_query = query.strip() if query and query.strip() else DEFAULT_MEMORY_QUERY
    payload = _run_mem0_cli(
        [
            "search",
            search_query,
            "--user-id",
            normalized_user_id,
            "--top-k",
            str(max(1, min(top_k, 10))),
        ]
    )
    if payload.get("status") != "success":
        return payload

    memories = payload.get("data", [])
    return {
        "status": "ok",
        "user_id": normalized_user_id,
        "query": search_query,
        "count": payload.get("count", len(memories)),
        "memories": memories,
    }


def save_user_interests(
    user_id: str,
    memory: str,
    category: str = "preferences",
) -> dict[str, Any]:
    normalized_user_id = user_id.strip()
    normalized_memory = memory.strip()
    normalized_category = category.strip() or "preferences"

    if not normalized_user_id:
        return {
            "status": "error",
            "message": "user_id is required.",
        }

    if not normalized_memory:
        return {
            "status": "error",
            "message": "memory is required.",
        }

    metadata = json.dumps(
        {
            "source": "travelly",
            "category": normalized_category,
        }
    )
    payload = _run_mem0_cli(
        [
            "add",
            normalized_memory,
            "--user-id",
            normalized_user_id,
            "--metadata",
            metadata,
        ]
    )
    if payload.get("status") != "success":
        return payload

    events = payload.get("data", [])
    return {
        "status": "ok",
        "user_id": normalized_user_id,
        "memory": normalized_memory,
        "category": normalized_category,
        "count": payload.get("count", len(events)),
        "events": events,
    }

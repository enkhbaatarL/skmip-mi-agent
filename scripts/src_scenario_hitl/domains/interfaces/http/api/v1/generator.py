from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from domains.interfaces.http.api.v1._runtime import get_runtime


def run_generator(
    *,
    event_input_path: str,
    storage_root: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Generate draft scenarios and stop at HITL interrupt point."""
    tid = thread_id or f"thr_{uuid.uuid4().hex[:12]}"
    runtime = get_runtime(storage_root)
    paths = runtime.file_checkpointer.resolve_paths(tid)

    initial_state = {
        "thread_id": tid,
        "event_input_path": str(Path(event_input_path).resolve()),
        "draft_path": str(paths.draft_path),
        "final_path": str(paths.final_path),
    }
    config = {"configurable": {"thread_id": tid}}

    runtime.app.invoke(initial_state, config=config)
    snapshot = runtime.app.get_state(config)
    checkpoint = runtime.file_checkpointer.load_graph_state(tid)

    return {
        "thread_id": tid,
        "status": "interrupted_for_hitl",
        "next_nodes": list(snapshot.next),
        "draft_path": str(paths.draft_path),
        "final_path": str(paths.final_path),
        "phase": checkpoint.get("phase"),
    }

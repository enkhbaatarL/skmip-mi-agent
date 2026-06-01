from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.storage.file_client import FileClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PipelinePaths:
    thread_dir: Path
    draft_path: Path
    final_path: Path
    checkpoint_path: Path


class FileCheckpointer:
    """Persist pipeline artifacts and lightweight graph state snapshots."""

    def __init__(self, root_dir: str | Path, file_client: FileClient | None = None) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.file_client = file_client or FileClient()

    def resolve_paths(self, thread_id: str) -> PipelinePaths:
        thread_dir = self.root_dir / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        return PipelinePaths(
            thread_dir=thread_dir,
            draft_path=thread_dir / "scenarios_draft.json",
            final_path=thread_dir / "scenarios_final.json",
            checkpoint_path=thread_dir / "graph_state.json",
        )

    def save_draft(self, thread_id: str, draft_state: dict[str, Any], explicit_path: str | Path | None = None) -> Path:
        paths = self.resolve_paths(thread_id)
        target = Path(explicit_path).resolve() if explicit_path else paths.draft_path
        return self.file_client.write_json(target, draft_state)

    def save_final(self, thread_id: str, final_state: dict[str, Any], explicit_path: str | Path | None = None) -> Path:
        paths = self.resolve_paths(thread_id)
        target = Path(explicit_path).resolve() if explicit_path else paths.final_path
        return self.file_client.write_json(target, final_state)

    def save_graph_state(self, thread_id: str, state: dict[str, Any], phase: str) -> Path:
        payload = {
            "thread_id": thread_id,
            "saved_at": _utc_now(),
            "phase": phase,
            "state": state,
        }
        return self.file_client.write_json(self.resolve_paths(thread_id).checkpoint_path, payload)

    def load_graph_state(self, thread_id: str) -> dict[str, Any]:
        return self.file_client.read_json(self.resolve_paths(thread_id).checkpoint_path)

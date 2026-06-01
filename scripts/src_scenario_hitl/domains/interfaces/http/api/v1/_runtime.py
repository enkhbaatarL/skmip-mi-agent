from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.storage.file_checkpointer import FileCheckpointer
from domains.workflow.graphs.pipeline import build_pipeline_app


@dataclass
class RuntimeContext:
    app: Any
    file_checkpointer: FileCheckpointer


_RUNTIME_CACHE: dict[str, RuntimeContext] = {}


def get_runtime(storage_root: str | Path) -> RuntimeContext:
    root = str(Path(storage_root).resolve())
    ctx = _RUNTIME_CACHE.get(root)
    if ctx is not None:
        return ctx

    file_checkpointer = FileCheckpointer(root)
    app = build_pipeline_app(file_checkpointer)
    ctx = RuntimeContext(app=app, file_checkpointer=file_checkpointer)
    _RUNTIME_CACHE[root] = ctx
    return ctx

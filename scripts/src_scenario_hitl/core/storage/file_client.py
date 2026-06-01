from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


class FileClient:
    """Thread-safe JSON file client with atomic writes."""

    def read_json(self, path: str | Path) -> dict[str, Any]:
        src = Path(path).resolve()
        with _lock_for(src):
            with src.open("r", encoding="utf-8") as f:
                data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be an object: {src}")
        return data

    def write_json(self, path: str | Path, payload: dict[str, Any]) -> Path:
        dst = Path(path).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        with _lock_for(dst):
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp.replace(dst)
        return dst

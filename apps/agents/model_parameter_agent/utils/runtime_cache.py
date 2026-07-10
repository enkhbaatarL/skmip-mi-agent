from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from threading import Event, RLock
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class FileMtimeSizeSignature:
    mtime_ns: int
    size: int


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_signature(path: Path) -> tuple[str, int | None, int | None]:
    resolved = Path(path).expanduser().resolve(strict=False)
    try:
        stat = resolved.stat()
    except OSError:
        return str(resolved), None, None
    return str(resolved), int(stat.st_mtime_ns), int(stat.st_size)


def file_mtime_size_signature(path: Path) -> FileMtimeSizeSignature:
    stat = path.stat()
    return FileMtimeSizeSignature(
        mtime_ns=int(stat.st_mtime_ns),
        size=int(stat.st_size),
    )


class RuntimeLruCache(Generic[T]):
    def __init__(self, *, max_entries: int) -> None:
        self._lock = RLock()
        self._max_entries = max_entries
        self._values: OrderedDict[tuple[Any, ...], T] = OrderedDict()
        self._inflight: dict[tuple[Any, ...], Event] = {}

    def get_or_build(
        self,
        key: tuple[Any, ...],
        *,
        builder: Callable[[], T],
    ) -> T:
        while True:
            with self._lock:
                cached = self._values.get(key)
                if cached is not None:
                    self._values.move_to_end(key)
                    return cached
                wait_event = self._inflight.get(key)
                if wait_event is None:
                    wait_event = Event()
                    self._inflight[key] = wait_event
                    break
            wait_event.wait()

        try:
            value = builder()
        except Exception:
            with self._lock:
                self._inflight.pop(key, None)
                wait_event.set()
            raise

        with self._lock:
            self._values[key] = value
            self._values.move_to_end(key)
            while len(self._values) > self._max_entries:
                self._values.popitem(last=False)
            self._inflight.pop(key, None)
            wait_event.set()
        return value

    def ensure_capacity(self, min_entries: int) -> None:
        with self._lock:
            self._max_entries = max(self._max_entries, min_entries)

    def clear(self) -> None:
        with self._lock:
            for wait_event in self._inflight.values():
                wait_event.set()
            self._values.clear()
            self._inflight.clear()

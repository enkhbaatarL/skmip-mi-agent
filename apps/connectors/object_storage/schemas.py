from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    etag: str
    content_length: int
    last_modified: str
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class DownloadedObject:
    path: Path
    size: int
    sha256: str
    metadata: ObjectMetadata

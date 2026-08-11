from __future__ import annotations

import hashlib
import json


EVENT_SET_HASH_VERSION = "v1"


def canonical_event_set(mi_event_ids: list[int]) -> str:
    """Return the order-independent, versioned representation of an Event set."""
    compact_ids = json.dumps(sorted(mi_event_ids), separators=(",", ":"))
    return f"{EVENT_SET_HASH_VERSION}:{compact_ids}"


def event_set_hash(mi_event_ids: list[int]) -> str:
    return hashlib.sha256(canonical_event_set(mi_event_ids).encode("utf-8")).hexdigest()

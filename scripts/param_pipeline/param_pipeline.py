"""Deprecated MI model-parameter pipeline entrypoint.

Mapping metadata is now loaded from DB tables by the model-parameter agent.
This legacy entrypoint is intentionally kept as a failing shim so old calls do
not silently use stale logic.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "scripts/param_pipeline/param_pipeline.py is deprecated. "
        "Use the DB-backed model_parameter_agent proposal flow instead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Rebuild run.json from an existing SSE log, to reuse an earlier platform run as one of the N runs.

Usage:
  poetry run python run_from_sse_log.py --sse-log OLD/create_sse.log --out-dir {WORK}/platform/run_01

Copies the log into the run folder and writes run.json in the same shape as run_platform.py.
Then run export_group.py and fetch_trace.py for that run as usual.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from common import dump_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sse-log", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(args.sse_log)
    if source.resolve() != (out / "create_sse.log").resolve():
        shutil.copy(source, out / "create_sse.log")
    events = [
        json.loads(line[5:])
        for line in (out / "create_sse.log").read_text(encoding="utf-8").splitlines()
        if line.startswith("data:")
    ]
    if not events:
        raise SystemExit("no SSE data lines found")

    def ts(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    final = events[-1]
    summary = {
        "scenarioGroupId": next((e.get("scenarioGroupId") for e in events if e.get("scenarioGroupId")), None),
        "operationId": next((e.get("operationId") for e in events if e.get("operationId")), None),
        "transactionId": next((e.get("mlflowTraceId") for e in events if e.get("mlflowTraceId")), None),
        "status": final.get("status") or final.get("eventType"),
        "message": final.get("messageMarkdown"),
        "elapsedSec": round((ts(final["createdAt"]) - ts(events[0]["createdAt"])).total_seconds(), 1),
        "retries": [
            {k: e.get(k) for k in ("phase", "attempt", "validationCode", "createdAt")}
            for e in events
            if e.get("eventType") == "retrying"
        ],
        "timeline": [{k: e.get(k) for k in ("sequence", "createdAt", "eventType", "phase", "title")} for e in events],
    }
    dump_json(out / "run.json", summary)
    print(f"group={summary['scenarioGroupId']} status={summary['status']} elapsed={summary['elapsedSec']}s "
          f"transactionId={summary['transactionId']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

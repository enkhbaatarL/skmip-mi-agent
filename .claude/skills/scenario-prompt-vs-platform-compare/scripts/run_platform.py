"""Call the platform SSE create API N times with the same input and record each run.

Usage:
  poetry run python run_platform.py --event-ids 1681,1682,1683 --user-id 10093 --runs 3 --out-dir OUT
      [--base-url http://127.0.0.1:8000]

Each run writes OUT/run_XX/create_sse.log and run.json
(scenarioGroupId, operationId, transaction id(=SSE mlflowTraceId), status, retries, phase timeline).
Runs are sequential so the LLM gateway is not overloaded. Each run creates one Scenario Group in the DB.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

from common import dump_json


def run_once(base_url: str, event_ids: list[int], user_id: int, run_dir: Path) -> dict[str, object]:
    run_dir.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, object]] = []
    started = time.time()
    with (run_dir / "create_sse.log").open("w", encoding="utf-8") as log, httpx.stream(
        "POST",
        f"{base_url.rstrip('/')}/scenario-groups",
        json={"miEventIds": event_ids, "userId": user_id},
        headers={"Accept": "text/event-stream"},
        timeout=httpx.Timeout(1800.0, connect=10.0),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            log.write(line + "\n")
            log.flush()  # keep the log readable while the run is still streaming
            if line.startswith("data:"):
                data = json.loads(line[5:])
                events.append(data)
                if data.get("eventType") in {"completed", "failed", "interrupted"}:
                    break
    final = events[-1] if events else {}
    summary = {
        "scenarioGroupId": next((e.get("scenarioGroupId") for e in events if e.get("scenarioGroupId")), None),
        "operationId": next((e.get("operationId") for e in events if e.get("operationId")), None),
        "transactionId": next((e.get("mlflowTraceId") for e in events if e.get("mlflowTraceId")), None),
        "status": final.get("status") or final.get("eventType"),
        "message": final.get("messageMarkdown"),
        "elapsedSec": round(time.time() - started, 1),
        "retries": [
            {k: e.get(k) for k in ("phase", "attempt", "validationCode", "createdAt")}
            for e in events
            if e.get("eventType") == "retrying"
        ],
        "timeline": [
            {k: e.get(k) for k in ("sequence", "createdAt", "eventType", "phase", "title")} for e in events
        ],
    }
    dump_json(run_dir / "run.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-ids", required=True)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    event_ids = [int(x) for x in args.event_ids.split(",") if x.strip()]
    results = []
    for index in range(1, args.runs + 1):
        run_dir = Path(args.out_dir) / f"run_{index:02d}"
        try:
            summary = run_once(args.base_url, event_ids, args.user_id, run_dir)
        except Exception as exc:  # keep going so one failed run does not hide the others
            summary = {"status": "error", "error": repr(exc)}
            dump_json(run_dir / "run.json", summary)
        results.append(summary)
        print(
            f"run {index:02d}: group={summary.get('scenarioGroupId')} status={summary.get('status')} "
            f"elapsed={summary.get('elapsedSec')}s retries={[(r['phase'], r['validationCode']) for r in summary.get('retries', [])]}"
        )
    dump_json(Path(args.out_dir) / "runs.json", results)
    return 0


if __name__ == "__main__":
    sys.exit(main())

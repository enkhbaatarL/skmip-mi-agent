"""Find and dump the MLflow traces of a platform create run (read-only).

The SSE `mlflowTraceId` is the app transaction id (`aip.transaction_id` trace metadata), not the
MLflow trace id, so traces are located by searching the experiment.

Usage:
  poetry run python fetch_trace.py --transaction-id <SSE mlflowTraceId> --group-id 307 --out-dir OUT/run_01
      [--experiment scenario_agent_local] [--tracking-uri http://...]

Writes trace.json (create), trace_additional.json (auto additional-dimension run, if any),
trace_by_stage.md (every LLM call: prompts, output or error, tokens, duration) and stage_summary.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from common import as_json, dump_json, mlflow_client


def find_traces(client: Any, experiment: str, transaction_id: str, group_id: str) -> tuple[str | None, str | None]:
    exp = client.get_experiment_by_name(experiment) if not experiment.isdigit() else client.get_experiment(experiment)
    traces = client.search_traces(locations=[exp.experiment_id], max_results=200, order_by=["timestamp_ms DESC"],
                                  include_spans=False)
    create_id = additional_id = None
    for trace in traces:
        info = trace.info
        meta = info.trace_metadata or {}
        tags = info.tags or {}
        if meta.get("aip.transaction_id") == transaction_id:
            create_id = info.trace_id
        elif (
            additional_id is None
            and str(meta.get("session_id") or tags.get("session_id")) == group_id
            and tags.get("api_identifier") == "add_dimension"
        ):
            additional_id = info.trace_id
    return create_id, additional_id


def _short_error(message: str | None) -> str:
    text = message or ""
    if title := re.search(r"<title>(.*?)</title>", text, re.S):
        return title.group(1).strip()
    return " ".join(text.split())[:300]


def llm_calls(trace_dict: dict[str, Any], label: str) -> list[dict[str, Any]]:
    spans = [s for s in trace_dict["data"]["spans"] if s["name"].startswith("llm.structured")]
    spans.sort(key=lambda s: int(s["start_time_unix_nano"]))
    calls = []
    for index, span in enumerate(spans, start=1):
        attrs = span["attributes"]
        inputs = as_json(attrs.get("mlflow.spanInputs", "{}")) or {}
        outputs = as_json(attrs.get("mlflow.spanOutputs", "null"))
        meta = as_json(attrs.get("metadata", "{}")) or {}
        status = span.get("status") or {}
        content = None
        if isinstance(outputs, dict):
            try:
                content = outputs["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = outputs.get("content") or json.dumps(outputs, ensure_ascii=False)
        calls.append({
            "label": label,
            "index": index,
            "node": meta.get("langgraph_node", label) if isinstance(meta, dict) else label,
            "schema": as_json(attrs.get("llm.output_schema")),
            "durationSec": round((int(span["end_time_unix_nano"]) - int(span["start_time_unix_nano"])) / 1e9, 1),
            "status": status.get("code"),
            "error": _short_error(status.get("message")) if "ERROR" in str(status.get("code")) else None,
            "usage": as_json(attrs.get("mlflow.chat.tokenUsage", "{}")) or {},
            "messages": inputs.get("messages", []) if isinstance(inputs, dict) else [],
            "content": content,
        })
    return calls


def to_markdown(calls: list[dict[str, Any]]) -> str:
    out = ["# MLflow trace — 단계별 LLM input/output"]
    for call in calls:
        out.append(f"\n\n# [{call['label']} #{call['index']}] {call['node']} — {call['durationSec']}s — "
                   f"{call['status']} — tokens {call['usage']}\n- schema: {call['schema']}\n")
        for message in call["messages"]:
            out.append(f"\n## {message.get('role')} prompt\n\n```\n{message.get('content')}\n```\n")
        if call["error"]:
            out.append(f"\n## ERROR\n{call['error']}\n")
        else:
            try:
                pretty = json.dumps(json.loads(call["content"]), ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                pretty = call["content"]
            out.append(f"\n## output\n\n```json\n{pretty}\n```\n")
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--experiment", default="scenario_agent_local")
    parser.add_argument("--tracking-uri", default=None)
    args = parser.parse_args()
    out = Path(args.out_dir)
    client = mlflow_client(args.tracking_uri)
    create_id, additional_id = find_traces(client, args.experiment, args.transaction_id, str(args.group_id))
    if create_id is None:
        raise SystemExit(f"trace with aip.transaction_id={args.transaction_id} not found in {args.experiment}")
    calls: list[dict[str, Any]] = []
    for label, trace_id, name in (("create", create_id, "trace.json"), ("additional", additional_id, "trace_additional.json")):
        if trace_id is None:
            continue
        trace_dict = client.get_trace(trace_id).to_dict()
        dump_json(out / name, trace_dict)
        calls += llm_calls(trace_dict, label)
    (out / "trace_by_stage.md").write_text(to_markdown(calls), encoding="utf-8")
    summary = {
        "createTraceId": create_id,
        "additionalTraceId": additional_id,
        "calls": [{k: v for k, v in c.items() if k not in {"messages", "content"}} for c in calls],
    }
    dump_json(out / "stage_summary.json", summary)
    print(f"create trace={create_id} additional trace={additional_id}")
    for c in summary["calls"]:
        print(f"  [{c['label']} #{c['index']}] {c['node']:32} {c['durationSec']:6}s {c['status']} "
              f"in={c['usage'].get('input_tokens')} out={c['usage'].get('output_tokens')} {c['error'] or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

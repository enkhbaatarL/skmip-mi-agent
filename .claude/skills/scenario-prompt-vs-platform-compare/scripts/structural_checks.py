"""Count structural defects of one platform run automatically (layer ① of the evaluation framework).

Usage:
  poetry run python structural_checks.py --run-dir {WORK}/platform/run_01

Reads group.json / scenarios.json (export_group.py), stage_summary.json + run.json (fetch_trace.py /
run_platform.py) and the source events (events.json, or a read-only DB query when missing).
Writes structural.json and prints a short summary. Every check is a mechanical signal; the operator
confirms "signal" items by reading the result before calling them defects.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from common import as_json, dump_json, query

TRANSLITERATIONS = ("엘엔지", "제이케이엠", "티티에프", "에이치에이치", "엔더블유이", "티에프디이", "피엔지", "에프에스알유")
# Lower-case English words inside Korean prose (e.g. "cargo" in "Atlantic cargo"). Capitalized words are
# treated as proper nouns and upper-case tokens as abbreviations, both of which the prompt allows.
ENGLISH_WORD = re.compile(r"(?<![A-Za-z_])[a-z]{3,}(?![A-Za-z_])")
ALLOWED_WORDS = {"day", "bcm", "bcfd", "mmbtu", "mtpa"}  # units that legitimately appear in lower case
EXPECTED_CALLS = {"analyze_event_interactions": 1, "design_model_lever_dimensions": 1, "synthesize_v4_scenarios": 1}


def load(run: Path, name: str) -> Any:
    path = run / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_events(run: Path, event_ids: list[int]) -> dict[int, dict[str, Any]]:
    cached = load(run, "events.json")
    rows = cached or query(
        "SELECT mi_event_id, event_title, one_line_summary, key_bullets_json FROM tmm_mi_mievent_m "
        f"WHERE mi_event_id IN ({','.join(str(i) for i in event_ids)})"
    )
    events = {}
    for row in rows:
        bullets = as_json(row.get("key_bullets_json"))
        if isinstance(bullets, dict):
            bullets = bullets.get("bullets", [])
        events[int(row["mi_event_id"])] = {"title": row.get("event_title"), "bullets": bullets or []}
    return events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run = Path(args.run_dir)
    group = load(run, "group.json")
    scenarios = load(run, "scenarios.json") or []
    if group is None:
        raise SystemExit(f"{run}/group.json missing — run export_group.py first")
    diag = as_json(group.get("generation_diagnostics")) or {}
    dims = as_json(group.get("dimension_definitions")) or []
    paths = diag.get("impact_paths", [])
    facts = diag.get("event_facts", [])
    interactions = diag.get("event_interactions", [])
    iu_to_interaction = {u.get("uncertainty_id"): u.get("interaction_id") for u in diag.get("interaction_uncertainties", [])}
    breakdowns = diag.get("scenario_pressure_breakdowns", [])

    # 1. Double counting: a Dimension built from an Interaction question while the same Interaction is applied.
    double = []
    for dim in dims:
        for source in dim.get("source_uncertainty_ids") or []:
            interaction_id = iu_to_interaction.get(source)
            if not interaction_id:
                continue
            for item in breakdowns:
                if interaction_id in (item.get("applied_interaction_ids") or []):
                    double.append({"dimension": dim.get("dimension_id"), "interaction": interaction_id,
                                   "scenario": item.get("title")})
    # 2. Dimension overlap signal: several Dimensions on the same primary Lever (confirm by reading).
    lever_count = Counter(str(d.get("primary_lever_code")) for d in dims)
    shared = {lever: n for lever, n in lever_count.items() if n > 1}
    iu_dims = [d.get("dimension_id") for d in dims if any(s in iu_to_interaction for s in d.get("source_uncertainty_ids") or [])]

    # 3. Fact coverage: is each event's first key bullet (title core fact) selected and used as Primary Fact?
    event_ids = sorted({int(f["event_id"]) for f in facts} | {int(p["event_id"]) for p in paths})
    events = load_events(run, event_ids)
    fact_rows = []
    for event_id in event_ids:
        selected = [f for f in facts if int(f["event_id"]) == event_id]
        core = (events.get(event_id, {}).get("bullets") or [""])[0].strip()
        texts = [str(f.get("observed_basis") or "").strip() for f in selected]
        bullets = [str(b).strip() for b in events.get(event_id, {}).get("bullets") or []]
        fact_rows.append({
            "event_id": event_id,
            "candidates": len(bullets),
            "selected_facts": len(selected),
            "selected_candidate_numbers": [bullets.index(t) + 1 for t in texts if t in bullets],
            "excluded_candidates": [
                {"number": index, "text": text[:160]} for index, text in enumerate(bullets, start=1) if text not in texts
            ],
            "core_fact_selected": bool(core) and core in texts,
            "core_fact_is_primary": bool(core) and bool(texts) and texts[0] == core,
        })
    # 4. Path role / balance consistency.
    no_primary = [p["impact_path_id"] for p in paths if not any(s.get("path_role") == "primary" for s in p.get("lever_steps") or [])]
    balance_mismatch = []
    for p in paths:
        balance = p.get("balance_effect") or {}
        directions = {s.get("state_direction") for s in p.get("lever_steps") or [] if s.get("path_role") == "primary"}
        if balance.get("direction") in {"increase", "decrease"} and directions and balance["direction"] not in directions:
            balance_mismatch.append({"path": p["impact_path_id"], "balance": balance.get("direction"), "lever": sorted(directions)})

    # 5. Retries and failures from the trace.
    stage = load(run, "stage_summary.json") or {"calls": []}
    calls = [c for c in stage["calls"] if c.get("label") == "create"]
    per_node = Counter(c["node"] for c in calls)
    retries = {node: n - EXPECTED_CALLS[node] for node, n in per_node.items() if node in EXPECTED_CALLS and n > EXPECTED_CALLS[node]}
    if per_node.get("analyze_event_impacts", 0) > len(event_ids):
        retries["analyze_event_impacts"] = per_node["analyze_event_impacts"] - len(event_ids)
    errors = [f"{c['node']}: {c['error']}" for c in calls if c.get("error")]
    run_json = load(run, "run.json") or {}

    # 6. Wording: transliteration and lower-case English words in user-facing text.
    texts = {"group.title": group.get("title") or "", "group.description": group.get("description") or ""}
    for s in scenarios:
        texts[f"scenario.{s.get('display_order')}"] = " ".join(str(s.get(k) or "") for k in ("title", "narrative", "global_pressure_rationale"))
    translit = Counter(t for text in texts.values() for t in TRANSLITERATIONS for _ in range(text.count(t)))
    english = Counter(w for text in texts.values() for w in ENGLISH_WORD.findall(text) if w.lower() not in ALLOWED_WORDS)

    # 7. Scenario shape.
    value_contrib = {v["value_id"]: v.get("pressure_contribution") for d in dims for v in d.get("values", [])}
    baseline = next((s for s in scenarios if s.get("baseline_yn") == "Y"), None)
    baseline_values = as_json(baseline.get("dimension_values")) if baseline else {}
    baseline_all_balanced = bool(baseline_values) and all(value_contrib.get(v) == "balanced" for v in baseline_values.values())

    result = {
        "group_id": group.get("scenario_group_id"),
        "status": run_json.get("status"),
        "elapsed_sec": run_json.get("elapsedSec"),
        "facts_total": len(facts),
        "facts": fact_rows,
        "core_fact_missing_events": [r["event_id"] for r in fact_rows if not r["core_fact_selected"]],
        "core_fact_not_primary_events": [r["event_id"] for r in fact_rows if not r["core_fact_is_primary"]],
        "impact_paths": len(paths),
        "paths_without_primary_role": no_primary,
        "balance_direction_mismatch": balance_mismatch,
        "interactions": [f"{i.get('relation')}:{'×'.join(i.get('impact_path_ids') or [])}" for i in interactions],
        "dimensions": len(dims),
        "dimension_levers": dict(lever_count),
        "dimensions_sharing_lever_signal": shared,
        "dimensions_from_interaction_questions": iu_dims,
        "double_counting": double,
        "double_counting_scenarios": len({d["scenario"] for d in double}),
        "combination_decision_table": bool(diag.get("combination_decisions") or diag.get("dimension_decisions")),
        "retries": retries,
        "llm_errors": errors,
        "transliteration": dict(translit),
        "english_words_signal": dict(english),
        "bands": [s.get("global_pressure_band") for s in scenarios],
        "excluded_bands": [e.get("pressure_band") for e in diag.get("excluded_candidates", [])],
        "baseline_band": baseline.get("global_pressure_band") if baseline else None,
        "baseline_all_balanced": baseline_all_balanced,
    }
    dump_json(run / "structural.json", result)
    print(f"group {result['group_id']}: double_counting_scenarios={result['double_counting_scenarios']} "
          f"core_fact_missing={result['core_fact_missing_events']} not_primary={result['core_fact_not_primary_events']} "
          f"retries={retries} translit={dict(translit)} english={dict(english)} dims={result['dimensions']} "
          f"shared={shared} baseline={result['baseline_band']} all_balanced={baseline_all_balanced}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

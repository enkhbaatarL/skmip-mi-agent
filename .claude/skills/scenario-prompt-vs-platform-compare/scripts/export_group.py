"""Export a Scenario Group (read-only SELECT) and render it in the workshop structure.

Usage:
  poetry run python export_group.py --group-id 307 --out-dir OUT/run_01

Writes group.json, scenarios.json, group_events.json, operations.json, platform_result.md, metrics.json.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from common import as_json, dump_json, query


def render(group: dict[str, Any], scenarios: list[dict[str, Any]]) -> str:
    diag = as_json(group.get("generation_diagnostics")) or {}
    dims = as_json(group.get("dimension_definitions")) or []
    out = [f"# Platform 결과 (group {group['scenario_group_id']})", ""]
    out += [f"- title: {group.get('title')}", f"- description: {group.get('description')}",
            f"- analysis_as_of: {diag.get('analysis_as_of')}", f"- catalog: {group.get('impact_catalog_version')}", ""]
    out.append("## Facts")
    out += [f"- {f.get('fact_id')} {f.get('observed_basis') or f.get('statement')}" for f in diag.get("event_facts", [])]
    out.append("\n## Decision basis")
    out += [f"- {d}" for d in diag.get("decision_basis", [])]
    out.append("\n## Impact Paths")
    for p in diag.get("impact_paths", []):
        steps = "; ".join(
            f"{s.get('lever_code')}|{s.get('path_role')}|{s.get('state_direction')}|{s.get('scope')}|{s.get('timing')}"
            for s in p.get("lever_steps", [])
        )
        out.append(f"- {p.get('impact_path_id')} (event {p.get('event_id')}, {p.get('materiality')}, "
                   f"balance={p.get('balance_effect')})\n  - {p.get('mechanism')}\n  - levers: {steps}")
    out.append("\n## Interactions")
    out += [f"- {i.get('interaction_id')} {i.get('relation')} paths={i.get('impact_path_ids')} "
            f"({i.get('materiality')})\n  - {i.get('mechanism')}" for i in diag.get("event_interactions", [])]
    out.append("\n## Open questions")
    for u in diag.get("path_uncertainties", []) + diag.get("interaction_uncertainties", []):
        out.append(f"- {u.get('uncertainty_id')} [{u.get('axis_type')}/{u.get('affected_lever_code')}] {u.get('subject')}")
    out.append("\n## Dimensions")
    for d in dims:
        out.append(f"### {d.get('dimension_id')} {d.get('label')} (lever={d.get('primary_lever_code')}, "
                   f"axis={d.get('dimension_type')}, src={d.get('source_uncertainty_ids')})")
        out.append(f"- question: {d.get('description')}\n- rationale: {d.get('rationale')}")
        for v in d.get("values", []):
            st = "; ".join(
                f"{s.get('lever_code')}|{s.get('direction')}|{s.get('level')}|{s.get('scope')}|{s.get('time_window')}"
                for s in v.get("lever_states", [])
            )
            out.append(f"  - {v.get('value_id')} {v.get('label')} [{v.get('pressure_contribution')}] {st}\n"
                       f"    - why: {v.get('assumption_rationale')}")
    out.append(f"\n## notUsed / excluded dims\n{diag.get('excluded_dimensions')}")
    out.append("\n## Excluded scenarios")
    out += [f"- {e}" for e in diag.get("excluded_candidates", [])]
    out.append("\n## Validation warnings")
    out += [f"- [{w.get('code')}] {w.get('message')}" for w in diag.get("validation_warnings", [])]
    out.append("\n## Scenarios")
    for s in scenarios:
        out.append(f"### {s.get('scenario_id')} {s.get('title')}")
        for key in ("global_pressure_band", "scenario_role", "baseline_yn", "probability_score", "dimension_values",
                    "narrative", "global_pressure_rationale", "related_markets"):
            out.append(f"- {key}: {s.get(key)}")
    return "\n".join(out) + "\n"


def metrics(group: dict[str, Any], scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    diag = as_json(group.get("generation_diagnostics")) or {}
    dims = as_json(group.get("dimension_definitions")) or []
    lever_per_dim = Counter(str(d.get("primary_lever_code")) for d in dims)
    return {
        "facts": len(diag.get("event_facts", [])),
        "impact_paths": len(diag.get("impact_paths", [])),
        "path_levers": sorted({s.get("lever_code") for p in diag.get("impact_paths", []) for s in p.get("lever_steps", [])}),
        "interactions": [
            f"{i.get('relation')}:{'×'.join(i.get('impact_path_ids') or [])}" for i in diag.get("event_interactions", [])
        ],
        "open_questions": len(diag.get("path_uncertainties", [])) + len(diag.get("interaction_uncertainties", [])),
        "dimensions": len(dims),
        "dimension_levers": dict(lever_per_dim),
        "dimensions_sharing_lever": sum(n for n in lever_per_dim.values() if n > 1),
        "multi_lever_choices": sum(1 for d in dims for v in d.get("values", []) if len(v.get("lever_states", [])) > 1),
        "scenarios": [
            {
                "band": s.get("global_pressure_band"),
                "probability": float(s.get("probability_score") or 0),
                "baseline": s.get("baseline_yn") == "Y",
                "role": s.get("scenario_role"),
            }
            for s in scenarios
        ],
        "excluded_bands": [e.get("pressure_band") for e in diag.get("excluded_candidates", [])],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-id", type=int, required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out = Path(args.out_dir)
    groups = query("SELECT * FROM tmm_mi_scenario_group_m WHERE scenario_group_id=%s", (args.group_id,))
    if not groups:
        raise SystemExit(f"group {args.group_id} not found")
    group = groups[0]
    scenarios = query(
        "SELECT * FROM tmm_mi_scenario_m WHERE scenario_group_id=%s AND del_yn='N' ORDER BY display_order",
        (args.group_id,),
    )
    dump_json(out / "group.json", group)
    dump_json(out / "scenarios.json", scenarios)
    dump_json(out / "group_events.json",
              query("SELECT * FROM tmm_mi_scenario_group_event_m WHERE scenario_group_id=%s", (args.group_id,)))
    dump_json(out / "operations.json",
              query("SELECT * FROM tmm_mi_scenario_group_operation_m WHERE scenario_group_id=%s", (args.group_id,)))
    (out / "platform_result.md").write_text(render(group, scenarios), encoding="utf-8")
    m = metrics(group, scenarios)
    dump_json(out / "metrics.json", m)
    print(f"group {args.group_id}: status={group.get('status')} stage={group.get('stage')} "
          f"dims={m['dimensions']} levers={m['dimension_levers']} scenarios={[s['band'] for s in m['scenarios']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

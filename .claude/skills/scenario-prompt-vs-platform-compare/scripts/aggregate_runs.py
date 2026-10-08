"""Aggregate structural metrics across N platform runs and N workshop runs.

Usage:
  poetry run python aggregate_runs.py --platform-dir OUT/platform --workshop-dir OUT/workshop --out OUT/aggregate.md

Platform: reads OUT/platform/run_XX/metrics.json (export_group.py) and stage_summary.json (fetch_trace.py).
Workshop: parses OUT/workshop/run_XX/workshop_*/01~05 markdown files (best effort regex).
The output is a mechanical stability table; semantic scoring (rubric) is done by the skill operator.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def workshop_metrics(ws: Path) -> dict[str, Any]:
    def read(name: str) -> str:
        matches = sorted(ws.glob(name))
        return matches[0].read_text(encoding="utf-8") if matches else ""

    s1, s2, s3, s4, s5 = (read(n) for n in ("01_*.md", "02_*.md", "03_*.md", "04_scenarios.md", "05_*.md"))
    dims = re.findall(r"^## Dimension (D\d+)\n(.*?)(?=^## |\Z)", s3, re.M | re.S)
    dim_levers = Counter((re.search(r"primaryDriverTree:\s*`?([a-z_]+)", body) or [None, "?"])[1] for _, body in dims)
    interactions = []
    for _iid, body in re.findall(r"^## Interaction (I\d+)\n(.*?)(?=^## |\Z)", s2, re.M | re.S):
        rel = (re.search(r"relation:\s*(\w+)", body) or [None, "?"])[1]
        events = (re.search(r"sourceEvents:\s*(.+)", body) or [None, "?"])[1].replace(" ", "")
        interactions.append(f"{rel}:{events}")
    table = re.search(r"## Scenario 비교표\n\|.*?\n\|.*?\n(.*?)(?:\n\n|\Z)", s4, re.S)
    scenarios = []
    for row in (table.group(1).splitlines() if table else []):
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) >= 7:
            scenarios.append({"band": cells[4], "probability": float(re.sub(r"[^\d.]", "", cells[5]) or 0),
                              "baseline": cells[6].upper() in {"Y", "YES"}})
    excluded = re.findall(r"^\| (strong_bullish|bullish|balanced|bearish|strong_bearish) \|", s4.split("## 제외 Scenario")[-1], re.M)
    quality = re.search(r"qualityAverage:\s*([\d.]+)", s5)
    decisions = re.search(r"## Dimension 선택·조합 결정\n(.*?)(?=\n## )", s3, re.S)
    return {
        "facts": len(re.findall(r"^\| E\d+-F\d+ \|", s1, re.M)),
        "impact_paths": len(re.findall(r"^### Impact Path ", s1, re.M)),
        "open_questions": len(re.findall(r"^### 열린 질문 ", s1, re.M)) + len(re.findall(r"^## Interaction 열린 질문 ", s2, re.M)),
        "interactions": interactions,
        "dimensions": len(dims),
        "dimension_levers": dict(dim_levers),
        "dimensions_sharing_lever": sum(n for n in dim_levers.values() if n > 1),
        "decision_rows": len(re.findall(r"^\| .* \| (KEEP|CONDITIONAL|MERGE|EXCLUDE|SEPARATE_EFFECT) \|", decisions.group(1), re.M)) if decisions else 0,
        "scenarios": scenarios,
        "excluded_bands": excluded,
        "self_quality_average": float(quality.group(1)) if quality else None,
        "step4a": bool(list(ws.glob("04a_*.md"))),
        "step6": bool(list(ws.glob("06_*.md"))),
    }


def platform_metrics(run: Path) -> dict[str, Any] | None:
    path = run / "metrics.json"
    if not path.exists():
        return None
    m = json.loads(path.read_text(encoding="utf-8"))
    stages = run / "stage_summary.json"
    if stages.exists():
        calls = json.loads(stages.read_text(encoding="utf-8"))["calls"]
        m["llm_calls"] = len(calls)
        m["llm_errors"] = [f"{c['node']}:{(c['error'] or '')[:40]}" for c in calls if c["error"]]
    run_json = run / "run.json"
    if run_json.exists():
        r = json.loads(run_json.read_text(encoding="utf-8"))
        m["status"], m["elapsedSec"] = r.get("status"), r.get("elapsedSec")
        m["retries"] = [f"{x['phase']}:{x['validationCode']}" for x in r.get("retries", [])]
    return m


def summarize(rows: list[dict[str, Any]], label: str) -> list[str]:
    if not rows:
        return [f"_{label}: 실행 결과 없음_"]

    def nums(key: str) -> str:
        values = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not values:
            return "-"
        return f"{statistics.mean(values):.2f} (min {min(values)}, max {max(values)})"

    bands = Counter(s["band"] for r in rows for s in r.get("scenarios", []))
    baselines = Counter(next((s["band"] for s in r.get("scenarios", []) if s.get("baseline")), "-") for r in rows)
    inter = Counter(i for r in rows for i in r.get("interactions", []))
    return [
        f"| 지표 | {label} (n={len(rows)}) |", "|---|---|",
        f"| Fact 수 | {nums('facts')} |",
        f"| Impact Path 수 | {nums('impact_paths')} |",
        f"| 열린 질문 수 | {nums('open_questions')} |",
        f"| Dimension 수 | {nums('dimensions')} |",
        f"| 같은 primary Lever를 공유한 Dimension 수 | {nums('dimensions_sharing_lever')} |",
        f"| Interaction (relation:events) 빈도 | {dict(inter)} |",
        f"| Scenario band 분포 | {dict(bands)} |",
        f"| baseline band 분포 | {dict(baselines)} |",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-dir", required=True)
    parser.add_argument("--workshop-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    platform = {p.name: m for p in sorted(Path(args.platform_dir).glob("run_*")) if (m := platform_metrics(p))}
    workshop = {}
    for run in sorted(Path(args.workshop_dir).glob("run_*")):
        ws = next(iter(sorted(run.glob("workshop_*"))), None)
        if ws and (ws / "04_scenarios.md").exists():
            workshop[run.name] = workshop_metrics(ws)

    lines = ["# 구조 지표 집계 (자동)", "", "## 요약", ""]
    lines += summarize(list(platform.values()), "플랫폼") + [""] + summarize(list(workshop.values()), "워크숍") + [""]
    lines += ["## 플랫폼 run별", "", "| run | status | elapsed | retries | Dim | Dim Lever | 공유 | Interaction | bands(baseline*) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name, m in platform.items():
        bands = ", ".join(f"{s['band']}{'*' if s['baseline'] else ''}:{s['probability']:.0f}" for s in m["scenarios"])
        lines.append(f"| {name} | {m.get('status')} | {m.get('elapsedSec')} | {m.get('retries')} | {m['dimensions']} | "
                     f"{m['dimension_levers']} | {m['dimensions_sharing_lever']} | {m['interactions']} | {bands} |")
    lines += ["", "## 워크숍 run별", "", "| run | Fact | Path | Dim | Dim Lever | 공유 | 결정표 행 | Interaction | bands(baseline*) | 자체 품질 | 4a/6 |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, m in workshop.items():
        bands = ", ".join(f"{s['band']}{'*' if s['baseline'] else ''}:{s['probability']:.0f}" for s in m["scenarios"])
        lines.append(f"| {name} | {m['facts']} | {m['impact_paths']} | {m['dimensions']} | {m['dimension_levers']} | "
                     f"{m['dimensions_sharing_lever']} | {m['decision_rows']} | {m['interactions']} | {bands} | "
                     f"{m['self_quality_average']} | {m['step4a']}/{m['step6']} |")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path(args.out).with_suffix(".json").write_text(
        json.dumps({"platform": platform, "workshop": workshop}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"aggregate written: {args.out} (platform runs={len(platform)}, workshop runs={len(workshop)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

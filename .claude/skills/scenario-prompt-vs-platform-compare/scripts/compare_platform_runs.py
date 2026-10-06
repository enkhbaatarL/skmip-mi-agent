"""Before/after comparison of two platform run sets (mode B: platform change verification, no workshop).

Usage:
  poetry run python compare_platform_runs.py --baseline {WORK_A}/platform --candidate {WORK_B}/platform \
      --out {WORK_B}/compare_before_after.md [--target double_counting,retries] [--baseline-label "변경 전"] \
      [--candidate-label "변경 후"]

Each set holds run_XX folders already processed by export_group.py, fetch_trace.py and structural_checks.py.
Optional per-run rubric: run_XX/rubric.json = {"J-01": 3, ..., "J-11": 3, "scorer": "..."}.

Verdict rule (SKILL.md "평가 기준"):
  1. every metric listed in --target improved,
  2. no other layer-① metric and no guardrail regressed,
  3. rubric average did not drop (if rubric.json exists on both sides).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RUBRIC_IDS = ("J-01", "J-02", "J-03", "J-04", "J-05", "J-06", "J-11")


def runs(root: Path) -> list[dict[str, Any]]:
    rows = []
    for run in sorted(root.glob("run_*")):
        structural = run / "structural.json"
        if not structural.exists():
            continue
        row = json.loads(structural.read_text(encoding="utf-8"))
        stage = run / "stage_summary.json"
        calls = json.loads(stage.read_text(encoding="utf-8"))["calls"] if stage.exists() else []
        row["llm_seconds"] = round(sum(c.get("durationSec") or 0 for c in calls), 1)
        row["max_dimension_seconds"] = max((c["durationSec"] for c in calls if c["node"] == "design_model_lever_dimensions"), default=None)
        rubric = run / "rubric.json"
        row["rubric"] = json.loads(rubric.read_text(encoding="utf-8")) if rubric.exists() else None
        row["run"] = run.name
        rows.append(row)
    return rows


# metric name -> (description, extractor returning a number per run, lower_is_better)
METRICS: dict[str, tuple[str, Any, bool]] = {
    "double_counting": ("이중 계산 시나리오 수", lambda r: r["double_counting_scenarios"], True),
    "iu_dimensions": ("Interaction 질문으로 만든 Dimension 수", lambda r: len(r["dimensions_from_interaction_questions"]), True),
    "shared_lever_dims": ("같은 Lever 공유 Dimension 수 (신호)", lambda r: sum(r["dimensions_sharing_lever_signal"].values()), True),
    "core_fact_missing": ("제목 핵심 Fact 누락 이벤트 수", lambda r: len(r["core_fact_missing_events"]), True),
    "core_fact_not_primary": ("핵심 Fact가 Primary가 아닌 이벤트 수", lambda r: len(r["core_fact_not_primary_events"]), True),
    "facts_total": ("선택 Fact 수", lambda r: r["facts_total"], False),
    "paths_without_primary": ("primary role 없는 Path 수", lambda r: len(r["paths_without_primary_role"]), True),
    "balance_mismatch": ("balance·Lever 방향 불일치 수", lambda r: len(r["balance_direction_mismatch"]), True),
    "retries": ("검증 실패 재시도 수", lambda r: sum(r["retries"].values()), True),
    "llm_errors": ("LLM 호출 오류(504 등) 수", lambda r: len(r["llm_errors"]), True),
    "transliteration": ("음역 횟수", lambda r: sum(r["transliteration"].values()), True),
    "english_words": ("영문 일반어 횟수 (신호)", lambda r: sum(r["english_words_signal"].values()), True),
    "baseline_all_balanced": ("중간값 baseline run 수", lambda r: int(r["baseline_all_balanced"]), True),
}
GUARDRAILS: dict[str, tuple[str, Any]] = {
    "failed": ("생성 실패", lambda r: int(r.get("status") != "succeeded")),
    "elapsed": ("생성 시간(초)", lambda r: r.get("elapsed_sec") or 0),
    "dimension_seconds": ("Dimension 단계 최대 시간(초)", lambda r: r.get("max_dimension_seconds") or 0),
}


def mean(values: list[float]) -> float:
    return round(statistics.mean(values), 2) if values else float("nan")


def stability(rows: list[dict[str, Any]]) -> dict[str, str]:
    def share(key: Any) -> str:
        counts = Counter(key(r) for r in rows)
        top, n = counts.most_common(1)[0] if counts else ("-", 0)
        return f"{n}/{len(rows)} ({top})"

    return {
        "Dimension 수 일치": share(lambda r: r["dimensions"]),
        "Dimension Lever 구성 일치": share(lambda r: json.dumps(r["dimension_levers"], sort_keys=True)),
        "Interaction 구성 일치": share(lambda r: json.dumps(sorted(x.split(":")[0] for x in r["interactions"]))),
        "baseline band 일치": share(lambda r: r["baseline_band"]),
    }


def rubric_avg(rows: list[dict[str, Any]]) -> float | None:
    scored = [r["rubric"] for r in rows if r.get("rubric")]
    if not scored:
        return None
    return mean([statistics.mean(float(s[j]) for j in RUBRIC_IDS if j in s) for s in scored])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--target", default="", help="쉼표로 구분한 목표 지표 키 (METRICS 키)")
    parser.add_argument("--baseline-label", default="변경 전")
    parser.add_argument("--candidate-label", default="변경 후")
    parser.add_argument("--elapsed-tolerance", type=float, default=0.3, help="허용 시간 증가율 (기본 30%)")
    args = parser.parse_args()
    base, cand = runs(Path(args.baseline)), runs(Path(args.candidate))
    if not base or not cand:
        raise SystemExit("structural.json이 있는 run이 양쪽에 필요합니다")
    targets = [t.strip() for t in args.target.split(",") if t.strip()]
    unknown = [t for t in targets if t not in METRICS]
    if unknown:
        raise SystemExit(f"알 수 없는 target: {unknown}. 가능: {sorted(METRICS)}")

    lines = [f"# 플랫폼 변경 전후 비교 ({args.baseline_label} n={len(base)} / {args.candidate_label} n={len(cand)})", ""]
    lines += ["## ① 구조 결함 (run 평균)", "", f"| 지표 | {args.baseline_label} | {args.candidate_label} | 판정 |", "|---|---:|---:|---|"]
    improved, regressed = [], []
    for key, (label, fn, lower_better) in METRICS.items():
        b, c = mean([fn(r) for r in base]), mean([fn(r) for r in cand])
        better = c < b if lower_better else c > b
        worse = c > b if lower_better else c < b
        mark = "개선" if better else ("악화" if worse else "동일")
        if better:
            improved.append(key)
        if worse:
            regressed.append(key)
        star = " ★목표" if key in targets else ""
        lines.append(f"| {label} (`{key}`){star} | {b} | {c} | {mark} |")

    lines += ["", "## ④ 가드레일", "", f"| 지표 | {args.baseline_label} | {args.candidate_label} | 판정 |", "|---|---:|---:|---|"]
    guard_fail = []
    for key, (label, fn) in GUARDRAILS.items():
        b, c = mean([fn(r) for r in base]), mean([fn(r) for r in cand])
        limit = b * (1 + args.elapsed_tolerance) if key != "failed" else b
        bad = c > limit
        if bad:
            guard_fail.append(key)
        lines.append(f"| {label} | {b} | {c} | {'초과' if bad else '정상'} |")

    lines += ["", "## ③ 안정성", "", f"| 항목 | {args.baseline_label} | {args.candidate_label} |", "|---|---|---|"]
    sb, sc = stability(base), stability(cand)
    lines += [f"| {k} | {sb[k]} | {sc[k]} |" for k in sb]

    rb, rc = rubric_avg(base), rubric_avg(cand)
    lines += ["", "## ② rubric 평균", "", f"- {args.baseline_label}: {rb if rb is not None else '미채점'}",
              f"- {args.candidate_label}: {rc if rc is not None else '미채점'}"]

    target_ok = all(t in improved for t in targets) if targets else None
    other_regressions = [k for k in regressed if k not in targets]
    rubric_ok = None if rb is None or rc is None else rc >= rb
    verdict = (
        "개선 인정" if target_ok and not other_regressions and not guard_fail and rubric_ok is not False
        else "판정 보류" if target_ok is None
        else "개선 불인정"
    )
    lines += [
        "", "## 판정", "",
        f"- 목표 지표 개선: {target_ok if target_ok is not None else '목표 미지정'} ({', '.join(targets) or '-'})",
        f"- 목표 외 구조 지표 악화: {other_regressions or '없음'}",
        f"- 가드레일 초과: {guard_fail or '없음'}",
        f"- rubric 하락 없음: {rubric_ok if rubric_ok is not None else '미채점'}",
        f"- **결론: {verdict}**",
        *(
            [f"- ⚠️ run 수 부족({args.baseline_label} {len(base)}회 / {args.candidate_label} {len(cand)}회): "
             "목표와 무관한 지표의 개선·악화는 run 간 무작위 변동일 수 있습니다. 양쪽 3회 이상을 권장합니다."]
            if min(len(base), len(cand)) < 3 else []
        ),
        "",
        "> 자동 판정은 신호입니다. '(신호)' 지표와 rubric 감점 근거는 결과를 직접 읽고 확인한 뒤 보고서에 적습니다.",
    ]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-8:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

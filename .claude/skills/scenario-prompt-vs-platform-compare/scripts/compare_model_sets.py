"""Compare several platform run sets side by side (e.g. one set per LLM model or parameter setting).

Usage:
  poetry run python compare_model_sets.py --set "gpt-5.5=DIR_A" --set "terra=DIR_B" ... --out OUT.md \
      [--price "skmidev-gpt-5.5-20260424=5/30"] [--price "skmidev-gpt-5.6-terra-20260709-mip=2/12"]

Each DIR holds run_XX folders processed by export_group.py, fetch_trace.py and structural_checks.py.
--price is USD per 1M input/output tokens per deployment; cost is computed from trace token usage.
The model actually used is read from the trace (mlflow.llm.model) so a wrong restart is visible.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from compare_platform_runs import METRICS, rubric_avg, stability


def models_in_trace(run: Path) -> list[str]:
    path = run / "trace.json"
    if not path.exists():
        return []
    spans = json.loads(path.read_text(encoding="utf-8"))["data"]["spans"]
    names = Counter()
    for span in spans:
        model = span.get("attributes", {}).get("mlflow.llm.model")
        if model and span["name"].startswith("llm.structured"):
            names[json.loads(model) if model.startswith('"') else model] += 1
    return sorted(names)


def load_set(root: Path, prices: dict[str, tuple[float, float]]) -> list[dict[str, Any]]:
    rows = []
    for run in sorted(root.glob("run_*")):
        structural = run / "structural.json"
        if not structural.exists():
            continue
        row = json.loads(structural.read_text(encoding="utf-8"))
        calls = json.loads((run / "stage_summary.json").read_text(encoding="utf-8"))["calls"] if (run / "stage_summary.json").exists() else []
        create = [c for c in calls if c.get("label") == "create"]
        row["models"] = models_in_trace(run)
        row["tokens_in"] = sum((c.get("usage") or {}).get("input_tokens") or 0 for c in create)
        row["tokens_out"] = sum((c.get("usage") or {}).get("output_tokens") or 0 for c in create)
        price = next((prices[m] for m in row["models"] if m in prices), None)
        row["cost"] = (row["tokens_in"] * price[0] + row["tokens_out"] * price[1]) / 1_000_000 if price else None
        row["dimension_seconds"] = max((c["durationSec"] for c in create if c["node"] == "design_model_lever_dimensions" and not c.get("error")), default=None)
        rubric = run / "rubric.json"
        row["rubric"] = json.loads(rubric.read_text(encoding="utf-8")) if rubric.exists() else None
        row["run"] = run.name
        rows.append(row)
    return rows


def fmt(values: list[float | None], digits: int = 2) -> str:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return "-"
    mean = statistics.mean(nums)
    return f"{mean:.{digits}f}" if len(nums) == 1 else f"{mean:.{digits}f} ({min(nums):g}~{max(nums):g})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", action="append", required=True, help="label=DIR")
    parser.add_argument("--price", action="append", default=[], help="deployment=input/output USD per 1M tokens")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    prices = {}
    for item in args.price:
        name, value = item.split("=", 1)
        a, b = value.split("/")
        prices[name] = (float(a), float(b))
    sets = {}
    for item in args.set:
        label, path = item.split("=", 1)
        sets[label] = load_set(Path(path), prices)
    labels = list(sets)

    head = "| 지표 | " + " | ".join(labels) + " |"
    sep = "|---|" + "---:|" * len(labels)
    lines = ["# 모델·파라미터 세트 비교", "", "## 실행 정보", "", head, sep]
    lines.append("| run 수 | " + " | ".join(str(len(sets[l])) for l in labels) + " |")
    lines.append("| 실제 사용 모델 (trace) | " + " | ".join(", ".join(sorted({m for r in sets[l] for m in r["models"]})) or "-" for l in labels) + " |")
    lines.append("| 그룹 | " + " | ".join(", ".join(str(r["group_id"]) for r in sets[l]) for l in labels) + " |")

    lines += ["", "## ① 구조 결함 (run 평균, 괄호는 최소~최대)", "", head, sep]
    for key, (label, fn, _lower) in METRICS.items():
        lines.append(f"| {label} | " + " | ".join(fmt([fn(r) for r in sets[l]]) for l in labels) + " |")

    lines += ["", "## ④ 시간·비용", "", head, sep]
    lines.append("| 생성 실패 | " + " | ".join(fmt([int(r.get("status") != "succeeded") for r in sets[l]]) for l in labels) + " |")
    lines.append("| 생성 시간(초) | " + " | ".join(fmt([r.get("elapsed_sec") for r in sets[l]], 1) for l in labels) + " |")
    lines.append("| Dimension 단계(초) | " + " | ".join(fmt([r.get("dimension_seconds") for r in sets[l]], 1) for l in labels) + " |")
    lines.append("| 입력 토큰 | " + " | ".join(fmt([r["tokens_in"] for r in sets[l]], 0) for l in labels) + " |")
    lines.append("| 출력 토큰 | " + " | ".join(fmt([r["tokens_out"] for r in sets[l]], 0) for l in labels) + " |")
    lines.append("| 비용 USD/그룹 | " + " | ".join(fmt([r["cost"] for r in sets[l]], 3) for l in labels) + " |")

    lines += ["", "## ③ 안정성", "", head, "|---|" + "---|" * len(labels)]
    stab = {l: stability(sets[l]) for l in labels}
    for key in stab[labels[0]]:
        lines.append(f"| {key} | " + " | ".join(stab[l][key] for l in labels) + " |")

    lines += ["", "## ② rubric 평균", "", head, sep,
              "| rubric 평균 | " + " | ".join(str(rubric_avg(sets[l]) if rubric_avg(sets[l]) is not None else "미채점") for l in labels) + " |",
              "", "> 자동 지표는 신호입니다. '(신호)' 지표는 결과를 읽고 확정합니다. run 수가 3 미만이면 차이는 변동일 수 있습니다."]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

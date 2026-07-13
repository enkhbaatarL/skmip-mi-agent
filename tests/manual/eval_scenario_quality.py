from __future__ import annotations

"""Evaluate scenario-pipeline artifacts without re-running the pipeline.

The command is deliberately a manual-tool entry point: it reads one persisted
pipeline batch, records reproducible results in the same SQLite database, and
writes a self-contained ``quality_report.md`` next to that batch.
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.manual.eval_trace_utils import collect_trace_summary
from tests.manual.eval_validation_probe import MUTATION_IDS, run_probe
from tests.manual.quality_eval.artifacts import BatchArtifacts, RunArtifacts, load_batch
from tests.manual.quality_eval.golden import GoldenCase, find_incidental_matches, load_golden_cases
from tests.manual.quality_eval.judge import JudgeResult, PROMPT_VERSION, judge_scenario_set, judge_signposts
from tests.manual.quality_eval.layer1_checks import CheckResult, run_layer1_checks
from tests.manual.quality_eval.report import collect_performance_stats, render_quality_report
from tests.manual.quality_eval.runtime_config import AGENT_ALIASES, load_runtime_target
from tests.manual.quality_eval.storage import QualityStore


DEFAULT_OUTPUT_ROOT = Path("local/output/sync_pipeline_api_test")
DEFAULT_GOLDEN_DIR = Path("tests/manual/golden_cases")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate persisted Scenario Group sync-pipeline quality artifacts")
    parser.add_argument("--batch-id", help="batch ID; defaults to the newest artifact directory")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--db-path", type=Path, help="defaults to <output-root>/sync_pipeline_metrics.sqlite3")
    parser.add_argument("--agent", choices=sorted(AGENT_ALIASES), help="agent target alias: mi-vm or local")
    parser.add_argument("--base-url", help="agent URL; takes precedence over --agent and test_info.local")
    parser.add_argument("--user-id", type=int, help="agent user ID; defaults to 10603 or test_info.local")
    parser.add_argument("--test-info", type=Path, help="local config; defaults to skill/test_info.local when present")
    parser.add_argument("--judge-limit", type=int, help="maximum successful groups to send to the bounded LLM judge")
    parser.add_argument(
        "--stability-runs",
        type=int,
        choices=(1, 2),
        default=1,
        help="run each fixed judge input once or twice; 2 reports verdict agreement for the acceptance smoke",
    )
    parser.add_argument("--no-judge", action="store_true", help="run Layer 1/report only (no LLM calls)")
    parser.add_argument("--mlflow-uri", help="optional MLflow tracking URI for Layer 3 diagnosis")
    parser.add_argument("--probe", action="store_true", help="run V-00…V-07 validation mutation probes for successful groups")
    parser.add_argument("--probe-base-url", help="Agent URL; required with --probe")
    parser.add_argument("--probe-user-id", type=int, help="Agent user ID; required with --probe")
    parser.add_argument("--probe-mutations", default=",".join(MUTATION_IDS), help="comma-separated V-00…V-07 list")
    parser.add_argument("--probe-timeout", type=float, default=120.0)
    parser.add_argument("--golden", action="store_true", help="evaluate golden-case event artifacts and show labels for review")
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument(
        "--golden-record",
        type=Path,
        help="reviewed JSON records: golden_id, matched, missed, extra, optional judge_ids/detail",
    )
    return parser


async def _judge_run(run: RunArtifacts) -> list[JudgeResult]:
    """Keep the two-call judge limit explicit and co-located with orchestration."""
    return [await judge_scenario_set(run), await judge_signposts(run)]


def _find_golden_runs(batch: BatchArtifacts, output_root: Path, cases: list[GoldenCase]) -> list[RunArtifacts]:
    """Find current-batch cases first, then the newest persisted batch per case."""
    by_event = {run.mi_event_id: run for run in batch.runs}
    selected: list[RunArtifacts] = []
    for case in cases:
        run = by_event.get(case.mi_event_id)
        if run is None and case.artifacts:
            artifact_dir = Path(case.artifacts)
            if not artifact_dir.is_absolute():
                artifact_dir = PROJECT_ROOT / artifact_dir
            if artifact_dir.is_dir():
                try:
                    artifact_batch = load_batch(artifact_dir.parent, artifact_dir.name)
                    run = next((item for item in artifact_batch.runs if item.mi_event_id == case.mi_event_id), None)
                except (FileNotFoundError, ValueError):
                    run = None
        if run is None:
            candidates: list[tuple[str, RunArtifacts]] = []
            for directory in output_root.iterdir() if output_root.is_dir() else []:
                if not directory.is_dir():
                    continue
                try:
                    candidate_batch = load_batch(output_root, directory.name)
                except (FileNotFoundError, ValueError):
                    continue
                candidates.extend((directory.name, item) for item in candidate_batch.runs if item.mi_event_id == case.mi_event_id)
            if candidates:
                _, run = max(candidates, key=lambda item: item[0])
        if run is not None and run.status == "success" and all(item.mi_event_id != run.mi_event_id for item in selected):
            selected.append(run)
    return selected


def _load_review_records(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("--golden-record must be a JSON array of objects")
    required = {"golden_id", "matched", "missed", "extra"}
    if any(not required <= set(item) for item in payload):
        raise ValueError("every --golden-record item requires golden_id, matched, missed, extra")
    return payload


def _golden_notices(
    cases: list[GoldenCase],
    *,
    formal: bool,
    evaluated_event_ids: set[int] | None = None,
) -> list[str]:
    notices: list[str] = []
    for case in cases:
        labels = ", ".join(f"{label.label_id}({label.expected_judge}, type {label.type})" for label in case.labels)
        if formal and evaluated_event_ids is not None and case.mi_event_id not in evaluated_event_ids:
            prefix = "증적 없음 또는 pipeline 성공 run 없음: 정식 채점 SKIP"
        else:
            prefix = "정식 judge 입력/검토 대상" if formal else "별도 --golden 실행 필요"
        notices.append(f"miEventId={case.mi_event_id}: {prefix} — {case.path.name}; labels: {labels}")
    return notices


def _golden_review_summary(cases: list[GoldenCase], records: list[dict[str, Any]]) -> list[str]:
    """Summarize reviewer-approved recall while preserving manual semantic matching."""
    matched_ids: set[str] = set()
    for record in records:
        matched = record.get("matched")
        if isinstance(matched, list):
            matched_ids.update(map(str, matched))
    labels = [label for case in cases for label in case.labels]
    payload_labels = [label for label in labels if label.type in {"A", "C", "D"}]
    external_labels = [label for label in labels if label.type == "B"]
    return [
        f"golden recall (Type A/C/D): {sum(label.label_id in matched_ids for label in payload_labels)}/{len(payload_labels)}",
        f"golden recall (Type B, external fact): {sum(label.label_id in matched_ids for label in external_labels)}/{len(external_labels)}",
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        target = load_runtime_target(
            agent=args.agent,
            base_url=args.base_url,
            user_id=args.user_id,
            mlflow_uri=args.mlflow_uri,
            test_info_path=args.test_info,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.judge_limit is not None and args.judge_limit < 0:
        raise SystemExit("--judge-limit must be zero or greater")
    if args.golden_record and not args.golden:
        raise SystemExit("--golden-record requires --golden")
    probe_base_url = args.probe_base_url or target.base_url
    probe_user_id = args.probe_user_id if args.probe_user_id is not None else target.user_id
    if args.probe and not probe_base_url:
        raise SystemExit("--probe requires --base-url/--agent or a base_url/agent entry in test_info.local")
    probe_mutations = [item.strip().upper() for item in args.probe_mutations.split(",") if item.strip()]
    unknown_mutations = set(probe_mutations) - set(MUTATION_IDS)
    if unknown_mutations:
        raise SystemExit(f"unknown --probe-mutations: {', '.join(sorted(unknown_mutations))}")

    batch = load_batch(args.output_root, args.batch_id)
    print(f"quality batch: {batch.batch_id} ({len(batch.runs)} pipeline runs)")
    db_path = args.db_path or args.output_root / "sync_pipeline_metrics.sqlite3"
    successful = [run for run in batch.runs if run.status == "success"]
    cases = load_golden_cases(args.golden_dir)
    incidental = find_incidental_matches([run.mi_event_id for run in batch.runs], cases)
    judge_targets = list(successful)
    golden_cases: list[GoldenCase] = []
    if args.golden:
        golden_cases = cases
        judge_targets = _find_golden_runs(batch, args.output_root, cases)
    if args.judge_limit is not None:
        judge_targets = judge_targets[: args.judge_limit]

    evaluated_runs = {run.mi_event_id: run for run in successful}
    evaluated_runs.update({run.mi_event_id: run for run in judge_targets})
    layer1: dict[int, list[CheckResult]] = {event_id: run_layer1_checks(run) for event_id, run in evaluated_runs.items()}
    judge_results: dict[int, list[JudgeResult]] = {}
    judge_errors: list[str] = []
    probe_results: list[dict[str, str]] = []
    stability_agreements: list[bool] = []
    trace = (
        {
            run.mi_event_id: collect_trace_summary(
                run.scenario_group_id,
                tracking_uri=target.mlflow_uri,
                tracking_username=target.mlflow_username,
                tracking_password=target.mlflow_password,
            )
            for run in evaluated_runs.values()
        }
        if target.mlflow_uri
        else {}
    )

    with QualityStore(db_path) as store:
        eval_ids: dict[int, int] = {}
        for run in evaluated_runs.values():
            eval_id = store.record_eval(
                batch_id=batch.batch_id,
                mi_event_id=run.mi_event_id,
                scenario_group_id=run.scenario_group_id,
                judge_model=None,
                prompt_version=PROMPT_VERSION if not args.no_judge else None,
            )
            eval_ids[run.mi_event_id] = eval_id
            store.record_checks(eval_id, layer1[run.mi_event_id])

            if args.probe:
                table_payload = run.step1 or run.step2
                table = table_payload.get("table") if table_payload else None
                if not isinstance(table, dict) or run.scenario_group_id is None:
                    skipped = {
                        "mutation_id": "V-ALL",
                        "expected": "successful run with scenarioGroup/table",
                        "observed": "missing artifact",
                        "verdict": "SKIP",
                        "detail": f"miEventId={run.mi_event_id}: scenarioGroup/table missing",
                    }
                    probe_results.append(skipped)
                    store.record_probe(eval_id=eval_id, **skipped)
                else:
                    try:
                        results = run_probe(
                            base_url=probe_base_url,
                            scenario_group_id=run.scenario_group_id,
                            user_id=probe_user_id,
                            table=table,
                            mutation_ids=probe_mutations,
                            timeout=args.probe_timeout,
                            dry_run=False,
                        )
                    except Exception as exc:  # Live API availability is infra, not a semantic quality result.
                        results = [
                            {
                                "mutation_id": "V-ALL",
                                "expected": "validation mutation execution",
                                "observed": "probe infra error",
                                "verdict": "SKIP",
                                "detail": f"miEventId={run.mi_event_id}: {exc}",
                            },
                        ]
                    for result in results:
                        result["detail"] = f"miEventId={run.mi_event_id}; {result['detail']}"
                        probe_results.append(result)
                        store.record_probe(eval_id=eval_id, **result)

        if not args.no_judge:
            for run in judge_targets:
                try:
                    results = asyncio.run(_judge_run(run))
                except Exception as exc:  # LLM/network boundary; retain deterministic evaluation and report infra error.
                    judge_errors.append(f"miEventId={run.mi_event_id}: judge infra failure — {exc}")
                    continue
                judge_results[run.mi_event_id] = results
                for result in results:
                    store.record_judge(eval_ids[run.mi_event_id], result)
                if args.stability_runs == 2:
                    try:
                        repeated = asyncio.run(_judge_run(run))
                    except Exception as exc:
                        judge_errors.append(f"miEventId={run.mi_event_id}: stability judge infra failure — {exc}")
                    else:
                        for result in repeated:
                            store.record_judge(eval_ids[run.mi_event_id], result)
                        first_verdicts = {item.judge_id: item.verdict for result in results for item in result.items}
                        repeated_verdicts = {item.judge_id: item.verdict for result in repeated for item in result.items}
                        stability_agreements.extend(
                            first_verdicts[judge_id] == repeated_verdicts.get(judge_id)
                            for judge_id in first_verdicts
                        )
                store.update_eval_metadata(
                    eval_ids[run.mi_event_id],
                    judge_model=results[0].model,
                    prompt_version=results[0].prompt_version,
                )

        review_records = _load_review_records(args.golden_record)
        for record in review_records:
            target_eval = eval_ids.get(int(record.get("mi_event_id", 0)))
            store.record_golden(
                eval_id=target_eval,
                golden_id=str(record["golden_id"]),
                matched=record["matched"],
                missed=record["missed"],
                extra=record["extra"],
                judge_ids=record.get("judge_ids", []),
                detail=str(record.get("detail", "reviewed through --golden-record")),
            )

    notices = (
        _golden_notices(
            golden_cases,
            formal=not args.no_judge,
            evaluated_event_ids={run.mi_event_id for run in judge_targets} if not args.no_judge else set(),
        )
        if args.golden
        else _golden_notices(incidental, formal=False)
    )
    notices.extend(judge_errors)
    if args.golden:
        if review_records:
            notices.extend(_golden_review_summary(golden_cases, review_records))
            notices.extend(
                "golden "
                f"{record['golden_id']}: matched={record['matched']}, missed={record['missed']}, extra={record['extra']}"
                for record in review_records
            )
        else:
            notices.append("골든 라벨의 matched/missed/extra는 검토 후 --golden-record JSON으로 기록해야 합니다.")
    if args.stability_runs == 2:
        agreed = sum(stability_agreements)
        total = len(stability_agreements)
        rate = agreed / total if total else 0.0
        notices.append(f"judge stability (fixed inputs, two runs): {agreed}/{total} ({rate:.0%}); acceptance threshold 80%")
    report = render_quality_report(
        batch,
        layer1,
        judge_results,
        collect_performance_stats(db_path, batch.batch_id),
        probe_results,
        golden_notice=notices,
        trace=trace,
    )
    report_path = batch.batch_dir / "quality_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"quality report: {report_path}")
    print(f"SQLite: {db_path}")
    if judge_errors:
        print(f"judge infra failures: {len(judge_errors)} (report records them separately)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

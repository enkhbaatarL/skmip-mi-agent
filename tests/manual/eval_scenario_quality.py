from __future__ import annotations

"""Evaluate scenario-pipeline artifacts without re-running the pipeline.

The command is deliberately a manual-tool entry point: it reads one persisted
pipeline batch, records reproducible results in the same SQLite database, and
writes a self-contained ``quality_report.md`` next to that batch.
"""

import argparse
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
from tests.manual.quality_eval.judge import (
    JudgeResult,
    PROMPT_VERSION,
    build_agent_judge_input,
    load_agent_judge_output,
    write_agent_judge_input,
)
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
    parser.add_argument("--judge-limit", type=int, help="maximum successful groups to send to the bounded agent judge")
    parser.add_argument(
        "--stability-runs",
        type=int,
        choices=(1, 2),
        default=1,
        help="request one or two independent passes from the skill runtime model",
    )
    parser.add_argument("--no-judge", action="store_true", help="run Layer 1/report only")
    parser.add_argument(
        "--judge-input",
        type=Path,
        help="agent judge request path; defaults to <batch>/quality_judge_input.json",
    )
    parser.add_argument(
        "--judge-result",
        type=Path,
        help="agent-produced result path; defaults to <batch>/quality_judge.json",
    )
    parser.add_argument(
        "--prepare-judge-only",
        action="store_true",
        help="write the agent judge request and exit before persistence/report generation",
    )
    parser.add_argument("--mlflow-uri", help="optional MLflow tracking URI for Layer 3 diagnosis")
    parser.add_argument(
        "--probe", action="store_true", help="run V-00…V-09 validation mutation probes for successful groups"
    )
    parser.add_argument("--probe-base-url", help="Agent URL; required with --probe")
    parser.add_argument("--probe-user-id", type=int, help="Agent user ID; required with --probe")
    parser.add_argument("--probe-mutations", default=",".join(MUTATION_IDS), help="comma-separated V-00…V-09 list")
    parser.add_argument("--probe-timeout", type=float, default=120.0)
    parser.add_argument(
        "--golden", action="store_true", help="evaluate golden-case event artifacts and show labels for review"
    )
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument(
        "--golden-record",
        type=Path,
        help="reviewed JSON records: golden_id, matched, missed, extra, optional judge_ids/detail",
    )
    return parser


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
                candidates.extend(
                    (directory.name, item) for item in candidate_batch.runs if item.mi_event_id == case.mi_event_id
                )
            if candidates:
                _, run = max(candidates, key=lambda item: item[0])
        if (
            run is not None
            and run.status == "success"
            and all(item.mi_event_id != run.mi_event_id for item in selected)
        ):
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
    if args.prepare_judge_only and args.no_judge:
        raise SystemExit("--prepare-judge-only cannot be used with --no-judge")
    if args.judge_result and args.no_judge:
        raise SystemExit("--judge-result cannot be used with --no-judge")
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
    layer1: dict[int, list[CheckResult]] = {
        event_id: run_layer1_checks(run) for event_id, run in evaluated_runs.items()
    }
    judge_results: dict[int, list[JudgeResult]] = {}
    judge_errors: list[str] = []
    probe_results: list[dict[str, str]] = []
    stability_agreements: list[bool] = []
    judge_input_path = args.judge_input or batch.batch_dir / "quality_judge_input.json"
    judge_result_path = args.judge_result or batch.batch_dir / "quality_judge.json"
    if not args.no_judge:
        deterministic_checks = {
            event_id: [
                {
                    "checkId": check.check_id,
                    "status": check.status,
                    "detail": check.detail,
                    "offenders": check.offenders,
                }
                for check in checks
            ]
            for event_id, checks in layer1.items()
        }
        judge_input = build_agent_judge_input(
            batch_id=batch.batch_id,
            runs=judge_targets,
            stability_runs=args.stability_runs,
            deterministic_checks=deterministic_checks,
        )
        write_agent_judge_input(judge_input_path, judge_input)
        print(f"agent judge input: {judge_input_path}")
        print(f"agent judge result expected: {judge_result_path}")
        if args.prepare_judge_only:
            return 0
        if judge_result_path.is_file():
            try:
                judge_results, stability_agreements = load_agent_judge_output(
                    judge_result_path,
                    batch_id=batch.batch_id,
                    expected_event_ids=[run.mi_event_id for run in judge_targets],
                    stability_runs=args.stability_runs,
                )
            except (OSError, ValueError) as exc:
                judge_errors.append(f"agent judge result validation failure — {exc}")
        else:
            judge_errors.append(
                "agent judge pending — skill runtime model must evaluate "
                f"{judge_input_path} and write {judge_result_path}",
            )
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

        if judge_results:
            for run in judge_targets:
                results = judge_results.get(run.mi_event_id)
                if not results:
                    continue
                for result in results:
                    store.record_judge(eval_ids[run.mi_event_id], result)
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
            formal=bool(judge_results),
            evaluated_event_ids=set(judge_results),
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
    if args.stability_runs == 2 and judge_results:
        agreed = sum(stability_agreements)
        total = len(stability_agreements)
        rate = agreed / total if total else 0.0
        notices.append(
            f"judge stability (fixed inputs, two runs): {agreed}/{total} ({rate:.0%}); acceptance threshold 80%"
        )
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
        print(f"agent judge notices: {len(judge_errors)} (report records them separately)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

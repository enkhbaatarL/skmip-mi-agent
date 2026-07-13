from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
from typing import Any


MANUAL_DIR = Path(__file__).resolve().parents[1] / "manual"
if str(MANUAL_DIR) not in sys.path:
    sys.path.insert(0, str(MANUAL_DIR))

from quality_eval.artifacts import RunArtifacts, load_batch
from quality_eval.golden import find_incidental_matches, load_golden_cases
from quality_eval.layer1_checks import CheckResult, run_layer1_checks
from quality_eval.report import render_quality_report
from quality_eval.runtime_config import DEFAULT_USER_ID, load_runtime_target
from quality_eval.storage import QualityStore
from eval_validation_probe import MUTATION_IDS, mutate_table, normalize_validation_table
from eval_trace_utils import SpanSummary, TraceSummary


def _payload(table: dict[str, Any], *, stage: str = "scenario_validated", is_valid: bool = True) -> dict[str, Any]:
    return {
        "scenarioGroup": {"scenarioGroupId": 10, "scenarioCount": 5, "stage": stage},
        "table": table,
        "isValid": is_valid,
    }


def _table(*, signposts: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index in range(5):
        row: dict[str, Any] = {
            "scenarioId": index + 1,
            "baselineYn": "Y" if index == 0 else "N",
            "cells": {"period": f"P{index}", "supply": f"S{index}"},
        }
        if signposts:
            row["signposts"] = [
                {
                    "signpostId": index + 100,
                    "label": f"signal-{index}",
                    "strength": "MEDIUM",
                    "probabilityImpactScore": 0.5,
                    "probabilityDirectionCode": "SUP",
                }
            ]
        rows.append(row)
    return {"headers": [{"key": "period"}, {"key": "supply"}], "rows": rows}


def _run() -> RunArtifacts:
    scenario_table = _table()
    return RunArtifacts(
        mi_event_id=1,
        scenario_group_id=10,
        status="success",
        step1=_payload(scenario_table),
        step2=_payload(scenario_table),
        step3=_payload(_table(signposts=True)),
        step4=None,
        event_detail={
            "scenarioTemplate": [
                {"dimKey": "period", "valueEnums": [f"P{index}" for index in range(5)]},
                {"dimKey": "supply", "valueEnums": [f"S{index}" for index in range(5)]},
            ]
        },
    )


def _result(run: RunArtifacts, check_id: str) -> CheckResult:
    return next(result for result in run_layer1_checks(run) if result.check_id == check_id)


def test_layer1_happy_path_passes_all_deterministic_checks() -> None:
    results = {result.check_id: result.status for result in run_layer1_checks(_run())}

    assert results == {f"R-{number:02d}": "PASS" for number in range(1, 10)}


def test_r01_requires_every_generation_callback_shape() -> None:
    run = replace(_run(), step3={"scenarioGroup": {}})

    result = _result(run, "R-01")

    assert result.status == "FAIL"
    assert "step3: table missing" in result.offenders


def test_r02_requires_exactly_one_baseline() -> None:
    run = _run()
    table = _table()
    for row in table["rows"]:
        row["baselineYn"] = "N"

    assert _result(replace(run, step1=_payload(table)), "R-02").status == "FAIL"


def test_r02_uses_create_table_when_validation_callback_omits_baseline() -> None:
    validation_table = _table()
    for row in validation_table["rows"]:
        row["baselineYn"] = None

    assert _result(replace(_run(), step2=_payload(validation_table)), "R-02").status == "PASS"


def test_r03_rejects_missing_header_cell_and_empty_value() -> None:
    run = _run()
    table = _table()
    table["rows"][0]["cells"] = {"period": "", "unexpected": "x"}

    result = _result(replace(run, step2=_payload(table)), "R-03")

    assert result.status == "FAIL"
    assert any("empty period" in offender for offender in result.offenders)


def test_r03_exempts_validation_generated_dimension_from_empty_cell_requirement() -> None:
    run = _run()
    validation_table = _table()
    validation_table["headers"].append({"key": "generated"})
    for row in validation_table["rows"]:
        row["cells"]["generated"] = None

    result = _result(replace(run, step2=_payload(validation_table)), "R-03")

    assert result.status == "PASS"
    assert "Validation-generated dimensions exempted" in result.detail


def test_r04_skips_without_event_detail_and_fails_invalid_enum() -> None:
    assert _result(replace(_run(), event_detail=None), "R-04").status == "SKIP"
    run = _run()
    table = _table()
    table["rows"][0]["cells"]["period"] = "out-of-enum"

    actual_event_detail = {
        "scenarioTemplate": {
            "dimensions": [
                {"key": "period", "enumValues": [f"P{index}" for index in range(5)]},
                {"key": "supply", "enumValues": [f"S{index}" for index in range(5)]},
            ],
        },
    }
    assert _result(replace(run, step2=_payload(table), event_detail=actual_event_detail), "R-04").status == "FAIL"


def test_r05_rejects_duplicate_dimension_combinations() -> None:
    run = _run()
    table = _table()
    table["rows"][1]["cells"] = dict(table["rows"][0]["cells"])

    assert _result(replace(run, step2=_payload(table)), "R-05").status == "FAIL"


def test_r06_uses_group_count_then_default_range() -> None:
    run = _run()
    wrong_count = _payload(_table())
    wrong_count["scenarioGroup"]["scenarioCount"] = 6
    assert _result(replace(run, step1=wrong_count), "R-06").status == "FAIL"

    no_configured_count = _payload(_table())
    del no_configured_count["scenarioGroup"]["scenarioCount"]
    small_table = _table()
    small_table["rows"] = small_table["rows"][:4]
    assert _result(replace(run, step1=no_configured_count, step2=_payload(small_table)), "R-06").status == "WARN"


def test_r07_requires_signpost_contract_and_r08_warns_on_common_label() -> None:
    run = _run()
    signpost_table = _table(signposts=True)
    signpost_table["rows"][0]["signposts"] = []
    assert _result(replace(run, step3=_payload(signpost_table)), "R-07").status == "FAIL"

    common_table = _table(signposts=True)
    for row in common_table["rows"]:
        row["signposts"][0]["label"] = "common"
    assert _result(replace(run, step3=_payload(common_table)), "R-08").status == "WARN"


def test_r09_enforces_is_valid_stage_pairing() -> None:
    run = _run()
    assert _result(replace(run, step2=_payload(_table(), stage="scenario_created", is_valid=True)), "R-09").status == "FAIL"
    assert _result(replace(run, step2=_payload(_table(), stage="scenario_created", is_valid=False)), "R-09").status == "PASS"


def test_artifact_loader_discovers_selected_event_and_event_detail_without_metrics(tmp_path: Path) -> None:
    batch_dir = tmp_path / "20260713_010101"
    batch_dir.mkdir()
    (batch_dir / "selected_events.json").write_text('[{"mi_event_id": 77}]', encoding="utf-8")
    (batch_dir / "77_event_detail.json").write_text('{"scenarioTemplate": []}', encoding="utf-8")
    (batch_dir / "77_step1_create_response.json").write_text('{"scenarioGroup": {}}', encoding="utf-8")

    batch = load_batch(tmp_path, None)

    assert batch.batch_id == batch_dir.name
    assert batch.runs[0].mi_event_id == 77
    assert batch.runs[0].event_detail == {"scenarioTemplate": []}


def test_artifact_loader_ignores_non_batch_output_directories_when_selecting_latest(tmp_path: Path) -> None:
    batch_dir = tmp_path / "20260713_193844"
    batch_dir.mkdir()
    (batch_dir / "selected_events.json").write_text('[{"mi_event_id": 77}]', encoding="utf-8")
    live_logs = tmp_path / "live_logs"
    live_logs.mkdir()
    (live_logs / "selected_events.json").write_text('[{"mi_event_id": 88}]', encoding="utf-8")

    batch = load_batch(tmp_path, None)

    assert batch.batch_id == "20260713_193844"
    assert [run.mi_event_id for run in batch.runs] == [77]


def test_artifact_loader_prefers_latest_batch_recorded_in_metrics(tmp_path: Path) -> None:
    batch_dir = tmp_path / "20260713_193844"
    batch_dir.mkdir()
    (batch_dir / "selected_events.json").write_text('[{"mi_event_id": 77}]', encoding="utf-8")
    live_logs = tmp_path / "live_logs"
    live_logs.mkdir()
    with sqlite3.connect(tmp_path / "sync_pipeline_metrics.sqlite3") as connection:
        connection.execute(
            "CREATE TABLE pipeline_runs (batch_id TEXT, mi_event_id INTEGER, scenario_group_id INTEGER, status TEXT)",
        )
        connection.execute("INSERT INTO pipeline_runs VALUES (?, ?, ?, ?)", (batch_dir.name, 77, 10, "success"))

    batch = load_batch(tmp_path, None)

    assert batch.batch_id == batch_dir.name
    assert batch.runs[0].status == "success"


def test_golden_parser_loads_labels_and_incidental_match(tmp_path: Path) -> None:
    case_path = tmp_path / "gc_77_fixture.md"
    case_path.write_text(
        """---
mi_event_id: 77
scenario_group_id: 12
event_title: test event
artifacts: local/output/example
---

## 정답 라벨

### GC-01

- type: A
- target: scenario
- expected_judge: J-01
- 지적: payload contradiction
- 인용: \"quoted evidence\"
""",
        encoding="utf-8",
    )

    cases = load_golden_cases(tmp_path)

    assert len(cases) == 1
    assert cases[0].mi_event_id == 77
    assert cases[0].scenario_group_id == 12
    assert cases[0].labels[0].label_id == "GC-01"
    assert cases[0].labels[0].quote == '"quoted evidence"'
    assert find_incidental_matches([77], cases) == cases
    assert find_incidental_matches([78], cases) == []


def test_mutations_are_pure_and_apply_the_expected_table_shape() -> None:
    original = _table()
    for mutation_id in MUTATION_IDS:
        mutated = mutate_table(original, mutation_id)
        assert mutated is not original
        assert original["headers"] == [{"key": "period"}, {"key": "supply"}]

    duplicate = mutate_table(original, "V-01")
    assert duplicate["rows"][0]["cells"] == duplicate["rows"][1]["cells"]
    optional = mutate_table(original, "V-05")
    assert "quality_eval_optional_dimension" in {header["key"] for header in optional["headers"]}
    required_removed = mutate_table(original, "V-06")
    assert "period" not in {header["key"] for header in required_removed["headers"]}
    baseline_converged = mutate_table(original, "V-03")
    assert {tuple(sorted(row["cells"].items())) for row in baseline_converged["rows"]} == {
        tuple(sorted(baseline_converged["rows"][0]["cells"].items())),
    }


def test_validation_probe_normalizes_callback_table_before_live_request() -> None:
    table = _table()
    table["rows"][0].update(
        {
            "narrative": "display only",
            "metrics": {"probabilityScore": "50"},
            "impact": {"ttf": "bull"},
            "baselineYn": "Y",
            "signposts": [],
        },
    )

    normalized = normalize_validation_table(table)

    assert set(normalized["rows"][0]) == {"scenarioId", "displayOrder", "title", "cells"}


def test_report_connects_slowest_api_to_trace_bottleneck_stage(tmp_path: Path) -> None:
    from quality_eval.artifacts import BatchArtifacts

    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()
    report = render_quality_report(
        BatchArtifacts("batch", batch_dir, [_run()]),
        perf={
            "available": True,
            "api_stats": [],
            "slowest": [
                {
                    "mi_event_id": 1,
                    "scenario_group_id": 10,
                    "step": "create_scenarios",
                    "elapsed_ms": 1000,
                    "retried_create": 0,
                    "pre_deleted": 0,
                },
            ],
            "failures": [],
        },
        trace={
            1: TraceSummary(
                scenario_group_id=10,
                trace_id="trace-1",
                status="PASS",
                detail="trace 수집 완료",
                spans=[SpanSummary("scenario_generation", "CHAIN", "OK", 900.0, "prompt", "output")],
            ),
        },
    )

    assert "scenario_generation (900.0ms)" in report
    assert "Prompt input excerpt" in report


def test_quality_store_creates_all_evaluation_tables_and_records_golden(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.sqlite3"
    with QualityStore(db_path) as store:
        eval_id = store.record_eval(
            batch_id="batch",
            mi_event_id=77,
            scenario_group_id=10,
            judge_model="quality-model",
            prompt_version="v1",
        )
        store.record_checks(eval_id, [CheckResult("R-01", "PASS", "ok", [])])
        store.record_probe(
            eval_id=eval_id,
            mutation_id="V-00",
            expected="pass",
            observed="pass",
            verdict="PASS",
            detail="ok",
        )
        store.record_golden(
            eval_id=eval_id,
            golden_id="GC-01",
            matched=["GC-01"],
            missed=[],
            extra=[],
            judge_ids=["J-01"],
            detail="reviewed",
        )

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM quality_evals").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM quality_check_results").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM validation_probe_results").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM golden_case_results").fetchone()[0] == 1


def test_runtime_target_uses_aliases_defaults_and_cli_precedence(tmp_path: Path) -> None:
    config_path = tmp_path / "test_info.local"
    config_path.write_text(
        """# ignored local settings
agent=mi-vm
base_url=http://configured.example:9000/
user_id=99
mlflow_uri=http://mlflow.example:5000/
mlflow_username=local-user
mlflow_password=local-password
""",
        encoding="utf-8",
    )

    configured = load_runtime_target(test_info_path=config_path)
    assert configured.base_url == "http://configured.example:9000"
    assert configured.user_id == 99
    assert configured.mlflow_uri == "http://mlflow.example:5000"
    assert configured.mlflow_username == "local-user"
    assert configured.mlflow_password == "local-password"

    alias = load_runtime_target(agent="mi-vm", test_info_path=config_path)
    assert alias.base_url == "http://40.82.137.178:8001"
    overridden = load_runtime_target(
        agent="local",
        base_url="http://explicit.example:8000/",
        user_id=123,
        mlflow_uri="http://explicit-mlflow:5001/",
        test_info_path=config_path,
    )
    assert overridden.base_url == "http://explicit.example:8000"
    assert overridden.user_id == 123
    assert overridden.mlflow_uri == "http://explicit-mlflow:5001"

    defaults = load_runtime_target(test_info_path=tmp_path / "missing.local")
    assert defaults.base_url is None
    assert defaults.user_id == DEFAULT_USER_ID == 10603

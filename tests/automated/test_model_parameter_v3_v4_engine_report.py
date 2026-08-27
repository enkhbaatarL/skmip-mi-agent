# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import json
from pathlib import Path
import struct

import pytest

from tests.manual.model_parameter_agent.report_v3_v4_engine_comparison import (
    ENGINE_SECTION_BEGIN,
    ENGINE_SECTION_END,
    _alignment_statistics,
    _campaign_footer_text,
    _failed_attempt_register,
    _failed_attempts_from_run_map,
    _failure_remediation,
    _infer_focus_month,
    _overall_quality_status,
    _price_pattern,
    _report_completion_time,
    _sha256_file,
    _supply_propagation,
    _tree_size_bytes,
    _v4_invariance_summary,
    _verify_evaluation_manifest,
    _verify_price_coverage,
    _warning_summary,
    build_engine_section,
    render_engine_dashboard,
    update_report_completion_time,
    upsert_engine_section,
)


TAGS_V3 = ("bullish", "balanced", "bearish", "strong_bearish")
WORKBOOKS = (
    "Demand Model_Input.xlsm",
    "Supply Model_Input.xlsm",
    "Trade Model_Input.xlsm",
)


def test_price_pattern_uses_epsilon_ties_and_expected_tag_order() -> None:
    rows = {
        ("bullish", "TTF"): {"user_adjusted_price": 10.0},
        ("balanced", "TTF"): {"user_adjusted_price": 10.0 + 0.5e-6},
        ("bearish", "TTF"): {"user_adjusted_price": 9.0},
    }

    assert _price_pattern(rows, region="TTF") == "bullish = balanced > bearish"


def test_upsert_engine_section_updates_formal_report_without_fixture_specific_rewrite() -> None:
    original = (
        "# report\n\n"
        "- 문서 상태: **PASS**\n"
        "- 실행 모드: proposal + confirmation E2E\n\n"
        "동일 원천 Event 집합을 가진 v3/v4 그룹에 대해 모든 proposal·confirmation·DB read-back "
        "계약이 충족되었습니다.\n\n"
        "| v4-only | - | 1077 | - | - | - | 0 | 0 |\n\n"
        "## 7. 결론 및 해석 한계\n\n"
        "- 최종 결론: v3와 v4가 동일 Event 집합 및 공용 DB 조건에서 "
        "모두 proposal·confirmation E2E 계약을 충족했습니다."
    )
    section = f"{ENGINE_SECTION_BEGIN}\n## engine\n- 통합 판정: **REVIEW**\n{ENGINE_SECTION_END}"

    updated = upsert_engine_section(original, section)

    assert "proposal + confirmation E2E + LNG Demand→Supply→Trade→Output 엔진" in updated
    assert "동일 LNG 엔진의 Demand→Supply→Trade→Output 전 단계 계약" in updated
    assert "| v4-only | - | 1077 | - | - | - | 0 | 0 |" in updated
    assert "- 문서 상태: **REVIEW**" in updated
    assert "## 10. 결론 및 해석 한계" in updated
    assert "가격 산출·read-back 계약을 모두 충족" in updated
    assert "가격 태그 정합성은 7절의 독립 판정" in updated
    assert "기술 PASS를 가격 태그 정렬 PASS로 해석하지 않으며" in updated


def test_upsert_engine_section_replaces_existing_section_idempotently() -> None:
    old_section = f"{ENGINE_SECTION_BEGIN}\nold\n{ENGINE_SECTION_END}"
    report = (
        "# report\n\n"
        "- 실행 모드: proposal + confirmation E2E + "
        "LNG Demand→Supply→Trade→Output 엔진\n\n"
        f"{old_section}\n\n## 10. 결론 및 해석 한계\n"
    )
    new_section = f"{ENGINE_SECTION_BEGIN}\nnew\n{ENGINE_SECTION_END}"

    updated = upsert_engine_section(report, new_section)
    updated_twice = upsert_engine_section(updated, new_section)

    assert updated.count(ENGINE_SECTION_BEGIN) == 1
    assert "\nnew\n" in updated
    assert "\nold\n" not in updated
    assert updated_twice == updated


def test_report_completion_time_uses_latest_engine_run_in_utc() -> None:
    completion = _report_completion_time(
        (
            {"generated_at": "2026-08-13T15:05:10+09:00"},
            {"generated_at": "2026-08-13T15:12:30+09:00"},
        ),
    )

    updated = update_report_completion_time(
        "# report\n- 검증 종료: old\n",
        completion,
    )

    assert completion == "2026-08-13T06:12:30+00:00"
    assert updated == "# report\n- 검증 종료: 2026-08-13T06:12:30+00:00\n"


def test_warning_summary_prioritizes_model_drift_over_routine_warnings() -> None:
    evaluation = {
        "validation": {
            "warnings": [
                {
                    "warning_count": 2,
                    "sample": [
                        {"text": "WARNING TEMPLATE AUTO-SYNC ADDED NEW KEYS"},
                        {"text": "WARNING ITER_SUR STOP unstable nonzero drift"},
                    ],
                },
            ],
        },
    }

    total, cases, sample = _warning_summary(evaluation)

    assert total == 2
    assert cases == 1
    assert sample.startswith("WARNING ITER_SUR STOP unstable nonzero drift")


def test_v4_invariance_summary_allows_only_expected_proposal_rows() -> None:
    stable = {
        key: {"sha256": f"{key}-hash"}
        for key in (
            "master",
            "impact_levers",
            "scenario_groups",
            "scenarios",
            "group_event_relations",
            "runtime",
        )
    }
    mapping = {
        "count": 129,
        "method_counts": {"direct": 35, "routing": 6, "indirect": 55, "na": 33},
    }
    baseline = {
        "v4_invariants": stable | {"stored_proposals": {"ids": [1, 2]}},
        "shared_mapping_observation": mapping,
    }
    after = {
        "v4_invariants": stable | {"stored_proposals": {"ids": [1, 2, 3, 4]}},
        "shared_mapping_observation": mapping,
    }

    summary = _v4_invariance_summary(baseline, after, expected_new_proposal_ids=[3, 4])

    assert "v4 범위 불변성: **PASS**" in summary
    assert "`2→4`" in summary
    assert "`[3, 4]`" in summary


def test_tree_size_bytes_counts_nested_files(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "one.bin").write_bytes(b"123")
    (nested / "two.bin").write_bytes(b"4567")

    assert _tree_size_bytes(tmp_path) == 7


def test_failed_attempt_run_map_is_retained_outside_success_denominator(tmp_path: Path) -> None:
    model_root = tmp_path / "model"
    (model_root / "engine").mkdir(parents=True)
    (model_root / "engine/run_all.py").write_text("# runner\n", encoding="utf-8")
    run_id = "20260813_150000"
    log_path = tmp_path / "orchestration/failed.log"
    log_path.parent.mkdir()
    log_path.write_text(
        "ModuleNotFoundError: No module named 'pandas'\n[run_all] STOP: supply failed (rc=1)\n",
        encoding="utf-8",
    )
    removed_paths = [
        str(model_root / "outputs" / run_id),
        str(model_root / "log" / run_id),
    ]
    run_map = tmp_path / "failed_run_map.json"
    run_map.write_text(
        json.dumps(
            {
                "runs": {
                    "scenario_1071_bullish": {
                        "scenario_id": 1071,
                        "tag": "bullish",
                        "run_id": run_id,
                        "exit_code": 1,
                        "orchestrator_log": str(log_path),
                    },
                },
                "removed_incomplete": {"scenario_1071_bullish": removed_paths},
            },
        ),
        encoding="utf-8",
    )
    evaluation = {
        "model_root": str(model_root),
        "execution": {
            "total_count": 1,
            "success_count": 1,
            "failed_count": 0,
            "run_mapping": [{"scenario_id": 1071, "tag": "bullish", "run_id": "success"}],
        },
    }

    attempts = _failed_attempts_from_run_map(run_map, evaluation=evaluation)

    assert evaluation["execution"]["success_count"] == 1
    assert attempts[0]["category"] == "ENVIRONMENT"
    assert attempts[0]["stage"] == "supply"
    assert attempts[0]["engine_returncodes"] == [1]
    assert attempts[0]["cleanup_status"] == "complete"

    log_path.write_text(
        "zipfile.BadZipFile: File is not a zip file\n[run_all] STOP: demand failed (rc=1)\n",
        encoding="utf-8",
    )
    xlsm_attempts = _failed_attempts_from_run_map(run_map, evaluation=evaluation)
    assert xlsm_attempts[0]["category"] == "INPUT"
    assert xlsm_attempts[0]["stage"] == "demand"
    assert "ZIP CRC" in _failure_remediation(xlsm_attempts[0])

    foreign_root = tmp_path / "foreign"
    payload = json.loads(run_map.read_text(encoding="utf-8"))
    payload["removed_incomplete"]["scenario_1071_bullish"] = [
        str(foreign_root / "outputs" / run_id),
        str(foreign_root / "log" / run_id),
    ]
    run_map.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="evaluation model root"):
        _failed_attempts_from_run_map(run_map, evaluation=evaluation)


def test_failed_attempt_register_defaults_to_zero_entries() -> None:
    evaluation = {"execution": {"failed_attempts": []}}

    assert _failed_attempt_register(evaluation, []) == []


def test_input_export_rc1_descriptor_is_retained_with_specific_remediation(
    tmp_path: Path,
) -> None:
    descriptor = tmp_path / "v3-input-export-failure.json"
    descriptor.write_text(
        json.dumps(
            {
                "attempt_ids": ["v3-export-attempt-1"],
                "returncodes": [1],
                "category": "INPUT",
                "stage": "input-export",
                "reason": "LiqProdAdjustment LUT-only exact cell was not resolved",
                "cleanup_status": "not_required",
            },
        ),
        encoding="utf-8",
    )

    attempts = _failed_attempt_register(
        {"execution": {"failed_attempts": []}},
        [],
        [descriptor],
    )

    assert attempts[0]["run_ids"] == ["v3-export-attempt-1"]
    assert attempts[0]["engine_returncodes"] == [1]
    assert attempts[0]["source_evidence_sha256"] == _sha256_file(descriptor)
    assert "Basecase/LUT exact-cell resolver" in _failure_remediation(attempts[0])


def test_campaign_dashboard_footer_is_symmetric_for_v3_and_v4() -> None:
    data = {
        "v3_runs": {"success_count": 4},
        "v3_campaign_attempt_count": 8,
        "v3_failed_attempt_count": 4,
        "v3_failed_categories": "ENVIRONMENT",
        "v4_runs": {"success_count": 5},
        "v4_campaign_attempt_count": 5,
        "v4_failed_attempt_count": 0,
        "v4_failed_categories": "NONE",
    }

    assert _campaign_footer_text("v3", data) == (
        "V3 CAMPAIGN ATTEMPTS 8 = PASS 4 + FAILED 4 (ENVIRONMENT)    ATTEMPTS RETAINED"
    )
    assert _campaign_footer_text("v4", data) == (
        "V4 CAMPAIGN ATTEMPTS 5 = PASS 5 + FAILED 0 (NONE)    ATTEMPTS RETAINED"
    )


def _binding_fixture(
    tmp_path: Path,
    *,
    tags: tuple[str, ...] = TAGS_V3,
) -> tuple[dict[str, object], dict[str, object]]:
    model_root = tmp_path / "model"
    group_dir = tmp_path / "group_182"
    group_dir.mkdir()
    run_map = group_dir / "run_map.json"
    summary = group_dir / "parameter_proposal_summary.md"
    run_map.write_text("{}\n", encoding="utf-8")
    summary.write_text("Year=2026\n", encoding="utf-8")
    scenarios = []
    cases = []
    runs = []
    for offset, tag in enumerate(tags, start=1):
        scenario_id = 1000 + offset
        run_id = f"run-{offset}"
        case_dir = group_dir / f"scenario_{scenario_id}_{tag}"
        case_dir.mkdir()
        manifest_workbooks = []
        source_hashes = {}
        for filename in WORKBOOKS:
            path = case_dir / filename
            path.write_bytes(f"{scenario_id}:{filename}".encode())
            digest = _sha256_file(path)
            manifest_workbooks.append({"filename": filename, "sha256": digest})
            source_hashes[filename] = {"path": path.as_posix(), "sha256": digest}
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "tag": tag,
                "proposal_id": 2000 + offset,
                "patches": [{"parameter_name": "LiqUtilAdjustment"}],
                "workbooks": manifest_workbooks,
            },
        )
        cases.append(
            {
                "scenario_id": scenario_id,
                "tag": tag,
                "run_id": run_id,
                "source_sha256": source_hashes,
            },
        )
        runs.append({"scenario_id": scenario_id, "tag": tag, "run_id": run_id})
    manifest: dict[str, object] = {
        "schema_version": "model-parameter-confirmed-engine-input-v1",
        "scenario_group": {
            "scenario_group_id": 182,
            "api_version": "v3",
            "generation_strategy": "multi_event_composite_dimensions",
        },
        "scenarios": scenarios,
    }
    (group_dir / "export_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    evaluation: dict[str, object] = {
        "group": {"id": 182, "name": "group_182"},
        "model_root": model_root.as_posix(),
        "group_dir": group_dir.as_posix(),
        "run_map": {"path": run_map.as_posix(), "sha256": _sha256_file(run_map)},
        "proposal_summary": {"path": summary.as_posix(), "sha256": _sha256_file(summary)},
        "cases": cases,
        "execution": {"run_mapping": runs},
    }
    return evaluation, manifest


def test_evaluation_is_bound_to_exact_confirmed_workbook_hashes(tmp_path: Path) -> None:
    evaluation, manifest = _binding_fixture(tmp_path)

    _verify_evaluation_manifest(evaluation, manifest, version="v3")

    cases = evaluation["cases"]
    assert isinstance(cases, list)
    first_case = cases[0]
    assert isinstance(first_case, dict)
    source_hashes = first_case["source_sha256"]
    assert isinstance(source_hashes, dict)
    source_hashes[WORKBOOKS[0]]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="workbook digest mismatch"):
        _verify_evaluation_manifest(evaluation, manifest, version="v3")


@pytest.mark.parametrize(
    "tags",
    [
        ("bullish", "balanced", "bearish"),
        TAGS_V3,
        ("strong_bullish", "bullish", "balanced", "bearish", "strong_bearish"),
    ],
)
def test_evaluation_accepts_dynamic_three_to_five_tag_manifests(
    tmp_path: Path,
    tags: tuple[str, ...],
) -> None:
    evaluation, manifest = _binding_fixture(tmp_path, tags=tags)

    assert _verify_evaluation_manifest(evaluation, manifest, version="v3") == frozenset(tags)


def test_evaluation_rejects_less_than_three_pressure_tags(tmp_path: Path) -> None:
    evaluation, manifest = _binding_fixture(
        tmp_path,
        tags=("bullish", "bearish"),
    )

    with pytest.raises(RuntimeError, match=r"expected=3\.\.5 unique allowed tags"):
        _verify_evaluation_manifest(evaluation, manifest, version="v3")


def test_evaluation_accepts_explicit_confirmed_source_alias_view(tmp_path: Path) -> None:
    evaluation, manifest = _binding_fixture(tmp_path)
    group_dir = Path(str(evaluation["group_dir"]))
    source_root = tmp_path / "confirmed-export"
    source_root.mkdir()
    (source_root / "export_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    cases = evaluation["cases"]
    assert isinstance(cases, list)
    for case in cases:
        assert isinstance(case, dict)
        scenario_name = f"scenario_{case['scenario_id']}_{case['tag']}"
        source_dir = source_root / scenario_name
        source_dir.mkdir()
        source_hashes = case["source_sha256"]
        assert isinstance(source_hashes, dict)
        for filename in WORKBOOKS:
            alias = group_dir / scenario_name / filename
            source = source_dir / filename
            source.write_bytes(alias.read_bytes())
            alias.unlink()
            alias.symlink_to(source)
            source_hashes[filename]["path"] = source.as_posix()

    _verify_evaluation_manifest(evaluation, manifest, version="v3")


def test_evaluation_rejects_arbitrary_external_source_without_alias_contract(
    tmp_path: Path,
) -> None:
    evaluation, manifest = _binding_fixture(tmp_path)
    cases = evaluation["cases"]
    assert isinstance(cases, list)
    first_case = cases[0]
    assert isinstance(first_case, dict)
    source_hashes = first_case["source_sha256"]
    assert isinstance(source_hashes, dict)
    original = Path(source_hashes[WORKBOOKS[0]]["path"])
    arbitrary = tmp_path / "arbitrary.xlsm"
    arbitrary.write_bytes(original.read_bytes())
    source_hashes[WORKBOOKS[0]]["path"] = arbitrary.as_posix()

    with pytest.raises(RuntimeError, match="path does not match confirmed identity"):
        _verify_evaluation_manifest(evaluation, manifest, version="v3")


def test_price_coverage_uses_dynamic_manifest_tag_set() -> None:
    expected_tags = ("bullish", "balanced", "bearish")
    index = {
        (tag, region): {"user_adjusted_price": 1.0}
        for tag in expected_tags
        for region in ("East Asia Spot", "TTF", "HH")
    }

    _verify_price_coverage(
        index,
        version="v3",
        period="annual",
        expected_tags=expected_tags,
    )

    incomplete = dict(index)
    incomplete.pop(("bearish", "HH"))
    with pytest.raises(RuntimeError, match="price tag set mismatch"):
        _verify_price_coverage(
            {key: value for key, value in incomplete.items() if key[0] != "bearish"},
            version="v3",
            period="annual",
            expected_tags=expected_tags,
        )

    with pytest.raises(RuntimeError, match="price region coverage differs by tag"):
        _verify_price_coverage(
            incomplete,
            version="v3",
            period="annual",
            expected_tags=expected_tags,
        )


def test_alignment_statistics_reports_strict_tie_and_decisive_rates() -> None:
    evaluation = {
        "price": {
            "tag_alignment": {
                "verdict": "partially_aligned",
                "reason_code": "direction_present_but_many_ties",
                "combined_comparison_counts": {"met": 52, "reversed": 0, "tie": 104},
                "responsive_region_count": 2,
            },
        },
    }

    result = _alignment_statistics(evaluation)

    assert result["met"] == 52
    assert result["reversed"] == 0
    assert result["tie"] == 104
    assert result["strict_satisfaction"] == pytest.approx(1 / 3)
    assert result["tie_rate"] == pytest.approx(2 / 3)
    assert result["decisive_accuracy"] == pytest.approx(1.0)


def test_overall_quality_is_review_when_technical_axes_pass_but_alignment_is_partial() -> None:
    technical_pass = {
        "export_integrity": {"judgement": "PASS"},
        "engine_execution": {"judgement": "PASS"},
        "tag_alignment": {"judgement": "REVIEW"},
        "mechanistic_consistency": {"judgement": "PASS"},
        "model_expressiveness": {"judgement": "PASS"},
    }

    assert _overall_quality_status(technical_pass, technical_pass) == "REVIEW"


def test_focus_month_is_inferred_from_generic_confirmed_patches() -> None:
    manifests = (
        {
            "scenarios": [
                {
                    "scenario_id": 1,
                    "patches": [
                        {"parameter_name": "GDP", "coordinates": {"Year": 2027, "Month": 7}},
                    ],
                },
                {
                    "scenario_id": 2,
                    "patches": [
                        {"parameter_name": "PMI", "coordinates": {"Year": 2027, "Month": 7}},
                    ],
                },
            ],
        },
        {
            "scenarios": [
                {
                    "scenario_id": 3,
                    "patches": [
                        {"parameter_name": "PowerMix", "coordinates": {"Year": 2027, "Month": 8}},
                    ],
                },
            ],
        },
    )

    assert _infer_focus_month(manifests, ({}, {}), None) == (
        7,
        "confirmed patch mode (2/3 cells)",
    )


def test_supply_propagation_is_optional_for_non_liq_util_parameters() -> None:
    evaluation = {
        "model_root": "/path/not/read/without-liq-util",
        "cases": [],
        "execution": {"run_mapping": []},
    }
    manifest = {
        "scenarios": [
            {
                "scenario_id": 1001,
                "tag": "bullish",
                "proposal_id": 2001,
                "patches": [
                    {
                        "parameter_name": "GDP",
                        "basecase_value": 1.0,
                        "proposed_value": 1.2,
                        "coordinates": {"Country": "Japan", "Year": 2027},
                    },
                ],
            },
        ],
    }

    assert _supply_propagation(evaluation, manifest) == []


def test_supply_propagation_rejects_output_changed_after_evaluation(tmp_path: Path) -> None:
    model_root = tmp_path / "model"
    output_path = model_root / "outputs" / "run-1" / "supply" / ("result_trademodelinput_liq_production_monthly.csv")
    output_path.parent.mkdir(parents=True)
    header = (
        "Year,Month,Country,LNG Plant,LNG Plant train,"
        "Implied new plant utilisation rate (%),"
        "Export LNG plant train production (Mt LNG per month),"
        "Export LNG plant train production (Bcm per month) - Post Adj 6 and 7\n"
    )
    output_path.write_text(
        header + "2026,8,Angola,Angola LNG,Angola LNG T1,0.84,0.3,0.4\n",
        encoding="utf-8",
    )
    digest = _sha256_file(output_path)
    evaluation = {
        "model_root": model_root.as_posix(),
        "cases": [
            {
                "scenario_id": 1001,
                "tag": "bullish",
                "run_id": "run-1",
                "output_sha256": {
                    output_path.as_posix(): {
                        "path": output_path.as_posix(),
                        "sha256": digest,
                    },
                },
            },
        ],
        "execution": {
            "run_mapping": [
                {"scenario_id": 1001, "tag": "bullish", "run_id": "run-1"},
            ],
        },
    }
    manifest = {
        "scenarios": [
            {
                "scenario_id": 1001,
                "tag": "bullish",
                "proposal_id": 2001,
                "patches": [
                    {
                        "parameter_name": "LiqUtilAdjustment",
                        "basecase_value": 0.90738,
                        "proposed_value": 0.84,
                        "coordinates": {
                            "Year": 2026,
                            "Month": 8,
                            "Country": "Angola",
                            "LNG Plant": "Angola LNG",
                            "LNG Plant Train": "Angola LNG T1",
                        },
                    },
                ],
            },
        ],
    }
    output_path.write_text(
        header + "2026,8,Angola,Angola LNG,Angola LNG T1,0.80,0.2,0.3\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="file/hash binding mismatch"):
        _supply_propagation(evaluation, manifest)


def _price_rows(
    tags: tuple[str, ...],
    *,
    year: int,
    month: int | None,
    scenario_start: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    tag_prices = {tag: 10.0 + (len(tags) - index) for index, tag in enumerate(tags)}
    for tag_offset, tag in enumerate(tags):
        for region_offset, region in enumerate(("East Asia Spot", "TTF", "HH")):
            row: dict[str, object] = {
                "scenario_id": scenario_start + tag_offset,
                "tag": tag,
                "year": year,
                "price_region": region,
                "base_case_price": 10.0 + region_offset,
                "user_adjusted_price": tag_prices[tag] + region_offset,
            }
            if month is not None:
                row["month"] = month
            rows.append(row)
    return rows


def _report_fixture(
    version: str,
    tags: tuple[str, ...],
    *,
    group_id: int,
    scenario_start: int,
    met: int,
    tie: int,
) -> tuple[dict[str, object], dict[str, object]]:
    scenarios = []
    runs = []
    for offset, tag in enumerate(tags):
        scenario_id = scenario_start + offset
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "tag": tag,
                "proposal_id": scenario_id + 10_000,
                "patches": [
                    {
                        "parameter_name": "GDP",
                        "basecase_value": 1.0,
                        "proposed_value": 1.1 + offset / 10,
                        "coordinates": {
                            "Country": "Japan",
                            "Year": 2027,
                            "Month": 7,
                        },
                    },
                ],
            },
        )
        runs.append(
            {
                "scenario_id": scenario_id,
                "tag": tag,
                "run_id": f"{version}-run-{offset + 1}",
            },
        )
    manifest: dict[str, object] = {
        "schema_version": "model-parameter-confirmed-engine-input-v1",
        "scenario_group": {
            "scenario_group_id": group_id,
            "api_version": version,
            "generation_strategy": (
                "multi_event_composite_dimensions" if version == "v3" else "multi_event_model_lever_dimensions"
            ),
        },
        "confirmed_snapshot_sha256": f"{version}-snapshot",
        "llm_call_count": 0,
        "scenarios": scenarios,
    }
    verdict = "aligned" if tie == 0 else "partially_aligned"
    evaluation: dict[str, object] = {
        "focus_year": 2027,
        "evaluation_sha256": f"{version}-evaluation",
        "validation": {
            "status": "PASS",
            "warnings": [
                {
                    "warning_count": 2,
                    "sample": [{"text": f"{version} workbook formula cache warning"}],
                },
            ],
        },
        "execution": {
            "success_count": len(tags),
            "total_count": len(tags),
            "failed_count": 0,
            "run_mapping": runs,
        },
        "price": {
            "annual_rows": _price_rows(
                tags,
                year=2027,
                month=None,
                scenario_start=scenario_start,
            ),
            "monthly_rows": _price_rows(
                tags,
                year=2027,
                month=7,
                scenario_start=scenario_start,
            ),
            "tag_alignment": {
                "verdict": verdict,
                "reason_code": "ties_reduce_strict_alignment" if tie else "expected_order_met",
                "combined_comparison_counts": {"met": met, "reversed": 0, "tie": tie},
                "responsive_region_count": 3,
            },
        },
        "input_differences": [{"workbook": "Demand Model_Input.xlsm"}],
        "upstream_differences": [{"changed_cell_count": len(tags)}],
    }
    return evaluation, manifest


def test_build_report_is_dynamic_generic_and_reviews_partial_alignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    v3_tags = ("bullish", "balanced", "bearish")
    v4_tags = ("strong_bullish", "bullish", "balanced", "bearish")
    v3_evaluation, v3_manifest = _report_fixture(
        "v3",
        v3_tags,
        group_id=301,
        scenario_start=1101,
        met=6,
        tie=6,
    )
    v4_evaluation, v4_manifest = _report_fixture(
        "v4",
        v4_tags,
        group_id=401,
        scenario_start=1201,
        met=18,
        tie=0,
    )
    monkeypatch.setattr(
        "tests.manual.model_parameter_agent.report_v3_v4_engine_comparison._verify_evaluation",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "tests.manual.model_parameter_agent.report_v3_v4_engine_comparison._verify_evaluation_manifest",
        lambda _evaluation, manifest, **_kwargs: frozenset(item["tag"] for item in manifest["scenarios"]),
    )

    section, figure_data = build_engine_section(
        v3_evaluation=v3_evaluation,
        v4_evaluation=v4_evaluation,
        v3_manifest=v3_manifest,
        v4_manifest=v4_manifest,
        v3_failed_attempts=(
            {
                "category": "ENVIRONMENT",
                "stage": "supply",
                "reason": "No module named pandas",
                "run_ids": ["v3-failed-1"],
                "engine_returncodes": [1],
                "cleanup_status": "complete",
                "removed_paths": ["outputs/v3-failed-1", "log/v3-failed-1"],
            },
        ),
        v4_failed_attempts=(),
        focus_month=None,
    )

    assert "- 통합 판정: **REVIEW**" in section
    assert "| v3 | `partially_aligned` | 6 | 0 | 6 | 50.0% | 50.0% | 100.0% | 3 |" in section
    assert "| v4 | `aligned` | 18 | 0 | 0 | 100.0% | 0.0% | 100.0% | 3 |" in section
    assert "방향 역전은 없고 반응한 비교 6건은 기대 순서를 따랐지만" in section
    assert "confirmed patch mode (7/7 cells)" in section
    assert "| v3 | `bullish` | 1101 / 11101 | GDP |" in section
    assert "LiqUtilAdjustment 전달 상세: `N/A`" in section
    assert "`.venv/bin/python` 경로를 resolve하지 말고 전달" in section
    assert "v3 workbook formula cache warning" in section
    assert "128행" not in section
    assert "후보 5개" not in section
    assert figure_data["overall_status"] == "REVIEW"
    assert figure_data["focus_month"] == 7
    assert figure_data["v3_scenario_count"] == 3
    assert figure_data["v4_scenario_count"] == 4


def test_report_figure_is_portrait_png(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    v3_evaluation, v3_manifest = _report_fixture(
        "v3",
        ("bullish", "balanced", "bearish"),
        group_id=302,
        scenario_start=1301,
        met=12,
        tie=0,
    )
    v4_evaluation, v4_manifest = _report_fixture(
        "v4",
        ("strong_bullish", "bullish", "balanced", "bearish", "strong_bearish"),
        group_id=402,
        scenario_start=1401,
        met=24,
        tie=0,
    )
    monkeypatch.setattr(
        "tests.manual.model_parameter_agent.report_v3_v4_engine_comparison._verify_evaluation",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "tests.manual.model_parameter_agent.report_v3_v4_engine_comparison._verify_evaluation_manifest",
        lambda _evaluation, manifest, **_kwargs: frozenset(item["tag"] for item in manifest["scenarios"]),
    )
    _, figure_data = build_engine_section(
        v3_evaluation=v3_evaluation,
        v4_evaluation=v4_evaluation,
        v3_manifest=v3_manifest,
        v4_manifest=v4_manifest,
        v3_failed_attempts=(),
        v4_failed_attempts=(),
        focus_month=None,
    )
    output = tmp_path / "alignment-report.png"

    render_engine_dashboard(output, figure_data)

    payload = output.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", payload[16:24]) == (1200, 1600)

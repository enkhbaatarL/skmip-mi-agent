# Copyright (c) 2026 SK Innovation E&S.
from __future__ import annotations

# ruff: noqa: ANN401, S101, SLF001
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "tests/lng_model/skills/evaluate-lng-price-tags/scripts/run_group.py"
)

if not SCRIPT_PATH.is_file():
    pytest.skip(
        "optional LNG price-tag harness is not available in this checkout",
        allow_module_level=True,
    )


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lng_price_tag_run_group", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUN_GROUP = _load_module()


def _write_workbook(path: Path, sheet_names: tuple[str, ...], marker: str) -> None:
    sheets = "".join(
        f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets>"
        "</workbook>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr(f"custom/{marker}.txt", marker)


def _make_case(tmp_path: Path, *, scenario_name: str = "scenario_101_balanced") -> Any:
    case_dir = tmp_path / "group_1" / scenario_name
    for index, workbook_name in enumerate(RUN_GROUP.REQUIRED_WORKBOOKS):
        _write_workbook(
            case_dir / workbook_name,
            RUN_GROUP.REQUIRED_ROLE_SHEETS[workbook_name],
            f"{index}-{workbook_name}",
        )
    return RUN_GROUP.ScenarioCase(
        directory_name=scenario_name,
        scenario_id=101,
        tag="balanced",
        case_dir=case_dir,
    )


def _make_model_root(tmp_path: Path) -> Path:
    model_root = tmp_path / "model"
    (model_root / "engine").mkdir(parents=True)
    (model_root / "engine/run_all.py").write_text("# runner\n", encoding="utf-8")
    for relative_path in ("data/LUT", "data/templates"):
        directory = model_root / relative_path
        directory.mkdir(parents=True)
        (directory / "fixture.txt").write_text(relative_path, encoding="utf-8")
    return model_root


def _args(
    *,
    model_root: Path,
    group_dir: Path,
    run_map: Path,
    uv_cache_dir: Path,
    delete_incomplete: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        model_root=model_root,
        group_dir=group_dir,
        run_map=run_map,
        jobs=2,
        run_id_prefix="20260814_010000",
        uv_cache_dir=uv_cache_dir,
        failed_attempt_run_map=[],
        delete_incomplete=delete_incomplete,
        dry_run=False,
    )


def test_validate_case_workbooks_accepts_exact_role_specific_ooxml(tmp_path: Path) -> None:
    case = _make_case(tmp_path)

    checks = RUN_GROUP._validate_case_workbooks(case)

    assert tuple(checks) == RUN_GROUP.REQUIRED_WORKBOOKS
    assert len({check.sha256 for check in checks.values()}) == 3
    assert all(check.size_bytes > 0 for check in checks.values())


def test_validate_case_workbooks_rejects_extra_xlsm_before_model_run(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_workbook(case.case_dir / "unexpected.xlsm", ("Unexpected",), "extra")

    with pytest.raises(RUN_GROUP.ClassifiedRunError) as captured:
        RUN_GROUP._validate_case_workbooks(case)

    assert captured.value.category is RUN_GROUP.FailureCategory.INPUT
    assert captured.value.details["discovered"] == sorted((*RUN_GROUP.REQUIRED_WORKBOOKS, "unexpected.xlsm"))


def test_validate_case_workbooks_rejects_corrupt_ooxml(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    (case.case_dir / "Supply Model_Input.xlsm").write_bytes(b"not-a-zip")

    with pytest.raises(RUN_GROUP.ClassifiedRunError) as captured:
        RUN_GROUP._validate_case_workbooks(case)

    assert captured.value.category is RUN_GROUP.FailureCategory.INPUT
    assert "valid OOXML" in str(captured.value)


def test_validate_case_workbooks_rejects_workbook_renamed_to_wrong_role(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_workbook(
        case.case_dir / "Demand Model_Input.xlsm",
        RUN_GROUP.REQUIRED_ROLE_SHEETS["Trade Model_Input.xlsm"],
        "wrong-role",
    )

    with pytest.raises(RUN_GROUP.ClassifiedRunError) as captured:
        RUN_GROUP._validate_case_workbooks(case)

    assert captured.value.category is RUN_GROUP.FailureCategory.INPUT
    assert captured.value.details["missing_role_sheets"] == ["DemandOutputOverwrite", "Scenario Tracker"]


def test_environment_preflight_invokes_venv_symlink_without_resolving_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_root = tmp_path / "model"
    python_bin = model_root / ".venv/bin/python"
    python_bin.parent.mkdir(parents=True)
    python_bin.symlink_to(Path(sys.executable))
    observed_command: list[str] = []

    def fake_run(command: list[str], **_: Any) -> SimpleNamespace:
        observed_command.extend(command)
        payload = {
            "sys_executable": str(python_bin),
            "sys_prefix": str(model_root / ".venv"),
            "modules": dict.fromkeys(RUN_GROUP.REQUIRED_PYTHON_MODULES, "test"),
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(RUN_GROUP.subprocess, "run", fake_run)

    result = RUN_GROUP._validate_python_environment(model_root)

    assert observed_command[0] == str(python_bin)
    assert observed_command[0] != str(python_bin.resolve())
    assert result.python_bin == str(python_bin)


def test_environment_preflight_classifies_missing_imports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model_root = tmp_path / "model"
    python_bin = model_root / ".venv/bin/python"
    python_bin.parent.mkdir(parents=True)
    python_bin.symlink_to(Path(sys.executable))
    monkeypatch.setattr(
        RUN_GROUP.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'pandas'",
        ),
    )

    with pytest.raises(RUN_GROUP.ClassifiedRunError) as captured:
        RUN_GROUP._validate_python_environment(model_root)

    assert captured.value.category is RUN_GROUP.FailureCategory.ENVIRONMENT
    assert captured.value.details["returncode"] == 1


def test_single_group_lock_rejects_concurrent_group_and_is_removed(tmp_path: Path) -> None:
    model_root = tmp_path / "model"
    model_root.mkdir()
    group_dir = tmp_path / "group_1"
    run_map = tmp_path / "run_map.json"

    with RUN_GROUP._single_group_lock(model_root, group_dir, run_map):
        assert (model_root / RUN_GROUP.RUN_LOCK_NAME).is_file()
        with (
            pytest.raises(RUN_GROUP.ClassifiedRunError) as captured,
            RUN_GROUP._single_group_lock(model_root, group_dir, run_map),
        ):
            pass
        assert captured.value.category is RUN_GROUP.FailureCategory.PREFLIGHT

    assert not (model_root / RUN_GROUP.RUN_LOCK_NAME).exists()


def test_prior_failed_attempt_is_retained_with_environment_classification(tmp_path: Path) -> None:
    model_root = _make_model_root(tmp_path)
    case = _make_case(tmp_path)
    failed_run_id = "20260814_005900"
    orchestrator_log = tmp_path / "orchestration/failed.log"
    orchestrator_log.parent.mkdir()
    orchestrator_log.write_text(
        "ModuleNotFoundError: No module named 'pandas'\n"
        "[run_all] STOP: supply failed (rc=1)\n",
        encoding="utf-8",
    )
    removed_paths = [
        str(model_root / "outputs" / failed_run_id),
        str(model_root / "log" / failed_run_id),
    ]
    failed_map = tmp_path / "failed_run_map.json"
    failed_map.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "created_at": "2026-08-14T00:59:00+09:00",
                "runs": {
                    case.directory_name: {
                        "scenario_id": case.scenario_id,
                        "tag": case.tag,
                        "run_id": failed_run_id,
                        "exit_code": 1,
                        "orchestrator_log": str(orchestrator_log),
                    },
                },
                "removed_incomplete": {case.directory_name: removed_paths},
            },
        ),
        encoding="utf-8",
    )

    attempts = RUN_GROUP._prior_failed_attempts(
        [failed_map],
        cases=[case],
        current_run_ids=["20260814_010000"],
        model_root=model_root,
    )

    assert len(attempts) == 1
    assert attempts[0]["category"] == "ENVIRONMENT"
    assert attempts[0]["stage"] == "supply"
    assert attempts[0]["run_ids"] == [failed_run_id]
    assert attempts[0]["engine_returncodes"] == [1]
    assert attempts[0]["cleanup_status"] == "complete"
    assert attempts[0]["removed_paths"] == sorted(removed_paths)


def test_prior_failed_attempt_rejects_unremoved_exact_path(tmp_path: Path) -> None:
    model_root = _make_model_root(tmp_path)
    case = _make_case(tmp_path)
    run_id = "20260814_005900"
    remaining_path = model_root / "outputs" / run_id
    remaining_path.mkdir(parents=True)
    failed_map = tmp_path / "failed_run_map.json"
    failed_map.write_text(
        json.dumps(
            {
                "runs": {
                    case.directory_name: {
                        "scenario_id": case.scenario_id,
                        "tag": case.tag,
                        "run_id": run_id,
                        "exit_code": 1,
                    },
                },
                "removed_incomplete": {case.directory_name: [str(remaining_path)]},
            },
        ),
        encoding="utf-8",
    )

    with pytest.raises(RUN_GROUP.ClassifiedRunError) as captured:
        RUN_GROUP._prior_failed_attempts(
            [failed_map],
            cases=[case],
            current_run_ids=["20260814_010000"],
            model_root=model_root,
        )

    assert captured.value.category is RUN_GROUP.FailureCategory.PREFLIGHT
    assert "still exists" in str(captured.value)


def test_run_records_model_failure_and_exact_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_root = _make_model_root(tmp_path)
    group_dir = tmp_path / "group_1"
    case_dir = group_dir / "scenario_101_balanced"
    case_dir.mkdir(parents=True)
    run_map = tmp_path / "evidence/run_map.json"
    python_bin = model_root / ".venv/bin/python"
    environment_check = RUN_GROUP.EnvironmentCheck(
        python_bin=str(python_bin),
        sys_executable=str(python_bin),
        sys_prefix=str(model_root / ".venv"),
        modules=dict.fromkeys(RUN_GROUP.REQUIRED_PYTHON_MODULES, "test"),
    )
    monkeypatch.setattr(RUN_GROUP, "_validate_python_environment", lambda _: environment_check)
    monkeypatch.setattr(RUN_GROUP, "_validate_case_workbooks", lambda _: {})

    def fake_run_case(**kwargs: Any) -> Any:
        run_id = str(kwargs["run_id"])
        for root_name in ("outputs", "log"):
            target = model_root / root_name / run_id
            target.mkdir(parents=True)
            (target / "partial.txt").write_text("partial", encoding="utf-8")
        return RUN_GROUP.RunResult(
            scenario_id=101,
            tag="balanced",
            case_dir=str(case_dir),
            run_id=run_id,
            exit_code=1,
            elapsed_seconds=0.01,
            orchestrator_log=str(run_map.parent / "orchestration/failure.log"),
            failure_category=RUN_GROUP.FailureCategory.MODEL.value,
        )

    monkeypatch.setattr(RUN_GROUP, "_run_case", fake_run_case)

    exit_code = RUN_GROUP._run(
        _args(
            model_root=model_root,
            group_dir=group_dir,
            run_map=run_map,
            uv_cache_dir=tmp_path / "uv-cache",
            delete_incomplete=True,
        ),
    )

    payload = json.loads(run_map.read_text(encoding="utf-8"))
    assert exit_code is RUN_GROUP.RunnerExitCode.MODEL
    assert payload["status"] == "FAIL"
    assert payload["failure"]["category"] == "MODEL"
    assert payload["failure"]["failed_cases"][0]["engine_returncode"] == 1
    assert payload["failure"]["runner_exit_code"] == 5
    assert sorted(payload["removed_incomplete"]["scenario_101_balanced"]) == sorted(
        [
            str((model_root / "outputs/20260814_010000").resolve()),
            str((model_root / "log/20260814_010000").resolve()),
        ],
    )
    assert not (model_root / "outputs/20260814_010000").exists()
    assert not (model_root / "log/20260814_010000").exists()
    assert not (model_root / RUN_GROUP.RUN_LOCK_NAME).exists()


@pytest.mark.parametrize(
    ("category", "expected_exit_code"),
    [
        ("PREFLIGHT", 2),
        ("ENVIRONMENT", 3),
        ("INPUT", 4),
        ("MODEL", 5),
    ],
)
def test_failure_categories_have_stable_non_ambiguous_exit_codes(
    category: str,
    expected_exit_code: int,
) -> None:
    assert int(RUN_GROUP.FAILURE_EXIT_CODES[RUN_GROUP.FailureCategory(category)]) == expected_exit_code


def test_run_case_passes_unresolved_venv_path_to_orchestrator_and_child_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_case(tmp_path)
    python_bin = tmp_path / "model/.venv/bin/python"
    observed_command: list[str] = []

    def fake_subprocess_run(command: list[str], **_: Any) -> SimpleNamespace:
        observed_command.extend(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(RUN_GROUP.subprocess, "run", fake_subprocess_run)
    result = RUN_GROUP._run_case(
        model_root=tmp_path / "model",
        python_bin=python_bin,
        case=case,
        run_id="20260814_010000",
        log_path=tmp_path / "orchestration.log",
        uv_cache_dir=tmp_path / "uv-cache",
    )

    assert observed_command[0] == str(python_bin)
    child_option = observed_command.index("--python-bin")
    assert observed_command[child_option + 1] == str(python_bin)
    assert result.exit_code == 0
    assert result.failure_category is None

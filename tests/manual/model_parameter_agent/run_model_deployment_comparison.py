from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values, load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_APP_CONFIG = ROOT_DIR / "envs" / "config.yaml"
DEFAULT_DOTENV = ROOT_DIR / "envs" / ".env"
EVALUATOR_PATH = (
    ROOT_DIR
    / "tests"
    / "manual"
    / "model_parameter_agent"
    / "evaluate_event_type_proposals.py"
)
REPORT_ROOT = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
REPORT_MARKER_PATTERN = re.compile(
    r"^(REPORT(?:_IN_PROGRESS|_UPDATED)?)\s+(\S+\.md)(?:\s|$)"
)
SENSITIVE_ENV_KEY_PATTERN = re.compile(
    r"(?:API_KEY|PASSWORD|SECRET|TOKEN|ACCESS_KEY)", re.IGNORECASE
)

if DEFAULT_DOTENV.exists():
    load_dotenv(DEFAULT_DOTENV, override=False)
if "APP_CONFIG" not in os.environ and DEFAULT_APP_CONFIG.exists():
    os.environ["APP_CONFIG"] = str(DEFAULT_APP_CONFIG)

from apps.common.configs.config import get_settings
from apps.common.logging.logger_config import logger


@dataclass(frozen=True)
class ModelRunSpec:
    label: str
    deployment_name: str


@dataclass
class ScenarioResult:
    scenario_group_id: int | None
    scenario_id: int | None
    event_type_l2_id: int | None
    parameters: str
    outcome: str
    summary: str
    elapsed_seconds: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass
class RunResult:
    label: str
    requested_model: str
    started_at: datetime
    finished_at: datetime | None = None
    return_code: int | None = None
    state: str = "PENDING"
    report_path: Path | None = None
    log_path: Path | None = None
    error_count: int | None = None
    execution_count: int | None = None
    planned_count: int | None = None
    completed_count: int | None = None
    empty_recommendations: int | None = None
    group_status: dict[str, bool] = field(default_factory=dict)
    actual_models: set[str] = field(default_factory=set)
    scenarios: list[ScenarioResult] = field(default_factory=list)
    proposal_core_by_scenario: dict[int, Any] = field(default_factory=dict)
    proposal_full_by_scenario: dict[int, Any] = field(default_factory=dict)
    attempts_by_scenario: dict[int, int] = field(default_factory=dict)
    report_marker_seen: bool = False
    secret_redacted: bool = False
    parse_error: str | None = None

    @property
    def elapsed_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def semantic_pass(self) -> bool | None:
        if not self.group_status:
            return None
        return all(self.group_status.values())

    @property
    def is_complete(self) -> bool:
        return (
            self.report_marker_seen
            and self.return_code == 0
            and self.planned_count is not None
            and self.completed_count == self.planned_count
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare current Public Stage model deployment with Luna, Sol, and Terra.",
    )
    parser.add_argument("--event-type-l2-ids", nargs="+", type=int, default=[6, 7])
    parser.add_argument("--groups-per-event", type=int, default=1)
    parser.add_argument("--scenarios-per-group", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Comparison artifact directory. Defaults to a timestamped directory under tests/reports.",
    )
    return parser.parse_args()


def _now() -> datetime:
    return datetime.now(UTC).astimezone()


def _normalize_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        msg = f"Invalid model endpoint: {endpoint!r}"
        raise ValueError(msg)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        msg = "Model endpoint must not contain user info, query, or fragment"
        raise ValueError(msg)
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _safe_output_dir(value: Path | None) -> Path:
    if value is None:
        timestamp = _now().strftime("%Y%m%d_%H%M%S_%f")
        return REPORT_ROOT / f"model_deployment_comparison_{timestamp}"
    candidate = value if value.is_absolute() else ROOT_DIR / value
    resolved = candidate.resolve()
    report_root = REPORT_ROOT.resolve()
    if not resolved.is_relative_to(report_root):
        msg = f"--output-dir must be under {report_root}"
        raise ValueError(msg)
    return resolved


def _secret_values() -> tuple[str, ...]:
    values: set[str] = set()
    sources: list[dict[str, Any]] = [dict(os.environ)]
    if DEFAULT_DOTENV.exists():
        sources.append(dict(dotenv_values(DEFAULT_DOTENV)))
    for source in sources:
        for key, value in source.items():
            if not SENSITIVE_ENV_KEY_PATTERN.search(str(key)):
                continue
            text = str(value or "")
            if len(text) >= 6:
                values.add(text)
    return tuple(sorted(values, key=len, reverse=True))


def _redact_text(text: str, secrets: tuple[str, ...]) -> tuple[str, bool]:
    redacted = text
    changed = False
    for secret in secrets:
        if secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")
            changed = True
    return redacted, changed


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(text, encoding="utf-8")
    temporary_path.replace(path)


def _validated_report_source(raw_path: str) -> Path | None:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(REPORT_ROOT.resolve()):
        logger.warning(
            "Evaluator report path is outside the expected report root: {}", resolved
        )
        return None
    return resolved


def _snapshot_report(
    *,
    source_path: Path,
    destination_path: Path,
    secrets: tuple[str, ...],
) -> bool:
    if not source_path.is_file():
        return False
    raw_text = source_path.read_text(encoding="utf-8")
    safe_text, redacted = _redact_text(raw_text, secrets)
    _atomic_write(destination_path, safe_text)
    return redacted


def _parse_int_marker(log_text: str, marker: str) -> int | None:
    match = re.search(rf"(?m)^{re.escape(marker)}\s+(\d+)\s*$", log_text)
    return int(match.group(1)) if match else None


def _parse_json_marker(log_text: str, marker: str) -> dict[str, bool]:
    matches = re.findall(rf"(?m)^{re.escape(marker)}\s+(\{{.*\}})\s*$", log_text)
    if not matches:
        return {}
    try:
        payload = json.loads(matches[-1])
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): bool(value) for key, value in payload.items()}


def _extract_bullet_int(report_text: str, label: str) -> int | None:
    match = re.search(rf"(?m)^-\s+{re.escape(label)}:\s+(\d+)\s*$", report_text)
    return int(match.group(1)) if match else None


def _extract_bullet_json_bool_map(report_text: str) -> dict[str, bool]:
    pattern = re.compile(
        r"(?m)^-\s+(?:GROUP_STATUS_BY_SCENARIO_GROUP|PARAMETER_SCENARIO_STATUS):\s+`(\{.*\})`\s*$",
    )
    match = pattern.search(report_text)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, bool] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            result[str(key)] = bool(value.get("passed"))
        else:
            result[str(key)] = bool(value)
    return result


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells = re.split(r"(?<!\\)\|", stripped)[1:-1]
    return [cell.strip().replace("\\|", "|") for cell in cells]


def _leading_int(value: str) -> int | None:
    match = re.match(r"\s*(\d+)", value)
    return int(match.group(1)) if match else None


def _parse_token_cell(value: str) -> tuple[int | None, int | None, int | None]:
    if value == "N/A":
        return None, None, None
    parts = [part.strip().replace(",", "") for part in value.split("/")]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None, None, None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _parse_scenario_rows(report_text: str) -> list[ScenarioResult]:
    lines = report_text.splitlines()
    header = "| 시나리오그룹 | 시나리오 | 이벤트타입 | 파라미터 | 결과요약 | 소요시간 | Token (입력/출력/합계) |"
    try:
        index = lines.index(header)
    except ValueError:
        return []
    results: list[ScenarioResult] = []
    for line in lines[index + 2 :]:
        cells = _split_markdown_row(line)
        if len(cells) != 7:
            break
        if cells[0] == "-":
            continue
        elapsed_match = re.search(r"\((\d+(?:\.\d+)?)s\)\s*$", cells[5])
        prompt_tokens, completion_tokens, total_tokens = _parse_token_cell(cells[6])
        outcome = cells[4].split(" · ", 1)[0].strip()
        results.append(
            ScenarioResult(
                scenario_group_id=_leading_int(cells[0]),
                scenario_id=_leading_int(cells[1]),
                event_type_l2_id=_leading_int(cells[2]),
                parameters=cells[3],
                outcome=outcome,
                summary=cells[4],
                elapsed_seconds=(
                    float(elapsed_match.group(1)) if elapsed_match else None
                ),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )
    return results


def _parse_actual_models(report_text: str) -> set[str]:
    models: set[str] = set()
    for line in report_text.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) != 9 or cells[1] not in {"True", "False"}:
            continue
        if cells[2]:
            models.add(cells[2])
    return models


def _drop_rationale(value: Any) -> Any:
    if isinstance(value, list):
        return [_drop_rationale(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _drop_rationale(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key).lower() != "rationale"
        }
    return value


def _canonicalize(value: Any, *, sort_list: bool = False) -> Any:
    if isinstance(value, list):
        normalized = [_canonicalize(item) for item in value]
        if sort_list:
            return sorted(
                normalized,
                key=lambda item: json.dumps(
                    item, ensure_ascii=False, sort_keys=True, default=str
                ),
            )
        return normalized
    if isinstance(value, dict):
        return {
            str(key): _canonicalize(item, sort_list=str(key) == "values")
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _parse_proposals(report_text: str) -> tuple[dict[int, Any], dict[int, Any]]:
    pattern = re.compile(
        r"(?ms)^#{5,6}\s+Final DB Proposal Row\s*$.*?^```json\s*$\n(.*?)^```\s*$",
    )
    core_by_scenario: dict[int, Any] = {}
    full_by_scenario: dict[int, Any] = {}
    for match in pattern.finditer(report_text):
        try:
            row = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        scenario_id = row.get("scenario_id")
        proposal_parameters = row.get("proposal_parameters")
        if not isinstance(scenario_id, int) or not isinstance(
            proposal_parameters, list
        ):
            continue
        full_by_scenario[scenario_id] = _canonicalize(
            proposal_parameters,
            sort_list=True,
        )
        core_by_scenario[scenario_id] = _canonicalize(
            _drop_rationale(proposal_parameters),
            sort_list=True,
        )
    return core_by_scenario, full_by_scenario


def _parse_attempts(log_text: str, report_text: str) -> dict[int, int]:
    attempts: dict[int, int] = {}
    for match in re.finditer(
        r"(?m)^OK\s+\d+\s+\d+\s+(\d+)\s+attempt=\s+(\d+)\s+",
        log_text,
    ):
        attempts[int(match.group(1))] = int(match.group(2))
    for match in re.finditer(
        r"(?m)^-\s+scenario_id=(\d+).*?\sattempts=(\d+)\s",
        report_text,
    ):
        attempts[int(match.group(1))] = int(match.group(2))
    return attempts


def _parse_report(result: RunResult, log_text: str) -> None:
    result.error_count = _parse_int_marker(log_text, "ERROR_COUNT")
    result.execution_count = _parse_int_marker(log_text, "SCENARIO_EXECUTION_COUNT")
    result.group_status = _parse_json_marker(log_text, "GROUP_STATUS_BY_SCENARIO_GROUP")
    if result.report_path is None or not result.report_path.is_file():
        result.parse_error = "archived report not found"
        return
    report_text = result.report_path.read_text(encoding="utf-8")
    result.planned_count = _extract_bullet_int(
        report_text, "PLANNED_SCENARIO_EXECUTIONS"
    )
    result.completed_count = _extract_bullet_int(
        report_text, "COMPLETED_SCENARIO_EXECUTIONS"
    )
    result.empty_recommendations = _extract_bullet_int(
        report_text, "EMPTY_RECOMMENDATIONS"
    )
    if not result.group_status:
        result.group_status = _extract_bullet_json_bool_map(report_text)
    result.scenarios = _parse_scenario_rows(report_text)
    result.actual_models = _parse_actual_models(report_text)
    result.attempts_by_scenario = _parse_attempts(log_text, report_text)
    (
        result.proposal_core_by_scenario,
        result.proposal_full_by_scenario,
    ) = _parse_proposals(report_text)
    missing: list[str] = []
    if result.planned_count is None:
        missing.append("planned count")
    if result.completed_count is None:
        missing.append("completed count")
    if not result.group_status:
        missing.append("group status")
    if result.completed_count and len(result.scenarios) != result.completed_count:
        missing.append("scenario rows")
    if result.completed_count and not result.actual_models:
        missing.append("actual model names")
    if result.actual_models and result.actual_models != {result.requested_model}:
        missing.append("requested/actual model match")
    if (
        result.completed_count
        and result.error_count == 0
        and len(result.proposal_core_by_scenario) != result.completed_count
    ):
        missing.append("proposal rows")
    if missing:
        result.parse_error = f"missing report fields: {', '.join(missing)}"


def _run_state(result: RunResult) -> str:
    if result.return_code is None:
        return result.state
    if not result.is_complete or result.parse_error:
        return "INCOMPLETE"
    if result.error_count:
        return "FAIL"
    if result.semantic_pass is False:
        return "FAIL"
    if any(scenario.outcome == "FAIL" for scenario in result.scenarios):
        return "FAIL"
    if any(scenario.outcome == "REVIEW" for scenario in result.scenarios):
        return "REVIEW"
    return "PASS"


def _relative_link(path: Path | None, comparison_path: Path) -> str:
    if path is None:
        return "N/A"
    relative = path.relative_to(comparison_path.parent)
    return f"[{path.name}]({relative})"


def _format_number(value: int | float | None, *, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:.{digits}f}"


def _scenario_totals(result: RunResult) -> tuple[int | None, int | None, int | None]:
    if not result.scenarios:
        return 0, 0, 0
    if any(scenario.total_tokens is None for scenario in result.scenarios):
        return None, None, None
    return (
        sum(scenario.prompt_tokens or 0 for scenario in result.scenarios),
        sum(scenario.completion_tokens or 0 for scenario in result.scenarios),
        sum(scenario.total_tokens or 0 for scenario in result.scenarios),
    )


def _average_elapsed(result: RunResult) -> float | None:
    values = [
        scenario.elapsed_seconds
        for scenario in result.scenarios
        if scenario.elapsed_seconds is not None
    ]
    return sum(values) / len(values) if values else None


def _reduction_percent(
    baseline_value: float | int | None, candidate_value: float | int | None
) -> float | None:
    if baseline_value is None or candidate_value is None or baseline_value == 0:
        return None
    return (
        (float(baseline_value) - float(candidate_value)) / float(baseline_value) * 100
    )


def _fingerprint(value: Any | None) -> str:
    if value is None:
        return "N/A"
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(
        serialized.encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:10]


def _comparison_word(
    candidate: RunResult, baseline: RunResult, scenario_id: int
) -> str:
    candidate_core = candidate.proposal_core_by_scenario.get(scenario_id)
    baseline_core = baseline.proposal_core_by_scenario.get(scenario_id)
    if candidate_core is None or baseline_core is None:
        return "N/A"
    if candidate_core != baseline_core:
        return "변동"
    candidate_full = candidate.proposal_full_by_scenario.get(scenario_id)
    baseline_full = baseline.proposal_full_by_scenario.get(scenario_id)
    return "핵심값 동일·근거문구 변동" if candidate_full != baseline_full else "동일"


def _scope_summary(results: list[RunResult]) -> tuple[bool, list[int]]:
    completed_results = [result for result in results if result.scenarios]
    if not completed_results:
        return False, []
    baseline_ids = sorted(
        scenario.scenario_id
        for scenario in completed_results[0].scenarios
        if scenario.scenario_id is not None
    )
    scope_equal = all(
        sorted(
            scenario.scenario_id
            for scenario in result.scenarios
            if scenario.scenario_id is not None
        )
        == baseline_ids
        for result in completed_results[1:]
    )
    return scope_equal and len(completed_results) == len(results), baseline_ids


def _render_comparison(
    *,
    comparison_path: Path,
    endpoint: str,
    app_config: Path,
    args: argparse.Namespace,
    run_specs: list[ModelRunSpec],
    results: list[RunResult],
    started_at: datetime,
    finished_at: datetime | None,
) -> str:
    result_by_label = {result.label: result for result in results}
    baseline = result_by_label.get("baseline")
    scope_equal, scenario_ids = _scope_summary(results)
    lines = [
        "# Model Parameter Agent 모델 배포 비교 리포트",
        "",
        f"- 실행 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 실행 종료: {finished_at.isoformat(timespec='seconds') if finished_at else '진행 중'}",
        f"- Public Stage endpoint: `{endpoint}`",
        "- endpoint 변동: 없음 (네 실행 모두 위 URL 사용)",
        "- API key: 기존 환경값 사용, 리포트에 저장하지 않음",
        f"- APP_CONFIG: `{app_config}`",
        f"- event_type_l2_ids: `{args.event_type_l2_ids}`",
        f"- groups/scenarios: 이벤트타입당 그룹 {args.groups_per_event}개, 그룹당 시나리오 {args.scenarios_per_group}개",
        f"- concurrency/retries: `{args.concurrency}` / `{args.retries}`",
        "- 테스트 범위: proposal 생성 및 저장까지; confirmation은 Step 3·4 범위 밖이라 미실행",
        "- DB 영향: 성공한 시나리오마다 `tmm_mi_model_param_proposal_m`에 `PROPOSED` 행 생성",
        "- 런타임 override: 세 모델 설정 키를 각 후보 deployment로 통일, "
        "`MODEL_PARAMETER_RESOURCE_STORAGE__ENABLED=false`로 packaged resource 고정",
        "- 기존 설정/코드 수정: 없음 (별도 runner와 생성된 리포트 파일만 추가)",
        "",
        "## 요청 모델",
        "",
        "| 순서 | 구분 | deployment |",
        "|---:|---|---|",
    ]
    for index, spec in enumerate(run_specs, start=1):
        lines.append(f"| {index} | {spec.label} | `{spec.deployment_name}` |")

    lines.extend(
        [
            "",
            "## 실행 요약",
            "",
            "| 구분 | 상태 | 실제 호출 model_name | 오류 | 완료/계획 | 그룹 판정 | 빈 제안 | 평균 시간(초) | "
            "Token 합계 | 원본 리포트 | 로그 |",
            "|---|---|---|---:|---:|---|---:|---:|---:|---|---|",
        ],
    )
    for spec in run_specs:
        result = result_by_label.get(spec.label)
        if result is None:
            lines.append(
                f"| {spec.label} | PENDING | - | - | - | - | - | - | - | - | - |"
            )
            continue
        _, _, total_tokens = _scenario_totals(result)
        actual_models = (
            ", ".join(f"`{item}`" for item in sorted(result.actual_models)) or "N/A"
        )
        semantic = (
            "PASS"
            if result.semantic_pass is True
            else "FAIL" if result.semantic_pass is False else "N/A"
        )
        lines.append(
            "| {label} | {state} | {models} | {errors} | {completed}/{planned} | {semantic} | {empty} | "
            "{elapsed} | {tokens} | {report} | {log} |".format(
                label=result.label,
                state=_run_state(result),
                models=actual_models,
                errors=_format_number(result.error_count),
                completed=_format_number(result.completed_count),
                planned=_format_number(result.planned_count),
                semantic=semantic,
                empty=_format_number(result.empty_recommendations),
                elapsed=_format_number(_average_elapsed(result)),
                tokens=_format_number(total_tokens),
                report=_relative_link(result.report_path, comparison_path),
                log=_relative_link(result.log_path, comparison_path),
            ),
        )

    lines.extend(
        [
            "",
            "## 동일 범위 검증",
            "",
            f"- 네 실행의 scenario_id 집합 일치: `{'PASS' if scope_equal else 'FAIL 또는 미완료'}`",
            f"- 비교 scenario_ids: `{scenario_ids}`",
            "",
            "## 시나리오별 결과 및 baseline 대비 변동",
            "",
            "| scenario_id | event_type_l2_id | baseline | Luna | Sol | Terra |",
            "|---:|---:|---|---|---|---|",
        ],
    )
    for scenario_id in scenario_ids:
        baseline_scenario = next(
            (
                scenario
                for scenario in (baseline.scenarios if baseline else [])
                if scenario.scenario_id == scenario_id
            ),
            None,
        )
        event_type_l2_id = (
            baseline_scenario.event_type_l2_id if baseline_scenario else None
        )

        def cell(label: str) -> str:
            result = result_by_label.get(label)
            if result is None:
                return "N/A"
            scenario = next(
                (item for item in result.scenarios if item.scenario_id == scenario_id),
                None,
            )
            if scenario is None:
                return "N/A"
            timing = _format_number(scenario.elapsed_seconds)
            tokens = _format_number(scenario.total_tokens)
            if label == "baseline" or baseline is None:
                detail = f"fingerprint={_fingerprint(result.proposal_core_by_scenario.get(scenario_id))}"
            else:
                detail = _comparison_word(result, baseline, scenario_id)
            attempts = result.attempts_by_scenario.get(scenario_id)
            retries = max(0, attempts - 1) if attempts is not None else None
            return (
                f"{scenario.outcome}; {timing}s; {tokens} tokens; "
                f"outer retry={_format_number(retries)}; {detail}"
            )

        lines.append(
            f"| {scenario_id} | {_format_number(event_type_l2_id)} | {cell('baseline')} | "
            f"{cell('luna')} | {cell('sol')} | {cell('terra')} |",
        )

    lines.extend(
        [
            "",
            "## 모델별 성능 집계",
            "",
            "| 구분 | PASS/REVIEW/FAIL | outer retry 합계 | 평균/최대 시간(초) | 입력/출력/합계 Token |",
            "|---|---|---:|---:|---:|",
        ],
    )
    for spec in run_specs:
        result = result_by_label.get(spec.label)
        if result is None:
            lines.append(f"| {spec.label} | N/A | N/A | N/A | N/A |")
            continue
        outcomes = {
            key: sum(1 for scenario in result.scenarios if scenario.outcome == key)
            for key in ("PASS", "REVIEW", "FAIL")
        }
        elapsed_values = [
            scenario.elapsed_seconds
            for scenario in result.scenarios
            if scenario.elapsed_seconds is not None
        ]
        prompt_tokens, completion_tokens, total_tokens = _scenario_totals(result)
        retry_total = sum(
            max(0, attempts - 1) for attempts in result.attempts_by_scenario.values()
        )
        lines.append(
            "| {label} | {passed}/{review}/{failed} | {retries} | {average}/{maximum} | "
            "{prompt}/{completion}/{total} |".format(
                label=result.label,
                passed=outcomes["PASS"],
                review=outcomes["REVIEW"],
                failed=outcomes["FAIL"],
                retries=retry_total,
                average=_format_number(_average_elapsed(result)),
                maximum=_format_number(max(elapsed_values) if elapsed_values else None),
                prompt=_format_number(prompt_tokens),
                completion=_format_number(completion_tokens),
                total=_format_number(total_tokens),
            ),
        )

    lines.extend(["", "## 결론", ""])
    if finished_at is None:
        lines.append("- 실행 진행 중입니다. 각 모델 종료 시 이 파일이 갱신됩니다.")
    elif baseline is None or not baseline.is_complete:
        lines.append(
            "- baseline이 완결되지 않아 Public Stage 현재 모델 대비 변동 여부를 확정할 수 없습니다."
        )
    else:
        lines.append(
            "- Public Stage endpoint 자체는 변경하지 않았습니다. 비교 변수는 deployment 이름뿐입니다."
        )
        for label in ("luna", "sol", "terra"):
            candidate = result_by_label.get(label)
            if candidate is None or not candidate.is_complete:
                lines.append(
                    f"- {label}: 실행이 미완료되어 baseline 대비 변동 여부를 확정할 수 없습니다."
                )
                continue
            comparable_ids = sorted(
                set(baseline.proposal_core_by_scenario)
                & set(candidate.proposal_core_by_scenario),
            )
            changed_ids = [
                scenario_id
                for scenario_id in comparable_ids
                if baseline.proposal_core_by_scenario[scenario_id]
                != candidate.proposal_core_by_scenario[scenario_id]
            ]
            _, _, baseline_tokens = _scenario_totals(baseline)
            _, _, candidate_tokens = _scenario_totals(candidate)
            time_reduction = _reduction_percent(
                _average_elapsed(baseline),
                _average_elapsed(candidate),
            )
            token_reduction = _reduction_percent(
                baseline_tokens,
                candidate_tokens,
            )
            lines.append(
                f"- {label}: proposal 핵심값 비교 가능 {len(comparable_ids)}건 중 "
                f"{len(changed_ids)}건 변동 (`{changed_ids}`), "
                f"실행 상태 `{_run_state(candidate)}`; baseline 대비 평균 시간 "
                f"{_format_number(time_reduction, digits=1)}% 감소, Token "
                f"{_format_number(token_reduction, digits=1)}% 감소.",
            )
    lines.extend(
        [
            "",
            "## 해석 한계",
            "",
            "- deployment 문자열은 gateway 요청값이며, alias 뒤 실제 backend 모델 식별자를 별도로 검증하지 않습니다.",
            "- 각 모델의 앞 단계 출력이 뒤 단계 입력을 바꾸므로 결과는 동일 Step 3 prompt 비교가 아닌 end-to-end 비교입니다.",
            "- 단일 반복 결과이며 gateway/DB 상태와 모델 비결정성의 영향을 받을 수 있습니다.",
            "- confirmation 결과는 포함하지 않습니다.",
        ],
    )
    parse_errors = [
        f"{result.label}: {result.parse_error}"
        for result in results
        if result.parse_error
    ]
    if parse_errors:
        lines.extend(["", "## 파싱 경고", ""])
        lines.extend(f"- {error}" for error in parse_errors)
    return "\n".join(lines) + "\n"


def _checkpoint(
    *,
    comparison_path: Path,
    endpoint: str,
    app_config: Path,
    args: argparse.Namespace,
    run_specs: list[ModelRunSpec],
    results: list[RunResult],
    started_at: datetime,
    finished_at: datetime | None,
) -> None:
    _atomic_write(
        comparison_path,
        _render_comparison(
            comparison_path=comparison_path,
            endpoint=endpoint,
            app_config=app_config,
            args=args,
            run_specs=run_specs,
            results=results,
            started_at=started_at,
            finished_at=finished_at,
        ),
    )


def _child_environment(
    *,
    endpoint: str,
    deployment_name: str,
    app_config: Path,
) -> dict[str, str]:
    child_env = os.environ.copy()
    child_env.update(
        {
            "APP_CONFIG": str(app_config),
            "MODEL_ENDPOINT": endpoint,
            "MODEL_API_DEPLOYMENT_NAME": deployment_name,
            "LIGHTLY_THINKING_MODEL_API_DEPLOYMENT_NAME": deployment_name,
            "DEEPLY_THINKING_MODEL_API_DEPLOYMENT_NAME": deployment_name,
            "MODEL_PARAMETER_RESOURCE_STORAGE__ENABLED": "false",
            "PYTHONUNBUFFERED": "1",
        },
    )
    child_env.pop("OPENAI_LOG", None)
    return child_env


def _evaluator_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "-u",
        str(EVALUATOR_PATH),
        "--event-type-l2-ids",
        *(str(value) for value in args.event_type_l2_ids),
        "--groups-per-event",
        str(args.groups_per_event),
        "--scenarios-per-group",
        str(args.scenarios_per_group),
        "--concurrency",
        str(args.concurrency),
        "--retries",
        str(args.retries),
    ]


def _run_one(
    *,
    index: int,
    spec: ModelRunSpec,
    output_dir: Path,
    endpoint: str,
    app_config: Path,
    args: argparse.Namespace,
    secrets: tuple[str, ...],
) -> RunResult:
    run_report_path = output_dir / "runs" / f"{index:02d}_{spec.label}.md"
    log_path = output_dir / "logs" / f"{index:02d}_{spec.label}.log"
    result = RunResult(
        label=spec.label,
        requested_model=spec.deployment_name,
        started_at=_now(),
        state="RUNNING",
        report_path=run_report_path,
        log_path=log_path,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = _evaluator_command(args)
    logger.info("Starting {} with deployment {}", spec.label, spec.deployment_name)
    process = subprocess.Popen(  # noqa: S603
        command,
        cwd=ROOT_DIR,
        env=_child_environment(
            endpoint=endpoint,
            deployment_name=spec.deployment_name,
            app_config=app_config,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    log_lines: list[str] = []
    source_report_path: Path | None = None
    try:
        if process.stdout is None:
            msg = "Evaluator stdout pipe was not created"
            raise RuntimeError(msg)
        with log_path.open("w", encoding="utf-8") as log_file:
            for raw_line in process.stdout:
                safe_line, redacted = _redact_text(raw_line, secrets)
                result.secret_redacted = result.secret_redacted or redacted
                log_lines.append(safe_line)
                log_file.write(safe_line)
                log_file.flush()
                logger.info("[{}] {}", spec.label, safe_line.rstrip())
                marker_match = REPORT_MARKER_PATTERN.match(safe_line.strip())
                if not marker_match:
                    continue
                candidate = _validated_report_source(marker_match.group(2))
                if candidate is None:
                    continue
                source_report_path = candidate
                result.secret_redacted = (
                    _snapshot_report(
                        source_path=candidate,
                        destination_path=run_report_path,
                        secrets=secrets,
                    )
                    or result.secret_redacted
                )
                if marker_match.group(1) == "REPORT":
                    result.report_marker_seen = True
        result.return_code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        result.return_code = process.returncode
        result.parse_error = "interrupted"
        raise
    finally:
        if source_report_path is not None:
            result.secret_redacted = (
                _snapshot_report(
                    source_path=source_report_path,
                    destination_path=run_report_path,
                    secrets=secrets,
                )
                or result.secret_redacted
            )
        result.finished_at = _now()
        _parse_report(result, "".join(log_lines))
        result.state = _run_state(result)
        logger.info(
            "Finished {}: state={}, return_code={}, elapsed={:.3f}s",
            spec.label,
            result.state,
            result.return_code,
            result.elapsed_seconds or 0.0,
        )
    return result


def _write_manifest(
    *,
    path: Path,
    endpoint: str,
    app_config: Path,
    args: argparse.Namespace,
    run_specs: list[ModelRunSpec],
    results: list[RunResult],
) -> None:
    payload = {
        "endpoint": endpoint,
        "app_config": str(app_config),
        "scope": {
            "event_type_l2_ids": args.event_type_l2_ids,
            "groups_per_event": args.groups_per_event,
            "scenarios_per_group": args.scenarios_per_group,
            "concurrency": args.concurrency,
            "retries": args.retries,
        },
        "runtime_overrides": {
            "model_keys": "all three model deployment keys set to the run candidate",
            "model_parameter_resource_storage_enabled": False,
        },
        "confirmation_executed": False,
        "runs": [
            {
                "label": spec.label,
                "requested_model": spec.deployment_name,
                "state": next(
                    (result.state for result in results if result.label == spec.label),
                    "PENDING",
                ),
                "report": next(
                    (
                        str(result.report_path)
                        for result in results
                        if result.label == spec.label
                    ),
                    None,
                ),
                "log": next(
                    (
                        str(result.log_path)
                        for result in results
                        if result.label == spec.label
                    ),
                    None,
                ),
            }
            for spec in run_specs
        ],
    }
    _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    endpoint = _normalize_endpoint(settings.model_endpoint)
    app_config = (
        Path(os.environ.get("APP_CONFIG", DEFAULT_APP_CONFIG)).expanduser().resolve()
    )
    output_dir = _safe_output_dir(args.output_dir)
    if output_dir.exists():
        msg = f"Output directory already exists: {output_dir}"
        raise FileExistsError(msg)
    output_dir.mkdir(parents=True)
    comparison_path = output_dir / "comparison.md"
    manifest_path = output_dir / "manifest.json"
    run_specs = [
        ModelRunSpec("baseline", settings.deeply_thinking_model_api_deployment_name),
        ModelRunSpec("luna", "skmidev-gpt-5.6-luna-20260709-mip"),
        ModelRunSpec("sol", "skmidev-gpt-5.6-sol-20260709-mip"),
        ModelRunSpec("terra", "skmidev-gpt-5.6-terra-20260709-mip"),
    ]
    secrets = _secret_values()
    started_at = _now()
    results: list[RunResult] = []
    _checkpoint(
        comparison_path=comparison_path,
        endpoint=endpoint,
        app_config=app_config,
        args=args,
        run_specs=run_specs,
        results=results,
        started_at=started_at,
        finished_at=None,
    )
    _write_manifest(
        path=manifest_path,
        endpoint=endpoint,
        app_config=app_config,
        args=args,
        run_specs=run_specs,
        results=results,
    )

    interrupted = False
    try:
        for index, spec in enumerate(run_specs, start=1):
            result = _run_one(
                index=index,
                spec=spec,
                output_dir=output_dir,
                endpoint=endpoint,
                app_config=app_config,
                args=args,
                secrets=secrets,
            )
            results.append(result)
            _checkpoint(
                comparison_path=comparison_path,
                endpoint=endpoint,
                app_config=app_config,
                args=args,
                run_specs=run_specs,
                results=results,
                started_at=started_at,
                finished_at=None,
            )
            _write_manifest(
                path=manifest_path,
                endpoint=endpoint,
                app_config=app_config,
                args=args,
                run_specs=run_specs,
                results=results,
            )
    except KeyboardInterrupt:
        interrupted = True
        logger.warning("Comparison run interrupted; partial artifacts were preserved")
    finally:
        finished_at = _now()
        _checkpoint(
            comparison_path=comparison_path,
            endpoint=endpoint,
            app_config=app_config,
            args=args,
            run_specs=run_specs,
            results=results,
            started_at=started_at,
            finished_at=finished_at,
        )
        _write_manifest(
            path=manifest_path,
            endpoint=endpoint,
            app_config=app_config,
            args=args,
            run_specs=run_specs,
            results=results,
        )

    logger.info("Comparison report: {}", comparison_path)
    logger.info("Manifest: {}", manifest_path)
    if interrupted or len(results) != len(run_specs):
        raise SystemExit(2)
    if any(_run_state(result) in {"FAIL", "INCOMPLETE"} for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

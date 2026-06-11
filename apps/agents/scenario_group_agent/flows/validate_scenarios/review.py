from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


PRICE_TIERS = (
    "strong_bull",
    "bull",
    "mild_bull",
    "neutral",
    "mild_bear",
    "bear",
    "strong_bear",
)
GROUP_STATUS_ENUM = ("creating", "created", "realized")
GROUP_STAGE_ENUM = (
    "ready",
    "scenario_created",
    "scenario_validated",
    "signpost_created",
    "completed",
)
SCENARIO_STATUS_ENUM = ("creating", "created", "realized", "discarded")
TAIL_OVERRIDE = {"supply_disruption_pattern": "P4: Permanent loss"}

COMPAT_SYSTEM = """\
당신은 LNG 멀티시나리오의 Compatibility Judge 입니다.
각 시나리오는 Dimension과 값의 조합으로 정의됩니다. 조합 안의 값들이 서로
물리적 또는 논리적으로 모순되는지 판정하십시오.

- 명백한 물리적 또는 논리적 모순이 있을 때만 compatible=false로 판정합니다.
- 단지 드물거나 강한 조합이라는 이유로 false로 판정하지 않습니다.
- narrative가 조합의 의도를 합리적으로 설명하면 모순으로 판정하지 않습니다.
- 입력의 모든 scenario_id를 정확히 한 번 포함하고 reason은 한국어 한 줄로 작성합니다.
"""


class CompatibilityItem(BaseModel):
    scenario_id: int
    compatible: bool
    reason: str


class CompatibilityOutput(BaseModel):
    items: list[CompatibilityItem] = Field(default_factory=list)


class CompatibilityInvocationResult(Protocol):
    result: CompatibilityOutput


@dataclass
class CheckResult:
    check_id: str
    stage: str
    name: str
    status: Literal["PASS", "WARN", "FAIL", "INFO"]
    detail: str
    offenders: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "stage": self.stage,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "offenders": self.offenders,
        }


@dataclass
class ReviewContext:
    group: dict[str, Any]
    scenarios: list[dict[str, Any]]
    template_dims: list[dict[str, Any]]
    selected_dims: list[str]
    dim_index: dict[str, dict[str, Any]]
    enum_index: dict[str, list[str]]
    tail_index: dict[str, str | None]
    persisted_scenario_ids: set[int]


@dataclass
class ReviewReport:
    verdict: Literal["PASS", "REVIEW", "BLOCK"]
    is_valid: bool
    reason: str
    summary: dict[str, int]
    checks: list[CheckResult]


def build_context(
    group: dict[str, Any],
    requested_rows: list[dict[str, Any]],
    persisted_scenarios: list[dict[str, Any]],
    template_dims: list[dict[str, Any]],
) -> ReviewContext:
    persisted_by_id = {
        int(scenario["scenario_id"]): scenario for scenario in persisted_scenarios
    }
    scenarios = [
        _normalize_scenario(row, persisted_by_id.get(int(row["scenario_id"])))
        for row in requested_rows
    ]
    dim_index = {
        str(dimension["dim_key"]): dimension
        for dimension in template_dims
        if isinstance(dimension, dict) and dimension.get("dim_key")
    }
    enum_index = {
        key: [str(value) for value in dimension.get("value_enums", [])]
        for key, dimension in dim_index.items()
    }
    tail_index = {
        key: TAIL_OVERRIDE.get(key, values[-1] if values else None)
        for key, values in enum_index.items()
    }
    return ReviewContext(
        group=group,
        scenarios=scenarios,
        template_dims=template_dims,
        selected_dims=[str(key) for key in group.get("dimension_selected") or []],
        dim_index=dim_index,
        enum_index=enum_index,
        tail_index=tail_index,
        persisted_scenario_ids=set(persisted_by_id),
    )


def _normalize_scenario(
    row: dict[str, Any],
    persisted: dict[str, Any] | None,
) -> dict[str, Any]:
    persisted = persisted or {}
    metrics = row.get("metrics") or {}
    impact = row.get("impact") or {}
    return {
        "scenario_id": int(row["scenario_id"]),
        "scenario_group_id": persisted.get("scenario_group_id"),
        "title": row.get("title") or persisted.get("title") or "",
        "narrative": row.get("narrative") or persisted.get("narrative") or "",
        "status": persisted.get("status"),
        "dimension_values": row.get("cells") or {},
        "probability_score": metrics.get(
            "probability_score", persisted.get("probability_score"),
        ),
        "probability_delta": metrics.get(
            "probability_delta", persisted.get("probability_delta"),
        ),
        "impact_jkm": impact.get("jkm", persisted.get("impact_jkm")),
        "impact_ttf": impact.get("ttf", persisted.get("impact_ttf")),
        "impact_hh": impact.get("hh", persisted.get("impact_hh")),
        "baseline_yn": row.get("baseline_yn") or persisted.get("baseline_yn"),
        "del_yn": "N",
    }


def _sid(scenario: dict[str, Any]) -> str:
    return str(scenario.get("scenario_id", "?"))


def _check_count(ctx: ReviewContext) -> CheckResult:
    declared = ctx.group.get("scenario_count")
    actual = len(ctx.scenarios)
    return CheckResult(
        "R01",
        "구조",
        "scenario_count = 실제 시나리오 수",
        "PASS" if declared == actual else "FAIL",
        f"선언={declared}, 실제={actual}",
    )


def _check_group_fk(ctx: ReviewContext) -> CheckResult:
    group_id = ctx.group.get("scenario_group_id")
    bad = [
        _sid(scenario)
        for scenario in ctx.scenarios
        if scenario["scenario_id"] not in ctx.persisted_scenario_ids
        or scenario.get("scenario_group_id") != group_id
    ]
    return CheckResult(
        "R02",
        "구조",
        "모든 시나리오의 group_id 일치",
        "PASS" if not bad else "FAIL",
        f"그룹 id={group_id}" if not bad else f"불일치 {len(bad)}건",
        bad,
    )


def _check_enums(ctx: ReviewContext) -> CheckResult:
    bad: list[str] = []
    if ctx.group.get("status") not in GROUP_STATUS_ENUM:
        bad.append(f"group.status={ctx.group.get('status')}")
    if ctx.group.get("stage") not in GROUP_STAGE_ENUM:
        bad.append(f"group.stage={ctx.group.get('stage')}")
    for scenario in ctx.scenarios:
        if scenario.get("status") not in SCENARIO_STATUS_ENUM:
            bad.append(f"{_sid(scenario)}.status={scenario.get('status')}")
        if scenario.get("baseline_yn") not in ("Y", "N"):
            bad.append(
                f"{_sid(scenario)}.baseline_yn={scenario.get('baseline_yn')}",
            )
    return CheckResult(
        "R03",
        "구조",
        "status/stage/Y·N 컬럼 CHECK 제약",
        "PASS" if not bad else "FAIL",
        "위반 없음" if not bad else f"위반 {len(bad)}건",
        bad,
    )


def _check_arrays(ctx: ReviewContext) -> CheckResult:
    bad: list[str] = []
    if not isinstance(ctx.group.get("dimension_selected"), list):
        bad.append("group.dimension_selected")
    bad.extend(
        f"{_sid(scenario)}.dimension_values"
        for scenario in ctx.scenarios
        if not isinstance(scenario.get("dimension_values"), dict)
    )
    return CheckResult(
        "R04",
        "구조",
        "JSON Dimension 컬럼 구조",
        "PASS" if not bad else "FAIL",
        "정상 구조" if not bad else f"구조 오류 {len(bad)}건",
        bad,
    )


def _check_required(ctx: ReviewContext) -> CheckResult:
    bad: list[str] = []
    if not ctx.group.get("mi_event_id"):
        bad.append("group.mi_event_id")
    if not str(ctx.group.get("title", "")).strip():
        bad.append("group.title")
    bad.extend(
        f"{_sid(scenario)}.title"
        for scenario in ctx.scenarios
        if not str(scenario.get("title", "")).strip()
    )
    return CheckResult(
        "R05",
        "구조",
        "필수 식별/제목 컬럼 존재",
        "PASS" if not bad else "FAIL",
        "필수값 충족" if not bad else f"누락 {len(bad)}건",
        bad,
    )


def _check_dim_in_template(ctx: ReviewContext) -> CheckResult:
    if not ctx.template_dims:
        return CheckResult(
            "R06",
            "Stage2",
            "선택 Dim이 템플릿에 존재",
            "FAIL",
            "기준 템플릿 미해석",
        )
    bad = [key for key in ctx.selected_dims if key not in ctx.dim_index]
    return CheckResult(
        "R06",
        "Stage2",
        "선택 Dim이 템플릿에 존재",
        "PASS" if not bad else "FAIL",
        f"템플릿 Dim {len(ctx.dim_index)}개와 대조"
        if not bad
        else f"미정의 {len(bad)}건",
        bad,
    )


def _check_dim_consistency(ctx: ReviewContext) -> CheckResult:
    wanted = set(ctx.selected_dims)
    bad: list[str] = []
    for scenario in ctx.scenarios:
        keys = set(scenario["dimension_values"])
        if keys != wanted:
            bad.append(
                f"{_sid(scenario)} (누락={sorted(wanted - keys)}, "
                f"여분={sorted(keys - wanted)})",
            )
    return CheckResult(
        "R07",
        "Stage2",
        "시나리오가 선택 Dim을 정확히 1:1 사용",
        "PASS" if not bad else "FAIL",
        "선택 Dim 전부·그것만 사용" if not bad else f"불일치 {len(bad)}건",
        bad,
    )


def _check_value_valid(ctx: ReviewContext) -> CheckResult:
    bad: list[str] = []
    for scenario in ctx.scenarios:
        for key, value in scenario["dimension_values"].items():
            allowed = ctx.enum_index.get(key)
            if allowed is not None and value not in allowed:
                bad.append(f"{_sid(scenario)}: {key}={value}")
    return CheckResult(
        "R08",
        "Stage3",
        "사용된 값이 value_enums 내",
        "PASS" if not bad else "FAIL",
        "모든 값 유효" if not bad else f"미정의 값 {len(bad)}건",
        bad,
    )


def _used_values(ctx: ReviewContext) -> dict[str, set[object]]:
    used = {key: set() for key in ctx.selected_dims}
    for scenario in ctx.scenarios:
        for key, value in scenario["dimension_values"].items():
            if key in used:
                used[key].add(_hashable(value))
    return used


def _hashable(value: object) -> object:
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


def _check_tail_preserved(ctx: ReviewContext) -> CheckResult:
    used = _used_values(ctx)
    missing = [
        f"{key} (tail='{ctx.tail_index[key]}')"
        for key in ctx.selected_dims
        if ctx.tail_index.get(key)
        and ctx.tail_index[key] not in used.get(key, set())
    ]
    return CheckResult(
        "R09",
        "Stage3",
        "선택 Dim별 극단값(tail) 보존",
        "PASS" if not missing else "WARN",
        "모든 Dim에서 tail 등장" if not missing else f"tail 미등장 {len(missing)}건",
        missing,
    )


def _check_value_diversity(ctx: ReviewContext) -> CheckResult:
    used = _used_values(ctx)
    bad = [key for key, values in used.items() if len(values) < 2]
    return CheckResult(
        "R10",
        "Stage3",
        "각 선택 Dim 값 다양성 ≥2",
        "PASS" if not bad else "WARN",
        " / ".join(f"{key}={len(values)}값" for key, values in used.items())
        if not bad
        else f"단일값 Dim {len(bad)}건",
        bad,
    )


def _check_impact_tiers(ctx: ReviewContext) -> CheckResult:
    bad: list[str] = []
    for scenario in ctx.scenarios:
        for field_name in ("impact_jkm", "impact_ttf", "impact_hh"):
            value = scenario.get(field_name)
            if value is not None and value not in PRICE_TIERS:
                bad.append(f"{_sid(scenario)}.{field_name}={value}")
    return CheckResult(
        "R11",
        "Stage4",
        "방향성(JKM/TTF/HH) 7단계 enum",
        "PASS" if not bad else "FAIL",
        "모두 7단계 내" if not bad else f"범위 밖 {len(bad)}건",
        bad,
    )


async def _check_compatibility(ctx: ReviewContext) -> CheckResult:
    if not ctx.scenarios:
        return CheckResult(
            "R12",
            "Stage4",
            "Compatibility(조합 모순) — LLM 판정",
            "INFO",
            "검증할 시나리오 없음",
        )
    lines: list[str] = []
    for scenario in ctx.scenarios:
        pairs = ", ".join(
            f"{ctx.dim_index.get(key, {}).get('label', key)}='{value}'"
            for key, value in scenario["dimension_values"].items()
        )
        lines.append(
            f"- {scenario['scenario_id']} [{scenario['title']}]: {pairs}\n"
            f"  narrative: {scenario['narrative']}",
        )
    messages = [
        {"role": "system", "content": COMPAT_SYSTEM},
        {
            "role": "user",
            "content": "다음 시나리오 조합을 판정하십시오.\n" + "\n".join(lines),
        },
    ]
    try:
        result = await _invoke_compatibility(messages=messages)
        items = result.result.items
        expected = {scenario["scenario_id"] for scenario in ctx.scenarios}
        actual = {item.scenario_id for item in items}
        if len(items) != len(actual) or actual != expected:
            return CheckResult(
                "R12",
                "Stage4",
                "Compatibility(조합 모순) — LLM 판정",
                "WARN",
                "LLM 응답 scenario_id 집합 불일치: "
                f"누락={expected - actual}, 여분={actual - expected}",
            )
        offenders = [
            f"{item.scenario_id}: {item.reason}"
            for item in items
            if not item.compatible
        ]
        return CheckResult(
            "R12",
            "Stage4",
            "Compatibility(조합 모순) — LLM 판정",
            "PASS" if not offenders else "FAIL",
            f"{len(items)}건 판정 — 모순 없음"
            if not offenders
            else f"모순 {len(offenders)}건",
            offenders,
        )
    except Exception as exc:
        return CheckResult(
            "R12",
            "Stage4",
            "Compatibility(조합 모순) — LLM 판정",
            "WARN",
            f"LLM 판정 실패: {type(exc).__name__}: {str(exc)[:120]}",
        )


async def _invoke_compatibility(
    *,
    messages: list[dict[str, str]],
) -> CompatibilityInvocationResult:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    return await invoke_llm_structured_output(
        CompatibilityOutput,
        messages=messages,
    )


def _check_mece(ctx: ReviewContext) -> CheckResult:
    seen: dict[tuple[tuple[str, Any], ...], str] = {}
    duplicates: list[str] = []
    for scenario in ctx.scenarios:
        key = tuple(
            sorted(
                (dimension, _hashable(value))
                for dimension, value in scenario["dimension_values"].items()
            ),
        )
        if key in seen:
            duplicates.append(f"{_sid(scenario)} = {seen[key]}")
        else:
            seen[key] = _sid(scenario)
    return CheckResult(
        "R13",
        "Stage5",
        "MECE — 조합 유일(상호배타)",
        "PASS" if not duplicates else "FAIL",
        "모든 조합 유일" if not duplicates else f"중복 조합 {len(duplicates)}쌍",
        duplicates,
    )


def _in_range(value: object, lower: Decimal, upper: Decimal) -> bool:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return lower <= parsed <= upper


def _check_probability_range(ctx: ReviewContext) -> CheckResult:
    bad: list[str] = []
    for scenario in ctx.scenarios:
        score = scenario.get("probability_score")
        if score is None:
            bad.append(f"{_sid(scenario)} (probability_score 누락)")
        elif not _in_range(score, Decimal("0"), Decimal("100")):
            bad.append(f"{_sid(scenario)} score={score}")
        delta = scenario.get("probability_delta")
        if delta is not None and not _in_range(
            delta, Decimal("-100"), Decimal("100"),
        ):
            bad.append(f"{_sid(scenario)} delta={delta}")
    return CheckResult(
        "R14",
        "Stage5",
        "확률/증감 값 범위 (0~100 / ±100)",
        "PASS" if not bad else "FAIL",
        "모든 확률값 범위 내" if not bad else f"범위 밖 {len(bad)}건",
        bad,
    )


CHECKS: list[Callable[[ReviewContext], CheckResult]] = [
    _check_count,
    _check_group_fk,
    _check_enums,
    _check_arrays,
    _check_required,
    _check_dim_in_template,
    _check_dim_consistency,
    _check_value_valid,
    _check_tail_preserved,
    _check_value_diversity,
    _check_impact_tiers,
]


async def run_review(ctx: ReviewContext) -> ReviewReport:
    checks: list[CheckResult] = []
    for check in CHECKS:
        try:
            checks.append(check(ctx))
        except Exception as exc:
            checks.append(
                CheckResult(
                    check.__name__,
                    "?",
                    check.__name__,
                    "FAIL",
                    f"검사 예외: {type(exc).__name__}: {exc}",
                ),
            )
    checks.append(await _check_compatibility(ctx))
    for check in (_check_mece, _check_probability_range):
        try:
            checks.append(check(ctx))
        except Exception as exc:
            checks.append(
                CheckResult(
                    check.__name__,
                    "?",
                    check.__name__,
                    "FAIL",
                    f"검사 예외: {type(exc).__name__}: {exc}",
                ),
            )
    counts = Counter(check.status for check in checks)
    summary = {
        status: counts.get(status, 0) for status in ("PASS", "WARN", "FAIL", "INFO")
    }
    if summary["FAIL"]:
        verdict: Literal["PASS", "REVIEW", "BLOCK"] = "BLOCK"
    elif summary["WARN"]:
        verdict = "REVIEW"
    else:
        verdict = "PASS"
    notable = [
        check for check in checks if check.status in {"FAIL", "WARN"}
    ]
    reason = (
        "; ".join(f"{check.check_id}: {check.detail}" for check in notable)
        if notable
        else "All scenario review checks passed"
    )
    return ReviewReport(
        verdict=verdict,
        is_valid=verdict != "BLOCK",
        reason=reason,
        summary=summary,
        checks=checks,
    )

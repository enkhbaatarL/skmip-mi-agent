from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


TAIL_OVERRIDE = {"supply_disruption_pattern": "P4: Permanent loss"}

COMPAT_SYSTEM = """\
당신은 LNG 멀티시나리오의 Compatibility Judge 입니다.
각 시나리오는 Dimension과 값의 조합으로 정의됩니다. 조합 안의 값들이 서로
물리적 또는 논리적으로 모순되는지 판정하십시오.

- 명백한 물리적 또는 논리적 모순이 있을 때만 compatible=false로 판정합니다.
- 단지 드물거나 강한 조합이라는 이유로 false로 판정하지 않습니다.
- narrative가 조합의 의도를 합리적으로 설명하면 모순으로 판정하지 않습니다.
- 입력의 모든 scenario_id를 정확히 한 번 포함하고 reason은 한국어 한 줄로 작성합니다.
- compatible=false인 경우, 모순을 일으키는 두 항목을 다음 필드로 함께 채웁니다.
  · conflict_dim_a / conflict_value_a : 충돌하는 첫 번째 항목명과 값 (입력에 표시된 항목명·값 그대로)
  · conflict_dim_b / conflict_value_b : 충돌하는 두 번째 항목명과 값
  · recommended_value_b : conflict_value_b 를 대체하면 모순이 해소되는 권장 값
- compatible=true인 경우 위 다섯 필드는 비워 둡니다(null).
"""


class CompatibilityItem(BaseModel):
    scenario_id: int
    compatible: bool
    reason: str
    conflict_dim_a: str | None = None
    conflict_value_a: str | None = None
    conflict_dim_b: str | None = None
    conflict_value_b: str | None = None
    recommended_value_b: str | None = None


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
    # 현업 사용자에게 그대로 노출할 완성형 안내 문장(시나리오명·값·권장 변경 포함).
    # 비어 있으면 CHECK_DISPLAY 기반 일반 문구로 대체된다.
    advice: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "stage": self.stage,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "offenders": self.offenders,
            "advice": self.advice,
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
    persisted_scenario_id_counts: Counter[int]


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
        persisted_scenario_id_counts=Counter(persisted_by_id.keys()),
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
        # Preserve explicitly submitted falsey values (e.g. "") so R03 can catch them.
        "baseline_yn": row["baseline_yn"]
        if "baseline_yn" in row
        else persisted.get("baseline_yn"),
        "del_yn": "N",
    }


def _sid(scenario: dict[str, Any]) -> str:
    return str(scenario.get("scenario_id", "?"))


def _scenario_label(scenario: dict[str, Any]) -> str:
    """사용자에게 보여줄 시나리오 이름(제목 우선, 없으면 ID)."""
    title = str(scenario.get("title") or "").strip()
    return title or f"시나리오 {_sid(scenario)}"


def _dim_label(ctx: ReviewContext, key: str) -> str:
    dimension = ctx.dim_index.get(key) or {}
    return str(dimension.get("label") or key)


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


def _top_probability_scenario(ctx: ReviewContext) -> dict[str, Any] | None:
    def score(scenario: dict[str, Any]) -> Decimal:
        try:
            return Decimal(str(scenario.get("probability_score")))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("-Infinity")

    if not ctx.scenarios:
        return None
    top = max(ctx.scenarios, key=score)
    return top if score(top) > Decimal("-Infinity") else None


def _check_tail_preserved(ctx: ReviewContext) -> CheckResult:
    used = _used_values(ctx)
    missing_pairs = [
        (key, ctx.tail_index[key])
        for key in ctx.selected_dims
        if ctx.tail_index.get(key)
        and ctx.tail_index[key] not in used.get(key, set())
    ]
    offenders = [f"{key} (tail='{tail}')" for key, tail in missing_pairs]
    advice: list[str] = []
    if missing_pairs:
        example = ", ".join(
            f"{_dim_label(ctx, key)}: {tail}" for key, tail in missing_pairs
        )
        top = _top_probability_scenario(ctx)
        opposite = (
            f"발생 가능성이 높은 시나리오 '{_scenario_label(top)}'와(과) 반대되는 "
            "시나리오를 추가해주세요. "
            if top is not None
            else ""
        )
        advice.append(
            "시나리오 다양성을 위해 발생 가능성이 낮은(극단적인) 시나리오를 "
            f"최소 1개 포함해야 합니다. {opposite}"
            f"예시 극단값 → {example}",
        )
    return CheckResult(
        "R01",
        "Stage3",
        "선택 Dim별 극단값(tail) 보존",
        "PASS" if not missing_pairs else "WARN",
        "모든 Dim에서 tail 등장"
        if not missing_pairs
        else f"tail 미등장 {len(missing_pairs)}건",
        offenders,
        advice,
    )


def _check_value_diversity(ctx: ReviewContext) -> CheckResult:
    used = _used_values(ctx)
    bad = [key for key, values in used.items() if len(values) < 2]
    advice: list[str] = []
    for key in bad:
        only = next(iter(used[key]), None)
        only_text = f"'{only}' 한 값만" if only is not None else "아무 값도"
        advice.append(
            f"'{_dim_label(ctx, key)}' 항목이 모든 시나리오에서 {only_text} "
            f"사용하고 있습니다. 서로 다른 값을 2가지 이상 사용해 다양성을 "
            f"확보하세요.",
        )
    return CheckResult(
        "R02",
        "Stage3",
        "각 선택 Dim 값 다양성 ≥2",
        "PASS" if not bad else "WARN",
        " / ".join(f"{key}={len(values)}값" for key, values in used.items())
        if not bad
        else f"단일값 Dim {len(bad)}건",
        bad,
        advice,
    )


def _compat_advice(item: CompatibilityItem, scenario_label: str | None) -> str:
    """모순 1건을 '동시에 가질 수 없습니다 + 권장 변경' 형태의 안내로 변환."""
    prefix = f"시나리오 '{scenario_label}': " if scenario_label else ""
    has_pair = bool(
        item.conflict_dim_a
        and item.conflict_value_a
        and item.conflict_dim_b
        and item.conflict_value_b
    )
    if not has_pair:
        # LLM이 충돌 항목을 구조화해 주지 못한 경우 서술형 reason 으로 폴백.
        return f"{prefix}값 조합이 서로 맞지 않습니다 — {item.reason}".rstrip(" —")
    body = (
        f"'{item.conflict_dim_a}'의 '{item.conflict_value_a}' 값과 "
        f"'{item.conflict_dim_b}'의 '{item.conflict_value_b}' 값은 "
        f"동시에 가질 수 없습니다."
    )
    if item.recommended_value_b:
        body += (
            f" '{item.conflict_value_b}'을(를) "
            f"'{item.recommended_value_b}'(으)로 바꾸는 것을 권장합니다."
        )
    return f"{prefix}{body}"


async def _check_compatibility(ctx: ReviewContext) -> CheckResult:
    if not ctx.scenarios:
        return CheckResult(
            "R03",
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
                "R03",
                "Stage4",
                "Compatibility(조합 모순) — LLM 판정",
                "WARN",
                "LLM 응답 scenario_id 집합 불일치: "
                f"누락={expected - actual}, 여분={actual - expected}",
            )
        title_by_id = {
            scenario["scenario_id"]: _scenario_label(scenario)
            for scenario in ctx.scenarios
        }
        incompatible = [item for item in items if not item.compatible]
        offenders = [f"{item.scenario_id}: {item.reason}" for item in incompatible]
        advice = [
            _compat_advice(item, title_by_id.get(item.scenario_id))
            for item in incompatible
        ]
        return CheckResult(
            "R03",
            "Stage4",
            "Compatibility(조합 모순) — LLM 판정",
            "PASS" if not incompatible else "WARN",
            f"{len(items)}건 판정 — 모순 없음"
            if not incompatible
            else f"모순 {len(incompatible)}건",
            offenders,
            advice,
        )
    except Exception as exc:
        return CheckResult(
            "R03",
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
    seen: dict[tuple[tuple[str, Any], ...], dict[str, Any]] = {}
    duplicates: list[str] = []
    advice: list[str] = []
    for scenario in ctx.scenarios:
        key = tuple(
            sorted(
                (dimension, _hashable(value))
                for dimension, value in scenario["dimension_values"].items()
            ),
        )
        original = seen.get(key)
        if original is not None:
            duplicates.append(f"{_sid(scenario)} = {_sid(original)}")
            dup_name = _scenario_label(scenario)
            origin_name = _scenario_label(original)
            advice.append(
                f"시나리오 '{origin_name}'와(과) 시나리오 '{dup_name}'가 중복됩니다. "
                f"시나리오 '{dup_name}'를 삭제하거나 다른 조합으로 변경해주세요.",
            )
        else:
            seen[key] = scenario
    return CheckResult(
        "R04",
        "Stage5",
        "MECE — 조합 유일(상호배타)",
        "PASS" if not duplicates else "WARN",
        "모든 조합 유일" if not duplicates else f"중복 조합 {len(duplicates)}쌍",
        duplicates,
        advice,
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
        "R05",
        "Stage5",
        "확률/증감 값 범위 (0~100 / ±100)",
        "PASS" if not bad else "WARN",
        "모든 확률값 범위 내" if not bad else f"범위 밖 {len(bad)}건",
        bad,
    )


CHECKS: list[Callable[[ReviewContext], CheckResult]] = [
    _check_tail_preserved,
    _check_value_diversity,
]

_STATUS_LABEL = {"FAIL": "실패", "WARN": "주의"}

# 현업 사용자에게 표출할 친화 문구. 내부 검사 코드(R01~)는 조회 키로만 쓰고
# 화면에는 노출하지 않는다. 모든 검사는 WARN(주의)로만 분류되며 검증을 막지 않는다.
#   - title       : 검사 항목을 가리키는 직관적 제목
#   - issue       : 문제 건수를 붙여 표시할 문제 설명 (예: "<issue> 2건")
#   - issue_empty : 건수가 없는 경우(자동 점검 실패 등) 단독 문장
#   - unit        : 건수 단위 (기본 "건")
#   - target_word : 문제 대상 목록 앞에 붙일 라벨 ("" 이면 대상 미표시)
#   - show_detail : 원본 detail 을 보조 설명으로 덧붙일지 여부
#   - suggestion  : 개선 제안 (advice 가 채워진 검사에서는 advice 가 우선)
#
# 적용 검사 (5개)
#   R01) 시나리오 다양성        : 발생 가능성이 낮은(극단) 시나리오 최소 1개 포함
#   R02) 값 다양성              : 각 항목에 서로 다른 값 2개 이상
#   R03) 값 조합 적합성         : 함께 가질 수 없는 값 조합(LLM 판정)
#   R04) 시나리오 조합 중복     : 두 시나리오의 값 조합이 모두 같음
#   R05) 확률·증감 값 범위      : 확률 0~100 / 증감 ±100
CHECK_DISPLAY: dict[str, dict[str, Any]] = {
    "R01": {
        "title": "시나리오 다양성",
        "issue": "극단(저확률) 값이 빠진 항목",
        "target_word": "해당 항목",
        "suggestion": "발생 가능성이 낮은(극단) 시나리오를 최소 1개 포함해 다양성을 "
        "확보하세요.",
    },
    "R02": {
        "title": "값 다양성",
        "issue": "값이 한 종류뿐인 항목",
        "target_word": "해당 항목",
        "suggestion": "각 항목에 서로 다른 값을 두 가지 이상 사용해 다양성을 확보하세요.",
    },
    "R03": {
        "title": "값 조합 적합성",
        "issue": "값 조합이 서로 맞지 않는 시나리오",
        "issue_empty": "값 조합 자동 점검을 완료하지 못했습니다 (재시도 필요)",
        "target_word": "해당 시나리오",
        "suggestion": "맞지 않는 값 조합을 다시 검토하거나, 시나리오 설명으로 조합 의도를 "
        "보완하세요.",
    },
    "R04": {
        "title": "시나리오 조합 중복",
        "issue": "다른 시나리오와 조합이 겹치는 경우",
        "unit": "쌍",
        "target_word": "해당 시나리오",
        "suggestion": "겹치는 시나리오 조합을 서로 다르게 조정하세요.",
    },
    "R05": {
        "title": "확률·증감 값 범위",
        "issue": "허용 범위를 벗어난 값",
        "target_word": "해당 값",
        "suggestion": "확률·증감 값을 허용 범위(확률 0~100, 증감 -100~100) 안으로 수정하세요.",
    },
}

# 대상 문자열에 남는 내부 표기를 사람이 읽기 쉬운 표현으로 치환한다.
_TARGET_TOKEN_REPLACEMENTS = (
    ("tail='", "극단값 '"),
)


def _dim_label_map(ctx: ReviewContext) -> dict[str, str]:
    """Dimension 키(supply_disruption_pattern 등) → 사람이 읽는 라벨 매핑."""
    return {
        key: str(dimension.get("label") or key)
        for key, dimension in ctx.dim_index.items()
    }


def _humanize_target(text: str, label_map: dict[str, str]) -> str:
    for key, label in label_map.items():
        if key != label:
            text = re.sub(rf"\b{re.escape(key)}\b", label, text)
    for token, replacement in _TARGET_TOKEN_REPLACEMENTS:
        text = text.replace(token, replacement)
    return text


def _humanize_targets(
    offenders: list[str],
    label_map: dict[str, str],
    limit: int = 3,
) -> str:
    if not offenders:
        return ""
    cleaned = [_humanize_target(item, label_map) for item in offenders]
    shown = ", ".join(cleaned[:limit])
    extra = len(cleaned) - limit
    return f"{shown} 외 {extra}건" if extra > 0 else shown


def _render_check(check: CheckResult, label_map: dict[str, str]) -> list[str]:
    display = CHECK_DISPLAY.get(check.check_id, {})
    title = display.get("title") or check.name
    label = _STATUS_LABEL.get(check.status, check.status)
    count = len(check.offenders) or len(check.advice)
    lines: list[str] = []
    if count:
        issue = display.get("issue") or check.detail
        unit = display.get("unit", "건")
        lines.append(f"• [{label}] {title} — {issue} {count}{unit}")
    else:
        issue = display.get("issue_empty") or display.get("issue") or check.detail
        if display.get("show_detail"):
            issue = f"{issue} ({check.detail})"
        lines.append(f"• [{label}] {title} — {issue}")
    if check.advice:
        # advice 는 시나리오명·값·권장 변경까지 담은 완성형 안내라 그대로 노출한다.
        lines.extend(f"  └ {item}" for item in check.advice[:3])
        extra = len(check.advice) - 3
        if extra > 0:
            lines.append(f"  └ 외 {extra}건")
        return lines
    target_word = display.get("target_word", "해당 항목")
    targets = _humanize_targets(check.offenders, label_map)
    if target_word and targets:
        lines.append(f"  └ {target_word}: {targets}")
    suggestion = display.get("suggestion")
    if suggestion:
        lines.append(f"  └ {suggestion}")
    return lines


def _build_reason(notable: list[CheckResult], label_map: dict[str, str]) -> str:
    counts = Counter(check.status for check in notable)
    lines = [f"검토 결과 — 주의 {counts.get('WARN', 0)}건"]
    for check in notable:
        lines.extend(_render_check(check, label_map))
    return "\n".join(lines)


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
                    "WARN",
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
                    "WARN",
                    f"검사 예외: {type(exc).__name__}: {exc}",
                ),
            )
    counts = Counter(check.status for check in checks)
    summary = {
        status: counts.get(status, 0) for status in ("PASS", "WARN", "FAIL", "INFO")
    }
    # 모든 검사는 WARN(주의)로만 분류되므로 검증을 막지 않는다(BLOCK 없음).
    verdict: Literal["PASS", "REVIEW", "BLOCK"] = (
        "REVIEW" if summary["WARN"] else "PASS"
    )
    notable = [check for check in checks if check.status == "WARN"]
    reason = (
        _build_reason(notable, _dim_label_map(ctx))
        if notable
        else "모든 시나리오 검토 항목을 통과했습니다."
    )
    return ReviewReport(
        verdict=verdict,
        is_valid=verdict == "PASS",
        reason=reason,
        summary=summary,
        checks=checks,
    )

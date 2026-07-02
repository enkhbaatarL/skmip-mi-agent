from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
import re
from typing import TYPE_CHECKING, Any, Literal, Protocol

from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    COMPAT_SYSTEM_PROMPT,
    CompatibilityItem,
    CompatibilityStructuredOutput,
    DimensionValueStructuredOutput,
    GeneratedDimensionCell as _GeneratedDimensionCell,
    build_dimension_value_messages,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.schema import (
    CheckResult,
    ReviewContext,
    ReviewReport,
)
from apps.persistence.scenario.baseline_contrast import (
    apply_single_baseline_by_probability,
    check_baseline_contrast_coverage,
)


if TYPE_CHECKING:
    from apps.persistence.scenario.schema import (
        ScenarioTemplate,
        ScenarioTemplateDimension,
    )


CompatibilityOutput = CompatibilityStructuredOutput
DimensionValueGenerationOutput = DimensionValueStructuredOutput
GeneratedDimensionCell = _GeneratedDimensionCell


class CompatibilityInvocationResult(Protocol):
    result: CompatibilityStructuredOutput


def build_context(
    group: dict[str, Any],
    requested_rows: list[dict[str, Any]],
    persisted_scenarios: list[dict[str, Any]],
    template_dims: list[dict[str, Any]],
    requested_headers: list[dict[str, Any]] | None = None,
) -> ReviewContext:
    persisted_by_id = {
        int(scenario["scenario_id"]): scenario for scenario in persisted_scenarios
    }
    scenarios = [
        _normalize_scenario(
            row,
            persisted_by_id.get(int(row["scenario_id"]))
            if row.get("scenario_id") is not None
            else None,
            index,
        )
        for index, row in enumerate(requested_rows)
    ]
    dim_index = {
        _template_dim_key(dimension): dimension
        for dimension in template_dims
        if isinstance(dimension, dict) and _template_dim_key(dimension)
    }
    enum_index = {
        key: _template_enum_labels(dimension)
        for key, dimension in dim_index.items()
    }
    selected_dims = _selected_dims_from_headers(requested_headers)
    if selected_dims is None:
        selected_dims = [str(key) for key in group.get("dimension_selected") or []]
    apply_single_baseline_by_probability(scenarios)
    return ReviewContext(
        group=group,
        scenarios=scenarios,
        template_dims=template_dims,
        selected_dims=selected_dims,
        dim_index=dim_index,
        enum_index=enum_index,
        unchanged=_is_request_unchanged(requested_rows, persisted_scenarios),
    )


def _template_dim_key(dimension: dict[str, Any]) -> str:
    return str(dimension.get("dim_key") or dimension.get("dimension_id") or "").strip()


def _template_enum_labels(dimension: dict[str, Any]) -> list[str]:
    if "value_enums" in dimension:
        return [str(value) for value in dimension.get("value_enums", [])]
    return [
        str(item.get("label") or item.get("id") or "")
        for item in dimension.get("enum", [])
        if isinstance(item, dict) and str(item.get("label") or item.get("id") or "").strip()
    ]


def _template_dim_label(dimension: dict[str, Any], fallback: str) -> str:
    return str(dimension.get("label") or dimension.get("label_ko") or fallback)


def _selected_dims_from_headers(
    requested_headers: list[dict[str, Any]] | None,
) -> list[str] | None:
    if requested_headers is None:
        return None
    return [
        str(header["key"])
        for header in requested_headers
        if isinstance(header, dict) and header.get("key")
    ]


def _norm_compare_value(value: Any) -> Any:
    """request/DB 값을 비교 가능한 형태로 정규화한다.

    - 숫자(int/float)는 Decimal 로 변환해 40 == 40.0 == Decimal('40.00') 을 동등 처리.
    - 문자열은 공백 제거 후 빈 문자열을 None 으로 취급(None == '' == '  ').
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return value
    if isinstance(value, str):
        return value.strip() or None
    return value


def _norm_cells(cells: Any) -> dict[str, Any]:
    if not isinstance(cells, dict):
        return {}
    return {
        str(key): _norm_compare_value(value)
        for key, value in cells.items()
        if str(key).strip() and value is not None
    }


def _is_request_unchanged(
    requested_rows: list[dict[str, Any]],
    persisted_scenarios: list[dict[str, Any]],
) -> bool:
    """validate 요청 본문이 DB(create scenario 결과)와 정확히 일치하는지 판정.

    사용자가 아무것도 수정하지 않은 경우(요청 == DB) True 를 반환한다. 이때는
    검토를 수행하면 사용자가 손대지 않은 항목에까지 불필요한 warning 이 떠서,
    review 를 건너뛰고 통과 처리하기 위한 신호로 쓴다.

    신규 시나리오 추가/삭제, 시나리오 식별자 불일치, validation 요청 body가
    받는 필드(title·dimension_values) 중 하나라도 다르면 False.
    """
    if not requested_rows or not persisted_scenarios:
        return False
    if len(requested_rows) != len(persisted_scenarios):
        return False
    persisted_by_id = {
        int(scenario["scenario_id"]): scenario
        for scenario in persisted_scenarios
        if scenario.get("scenario_id") is not None
    }
    for row in requested_rows:
        raw_id = row.get("scenario_id")
        if raw_id is None:
            # 신규 시나리오는 DB 에 없으므로 변경으로 간주.
            return False
        persisted = persisted_by_id.get(int(raw_id))
        if persisted is None:
            return False
        comparisons: list[tuple[Any, Any]] = [
            (row.get("title"), persisted.get("title")),
        ]
        if any(
            _norm_compare_value(requested) != _norm_compare_value(stored)
            for requested, stored in comparisons
        ):
            return False
        if _norm_cells(row.get("cells")) != _norm_cells(
            persisted.get("dimension_values"),
        ):
            return False
    return True


def _normalize_scenario(
    row: dict[str, Any],
    persisted: dict[str, Any] | None,
    index: int,
) -> dict[str, Any]:
    persisted = persisted or {}
    metrics = row.get("metrics") or {}
    raw_id = row.get("scenario_id")
    is_new = raw_id is None
    display_order = int(row.get("display_order") or (index + 1))
    # 신규 시나리오는 아직 DB ID가 없으므로 displayOrder 기반 음수 임시 ID를
    # 부여해 기존 review 흐름(조합 판정·중복 검사 등)을 그대로 유지한다.
    scenario_id = -display_order if is_new else int(raw_id)
    return {
        "scenario_id": scenario_id,
        "is_new": is_new,
        "display_order": display_order,
        "title": row.get("title") or persisted.get("title") or "",
        "narrative": row.get("narrative") or persisted.get("narrative") or "",
        "dimension_values": row.get("cells") or {},
        "probability_score": metrics.get(
            "probability_score", persisted.get("probability_score"),
        ),
        "probability_delta": metrics.get(
            "probability_delta", persisted.get("probability_delta"),
        ),
        "baseline_yn": row.get("baseline_yn") or persisted.get("baseline_yn"),
    }


def _sid(scenario: dict[str, Any]) -> str:
    """대상 표기에 쓰는 시나리오 식별자.

    신규(아직 ID 미발급) 시나리오는 음수 임시 ID 대신 displayOrder 기반
    '{n}번째 시나리오' 표기를 사용해 사용자 친화적으로 노출한다.
    """
    if scenario.get("is_new"):
        return f"{scenario.get('display_order')}번째 시나리오"
    return str(scenario.get("scenario_id", "?"))


def _scenario_label(scenario: dict[str, Any]) -> str:
    """사용자에게 보여줄 시나리오 이름(제목 우선, 없으면 순번/ID)."""
    title = str(scenario.get("title") or "").strip()
    if title:
        return title
    if scenario.get("is_new"):
        return f"{scenario.get('display_order')}번째 시나리오"
    return f"시나리오 {_sid(scenario)}"


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


def _baseline_scenarios(ctx: ReviewContext) -> list[dict[str, Any]]:
    return [scenario for scenario in ctx.scenarios if scenario.get("baseline_yn") == "Y"]


def _check_baseline_contrast_covered(ctx: ReviewContext) -> CheckResult:
    baselines = _baseline_scenarios(ctx)
    if len(baselines) != 1:
        detail = f"baseline scenario {len(baselines)}건"
        advice = [
            "baseline scenario는 발생 가능성이 가장 높은 1개만 선택되어야 합니다. "
            "확률값을 확인해 baseline을 1개로 정리해주세요.",
        ]
        return CheckResult(
            "R01",
            "Stage3",
            "Baseline 대비 대안값 coverage",
            "WARN",
            detail,
            ["baseline_yn"],
            advice,
        )

    baseline_index = ctx.scenarios.index(baselines[0])
    coverage = check_baseline_contrast_coverage(
        ctx.scenarios,
        ctx.selected_dims,
        baseline_index=baseline_index,
    )
    missing_pairs = [
        (key, coverage.baseline_values.get(key))
        for key in coverage.missing_dimensions
    ]
    offenders = [
        f"{key} (baseline='{baseline_value}')"
        for key, baseline_value in missing_pairs
    ]
    advice: list[str] = []
    if missing_pairs:
        example = ", ".join(
            f"{_dim_label(ctx, key)}: baseline '{baseline_value}'와 다른 값"
            for key, baseline_value in missing_pairs
        )
        advice.append(
            f"baseline 시나리오 '{_scenario_label(baselines[0])}'와(과) 다른 방향의 "
            "대안 값을 전체 시나리오 묶음에 포함해야 합니다. "
            f"누락된 대안값 기준 → {example}",
        )
    return CheckResult(
        "R01",
        "Stage3",
        "Baseline 대비 대안값 coverage",
        "PASS" if not missing_pairs else "WARN",
        "모든 선택 Dim에서 baseline 대비 대안값 등장"
        if not missing_pairs
        else f"baseline 대비 대안값 누락 {len(missing_pairs)}건",
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


def _compatibility_enum_lines(ctx: ReviewContext) -> list[str]:
    """LLM compatibility judge가 참조할 수 있도록 선택 Dimension의 enum 목록을 프롬프트 행으로 만든다."""
    lines: list[str] = []
    for key in ctx.selected_dims:
        enum_values = ctx.enum_index.get(key) or []
        if not enum_values:
            continue
        lines.append(f"- {_dim_label(ctx, key)} ({key}): {', '.join(enum_values)}")
    return lines


def _resolve_compat_dim_key(ctx: ReviewContext, raw_dim: str | None) -> str | None:
    """LLM이 반환한 Dimension 표기를 내부 dim_key로 해석한다.LLM이 반환한 conflict_dim_b가 라벨, key, 또는 "기간 (period)" 같은 혼합 표기일 수 있어서 내부 dim_key로 매핑합니다."""
    if not raw_dim:
        return None
    text = str(raw_dim).strip()
    if text in ctx.dim_index:
        return text
    label_by_key = {key: _dim_label(ctx, key) for key in ctx.dim_index}
    for key, label in label_by_key.items():
        if text == label or key in text or label in text:
            return key
    return None


def _has_only_unusable_enum_recommendations(
    ctx: ReviewContext,
    incompatible: list[CompatibilityItem],
) -> bool:
    """모든 모순 판정이 enum 안에서 실행 가능한 권장 변경 없이 나온 경우인지 확인한다. 모순 판정이 있더라도 모든 권장 변경값이 해당 Dimension enum 밖이라 실제 수정 가능한 대안이 없는 경우인지 확인합니다. 이때만 review R03을 pass 처리합
    니다."""
    if not incompatible:
        return False
    scenario_by_id = {
        int(scenario["scenario_id"]): scenario
        for scenario in ctx.scenarios
    }
    for item in incompatible:
        if item.recommended_value_b is None:
            return False
        scenario = scenario_by_id.get(item.scenario_id)
        if scenario is None:
            return False
        dim_key = _resolve_compat_dim_key(ctx, item.conflict_dim_b)
        if dim_key is None:
            return False
        current_value = scenario["dimension_values"].get(dim_key)
        if current_value is None or str(current_value) != str(item.conflict_value_b):
            return False
        if str(item.recommended_value_b) in set(ctx.enum_index.get(dim_key) or []):
            return False
    return True


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
            f"{_template_dim_label(ctx.dim_index.get(key, {}), key)}='{value}'"
            for key, value in scenario["dimension_values"].items()
        )
        lines.append(
            f"- {scenario['scenario_id']} [{scenario['title']}]: {pairs}\n"
            f"  narrative: {scenario['narrative']}",
        )
    enum_lines = _compatibility_enum_lines(ctx)
    user_prompt = "다음 시나리오 조합을 판정하십시오.\n\n"
    if enum_lines:
        user_prompt += "## Dimension enum\n" + "\n".join(enum_lines) + "\n\n"
    user_prompt += "## Scenarios\n" + "\n".join(lines)
    messages = [
        {"role": "system", "content": COMPAT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
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
        if _has_only_unusable_enum_recommendations(ctx, incompatible):
            return CheckResult(
                "R03",
                "Stage4",
                "Compatibility(조합 모순) — LLM 판정",
                "PASS",
                f"{len(items)}건 판정 — enum 안 실행 가능한 권장 변경 없음",
            )
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
        CompatibilityStructuredOutput,
        messages=messages,
    )


class DimensionValueInvocationResult(Protocol):
    result: DimensionValueStructuredOutput


async def _invoke_dimension_values(
    *,
    messages: list[dict[str, str]],
) -> DimensionValueInvocationResult:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    return await invoke_llm_structured_output(
        DimensionValueStructuredOutput,
        messages=messages,
    )


def _enum_labels(dimension: "ScenarioTemplateDimension") -> list[str]:
    return [enum.label for enum in dimension.enum]


async def generate_new_dimension_values(
    template: "ScenarioTemplate",
    rows: list[dict[str, Any]],
    new_dimensions: list[str],
) -> dict[int, dict[str, str]]:
    """새로 추가된 Dimension 의 null 값을 LLM 으로 생성한다.

    반환: {scenario_index: {dim_key: value}}. value 는 항상 해당 Dimension 의
    enum label 중 하나로 보정된다(LLM 이 범위 밖 값을 반환하면 결정론적 폴백).
    """
    if not rows or not new_dimensions:
        return {}
    dim_by_key = {
        dimension.dimension_id: dimension for dimension in template.dimensions
    }
    target_dimensions = [
        dim_by_key[key] for key in new_dimensions if key in dim_by_key
    ]
    if not target_dimensions:
        return {}
    enum_by_key = {
        dimension.dimension_id: _enum_labels(dimension)
        for dimension in target_dimensions
    }

    generated: dict[int, dict[str, str]] = {}
    try:
        result = await _invoke_dimension_values(
            messages=build_dimension_value_messages(dimensions=target_dimensions, rows=rows),
        )
        for item in result.result.items:
            if item.dim_key not in enum_by_key:
                continue
            if not 0 <= item.scenario_index < len(rows):
                continue
            allowed = enum_by_key[item.dim_key]
            value = item.value if item.value in allowed else None
            if value is None:
                continue
            generated.setdefault(item.scenario_index, {})[item.dim_key] = value
    except Exception:
        generated = {}

    # 누락된 (scenario_index, dim_key) 는 결정론적 폴백(첫 enum)으로 채운다.
    for index in range(len(rows)):
        for dimension in target_dimensions:
            labels = enum_by_key[dimension.dimension_id]
            if not labels:
                continue
            row_values = generated.setdefault(index, {})
            row_values.setdefault(dimension.dimension_id, labels[0])
    return generated


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
    _check_baseline_contrast_covered,
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
#   R01) 시나리오 다양성        : baseline 대비 대안값을 각 선택 항목에 최소 1개 포함
#   R02) 값 다양성              : 각 항목에 서로 다른 값 2개 이상
#   R03) 값 조합 적합성         : 함께 가질 수 없는 값 조합(LLM 판정)
#   R04) 시나리오 조합 중복     : 두 시나리오의 값 조합이 모두 같음
#   R05) 확률·증감 값 범위      : 확률 0~100 / 증감 ±100
CHECK_DISPLAY: dict[str, dict[str, Any]] = {
    "R01": {
        "title": "시나리오 다양성",
        "issue": "baseline 대비 대안값이 빠진 항목",
        "target_word": "해당 항목",
        "suggestion": "baseline 시나리오와 다른 값을 각 항목에 최소 1개 포함해 "
        "다양성을 확보하세요.",
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
    ("baseline='", "baseline 값 '"),
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
    if ctx.unchanged:
        # 요청 본문이 DB(create scenario 결과)와 동일 → 사용자가 수정한 것이
        # 없으므로 불필요한 warning 없이 그대로 통과 처리한다.
        return ReviewReport(
            verdict="PASS",
            is_valid=True,
            reason="모든 검사 항목을 통과했습니다.",
            summary={"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0},
            checks=[],
        )
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
    # R05(확률/증감 값 범위) 검토 비활성화(always):
    # 서비스 사용자가 시나리오 추가 시 probability 가 null 등으로 들어올 수 있어
    # 0~100 범위 검토가 무의미하므로 항상 비활성화한다.
    for check in (_check_mece,):  # _check_probability_range 비활성화
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

# ==============================================
# LangGraph Node Classes
# ==============================================

from abc import ABC, abstractmethod
from typing import Any

from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import (
    ScenarioReviewState,
)


class BaseNode(ABC):
    """Stateless LangGraph node."""

    async def __call__(self, state: ScenarioReviewState) -> dict[str, Any]:
        return await self.run(state)

    @abstractmethod
    async def run(self, state: ScenarioReviewState) -> dict[str, Any]:
        ...


class RunReviewNode(BaseNode):
    async def run(self, state: ScenarioReviewState) -> dict[str, Any]:
        if state.skip_review or state.error:
            return {}
        context = self._build_context(state)
        return {"report": await self._run_review(context)}

    def _build_context(self, state: ScenarioReviewState) -> ReviewContext:
        return build_context(
            group=state.group,
            requested_rows=state.requested_rows,
            persisted_scenarios=state.persisted_scenarios,
            template_dims=state.template_dims,
            requested_headers=state.requested_headers,
        )

    async def _run_review(self, context: ReviewContext) -> ReviewReport:
        return await run_review(context)


async def run_review_node(state: ScenarioReviewState) -> dict[str, Any]:
    return await RunReviewNode()(state)

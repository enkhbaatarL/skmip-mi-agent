from __future__ import annotations

# ruff: noqa: CPY001
import json
from pathlib import Path
from typing import Any

from tests.manual.multi_event_comparison.models import ComparisonJudgment, QualityCheck


_DETERMINISTIC_CHECK_GUIDANCE: dict[str, tuple[str, str, str, str]] = {
    "M-01": (
        "Scenario 개수 범위",
        "생성된 Scenario가 비교에 필요한 3~5개 범위인지 검사합니다.",
        "Scenario spectrum이 지나치게 좁거나 불필요하게 많아져 버전 간 비교와 운영 활용성이 낮아집니다.",
        "table.rows를 3~5개로 조정하고 서로 다른 가격 압력 경로를 유지합니다.",
    ),
    "M-02": (
        "단일 baseline 지정",
        "가장 개연성 높은 기준 Scenario가 baselineYn=Y로 정확히 하나 지정됐는지 검사합니다.",
        "기준 경로가 없거나 여러 개이면 대안 Scenario와의 비교 기준이 모호해집니다.",
        "현재 Event 사실에 가장 가까운 Scenario 하나만 baselineYn=Y로 지정합니다.",
    ),
    "M-03": (
        "Scenario 조합·pressure band 고유성",
        "모든 Scenario에 cells와 pressure band가 있고, Scenario별 조합과 band가 중복되지 않는지 검사합니다.",
        "동일한 경로가 중복되거나 가격 압력 위치를 알 수 없어 Scenario spectrum의 변별력이 떨어집니다.",
        "누락된 cells/band를 채우고 중복 Scenario는 cell 조합 또는 pressure band가 구분되도록 수정합니다.",
    ),
    "M-04": (
        "scenario role과 가격 극단 정합성",
        "floor·ceiling이 각각 하나이고, 선택적인 mixed role이 비극단 pressure band에 있는지 검사합니다.",
        "상·하단 또는 표시된 혼합 경로의 의미가 뒤바뀌어 가격 시나리오 해석이 잘못될 수 있습니다.",
        (
            "최저 band에는 floor, 최고 band에는 ceiling을 지정하고 실제 상쇄 조합이 있을 때만 "
            "mixed를 비극단 band에 배치합니다."
        ),
    ),
    "M-05": (
        "Dimension 개수 범위",
        "해당 API version의 Dimension 수가 운영 기대 범위인 3~6개인지 검사합니다.",
        "핵심 driver가 빠지거나 Dimension이 과도하게 세분되어 Scenario 조합을 이해하기 어려워집니다.",
        "핵심 LNG 가격 driver를 유지하면서 dimensionDefinitions를 3~6개로 조정합니다.",
    ),
    "M-06": (
        "전체 Event의 Dimension lineage 포함 여부",
        "선택된 모든 Event가 적어도 하나의 Dimension 또는 Value source에 연결됐는지 검사합니다.",
        (
            "누락 Event의 핵심 driver가 Scenario cell 조합을 실제로 구분하지 못해 "
            "multi-event 시나리오가 입력 전체를 대표하지 못합니다."
        ),
        (
            "누락 Event의 핵심 가격 driver를 반영한 Dimension을 추가하거나 기존 Dimension의 "
            "eventGroundings 또는 sourceEventIds/sourceRefs/sourceAssignments에 근거와 함께 연결합니다."
        ),
    ),
    "M-07": (
        "Scenario별 글로벌 가격 판단 근거",
        "모든 Scenario에 globalPressureRationale이 비어 있지 않은지 검사합니다.",
        "cells 조합이 해당 pressure band로 이어지는 인과관계를 사용자가 확인할 수 없습니다.",
        "각 Scenario에 선택된 driver 조합이 글로벌 LNG 가격 압력으로 이어지는 근거를 작성합니다.",
    ),
    "M-08": (
        "5개 pressure band 설명 범위",
        "5개 목표 band가 생성됐거나 제외·미표현 사유로 모두 설명되는지 검사합니다.",
        "Scenario spectrum의 빈 구간이 이유 없이 남아 상·하방 범위를 완전하게 비교할 수 없습니다.",
        "누락 band의 Scenario를 생성하거나 generationDiagnostics에 제외 또는 미표현 사유를 명시합니다.",
    ),
}


def render_report(  # noqa: C901
    manifest: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    checks: dict[str, list[QualityCheck]],
    judge: ComparisonJudgment | None,
    *,
    quality_check: bool,
    judge_error: str | None = None,
) -> str:
    lines = [
        f"# Multi-Event Scenario API Comparison — {manifest['batchId']}",
        "",
        "## 실행 조건",
        "",
        f"- comparisonRunId: `{manifest['comparisonRunId']}`",
        f"- Agent: `{manifest['baseUrl']}`",
        f"- userId: `{manifest['userId']}`",
        f"- Event 선택: {manifest['selection']['description']}",
        f"- 품질검사: **{'실행' if quality_check else '미실행'}**",
        f"- 실행 방식: **{_execution_mode(manifest)}**",
        "",
        "### 선택 이벤트",
        "",
        "| miEventId | 제목 | 요약/발생시각 |",
        "| --- | --- | --- |",
    ]
    for detail in manifest["events"]:
        event = detail.get("event") if isinstance(detail.get("event"), dict) else detail
        summary = _field(event, "oneLineSummary", "one_line_summary") or _field(
            event,
            "occurredAt",
            "occurred_at",
        )
        lines.append(
            f"| {_field(event, 'miEventId', 'mi_event_id')} | {_cell(event.get('title'))} | {_cell(summary)} |",
        )
    lines.extend(
        [
            "",
            "## API 실행 결과",
            "",
            "| Version | 성공 | HTTP | Scenario Group | 시간(ms) | Tokens |",
            "| --- | --- | --- | --- | --- | --- |",
        ],
    )
    successful: dict[str, dict[str, Any]] = {}
    for version in ("v2", "v3", "v4"):
        artifact = artifacts.get(version, {})
        response = artifact.get("response") if isinstance(artifact.get("response"), dict) else {}
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        success = (
            artifact.get("transportStatus") == "success"
            and artifact.get("outcome", "success") == "success"
            and response.get("status") == "success"
            and bool(data)
        )
        if success:
            successful[version] = data
        group = data.get("scenarioGroup") if isinstance(data.get("scenarioGroup"), dict) else {}
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        lines.append(
            f"| {version} | {'Y' if success else 'N'} | {artifact.get('httpStatus', '-')} | "
            f"{_field(group, 'scenarioGroupId', 'scenario_group_id') or '-'} | "
            f"{artifact.get('elapsedMs', '-')} | {usage.get('totalTokens', usage.get('total_tokens', '-'))} |",
        )
        if not success:
            reason = artifact.get("error") or response.get("message") or "응답 없음"
            label = "결과 불명" if artifact.get("outcome") == "unknown" else "실패"
            lines.append(f"\n- **{version} {label}:** {_cell(reason)}")

    lines.extend(["", "## Scenario Group 및 Dimension 비교", ""])
    for version, data in successful.items():
        group = data.get("scenarioGroup") if isinstance(data.get("scenarioGroup"), dict) else {}
        diagnostics = data.get("generationDiagnostics")
        dimensions = _dimensions(data)
        lines.extend(
            [
                f"### {version}",
                "",
                f"- 전략: `{data.get('generationStrategy')}`",
                f"- Dimension 수: {len(dimensions)}",
                "",
                "#### Scenario Group 설명",
                "",
                f"- 제목: **{_cell(_field(group, 'title'))}**",
                f"- 요약: {_cell(_field(group, 'summary'))}",
                f"- 설명: {_cell(_field(group, 'description'))}",
                "",
                "| Dimension | 설명 | Event lineage | Values |",
                "| --- | --- | --- | --- |",
            ],
        )
        for dimension in dimensions:
            sources = _dimension_event_ids(dimension)
            values = [
                _cell(value.get("label") or "레이블 없음")
                for value in dimension.get("values", [])
                if isinstance(value, dict)
            ]
            lines.append(
                f"| {_cell(dimension.get('label') or '레이블 없음')} | "
                f"{_cell(dimension.get('description'))} | {_cell(', '.join(map(str, sources)) or '-')} | "
                f"{_cell('; '.join(values))} |",
            )
        lines.extend(_scenario_dimension_sections(data, dimensions))
        lines.extend(
            [
                "",
                "#### generationDiagnostics 실제 값",
                "",
                "```json",
                json.dumps(diagnostics, ensure_ascii=False, indent=2, default=str),
                "```",
                "",
            ],
        )

    lines.extend(["", "## Scenario 실제 값 비교", ""])
    bands = _all_bands(successful)
    for band in bands:
        lines.extend(
            [
                f"### `{band}`",
                "",
                "| Version | Scenario | Role / Baseline / Probability | Cells | API 가격 판단 근거 |",
                "| --- | --- | --- | --- | --- |",
            ],
        )
        related_market_details: list[str] = []
        for version, data in successful.items():
            row = _row_for_band(data, band)
            if row is None:
                lines.append(f"| {version} | - | - | - | 해당 band 없음 |")
                continue
            lines.append(
                f"| {version} | **{_cell(row.get('title'))}** — {_cell(row.get('narrative'))} | "
                f"{_field(row, 'scenarioRole', 'scenario_role')} / "
                f"{_field(row, 'baselineYn', 'baseline_yn')} / "
                f"{_field(row, 'probabilityScore', 'probability_score')} | "
                f"{_cell(_scenario_cell_summary(data, row))} | "
                f"{_cell(_field(row, 'globalPressureRationale', 'global_pressure_rationale'))} |",
            )
            related_markets = _field(row, "relatedMarkets", "related_markets")
            for item in related_markets if isinstance(related_markets, list) else []:
                if isinstance(item, dict) and item.get("market") and item.get("rationale"):
                    related_market_details.append(  # noqa: PERF401
                        f"- **{version} · {item['market']}**: {_cell(item['rationale'])}",
                    )
        # Always leave a blank line after the table so CommonMark/GFM viewers
        # do not absorb the next heading into the table.
        lines.append("")
        if related_market_details:
            lines.extend(
                [
                    "#### 관련 시장 보조정보",
                    "",
                    *related_market_details,
                    "",
                ],
            )

    if quality_check:
        lines.extend(["", "## 결정적 품질검사", "", "| Version | Check | 결과 | 상세 |", "| --- | --- | --- | --- |"])
        for version, version_checks in checks.items():
            for check in version_checks:
                detail = check.detail
                if check.offenders:
                    detail += f" offenders={check.offenders}"
                lines.append(f"| {version} | {check.check_id} | {check.status} | {_cell(detail)} |")
        lines.extend(_deterministic_failure_section(checks))
        lines.extend(_judge_section(judge, judge_error))
    else:
        lines.extend(
            [
                "",
                "## 품질 비교",
                "",
                "- 사용자가 품질검사를 제외하여 결정적 검사, Agent Judge 점수, 버전 순위는 생성하지 않았습니다.",
            ],
        )
    lines.extend(
        [
            "",
            "## 해석상 주의",
            "",
            "- 모든 버전의 pressure band는 글로벌 LNG 가격 압력을 기준으로 비교합니다.",
            "- v4 relatedMarkets는 방향·강도 태그가 아닌 Scenario별 보조 관련성 정보입니다.",
            "- 이 보고서의 Agent Judge 평가는 제공된 Event/API 증적만 사용하며 외부 사실의 진위를 검증하지 않습니다.",
        ],
    )
    return "\n".join(lines) + "\n"


def _deterministic_failure_section(checks: dict[str, list[QualityCheck]]) -> list[str]:
    failures = [
        (version, check)
        for version, version_checks in checks.items()
        for check in version_checks
        if check.status == "FAIL"
    ]
    if not failures:
        return []

    lines = ["", "### FAIL 항목 상세 설명", ""]
    for version, check in failures:
        title, purpose, impact, fix = _DETERMINISTIC_CHECK_GUIDANCE.get(
            check.check_id,
            (
                "정의되지 않은 결정적 검사",
                "검사 정의를 확인해야 합니다.",
                "품질 영향을 확인해야 합니다.",
                "검사 구현을 확인합니다.",
            ),
        )
        lines.extend(
            [
                f"#### {version} · {check.check_id} — {title}",
                "",
                f"- **검사 목적:** {purpose}",
                f"- **확인된 문제:** {_deterministic_failure_observation(check)}",
                f"- **영향:** {impact}",
                f"- **수정 방향:** {fix}",
                "",
            ],
        )
    return lines


def _deterministic_failure_observation(check: QualityCheck) -> str:
    if check.check_id == "M-06" and check.offenders:
        missing = ", ".join(f"Event `{event_id}`" for event_id in check.offenders)
        return (
            f"선택 Event 중 {missing}이 어떤 Dimension lineage에도 포함되지 않았습니다. "
            "즉 이 Event의 핵심 driver가 생성된 Dimension/Value 조합에 직접 반영되지 않았습니다."
        )
    offenders = f" 문제 대상: {', '.join(check.offenders)}." if check.offenders else ""
    return f"{check.detail}{offenders}"


def _judge_section(judge: ComparisonJudgment | None, judge_error: str | None) -> list[str]:
    lines = ["", "## Agent Judge 품질 평가", ""]
    if judge is None:
        reason = f" Agent Judge 오류: `{_cell(judge_error)}`" if judge_error else ""
        return [
            *lines,
            (f"- 성공 버전이 2개 미만이거나 Judge가 실행되지 않아 비교 결론은 **판정 불가**입니다.{reason}"),
        ]
    lines.extend(
        [
            "### 절대 적합성 점수",
            "",
            (
                "이 점수는 각 버전이 품질 조건을 얼마나 충족하는지 보여주며, "
                "상대평가의 최종 승자를 자동 결정하지 않습니다."
            ),
            "",
            "| Version | 기준 | 점수 | 결과 | Agent Judge 근거 |",
            "| --- | --- | --- | --- | --- |",
        ],
    )
    for version in judge.versions:
        for criterion in version.criteria:
            lines.append(  # noqa: PERF401
                f"| {version.api_version} | {criterion.criterion} | {criterion.score}/5 | "
                f"{criterion.verdict} | {_cell(criterion.rationale)} "
                f"(evidence: {_cell('; '.join(criterion.evidence))}) |",
            )
    lines.extend(
        [
            "",
            f"- **절대 점수 최고 버전:** {', '.join(judge.best_versions)}",
            "",
            "### 버전별 잘한 점과 아쉬운 점",
            "",
        ],
    )
    for version in judge.versions:
        strengths = version.strengths or ["명시된 강점 없음"]
        weaknesses = version.weaknesses or ["명시된 약점 없음"]
        lines.extend(
            [
                f"#### {version.api_version}",
                "",
                "**잘한 점**",
                "",
                *(f"- {_cell(item)}" for item in strengths),
                "",
                "**아쉬운 점**",
                "",
                *(f"- {_cell(item)}" for item in weaknesses),
                "",
            ],
        )

    lines.extend(["### Pairwise 직접 상대평가", ""])
    for comparison in judge.pairwise_comparisons:
        lines.extend(
            [
                (
                    f"#### {comparison.left_version} vs {comparison.right_version} — "
                    f"종합 승자: {_winner_label(comparison.overall_winner)}"
                ),
                "",
                f"- **종합 판단:** {_cell(comparison.summary)}",
                "",
                "| 비교 기준 | 승자 | 판단 | 반론 |",
                "| --- | --- | --- | --- |",
            ],
        )
        for criterion in comparison.criteria:
            evidence = "; ".join(criterion.evidence)
            lines.append(
                f"| {criterion.criterion} | {_winner_label(criterion.winner)} | "
                f"{_cell(criterion.rationale)} (evidence: {_cell(evidence)}) | "
                f"{_cell(criterion.counterargument)} |",
            )
        lines.append("")

    lines.extend(
        [
            "### 최종 추천",
            "",
            f"#### 품질 우선 — {', '.join(judge.quality_recommendation.versions)}",
            "",
            f"- **추천 근거:** {_cell(judge.quality_recommendation.rationale)}",
            f"- **선택 조건:** {_cell(judge.quality_recommendation.selection_condition)}",
            *(f"- **트레이드오프:** {_cell(tradeoff)}" for tradeoff in judge.quality_recommendation.tradeoffs),
            "",
            f"#### 비용·속도 포함 실용 선택 — {', '.join(judge.practical_recommendation.versions)}",
            "",
            f"- **추천 근거:** {_cell(judge.practical_recommendation.rationale)}",
            f"- **선택 조건:** {_cell(judge.practical_recommendation.selection_condition)}",
            *(f"- **트레이드오프:** {_cell(tradeoff)}" for tradeoff in judge.practical_recommendation.tradeoffs),
            "",
            f"- **종합 결론:** {_cell(judge.conclusion)}",
            "",
            "### Scenario별 Agent Judge 판단",
            "",
            "| Version | Scenario | Band | 결과 | 판단 근거 |",
            "| --- | --- | --- | --- | --- |",
        ],
    )
    for version in judge.versions:
        for scenario in version.scenario_judgments:
            lines.append(  # noqa: PERF401
                f"| {version.api_version} | {scenario.scenario_id} · {_cell(scenario.title)} | "
                f"{scenario.global_pressure_band} | {scenario.verdict} | {_cell(scenario.rationale)} "
                f"(evidence: {_cell('; '.join(scenario.evidence))}) |",
            )
    return lines


def _winner_label(winner: str) -> str:
    return "동률" if winner == "tie" else winner


def _all_bands(successful: dict[str, dict[str, Any]]) -> list[str]:
    order = ["strong_bearish", "bearish", "balanced", "bullish", "strong_bullish"]
    found = {
        str(_field(row, "globalPressureBand", "global_pressure_band"))
        for data in successful.values()
        for row in _rows(data)
        if _field(row, "globalPressureBand", "global_pressure_band")
    }
    return [band for band in order if band in found] + sorted(found - set(order))


def _row_for_band(data: dict[str, Any], band: str) -> dict[str, Any] | None:
    return next(
        (row for row in _rows(data) if _field(row, "globalPressureBand", "global_pressure_band") == band),
        None,
    )


def _rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    table = data.get("table") if isinstance(data.get("table"), dict) else {}
    return [row for row in table.get("rows", []) if isinstance(row, dict)]


def _dimensions(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in data.get("dimensionDefinitions", []) if isinstance(item, dict)]


def _scenario_dimension_sections(
    data: dict[str, Any],
    dimensions: list[dict[str, Any]],
) -> list[str]:
    labels = _dimension_display_labels(dimensions)
    lines = [
        "",
        "#### 시나리오별 Dimension Value",
        "",
        "Dimension과 Value는 API의 사용자용 label로 표시합니다.",
        "",
        (f"| Scenario ID · 레이블 | scenario_role | pressure_band | {' | '.join(_cell(label) for label in labels)} |"),
        f"| --- | --- | --- | {' | '.join('---' for _ in labels)} |",
    ]
    for row in _rows(data):
        selected = [_selected_value_label(row, dimension) for dimension in dimensions]
        lines.append(
            f"| {_cell(_scenario_label(row))} | "
            f"{_cell(_field(row, 'scenarioRole', 'scenario_role'))} | "
            f"{_cell(_field(row, 'globalPressureBand', 'global_pressure_band'))} | "
            f"{' | '.join(_cell(value) for value in selected)} |",
        )

    lines.extend(["", "#### 시나리오별 Dimension/Value 선택 근거", ""])
    for row in _rows(data):
        lines.extend(
            [
                f"##### {_cell(_scenario_label(row))}",
                "",
                f"- 시나리오 설명: {_cell(row.get('narrative'))}",
                (
                    "- 시나리오 조합/가격 판단 근거: "
                    f"{_cell(_field(row, 'globalPressureRationale', 'global_pressure_rationale'))}"
                ),
                "",
                "| Dimension | Dimension 선택 근거 | 선택 Value | Value 선택 근거 |",
                "| --- | --- | --- | --- |",
            ],
        )
        for dimension, label in zip(dimensions, labels, strict=True):
            selected_value = _selected_value(row, dimension)
            lines.append(
                f"| {_cell(label)} | {_cell(_dimension_rationale(dimension))} | "
                f"{_cell(_value_label(selected_value))} | {_cell(_value_rationale(selected_value))} |",
            )
        lines.append("")
    return lines


def _dimension_display_labels(dimensions: list[dict[str, Any]]) -> list[str]:
    base_labels = [str(dimension.get("label") or "레이블 없음") for dimension in dimensions]
    counts = {label: base_labels.count(label) for label in set(base_labels)}
    labels: list[str] = []
    for dimension, label in zip(dimensions, base_labels, strict=True):
        if counts[label] == 1:
            labels.append(label)
            continue
        event_lineage = ", ".join(map(str, _dimension_event_ids(dimension))) or "lineage 없음"
        labels.append(f"{label} (Event {event_lineage})")
    return labels


def _scenario_label(row: dict[str, Any]) -> str:
    scenario_id = _field(row, "scenarioId", "scenario_id")
    title = row.get("title") or "레이블 없음"
    return f"{scenario_id if scenario_id is not None else '-'} · {title}"


def _selected_value(row: dict[str, Any], dimension: dict[str, Any]) -> dict[str, Any] | None:
    cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
    dimension_id = _field(dimension, "dimensionId", "dimension_id")
    raw_value = cells.get(dimension_id)
    for value in dimension.get("values", []):
        if isinstance(value, dict) and raw_value == _field(value, "valueId", "value_id"):
            return value
    return None


def _selected_value_label(row: dict[str, Any], dimension: dict[str, Any]) -> str:
    cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
    dimension_id = _field(dimension, "dimensionId", "dimension_id")
    if cells.get(dimension_id) is None:
        return "-"
    selected = _selected_value(row, dimension)
    return _value_label(selected) if selected else "미정의 Value"


def _value_label(value: dict[str, Any] | None) -> str:
    if value is None:
        return "-"
    return str(value.get("label") or "레이블 없음")


def _dimension_rationale(dimension: dict[str, Any]) -> str:
    direct = _field(dimension, "selectionRationale", "selection_rationale", "rationale")
    if direct:
        return str(direct)
    groundings = _field(dimension, "eventGroundings", "event_groundings")
    grounding_rationales: list[str] = []
    if isinstance(groundings, list):
        for grounding in groundings:
            if not isinstance(grounding, dict):
                continue
            event_id = _field(grounding, "eventId", "event_id")
            observed = _field(grounding, "observedBasis", "observed_basis")
            uncertainty = grounding.get("uncertainty")
            if observed or uncertainty:
                grounding_rationales.append(
                    f"Event {event_id}: 관측 근거={observed or '-'}, 불확실성={uncertainty or '-'}",
                )
    if grounding_rationales:
        return "; ".join(grounding_rationales)
    source_rationales = _nested_rationales(_field(dimension, "sourceRefs", "source_refs"))
    return "; ".join(source_rationales) if source_rationales else "API 응답에 Dimension 선택 근거 없음"


def _value_rationale(value: dict[str, Any] | None) -> str:
    if value is None:
        return "API 응답에서 선택 Value 정의를 찾을 수 없음"
    source_rationales = _nested_rationales(_field(value, "sourceAssignments", "source_assignments"))
    if source_rationales:
        return "; ".join(source_rationales)
    assumption = _field(value, "assumptionRationale", "assumption_rationale")
    if assumption:
        return str(assumption)
    contribution = _field(value, "globalPressureContribution", "global_pressure_contribution")
    if contribution:
        return f"가격 압력 기여: {contribution}"
    return "API 응답에 Value 선택 근거 없음"


def _nested_rationales(items: Any) -> list[str]:  # noqa: ANN401
    if not isinstance(items, list):
        return []
    return [
        str(item["rationale"]) for item in items if isinstance(item, dict) and str(item.get("rationale") or "").strip()
    ]


def _scenario_cell_summary(data: dict[str, Any], row: dict[str, Any]) -> str:
    dimensions = _dimensions(data)
    labels = _dimension_display_labels(dimensions)
    return "; ".join(
        f"{label} = {_selected_value_label(row, dimension)}"
        for dimension, label in zip(dimensions, labels, strict=True)
    )


def _dimension_event_ids(dimension: dict[str, Any]) -> list[int]:  # noqa: C901
    event_ids: set[int] = set()
    for grounding in dimension.get("eventGroundings", []) or dimension.get("event_groundings", []):
        if isinstance(grounding, dict):
            event_id = _field(grounding, "eventId", "event_id")
            if event_id is not None:
                event_ids.add(int(event_id))
    for value in dimension.get("sourceEventIds", []) or dimension.get("source_event_ids", []):
        event_ids.add(int(value))
    for source in dimension.get("sourceRefs", []) or dimension.get("source_refs", []):
        if isinstance(source, dict):
            event_id = _field(source, "eventId", "event_id")
            if event_id is not None:
                event_ids.add(int(event_id))
    compact_source = dimension.get("sourceRef") or dimension.get("source_ref")
    if isinstance(compact_source, dict):
        event_id = _field(compact_source, "eventId", "event_id")
        if event_id is not None:
            event_ids.add(int(event_id))
    for value in dimension.get("values", []):
        if not isinstance(value, dict):
            continue
        for source in value.get("sourceAssignments", []) or value.get("source_assignments", []):
            if isinstance(source, dict):
                event_id = _field(source, "eventId", "event_id")
                if event_id is not None:
                    event_ids.add(int(event_id))
    return sorted(event_ids)


def _execution_mode(manifest: dict[str, Any]) -> str:
    declared_mode = manifest.get("executionMode")
    if declared_mode:
        return str(declared_mode)
    orchestration_path = manifest.get("artifacts", {}).get("orchestration")
    if orchestration_path and Path(orchestration_path).is_file():
        return "async fallback (v2‖v3 → v4)"
    return "manual staged (v2 → v3 → v4)"


def _field(payload: dict[str, Any], *names: str) -> Any:  # noqa: ANN401
    return next((payload[name] for name in names if name in payload), None)


def _cell(value: Any) -> str:  # noqa: ANN401
    # Prefer plain-text separators over HTML so Markdown previewers stay compatible.
    return (
        str(value if value is not None else "-")
        .replace("|", "\\|")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )

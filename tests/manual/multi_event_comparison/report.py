from __future__ import annotations

# ruff: noqa: CPY001
import json
from pathlib import Path
from typing import Any

from tests.manual.multi_event_comparison.models import ComparisonJudgment, QualityCheck


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
        lines.extend(
            [
                f"### {version}",
                "",
                f"- 전략: `{data.get('generationStrategy')}`",
                f"- 그룹: **{_field(group, 'title') or '-'}** — {_field(group, 'description', 'summary') or '-'}",
                f"- Dimension 수: {len(data.get('dimensionDefinitions') or [])}",
                "",
                "| Dimension | 설명 | Event lineage | Values |",
                "| --- | --- | --- | --- |",
            ],
        )
        for dimension in data.get("dimensionDefinitions") or []:
            sources = _dimension_event_ids(dimension)
            values = [
                f"{value.get('label', value.get('valueId', value.get('value_id', '-')))}"
                for value in dimension.get("values", [])
                if isinstance(value, dict)
            ]
            lines.append(
                f"| {_cell(dimension.get('label') or dimension.get('dimensionId'))} | "
                f"{_cell(dimension.get('description'))} | {_cell(', '.join(map(str, sources)) or '-')} | "
                f"{_cell('; '.join(values))} |",
            )
        lines.extend(
            [
                "",
                "<details><summary>generationDiagnostics 실제 값</summary>",
                "",
                "```json",
                json.dumps(diagnostics, ensure_ascii=False, indent=2, default=str),
                "```",
                "</details>",
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
                f"| {version} | **{_cell(row.get('title'))}**<br>{_cell(row.get('narrative'))} | "
                f"{_field(row, 'scenarioRole', 'scenario_role')} / "
                f"{_field(row, 'baselineYn', 'baseline_yn')} / "
                f"{_field(row, 'probabilityScore', 'probability_score')} | "
                f"{_cell(json.dumps(row.get('cells'), ensure_ascii=False, default=str))} | "
                f"{_cell(_field(row, 'globalPressureRationale', 'global_pressure_rationale'))} |",
            )
            related_markets = _field(row, "relatedMarkets", "related_markets")
            for item in related_markets if isinstance(related_markets, list) else []:
                if isinstance(item, dict) and item.get("market") and item.get("rationale"):
                    related_market_details.append(
                        f"- **{version} · {item['market']}**: {_cell(item['rationale'])}",
                    )
        if related_market_details:
            lines.extend(
                [
                    "",
                    "<details><summary>관련 시장 보조정보</summary>",
                    "",
                    *related_market_details,
                    "",
                    "</details>",
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
        lines.extend(_judge_section(judge, judge_error))
    else:
        lines.extend(
            [
                "",
                "## 품질 비교",
                "",
                "- 사용자가 품질검사를 제외하여 결정적 검사, LLM 점수, 버전 순위는 생성하지 않았습니다.",
            ],
        )
    lines.extend(
        [
            "",
            "## 해석상 주의",
            "",
            "- 모든 버전의 pressure band는 글로벌 LNG 가격 압력을 기준으로 비교합니다.",
            "- v4 relatedMarkets는 방향·강도 태그가 아닌 Scenario별 보조 관련성 정보입니다.",
            "- 이 보고서의 LLM 평가는 제공된 Event/API 증적만 사용하며 외부 사실의 진위를 검증하지 않습니다.",
        ],
    )
    return "\n".join(lines) + "\n"


def _judge_section(judge: ComparisonJudgment | None, judge_error: str | None) -> list[str]:
    lines = ["", "## LLM 품질 비교", ""]
    if judge is None:
        reason = f" Judge 오류: `{_cell(judge_error)}`" if judge_error else ""
        return [
            *lines,
            (f"- 성공 버전이 2개 미만이거나 Judge가 실행되지 않아 비교 결론은 **판정 불가**입니다.{reason}"),
        ]
    lines.extend(["| Version | 기준 | 점수 | 결과 | LLM 근거 |", "| --- | --- | --- | --- | --- |"])
    for version in judge.versions:
        for criterion in version.criteria:
            lines.append(  # noqa: PERF401
                f"| {version.api_version} | {criterion.criterion} | {criterion.score}/5 | "
                f"{criterion.verdict} | {_cell(criterion.rationale)}<br>"
                f"evidence: {_cell('; '.join(criterion.evidence))} |",
            )
    lines.extend(
        [
            "",
            f"- **우수 버전:** {', '.join(judge.best_versions)}",
            f"- **선정 이유:** {judge.conclusion}",
            "",
            "### Scenario별 LLM 판단",
            "",
            "| Version | Scenario | Band | 결과 | 판단 근거 |",
            "| --- | --- | --- | --- | --- |",
        ],
    )
    for version in judge.versions:
        for scenario in version.scenario_judgments:
            lines.append(  # noqa: PERF401
                f"| {version.api_version} | {scenario.scenario_id} · {_cell(scenario.title)} | "
                f"{scenario.global_pressure_band} | {scenario.verdict} | {_cell(scenario.rationale)}"
                f"<br>evidence: {_cell('; '.join(scenario.evidence))} |",
            )
    return lines


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


def _dimension_event_ids(dimension: dict[str, Any]) -> list[int]:
    event_ids: set[int] = set()
    for value in dimension.get("sourceEventIds", []) or dimension.get("source_event_ids", []):
        event_ids.add(int(value))
    for source in dimension.get("sourceRefs", []) or dimension.get("source_refs", []):
        if isinstance(source, dict):
            event_id = _field(source, "eventId", "event_id")
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
    orchestration_path = manifest.get("artifacts", {}).get("orchestration")
    if orchestration_path and Path(orchestration_path).is_file():
        return "async fallback (v2‖v3 → v4)"
    return "subagent staged (v2‖v3 → v4)"


def _field(payload: dict[str, Any], *names: str) -> Any:  # noqa: ANN401
    return next((payload[name] for name in names if name in payload), None)


def _cell(value: Any) -> str:  # noqa: ANN401
    return str(value if value is not None else "-").replace("|", "\\|").replace("\n", "<br>")

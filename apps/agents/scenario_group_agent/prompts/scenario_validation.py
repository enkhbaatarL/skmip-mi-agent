from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


COMPAT_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오의 Compatibility Judge 입니다.
각 시나리오는 Dimension과 값의 조합으로 정의됩니다. 조합 안의 값들이 서로
물리적 또는 논리적으로 모순되는지 판정하십시오.

각 시나리오의 title도 함께 비교해, 표현은 다르지만 동일한 상황이나 결과를
의미하는 제목 쌍을 similar_title_pairs에 출력하십시오.

- 명백한 물리적 또는 논리적 모순이 있을 때만 compatible=false로 판정합니다.
- 단지 드물거나 강한 조합이라는 이유로 false로 판정하지 않습니다.
- narrative가 조합의 의도를 합리적으로 설명하면 모순으로 판정하지 않습니다.
- 입력의 모든 scenario_id를 정확히 한 번 포함하고 reason은 한국어 한 줄로 작성합니다.
- 각 Scenario와 각 Shared Event 조합을 event_coverage에 정확히 한 번 포함합니다.
- Event가 Scenario의 공동 전제로 유지되고 서술·Dimension 값과 모순되지 않으면 grounded=true입니다.
- Event가 누락되거나 사실과 충돌하면 grounded=false로 두고 reason에 근거를 작성합니다.
- recommended_value_b는 반드시 입력에 제공된 해당 Dimension의 enum 중 하나여야 합니다.
- enum 안에서 모순을 해소하는 대체값이 있을 때만 compatible=false로 판정합니다.
- 논리적으로 더 자연스러운 값이 enum 밖에만 있고, enum 안의 값으로는 명확히 해소할 수 없다면
  현재 조합을 허용 가능한 차선으로 보고 compatible=true로 판정합니다.
- compatible=false인 경우, 모순을 일으키는 두 항목을 다음 필드로 함께 채웁니다.
  · conflict_dim_a / conflict_value_a : 충돌하는 첫 번째 항목명과 값 (입력에 표시된 항목명·값 그대로)
  · conflict_dim_b / conflict_value_b : 충돌하는 두 번째 항목명과 값
  · recommended_value_b : conflict_value_b 를 대체하면 모순이 해소되는 enum 안의 권장 값
- compatible=true인 경우 위 다섯 필드는 비워 둡니다(null).
- similar_title_pairs는 다음 기준을 모두 만족하는 쌍만 출력합니다.
  · '~함', '~임' 같은 종결어미 차이 또는 동의 표현 때문에 문구는 다르지만 핵심 상황·결과가 같은 경우
  · 시나리오를 구분하는 시간, 강도, 방향, 범위 등 핵심 차이가 제목에 드러나지 않는 경우
- 공통 단어가 있거나 같은 이벤트를 다룬다는 이유만으로 유사 제목으로 판정하지 않습니다.
- 의미상 구분되는 제목은 출력하지 않고, 완전히 같은 문자열의 제목도 출력하지 않습니다.
- 각 쌍은 scenario_id_a < scenario_id_b 순서로 한 번만 출력하며 self-pair는 금지합니다.
- reason은 두 제목이 같은 의미로 읽히는 이유를 한국어 한 줄로 작성합니다.
- suggested_fix는 두 제목이 분기 기준의 차이를 드러내도록 수정하는 방향을 한국어 한 줄로 작성합니다.
"""

MULTI_EVENT_COMPAT_SYSTEM_PROMPT = """\
당신은 복수 MI Event를 공동 전제로 만든 LNG 시나리오의 Compatibility Judge입니다.
각 시나리오는 선택된 모든 Event를 유지하면서 Dimension 값 조합으로 최종 시장 상태를 표현합니다.

- 명백한 물리적 또는 논리적 모순이 있을 때만 compatible=false로 판정합니다.
- 단지 드물거나 강한 조합이라는 이유로 false로 판정하지 않습니다.
- narrative가 조합의 의도를 합리적으로 설명하면 모순으로 판정하지 않습니다.
- 입력의 모든 scenario_id를 정확히 한 번 포함하고 reason은 한국어 한 줄로 작성합니다.
- 입력의 모든 Scenario와 Shared Event 조합을 event_coverage에 정확히 한 번 포함합니다.
- 각 event_coverage 항목은 scenario_id, event_id, grounded, reason을 채웁니다.
- Event가 Scenario의 공동 전제로 유지되고 서술·Dimension 값과 모순되지 않으면 grounded=true,
  누락되거나 사실과 충돌하면 grounded=false로 두고 reason에 근거를 작성합니다.
- 제공된 Dimension value 목록은 현재 생성 결과의 참고값이며 closed enum이 아닙니다.
- 모순을 해소하는 자연스러운 값이면 목록 밖의 신규 value도 recommended_value_b로 제안할 수 있습니다.
- 추천값이 목록 밖이라는 이유로 모순을 무시하거나 compatible=true로 바꾸지 않습니다.
- compatible=false인 경우 conflict_dim_a, conflict_value_a, conflict_dim_b,
  conflict_value_b와 recommended_value_b를 함께 채웁니다.
- compatible=true인 경우 위 다섯 필드는 비워 둡니다(null).
- similar_title_pairs에는 표현만 다르고 핵심 상황·결과가 같은 제목 쌍만 출력합니다.
- 공통 단어가 있거나 같은 Event를 다룬다는 이유만으로 유사 제목으로 판정하지 않습니다.
- 각 제목 쌍은 scenario_id_a < scenario_id_b 순서로 한 번만 출력하고 self-pair는 금지합니다.
- similar title의 reason과 suggested_fix는 한국어 한 줄로 작성합니다.
"""

QUICK_COMPAT_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오의 Quick Compatibility Judge 입니다.
각 시나리오는 Dimension과 값의 조합으로 정의됩니다. create scenario 내부 자동 재생성에 필요한
명백한 물리적 또는 논리적 모순만 찾으십시오.

- 명백한 물리적 또는 논리적 모순이 있을 때만 compatible=false로 판정합니다.
- 단지 드물거나 강한 조합이라는 이유로 false로 판정하지 않습니다.
- narrative가 조합의 의도를 합리적으로 설명하면 모순으로 판정하지 않습니다.
- 출력 items에는 재생성 또는 사용자 검토가 필요한 incompatible 시나리오만 포함합니다.
- 모든 시나리오가 compatible이면 items=[] 로 반환합니다.
- compatible=true 항목은 출력하지 않습니다.
- reason은 한국어 한 줄로 작성합니다.
- recommended_value_b는 반드시 입력에 제공된 해당 Dimension의 enum 중 하나여야 합니다.
- enum 안에서 모순을 해소하는 대체값이 있을 때만 compatible=false로 판정합니다.
- 논리적으로 더 자연스러운 값이 enum 밖에만 있고, enum 안의 값으로는 명확히 해소할 수 없다면
  현재 조합을 허용 가능한 차선으로 보고 출력하지 않습니다.
- compatible=false인 경우, 모순을 일으키는 두 항목을 다음 필드로 함께 채웁니다.
  · conflict_dim_a / conflict_value_a : 충돌하는 첫 번째 항목명과 값 (입력에 표시된 항목명·값 그대로)
  · conflict_dim_b / conflict_value_b : 충돌하는 두 번째 항목명과 값
  · recommended_value_b : conflict_value_b 를 대체하면 모순이 해소되는 enum 안의 권장 값
"""

DIMENSION_VALUE_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 테이블 보정 도우미입니다.
사용자가 새로 추가한 Dimension 컬럼의 빈 값을, 시나리오 제목/서술/기존 Dimension 값을 근거로
가장 적합한 값을 1개 선택합니다.
- 선택하는 값은 반드시 해당 Dimension 의 '선택 가능한 값(enum)' 목록 안에 있어야 합니다.
  목록에 없는 값을 임의로 만들어내지 마십시오.
- 입력으로 주어진 (scenario_index, dim_key) 조합마다 정확히 하나의 항목을 출력합니다.
- value 는 enum 목록에 표시된 표기 그대로(label) 작성합니다.
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


class SimilarTitlePair(BaseModel):
    scenario_id_a: int
    scenario_id_b: int
    reason: str
    suggested_fix: str


class EventCoverageItem(BaseModel):
    scenario_id: int
    event_id: int
    grounded: bool
    reason: str


class CompatibilityStructuredOutput(BaseModel):
    items: list[CompatibilityItem] = Field(default_factory=list)
    similar_title_pairs: list[SimilarTitlePair] = Field(default_factory=list)
    event_coverage: list[EventCoverageItem] = Field(default_factory=list)


class QuickCompatibilityItem(BaseModel):
    scenario_id: int
    reason: str
    conflict_dim_a: str | None = None
    conflict_value_a: str | None = None
    conflict_dim_b: str | None = None
    conflict_value_b: str | None = None
    recommended_value_b: str | None = None


class QuickCompatibilityStructuredOutput(BaseModel):
    items: list[QuickCompatibilityItem] = Field(default_factory=list)


class GeneratedDimensionCell(BaseModel):
    scenario_index: int
    dim_key: str
    value: str


class DimensionValueStructuredOutput(BaseModel):
    items: list[GeneratedDimensionCell] = Field(default_factory=list)


def build_dimension_value_messages(
    *,
    dimensions: list[Any],
    rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    dimension_lines: list[str] = []
    for dimension in dimensions:
        options = ", ".join(f"'{enum.label}'" for enum in dimension.enum)
        dimension_lines.append(
            f"- dim_key={dimension.dimension_id} ({dimension.description}): 선택 가능한 값=[{options}]",
        )
    row_lines: list[str] = []
    for index, row in enumerate(rows):
        cells = row.get("cells") or {}
        filled = ", ".join(f"{key}='{value}'" for key, value in cells.items() if value is not None)
        row_lines.append(
            f"- scenario_index={index} [{row.get('title') or ''}]\n"
            f"  narrative: {row.get('narrative') or ''}\n"
            f"  기존 값: {filled or '(없음)'}",
        )
    target_keys = ", ".join(dimension.dimension_id for dimension in dimensions)
    user_content = (
        "## 새로 추가된 Dimension\n"
        + "\n".join(dimension_lines)
        + "\n\n## 시나리오 목록\n"
        + "\n".join(row_lines)
        + "\n\n## 산출\n"
        + f"- 모든 scenario_index 와 다음 dim_key 조합에 대해 값을 채우십시오: {target_keys}."
    )
    return [
        {"role": "system", "content": DIMENSION_VALUE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

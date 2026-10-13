"""이벤트 타입(L2) 분류 프롬프트 및 structured output schema.

초안(생성·병합·수정 결과) 1건이 tmm_mi_event_type_l2_m 의 카테고리(level_2_label) 중
어디에 해당하는지 LLM 이 판단해 하나를 고른다.

- LLM 은 숫자 id 가 아니라 카테고리 이름을 고른다. 이름 → event_type_l2_id 변환은 노드가 한다.
- 출력 schema 의 `event_type` 은 카탈로그 이름만 허용하는 enum 으로 매 요청 동적으로 만든다
  (build_output_schema). 그래서 카탈로그에 없는 카테고리는 출력 자체가 불가능하다.
- `rationale` 을 `event_type` 보다 먼저 두어, 근거를 쓴 뒤 카테고리를 고르게 한다.

프롬프트 빌더는 순수 함수(I/O 없음)로 유지한다.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from apps.agents.event_generate_agent.schemas.domain import EventDraft, EventTypeCatalogItem


class EventTypeLLMOutput(BaseModel):
    rationale: str = Field(default="", description="초안의 핵심 동인과 그에 맞는 카테고리를 고른 근거 한 문장")
    event_type: str | None = Field(default=None, description="고른 카테고리 이름. 맞는 카테고리가 없으면 null")


def build_choices(catalog: list[EventTypeCatalogItem]) -> dict[str, EventTypeCatalogItem]:
    """LLM 이 고를 카테고리 이름 → 카탈로그 항목.

    L2 는 (L1, code) 단위로만 유일해 한글명이 겹칠 수 있으므로, 겹치는 이름만 코드를 붙여 구분한다.
    """
    label_counts = Counter(item.label for item in catalog)
    choices: dict[str, EventTypeCatalogItem] = {}
    for item in catalog:
        name = item.label or item.code or str(item.event_type_l2_id)
        if label_counts[item.label] > 1:
            name = f"{name} ({item.code or item.event_type_l2_id})"
        choices.setdefault(name, item)
    return choices


def build_output_schema(choice_names: list[str]) -> type[EventTypeLLMOutput]:
    """`event_type` 을 카탈로그 카테고리 이름 enum 으로 좁힌 출력 schema 를 만든다."""
    category = Literal[tuple(choice_names)]  # type: ignore[valid-type]
    return create_model(
        "EventTypeLLMOutput",
        __base__=EventTypeLLMOutput,
        event_type=(
            category | None,
            Field(
                default=None,
                description="[이벤트 유형 카탈로그]에서 고른 카테고리 이름. 맞는 카테고리가 없으면 null",
            ),
        ),
    )


SYSTEM_PROMPT = """
당신은 LNG·에너지 시장 MI(Market Intelligence) 시스템의 이벤트 유형 분류기입니다.
[이벤트 초안]이 [이벤트 유형 카탈로그]의 어느 카테고리에 해당하는지 판단해 하나를 고릅니다.

### [분류 절차]
1. 초안의 제목·요약·핵심 포인트를 읽고, 이 사건이 시장에 영향을 주는 핵심 동인(무엇이 수급·가격을 움직이는가)을 파악합니다.
2. 카탈로그의 각 카테고리 이름과 핵심 동인을 비교해 가장 가까운 카테고리 하나를 고릅니다.
3. rationale 에 파악한 핵심 동인과 그 카테고리를 고른 이유를 한 문장으로 먼저 적고, event_type 에 카테고리 이름을 적습니다.

### [분류 원칙]
* event_type 에는 카탈로그의 카테고리 이름을 글자 그대로 적습니다. 카탈로그에 없는 카테고리를 만들지 않습니다.
* 제목에 나온 단어가 아니라 사건의 핵심 동인으로 판단합니다.
* 여러 카테고리에 걸치면 시장 영향이 가장 큰 동인의 카테고리를 고릅니다.
* 어느 카테고리에도 맞지 않으면 event_type 을 null 로 둡니다.

### [기존 이벤트를 편집한 초안]
초안에 편집 방식과 원본 이벤트 유형이 함께 주어지면 다음을 따릅니다.
* modify(수치 수정): 원본 유형을 유지하는 것이 원칙입니다. 바뀐 수치 때문에 사건의 성격 자체가 달라진 경우
  (예: 일시적 운항 차질 → 장기 봉쇄)에만 다른 유형을 고르고, rationale 에 무엇이 달라졌는지 적습니다.
* merge(병합): 원본 유형 중 병합된 사건의 핵심 동인에 해당하는 유형을 우선합니다.
  원본 유형 어느 것도 병합된 사건 전체를 대표하지 못하면 카탈로그에서 새로 고릅니다.
* 원본 유형 이름이 카탈로그 이름과 조금 다르면 같은 의미의 카테고리를 고릅니다.
""".strip()


def _format_catalog(choices: dict[str, EventTypeCatalogItem]) -> str:
    """카테고리 이름 한 줄씩. 코드는 의미 파악을 돕도록 덧붙이되, 이름에 이미 붙은 경우는 생략한다."""
    lines: list[str] = []
    for name, item in choices.items():
        show_code = item.code and not name.endswith(f"({item.code})")
        lines.append(f"- {name}" + (f" (코드: {item.code})" if show_code else ""))
    return "\n".join(lines)


def _format_draft(draft: EventDraft, source_type_labels: list[str]) -> str:
    lines = [f"제목: {draft.event_title_ko}", f"요약: {draft.one_line_summary}"]
    if draft.key_bullets:
        lines.append("핵심: " + " / ".join(draft.key_bullets))
    if draft.tags:
        lines.append("태그: " + ", ".join(draft.tags))
    if draft.operation is not None:
        lines.append(f"편집 방식: {draft.operation.value}")
        lines.append("원본 이벤트 유형: " + (", ".join(source_type_labels) if source_type_labels else "(알 수 없음)"))
    return "\n".join(lines)


def build_messages(
    draft: EventDraft,
    choices: dict[str, EventTypeCatalogItem],
    *,
    source_type_labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """system/user 메시지 리스트를 구성한다(I/O 없음).

    Args:
        draft: 분류할 초안.
        choices: 고를 수 있는 카테고리 이름 → 카탈로그 항목(build_choices 결과).
        source_type_labels: 원본 기존 이벤트의 유형 이름(병합·수정 초안만).

    """
    user_content = f"""[이벤트 유형 카탈로그]
{_format_catalog(choices)}

[이벤트 초안]
{_format_draft(draft, source_type_labels or [])}

이 초안이 어느 카테고리에 해당하는지 판단해 카탈로그에서 골라 주세요."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

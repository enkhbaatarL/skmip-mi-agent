"""시나리오 그룹 종합 프롬프트 및 structured output schema.

시나리오별 동일 구조 해석을 받아 그룹 전체를 아우르는 한 단락 메시지를 만든다.
개별 비교는 시나리오 해석에 이미 담기므로 여기서는 종합 메시지만 생성한다.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field


class GroupSynthesisLLMOutput(BaseModel):
    overall_message: str = Field(description="그룹 전체 종합 메시지 한 단락")


SYSTEM_PROMPT = (
    "당신은 LNG 시장 시나리오 그룹 종합 애널리스트입니다. 각 시나리오의 정체성과 "
    "가격 성격, 신뢰도(모두 MI Base 대비)를 종합해 그룹 단위 결론·제언을 작성합니다."
)


def build_user_prompt(scenarios_brief: list[dict]) -> str:
    return f"""[시나리오 요약 (MI Base 대비)]
{json.dumps(scenarios_brief, ensure_ascii=False, indent=2)}

[작성 규칙 — '종합 결론 및 제언' 보고서 문체]
- 모든 문장은 친절하고 정중한 '-합니다/-됩니다'체로 끝맺습니다(개조식·명사종결·반말 금지).
- MI Base 대비 관점으로만 서술.
- 첫 문장에서 시나리오들이 어떤 성격으로 나뉘는지 한 줄로 정리한다.
- 이어서 시나리오별로 '■ ' 로 시작하는 문단을 두어, 각 시나리오의 핵심 성격,
  신뢰도(데이터 품질), 실무적으로 신뢰/검증/채택할 점을 제언한다.
- 데이터 품질 신호(이상치)가 있는 시나리오는 저신뢰로 다루고 모델 안정성 검증을 강조한다.
- 과도한 수치 나열은 피하고 판단·행동 중심으로 서술한다.

[분량 제한 — 반드시 준수]
- 전체 공백 포함 600자 이내. 도입 1문장 + 시나리오별 '■' 문단(각 2~3문장)으로 구성한다.

[출력 JSON 필드] overall_message (여러 문단을 개행으로 구분한 하나의 문자열)
순수 JSON 객체만 반환하세요."""

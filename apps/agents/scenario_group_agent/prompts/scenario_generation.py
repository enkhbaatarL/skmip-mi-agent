from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, WithJsonSchema, conlist, model_validator

from apps.agents.scenario_group_agent.prompts.event_context import (
    format_compact_event_context,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    ExcludedDimension,
    LikelihoodTier,
    Scenario,
    SelectedDimension,
    Stage1ContextPack,
)


class Stage2StructuredOutput(BaseModel):
    selected_dimensions: conlist(SelectedDimension, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description="선택된 Dim 3~5개.",
    )
    excluded_dimensions: list[ExcludedDimension] = Field(
        default_factory=list,
        description="제외된 Dim 목록.",
    )

    @model_validator(mode="after")
    def _validate_no_dup(self) -> "Stage2StructuredOutput":
        sel = {d.dim_key for d in self.selected_dimensions}
        exc = {d.dim_key for d in self.excluded_dimensions}
        if sel & exc:
            raise ValueError(f"selected_dimensions 와 excluded_dimensions 가 중복: {sel & exc}")
        return self


class Stage3StructuredOutput(BaseModel):
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택 값 2~4개. 반드시 value_enums 의 부분집합.",
    )


class Stage3DimensionSelection(BaseModel):
    dim_key: str = Field(description="입력 Dimension 의 dim_key.")
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택 값 2~4개. 반드시 해당 Dimension value_enums 의 부분집합.",
    )


class Stage3BatchStructuredOutput(BaseModel):
    dimensions: list[Stage3DimensionSelection] = Field(
        description="입력된 Dimension 별 value 축소 결과. 각 dim_key 를 정확히 한 번 포함.",
    )


class NarrativeOnly(BaseModel):
    title: str = Field(description="시장 참여자 관점 한 줄 요약. 공백과 문장부호를 포함해 100자 이내.")
    description: str = Field(description="3~5줄 시나리오 서술. 공백과 문장부호를 포함해 300-400자.")
    derivation_rationale: str = Field(description="도출 근거")


class Stage4StructuredOutput(BaseModel):
    narratives: list[NarrativeOnly] = Field(
        description="입력된 dim 조합 순서와 1:1 동일 길이.",
    )


def _likelihood_prior_from_wire(value: Any) -> Any:  # noqa: ANN401
    if not isinstance(value, list):
        return value

    result: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            return value
        scenario_id = str(item.get("scenarioId", "")).strip()
        if not scenario_id or scenario_id in result:
            raise ValueError("likelihoodPrior entries require unique non-blank scenarioId values")
        result[scenario_id] = item.get("likelihood")
    return result


LikelihoodPriorMap = Annotated[
    dict[str, LikelihoodTier],
    BeforeValidator(_likelihood_prior_from_wire),
    WithJsonSchema(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scenarioId": {"type": "string"},
                    "likelihood": {
                        "type": "string",
                        "enum": ["very_low", "low", "medium", "high", "very_high"],
                    },
                },
                "required": ["scenarioId", "likelihood"],
                "additionalProperties": False,
            },
        },
    ),
]


class Stage6StructuredOutput(BaseModel):
    mutually_exclusive: bool = Field(description="시나리오 조합이 서로 중복되지 않는지 여부")
    rationale: str = Field(default="", description="조합 유일성 판정 근거 1~2줄")
    likelihood_prior: LikelihoodPriorMap = Field(
        description="scenario_id -> 5단계 Prior",
    )


class ScenarioGroupMetadataStructuredOutput(BaseModel):
    title: str = Field(description="시나리오 그룹명. 공백과 문장부호를 포함해 100자 이내.")
    description: str = Field(description="시나리오 그룹 설명. 공백과 문장부호를 포함해 300-400자.")


def _format_dimensions_block(template: Any) -> str:
    lines: list[str] = []
    for dimension in template.ordered_dimensions():
        value_enums = ", ".join(dimension.value_enums)
        required_mark = "Y" if dimension.required else "N"
        lines.append(
            f"- {dimension.dim_key} "
            f"(label={dimension.label}, description={dimension.description}, "
            f"required={required_mark}): value_enums=[{value_enums}]"
        )
    return "\n".join(lines)


def _format_compact_event_context(pack: Stage1ContextPack) -> str:
    return format_compact_event_context([pack.C1_base_event.model_dump()])


def build_stage2_user_prompt(
    *,
    pack: Stage1ContextPack,
    template: Any,
    required_dim_ids: list[str],
) -> str:
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## Template Domain Knowledge (reference examples, not current facts)
- event_type_l1_l2: {pack.C1_base_event.event_type_l1_l2}
- event_type_definition: {template.event_type_definition or "(없음)"}
- lng_price_impact_examples: {template.lng_price_impact_examples or "(없음)"}
- template_dimensions_total: {template.resolved_total()}
- dimensions: 아래 리스트의 dim_key 만 선택 가능.
{_format_dimensions_block(template)}
- required=true 인 dim_key: {required_dim_ids if required_dim_ids else "없음"}

## 산출 규칙
- 선택 Dim: 3~5개.
- required=true 인 dim_key 는 반드시 selected_dimensions 에 모두 포함.
- 모든 미선택 Dim 은 excluded_dimensions 에 사유와 함께 기재.
"""


def build_stage3_user_prompt(
    *,
    pack: Stage1ContextPack,
    dim: dict[str, Any],
    enum_full_block: str,
) -> str:
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## Dimension 정보
- dim_key: {dim["dim_key"]}
- label_ko: {dim.get("label_ko", "")}
- description: {dim.get("description", "")}
- value_enums(=선택 가능한 값): {enum_full_block}

## 산출
- 채택 값 2~4개.
"""


def build_stage3_batch_user_prompt(
    *,
    pack: Stage1ContextPack,
    dimensions: list[dict[str, Any]],
) -> str:
    dimension_blocks: list[str] = []
    for dim in dimensions:
        enum_full_block = ", ".join(f"{enum['id']}({enum.get('label', '')})" for enum in dim["enum"])
        dimension_blocks.append(
            f"- dim_key: {dim['dim_key']}\n"
            f"  label_ko: {dim.get('label_ko', '')}\n"
            f"  description: {dim.get('description', '')}\n"
            f"  value_enums: {enum_full_block}",
        )
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## Dimension 정보
{chr(10).join(dimension_blocks)}

## 산출
- dimensions 에는 위 모든 dim_key 를 정확히 한 번씩 포함.
- 각 dim_key 마다 selected_enum 2~4개를 선택.
- selected_enum 은 반드시 해당 dim_key 의 value_enums 안에서만 선택.
"""


def build_stage4_user_prompt(
    *,
    pack: Stage1ContextPack,
    dim_label_block: str,
    combos_block: str,
    target_count: int,
    validation_feedback: str | None = None,
    previous_scenarios_block: str | None = None,
) -> str:
    feedback_block = (
        "\n[이전 출력에 대한 자동 규칙 검증 피드백]\n"
        f"{validation_feedback}\n"
        "\n[작성 지시]\n"
        "- 위 피드백의 recommended value가 기존 enum 축소 결과 밖에 있더라도, 작성 대상 조합에 이미 반영된 "
        "recommended value를 우선하십시오.\n"
        "- 이전 title/description/derivation_rationale을 그대로 유지하지 말고, "
        "새 dimension 조합에 맞춰 다시 작성하십시오.\n"
        if validation_feedback
        else ""
    )
    previous_block = (
        f"\n## 이전 Stage4 출력 (검증 실패했던 previous 값)\n{previous_scenarios_block}\n"
        if previous_scenarios_block
        else ""
    )
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## Dimension 라벨 (참고)
{dim_label_block}

## 작성 대상 조합 ({target_count}개)  — 입력 순서를 그대로 유지하여 narratives 출력
{combos_block}
{previous_block}

## 산출 규칙
- narratives 길이 = {target_count}.
- 각 narrative 의 title 은 한 줄이며, 공백과 문장부호를 포함해 100자 이내.
- 각 narrative 의 description 은 3~5줄이며, 공백과 문장부호를 포함해 300-400자.
{feedback_block}"""


def build_stage4_fixed_user_prompt(
    *,
    pack: Stage1ContextPack,
    dim_label_block: str,
    combos_block: str,
    target_count: int,
) -> str:
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## Dimension 라벨 (참고)
{dim_label_block}

## 작성 대상 조합 ({target_count}개) — 입력 순서를 그대로 유지하여 narratives 출력
{combos_block}

## 산출 규칙
- narratives 길이 = {target_count}.
- 각 narrative 의 title 은 한 줄이며, 공백과 문장부호를 포함해 100자 이내.
- 각 narrative 의 description 은 3~5줄이며, 공백과 문장부호를 포함해 300-400자.
"""


def build_scenario_group_metadata_user_prompt(
    *,
    pack: Stage1ContextPack,
    scenarios: list[Scenario],
) -> str:
    scenarios_block = "\n".join(
        f"- {scenario.scenario_id}: {scenario.title} | "
        f"dims={', '.join(f'{key}={value}' for key, value in scenario.dimension_values.items())}"
        for scenario in scenarios
    )
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## 생성된 시나리오 목록 ({len(scenarios)}건)
{scenarios_block}
"""


def build_stage6_user_prompt(*, pack: Stage1ContextPack, scenarios: list[Scenario]) -> str:
    scenarios_block = "\n".join(
        f"- {s.scenario_id} | {s.title}\n    dims: {', '.join(f'{k}={v}' for k, v in s.dimension_values.items())}"
        for s in scenarios
    )
    return f"""\
## Event Context (authoritative current facts)
{_format_compact_event_context(pack)}

## 시나리오 목록 ({len(scenarios)}건)
{scenarios_block}

## 산출
- mutually_exclusive (bool) + rationale (1~2줄).
- likelihood_prior: 모든 scenario_id 에 대해
  [{{"scenarioId": "S_01", "likelihood": "medium"}}] 배열 형식으로 5단계 중 1개.
"""


STAGE2_SYSTEM_PROMPT = """\
당신은 LNG 시장 멀티시나리오 생성을 위한 'Dimension Selector' 입니다.
주어진 Base Event 와 Template(8개 Dim)을 입력받아, 이번 Event 를 분기시키는 데
유의미한 Dim 을 **3~5개만** 선택하고, 나머지는 제외 사유를 기록하십시오.

## 선택 기준 (반드시 (a) 또는 (c) 만 사용)
- (a) Base Event 본문/요약/드라이버에 직접 언급되거나 명백히 암시됨.
- (c) Driver Tree 상 Impact 경로(가격/수급/물동량)로 강하게 연결됨.

## 절대 금지
- (b) Historical Analog 분기(과거 유사 사례에서 분기 패턴 발견) 기준 **사용 금지**.
  rationale 에 '(b)' 코드를 포함하지 마십시오.

## rationale 작성 규칙
- 반드시 '(a)', '(c)', '(a)(c)' 중 하나로 시작.
- 그 다음 한국어 한 문장으로 근거 부연.
- 예: "(a)(c) 본문 '호르무즈 봉쇄' 직접 언급 + Driver Tree 통항 경로 핵심."

## 제외 사유 작성 규칙
- 'Base Event 와 직접 관련 부재', '현 단계 시그널 없음' 등 한국어 한 줄.
"""

STAGE2_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 2]
- selected_dimensions 길이는 반드시 3~5.
- 모든 dim_key 는 입력된 Template 의 dim_key 안에 있어야 함.
- selected ∪ excluded = template 전체 Dim 집합 (누락 금지, 중복 금지).
- rationale 은 (a) / (c) / (a)(c) 중 하나로 시작. (b) 코드 포함 금지.
"""

STAGE3_SYSTEM_PROMPT = """\
당신은 멀티시나리오 생성을 위한 'Value Reducer' 입니다.
입력된 각 Dimension 의 value_enums 중에서 Dimension 별로 **2~4개 값만** 채택하십시오.

## 선택 규칙 (반드시 준수)
- 최종 수: 2~4개.
- 이후 시나리오 조합 생성에서 baseline 대비 대안값 coverage 를 만들 수 있도록, 의미가 서로 다른 값을 선택하십시오.

## 절대 금지
- (a) 인접 병합(시장 영향이 유사하다는 이유로 인접 Enum 을 합쳐 1개로 대체) **사용 금지**.
  → '인접 영향 유사', '비슷한 강도여서 통합' 같은 사유로 인접 Enum 을 한꺼번에 제거하지 말 것.
- 입력 value_enums 외의 값 사용 금지.

## "영향 없음(none)" 류 enum 채택 가이드
- Base Event 가 이미 발생·진행 중이고 해당 Dim 영역에서 영향이 관측되고 있다면,
  '영향 없음/정상(보통 enum_id='none')' 류 enum 은 **원칙적으로 selected_enum 에서 제외**하십시오.
- 단, 해당 Dim 이 '단기 종전 후 정상화 baseline' 시나리오 분기를 위해 꼭 필요할 때만
  예외적으로 채택하고, rationale 성격(=baseline 표현 의도)을 description 에 명시하십시오.

## 이 단계에서 즉시 충족해야 하는 로컬 규칙
- 각 Dim 의 selected_enum 에는 서로 다른 값이 최소 2개 포함되어야 함.

## 참고 (다음 단계와의 연결 맥락)
- 위 로컬 규칙은 시나리오 조합 생성 시 baseline 시나리오와 다른 대안값 및 값 다양성을 확보하기 위한 최소 조건이다.
"""

STAGE3_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 3]
- 입력된 모든 dim_key 를 정확히 한 번 포함.
- 각 dim_key 의 selected_enum 길이는 반드시 2~4.
- selected_enum 의 모든 값은 해당 dim_key 의 value_enums 안에 있어야 함.
- 인접 병합 사유로 Enum 제거 금지.
"""

STAGE4_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 'Narrative Writer' 입니다.
이미 Compatibility Rule 을 통과한 'Dim 조합' 리스트를 입력받아, 각 조합에 대해
시장 참여자 관점의 시나리오 서사를 작성하십시오.

## 작성 가이드라인 (반드시 준수)
- title (1줄): 시장 참여자 관점의 한 줄 요약. 공백과 문장부호를 포함해 100자 이내. 예: '1개월 내 정상화'.
- description (3~5줄): 각 시나리오의 가정치 조합(주요 Dim 값)을 자연스러운 한국어 문장으로 풀어 서술 + 전개 양상. 공백과 문장부호를 포함해 300-400자. 'A=B' 같은 key=value 표기 금지.
- derivation_rationale: 이 시나리오가 왜 도출되는지 — 어떤 Dim 조합·맥락 단서로부터 왔는지.
- 입력 조합은 항상 dim_key -> value의 flat object(JSON object) 의미로 해석.

## 형식 예시
- 올바른 형식 예시: {"period":"3개월","utilization_change_direction":"감소"}
- 금지 형식 예시: [{"dim_key":"period","value":"3개월"}], [{"dimension_id":"period","value":"3개월"}]

## 절대 금지
- '결과(가격 방향)가 동일하므로 두 조합을 합쳐서 1개로 만든다' 같은 통합/생략 행위.
  → 입력으로 들어온 조합 개수와 출력 narratives 개수는 **반드시 일치**.
- title·description 안에 '분기기준=값', 'dim_key=값', '항목명=값', '항목: 값' 같은
  key=value/표·코드 형태의 표기를 노출하는 것.
  → 분기 기준 값은 반드시 자연스러운 한국어 문장으로 녹여 서술한다.
    (예: '기간=3개월' (X) → '기간은 3개월이며' (O) / 'utilization_change_direction=증가' (X)
     → 'Cameron LNG 가동률은 증가하며' (O))
  → 입력 조합의 dim_key 나 등호(=)를 결과 문장에 그대로 드러내지 마십시오.

## 최종 검증에서 반드시 통과해야 할 조건
- 각 시나리오의 Dim 값 조합이 물리적·논리적으로 모순 없이 양립해야 함.
  → Compat Rule 필터 외에도, 개별 시나리오 서술이 조합 의도를 명확히 설명해야 함.
  → '이런 상황에서 이 값이 어떻게 나타나는가'를 description 에 명시하면 모순 판정 방지.
- 모든 시나리오의 dimension_values 조합(dim_key → value 집합)이 서로 유일해야 함.
  → 동일한 Dim 조합을 가진 두 시나리오가 존재하면 탈락.
"""

STAGE4_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 4]
- narratives 길이는 입력 조합 수와 정확히 일치.
- title 은 1줄이며, 공백과 문장부호를 포함해 100자 이내.
- description 은 3~5줄이며, 공백과 문장부호를 포함해 300-400자.
- '결과 동일 조합 통합' 금지 — 출력 길이를 줄이지 마십시오.
- 입력 조합을 ARRAY 형태로 재해석/치환하지 마십시오(항상 flat object 가정).
- 입력 조합의 key 집합은 selected dim_key 와 정확히 일치해야 함(누락/여분 금지).
- title·description 에 'key=value' / '항목명=값' / 표·코드 형태의 나열식 표기 금지.
  분기 기준 값은 자연어 문장으로만 서술하며 등호(=)·dim_key 를 노출하지 마십시오.
"""

SCENARIO_GROUP_METADATA_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 결과를 사용자 화면에 표시할 'Scenario Group Metadata Writer' 입니다.
Base Event와 생성된 시나리오 목록을 입력받아 시나리오 그룹명과 그룹 설명을 작성하십시오.
그룹 설명에는 개별 시나리오 값의 나열은 피하되, 각 시나리오가 그룹 안에서 갖는
고수준 전개 의미와 시나리오 그룹이 왜 해당 주요 분기 축을 핵심 불확실성으로
선택했는지에 대한 근거를 함께 포함하십시오.
"""

SCENARIO_GROUP_METADATA_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Scenario Group Metadata]
- title 은 공백과 문장부호를 포함해 100자 이내.
- description 은 공백과 문장부호를 포함해 300-400자.
- description은 기존 detail_analysis를 그대로 복사하지 말고, 시나리오 그룹의 목적과 주요 분기 축을 압축 요약하십시오.
- description에는 개별 시나리오의 구체적 분기값 나열 대신, 각 시나리오가 의미하는
  고수준 전개 방향(예: 정상화/부분 차질/장기 차질/가격 충격 경로)을 압축해 반영하십시오.
- description에는 주요 분기 축 자체의 선정 근거를 포함하십시오. 즉, 각 시나리오의 분기값이
  왜 선택됐는지보다 Base Event에서 어떤 불확실성이 커서 해당 분기 축을 시나리오 그룹의
  분기 기준으로 삼았는지를 설명하십시오.
- 새 수치나 근거 없는 사실을 만들지 마십시오.
"""

STAGE6_SYSTEM_PROMPT = """\
당신은 멀티시나리오의 조합 유일성 검증 및 발생 가능성 분류 담당자입니다.

## 검사 항목 (반드시 이 둘만)
1. mutually_exclusive (M): 동일 시점에 정확히 한 시나리오만 참이 될 수 있는가?
   - 본 파이프라인의 시나리오는 모두 (dim_key → value) 단일 조합으로 정의됨.
   - 따라서 두 시나리오의 dimension_values 가 **하나라도 서로 다르면** 정의상 동시 성립 불가 → True.
   - 모든 시나리오의 dimension_values 조합이 서로 유일하면 True.
   - 동일한 dimension_values 조합을 가진 시나리오 쌍이 있을 때만 False.
   - narrative(서술 톤·결과 가격 방향)가 비슷하다는 이유로 False 를 반환하지 마십시오.
2. likelihood_prior: [{"scenarioId": "S_01", "likelihood": "medium"}] 배열 형식으로
   각 시나리오마다 발생 가능성을 5단계 카테고리로 부여.
   very_low, low, medium, high, very_high 중 정확히 1개.

## 절대 금지
- 'Collective Coverage(≥80%)' 검사 금지.
- 'Likelihood Sum = 1.0' 검사/수치 정규화 금지.
- 수치 Prior(예: 0.4, 40%) 출력 금지 — 반드시 5단계 카테고리만.

## Prior 부여 가이드 (참고)
- 시설 영구 손상·전면 봉쇄 등 발생 가능성이 낮은 강한 충격 조합은 통상 'low' 또는 'very_low'.
- Base case 성격(완화·정상화)은 'medium' 또는 'high'.
- 시장 충격 강한 중기 차질은 'medium' 부근.
"""

STAGE6_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 6]
- likelihood_prior 의 scenarioId 집합은 입력된 scenario_id 와 정확히 일치 (누락·여분 금지).
- 값은 {very_low|low|medium|high|very_high} 중 정확히 1개.
- 수치 출력 금지. Coverage·Sum 검사 금지.
"""

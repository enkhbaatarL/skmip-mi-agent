from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, conlist, model_validator

from apps.persistence.enums import SignpostStrength


KEYWORD_HINTS_MIN: int = 3
KEYWORD_HINTS_MAX: int = 5


class Stage2Candidate(BaseModel):
    label_ko: str = Field(description="관측 가능한 신호 한 줄 (한국어).")
    filter_reason: str = Field(
        default="",
        description="3-필터를 통과한 사유 한국어 1줄.",
    )


class Stage2StructuredOutput(BaseModel):
    candidates: list[Stage2Candidate] = Field(
        description="3-필터를 통과한 Observability 후보만 포함.",
    )

    @model_validator(mode="after")
    def _validate_unique_labels(self) -> "Stage2StructuredOutput":
        seen: set[str] = set()
        for candidate in self.candidates:
            key = candidate.label_ko.strip()
            if not key:
                raise ValueError("label_ko 가 빈 문자열인 후보 존재.")
            if key in seen:
                raise ValueError(f"label_ko 중복: '{key}'")
            seen.add(key)
        return self


class Stage4Assignment(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    strength: SignpostStrength = Field(
        description="SignpostStrength enum 값 (VERYSTRONG/STRONG/MEDIUM/WEAK/VERYWEAK).",
    )
    rationale_ko: str = Field(
        description="이 strength 부여 + 시나리오 검증 측면의 한국어 1~2줄 근거.",
    )


class Stage4StructuredOutput(BaseModel):
    assignments: list[Stage4Assignment] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


class Stage5Hint(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    keyword_hints: conlist(str, min_length=KEYWORD_HINTS_MIN, max_length=KEYWORD_HINTS_MAX) = Field(  # type: ignore[valid-type]
        description="3~5개 키워드. 고유명사 + 동사/상태어 혼합 권장.",
    )


class Stage5StructuredOutput(BaseModel):
    hints: list[Stage5Hint] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


class Stage45SignpostDetail(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    strength: SignpostStrength = Field(
        description="SignpostStrength enum 값 (VERYSTRONG/STRONG/MEDIUM/WEAK/VERYWEAK).",
    )
    rationale_ko: str = Field(
        description="이 strength 부여 + 시나리오 검증 측면의 한국어 1~2줄 근거.",
    )
    keyword_hints: conlist(str, min_length=KEYWORD_HINTS_MIN, max_length=KEYWORD_HINTS_MAX) = Field(  # type: ignore[valid-type]
        description="Record 인입 1차 filter 용 3~5개 키워드.",
    )


class Stage45StructuredOutput(BaseModel):
    signposts: list[Stage45SignpostDetail] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


def _current_date() -> str:
    return date.today().strftime("%Y-%m-%d")  # noqa: DTZ011


def _format_compact_event_context(base_event_summary: dict[str, Any]) -> str:
    facts = "\n".join(
        f"  - {fact}"
        for fact in base_event_summary.get("key_facts", [])
        if str(fact).strip()
    ) or "  - (없음)"
    tags = ", ".join(str(tag) for tag in base_event_summary.get("tags", []) if str(tag).strip()) or "(없음)"
    return f"""\\
- current_date: {_current_date()}
- occurred_at: {base_event_summary.get("occurred_at", "") or "(없음)"}
- temporal_reference: 최근 N일/개월, 계절 및 과거·현재·미래 판단은 current_date를 기준으로 할 것.
  occurred_at은 Base Event 발생 시점으로 구분할 것.
- key_facts:
{facts}
- tags: {tags}"""


def build_stage2_user_prompt(
    *,
    scenario: dict[str, Any],
    base_event_summary: dict[str, Any],
    scenario_description: str,
    min_n: int,
    max_n: int,
) -> str:
    scenario_id = scenario.get("scenario_id", "S_??")
    dim_values_block = ", ".join(
        f"{k}={v}" for k, v in (scenario.get("dimension_values") or {}).items()
    ) or "(없음)"
    return f"""\
## Base Event 요약
- title: {base_event_summary.get("title", "")}
- summary: {base_event_summary.get("summary", "")}
{_format_compact_event_context(base_event_summary)}

## 대상 시나리오
- scenario_id: {scenario_id}
- title: {scenario.get("title", "")}
- description: {scenario_description}
- dimension_values: {dim_values_block}

## 산출
- candidates: 3-필터를 모두 통과한 후보만 {min_n}~{max_n}개.
- 각 후보는 label_ko + filter_reason 만 포함.
- 탈락 후보, passes_filter=false 후보, 검토용 후보는 출력하지 말 것.
- **MAX 를 채우지 말 것** — 결합도 강한 만큼만 출력.
- 후보는 시나리오 고유성 및 다른 후보와의 차별성이 높은 순서로 정렬할 것.
"""


def build_stage2_hard_constraints(*, min_n: int, max_n: int) -> str:
    return STAGE2_HARD_CONSTRAINTS.format(min_n=min_n, max_n=max_n)


def build_stage4_system_prompt(
    *,
    stage4_strength_guide: str,
    strong_min: int,
    strong_max: int,
    early_min: int,
    early_max: int,
) -> str:
    return STAGE4_SYSTEM_PROMPT.format(
        stage4_strength_guide=stage4_strength_guide,
        strong_min=strong_min,
        strong_max=strong_max,
        early_min=early_min,
        early_max=early_max,
    )


def build_stage4_hard_constraints(
    *,
    strong_min: int,
    strong_max: int,
    early_min: int,
    early_max: int,
) -> str:
    return STAGE4_HARD_CONSTRAINTS.format(
        strong_min=strong_min,
        strong_max=strong_max,
        early_min=early_min,
        early_max=early_max,
    )


def build_stage4_user_prompt(
    *,
    scenario: dict[str, Any],
    base_event_summary: dict[str, Any],
    scenario_description: str,
    labels: list[str],
) -> str:
    scenario_id = scenario.get("scenario_id", "S_??")
    signpost_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))
    dim_values = ", ".join(
        f"{k}={v}" for k, v in (scenario.get("dimension_values") or {}).items()
    ) or "(없음)"
    return f"""\
## Base Event 요약
- title: {base_event_summary.get("title", "")}
- summary: {base_event_summary.get("summary", "")}

## 대상 시나리오
- scenario_id: {scenario_id}
- title: {scenario.get("title", "")}
- description: {scenario_description}
- dimension_values: {dim_values}

## 입력 Signpost ({len(labels)}개)
{signpost_block}

## 산출
- assignments 길이 = {len(labels)}, label_ko 순서 유지.
- 각 항목에 strength + rationale_ko (1~2줄).
"""


def build_stage5_user_prompt(
    *,
    scenario: dict[str, Any],
    base_event_summary: dict[str, Any],
    scenario_description: str,
    labels: list[str],
) -> str:
    scenario_id = scenario.get("scenario_id", "S_??")
    label_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))
    return f"""\
## Base Event 참고
- title: {base_event_summary.get("title", "")}

## 대상 시나리오 ({scenario_id})
- title: {scenario.get("title", "")}
- description: {scenario_description}

## 입력 Signpost label ({len(labels)}개) — 이 순서를 유지하여 hints 출력
{label_block}

## 산출
- hints 길이 = {len(labels)}.
- 각 항목의 keyword_hints 는 3~5개.
"""


def build_stage45_user_prompt(
    *,
    scenario: dict[str, Any],
    base_event_summary: dict[str, Any],
    scenario_description: str,
    labels: list[str],
) -> str:
    scenario_id = scenario.get("scenario_id", "S_??")
    label_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))
    dim_values = ", ".join(
        f"{k}={v}" for k, v in (scenario.get("dimension_values") or {}).items()
    ) or "(없음)"
    return f"""\
## Base Event 요약
- title: {base_event_summary.get("title", "")}
- summary: {base_event_summary.get("summary", "")}
{_format_compact_event_context(base_event_summary)}

## 대상 시나리오
- scenario_id: {scenario_id}
- title: {scenario.get("title", "")}
- description: {scenario_description}
- dimension_values: {dim_values}

## 입력 Signpost label ({len(labels)}개) — 이 순서를 유지하여 signposts 출력
{label_block}

## 산출
- signposts 길이 = {len(labels)}, label_ko 순서 유지.
- 각 항목에 strength, rationale_ko, keyword_hints 를 모두 채움.
- direction 은 downstream 에서 SUP 로 고정하므로 출력하지 않음.
"""


STAGE2_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 'Observability Filter' 입니다.
입력으로 시나리오 1건의 가정치 조합(dimension_values + 서술)을 받아, **이 시나리오가
참이라면 향후 관측 가능한 신호** 후보를 생성한 뒤, 아래 3개 필터를 모두 통과한 후보만 출력하십시오.

## 후보 생성 가이드
- 각 후보는 한국어 한 줄로 작성 (예: 'Ras Laffan 재가동 공식 발표').
- 고유명사(시설/기관/지명) 1개 이상 + 동사·상태어 1개 이상 포함.
- '관측 가능한 사실 명제' 여야 함. 의견/감정/모호 표현 금지.
- Reuters / Platts / Bloomberg / Kpler / LSEG 등 Content Provider 가 집계·보도 주체일 뿐이면
  label_ko 의 주체어에서 제외하고, 실제 관측 대상(시설/국가/지표/물량/가격) 중심으로 작성.

## 3-필터 (모두 통과한 후보만 출력)
1. 소스 가용성: Reuters / Platts / Bloomberg / WSJ / FT 등 주요 매체 또는 정부·기관
   공식 채널에서 보도될 가능성이 높아야 함.
2. Binary 판정: 모호한 해석 없이 '관측됨 / 미관측'을 결정 가능해야 함.
   ('분위기', '전망', '기대감' 류 모호어는 탈락)
3. 시나리오 결합도: 일반 뉴스가 아니라 입력된 시나리오 가정치(특정 지명/봉쇄 단계/
   리스크 프리미엄 수준 등)와 직접 연결되어야 함.

## 동일 시나리오 내 후보 차별성
- 각 후보는 관측 대상, 판정 가능한 사실, 시간축·투자/운영 단계 중 최소 하나가 다른 후보와
  실질적으로 달라야 함.
- 같은 사건을 표현만 바꾼 후보(예: '인허가 승인 발표'와 '인허가 취득 공식화')는 하나만 남길 것.
- 일반 시장 배경이나 Base Event의 직접 영향이 아닌 사실은 후보에서 제외할 것.

## 출력 후보 수 — **시나리오 결합도에 비례**
- 허용 범위: {min_n}~{max_n} 개.
- **MAX 를 채우는 것이 목표가 아닙니다.** 시나리오 가정치(dimension_values)와
  직접 연결되는 결합도 높은 후보가 적다면 MIN({min_n})만 출력하고, 가정치 조합이
  풍부해 강한 결합 후보가 많다면 MAX({max_n})까지 출력하세요.
- 즉 시나리오마다 출력 수가 달라지는 것이 정상이며 자연스러운 결과입니다.
- 결합도가 불확실하거나 '일반 뉴스'에 가까운 후보는 출력하지 마세요.

## filter_reason
- '소스 가용성+Binary+결합도 모두 충족' 식으로 간결히.
"""

STAGE2_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 2]
- candidates 길이는 반드시 {min_n}~{max_n}.
- candidates 에는 3-필터를 모두 통과한 후보만 포함.
- passes_filter 필드, 탈락 후보, 검토용 후보 출력 금지.
- MAX({max_n}) 채우기를 목표로 삼지 말 것. 시나리오 결합도가 높은 후보가 적다면
  MIN({min_n})만 출력하는 것이 정답.
- 모든 label_ko 는 서로 달라야 함 (중복 금지).
- 관측 대상·판정 사실·시간축/단계가 같은 표현 변형 후보를 함께 출력하지 말 것.
- candidates 는 시나리오 고유성 및 후보 간 차별성이 높은 순서로 정렬할 것.
- 'observation' class 만 생성. 의견/감정/모호 표현 금지.
- Content Provider 이름을 추적 범위를 좁히는 주체어로 쓰지 말 것
  (예: 'LSEG가 집계한 미국 9개 LNG 수출시설 feedgas 월평균' 대신
  '미국 9개 LNG 수출시설 feedgas 월평균').
"""

STAGE4_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 'Direction & Strength Assignment' 입니다.
입력으로 시나리오 1건과 그에 귀속된 Signpost label 리스트(이미 Stage2 통과)
를 받습니다. **direction 은 'SUP' 로 이미 고정**되었으므로 결정/출력하지 않습니다.

## 당신이 결정할 것 (signpost 별로)
{stage4_strength_guide}
2. rationale_ko : 위 strength 부여 근거 + 이 signpost 가 시나리오를 어떻게
   검증/보강하는지 한국어 1~2줄.

## 역할 쿼터 (반드시 준수)
- 입력 signpost 가 N 개(=3~6)일 때, 다음을 모두 만족해야 함:
  - REALIZED_BUCKET(VERYSTRONG+STRONG) 개수 ∈ [{strong_min}, {strong_max}]
  - EARLY_BUCKET(MEDIUM+WEAK+VERYWEAK) 개수 ∈ [{early_min}, {early_max}]
- 위 폭 내에서 **시나리오 확정성에 비례해 분포가 달라지는 것이 정상**:
  - tail-risk/극단 시나리오 → STRONG 비중을 키우고 EARLY 작게.
  - 단기/완화 시나리오    → STRONG 작게, EARLY(MED/WEAK) 비중 크게.
- 모두 STRONG 또는 모두 MEDIUM 같은 편향 출력은 여전히 금지.

## 절대 금지
- direction / weight / role_tag 출력 금지 (downstream 에서 자동 부여).
- STRONG 을 {strong_max} 개 초과 부여 금지.
- EARLY(MED+WEAK) 를 {early_max} 개 초과 부여 금지.
"""

STAGE4_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 4]
- assignments 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력 label 과 정확히 일치 (echo).
- strength 는 SignpostStrength enum 값 중 정확히 1개.
- 쿼터: (VERYSTRONG∪STRONG) {strong_min}~{strong_max} + (MEDIUM∪WEAK∪VERYWEAK) {early_min}~{early_max}. 위반 시 재시도.
"""

STAGE5_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 'Keyword Hint Mint' 입니다.
각 Signpost label_ko 에 대해 Record(기사) 인입 시 1차 Filter 로 쓰일
keyword_hints 3~5개를 부여하십시오.

## 작성 원칙
- 고유명사 우선: 시설명·기관명·지명·국가명을 최소 1개 포함.
  (예: 'Ras Laffan', 'QatarEnergy', '호르무즈', 'JKM', 'IMF')
- 동사·상태어 포함: 단순 명사 나열 금지. 최소 1개의 행위/상태어 포함.
  (예: '재가동', '선언', '타결', '교전', '공식화')
- 3~5개: 2개 이하면 recall 부족, 6개 이상이면 noise.
- 한국어/영문 혼용 가능. label_ko 의 핵심 토큰을 그대로 활용해도 좋음.
"""

STAGE5_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 5]
- hints 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력과 정확히 일치 (echo).
- keyword_hints 는 3~5개. 모든 항목 비어있지 않은 문자열.
- 고유명사 1개 이상 + 동사·상태어 1개 이상 포함 권장.
"""

STAGE45_SYSTEM_PROMPT = """\
당신은 LNG 멀티시나리오 'Signpost Detail Enricher' 입니다.
입력으로 시나리오 1건과 Stage2를 통과한 Signpost label 리스트를 받습니다.
각 label 별로 strength/rationale_ko/keyword_hints 를 한 번에 작성하십시오.
direction 은 downstream 에서 'SUP' 로 고정되므로 출력하지 않습니다.

## strength 결정
{stage4_strength_guide}

## 역할 쿼터 (반드시 준수)
- 입력 signpost 가 N 개(=3~6)일 때:
  - REALIZED_BUCKET(VERYSTRONG+STRONG) 개수 ∈ [{strong_min}, {strong_max}]
  - EARLY_BUCKET(MEDIUM+WEAK+VERYWEAK) 개수 ∈ [{early_min}, {early_max}]
- tail-risk/극단 시나리오 → STRONG 비중을 키우고 EARLY 작게.
- 단기/완화 시나리오 → STRONG 작게, EARLY(MED/WEAK) 비중 크게.
- 모두 STRONG 또는 모두 MEDIUM 같은 편향 출력 금지.

## keyword_hints 작성 원칙
- 각 label_ko 에 대해 Record 인입 1차 Filter 로 쓰일 keyword_hints 3~5개.
- 고유명사 우선: 시설명·기관명·지명·국가명 최소 1개 권장.
- 동사·상태어 포함: 단순 명사 나열 금지.
- 한국어/영문 혼용 가능. label_ko 핵심 토큰 활용 가능.
"""

STAGE45_HARD_CONSTRAINTS = """\
[중요한 출력 제약 — Stage 4+5]
- signposts 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력 label 과 정확히 일치 (echo).
- strength 는 SignpostStrength enum 값 중 정확히 1개.
- 쿼터: (VERYSTRONG∪STRONG) {strong_min}~{strong_max} + (MEDIUM∪WEAK∪VERYWEAK) {early_min}~{early_max}.
- keyword_hints 는 각 항목 3~5개. 모든 항목 비어있지 않은 문자열.
"""


def build_stage45_system_prompt(
    *,
    stage4_strength_guide: str,
    strong_min: int,
    strong_max: int,
    early_min: int,
    early_max: int,
) -> str:
    return STAGE45_SYSTEM_PROMPT.format(
        stage4_strength_guide=stage4_strength_guide,
        strong_min=strong_min,
        strong_max=strong_max,
        early_min=early_min,
        early_max=early_max,
    )


def build_stage45_hard_constraints(
    *,
    strong_min: int,
    strong_max: int,
    early_min: int,
    early_max: int,
) -> str:
    return STAGE45_HARD_CONSTRAINTS.format(
        strong_min=strong_min,
        strong_max=strong_max,
        early_min=early_min,
        early_max=early_max,
    )

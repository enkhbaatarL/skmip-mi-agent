"""
Multi-Scenario Generation Pipeline (Stage 1~5 통합)
────────────────────────────────────────────────────
SKT AI Gateway(OpenAI 호환) 기반으로 단일 Base Event(MIEvent) → 5~7개 멀티 시나리오를
Stage 0 스키마(../schemas/state_dict.schema.json) 형태의 단일 상태 객체에 채워 출력함.

관계 구조:
    MIEvent ─(1:1)─> ScenarioGroupState
        ├─ Stage1 Context Pack    (C1 real / C2~C4 stub)
        ├─ Stage2 Dimension       (Template Dim 8 → 3~5개 선택)
        ├─ Stage3 Value Reducer   (각 Dim 5 Enum → 2~4개)
        ├─ Stage4 Synthesis       (Cartesian → Compat → Narrative 5~7건)
        └─ Stage5 Validation      (MECE + 5-tier Likelihood Prior)

가이드라인 준수 (제외 규칙):
    - Stage1: C1만 실제 사용, C2/C3/C4 는 형식적 stub.
    - Stage2: 선택 기준 (b) Historical Analog 분기 사용 금지.
    - Stage3: 선택 규칙 (a) 인접 병합 사용 금지.
    - Stage4: '결과 동일 조합 통합' 룰 사용 금지.
    - Stage5: 'Collective Coverage', 'Likelihood Sum' 검사 제외,
              Prior 는 5단계({very_low|low|medium|high|very_high}) 카테고리.

Template Registry:
    - 이벤트 유형의 level_1_code 에 따라 별도 파일을 사용합니다.
        * level_1='geopolitical_risk'       → template_registry_geopolitical.json
        * level_1='weather_climate'         → template_registry_weather_climate.json
        * level_1='supply_demand_balance'   → template_registry_supply_demand_balance.json
        * level_1='energy_mix_transition'   → template_registry_energy_mix_transition.json
        * level_1='infrastructure_facility' → template_registry_infrastructure.json
      (신규 주제 추가 시 _LEVEL_1_TO_REGISTRY_SUFFIX 매핑에 항목을 추가)
    - 환경변수 REF_TEMPLATE_REGISTRY_PATH 가 지정되면 그 경로(콤마/콜론 다중 가능)를 우선 사용.

Usage:
    SKT_AI_API_KEY=sk-xxx \\
        python stage_integrated_scenario.py \\
            --input  sample_event_ev_2a58da7f4ff2.json \\
            --output stage_result_ev_2a58da7f4ff2.json
"""

import argparse
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Dict, List, Literal, Tuple, Type

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, conlist, model_validator
from _openai_client import get_default_model, get_openai_client, parse_structured_sync

load_dotenv()


# ══════════════════════════════════════════════════════════════
# 1. Env / Constants  (REF_* 접두어, ref_code_style 규칙 #2·#9)
# ══════════════════════════════════════════════════════════════

# [패턴] 모델·토큰·재시도 횟수 등 튜닝 파라미터는 모두 환경변수로 노출.
#         입/출력 경로는 CLI 인자(--input / --output)로 받음.
REF_MODEL: str           = os.getenv("REF_MODEL", get_default_model())
REF_MAX_TOKENS: int      = int(os.getenv("REF_MAX_TOKENS", "8192"))
REF_TEMPERATURE: float   = float(os.getenv("REF_TEMPERATURE", "0.0"))
REF_MAX_RETRIES: int     = int(os.getenv("REF_MAX_RETRIES", "5"))
REF_TARGET_SCENARIOS: int = int(os.getenv("REF_TARGET_SCENARIOS", "6"))   # 5~7 권장
REF_TEMPLATE_REGISTRY_PATH: str = os.getenv("REF_TEMPLATE_REGISTRY_PATH", "")
OPENAI_CLIENT: OpenAI    = get_openai_client()

# event_type.level_1_code → template_registry_<suffix>.json 파일 매핑.
# 신규 level_1 추가 시 본 매핑을 확장하면 자동으로 해당 registry 파일이 라우팅됨.
_LEVEL_1_TO_REGISTRY_SUFFIX: Dict[str, str] = {
    "geopolitical_risk":       "geopolitical",
    "weather_climate":         "weather_climate",
    "supply_demand_balance":   "supply_demand_balance",
    "energy_mix_transition":   "energy_mix_transition",
    "infrastructure_facility": "infrastructure",
}

# Stage 4 PriceDirection / Stage 5 Likelihood 의 허용 카테고리.
PRICE_TIERS: Tuple[str, ...] = (
    "strong_bull", "bull", "mild_bull", "neutral", "mild_bear", "bear", "strong_bear",
)
LIKELIHOOD_TIERS: Tuple[str, ...] = (
    "very_low", "low", "medium", "high", "very_high",
)

PriceTier = Literal[
    "strong_bull", "bull", "mild_bull", "neutral", "mild_bear", "bear", "strong_bear",
]
LikelihoodTier = Literal["very_low", "low", "medium", "high", "very_high"]


# ══════════════════════════════════════════════════════════════
# 2. Template Registry Loader  (template_registry.json)
# ══════════════════════════════════════════════════════════════

def _resolve_template_registry_paths(level_1: str = "") -> List[Path]:
    """우선순위:
        1) 환경변수 REF_TEMPLATE_REGISTRY_PATH (콤마 / os.pathsep 다중 경로)
        2) event_type.level_1_code 매핑(_LEVEL_1_TO_REGISTRY_SUFFIX) 기반 단일 파일
        3) 모듈 디렉터리 'template_registry*.json' 전체 글롭(과거 호환)

    [패턴] 신규 주제 추가 시 _LEVEL_1_TO_REGISTRY_SUFFIX 에 항목을 추가하면
            해당 이벤트 유형이 들어왔을 때 정확히 한 파일만 로드되도록 라우팅됨.
    """
    if REF_TEMPLATE_REGISTRY_PATH:
        items = [
            s.strip()
            for s in REF_TEMPLATE_REGISTRY_PATH.replace(os.pathsep, ",").split(",")
            if s.strip()
        ]
        paths = [Path(s) for s in items]
        for p in paths:
            if not p.exists():
                raise FileNotFoundError(f"REF_TEMPLATE_REGISTRY_PATH 가 가리키는 파일 없음: {p}")
        return paths

    fallback_dir = Path(__file__).parent
    suffix = _LEVEL_1_TO_REGISTRY_SUFFIX.get(level_1, "")
    if suffix:
        routed = fallback_dir / f"template_registry_{suffix}.json"
        if routed.exists():
            return [routed]

    paths = sorted(fallback_dir.glob("template_registry*.json"))
    if not paths:
        raise FileNotFoundError(
            "template_registry*.json 을 찾지 못함. "
            "REF_TEMPLATE_REGISTRY_PATH 환경변수 또는 모듈 디렉터리 배치 필요."
        )
    return paths


def _load_template_registry(level_1: str = "") -> Dict:
    """Template Registry 들을 로드/병합한 dict 반환.

    실패/경계 조건:
        - 동일 키('l1::l2')가 두 파일에 존재 시 명시적 ValueError → 조용한 덮어쓰기 방지.
    """
    paths = _resolve_template_registry_paths(level_1)
    merged: Dict = {}
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "templates" not in data:
            raise ValueError(f"{p}: 'templates' 최상위 키가 필요합니다.")
        for k, v in data["templates"].items():
            if k in merged:
                raise ValueError(f"중복 템플릿 키 '{k}' (파일: {p})")
            merged[k] = v
    return merged


def _resolve_template(event_type_l1_l2: str) -> Dict:
    """event_type_l1_l2('l1::l2') 키로 템플릿을 조회. 누락 시 명시적 에러.

    level_1 으로부터 적절한 registry 파일을 라우팅해서 그때그때 로드한다.
    (이전 버전은 모듈 import 시점에 모든 registry 를 병합 로드했음.)
    """
    level_1 = event_type_l1_l2.split("::", 1)[0].strip() if event_type_l1_l2 else ""
    registry = _load_template_registry(level_1)
    tmpl = registry.get(event_type_l1_l2)
    if tmpl is None:
        available = ", ".join(sorted(registry.keys()))
        raise KeyError(
            f"template_registry 에 '{event_type_l1_l2}' 키 없음. 사용 가능: [{available}]"
        )
    return tmpl


def _dim_index(template: Dict) -> Dict[str, Dict]:
    """dimension_id -> dimension dict 인덱스."""
    return {d["dimension_id"]: d for d in template["dimensions"]}


def _enum_id_set(dimension: Dict) -> List[str]:
    return [e["id"] for e in dimension["enum"]]


def _tail_id_set(dimension: Dict) -> List[str]:
    return [e["id"] for e in dimension["enum"] if e.get("tail")]


# ══════════════════════════════════════════════════════════════
# 3. Pydantic Models  (../schemas/state_dict.schema.json 정합)
# ══════════════════════════════════════════════════════════════

# --- Stage 1 ---
class C1BaseEvent(BaseModel):
    """Stage1 — 단일 Base Event 요약 (state.stage1_context_pack.C1_base_event)."""
    event_id: str = Field(default="", description="MIEvent 고유 ID (mi_event_id)")
    title: str = Field(default="", description="이벤트 한글 제목")
    event_type_l1_l2: str = Field(default="", description="'l1_code::l2_code' 형태")
    summary: str = Field(default="", description="이벤트 한 줄 요약 (one_line_summary)")
    driver: str = Field(default="", description="핵심 드라이버 (자유 서술)")


class C2LinkedRecords(BaseModel):
    window_days: int = Field(default=30, description="연관 Record 조회 시간창 (일)")
    records: List[Dict] = Field(default_factory=list, description="연관 Record 요약 리스트(stub)")


class C3HistoricalAnalog(BaseModel):
    analog_event_id: str = Field(default="", description="과거 유사 이벤트 ID")
    trajectory: List[str] = Field(default_factory=list, description="전개 단계 라벨 시퀀스")


class Stage1ContextPack(BaseModel):
    """Stage1 — 4개 Context 컨테이너."""
    C1_base_event: C1BaseEvent = Field(description="필수 — 단일 Base Event")
    C2_linked_records: C2LinkedRecords = Field(
        default_factory=C2LinkedRecords,
        description="형식적 stub — 실제 구현은 본 파이프라인 범위 밖.",
    )
    C3_historical_analogs: List[C3HistoricalAnalog] = Field(
        default_factory=list,
        description="형식적 stub — RAG 미연결.",
    )
    C4_related_events: List[Dict] = Field(
        default_factory=list,
        description="형식적 stub — Graph 미연결.",
    )


# --- Stage 2 ---
class SelectedDimension(BaseModel):
    dimension_id: str = Field(description="템플릿의 dimension_id")
    rationale: str = Field(
        description=(
            "선택 근거. 반드시 '(a)' 또는 '(c)' 또는 '(a)(c)' 코드로 시작하고, "
            "한국어 근거문을 1줄로 부연. 예: '(a)(c) 본문에 호르무즈 봉쇄 직접 언급 + Driver Tree 통항 경로 핵심.'"
        )
    )


class ExcludedDimension(BaseModel):
    dimension_id: str = Field(description="제외된 템플릿 dimension_id")
    reason: str = Field(description="제외 사유 한국어 1줄.")


class Stage2DimensionSelection(BaseModel):
    template_id: str = Field(description="event_type_l1_l2 형태의 템플릿 키")
    template_dimensions_total: int = Field(description="템플릿 전체 Dim 수 (보통 8)")
    # ref 규칙 #4: conlist 에는 type-ignore 주석.
    selected_dimensions: conlist(SelectedDimension, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description="선택된 Dim 3~5개. (b) 기준 사용 금지.",
    )
    excluded_dimensions: List[ExcludedDimension] = Field(
        default_factory=list,
        description="선택되지 않은 Dim + 사유.",
    )


# --- Stage 3 ---
class PerDimensionValue(BaseModel):
    dimension_id: str = Field(description="템플릿의 dimension_id")
    template_enum_full: List[str] = Field(
        default_factory=list,
        description="해당 Dim 의 원본 5단계 Enum ID 전체.",
    )
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택한 Enum ID 2~4개. 인접 병합(=영향 유사 통합) 금지.",
    )
    tail_risk_kept: str = Field(
        default="",
        description="Tail Risk 로 보존된 Enum ID 1개 이상 (selected_enum 내 포함).",
    )


class Stage3ValueSelection(BaseModel):
    per_dimension: List[PerDimensionValue] = Field(
        default_factory=list,
        description="Dim 별 Value 축소 결과 리스트.",
    )


# --- Stage 4 ---
class PriceDirection(BaseModel):
    brent: PriceTier = Field(description="Brent 방향성 7단계")
    jkm: PriceTier   = Field(description="JKM 방향성 7단계")
    ttf: PriceTier   = Field(description="TTF 방향성 7단계")


class Scenario(BaseModel):
    scenario_id: str = Field(description="S_01 형태")
    title: str = Field(description="시장 참여자 관점 한 줄 요약 (예: '1개월 내 정상화')")
    dimension_values: Dict[str, str] = Field(
        description="dim_id -> enum_id 의 1:1 매핑.",
    )
    description: str = Field(
        description="3~5줄. 주요 Dim 가정치 조합 + 전개 양상 서술.",
    )
    derivation_rationale: str = Field(
        description="이 시나리오를 도출한 근거 (어떤 Dim 조합·맥락 단서로부터 왔는지).",
    )
    price_direction: PriceDirection = Field(description="Brent/JKM/TTF 7단계 방향성.")
    compatibility_passed: bool = Field(
        default=True,
        description="Compat Rule 통과 여부 (출력 시점 항상 True).",
    )


class Stage4ScenarioSynthesis(BaseModel):
    cartesian_total: int = Field(description="Stage3 결과 기준 Dim Cartesian 조합 수.")
    filtered_by_compatibility: int = Field(
        description="Compat Rule 통과 후 남은 조합 수 (cartesian_total 이하).",
    )
    scenarios: conlist(Scenario, min_length=1, max_length=10) = Field(  # type: ignore[valid-type]
        description="최종 시나리오 5~7건 권장.",
    )


# --- Stage 5 ---
class MECECheck(BaseModel):
    mutually_exclusive: bool = Field(
        description="시나리오 간 동시 성립 사례 부재 시 True.",
    )


class Stage5Validation(BaseModel):
    mece_check: MECECheck = Field(default_factory=lambda: MECECheck(mutually_exclusive=True))
    likelihood_prior: Dict[str, LikelihoodTier] = Field(
        default_factory=dict,
        description="scenario_id -> 5단계 카테고리. 수치 Prior 금지.",
    )


# --- Root ---
class ScenarioGroupState(BaseModel):
    """Stage 1~5 단일 상태 객체 (../schemas/state_dict.schema.json 의 root)."""
    scenario_group_id: str = Field(description="sg_<slug>_<yyyy_mm_dd> 형태")
    created_at: str = Field(description="ISO-8601 UTC")
    stage1_context_pack: Stage1ContextPack
    stage2_dimension_selection: Stage2DimensionSelection
    stage3_value_selection: Stage3ValueSelection
    stage4_scenario_synthesis: Stage4ScenarioSynthesis
    stage5_validation: Stage5Validation


# --- LLM 출력 전용 (state 미직접 매핑) ---
class _Stage2LLMOutput(BaseModel):
    selected_dimensions: conlist(SelectedDimension, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description="선택된 Dim 3~5개.",
    )
    excluded_dimensions: List[ExcludedDimension] = Field(
        default_factory=list,
        description="제외된 Dim 목록.",
    )

    @model_validator(mode="after")
    def _validate_no_dup(self):
        sel = {d.dimension_id for d in self.selected_dimensions}
        exc = {d.dimension_id for d in self.excluded_dimensions}
        if sel & exc:
            raise ValueError(
                f"selected_dimensions 와 excluded_dimensions 가 중복: {sel & exc}"
            )
        return self


class _Stage3SingleDimOutput(BaseModel):
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택 enum_id 2~4개. 반드시 template_enum_full 의 부분집합.",
    )
    tail_risk_kept: str = Field(
        description="유지된 Tail Risk enum_id (selected_enum 안에 포함).",
    )


class _NarrativeOnly(BaseModel):
    title: str = Field(description="시장 참여자 관점 한 줄 요약")
    description: str = Field(description="3~5줄 시나리오 서술")
    derivation_rationale: str = Field(description="도출 근거")
    price_direction: PriceDirection


class _Stage4LLMOutput(BaseModel):
    narratives: List[_NarrativeOnly] = Field(
        description="입력된 dim 조합 순서와 1:1 동일 길이.",
    )


class _Stage5LLMOutput(BaseModel):
    class LikelihoodPriorItem(BaseModel):
        scenario_id: str = Field(description="scenario_id (예: S_01)")
        prior: LikelihoodTier = Field(description="5단계 Prior 카테고리")

    mutually_exclusive: bool = Field(description="MECE 동시성립 부재 여부")
    rationale: str = Field(description="MECE 판정 근거 1~2줄")
    likelihood_prior: List[LikelihoodPriorItem] = Field(
        description="시나리오별 5단계 Prior 목록",
    )


# ══════════════════════════════════════════════════════════════
# 4. Stage 1  —  Context Retriever (C1 real / C2~C4 stub)
# ══════════════════════════════════════════════════════════════
#
# [패턴] 가이드라인상 멀티시나리오 생성에 실제 사용되는 Context 는 C1 단일 Base
#         Event 만이며, C2~C4 는 구조 정합성을 위한 형식적 stub 으로만 채움.
#         실제 Retrieval 구현은 본 파이프라인 범위 밖이므로 ref_code_style 규칙
#         #2 에 따라 "### 생략" 표식을 남김.

def _build_c1_base_event(event: Dict) -> C1BaseEvent:
    """단일 Base Event JSON 으로부터 C1 슬롯을 채움.

    실패/경계 조건:
        - event_type 누락 시 빈 문자열로 채워 후속 Stage 에서 명시적 KeyError 가
          나도록 유도(조용한 실패 방지).
    """
    et = event.get("event_type", {}) or {}
    l1 = et.get("level_1_code", "")
    l2 = et.get("level_2_code", "")
    et_key = f"{l1}::{l2}" if l1 and l2 else ""

    return C1BaseEvent(
        event_id=event.get("mi_event_id", ""),
        title=event.get("event_title_ko", ""),
        event_type_l1_l2=et_key,
        summary=event.get("one_line_summary", ""),
        driver=_extract_driver_hint(event),
    )


def _extract_driver_hint(event: Dict) -> str:
    """Driver 힌트 — detail_analysis 첫 문장 또는 첫 key_bullet 으로 대체.

    LLM 호출 없이도 의미있는 '핵심 드라이버 한 줄' 을 채우기 위한 발견적 처리.
    """
    bullets = event.get("key_bullets") or []
    if bullets:
        first = str(bullets[0]).strip()
        return first[:160]
    detail = str(event.get("detail_analysis", "")).strip()
    if not detail:
        return ""
    head = detail.split(".")[0].strip()
    return head[:160]


def _build_c2_linked_records_stub() -> C2LinkedRecords:
    # ### 생략: 본 파이프라인은 단일 Base Event 만 사용하므로 Linked Record DB 조회는 미구현.
    return C2LinkedRecords(window_days=30, records=[])


def _build_c3_historical_analogs_stub() -> List[C3HistoricalAnalog]:
    # ### 생략: 과거 기사 RAG 인덱스 미연결. Stage2 에서도 (b) Historical Analog
    #          기준은 사용 금지이므로 본 stub 으로 충분.
    return []


def _build_c4_related_events_stub() -> List[Dict]:
    # ### 생략: Region/Actor 기반 Graph 탐색 미연결.
    return []


def stage1_build_context_pack(event: Dict) -> Stage1ContextPack:
    """Stage 1 진입점 — Single Base Event → Stage1ContextPack."""
    return Stage1ContextPack(
        C1_base_event=_build_c1_base_event(event),
        C2_linked_records=_build_c2_linked_records_stub(),
        C3_historical_analogs=_build_c3_historical_analogs_stub(),
        C4_related_events=_build_c4_related_events_stub(),
    )


# ══════════════════════════════════════════════════════════════
# 5. Stage 2  —  Dimension Selector  (Prompt + LLM Chain + Logger)
# ══════════════════════════════════════════════════════════════

# [패턴] SYSTEM / USER / HARD_CONSTRAINTS 3분할 (ref 규칙 #5).
#         HARD_CONSTRAINTS 는 재시도 시 누적 주입.

STAGE2_SYSTEM = """\
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

STAGE2_USER = """\
## Base Event
- event_id: {event_id}
- title: {title}
- event_type_l1_l2: {event_type_l1_l2}
- summary: {summary}
- driver: {driver}
- detail_analysis(요약): {detail_excerpt}

## Template (event_type_l1_l2 = {event_type_l1_l2})
- template_dimensions_total: {template_dimensions_total}
- dimensions: 아래 리스트의 dimension_id 만 선택 가능.
{dimensions_block}

## 산출 규칙
- 선택 Dim: 3~5개.
- 모든 미선택 Dim 은 excluded_dimensions 에 사유와 함께 기재.
"""

STAGE2_HARD = """\

[중요한 출력 제약 — Stage 2]
- selected_dimensions 길이는 반드시 3~5.
- 모든 dimension_id 는 입력된 Template 의 dimension_id 안에 있어야 함.
- selected ∪ excluded = template 전체 Dim 집합 (누락 금지, 중복 금지).
- rationale 은 (a) / (c) / (a)(c) 중 하나로 시작. (b) 코드 포함 금지.
"""

def _format_dimensions_block(template: Dict) -> str:
    lines: List[str] = []
    for d in template["dimensions"]:
        enum_ids = ", ".join(_enum_id_set(d))
        lines.append(
            f"- {d['dimension_id']} ({d.get('label_ko','')}): enum=[{enum_ids}] / {d.get('description','')}"
        )
    return "\n".join(lines)


def stage2_select_dimensions(
    pack: Stage1ContextPack,
    event: Dict,
    template: Dict,
) -> Stage2DimensionSelection:
    """Stage 2 진입점 — 8개 Dim 중 3~5개 선택."""
    base_user = {
        "event_id": pack.C1_base_event.event_id,
        "title": pack.C1_base_event.title,
        "event_type_l1_l2": pack.C1_base_event.event_type_l1_l2,
        "summary": pack.C1_base_event.summary,
        "driver": pack.C1_base_event.driver,
        "detail_excerpt": _shorten(event.get("detail_analysis", ""), 600),
        "template_dimensions_total": template["template_dimensions_total"],
        "dimensions_block": _format_dimensions_block(template),
    }
    template_dim_ids = [d["dimension_id"] for d in template["dimensions"]]

    def _validate(out: _Stage2LLMOutput) -> None:
        sel_ids = {d.dimension_id for d in out.selected_dimensions}
        exc_ids = {d.dimension_id for d in out.excluded_dimensions}
        unknown = (sel_ids | exc_ids) - set(template_dim_ids)
        if unknown:
            raise ValueError(f"Template 외 dimension_id 사용: {unknown}")
        # rationale (b) 차단 — 점진적 후처리(완전한 enum 검증은 LLM 측 협조).
        for d in out.selected_dimensions:
            if "(b)" in d.rationale:
                raise ValueError(f"(b) 기준 rationale 검출: {d.dimension_id}")

    out = _invoke_with_retry(
        stage="Stage 2",
        base_payload=base_user,
        hard_constraints=STAGE2_HARD,
        validate_fn=_validate,
        response_model=_Stage2LLMOutput,
    )

    if out is None:
        out = _stage2_fallback(template_dim_ids, template)

    # excluded 보강: LLM 이 빠뜨린 미선택 Dim 자동 채움(누락 방지).
    sel_ids = {d.dimension_id for d in out.selected_dimensions}
    given_exc_ids = {d.dimension_id for d in out.excluded_dimensions}
    auto_excluded = [
        ExcludedDimension(dimension_id=did, reason="LLM 미언급 — 자동 제외 처리")
        for did in template_dim_ids
        if did not in sel_ids and did not in given_exc_ids
    ]
    excluded = list(out.excluded_dimensions) + auto_excluded

    return Stage2DimensionSelection(
        template_id=pack.C1_base_event.event_type_l1_l2,
        template_dimensions_total=template["template_dimensions_total"],
        selected_dimensions=out.selected_dimensions,
        excluded_dimensions=excluded,
    )


def _stage2_fallback(template_dim_ids: List[str], template: Dict) -> _Stage2LLMOutput:
    """LLM 실패 시 — 템플릿 앞 4개 Dim 을 (a) 코드로 안전 채택."""
    print("  ↳ Stage 2 fallback: 템플릿 앞 4개 Dim 안전 선택")
    selected = [
        SelectedDimension(
            dimension_id=did,
            rationale="(a) Fallback 안전 선택 — Base Event 와 잠재적 관련성 가정.",
        )
        for did in template_dim_ids[:4]
    ]
    excluded = [
        ExcludedDimension(dimension_id=did, reason="Fallback 자동 제외")
        for did in template_dim_ids[4:]
    ]
    return _Stage2LLMOutput(selected_dimensions=selected, excluded_dimensions=excluded)


# ══════════════════════════════════════════════════════════════
# 6. Stage 3  —  Value Reducer  (Tail 보존 / 인접 병합 금지)
# ══════════════════════════════════════════════════════════════

STAGE3_SYSTEM = """\
당신은 멀티시나리오 생성을 위한 'Value Reducer' 입니다.
하나의 Dimension 의 5단계 Enum 중에서 **2~4개만** 채택하십시오.

## 선택 규칙 (반드시 준수)
- (b) 극단 보존: Tail Risk(=template 정의상 tail=true) 중 **최소 1개** 를 selected_enum 안에 포함.
- (c) 최종 수: 2~4개.

## 절대 금지
- (a) 인접 병합(시장 영향이 유사하다는 이유로 인접 Enum 을 합쳐 1개로 대체) **사용 금지**.
  → '인접 영향 유사', '비슷한 강도여서 통합' 같은 사유로 인접 Enum 을 한꺼번에 제거하지 말 것.
- 입력 template_enum_full 외의 enum_id 사용 금지.

## "영향 없음(none)" 류 enum 채택 가이드
- Base Event 가 이미 발생·진행 중이고 해당 Dim 영역에서 영향이 관측되고 있다면,
  '영향 없음/정상(보통 enum_id='none')' 류 enum 은 **원칙적으로 selected_enum 에서 제외**하십시오.
  → 예: 본 이벤트가 '호르무즈 45일째 봉쇄' 라면 strait_shipping_impact='none' 채택 금지.
- 단, 해당 Dim 이 '단기 종전 후 정상화 baseline' 시나리오 분기를 위해 꼭 필요할 때만
  예외적으로 채택하고, rationale 성격(=baseline 표현 의도)을 description 에 명시하십시오.

## tail_risk_kept
- selected_enum 에 포함된 enum_id 중 tail=true 인 1개를 명시.
"""

STAGE3_USER = """\
## Base Event 요약
- title: {title}
- summary: {summary}
- driver: {driver}

## Dimension 정보
- dimension_id: {dimension_id}
- label_ko: {label_ko}
- description: {description}
- template_enum_full: {enum_full_block}
- tail enum 후보: {tail_block}

## 산출
- 채택 enum_id 2~4개 + tail_risk_kept 1개.
"""

STAGE3_HARD = """\

[중요한 출력 제약 — Stage 3]
- selected_enum 길이는 반드시 2~4.
- 모든 enum_id 는 입력된 template_enum_full 안에 있어야 함.
- tail_risk_kept 는 selected_enum 안의 값이며, tail=true 인 enum 이어야 함.
- 인접 병합 사유로 Enum 제거 금지.
"""

def stage3_reduce_values(
    pack: Stage1ContextPack,
    selected: Stage2DimensionSelection,
    template: Dict,
) -> Stage3ValueSelection:
    """Stage 3 진입점 — 선택된 Dim 별로 LLM 호출하여 Enum 축소."""
    dim_idx = _dim_index(template)

    per_dim: List[PerDimensionValue] = []
    for sd in selected.selected_dimensions:
        dim = dim_idx.get(sd.dimension_id)
        if dim is None:
            print(f"  ↳ 경고: Stage3 — '{sd.dimension_id}' 템플릿 누락. 스킵.")
            continue
        enum_full = _enum_id_set(dim)
        tail_full = _tail_id_set(dim)

        base_user = {
            "title": pack.C1_base_event.title,
            "summary": pack.C1_base_event.summary,
            "driver": pack.C1_base_event.driver,
            "dimension_id": dim["dimension_id"],
            "label_ko": dim.get("label_ko", ""),
            "description": dim.get("description", ""),
            "enum_full_block": ", ".join(
                f"{e['id']}({e.get('label','')}, tail={'Y' if e.get('tail') else 'N'})"
                for e in dim["enum"]
            ),
            "tail_block": ", ".join(tail_full) if tail_full else "(없음)",
        }

        def _validate(out: _Stage3SingleDimOutput) -> None:
            unknown = set(out.selected_enum) - set(enum_full)
            if unknown:
                raise ValueError(f"template_enum_full 외 enum_id 사용: {unknown}")
            if out.tail_risk_kept not in out.selected_enum:
                raise ValueError("tail_risk_kept 가 selected_enum 안에 없음.")
            if tail_full and out.tail_risk_kept not in tail_full:
                raise ValueError(
                    f"tail_risk_kept='{out.tail_risk_kept}' 가 tail enum 집합에 없음. "
                    f"tail 후보: {tail_full}"
                )

        out = _invoke_with_retry(
            stage=f"Stage 3 [{dim['dimension_id']}]",
            base_payload=base_user,
            hard_constraints=STAGE3_HARD,
            validate_fn=_validate,
            response_model=_Stage3SingleDimOutput,
        )

        if out is None:
            out = _stage3_fallback(dim)

        per_dim.append(PerDimensionValue(
            dimension_id=dim["dimension_id"],
            template_enum_full=enum_full,
            selected_enum=out.selected_enum,
            tail_risk_kept=out.tail_risk_kept,
        ))

    return Stage3ValueSelection(per_dimension=per_dim)


def _stage3_fallback(dim: Dict) -> _Stage3SingleDimOutput:
    """LLM 실패 시 — 첫 1개 + 중간 1개 + Tail 1개 안전 채택."""
    print(f"  ↳ Stage 3 fallback ({dim['dimension_id']}): 안전 3개 Enum 선택")
    enum_full = _enum_id_set(dim)
    tail_full = _tail_id_set(dim)
    tail_pick = tail_full[0] if tail_full else enum_full[-1]
    base = enum_full[0]
    mid = enum_full[len(enum_full) // 2] if len(enum_full) >= 2 else enum_full[0]
    selected = []
    for cand in (base, mid, tail_pick):
        if cand and cand not in selected:
            selected.append(cand)
    while len(selected) < 2 and enum_full:
        for cand in enum_full:
            if cand not in selected:
                selected.append(cand)
                break
        else:
            break
    return _Stage3SingleDimOutput(selected_enum=selected[:4], tail_risk_kept=tail_pick)


# ══════════════════════════════════════════════════════════════
# 7. Stage 4  —  Compatibility Rule Engine + Narrative Writer
# ══════════════════════════════════════════════════════════════

# [패턴] '결과 동일 조합 통합' 규칙은 사용하지 않음.
#         물리적 모순 / 강도 모순 / 극단 보존만 적용.

def _cartesian_combos(stage3: Stage3ValueSelection) -> List[Dict[str, str]]:
    """Stage3 결과를 Dim×Enum Cartesian 으로 펼침."""
    dim_ids = [pd.dimension_id for pd in stage3.per_dimension]
    enum_lists = [list(pd.selected_enum) for pd in stage3.per_dimension]
    combos: List[Dict[str, str]] = []
    for tup in product(*enum_lists):
        combos.append({did: eid for did, eid in zip(dim_ids, tup)})
    return combos


def _apply_compat_rules(
    combos: List[Dict[str, str]],
    template: Dict,
) -> Tuple[List[Dict[str, str]], List[Tuple[Dict[str, str], str]]]:
    """Compatibility Rule Engine — 통과/탈락 분리.

    forbid 정의: 모든 forbid 키의 값이 forbid 리스트 안에 들어있으면 탈락.
    """
    rules = template.get("compatibility_rules", []) or []
    passed: List[Dict[str, str]] = []
    rejected: List[Tuple[Dict[str, str], str]] = []
    for combo in combos:
        violated_rule: str | None = None
        for rule in rules:
            forbid: Dict[str, List[str]] = rule.get("forbid", {})
            if not forbid:
                continue
            hit = True
            for k, vals in forbid.items():
                if combo.get(k) not in vals:
                    hit = False
                    break
            if hit:
                violated_rule = rule.get("rule_id", "UNKNOWN")
                break
        if violated_rule is None:
            passed.append(combo)
        else:
            rejected.append((combo, violated_rule))
    return passed, rejected


def _select_target_combos(
    passed: List[Dict[str, str]],
    stage3: Stage3ValueSelection,
    target_n: int,
    template: Dict,
) -> List[Dict[str, str]]:
    """Compat 통과 조합 중 5~7개 추출 — Base/Extreme 앵커 + Farthest-First 다양성.

    [패턴] 선정 기준 (사용자에게 설명 가능한 명시적 근거):
        1) Tail score = combo 내 enum_id 중 template.enum.tail=true 인 개수.
           → tail_risk_kept(=Stage3 산출) 1개로 제한된 기존 점수의 약점 해소.
        2) Base anchor(score 최소): 가장 baseline 에 가까운 1건.
        3) Extreme anchor(score 최대): 가장 tail 쪽 1건 (Base 와 Hamming 최대).
        4) 나머지 슬롯: 이미 선택된 anchor 들과의 Hamming 거리 최소값을 최대화하는
           Farthest-First 탐색으로 다양성 확보.
    실패/경계 조건:
        - passed ≤ target_n 이면 그대로 반환.
        - 모든 combo 가 동일 tail_score 이면 farthest-first 가 자연스럽게 분산.
    """
    if len(passed) <= target_n:
        return list(passed)

    dim_idx = _dim_index(template)
    template_tail: Dict[str, set] = {
        pd.dimension_id: set(
            e["id"] for e in dim_idx.get(pd.dimension_id, {}).get("enum", [])
            if e.get("tail")
        )
        for pd in stage3.per_dimension
    }

    def _tail_score(combo: Dict[str, str]) -> int:
        return sum(
            1 for did, eid in combo.items() if eid in template_tail.get(did, set())
        )

    def _hamming(a: Dict[str, str], b: Dict[str, str]) -> int:
        return sum(1 for k in a if a.get(k) != b.get(k))

    def _farthest_idx(pool_idx: List[int], anchors: List[int]) -> int:
        """Farthest-first: anchor 들과의 최소거리가 최대가 되는 후보 인덱스."""
        best_i, best_d = pool_idx[0], -1
        for i in pool_idx:
            d_min = min(_hamming(passed[i], passed[a]) for a in anchors)
            if d_min > best_d:
                best_i, best_d = i, d_min
        return best_i

    scores = [_tail_score(c) for c in passed]
    min_s, max_s = min(scores), max(scores)
    base_idx = next(i for i, s in enumerate(scores) if s == min_s)

    chosen_idx: List[int] = [base_idx]

    if max_s != min_s:
        ext_pool = [i for i, s in enumerate(scores) if s == max_s]
        chosen_idx.append(_farthest_idx(ext_pool, chosen_idx))

    pool = [i for i in range(len(passed)) if i not in chosen_idx]
    while len(chosen_idx) < target_n and pool:
        nxt = _farthest_idx(pool, chosen_idx)
        chosen_idx.append(nxt)
        pool.remove(nxt)

    return [passed[i] for i in chosen_idx[:target_n]]


STAGE4_SYSTEM = """\
당신은 LNG 멀티시나리오 'Narrative Writer' 입니다.
이미 Compatibility Rule 을 통과한 'Dim 조합' 리스트를 입력받아, 각 조합에 대해
시장 참여자 관점의 시나리오 서사를 작성하십시오.

## 작성 가이드라인 (반드시 준수)
- title (1줄): 시장 참여자 관점의 한 줄 요약. 예: '1개월 내 정상화'.
- description (3~5줄): 각 시나리오의 가정치 조합(=주요 Dim 값) + 전개 양상.
- derivation_rationale: 이 시나리오가 왜 도출되는지 — 어떤 Dim 조합·맥락 단서로부터 왔는지.
- price_direction.brent / jkm / ttf: 7단계({{strong_bull|bull|mild_bull|neutral|mild_bear|bear|strong_bear}}) 중 1개.

## 절대 금지
- '결과(가격 방향)가 동일하므로 두 조합을 합쳐서 1개로 만든다' 같은 통합/생략 행위.
  → 입력으로 들어온 조합 개수와 출력 narratives 개수는 **반드시 일치**.
"""

STAGE4_USER = """\
## Base Event
- title: {title}
- summary: {summary}
- driver: {driver}

## Dimension 라벨 (참고)
{dim_label_block}

## 작성 대상 조합 ({n_combos}개)  — 입력 순서를 그대로 유지하여 narratives 출력
{combos_block}

## 산출 규칙
- narratives 길이 = {n_combos}.
- 각 narrative 의 description 은 3~5줄.
- title 은 한 줄.
"""

STAGE4_HARD = """\

[중요한 출력 제약 — Stage 4]
- narratives 길이는 입력 조합 수와 정확히 일치.
- price_direction.brent / jkm / ttf 는 반드시 7단계 enum 중 정확히 1개.
- description 은 3~5줄, title 은 1줄.
- '결과 동일 조합 통합' 금지 — 출력 길이를 줄이지 마십시오.
"""

def stage4_synthesize_scenarios(
    pack: Stage1ContextPack,
    stage3: Stage3ValueSelection,
    template: Dict,
) -> Stage4ScenarioSynthesis:
    """Stage 4 진입점 — Cartesian → Compat → 5~7건 선정 → Narrative LLM."""
    combos_all = _cartesian_combos(stage3)
    passed, rejected = _apply_compat_rules(combos_all, template)
    print(
        f"  ▸ Stage 4 — cartesian={len(combos_all)} / compat_passed={len(passed)} / "
        f"rejected={len(rejected)}"
    )
    for combo, rule in rejected[:5]:
        print(f"    - reject ({rule}): {combo}")

    target = _select_target_combos(passed, stage3, REF_TARGET_SCENARIOS, template)
    if not target:
        print("  ↳ 경고: Compat 통과 조합 0건 — Cartesian 전체 중 1건 강제 채택.")
        target = combos_all[:1] or [{}]

    dim_idx = _dim_index(template)
    dim_label_block = "\n".join(
        f"- {pd.dimension_id} ({dim_idx.get(pd.dimension_id,{}).get('label_ko','')})"
        for pd in stage3.per_dimension
    )
    combos_block = "\n".join(
        f"  [{i+1}] " + ", ".join(f"{k}={v}" for k, v in combo.items())
        for i, combo in enumerate(target)
    )

    base_user = {
        "title": pack.C1_base_event.title,
        "summary": pack.C1_base_event.summary,
        "driver": pack.C1_base_event.driver,
        "dim_label_block": dim_label_block,
        "n_combos": len(target),
        "combos_block": combos_block,
    }

    def _validate(out: _Stage4LLMOutput) -> None:
        if len(out.narratives) != len(target):
            raise ValueError(
                f"narratives 길이 불일치: {len(out.narratives)} != {len(target)}"
            )
        for n in out.narratives:
            for v in (n.price_direction.brent, n.price_direction.jkm, n.price_direction.ttf):
                if v not in PRICE_TIERS:
                    raise ValueError(f"price_direction 범위 밖 값: {v}")

    out = _invoke_with_retry(
        stage="Stage 4",
        base_payload=base_user,
        hard_constraints=STAGE4_HARD,
        validate_fn=_validate,
        response_model=_Stage4LLMOutput,
    )

    if out is None:
        out = _stage4_fallback(target)

    scenarios: List[Scenario] = []
    for i, (combo, narr) in enumerate(zip(target, out.narratives), start=1):
        scenarios.append(Scenario(
            scenario_id=f"S_{i:02d}",
            title=narr.title,
            dimension_values=combo,
            description=narr.description,
            derivation_rationale=narr.derivation_rationale,
            price_direction=narr.price_direction,
            compatibility_passed=True,
        ))

    return Stage4ScenarioSynthesis(
        cartesian_total=len(combos_all),
        filtered_by_compatibility=len(passed),
        scenarios=scenarios,
    )


def _stage4_fallback(target: List[Dict[str, str]]) -> _Stage4LLMOutput:
    """LLM 실패 시 — 모든 조합에 대해 중립 시나리오 narrative 생성."""
    print(f"  ↳ Stage 4 fallback: {len(target)}개 중립 narrative 생성")
    narratives = [
        _NarrativeOnly(
            title=f"[Fallback] 조합 #{i+1} 시나리오",
            description=(
                "LLM 호출 실패로 fallback 서사가 적용됨.\n"
                f"가정치 조합: {', '.join(f'{k}={v}' for k,v in combo.items())}\n"
                "전개 양상 판단 보류 — 후속 재실행 필요."
            ),
            derivation_rationale="LLM 실패 — 안전 기본값.",
            price_direction=PriceDirection(brent="neutral", jkm="neutral", ttf="neutral"),
        )
        for i, combo in enumerate(target)
    ]
    return _Stage4LLMOutput(narratives=narratives)


# ══════════════════════════════════════════════════════════════
# 8. Stage 5  —  MECE Validator + 5-tier Likelihood Calibrator
# ══════════════════════════════════════════════════════════════

STAGE5_SYSTEM = """\
당신은 멀티시나리오 'MECE Validator + Likelihood Calibrator' 입니다.

## 검사 항목 (반드시 이 둘만)
1. mutually_exclusive (M): 동일 시점에 정확히 한 시나리오만 참이 될 수 있는가?
   - 본 파이프라인의 시나리오는 모두 (dimension_id → enum_id) 단일 조합으로 정의됨.
   - 따라서 두 시나리오의 dimension_values 가 **하나라도 서로 다르면** 정의상 동시 성립 불가 → True.
   - 모든 시나리오의 dimension_values 조합이 서로 유일하면 True.
   - 동일한 dimension_values 조합을 가진 시나리오 쌍이 있을 때만 False.
   - narrative(서술 톤·결과 가격 방향)가 비슷하다는 이유로 False 를 반환하지 마십시오.
2. likelihood_prior: 각 시나리오마다 발생 가능성을 5단계 카테고리로 부여.
   {{very_low, low, medium, high, very_high}} 중 정확히 1개.

## 절대 금지
- 'Collective Coverage(≥80%)' 검사 금지.
- 'Likelihood Sum = 1.0' 검사/수치 정규화 금지.
- 수치 Prior(예: 0.4, 40%) 출력 금지 — 반드시 5단계 카테고리만.

## Prior 부여 가이드 (참고)
- Tail Risk(시설 영구 손상·전면 봉쇄 등 극단)는 통상 'low' 또는 'very_low'.
- Base case 성격(완화·정상화)은 'medium' 또는 'high'.
- 시장 충격 강한 중기 차질은 'medium' 부근.
"""

STAGE5_USER = """\
## Base Event 요약
- title: {title}
- summary: {summary}

## 시나리오 목록 ({n_scenarios}건)
{scenarios_block}

## 산출
- mutually_exclusive (bool) + rationale (1~2줄).
- likelihood_prior: [{{"scenario_id":"S_01","prior":"medium"}}, ...] 형태.
- 모든 scenario_id 를 1회씩만 포함.
"""

STAGE5_HARD = """\

[중요한 출력 제약 — Stage 5]
- likelihood_prior 는 scenario_id/prior 객체의 배열.
- scenario_id 집합은 입력된 scenario_id 와 정확히 일치 (누락·여분·중복 금지).
- prior 값은 {{very_low|low|medium|high|very_high}} 중 정확히 1개.
- 수치 출력 금지. Coverage·Sum 검사 금지.
"""

def stage5_validate(
    pack: Stage1ContextPack,
    stage4: Stage4ScenarioSynthesis,
) -> Stage5Validation:
    """Stage 5 진입점 — MECE 통과 여부 + 5단계 Prior 부여."""
    sc_ids = [s.scenario_id for s in stage4.scenarios]
    scenarios_block = "\n".join(
        f"- {s.scenario_id} | {s.title}\n"
        f"    dims: {', '.join(f'{k}={v}' for k,v in s.dimension_values.items())}\n"
        f"    price: brent={s.price_direction.brent}, jkm={s.price_direction.jkm}, ttf={s.price_direction.ttf}"
        for s in stage4.scenarios
    )

    base_user = {
        "title": pack.C1_base_event.title,
        "summary": pack.C1_base_event.summary,
        "n_scenarios": len(sc_ids),
        "scenarios_block": scenarios_block,
    }

    def _validate(out: _Stage5LLMOutput) -> None:
        keys = {p.scenario_id for p in out.likelihood_prior}
        wanted = set(sc_ids)
        if len(keys) != len(out.likelihood_prior):
            raise ValueError("likelihood_prior 에 중복 scenario_id 존재")
        if keys != wanted:
            raise ValueError(
                f"likelihood_prior 키 집합 불일치: 누락={wanted-keys}, 여분={keys-wanted}"
            )
        for item in out.likelihood_prior:
            if item.prior not in LIKELIHOOD_TIERS:
                raise ValueError(f"5단계 외 Prior 값: {item.prior}")

    out = _invoke_with_retry(
        stage="Stage 5",
        base_payload=base_user,
        hard_constraints=STAGE5_HARD,
        validate_fn=_validate,
        response_model=_Stage5LLMOutput,
    )

    if out is None:
        out = _stage5_fallback(sc_ids)

    # 입력 범위 밖 키/값 방어적 후처리.
    cleaned: Dict[str, str] = {}
    prior_map = {p.scenario_id: p.prior for p in out.likelihood_prior}
    for k in sc_ids:
        v = prior_map.get(k, "medium")
        if v not in LIKELIHOOD_TIERS:
            v = "medium"
        cleaned[k] = v

    # MECE 결정론적 판정 우선:
    #   각 시나리오의 dimension_values 조합이 모두 유일하면 정의상 ME=True.
    #   LLM 판정이 이와 다르면(narrative 유사도로 False 를 반환하는 케이스 등) 코드 판정으로 덮어씀.
    deterministic_me = _all_dim_values_unique(stage4.scenarios)
    if bool(out.mutually_exclusive) != deterministic_me:
        print(
            f"  ↳ Stage 5 — LLM 판정({out.mutually_exclusive}) 과 코드 결정론 판정"
            f"({deterministic_me}) 불일치 → 코드 판정 우선 적용"
        )

    return Stage5Validation(
        mece_check=MECECheck(mutually_exclusive=deterministic_me),
        likelihood_prior=cleaned,  # type: ignore[arg-type]
    )


def _all_dim_values_unique(scenarios: List[Scenario]) -> bool:
    """모든 시나리오의 dimension_values 조합이 서로 유일한지 검사.

    유일하면 정의상 동일 시점에 한 시나리오만 참이 되어 ME=True 가 결정론적으로 성립.
    """
    seen: set = set()
    for s in scenarios:
        key = tuple(sorted(s.dimension_values.items()))
        if key in seen:
            return False
        seen.add(key)
    return True


def _stage5_fallback(sc_ids: List[str]) -> _Stage5LLMOutput:
    """LLM 실패 시 — 모두 'medium' 으로 안전 부여."""
    print("  ↳ Stage 5 fallback: 전체 'medium' Prior 안전 부여")
    return _Stage5LLMOutput(
        mutually_exclusive=True,
        rationale="Fallback — Prior 카테고리 정밀 판정 보류.",
        likelihood_prior=[
            _Stage5LLMOutput.LikelihoodPriorItem(scenario_id=sid, prior="medium")
            for sid in sc_ids
        ],
    )


# ══════════════════════════════════════════════════════════════
# 9. OpenAI 공용 유틸 (재시도 + HARD_CONSTRAINTS 누적 주입 + fallback)
# ══════════════════════════════════════════════════════════════

# [패턴] 모든 Stage 가 동일 retry 정책 / 점진적 HARD_CONSTRAINTS 강화를 공유.
#         재시도 판정은 종류별로 함수를 쪼개어 단일 책임 유지(ref 규칙 #6·#7).

_STAGE_PROMPTS: Dict[str, Tuple[str, str]] = {
    "Stage 2": (STAGE2_SYSTEM, STAGE2_USER),
    "Stage 3": (STAGE3_SYSTEM, STAGE3_USER),
    "Stage 4": (STAGE4_SYSTEM, STAGE4_USER),
    "Stage 5": (STAGE5_SYSTEM, STAGE5_USER),
}


def _resolve_stage_key(stage: str) -> str:
    """`Stage 3 [dim]` 같은 상세명을 기본 stage 키로 정규화."""
    return stage.split(" [")[0]


def _build_messages_for_stage(stage: str, payload: Dict) -> List[dict]:
    """Stage 템플릿 + payload 를 OpenAI messages 형식으로 렌더링."""
    stage_key = _resolve_stage_key(stage)
    prompt_pair = _STAGE_PROMPTS.get(stage_key)
    if prompt_pair is None:
        raise RuntimeError(f"Stage prompt 미등록: {stage}")
    system_prompt, user_prompt = prompt_pair
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.format(**payload)},
    ]


def _parse_stage_output(
    stage: str,
    payload: Dict,
    response_model: Type[BaseModel],
) -> BaseModel:
    """OpenAI structured output 파싱 호출 + 타입 안전 검증."""
    messages = _build_messages_for_stage(stage, payload)
    parsed = parse_structured_sync(
        client=OPENAI_CLIENT,
        model=REF_MODEL,
        messages=messages,
        response_model=response_model,
        max_completion_tokens=REF_MAX_TOKENS,
        env_prefix="REF",
    )
    if isinstance(parsed, response_model):
        return parsed
    return response_model.model_validate(parsed.model_dump())


def _is_retryable_api_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 500, 502, 503, 529}:
        return True
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    keywords = ("overloaded", "rate limit", "too many requests", "timeout", "connection")
    return any(k in name or k in msg for k in keywords)


def _is_retryable_schema_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    keywords = (
        "validationerror", "validation error", "structured", "min_length",
        "max_length", "json", "output parsing", "literal", "enum",
    )
    return "validation" in name or any(k in msg for k in keywords)


def _invoke_with_retry(
    stage: str,
    base_payload: Dict,
    hard_constraints: str,
    validate_fn,
    response_model: Type[BaseModel],
) -> BaseModel | None:
    """공용 LLM 호출 — 지수백오프+지터, HARD_CONSTRAINTS 누적, validation 실패 시 재시도.

    실패/경계 조건:
        - REF_MAX_RETRIES 소진 시 None 반환 → 호출부에서 fallback 으로 분기.
        - 'max_tokens 출력 잘림' 감지 시 동일 재시도(토큰 늘림은 호출부 책임).
    """
    if _resolve_stage_key(stage) not in _STAGE_PROMPTS:
        raise RuntimeError(f"Stage prompt 미등록: {stage}")

    last_exc: Exception | None = None
    last_validation_exc: Exception | None = None
    accumulated_hint = hard_constraints

    for attempt in range(1, REF_MAX_RETRIES + 1):
        try:
            payload = dict(base_payload)
            # 재시도 시 HARD_CONSTRAINTS 점진 강화.
            payload_with_hint = _augment_user_payload(payload, accumulated_hint, last_validation_exc, attempt)
            result = _parse_stage_output(stage, payload_with_hint, response_model)
            validate_fn(result)
            return result

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            is_api = _is_retryable_api_error(exc)
            is_schema = _is_retryable_schema_error(exc)
            is_validation = isinstance(exc, ValueError) and "ValueError" in exc.__class__.__name__
            should_retry = (is_api or is_schema or is_validation) and attempt < REF_MAX_RETRIES
            if not should_retry:
                print(f"  ↳ {stage} 재시도 불가 — {exc.__class__.__name__}: {str(exc)[:160]}")
                break

            if is_validation or is_schema:
                last_validation_exc = exc
                accumulated_hint = hard_constraints + (
                    f"\n[직전 실패 원인 — Stage {stage}]\n- {str(exc)[:240]}\n"
                )
                reason = "출력 검증/스키마 불일치"
            elif is_api:
                reason = "API 과부하/레이트리밋"
            else:
                reason = "기타 재시도"

            wait_sec = min(20.0, 1.5 ** (attempt - 1)) + random.uniform(0, 0.7)
            print(f"  ↳ {stage} 재시도 ({attempt}/{REF_MAX_RETRIES}) — {reason}, {wait_sec:.1f}s 후")
            time.sleep(wait_sec)

    print(f"  ↳ {stage} 재시도 소진 — fallback 진입 (last_error={type(last_exc).__name__})")
    return None


def _augment_user_payload(
    payload: Dict,
    hard_constraints: str,
    last_validation_exc: Exception | None,
    attempt: int,
) -> Dict:
    """USER 메시지 마지막 변수에 HARD_CONSTRAINTS 를 부착.

    Prompt 마다 USER 끝에 별도 '__hard__' 변수를 두지 않으려고, 모든 Stage 의
    USER 텍스트는 '## 산출' 등 정형 마무리로 끝나도록 작성되어 있고, hint 는
    문서적으로는 별도 system-level 강화이지만 여기서는 USER payload 의 끝에
    있는 임의 텍스트 키('combos_block','scenarios_block','dimensions_block',
    'enum_full_block','detail_excerpt')에 append 하는 방식으로 구현.
    """
    appended_payload = dict(payload)
    text_keys = ("combos_block", "scenarios_block", "dimensions_block",
                 "enum_full_block", "tail_block", "detail_excerpt")
    target = None
    for k in text_keys:
        if k in appended_payload and isinstance(appended_payload[k], str):
            target = k
    if target is None:
        # 텍스트 키 없으면 그냥 첫 번째 string 변수에 부착.
        for k, v in list(appended_payload.items()):
            if isinstance(v, str):
                target = k
                break
    if target is not None:
        appended_payload[target] = (
            f"{appended_payload[target]}\n\n{hard_constraints.strip()}"
        )
        if last_validation_exc is not None and attempt >= 2:
            appended_payload[target] += (
                f"\n[직전 실패 사유]\n- {str(last_validation_exc)[:240]}"
            )
    return appended_payload


# ══════════════════════════════════════════════════════════════
# 10. Document 조립 / JSON 저장 / 터미널 요약
# ══════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shorten(text: str, n: int) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n] + " …(생략)"


def _build_scenario_group_id(event: Dict) -> str:
    """sg_<slug>_<yyyy_mm_dd> 패턴.

    - event_title_ko 의 영문/숫자만 남긴 단순 slug + occurred_at 날짜.
    - 둘 다 없으면 uuid 단편으로 안정적 fallback.
    """
    occ = event.get("occurred_at", "") or ""
    date_part = occ[:10].replace("-", "_") if len(occ) >= 10 else datetime.now(
        timezone.utc).strftime("%Y_%m_%d")

    title = event.get("event_title_ko", "") or ""
    slug_chars = []
    for ch in title:
        if ch.isalnum():
            slug_chars.append(ch.lower())
        elif ch in (" ", "-", "_") and slug_chars and slug_chars[-1] != "_":
            slug_chars.append("_")
        if len(slug_chars) >= 24:
            break
    slug = "".join(slug_chars).strip("_") or uuid.uuid4().hex[:8]
    return f"sg_{slug}_{date_part}"


def build_document(state: ScenarioGroupState) -> Dict:
    """ScenarioGroupState → JSON 직렬화용 dict (../schemas/state_dict.schema.json 정합).

    출력 dict 의 key 순서는 ../schemas/state_dict.schema.json 과 동일하게 유지하여
    IDE 디핑 용이.
    """
    payload = state.model_dump()
    return payload


def save_json(doc: Dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"\n  => 저장 완료: {path.resolve()}")


def print_summary(state: ScenarioGroupState) -> None:
    W = 120
    pack = state.stage1_context_pack
    s2 = state.stage2_dimension_selection
    s3 = state.stage3_value_selection
    s4 = state.stage4_scenario_synthesis
    s5 = state.stage5_validation

    print("\n" + "═" * W)
    print(f"  ScenarioGroup: {state.scenario_group_id}")
    print(f"  Base Event   : {pack.C1_base_event.event_id} / {pack.C1_base_event.event_type_l1_l2}")
    print(f"  Title        : {pack.C1_base_event.title}")
    print("─" * W)
    print(
        f"  Stage 2 — selected_dims={len(s2.selected_dimensions)} / "
        f"excluded={len(s2.excluded_dimensions)} / total={s2.template_dimensions_total}"
    )
    for sd in s2.selected_dimensions:
        print(f"    ✓ {sd.dimension_id:<28} | {sd.rationale}")
    print(
        f"  Stage 3 — per_dimension={len(s3.per_dimension)}건"
    )
    for pd in s3.per_dimension:
        print(
            f"    ▸ {pd.dimension_id:<28} | selected=[{', '.join(pd.selected_enum)}] | "
            f"tail={pd.tail_risk_kept}"
        )
    print(
        f"  Stage 4 — cartesian_total={s4.cartesian_total} / compat_passed={s4.filtered_by_compatibility} / "
        f"final_scenarios={len(s4.scenarios)}"
    )
    print("─" * W)
    print(f"  {'#':<4} {'sid':<7} {'title':<32} {'brent':<11} {'jkm':<11} {'ttf':<11} {'prior':<10}")
    for i, sc in enumerate(s4.scenarios, 1):
        title_short = (sc.title[:30] + "…") if len(sc.title) > 31 else sc.title
        prior = s5.likelihood_prior.get(sc.scenario_id, "?")
        print(
            f"  {i:<4} {sc.scenario_id:<7} {title_short:<32} "
            f"{sc.price_direction.brent:<11} {sc.price_direction.jkm:<11} {sc.price_direction.ttf:<11} "
            f"{prior:<10}"
        )
    print("═" * W)
    # Σ 행 — 5단계 Prior 분포 + MECE 통과.
    tier_count = {t: 0 for t in LIKELIHOOD_TIERS}
    for v in s5.likelihood_prior.values():
        tier_count[v] = tier_count.get(v, 0) + 1
    dist_str = " | ".join(f"{t}={tier_count[t]}" for t in LIKELIHOOD_TIERS)
    print(
        f"  Σ scenarios={len(s4.scenarios)}  |  MECE.mutually_exclusive={s5.mece_check.mutually_exclusive}  "
        f"|  prior dist: {dist_str}"
    )


# ══════════════════════════════════════════════════════════════
# 11. Input Loader  (단일 Base Event)
# ══════════════════════════════════════════════════════════════

def load_base_event(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        event = json.load(f)
    if not event.get("mi_event_id"):
        raise ValueError(f"{path}: mi_event_id 키 누락")
    print(f"  ▸ Base Event 로드: {path.name}  (mi_event_id={event['mi_event_id']})")
    return event


# ══════════════════════════════════════════════════════════════
# 12. Main
# ══════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Multi-Scenario Generator — Base Event JSON 으로부터 5~7개 멀티 시나리오 생성."
            " 입/출력 파일 경로는 인자로 지정한다 (상대 경로는 현재 작업 디렉터리 또는"
            " 본 스크립트 디렉터리 기준으로 자동 해석)."
        )
    )
    parser.add_argument(
        "--input", "-i", type=str, required=True,
        help="입력 Base Event JSON 경로 (예: sample_event_ev_2a58da7f4ff2.json).",
    )
    parser.add_argument(
        "--output", "-o", type=str, required=True,
        help="출력 시나리오 결과 JSON 경로 (예: stage_result_ev_2a58da7f4ff2.json).",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    cwd = Path.cwd()

    def _resolve_input_path(raw_path: str) -> Path:
        p = Path(raw_path)
        if p.is_absolute():
            return p.resolve()
        # 1순위: 실행한 현재 작업 디렉터리 기준
        cand_cwd = (cwd / p).resolve()
        if cand_cwd.exists():
            return cand_cwd
        # 2순위: 스크립트 디렉터리 기준 (기존 하위호환)
        return (base_dir / p).resolve()

    def _resolve_output_path(raw_path: str) -> Path:
        p = Path(raw_path)
        if p.is_absolute():
            return p.resolve()
        # 출력 파일은 아직 없을 수 있으므로, 파일 존재 여부 대신 부모 디렉터리 존재를 본다.
        cand_cwd = (cwd / p).resolve()
        if cand_cwd.parent.exists():
            return cand_cwd
        return (base_dir / p).resolve()

    in_p = _resolve_input_path(args.input)
    out_p = _resolve_output_path(args.output)
    if not in_p.exists():
        raise FileNotFoundError(f"입력 base_event 파일 없음: {in_p}")
    args.input = in_p
    args.output = out_p
    return args


def main() -> None:
    args = parse_args()
    input_path: Path = args.input
    output_path: Path = args.output

    print("═" * 70)
    print("  Multi-Scenario Generator  —  Stage 1~5 통합")
    print(f"  Model: {REF_MODEL} (OpenAI-compatible) / max_tokens={REF_MAX_TOKENS}")
    print(f"  input:  {input_path}")
    print(f"  output: {output_path}")
    print("═" * 70)

    event = load_base_event(input_path)
    pack = stage1_build_context_pack(event)
    print(f"  ✓ Stage 1 — Context Pack 구성 (event_type={pack.C1_base_event.event_type_l1_l2})")

    template = _resolve_template(pack.C1_base_event.event_type_l1_l2)
    print(
        f"  ✓ Template 로드: {pack.C1_base_event.event_type_l1_l2} "
        f"({template['template_dimensions_total']} Dim)"
    )

    t_s2 = time.time()
    stage2 = stage2_select_dimensions(pack, event, template)
    print(f"  ✅ Stage 2 — Dim 선택 완료 ({time.time()-t_s2:.1f}s)")

    t_s3 = time.time()
    stage3 = stage3_reduce_values(pack, stage2, template)
    print(f"  ✅ Stage 3 — Value 축소 완료 ({time.time()-t_s3:.1f}s)")

    t_s4 = time.time()
    stage4 = stage4_synthesize_scenarios(pack, stage3, template)
    print(f"  ✅ Stage 4 — 시나리오 합성 완료 ({time.time()-t_s4:.1f}s)")

    t_s5 = time.time()
    stage5 = stage5_validate(pack, stage4)
    print(f"  ✅ Stage 5 — MECE + Prior 완료 ({time.time()-t_s5:.1f}s)")

    state = ScenarioGroupState(
        scenario_group_id=_build_scenario_group_id(event),
        created_at=_now_iso(),
        stage1_context_pack=pack,
        stage2_dimension_selection=stage2,
        stage3_value_selection=stage3,
        stage4_scenario_synthesis=stage4,
        stage5_validation=stage5,
    )

    doc = build_document(state)
    print_summary(state)

    save_json(doc, output_path)
    print(f"  IDE에서 {output_path.name} 파일을 여세요.\n")


if __name__ == "__main__":
    main()

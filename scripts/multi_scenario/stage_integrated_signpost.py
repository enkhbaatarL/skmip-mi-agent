"""
Multi-Scenario Signpost Pipeline (Stage 0 / 2 / 3 / 4 / 5 통합)
─────────────────────────────────────────────────────────────────
LangChain + Claude 기반으로, 이미 생성된 멀티시나리오 결과 JSON
(`stage_result_ev_<id>.json`) 을 입력받아 각 시나리오에 **Signpost** 트리를
부착·확장한 결과(`stage_result_extended_ev_<id>.json`) 를 출력함.

관계 구조:
    Scenario (state.stage4_scenario_synthesis.scenarios[*])
        ├─ assumptions[]                 ← Stage 1 (미진행: 빈 리스트)
        ├─ signposts[]                   ← Stage 2 / 3 / 4 / 5 의 협업 산출
        │     ├─ signpost_class          ← Stage 2 ('observation' 고정)
        │     ├─ label_ko                ← Stage 2
        │     ├─ signpost_source         ← Stage 3 ('mi_record' 고정)
        │     ├─ actor_nature            ← Stage 3 (Phase1: 무시 → null)
        │     ├─ direction               ← Stage 4 ('SUP' 고정)
        │     ├─ strength                ← Stage 4 (LLM)
        │     ├─ weight                  ← Stage 4 (Phase1: 무시 → null)
        │     ├─ rationale_ko            ← Stage 4 (LLM)
        │     ├─ role_tag                ← Stage 4 (Phase1: 무시 → null)
        │     └─ keyword_hints           ← Stage 5 (LLM)
        ├─ window_end_ts                 ← Stage 6 (미진행: '')
        ├─ monitored_signposts           ← Stage 6 (미진행: [])
        └─ deadline_kill_conditions      ← Stage 6 (미진행: [])

가이드라인 준수 (Phase 1 처리 규칙):
    - Stage 1 / 6 : 미진행. 컨테이너/필드 형태만 채우고 값은 빈 채로 유지.
    - Stage 2     : signpost_class = 'observation' 고정, LLM 으로 label_ko 생성
                    + Observability 3-필터 (소스 가용성 / Binary 판정 /
                    시나리오 결합도) 자체 적용해 통과만 채택.
    - Stage 3     : signpost_source = 'mi_record' 고정, actor_nature 는 무시(null).
    - Stage 4     : direction = 'SUP' 고정. weight, role_tag 는 무시(null).
                    LLM 이 strength(STRONG/MEDIUM/WEAK) + rationale_ko 만 부여.
                    역할 쿼터(realized 1~3 + early 1~3)를 strength 분포로 강제.
                    → N 의 폭(3~6) 만큼 분포 다양성 허용.
    - Stage 5     : 진행. signpost 별 keyword_hints 3~5개를 LLM 으로 부여.

Usage:
    ANTHROPIC_API_KEY=sk-ant-xxx \\
        python stage_integrated_signpost.py [stage_result_ev_<id>.json]

Output:
    state_dict_signpost.json                   ← 빈 스키마 (구조 참고용)
    stage_result_extended_ev_<id>.json         ← 최종 산출 (IDE 에서 열기)
"""

import copy
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, conlist, model_validator

load_dotenv()


# ══════════════════════════════════════════════════════════════
# 1. Env / Constants  (REF_* 접두어, ref_code_style 규칙 #2·#9)
# ══════════════════════════════════════════════════════════════

# [패턴] 모델·토큰·경로·재시도·시나리오당 signpost 수 등 튜닝 파라미터는
#         모두 환경변수로 노출하여 호출자가 외부에서 조정 가능하도록 함.
REF_MODEL: str             = os.getenv("REF_MODEL", "claude-opus-4-1-20250805")
REF_MAX_TOKENS: int        = int(os.getenv("REF_MAX_TOKENS", "8192"))
REF_TEMPERATURE: float     = float(os.getenv("REF_TEMPERATURE", "0.0"))
REF_MAX_RETRIES: int       = int(os.getenv("REF_MAX_RETRIES", "5"))
REF_INPUT_RESULT_PATH: str = os.getenv("REF_INPUT_RESULT_PATH", "")

# Phase 1 가이드라인: realized(SUP·STRONG) 1~3 + early(SUP·MED/WEAK) 1~3.
#                    → 시나리오당 총 3~6개의 SUP signpost.
#  (시나리오의 결합도/확정성에 따라 분포가 달라지도록 폭을 넓힘.)
REF_SIGNPOSTS_PER_SCENARIO_MIN: int = int(os.getenv("REF_SIGNPOSTS_PER_SCENARIO_MIN", "3"))
REF_SIGNPOSTS_PER_SCENARIO_MAX: int = int(os.getenv("REF_SIGNPOSTS_PER_SCENARIO_MAX", "6"))

# Stage 4 strength 쿼터 (N 분포 다양성 확보용 폭).
REF_STRONG_QUOTA_MIN: int = int(os.getenv("REF_STRONG_QUOTA_MIN", "1"))
REF_STRONG_QUOTA_MAX: int = int(os.getenv("REF_STRONG_QUOTA_MAX", "3"))
REF_EARLY_QUOTA_MIN:  int = int(os.getenv("REF_EARLY_QUOTA_MIN",  "1"))
REF_EARLY_QUOTA_MAX:  int = int(os.getenv("REF_EARLY_QUOTA_MAX",  "3"))

# Stage 2 enum.
SIGNPOST_CLASS_TIERS: Tuple[str, ...] = ("observation",)
# Stage 3 enum (Phase 1: source 만 사용).
SIGNPOST_SOURCE_TIERS: Tuple[str, ...] = ("mi_record",)
# Stage 4 enum.
DIRECTION_TIERS: Tuple[str, ...] = ("SUP", "REF")
STRENGTH_TIERS: Tuple[str, ...]  = ("STRONG", "MEDIUM", "WEAK")
# Stage 5 keyword 길이 가드.
KEYWORD_HINTS_MIN: int = 3
KEYWORD_HINTS_MAX: int = 5

SignpostClass  = Literal["observation"]
SignpostSource = Literal["mi_record"]
Direction      = Literal["SUP", "REF"]
Strength       = Literal["STRONG", "MEDIUM", "WEAK"]


# ══════════════════════════════════════════════════════════════
# 2. Pydantic Models  (state_dict_signpost.json 정합)
# ══════════════════════════════════════════════════════════════

# --- Signpost (시나리오 귀속 단위) ---
class Signpost(BaseModel):
    """단일 Signpost — 시나리오에 귀속되는 관측 신호 1건."""

    # --- 식별 ---
    signpost_id: str = Field(description="sgp_S{NN}_{NN} 형태, 시나리오 내 유일.")

    # --- Stage 1 (미진행) ---
    assumption_refs: List[str] = Field(
        default_factory=list,
        description="검증 대상 가정 ID 리스트. Phase 1: Stage 1 미진행으로 빈 리스트.",
    )

    # --- Stage 2 (Observability) ---
    signpost_class: SignpostClass = Field(
        default="observation",
        description="Phase 1: 'observation' 고정.",
    )
    label_ko: str = Field(
        description="관측 가능한 신호 한 줄 (예: 'Ras Laffan 재가동 공식 발표').",
    )

    # --- Stage 3 (Axis) ---
    signpost_source: SignpostSource = Field(
        default="mi_record",
        description="Phase 1: 'mi_record' 고정.",
    )
    actor_nature: str | None = Field(
        default=None,
        description="Phase 1: 무시 → None.",
    )

    # --- Stage 4 (Direction & Strength) ---
    direction: Direction = Field(
        default="SUP",
        description="Phase 1: 'SUP' 고정 (Supporting).",
    )
    strength: Strength = Field(
        description="STRONG / MEDIUM / WEAK 중 1개. realized=SUP×STRONG, early=SUP×MED|WEAK.",
    )
    weight: float | None = Field(
        default=None,
        description="Phase 1: 무시 → None.",
    )
    rationale_ko: str = Field(
        description="이 signpost 가 시나리오를 어떻게 검증/보강하는지 한국어 1~2줄.",
    )
    role_tag: str | None = Field(
        default=None,
        description="Phase 1: 무시 → None. (downstream 에서 strength 로부터 파생 가능)",
    )

    # --- Stage 5 (Keyword) ---
    keyword_hints: List[str] = Field(
        default_factory=list,
        description="Record 인입 시 1차 Filter 로 쓰일 3~5개 키워드.",
    )


class ExtendedScenario(BaseModel):
    """기존 Scenario + Signpost 트리 + Stage6 컨테이너.

    기존 Scenario 의 모든 키는 보존하면서 (extra='allow' 로 미지정 키 통과) 신규
    Signpost 관련 필드만 명시적으로 선언.
    """

    # --- 기존 Scenario 키 (보존) ---
    scenario_id: str = Field(description="S_01 형태")
    title: str = Field(default="", description="시장 참여자 관점 한 줄 요약")
    dimension_values: Dict[str, str] = Field(
        default_factory=dict, description="dim_id -> enum_id 1:1 매핑.",
    )
    description: str = Field(default="", description="3~5줄 시나리오 서술")
    derivation_rationale: str = Field(default="", description="도출 근거")
    price_direction: Dict[str, str] = Field(
        default_factory=dict,
        description="brent/jkm/ttf 7단계 방향성. 기존 dict 그대로 보존.",
    )
    compatibility_passed: bool = Field(default=True, description="Compat 통과 여부")

    # --- Stage 1 (미진행) ---
    assumptions: List[Dict] = Field(
        default_factory=list,
        description="가정 분해 결과. Phase 1: 미진행 → 빈 리스트.",
    )

    # --- Stage 2~5 (Signpost 트리) ---
    signposts: List[Signpost] = Field(
        default_factory=list,
        description="시나리오에 귀속되는 Signpost 들. 길이 3~6 권장.",
    )

    # --- Stage 6 (미진행) ---
    window_end_ts: str = Field(
        default="", description="시나리오 모니터링 마감 ISO-8601 UTC. Phase 1: 빈 문자열.",
    )
    monitored_signposts: List[str] = Field(
        default_factory=list,
        description="현 시점 모니터링 대상 signpost_id 목록. Phase 1: 빈 리스트.",
    )
    deadline_kill_conditions: List[Dict] = Field(
        default_factory=list,
        description="시나리오 폐기 조건. Phase 1: 빈 리스트.",
    )

    model_config = {"extra": "allow"}  # 기존 입력의 미지정 키 보존


# --- LLM 출력 전용 (state 미직접 매핑) ---
class _Stage2Candidate(BaseModel):
    label_ko: str = Field(description="관측 가능한 신호 한 줄 (한국어).")
    passes_filter: bool = Field(
        description="3-필터 (소스 가용성 / Binary / 시나리오 결합도) 통과 여부.",
    )
    filter_reason: str = Field(
        default="",
        description="통과/탈락 사유 한국어 1줄. 통과 시도 사유를 명기.",
    )


class _Stage2LLMOutput(BaseModel):
    candidates: conlist(_Stage2Candidate, min_length=5, max_length=10) = Field(  # type: ignore[valid-type]
        description=(
            "Observability 후보 5~10개. 그 중 passes_filter=True 가 "
            f"{REF_SIGNPOSTS_PER_SCENARIO_MIN}~{REF_SIGNPOSTS_PER_SCENARIO_MAX}개 이어야 함. "
            "MAX 채우는 것이 목표가 아니며, 결합도가 강한 후보만 통과시킬 것."
        ),
    )

    @model_validator(mode="after")
    def _validate_unique_labels(self):
        seen: set = set()
        for c in self.candidates:
            key = c.label_ko.strip()
            if not key:
                raise ValueError("label_ko 가 빈 문자열인 후보 존재.")
            if key in seen:
                raise ValueError(f"label_ko 중복: '{key}'")
            seen.add(key)
        return self


class _Stage4Assignment(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    strength: Strength = Field(description="STRONG / MEDIUM / WEAK 중 1개.")
    rationale_ko: str = Field(
        description="이 strength 부여 + 시나리오 검증 측면의 한국어 1~2줄 근거.",
    )


class _Stage4LLMOutput(BaseModel):
    assignments: List[_Stage4Assignment] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


class _Stage5Hint(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    keyword_hints: conlist(str, min_length=KEYWORD_HINTS_MIN, max_length=KEYWORD_HINTS_MAX) = Field(  # type: ignore[valid-type]
        description="3~5개 키워드. 고유명사 + 동사/상태어 혼합 권장.",
    )


class _Stage5LLMOutput(BaseModel):
    hints: List[_Stage5Hint] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


# ══════════════════════════════════════════════════════════════
# 3. Stage 0 — 스키마 확장 / 기존 결과 로드 / 빈 스키마 덤프
# ══════════════════════════════════════════════════════════════
#
# [패턴] Stage 0 는 LLM 호출 없이 결정론적 부착만 수행. 입력 dict 의 키는
#         절대 삭제하지 않고, 누락 키만 default 로 채워 다음 Stage 진입 준비.

# 시나리오에 부착할 Signpost 컨테이너의 default(Stage 6 미진행 포함).
_SCENARIO_EXTENSION_DEFAULTS: Dict[str, Any] = {
    "assumptions": [],
    "signposts": [],
    "window_end_ts": "",
    "monitored_signposts": [],
    "deadline_kill_conditions": [],
}


def stage0_extend_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 0 진입점 — 입력 state dict 를 deepcopy 후 Signpost 컨테이너를 부착.

    실패/경계 조건:
        - state['stage4_scenario_synthesis']['scenarios'] 가 list 가 아니면 ValueError.
        - 시나리오 객체에 이미 동일 키가 있으면 **건드리지 않음** (보존 우선).
    """
    extended = copy.deepcopy(state)
    s4 = extended.get("stage4_scenario_synthesis", {}) or {}
    scenarios = s4.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(
            "stage4_scenario_synthesis.scenarios 가 비어있거나 list 가 아님. "
            "시나리오 생성 결과 JSON 인지 확인하세요."
        )

    for sc in scenarios:
        for k, default_val in _SCENARIO_EXTENSION_DEFAULTS.items():
            if k not in sc:
                sc[k] = copy.deepcopy(default_val)

    return extended


def dump_empty_signpost_schema(out_path: Path) -> None:
    """state_dict.json 옆에 비어있는 state_dict_signpost.json 을 작성.

    - 입력은 같은 디렉토리의 state_dict.json (없으면 안전 fallback 으로 최소 골격).
    - 시나리오 1건에 빈 Signpost 1건을 끼워 IDE diffing 으로 확장 위치를 한눈에.
    """
    src = Path(__file__).parent / "state_dict.json"
    if src.exists():
        with open(src, "r", encoding="utf-8") as f:
            base = json.load(f)
    else:
        # ### 생략: state_dict.json 부재 시의 최소 골격 fallback.
        base = {
            "scenario_group_id": "",
            "stage4_scenario_synthesis": {"scenarios": [{"scenario_id": "S_01"}]},
        }

    scenarios = base.get("stage4_scenario_synthesis", {}).get("scenarios") or [{}]
    sc0 = scenarios[0]
    sc0.setdefault("assumptions", [])
    sc0.setdefault("signposts", [{
        "signpost_id": "sgp_S01_01",
        "assumption_refs": [],
        "signpost_class": "observation",
        "label_ko": "",
        "signpost_source": "mi_record",
        "actor_nature": None,
        "direction": "SUP",
        "strength": "STRONG|MEDIUM|WEAK",
        "weight": None,
        "rationale_ko": "",
        "role_tag": None,
        "keyword_hints": [],
    }])
    sc0.setdefault("window_end_ts", "")
    sc0.setdefault("monitored_signposts", [])
    sc0.setdefault("deadline_kill_conditions", [])

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
    print(f"  => state_dict_signpost.json 작성: {out_path.name}")


# ══════════════════════════════════════════════════════════════
# 4. Stage 2 — Observability Filter  (label_ko 생성 + 3-필터)
# ══════════════════════════════════════════════════════════════

# [패턴] SYSTEM / USER / HARD_CONSTRAINTS 3분할 (ref 규칙 #5).
#         HARD_CONSTRAINTS 는 재시도 시 누적 주입.

STAGE2_SYSTEM = """\
당신은 LNG 멀티시나리오 'Observability Filter' 입니다.
입력으로 시나리오 1건의 가정치 조합(dimension_values + 서술)을 받아, **이 시나리오가
참이라면 향후 관측 가능한 신호** 후보를 생성한 뒤, 아래 3개 필터로 self-filter 하십시오.

## 후보 생성 가이드 (5~10개)
- 각 후보는 한국어 한 줄로 작성 (예: 'Ras Laffan 재가동 공식 발표').
- 고유명사(시설/기관/지명) 1개 이상 + 동사·상태어 1개 이상 포함.
- '관측 가능한 사실 명제' 여야 함. 의견/감정/모호 표현 금지.

## 3-필터 (모두 통과해야 passes_filter=True)
1. 소스 가용성: Reuters / Platts / Bloomberg / WSJ / FT 등 주요 매체 또는 정부·기관
   공식 채널에서 보도될 가능성이 높아야 함.
2. Binary 판정: 모호한 해석 없이 '관측됨 / 미관측'을 결정 가능해야 함.
   ('분위기', '전망', '기대감' 류 모호어는 탈락)
3. 시나리오 결합도: 일반 뉴스가 아니라 입력된 시나리오 가정치(특정 지명/봉쇄 단계/
   리스크 프리미엄 수준 등)와 직접 연결되어야 함.

## passes_filter=True 후보 수 — **시나리오 결합도에 비례**
- 허용 범위: {min_n}~{max_n} 개.
- **MAX 를 채우는 것이 목표가 아닙니다.** 시나리오 가정치(dimension_values)와
  직접 연결되는 결합도 높은 후보가 적다면 MIN({min_n})만 통과시키고, 가정치 조합이
  풍부해 강한 결합 후보가 많다면 MAX({max_n})까지 통과시키세요.
- 즉 시나리오마다 통과 수가 달라지는 것이 정상이며 자연스러운 결과입니다.
- 결합도가 불확실하거나 '일반 뉴스'에 가까운 후보는 통과 0표 처리하세요.

## filter_reason
- 통과 시: '소스 가용성+Binary+결합도 모두 충족' 식으로 간결히.
- 탈락 시: 어느 필터에서 탈락했는지(예: 'Binary 판정 불가 — 분위기 표현') 명기.
"""

STAGE2_USER = """\
## Base Event 요약
- title: {base_title}
- summary: {base_summary}
- driver: {base_driver}

## 대상 시나리오
- scenario_id: {scenario_id}
- title: {scenario_title}
- description: {scenario_description}
- dimension_values: {dim_values_block}
- price_direction: {price_block}

## 산출
- candidates: 5~10개 (각 label_ko + passes_filter + filter_reason).
- 통과 후보 수: {min_n}~{max_n} 개. **MAX 를 채우지 말 것** — 결합도 강한 만큼만 통과.
"""

STAGE2_HARD = """\

[중요한 출력 제약 — Stage 2]
- candidates 길이는 5~10.
- passes_filter=True 후보의 수는 반드시 {min_n}~{max_n} 사이.
- MAX({max_n}) 채우기를 목표로 삼지 말 것. 시나리오 결합도가 높은 후보가 적다면
  MIN({min_n})만 통과시키는 것이 정답.
- 모든 label_ko 는 서로 달라야 함 (중복 금지).
- 'observation' class 만 생성. 의견/감정/모호 표현 금지.
"""

STAGE2_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE2_SYSTEM),
    ("human", STAGE2_USER),
])


def stage2_observability_filter(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
) -> List[str]:
    """Stage 2 진입점 — 시나리오 1건 → 통과 label_ko 리스트 반환.

    실패/경계 조건:
        - 통과 후보 수가 [MIN, MAX] 범위를 벗어나면 검증 실패 → 재시도.
        - LLM 실패 시 fallback 으로 시나리오 description 기반 안전 4건 생성.
    """
    scenario_id = scenario.get("scenario_id", "S_??")
    chain = _build_chain(_Stage2LLMOutput)

    base_payload = {
        "base_title": base_event_summary.get("title", ""),
        "base_summary": base_event_summary.get("summary", ""),
        "base_driver": base_event_summary.get("driver", ""),
        "scenario_id": scenario_id,
        "scenario_title": scenario.get("title", ""),
        "scenario_description": _shorten(scenario.get("description", ""), 600),
        "dim_values_block": ", ".join(
            f"{k}={v}" for k, v in (scenario.get("dimension_values") or {}).items()
        ) or "(없음)",
        "price_block": ", ".join(
            f"{k}={v}" for k, v in (scenario.get("price_direction") or {}).items()
        ) or "(없음)",
        "min_n": REF_SIGNPOSTS_PER_SCENARIO_MIN,
        "max_n": REF_SIGNPOSTS_PER_SCENARIO_MAX,
    }
    hard = STAGE2_HARD.format(
        min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
        max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
    )

    def _validate(out: _Stage2LLMOutput) -> None:
        passing = [c for c in out.candidates if c.passes_filter]
        if not (REF_SIGNPOSTS_PER_SCENARIO_MIN <= len(passing) <= REF_SIGNPOSTS_PER_SCENARIO_MAX):
            raise ValueError(
                f"통과 후보 수 {len(passing)} 이 허용 범위 "
                f"[{REF_SIGNPOSTS_PER_SCENARIO_MIN}, {REF_SIGNPOSTS_PER_SCENARIO_MAX}] 밖."
            )

    out = _invoke_with_retry(
        stage="Stage 2",
        chain=chain,
        base_payload=base_payload,
        hard_constraints=hard,
        validate_fn=_validate,
    )

    if out is None:
        labels = _stage2_fallback(scenario)
        print(f"  ↳ Stage 2 [{scenario_id}] fallback labels={len(labels)}")
        return labels

    passing = [c for c in out.candidates if c.passes_filter]
    # 방어적 후처리: 혹시 검증을 통과했지만 MAX 를 초과하면 앞 MAX 개로 잘라냄.
    passing = passing[:REF_SIGNPOSTS_PER_SCENARIO_MAX]
    print(
        f"  ▸ Stage 2 [{scenario_id}] candidates={len(out.candidates)} "
        f"passed={len(passing)}"
    )
    return [c.label_ko.strip() for c in passing]


def _stage2_fallback(scenario: Dict[str, Any]) -> List[str]:
    """LLM 실패 시 — 시나리오 description / dimension_values 키워드로 안전 라벨 생성."""
    sid = scenario.get("scenario_id", "S_??")
    dims = scenario.get("dimension_values") or {}
    dim_pairs = [(k, v) for k, v in dims.items()]
    base = (scenario.get("title") or "").strip() or "시나리오 관측 신호"

    fallbacks = [
        f"{base} — 관련 공식 발표 보도 ({sid})",
        f"{base} — 주요 매체의 가격 영향 분석 보도 ({sid})",
    ]
    for k, v in dim_pairs[:2]:
        fallbacks.append(f"{base} — {k}={v} 공식 확인 보도")

    seen: set = set()
    out: List[str] = []
    for lbl in fallbacks:
        if lbl in seen:
            continue
        seen.add(lbl)
        out.append(lbl)
        if len(out) >= REF_SIGNPOSTS_PER_SCENARIO_MAX:
            break
    while len(out) < REF_SIGNPOSTS_PER_SCENARIO_MIN:
        out.append(f"{base} — 추가 관측 #{len(out)+1}")
    return out


# ══════════════════════════════════════════════════════════════
# 5. Stage 3 — Axis Classifier  (Phase1: 결정론적 부여)
# ══════════════════════════════════════════════════════════════
#
# [패턴] Phase 1 가이드라인상 signpost_source='mi_record' 고정,
#         actor_nature 는 무시. → LLM 호출 없이 결정론적 함수 1개로 충분.

def stage3_assign_axes(label_ko: str) -> Dict[str, Any]:
    """단일 label 에 대한 Axis 부여. Phase1: 무조건 mi_record / actor_nature=None."""
    return {
        "signpost_source": "mi_record",
        "actor_nature": None,
    }


# ══════════════════════════════════════════════════════════════
# 6. Stage 4 — Direction & Strength Assignment
# ══════════════════════════════════════════════════════════════

STAGE4_SYSTEM = """\
당신은 LNG 멀티시나리오 'Direction & Strength Assignment' 입니다.
입력으로 시나리오 1건과 그에 귀속된 Signpost label 리스트(이미 Stage2 통과)
를 받습니다. **direction 은 'SUP' 로 이미 고정**되었으므로 결정/출력하지 않습니다.

## 당신이 결정할 것 (signpost 별로)
1. strength ∈ {{STRONG, MEDIUM, WEAK}}
   - STRONG = 'realized' 신호: 시나리오가 사실상 실현됐음을 직접 증명하는 결정적 관측.
   - MEDIUM = 'early' 신호 (강): 시나리오 방향성의 분명한 초기 신호. 확정은 아님.
   - WEAK   = 'early' 신호 (약): 정황적·간접적 초기 신호. 단독으로는 약함.
2. rationale_ko : 위 strength 부여 근거 + 이 signpost 가 시나리오를 어떻게
   검증/보강하는지 한국어 1~2줄.

## 역할 쿼터 (반드시 준수)
- 입력 signpost 가 N 개(=3~6)일 때, 다음을 모두 만족해야 함:
  - STRONG 개수 ∈ [{strong_min}, {strong_max}]   (=realized)
  - MEDIUM+WEAK 개수 ∈ [{early_min}, {early_max}]  (=early)
- 위 폭 내에서 **시나리오 확정성에 비례해 분포가 달라지는 것이 정상**:
  - tail-risk/극단 시나리오 → STRONG 비중을 키우고 EARLY 작게.
  - 단기/완화 시나리오    → STRONG 작게, EARLY(MED/WEAK) 비중 크게.
- 모두 STRONG 또는 모두 MEDIUM 같은 편향 출력은 여전히 금지.

## 절대 금지
- direction / weight / role_tag 출력 금지 (downstream 에서 자동 부여).
- STRONG 을 {strong_max} 개 초과 부여 금지.
- EARLY(MED+WEAK) 를 {early_max} 개 초과 부여 금지.
"""

STAGE4_USER = """\
## Base Event 요약
- title: {base_title}
- summary: {base_summary}

## 대상 시나리오
- scenario_id: {scenario_id}
- title: {scenario_title}
- description: {scenario_description}
- dimension_values: {dim_values_block}

## 입력 Signpost ({n_signposts}개)
{signpost_block}

## 산출
- assignments 길이 = {n_signposts}, label_ko 순서 유지.
- 각 항목에 strength + rationale_ko (1~2줄).
"""

STAGE4_HARD = """\

[중요한 출력 제약 — Stage 4]
- assignments 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력 label 과 정확히 일치 (echo).
- strength ∈ {{STRONG, MEDIUM, WEAK}} 중 정확히 1개.
- 쿼터: STRONG {strong_min}~{strong_max} + (MEDIUM∪WEAK) {early_min}~{early_max}. 위반 시 재시도.
"""

STAGE4_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE4_SYSTEM),
    ("human", STAGE4_USER),
])


def stage4_assign_direction_strength(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
) -> List[Dict[str, str]]:
    """Stage 4 진입점 — labels → [{label_ko, strength, rationale_ko}, ...].

    실패/경계 조건:
        - 출력 길이가 입력과 다르면 재시도.
        - STRONG / EARLY 쿼터 위반 시 재시도.
        - LLM 실패 시 fallback (분포 균형 + N 비례 분배).
    """
    scenario_id = scenario.get("scenario_id", "S_??")
    if not labels:
        return []

    chain = _build_chain(_Stage4LLMOutput)

    signpost_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))
    base_payload = {
        "base_title": base_event_summary.get("title", ""),
        "base_summary": base_event_summary.get("summary", ""),
        "scenario_id": scenario_id,
        "scenario_title": scenario.get("title", ""),
        "scenario_description": _shorten(scenario.get("description", ""), 600),
        "dim_values_block": ", ".join(
            f"{k}={v}" for k, v in (scenario.get("dimension_values") or {}).items()
        ) or "(없음)",
        "n_signposts": len(labels),
        "signpost_block": signpost_block,
        "strong_min": REF_STRONG_QUOTA_MIN,
        "strong_max": REF_STRONG_QUOTA_MAX,
        "early_min":  REF_EARLY_QUOTA_MIN,
        "early_max":  REF_EARLY_QUOTA_MAX,
    }

    label_set = [lbl.strip() for lbl in labels]
    hard = STAGE4_HARD.format(
        strong_min=REF_STRONG_QUOTA_MIN,
        strong_max=REF_STRONG_QUOTA_MAX,
        early_min=REF_EARLY_QUOTA_MIN,
        early_max=REF_EARLY_QUOTA_MAX,
    )

    def _validate(out: _Stage4LLMOutput) -> None:
        if len(out.assignments) != len(labels):
            raise ValueError(
                f"assignments 길이 불일치: {len(out.assignments)} != {len(labels)}"
            )
        out_labels = [a.label_ko.strip() for a in out.assignments]
        if out_labels != label_set:
            raise ValueError(
                "assignments 의 label_ko 순서가 입력과 다름. "
                f"expected={label_set}, got={out_labels}"
            )
        n_strong = sum(1 for a in out.assignments if a.strength == "STRONG")
        n_early = sum(1 for a in out.assignments if a.strength in ("MEDIUM", "WEAK"))
        if not (REF_STRONG_QUOTA_MIN <= n_strong <= REF_STRONG_QUOTA_MAX):
            raise ValueError(
                f"STRONG 쿼터 위반: {n_strong} "
                f"(허용 {REF_STRONG_QUOTA_MIN}~{REF_STRONG_QUOTA_MAX})"
            )
        if not (REF_EARLY_QUOTA_MIN <= n_early <= REF_EARLY_QUOTA_MAX):
            raise ValueError(
                f"MEDIUM+WEAK 쿼터 위반: {n_early} "
                f"(허용 {REF_EARLY_QUOTA_MIN}~{REF_EARLY_QUOTA_MAX})"
            )

    out = _invoke_with_retry(
        stage="Stage 4",
        chain=chain,
        base_payload=base_payload,
        hard_constraints=hard,
        validate_fn=_validate,
    )

    if out is None:
        return _stage4_fallback(labels)

    return [
        {"label_ko": a.label_ko.strip(), "strength": a.strength, "rationale_ko": a.rationale_ko}
        for a in out.assignments
    ]


def _stage4_fallback(labels: List[str]) -> List[Dict[str, str]]:
    """LLM 실패 시 — 새 쿼터(STRONG/EARLY 각 MIN~MAX) 안에서 균형 분배.

    분배 규칙:
        - STRONG 수 = clamp(round(N/3), STRONG_MIN, STRONG_MAX).
        - 나머지 EARLY 는 MED/WEAK 를 라운드로빈 (MED 우선).
        - EARLY 수가 EARLY_MAX 를 초과하면 초과분은 STRONG 으로 이동
          (단 STRONG_MAX 한도 내에서). 이래도 안 맞으면 안전한 최소 분배로 fallback.
    """
    n = len(labels)
    n_strong = max(REF_STRONG_QUOTA_MIN, min(REF_STRONG_QUOTA_MAX, round(n / 3) or 1))
    n_early = n - n_strong

    if n_early > REF_EARLY_QUOTA_MAX:
        overflow = n_early - REF_EARLY_QUOTA_MAX
        bump = min(overflow, REF_STRONG_QUOTA_MAX - n_strong)
        n_strong += bump
        n_early -= bump
    if n_early < REF_EARLY_QUOTA_MIN and n_strong > REF_STRONG_QUOTA_MIN:
        shift = min(REF_EARLY_QUOTA_MIN - n_early, n_strong - REF_STRONG_QUOTA_MIN)
        n_strong -= shift
        n_early += shift

    n_med = (n_early + 1) // 2
    n_weak = n_early - n_med

    print(
        f"  ↳ Stage 4 fallback: N={n} → STRONG={n_strong} "
        f"MED={n_med} WEAK={n_weak}"
    )

    sequence = (["STRONG"] * n_strong) + (["MEDIUM"] * n_med) + (["WEAK"] * n_weak)
    out: List[Dict[str, str]] = []
    for lbl, strength in zip(labels, sequence):
        out.append({
            "label_ko": lbl,
            "strength": strength,
            "rationale_ko": (
                "Fallback — LLM 실패로 분포 기반 안전 strength 부여. "
                "후속 재실행을 통해 정밀 평가 필요."
            ),
        })
    return out


# ══════════════════════════════════════════════════════════════
# 7. Stage 5 — Keyword Hint Mint
# ══════════════════════════════════════════════════════════════

STAGE5_SYSTEM = """\
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

STAGE5_USER = """\
## Base Event 참고
- title: {base_title}

## 대상 시나리오 ({scenario_id})
- title: {scenario_title}
- description: {scenario_description}

## 입력 Signpost label ({n_signposts}개) — 이 순서를 유지하여 hints 출력
{label_block}

## 산출
- hints 길이 = {n_signposts}.
- 각 항목의 keyword_hints 는 3~5개.
"""

STAGE5_HARD = """\

[중요한 출력 제약 — Stage 5]
- hints 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력과 정확히 일치 (echo).
- keyword_hints 는 3~5개. 모든 항목 비어있지 않은 문자열.
- 고유명사 1개 이상 + 동사·상태어 1개 이상 포함 권장.
"""

STAGE5_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE5_SYSTEM),
    ("human", STAGE5_USER),
])


def stage5_mint_keywords(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
) -> List[List[str]]:
    """Stage 5 진입점 — labels → [keyword_hints, ...] (signpost 별 3~5개).

    실패/경계 조건:
        - 길이 / label echo / 키워드 개수 위반 시 재시도.
        - LLM 실패 시 fallback (label 토큰 분할 + 정형 행위어).
    """
    scenario_id = scenario.get("scenario_id", "S_??")
    if not labels:
        return []

    chain = _build_chain(_Stage5LLMOutput)

    label_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))
    base_payload = {
        "base_title": base_event_summary.get("title", ""),
        "scenario_id": scenario_id,
        "scenario_title": scenario.get("title", ""),
        "scenario_description": _shorten(scenario.get("description", ""), 400),
        "n_signposts": len(labels),
        "label_block": label_block,
    }

    label_set = [lbl.strip() for lbl in labels]

    def _validate(out: _Stage5LLMOutput) -> None:
        if len(out.hints) != len(labels):
            raise ValueError(
                f"hints 길이 불일치: {len(out.hints)} != {len(labels)}"
            )
        out_labels = [h.label_ko.strip() for h in out.hints]
        if out_labels != label_set:
            raise ValueError(
                "hints 의 label_ko 순서가 입력과 다름. "
                f"expected={label_set}, got={out_labels}"
            )
        for h in out.hints:
            if not (KEYWORD_HINTS_MIN <= len(h.keyword_hints) <= KEYWORD_HINTS_MAX):
                raise ValueError(
                    f"keyword_hints 길이 위반 ({len(h.keyword_hints)}): "
                    f"허용 {KEYWORD_HINTS_MIN}~{KEYWORD_HINTS_MAX}"
                )
            if any(not str(kw).strip() for kw in h.keyword_hints):
                raise ValueError("keyword_hints 안에 빈 문자열 존재.")

    out = _invoke_with_retry(
        stage="Stage 5",
        chain=chain,
        base_payload=base_payload,
        hard_constraints=STAGE5_HARD,
        validate_fn=_validate,
    )

    if out is None:
        return [_stage5_fallback_keywords(lbl) for lbl in labels]

    return [[kw.strip() for kw in h.keyword_hints] for h in out.hints]


# label 토큰 분할용 — 한글/영숫자/하이픈 시퀀스 단위.
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-]+|[가-힣]+")


def _stage5_fallback_keywords(label: str) -> List[str]:
    """LLM 실패 시 — label 의 명사 토큰 + 정형 행위어로 안전 3개 키워드 구성."""
    tokens = [t for t in _TOKEN_PATTERN.findall(label) if len(t) >= 2]
    seen: set = set()
    proper: List[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        proper.append(t)
        if len(proper) >= 2:
            break
    fallback_action = "보도"  # 동사·상태어 정형 fallback.
    out = list(proper)
    if fallback_action not in out:
        out.append(fallback_action)
    while len(out) < KEYWORD_HINTS_MIN:
        out.append(f"신호{len(out)+1}")
    return out[:KEYWORD_HINTS_MAX]


# ══════════════════════════════════════════════════════════════
# 8. LLM Chain 공용 유틸 (재시도 + HARD_CONSTRAINTS 누적 + fallback)
# ══════════════════════════════════════════════════════════════
#
# [패턴] 모든 Stage 가 동일 retry 정책 / 점진적 HARD_CONSTRAINTS 강화를 공유.
#         재시도 판정은 종류별로 함수를 쪼개어 단일 책임 유지(ref 규칙 #6·#7).

_STAGE_PROMPTS: Dict[str, ChatPromptTemplate] = {}


def _register_stage_prompts() -> None:
    """Stage 별 ChatPromptTemplate 매핑 — _invoke_with_retry 가 사용."""
    _STAGE_PROMPTS["Stage 2"] = STAGE2_PROMPT
    _STAGE_PROMPTS["Stage 4"] = STAGE4_PROMPT
    _STAGE_PROMPTS["Stage 5"] = STAGE5_PROMPT


_register_stage_prompts()


def _build_chain(schema_cls: type[BaseModel]):
    """structured_output 체인 빌더 — Stage 별로 schema 만 다르게 주입."""
    llm = ChatAnthropic(
        model=REF_MODEL,
        temperature=REF_TEMPERATURE,
        max_tokens=REF_MAX_TOKENS,
    )
    return llm.with_structured_output(schema_cls)


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
    chain,
    base_payload: Dict,
    hard_constraints: str,
    validate_fn,
) -> BaseModel | None:
    """공용 LLM 호출 — 지수백오프+지터, HARD_CONSTRAINTS 누적, validation 실패 시 재시도.

    실패/경계 조건:
        - REF_MAX_RETRIES 소진 시 None 반환 → 호출부에서 fallback 으로 분기.
        - max_tokens 출력 잘림은 동일 재시도 정책으로 흡수.
    """
    prompt = _STAGE_PROMPTS.get(stage, None)
    if prompt is None:
        raise RuntimeError(f"Stage prompt 미등록: {stage}")

    last_exc: Exception | None = None
    last_validation_exc: Exception | None = None
    accumulated_hint = hard_constraints

    for attempt in range(1, REF_MAX_RETRIES + 1):
        try:
            payload = dict(base_payload)
            payload_with_hint = _augment_user_payload(
                payload, accumulated_hint, last_validation_exc, attempt,
            )
            messages = prompt.format_messages(**payload_with_hint)
            result = chain.invoke(messages)
            validate_fn(result)
            return result

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            is_api = _is_retryable_api_error(exc)
            is_schema = _is_retryable_schema_error(exc)
            is_validation = isinstance(exc, ValueError)
            should_retry = (is_api or is_schema or is_validation) and attempt < REF_MAX_RETRIES
            if not should_retry:
                print(f"  ↳ {stage} 재시도 불가 — {exc.__class__.__name__}: {str(exc)[:160]}")
                break

            if is_validation or is_schema:
                last_validation_exc = exc
                accumulated_hint = hard_constraints + (
                    f"\n[직전 실패 원인 — {stage}]\n- {str(exc)[:240]}\n"
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

    각 Stage 의 USER 텍스트는 '## 산출' 등 정형 마무리로 끝나게 작성되어 있고,
    hint 는 USER payload 끝 텍스트 키(signpost_block / label_block /
    dim_values_block / scenario_description) 에 append 하는 방식.
    """
    appended_payload = dict(payload)
    text_keys = (
        "signpost_block", "label_block", "dim_values_block",
        "price_block", "scenario_description",
    )
    target = None
    for k in text_keys:
        if k in appended_payload and isinstance(appended_payload[k], str):
            target = k
    if target is None:
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
# 9. Pipeline Orchestration  (시나리오 단위로 Stage 2→3→4→5 합성)
# ══════════════════════════════════════════════════════════════

def _build_signpost_id(scenario_id: str, idx: int) -> str:
    """sgp_S{NN}_{NN} 패턴 — scenario_id 의 'S_NN' 에서 번호 추출."""
    m = re.match(r"^S_?0*(\d+)$", str(scenario_id))
    sc_no = int(m.group(1)) if m else 0
    return f"sgp_S{sc_no:02d}_{idx:02d}"


def _extract_base_event_summary(state: Dict[str, Any]) -> Dict[str, str]:
    """state.stage1_context_pack.C1_base_event 에서 LLM 입력용 요약 발췌."""
    c1 = (state.get("stage1_context_pack") or {}).get("C1_base_event") or {}
    return {
        "title": c1.get("title", ""),
        "summary": c1.get("summary", ""),
        "driver": c1.get("driver", ""),
    }


def build_signposts_for_scenario(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
) -> List[Dict[str, Any]]:
    """단일 시나리오에 대해 Stage 2→3→4→5 를 순차 실행하고 signposts dict list 반환.

    실패/경계 조건:
        - Stage 2 가 0건을 반환하면 Stage 4/5 호출 없이 빈 리스트 반환.
        - Stage 4/5 의 길이 mismatch 는 각 Stage 내부에서 재시도 또는 fallback.
    """
    sid = scenario.get("scenario_id", "S_??")

    # ── Stage 2 ────────────────────────────────────────────────
    labels = stage2_observability_filter(scenario, base_event_summary)
    if not labels:
        print(f"  ↳ {sid}: Stage 2 통과 0건 — signposts 비어있음")
        return []

    # ── Stage 4 ────────────────────────────────────────────────
    s4_assigns = stage4_assign_direction_strength(scenario, base_event_summary, labels)
    print(
        f"  ▸ Stage 4 [{sid}] strong="
        f"{sum(1 for a in s4_assigns if a['strength']=='STRONG')} "
        f"med={sum(1 for a in s4_assigns if a['strength']=='MEDIUM')} "
        f"weak={sum(1 for a in s4_assigns if a['strength']=='WEAK')}"
    )

    # ── Stage 5 ────────────────────────────────────────────────
    s5_keywords = stage5_mint_keywords(scenario, base_event_summary, labels)
    print(
        f"  ▸ Stage 5 [{sid}] keyword 평균={_avg_len(s5_keywords):.1f}개 "
        f"(min={min((len(k) for k in s5_keywords), default=0)}, "
        f"max={max((len(k) for k in s5_keywords), default=0)})"
    )

    # ── Stage 3 + 조립 ─────────────────────────────────────────
    signposts: List[Dict[str, Any]] = []
    for idx, (lbl, assign, kws) in enumerate(zip(labels, s4_assigns, s5_keywords), start=1):
        axes = stage3_assign_axes(lbl)
        signposts.append({
            "signpost_id": _build_signpost_id(sid, idx),
            "assumption_refs": [],  # Stage 1 미진행
            "signpost_class": "observation",
            "label_ko": lbl,
            "signpost_source": axes["signpost_source"],
            "actor_nature": axes["actor_nature"],
            "direction": "SUP",
            "strength": assign["strength"],
            "weight": None,
            "rationale_ko": assign["rationale_ko"],
            "role_tag": None,
            "keyword_hints": kws,
        })
    return signposts


def run_signpost_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 0 → 2/3/4/5 통합 실행. extended state dict 반환.

    호출 순서:
        1) stage0_extend_state    : 컨테이너 부착 (deepcopy).
        2) 시나리오 루프          : Stage 2→4→5 호출.
        3) signposts 부착         : 결정론적 Stage 3 + Stage6 빈 필드는 이미 부착.
    """
    ext = stage0_extend_state(state)
    base_summary = _extract_base_event_summary(ext)

    scenarios = ext["stage4_scenario_synthesis"]["scenarios"]
    print(f"  ▸ 시나리오 {len(scenarios)}건 처리 시작")

    for sc in scenarios:
        sid = sc.get("scenario_id", "S_??")
        print(f"\n  ── Scenario {sid} ──")
        signposts = build_signposts_for_scenario(sc, base_summary)
        sc["signposts"] = signposts

    return ext


# ══════════════════════════════════════════════════════════════
# 10. I/O / Document 조립 / 터미널 요약
# ══════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shorten(text: str, n: int) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n] + " …(생략)"


def _avg_len(items: List[List[Any]]) -> float:
    if not items:
        return 0.0
    return sum(len(x) for x in items) / len(items)


def _resolve_input_path() -> Path:
    """우선순위: CLI 인자 > 환경변수 > 모듈 옆 sample 결과 파일."""
    if len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help"):
        p = Path(sys.argv[1])
        if not p.exists():
            raise FileNotFoundError(f"CLI 인자 입력 파일 없음: {p}")
        return p
    if REF_INPUT_RESULT_PATH:
        p = Path(REF_INPUT_RESULT_PATH)
        if not p.exists():
            raise FileNotFoundError(f"REF_INPUT_RESULT_PATH 가 가리키는 파일 없음: {p}")
        return p
    fallback = Path(__file__).parent / "stage_result_ev_2a58da7f4ff2.json"
    if not fallback.exists():
        raise FileNotFoundError(
            "기존 시나리오 결과 JSON 을 찾지 못함. "
            "CLI 인자, REF_INPUT_RESULT_PATH 환경변수, 또는 모듈 디렉터리 sample 결과 파일을 사용하세요."
        )
    return fallback


def load_stage_result(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)
    if "stage4_scenario_synthesis" not in state:
        raise ValueError(f"{path}: stage4_scenario_synthesis 키 누락")
    sc_n = len(state["stage4_scenario_synthesis"].get("scenarios") or [])
    print(f"  ▸ 시나리오 결과 로드: {path.name}  (scenarios={sc_n})")
    return state


def save_json(doc: Dict[str, Any], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"\n  => 저장 완료: {path.resolve()}")


def _infer_event_id_from_state(state: Dict[str, Any]) -> str:
    """C1.event_id 가 있으면 그걸 사용, 없으면 'unknown' fallback."""
    c1 = (state.get("stage1_context_pack") or {}).get("C1_base_event") or {}
    return c1.get("event_id") or "unknown"


def print_summary(ext: Dict[str, Any]) -> None:
    W = 120
    scenarios = ext["stage4_scenario_synthesis"]["scenarios"]
    c1 = (ext.get("stage1_context_pack") or {}).get("C1_base_event") or {}

    print("\n" + "═" * W)
    print(f"  ScenarioGroup: {ext.get('scenario_group_id','')}")
    print(f"  Base Event   : {c1.get('event_id','')} / {c1.get('event_type_l1_l2','')}")
    print(f"  Title        : {c1.get('title','')}")
    print("─" * W)
    print(
        f"  {'#':<4} {'sid':<7} {'#sgp':<6} {'STRONG':<8} {'MED':<6} {'WEAK':<6} "
        f"{'kw_avg':<8} {'kw_min':<7} {'kw_max':<7}"
    )

    total_sgp = 0
    total_strong = 0
    total_med = 0
    total_weak = 0
    for i, sc in enumerate(scenarios, 1):
        sps: List[Dict[str, Any]] = sc.get("signposts") or []
        n_strong = sum(1 for s in sps if s.get("strength") == "STRONG")
        n_med    = sum(1 for s in sps if s.get("strength") == "MEDIUM")
        n_weak   = sum(1 for s in sps if s.get("strength") == "WEAK")
        kw_lens  = [len(s.get("keyword_hints") or []) for s in sps]
        kw_avg   = (sum(kw_lens) / len(kw_lens)) if kw_lens else 0.0
        kw_min   = min(kw_lens) if kw_lens else 0
        kw_max   = max(kw_lens) if kw_lens else 0

        print(
            f"  {i:<4} {sc.get('scenario_id',''):<7} {len(sps):<6} "
            f"{n_strong:<8} {n_med:<6} {n_weak:<6} "
            f"{kw_avg:<8.1f} {kw_min:<7} {kw_max:<7}"
        )

        total_sgp += len(sps)
        total_strong += n_strong
        total_med += n_med
        total_weak += n_weak

    print("═" * W)
    out_of_range = sum(
        1 for sc in scenarios
        if not (REF_SIGNPOSTS_PER_SCENARIO_MIN
                <= len(sc.get("signposts") or [])
                <= REF_SIGNPOSTS_PER_SCENARIO_MAX)
    )
    print(
        f"  Σ scenarios={len(scenarios)}  signposts={total_sgp}  "
        f"strong={total_strong} medium={total_med} weak={total_weak}  "
        f"out_of_range={out_of_range}"
    )


# ══════════════════════════════════════════════════════════════
# 11. Main
# ══════════════════════════════════════════════════════════════

def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print("═" * 70)
        print("  Multi-Scenario Signpost Pipeline  —  Stage 0/2/3/4/5 통합")
        print("═" * 70)
        print("\n사용법:")
        print("  python stage_integrated_signpost.py [stage_result_ev_<id>.json]")
        print("\n환경변수:")
        print("  REF_MODEL                       Anthropic 모델 (default: claude-opus-4-1-20250805)")
        print("  REF_MAX_TOKENS                  max_tokens (default: 8192)")
        print("  REF_TEMPERATURE                 온도 (default: 0.0)")
        print("  REF_MAX_RETRIES                 Stage 별 재시도 횟수 (default: 5)")
        print("  REF_INPUT_RESULT_PATH           기존 시나리오 결과 JSON 경로")
        print("  REF_SIGNPOSTS_PER_SCENARIO_MIN  시나리오당 signpost 최소 (default: 2)")
        print("  REF_SIGNPOSTS_PER_SCENARIO_MAX  시나리오당 signpost 최대 (default: 4)")
        print("  ANTHROPIC_API_KEY               Anthropic API Key")
        sys.exit(0)

    print("═" * 70)
    print("  Multi-Scenario Signpost Pipeline  —  Stage 0/2/3/4/5 통합")
    print(f"  Model: {REF_MODEL} (Anthropic) / max_tokens={REF_MAX_TOKENS}")
    print(
        f"  Signposts/scenario: {REF_SIGNPOSTS_PER_SCENARIO_MIN}~{REF_SIGNPOSTS_PER_SCENARIO_MAX}"
    )
    print("═" * 70)

    # 입력 결과 로드
    in_path = _resolve_input_path()
    state = load_stage_result(in_path)

    # state_dict_signpost.json 빈 스키마 덤프 (기존 파일 있으면 덮어씀).
    schema_path = Path(__file__).parent / "state_dict_signpost.json"
    dump_empty_signpost_schema(schema_path)

    # 파이프라인 실행
    t0 = time.time()
    ext = run_signpost_pipeline(state)
    print(f"\n  ✅ Stage 0/2/3/4/5 완료 ({time.time()-t0:.1f}s)")

    # created_at 갱신 (확장 시점 표기). 기존 키 보존을 위해 None 일 때만 채움.
    if not ext.get("created_at"):
        ext["created_at"] = _now_iso()

    print_summary(ext)

    event_id = _infer_event_id_from_state(ext)
    out_path = Path(__file__).parent / f"stage_result_extended_{event_id}.json"
    save_json(ext, out_path)
    print(f"  IDE에서 {out_path.name} 파일을 여세요.\n")


if __name__ == "__main__":
    main()

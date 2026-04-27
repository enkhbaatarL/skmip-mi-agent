"""
MI Record Analysis Pipeline
────────────────────────────
LangChain + Claude 기반으로 LNG 뉴스 기사에서 record_analysis 태그를 일괄 추출합니다.
스키마: mi_record.schema.yaml > MIRecord > record_analysis

Usage:
    ANTHROPIC_API_KEY=sk-ant-xxx python mi_record_analysis.py

Output:
    mi_record_analysis_results.yaml  ← IDE에서 바로 열기 가능
"""

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Set, Tuple

import yaml
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════════
# 1. Pydantic Models  (스키마 mi_record.schema.yaml 정합)
# ══════════════════════════════════════════════════════════════

class EntityType(str, Enum):
    country      = "country"
    company      = "company"
    facility     = "facility"
    organization = "organization"
    other        = "other"

class Entity(BaseModel):
    name:        str        = Field(description="엔티티 정규 명칭 (한국어 또는 영어)")
    entity_type: EntityType = Field(description="엔티티 유형")

class OccurrencePrecision(str, Enum):
    exact   = "exact"
    day     = "day"
    month   = "month"
    quarter = "quarter"
    year    = "year"
    unknown = "unknown"

class EventTiming(BaseModel):
    occurrence_time: str = Field(
        default="",
        description="이벤트 실제 발생 시점. ISO-8601 또는 빈 문자열. 예: '2026-03-03T00:00:00Z'",
    )
    occurrence_time_precision: OccurrencePrecision = Field(
        default=OccurrencePrecision.unknown,
        description="occurrence_time 정밀도",
    )

class ImpactIndex(str, Enum):
    JKM  = "JKM"
    HH   = "HH"
    TTF  = "TTF"
    NBP  = "NBP"
    NONE = "None"

class ImpactDirection(str, Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"
    unclear = "unclear"

class SupplyDemandSide(str, Enum):
    supply  = "supply"
    demand  = "demand"
    both    = "both"
    none    = "none"
    unclear = "unclear"

def _load_category_pairs_and_guide() -> Tuple[Set[Tuple[str, str]], str]:
    base_dir = Path(__file__).parent
    candidates = [
        base_dir / "event_type_taxnomy.json",   # 요청된 파일명(오타 포함) 우선 시도
        base_dir / "event_type_taxonomy.json",  # 실제 파일명
    ]
    taxonomy_path = next((p for p in candidates if p.exists()), None)
    if taxonomy_path is None:
        raise FileNotFoundError("event_type_taxnomy.json 또는 event_type_taxonomy.json 파일을 찾을 수 없습니다.")

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs: Set[Tuple[str, str]] = set()
    guide_lines: List[str] = []
    for node in data.get("taxonomy", []):
        level_1 = node.get("level_1_code", "")
        children = node.get("children", [])
        level_2_codes: List[str] = []
        for child in children:
            level_2 = child.get("level_2_code", "")
            if level_1 and level_2:
                pairs.add((level_1, level_2))
                level_2_codes.append(level_2)
        if level_1 and level_2_codes:
            guide_lines.append(f"- {level_1}: {', '.join(level_2_codes)}")

    return pairs, "\n".join(guide_lines)

ALLOWED_CATEGORY_PAIRS, CATEGORY_GUIDE = _load_category_pairs_and_guide()

class CategoryAnalysis(BaseModel):
    level_1: str = Field(description="event_type_taxnomy(event_type_taxonomy) 기준 level_1_code")
    level_2: str = Field(description="event_type_taxnomy(event_type_taxonomy) 기준 level_2_code")
    entities: List[Entity] = Field(default_factory=list)
    event_timing: EventTiming = Field(default_factory=EventTiming)
    regions: List[str] = Field(default_factory=list)
    supply_demand_side: SupplyDemandSide = Field(default=SupplyDemandSide.unclear)
    score: float = Field(ge=0, le=10, description="해당 record가 이 카테고리에 부합하는 정도 (0~10)")
    reason: str = Field(default="", description="score 근거")

    @model_validator(mode="after")
    def validate_category_pair(self):
        if (self.level_1, self.level_2) not in ALLOWED_CATEGORY_PAIRS:
            raise ValueError(
                f"유효하지 않은 category 조합: ({self.level_1}, {self.level_2}). "
                "event_type_taxnomy/event_type_taxonomy의 level_1_code+level_2_code 조합만 허용됩니다."
            )
        return self

class RecordAnalysis(BaseModel):
    """MI Record LNG 가격 분석 태그 세트"""
    categories:    List[CategoryAnalysis] = Field(
        default_factory=list,
        description="반드시 1개 이상의 category를 포함해야 함",
    )
    analysis_time: str = Field(default="")

    @model_validator(mode="after")
    def validate_categories(self):
        # 중복 조합은 에러 대신 점수가 높은 항목만 남겨 자동 정리
        dedup = {}
        for c in self.categories:
            key = (c.level_1, c.level_2)
            if key not in dedup or c.score > dedup[key].score:
                dedup[key] = c
        self.categories = list(dedup.values())
        return self


# ══════════════════════════════════════════════════════════════
# 2. Prompt
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
당신은 LNG(액화천연가스) 시장 분석 전문가입니다.
주어진 뉴스 기사를 분석하여 LNG 가격(JKM, HH, TTF, NBP) 예측에 활용할 구조화된 분석 태그를 추출합니다.

## 분석 지침

### categories (리스트)
- 하나의 record에 대해 복수 category를 추출할 수 있습니다.
- categories는 반드시 1개 이상이어야 하며, 빈 리스트([])는 절대 허용되지 않습니다.
- 동일 level_1+level_2 조합 중복은 금지합니다.
- 각 category 원소마다 아래 필드를 채우세요:
  - level_1, level_2 (반드시 아래 taxonomy 조합 중 하나)
  - entities (리스트)
  - event_timing (단일)
  - regions (리스트)
  - supply_demand_side (단일: supply / demand / both / none / unclear)
  - score (0~10)
  - reason (score 근거)

### category taxonomy (level_1 -> allowed level_2)
{CATEGORY_GUIDE}

### entities
- category별로 이벤트를 일으키거나 직접 영향을 받는 주체만 포함합니다.
- entity_type: country(국가) / company(기업) / facility(설비·터미널) / organization(기관·단체) / other

### event_timing
- category별 이벤트 실제 발생 시점. ISO-8601("2026-03-03T00:00:00Z") 또는 빈 문자열("").
- occurrence_time_precision: exact / day / month / quarter / year / unknown

### regions
- category별 이벤트와 직접 관련된 지역. 예: "중동", "동북아", "유럽", "북미", "호주", "남아시아"
"""

USER_PROMPT = """\
다음 뉴스 기사를 분석하여 RecordAnalysis 태그를 추출하세요.

## 기사 제목
{title}

## 기사 본문
{body}
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT.format(CATEGORY_GUIDE=CATEGORY_GUIDE)),
    ("human",  USER_PROMPT),
])

HARD_OUTPUT_CONSTRAINTS = """\

[중요한 출력 제약]
- categories 리스트는 반드시 1개 이상 채우세요.
- 빈 리스트([])를 절대 반환하지 마세요.
- taxonomy에 있는 level_1/level_2 조합만 사용하세요.
- 가장 관련도 높은 카테고리 1개라도 반드시 포함하세요.
"""


# ══════════════════════════════════════════════════════════════
# 3. 10개 기사 데이터 (ARTICLES)
#     DB 테이블 `tmd_mi_record` 스키마에 맞춘 dict 리스트.
#     - mi_record_id        : int unsigned
#     - first_created       : datetime (Record 최초생성일시)
#     - crt_usr_logn_id     : varchar(50)
#     - crt_dtm             : datetime
#     - mod_usr_logn_id     : varchar(50)
#     - mod_dtm             : datetime
#     - del_yn              : char(1)  (Y/N)
#     - record_type         : varchar(20)  (NEWS / REPORT / EMAIL)
#     - source_obj_id       : int unsigned (원문 소스 객체 FK)
#
#     NOTE: `source`, `title`, `body` 필드는 `tmd_mi_record` 컬럼에는 존재하지 않는다.
#     실제 운영에서는 `source_obj_id` 가 가리키는 별도 소스 객체 테이블
#     (예: `tmd_news_article`) 에서 조회된다. 여기서는 LLM 분석 입력으로 쓰기 위해
#     스키마 외 보조 정보로 동일 dict 안에 포함해 둔다.
# ══════════════════════════════════════════════════════════════

ARTICLES = [
    # ── Record #1 ──────────────────────────────────────────────
    {
        # tmd_mi_record 컬럼
        "mi_record_id":      1,
        "first_created":     "2026-03-23T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-23T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-23T00:00:00",
        "del_yn":            "N",
        "record_type":       "NEWS",
        "source_obj_id":     1,
        # 스키마 외 (source_obj_id가 가리키는 원문 소스 객체에서 조회되는 값)
        "source":            "American Press",
        "title": "U.S. Gulf LNG poised to fill gap after Qatar plant damage",
        "body": """\
Iranian missile strikes late Wednesday caused extensive damage to the Ras Laffan
Industrial City, the world's largest LNG export hub capable of loading several
super-sized tankers simultaneously and processing over 77 million tons of gas annually.
The disruption has wiped out approximately 17% of Qatar's LNG capacity, leading to
forced suspensions on long-term contracts to Italy, Belgium, South Korea and China.
Qatar officials estimate LNG production units with 12.8 million tons of annual capacity
that were expected to come online in 2026 will instead take three to five years to repair.

U.S. Henry Hub natural gas futures for delivery in April settled Friday at $3.01/MMBtu.
The benchmark Japan-Korea market traded Friday at $22.35/MMBtu.
LNG plants in Texas and Louisiana already account for about 25% of all global export capacity.

In 2026, Houston-based Venture Global expects to bring LNG production units online at its
Plaquemines plant in Louisiana, while Golden Pass LNG, a joint venture between ExxonMobil
and state-owned QatarEnergy, commenced operations in December and will continue to ramp up
output through the end of 2026.

On March 13, U.S. Secretary of Energy Chris Wright authorized an immediate 13% increase
in exports at the Plaquemines plant, allowing additional LNG shipments of up to
0.45 billion cubic feet per day.
""",
    },

    # ── Record #2 ──────────────────────────────────────────────
    {
        "mi_record_id":      2,
        "first_created":     "2026-03-11T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-11T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-11T00:00:00",
        "del_yn":            "N",
        "record_type":       "REPORT",
        "source_obj_id":     2,
        "source":            "Wood Mackenzie",
        "title": "The Strait of Hormuz closure pressures LNG spot prices, threatens Northeast Asia demand",
        "body": """\
Northeast Asia's LNG market faces a major supply shock following the closure of the Strait
of Hormuz, with regional demand expected to fall by 4-5 million tonnes through Q3 2026 if
supply disruptions last for two months, according to new analysis from Wood Mackenzie.

The closure has removed 1.5 million tonnes per week (2.2 bcm) from global LNG supply,
equivalent to 19% of global exports. With around 90% of LNG exports from Qatar and the UAE
destined for Asia, the region is most exposed to the disruption.

Asian LNG spot prices have surged above USD 20/MMBtu, shifting from a discount to a premium
relative to European prices. South Korea faces greater exposure at elevated prices. While its
LNG stocks provide a temporary buffer, moderate supply gaps and over 20% spot LNG exposure
strain power utilities. Coal switching can reduce spot needs.

Wood Mackenzie previously projected 4.4 Mt growth in Northeast Asian LNG demand in 2026,
but the Strait of Hormuz disruption is likely to halt that expansion.
Taiwan region could be one of the most exposed LNG importers globally.
Qatar and the UAE accounted for 8.4 Mt, or 35%, of Taiwan region's LNG imports in 2025.
""",
    },

    # ── Record #3 ──────────────────────────────────────────────
    {
        "mi_record_id":      3,
        "first_created":     "2026-03-09T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-09T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-09T00:00:00",
        "del_yn":            "N",
        "record_type":       "NEWS",
        "source_obj_id":     3,
        "source":            "Bloomberg / Morgan Stanley",
        "title": "Qatar LNG Outage Erases 2026 Supply Surplus, Morgan Stanley Says",
        "body": """\
The halt of production in major liquefied natural gas exporter Qatar is likely to remove
most of a glut forecast for this year, according to Morgan Stanley.

Any extension in the Qatar LNG outage beyond one month quickly brings a deficit,
analysts including Devin McDermott said in a note dated March 8.

Before the escalation of the conflict in the Middle East, Morgan Stanley predicted that
the global LNG market, with a volume of approximately 420 million tons per year in 2026,
would face a surplus of up to 6 million tons amid the launch of new projects in the US.

The bank also moved its forecast for the first shipments from Qatar's North Field expansion
project to the first quarter of 2027, removing about 1 million tons from its 2026 supply
forecast. The country's energy minister told the Financial Times that any restart and
resumption of supplies could take weeks or even months.
""",
    },

    # ── Record #4 ──────────────────────────────────────────────
    {
        "mi_record_id":      4,
        "first_created":     "2026-03-22T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-22T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-22T00:00:00",
        "del_yn":            "N",
        "record_type":       "NEWS",
        "source_obj_id":     4,
        "source":            "Anadolu Agency / Rystad Energy",
        "title": "Damaged Qatar LNG facility may take up to 5 years to recover",
        "body": """\
Restoring output at Qatar's Ras Laffan is not primarily a question of funding but of supply
chain constraints, as only three global manufacturers produce the large-frame turbines required
for LNG operations. These suppliers entered 2026 with order books already stretched by strong
demand linked to data center expansion and the global shift away from coal.

Even with immediate capital deployment, procurement delays alone could push meaningful recovery
several years out, with full restoration timelines extending up to five years.

The scale of damage and long lead times for critical equipment could result in slow recovery
at Ras Laffan, said Audun Martinsen, head of supply chain research at Rystad Energy.

The disruption forms part of a broader regional energy shock triggered by the conflict, which
has damaged LNG plants, refineries and fuel infrastructure across the Middle East.
The prolonged outage is expected to have lasting implications for global LNG supply,
particularly for European and Asian markets that rely heavily on Qatari exports.
""",
    },

    # ── Record #5 ──────────────────────────────────────────────
    {
        "mi_record_id":      5,
        "first_created":     "2026-03-20T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-20T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-20T00:00:00",
        "del_yn":            "N",
        "record_type":       "REPORT",
        "source_obj_id":     5,
        "source":            "World Oil / Wood Mackenzie",
        "title": "Ras Laffan attacks could reshape global LNG supply as outage timeline extends",
        "body": """\
Attacks on Qatar's Ras Laffan hub have removed nearly 20% of global LNG supply, with Wood
Mackenzie warning the disruption could last months or longer, tightening markets, delaying
new capacity and reshaping global gas flows.

The disruption also threatens to delay Qatar's North Field East expansion, which was expected
to add 32 MMtpa of capacity. Any slippage into 2027 or beyond could constrain global LNG
supply growth through 2028.

Asian buyers, which account for roughly 90% of Qatar's LNG exports, are expected to be most
affected, with demand likely to weaken amid higher prices. In Europe, reduced LNG availability
may limit storage injections and accelerate fuel switching.

Qatar produced an average of 6.7 MMt of LNG per month in 2025, meaning even a five- to
six-month disruption would push global supply into year-on-year decline. Each additional month
of downtime could remove roughly 1.5% of annual LNG availability.
""",
    },

    # ── Record #6 ──────────────────────────────────────────────
    {
        "mi_record_id":      6,
        "first_created":     "2026-03-18T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-18T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-18T00:00:00",
        "del_yn":            "N",
        "record_type":       "NEWS",
        "source_obj_id":     6,
        "source":            "PGJ Online / Reuters",
        "title": "U.S. Gas Futures Stall as Freeport LNG Outage Counters Supply Drop",
        "body": """\
U.S. natural gas futures held steady on March 17 as a decrease in demand from the temporary
shutdown of a liquefaction train at Freeport LNG's export plant in Texas offset a bullish
drop in supply likely due to freezing pipes in North Dakota.

Front-month gas futures for April delivery rose one cent, or 0.3%, to settle at $3.033/MMBtu.
That lack of price movement also came despite bearish forecasts for milder weather and lower
heating demand over the next couple of weeks.

Average gas flows to the nine big U.S. LNG export plants slid to 18.5 bcfd so far in March,
down from a record 18.7 bcfd in February.

In the U.S. cash market, average prices at the Waha Hub in West Texas remained in negative
territory for a record 28 days in a row as pipeline constraints trapped gas in the Permian,
the nation's biggest oil-producing shale basin.
""",
    },

    # ── Record #7 ──────────────────────────────────────────────
    {
        "mi_record_id":      7,
        "first_created":     "2026-03-27T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-27T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-27T00:00:00",
        "del_yn":            "N",
        "record_type":       "NEWS",
        "source_obj_id":     7,
        "source":            "Bloomberg / Hydrocarbon Processing",
        "title": "Australia's biggest LNG plants suffer outages due to cyclone, straining global supply",
        "body": """\
A powerful tropical cyclone in Western Australia has disrupted production at the country's two
biggest liquefied natural gas plants run by Chevron and Woodside, exacerbating a global supply
crunch caused by the conflict in the Middle East.

Chevron said it was working to restore production at its Gorgon (15.6 MMtpy, 3 trains) and
Wheatstone (8.9 MMtpy, 2 trains) LNG facilities following outages due to Tropical Cyclone
Narelle, a Category 3 storm that made landfall on Friday. Woodside also said production at
its North West Shelf project (14.3 MMtpy) was disrupted.

Santos confirmed its 3.7-MMtpy Darwin LNG project was also temporarily offline.
MST Marquee analyst Saul Kavonic estimated the cyclone was disrupting more than 30 MMtpy of
Australian LNG supply. Combined with the Middle East shock, more than a quarter of global LNG
supply was currently affected.

Australia became the world's second-largest LNG exporter after Qatar shut down production.
Asian LNG prices rose more than 90% since the US and Israel first struck Iran.
""",
    },

    # ── Record #8 ──────────────────────────────────────────────
    {
        "mi_record_id":      8,
        "first_created":     "2026-03-09T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-09T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-09T00:00:00",
        "del_yn":            "N",
        "record_type":       "REPORT",
        "source_obj_id":     8,
        "source":            "Global LNG Hub (JOGMEC)",
        "title": "Natural gas prices weekly update - JKM, TTF and Henry Hub (9 March 2026)",
        "body": """\
The Northeast Asian assessed spot LNG price JKM (April delivery) for the week of 2-6 March
rose to low-USD 20s/MMBtu on 6 March from high-USD 10s/MMBtu the previous weekend.
JKM surged to low-USD 15s/MMBtu on 2 March amid rising supply concerns following escalating
tensions in the Middle East after Israeli and U.S. attacks on Iran starting on 28 February.
On 3 March, the price jumped by more than USD 10 to mid-USD 20s/MMBtu after an air strike on
Qatar's Ras Laffan forced the shutdown of LNG export facilities, marking the highest level
in more than three years.

The U.S. gas price HH rose to USD 3.2/MMBtu on 6 March from USD 2.9/MMBtu, driven by
expectations that Middle East tensions could increase demand for U.S. LNG exports.

EIA reported U.S. natural gas inventories as of 27 February at 1,886 Bcf, down 132 Bcf from
the previous week, up 6.5% from the same period last year, and down 2.2% from the five-year average.
""",
    },

    # ── Record #9 ──────────────────────────────────────────────
    {
        "mi_record_id":      9,
        "first_created":     "2026-04-06T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-04-06T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-04-06T00:00:00",
        "del_yn":            "N",
        "record_type":       "REPORT",
        "source_obj_id":     9,
        "source":            "Canada LNG Group (JOGMEC)",
        "title": "Natural gas prices weekly update - JKM, TTF and Henry Hub (6 April 2026)",
        "body": """\
Natural gas prices fell across Asia, Europe and the United States last week, with JKM, TTF and
Henry Hub all declining amid recovering LNG supply, milder weather expectations and softer demand.

The Northeast Asian assessed spot LNG price JKM (May delivery) fell to high-USD 17s/MMBtu on
2 April from mid-USD 20s/MMBtu the previous weekend. JKM fell sharply as Australian LNG
production facilities that were shut due to cyclones resumed operations and expectations grew
for an easing of geopolitical tensions in the Middle East.

METI announced that Japan's LNG inventories for power generation as of 29 March stood at
2.19 million tonnes, down 0.19 million tonnes from the previous week.

The European gas price TTF (May delivery) fell to USD 16.9/MMBtu on 2 April from
USD 18.3/MMBtu. HH also declined, settling around USD 3.0/MMBtu.
""",
    },

    # ── Record #10 ──────────────────────────────────────────────
    {
        "mi_record_id":      10,
        "first_created":     "2026-03-16T00:00:00",
        "crt_usr_logn_id":   "system",
        "crt_dtm":           "2026-03-16T00:00:00",
        "mod_usr_logn_id":   "system",
        "mod_dtm":           "2026-03-16T00:00:00",
        "del_yn":            "N",
        "record_type":       "REPORT",
        "source_obj_id":     10,
        "source":            "ING Think",
        "title": "Energy markets brace for a prolonged supply disruption",
        "body": """\
Energy markets are having to continuously price in a more prolonged disruption to oil and gas
flows through the Strait of Hormuz, with little sign of de-escalation.

For the global LNG market, there is even less flexibility on the supply side, with the disruption
in Persian Gulf flows hitting around 20% of global LNG trade. New capacity ramping up in the US
this year at just 15 bcm of annual capacity falls short of the 110 bcm of annual production
currently disrupted. The only real solution in the short term is demand destruction.

ING outlined three scenarios:
- Scenario 1 (Base): Hormuz flows remain cut off until end of March, gradual recovery in Q2.
  Near-normal flows by start of Q3 2026.
- Scenario 2 (Optimistic): Quick de-escalation, energy flows back to near-normal by May 2026.
- Scenario 3 (Aggressive): Intense conflict continues into April, gradual recovery June-August.

A more prolonged disruption means producers will reduce upstream production to manage storage
constraints, further prolonging recovery even after the Strait reopens.
""",
    },
]


# ══════════════════════════════════════════════════════════════
# 4. Chain  &  Async Batch Runner
# ══════════════════════════════════════════════════════════════

def build_chain():
    # 기본 모델을 상향(최신 고성능 계열)하고, 필요 시 환경변수로 오버라이드 가능
    model_name = os.getenv("MI_ANALYSIS_MODEL", "claude-opus-4-1-20250805")
    max_tokens = int(os.getenv("MI_ANALYSIS_MAX_TOKENS", "8192"))
    llm = ChatAnthropic(model=model_name, temperature=0, max_tokens=max_tokens)
    return PROMPT | llm.with_structured_output(RecordAnalysis)

def _is_retryable_api_error(exc: Exception) -> bool:
    """Anthropic 과부하/레이트리밋 계열(429/529)만 재시도."""
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 529}:
        return True

    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    retry_keywords = ("overloaded", "rate limit", "too many requests")
    return any(k in name or k in msg for k in retry_keywords)

def _is_retryable_schema_error(exc: Exception) -> bool:
    """Structured output/Pydantic 검증 실패 계열은 재시도로 보정."""
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    schema_keywords = (
        "validationerror",
        "structured",
        "categories",
        "min_length",
        "json",
        "output parsing",
    )
    return "validation" in name or any(k in msg for k in schema_keywords)

def _is_max_tokens_incomplete_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    keywords = (
        "max_tokens",
        "stop reason",
        "output is likely incomplete",
        "incomplete",
    )
    return all(k in msg for k in ("max_tokens", "stop reason")) or any(k in msg for k in keywords)

def _shorten_text_for_retry(text: str, attempt: int) -> str:
    """max_tokens 실패 시 재시도할수록 본문을 점진적으로 축약."""
    if attempt <= 1:
        return text

    ratio_by_attempt = {2: 0.8, 3: 0.65, 4: 0.5}
    ratio = ratio_by_attempt.get(attempt, 0.4)
    keep_chars = max(1200, int(len(text) * ratio))
    shortened = text[:keep_chars].rstrip()
    if len(shortened) < len(text):
        shortened += "\n\n[알림] 출력 안정성을 위해 본문을 핵심 위주로 축약했습니다."
    return shortened

def _build_body_for_attempt(body: str, attempt: int, last_exc: Exception | None) -> str:
    """재시도 시 출력 제약을 점진 강화."""
    body_for_attempt = body
    if last_exc is not None and _is_max_tokens_incomplete_error(last_exc):
        body_for_attempt = _shorten_text_for_retry(body_for_attempt, attempt)

    hint = HARD_OUTPUT_CONSTRAINTS
    if last_exc is not None and attempt >= 3:
        hint += f"\n[직전 실패 원인]\n- {str(last_exc)[:240]}\n"
    return f"{body_for_attempt}\n\n{hint}"

def _guess_fallback_category_pair(article: dict) -> Tuple[str, str]:
    """기사 텍스트와 taxonomy 코드 토큰 겹침으로 최선의 fallback 카테고리 선택."""
    text = f"{article.get('title', '')} {article.get('body', '')}".lower()
    words = set(re.findall(r"[a-z0-9_]{3,}", text))
    sorted_pairs = sorted(ALLOWED_CATEGORY_PAIRS)
    if not sorted_pairs:
        raise RuntimeError("허용 category taxonomy가 비어 있습니다.")

    best_pair = sorted_pairs[0]
    best_score = -1
    for pair in sorted_pairs:
        tokens = set(re.findall(r"[a-z0-9]{3,}", f"{pair[0]} {pair[1]}".lower()))
        overlap = len(tokens & words)
        if overlap > best_score:
            best_pair = pair
            best_score = overlap
    return best_pair

def _build_fallback_result(article: dict, last_exc: Exception | None) -> RecordAnalysis:
    """LLM 호출이 끝내 실패해도 categories 비어있지 않은 안전 결과를 생성."""
    level_1, level_2 = _guess_fallback_category_pair(article)
    reason = "LLM 분석 실패로 taxonomy 기반 fallback category를 할당했습니다."
    if last_exc is not None:
        reason += f" (error: {str(last_exc)[:160]})"

    return RecordAnalysis(
        categories=[
            CategoryAnalysis(
                level_1=level_1,
                level_2=level_2,
                entities=[],
                event_timing=EventTiming(),
                regions=[],
                supply_demand_side=SupplyDemandSide.unclear,
                score=0.1,
                reason=reason,
            )
        ]
    )

async def analyze_one(chain, article: dict, idx: int, total: int) -> dict:
    mi_id = _mi_record_id_from_article(article, idx - 1)
    print(f"  [{idx:02d}/{total}] 분석 중 (mi_record_id={mi_id}): {article['title'][:50]}...")
    max_retries = 9
    last_exc: Exception | None = None
    result: RecordAnalysis | None = None

    for attempt in range(1, max_retries + 1):
        try:
            body = _build_body_for_attempt(article["body"], attempt, last_exc)
            result: RecordAnalysis = await chain.ainvoke({
                "title": article["title"],
                "body":  body,
            })
            if not result.categories:
                raise ValueError("LLM 출력에서 categories가 비어 있음")
            break
        except Exception as exc:
            last_exc = exc
            is_api_error = _is_retryable_api_error(exc)
            is_schema_error = _is_retryable_schema_error(exc)
            is_max_tokens_error = _is_max_tokens_incomplete_error(exc)
            should_retry = (is_api_error or is_schema_error) and attempt < max_retries

            if not should_retry:
                break

            # Exponential backoff + jitter로 동시 재시도 충돌 완화
            wait_sec = min(20.0, 1.5 ** (attempt - 1)) + random.uniform(0, 0.7)
            if is_api_error:
                reason = "API 과부하/레이트리밋"
            elif is_max_tokens_error:
                reason = "max_tokens 출력 잘림"
            else:
                reason = "출력 파싱/스키마 불일치"
            print(
                f"    ↳ 재시도 사유: {reason} ({attempt}/{max_retries}). "
                f"{wait_sec:.1f}s 후 재시도..."
            )
            await asyncio.sleep(wait_sec)

    if result is None:
        print(
            "    ↳ 경고: 재시도 소진. fallback category로 결과를 생성합니다."
        )
        result = _build_fallback_result(article, last_exc)

    result.analysis_time = datetime.now(timezone.utc).isoformat()
    # Enum 등을 순수 scalar로 변환해 YAML 직렬화 호환성 유지
    return result.model_dump(mode="json")

async def run_batch(articles: list) -> list:
    """전체 기사 병렬 분석 (Semaphore로 동시 호출 최대 3개 제한)"""
    chain = build_chain()
    sem   = asyncio.Semaphore(3)

    async def safe_analyze(article, idx):
        async with sem:
            return await analyze_one(chain, article, idx, len(articles))

    tasks = [safe_analyze(a, i + 1) for i, a in enumerate(articles)]
    return await asyncio.gather(*tasks)


# ══════════════════════════════════════════════════════════════
# 5. YAML 결과 저장  (IDE 가독성 최적화)
# ══════════════════════════════════════════════════════════════

class _IdeDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True   # 중복 참조 앵커(&id001) 비활성화 → 가독성 향상

def _str_list_representer(dumper, data):
    """짧은 문자열 리스트 → 한 줄 인라인"""
    if data and all(isinstance(x, str) for x in data):
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=False)

def _str_representer(dumper, data):
    """빈 문자열 → '' 명시 출력"""
    if data == "":
        return dumper.represent_scalar("tag:yaml.org,2002:str", "", style="'")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

_IdeDumper.add_representer(list, _str_list_representer)
_IdeDumper.add_representer(str,  _str_representer)


def _mi_record_id_from_article(article: dict, index: int) -> int:
    """ARTICLES dict → tmd_mi_record.mi_record_id 정수."""
    raw = article.get("mi_record_id")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    # 하위호환: 과거 "record_01" 형태의 id 도 허용
    m = re.match(r"(?i)record_0*(\d+)", str(article.get("id", "")))
    if m:
        return int(m.group(1))
    return index + 1


def build_yaml_doc(articles: list, analyses: list) -> dict:
    """record_analysis 중간 YAML 문서를 조립.

    records[] 구성:
      1) tmd_mi_record 컬럼 (mi_record_id ~ source_obj_id) — DB 스키마 정합
      2) source / title / body — tmd_mi_record 에는 없는 컬럼이지만, 본 파이프라인이
         실제로 활용하는 핵심 입력 데이터이므로 1급 필드로 함께 출력한다.
         (운영 환경에서는 source_obj_id 가 가리키는 별도 소스 객체 테이블에서 조회됨)
      3) analysis_time, categories — LLM 분석 결과. 다음 단계(mi_event_extraction.py)
         입력으로 사용되는 본 파이프라인 산출물.
    """
    records = []
    for i, (art, ana) in enumerate(zip(articles, analyses)):
        mi_id = _mi_record_id_from_article(art, i)
        records.append({
            # ── tmd_mi_record 컬럼 ──────────────────────────────
            "mi_record_id":      mi_id,
            "first_created":     art.get("first_created", ""),
            "crt_usr_logn_id":   art.get("crt_usr_logn_id", ""),
            "crt_dtm":           art.get("crt_dtm", ""),
            "mod_usr_logn_id":   art.get("mod_usr_logn_id", ""),
            "mod_dtm":           art.get("mod_dtm", ""),
            "del_yn":            art.get("del_yn", "N"),
            "record_type":       art.get("record_type", "NEWS"),
            "source_obj_id":     art.get("source_obj_id", mi_id),
            # ── 원문 소스 객체 데이터 (스키마 외, LLM 분석 입력으로 활용) ──
            "source":            art.get("source", ""),
            "title":             art.get("title", ""),
            "body":              art.get("body", ""),
            # ── LLM 분석 결과 (다음 단계 입력) ──────────────────
            "analysis_time":     ana.get("analysis_time", ""),
            "categories":        ana.get("categories", []),
        })

    summary = []
    for i, (art, ana) in enumerate(zip(articles, analyses)):
        cat_items = ana.get("categories", [])
        summary.append({
            "mi_record_id": _mi_record_id_from_article(art, i),
            "record_type":  art.get("record_type", ""),
            "source":       art.get("source", ""),
            "title":        art.get("title", ""),
            "categories": [
                {
                    "level_1": c["level_1"],
                    "level_2": c["level_2"],
                    "score": c["score"],
                }
                for c in cat_items
            ],
        })

    return {
        "_meta": {
            "description":  "MI Record 배치 분석 결과 — LNG(JKM/HH) 가격 예측용 태그",
            "input_table":  "tmd_mi_record",
            "schema_note":  "records[].mi_record_id..source_obj_id 컬럼은 tmd_mi_record 스키마 정합. "
                            "source/title/body 는 스키마 외 원문 소스 객체 데이터 (LLM 입력으로 활용). "
                            "analysis_time/categories 는 본 파이프라인 중간 산출물(DB 미저장).",
            "generated":    datetime.now(timezone.utc).isoformat(),
            "total":        len(records),
        },
        "summary": summary,
        "records": records,
    }


def save_yaml(doc: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ════════════════════════════════════════════════════════════\n")
        f.write("# MI Record Analysis Results  —  LNG Price Tag Extraction\n")
        f.write("# ════════════════════════════════════════════════════════════\n\n")
        yaml.dump(
            doc,
            f,
            Dumper=_IdeDumper,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=100,
        )
    print(f"\n  => 저장 완료: {path.resolve()}")


# ══════════════════════════════════════════════════════════════
# 6. 터미널 요약 출력
# ══════════════════════════════════════════════════════════════

def print_summary(articles: list, analyses: list) -> None:
    W = 120
    print("\n" + "═" * W)
    print(f"  {'#':<4} {'mi_record_id':<14} {'record_type':<10} {'카테고리(상위/하위)':<72} {'개수':<6}")
    print("─" * W)
    for i, (art, ana) in enumerate(zip(articles, analyses), 1):
        categories = ana.get("categories", [])
        cat_text = ", ".join(f"{c['level_1']}/{c['level_2']}({c['score']})" for c in categories) or "-"
        mi_id = _mi_record_id_from_article(art, i - 1)
        rtype = str(art.get("record_type", ""))
        print(
            f"  {i:<4} {mi_id:<14} {rtype:<10} {cat_text:<72} {len(categories):<6}"
        )
    print("═" * W)


# ══════════════════════════════════════════════════════════════
# 7. Main
# ══════════════════════════════════════════════════════════════

async def main():
    OUTPUT_PATH = Path("mi_record_analysis_results.yaml")

    print("═" * 65)
    print("  MI Record Batch Analysis  —  LNG Price Tag Extraction")
    print(f"  총 {len(ARTICLES)}개 기사  →  {OUTPUT_PATH.name}")
    print("═" * 65)

    t0       = time.time()
    analyses = await run_batch(ARTICLES)
    elapsed  = time.time() - t0

    print(f"\n✅ 분석 완료  ({elapsed:.1f}s / {len(ARTICLES)}건)")

    print_summary(ARTICLES, analyses)

    doc = build_yaml_doc(ARTICLES, analyses)
    save_yaml(doc, OUTPUT_PATH)
    print("  IDE에서 mi_record_analysis_results.yaml 파일을 여세요.\n")


if __name__ == "__main__":
    asyncio.run(main())
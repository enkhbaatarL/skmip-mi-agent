# generate_from_query flow 따라가기 — 호르무즈 재개 + 동시 한파 사례

> ⚠️ **2026-10-06 구조 단순화 이전의 실행 기록이다.** 이후 바뀐 점:
> - `validate_premises`(전제 판정 LLM) → `build_fact_timeline`(LLM 없이 시점표만 계산). 전제 P1~P9·`premise_ids`·`meta.premiseValidation` 제거, 대신 `meta.factTimeline{targetDate, entries}`.
>   시나리오 기준일은 `plan_search` 가 `query_plan.scenario_date` 로 정한다.
> - 초안은 단일 값: `drafts/validations/type_assignments/saved_event_ids` → `draft/validation/type_assignment/saved_event_id`, `draft_key` 제거.
> - 응답 축소: 기본 응답은 본문·사용 근거·검증 요약(issues)·meta 만. 토픽별 사실·시점표·claim 은 요청 `debug=true` 일 때 `debug` 블록에만 담는다. `keyFacts` 제거, `meta.warnings` 에서 검증 이슈 중복 제거.
>   시점표에 `PAST_EVENT`(기준일 전 일회성 사건) 추가 — 과거 사례가 ACTIVE 로 판정되던 문제 수정.
> - `merge_evidence` 노드 제거: 검색 노드가 결과를 바로 `EvidenceItem` 으로 바꿔 `evidences`(누적 reducer)에 덧붙인다. `web_documents`·`existing_events` state 필드 제거.
> - `route_decision`·`initial_route`·`QueryPlan.normalized_query/keywords/route/route_reason`·`TopicBrief.key_facts`(응답에서만 생성)·`EvidenceItem.score`·`declared_severity`·`confidence` 제거.

> 실행일: 2026-10-05 · 브랜치 `feat/event_gen_web`(작업 중 변경 포함) · 총 소요 **207.7초**
> 실행 방법: 그래프를 `astream(stream_mode="updates")` 로 1회 실행해 노드별 state 변경분을 기록함.
> LLM·웹 검색·MI MCP 는 실제 호출, **DB insert(`persist_events`)만 모의 처리**(가짜 `mi_event_id=-1`).

## 0. 입력

```json
{
  "userQuery": "호르무즈 해협 통항이 2026년 12월 완전 재개되어 카타르 Ras Laffan LNG 설비 가동률이 2027년 1월 정상 수준으로 회복된 상황에서, 2027년 1월 중순 독일·네덜란드·영국에 평년보다 6℃ 낮은 한파와 약 10일간 둔켈플라우테(풍력 발전 비중 평소 대비 절반 이하)가 겹치고 한국·일본도 평년보다 4℃ 낮은 한파를 겪는다면, 재개된 카타르 물량은 유럽과 아시아 중 어디로 배분되고 JKM은 어떻게 움직일까?"
}
```

## 1. 한눈에 보기

이 flow 는 한 문장을 **"근거로 뒷받침된 가상 이벤트 1건"** 으로 바꾼다. 단계는 크게 다섯 묶음이다.

| 묶음 | 노드 | 한 줄 역할 | 이번 실행 |
|---|---|---|---|
| ① 질의 분석 | `classify_route` → `plan_search` | 어디서 찾을지 정하고, 요청을 토픽으로 쪼개 검색어를 만든다 | `both`, 토픽 3개 |
| ② 근거 수집 | `search_web` ∥ `search_existing_events` → `merge_evidence` | 토픽별로 검색하고 공통 근거 형태로 모은다 | 웹 21 + 기존 이벤트 7 = 28건 |
| ③ 근거 정리 | `summarize_topics` | 토픽별로 관련 근거만 고르고 사실을 뽑는다 | T1·T3 found, **T2 not found** |
| ④ 생성 + 검증 | `validate_premises` → `draft_events` → (`validate_claims` ∥ `classify_event_type`) → `join_draft_review` | 전제 판정 → 초안 작성 → claim 검증·유형 분류 | 초안 1건, error 0, 재작성 없음 |
| ⑤ 저장·응답 | `persist_events` → `finalize` | 저장 가능한 초안만 insert, 응답 조립 | 1건 저장(모의) |

```
classify_route ─► plan_search ─┬─► search_web ─────────────┐   (route=both 라 둘 다 병렬)
                               └─► search_existing_events ─┤
                                                           ▼
                                                    merge_evidence
                                                           ▼
                                                   summarize_topics ──(근거 없는 토픽 → 반대 분기 1회, both 면 생략)
                                                           ▼
                                                   validate_premises
                                                           ▼
                                          ┌──────►  draft_events
                                          │        ┌─────┴──────┐
                               (fixable   │  validate_claims  classify_event_type
                                error 시  │        └─────┬──────┘
                                재작성 1회)└──── join_draft_review
                                                           ▼
                                                   persist_events ─► finalize
```

### 노드가 주고받는 것 = `GenerateFromQueryState`

노드는 state 전체를 받아 **바꾼 필드만** 돌려준다. 그래서 "입력 = 앞 노드가 채운 필드", "출력 = 이 노드가 채우는 필드"로 읽으면 된다.

| state 필드 | 채우는 노드 | 읽는 노드 |
|---|---|---|
| `user_query`, `date_from/to`, `language` | (요청) | 거의 전부 |
| `route_decision`, `route`, `initial_route` | classify_route | plan_search, routing, summarize_topics |
| `query_plan` (topics, keywords, impact_chain, 기간) | plan_search | 검색 노드, merge, premises |
| `web_documents` | search_web | merge_evidence |
| `existing_events` | search_existing_events | merge_evidence |
| `evidences` | merge_evidence | summarize 이후 전부 |
| `topic_briefs` | summarize_topics | premises, draft, claims |
| `pending_fallback`, `fallback_*` | summarize_topics | routing, 검색 노드 |
| `premise_validation` | validate_premises | draft, claims, finalize |
| `drafts` | draft_events | claims, classify, persist, finalize |
| `validations`, `pending_revision`, `revision_count` | validate_claims | routing, persist, finalize |
| `type_assignments` | classify_event_type | persist, finalize |
| `saved_event_ids` | persist_events | finalize |
| `warnings`, `branch_errors` | 여러 노드(누적 reducer) | finalize |
| `result` | finalize | API 응답 |

---

## 2. 노드별 상세

### ① classify_route — 근거를 어디서 모을지 결정 (5.1s, SPEED LLM)

- **목적**: 요청이 웹 최신 정보가 필요한지, MI DB 의 기존 이벤트를 다루는지, 둘 다인지 판단.
- **입력**: `user_query`
- **출력**: `route_decision{route, route_reason}`, `route`, `initial_route`
- **이번 결과**: `route = both`
  > "호르무즈 통항 재개·Ras Laffan 회복이라는 기준 시나리오·관련 기존 이벤트를 식별하고, 한파·둔켈플라우테 영향 판단을 위해 웹에서 최신 수급·유사 사례를 보완해야 함"
- **의미**: `both` 라서 이후 두 검색이 병렬로 돌고, **폴백(반대 분기 재검색)은 일어나지 않는다**.

### ② plan_search — 요청을 토픽으로 쪼개고 검색어 생성 (11.3s, SPEED LLM)

- **목적**: 사건·주제 단위(토픽)로 나눠 토픽마다 검색 질의를 만든다. 검색·정리는 토픽 단위로 격리된다.
- **입력**: `user_query`, `route_decision`
- **출력**: `query_plan{normalized_query, keywords, topics[], impact_chain[], date_from, date_to}`
- **이번 결과**

| topic | label (LLM 생성) | event_keyword (MI 검색용) | web_queries |
|---|---|---|---|
| T1 | 호르무즈 통항 재개와 Ras Laffan 정상화 | 호르무즈 | `Strait of Hormuz LNG flows Qatar Ras Laffan export capacity share` / `Qatar Ras Laffan LNG production capacity trains exports Europe Asia destination flexibility` |
| T2 | 북서유럽 한파와 둔켈플라우테 | 둔켈플라우테 | `Europe cold snap dunkelflaute gas demand wind generation TTF LNG imports history` / `Germany Netherlands UK dunkelflaute cold weather gas power demand LNG price impact` |
| T3 | 한국·일본 한파와 동북아 LNG 수요 | 한파 | `Japan Korea cold snap LNG demand JKM spot price impact history` / `Northeast Asia winter cold spell LNG spot demand Japan Korea JKM` |

  - `impact_chain`(영향 경로 4단계): 호르무즈·Ras Laffan 정상화 → 카타르 가용 물량 회복 / 북서유럽 한파 → TTF 지지 / 한·일 한파 → JKM 매수 압력 / 동시 수요 충격 → 지역 간 경쟁·JKM-TTF 스프레드
  - 기간: `date_from=""`, `date_to=2026-10-05`(기간 언급 없음 → 오늘까지). 웹은 기본 최근 90일로 좁힘.

### ③-a search_existing_events — MI DB 기존 이벤트 검색 (0.9s, MCP)

- **목적**: 토픽의 `event_keyword` 로 `mi_events_list` → `mi_event_detail` 을 호출해 기존 이벤트를 근거로 수집.
- **입력**: `query_plan.topics[].event_keyword`, 기간
- **출력**: `existing_events[]` (각 항목에 `topic_key`)
- **이번 결과**: T1(호르무즈) 5건, T2(둔켈플라우테) **0건**, T3(한파) 2건 — 토픽당 상한 5건.
  - T1: 7월 호르무즈 통항 중단·JKM 상승 관련 이벤트들(id 1287 등)
  - T3: "아르헨티나 겨울 수요", "독일 가스 수요" — 키워드 `한파` 가 넓어서 한·일과 무관한 이벤트가 걸림

### ③-b search_web — 웹 검색 (42.1s, Responses API)

- **목적**: 토픽별 `web_queries` 를 설정된 provider 전부로 검색. 먼저 공식·1차 출처 도메인(source registry)으로 제한해 검색하고, 0건인 토픽만 제한 없이 재검색.
- **입력**: `query_plan.topics[].web_queries`, 기간
- **출력**: `web_documents[]` (각 항목에 `topic_key`, `provider`)
- **이번 결과**: 질의 6개 × provider 1개 = 검색 6회 → 인용 43건 수집 → 토픽별 URL dedup → **21건 채택(토픽당 7건)**. registry 범위에서 모든 토픽이 결과를 얻어 재검색 없음.
- ⚠️ `tavily` 는 `config.yaml` 에 있으나 factory 에서 주석 처리돼 `PROVIDER_INIT_FAILED` ERROR 로그 후 제외됨 → 실제 provider 는 `responses` 하나.
- ⚠️ **웹 문서 `content` 가 본문이 아니라 인용 표식뿐**: 예) `T1-W1.content = "([eia.gov](https://www.eia.gov/todayinenergy/detail.php?id=65584))"`. 자세한 원인은 §4.

### ④ merge_evidence — 공통 근거로 정규화 (0.0s, LLM 없음)

- **목적**: 웹 문서와 기존 이벤트를 같은 모양(`EvidenceItem`)으로 바꾸고 토픽 안에서 키를 매긴다. 이후 노드는 출처를 몰라도 된다. **필터링은 하지 않는다.**
- **입력**: `web_documents`, `existing_events`, `query_plan.topics`
- **출력**: `evidences[]`
- **이번 결과**: 28건

| topic | 웹(W) | 기존 이벤트(E) | 비고 |
|---|---|---|---|
| T1 | W1~W7 (EIA, IEA, QatarEnergy 페이지) | E1~E5 (본문 2,300~2,900자) | 실질 내용은 E 쪽에만 있음 |
| T2 | W1~W7 (Copernicus 여름 폭염, IEA·ICIS 전망) | 없음 | 한파·둔켈플라우테 직접 근거 없음 |
| T3 | W1~W7 (IEA, EIA, Platts JKM 2021 최고치 등) | E1~E2 (아르헨티나, 독일) | 웹은 제목만 의미 있음 |

### ⑤ summarize_topics — 토픽별 관련 근거 선별 + 사실 추출 (11.5s, SPEED LLM × 토픽 3개 병렬)

- **목적**: 검색에 섞인 무관한 결과를 걸러내고, 관련 근거에서 시점·상태가 붙은 사실(`facts`)을 뽑는다. 관련 근거가 없는 토픽은 반대 분기 재검색을 예약한다.
- **입력**: `user_query`, `query_plan.topics`, `evidences`(토픽별로 잘라서)
- **출력**: `topic_briefs[]`, `pending_fallback` (+ 필요 시 `fallback_route`, `fallback_topic_keys`), `warnings`
- **이번 결과**

| topic | found | 고른 근거 | 뽑은 사실 |
|---|---|---|---|
| T1 | ✅ | E3, E4, E2, W1, W3 | 6건 — 7/17 주간 호르무즈 LNG 통항 사실상 중단(ACTUAL·OUTAGE), 세계 LNG 약 20% 통과(STATUS), 비롤 IEA 발언(FORECAST) 등 |
| T2 | ❌ | — | 0건. 사유: "유럽 일반 기후·에너지 전망 또는 여름 고온·건조만 다룸" |
| T3 | ✅ | W5, E1, W6 | 4건 — 2021-01-07 Platts JKM $20.705 사상 최고(ACTUAL), 일본 2026 수요 전망 61.3Mt(FORECAST) 등 |

- `pending_fallback = false`: T2 가 비었지만 `route=both` 라 이미 양쪽을 다 돌았으므로 재검색하지 않음 → 경고만 남김.
- 사실의 출처 키가 관련 근거 목록에 없으면 그 키는 버림(이번에 `T1-E5` 1건 `UNKNOWN_EVIDENCE` 경고).

### ⑥ validate_premises — 생성 전에 전제를 근거와 대조 (53.3s, QUALITY LLM + 코드)

- **목적**: 요청이 깔고 있는 전제를 원자 단위로 나눠 "사실인지 / 가정인지 / 근거와 충돌하는지" 판정하고, 기준일 사실 시점표를 만든다. 결과는 초안 생성의 **제약 조건**이 된다.
- **입력**: `user_query`, `topic_briefs`(+관련 근거), `query_plan.impact_chain`, 오늘 날짜
- **출력**: `premise_validation{target_date, premises[], timeline[]}`, `warnings`
- **이번 결과**: 기준일 `target_date = 2027-01-15`

| id | origin | support | shock_cluster | 전제 |
|---|---|---|---|---|
| P1 | EVIDENCED_FACT | PARTIAL | | 2026-10-05 기준 호르무즈 LNG 통항은 차질 상태 |
| P2 | EVIDENCED_FACT | SUPPORTED | | 호르무즈는 세계 LNG 약 20% 통과 항로 |
| P3 | USER_ASSUMPTION | PARTIAL | 호르무즈 통항 정상화 | 2026년 12월 통항 완전 재개 |
| P4 | EVIDENCED_FACT | UNSUPPORTED | | Ras Laffan 가동률이 기준일 이전 정상 이하 (← LLM 이 추가한 숨은 전제) |
| P5 | USER_ASSUMPTION | UNSUPPORTED | Ras Laffan 정상화 | 2027년 1월 Ras Laffan 정상 회복 |
| P6 | USER_ASSUMPTION | UNSUPPORTED | | 배분 가능한 재개 물량 존재 |
| P7 | USER_ASSUMPTION | UNSUPPORTED | 북서유럽 기상 | 독·네·영 평년 -6℃ 한파 |
| P8 | USER_ASSUMPTION | UNSUPPORTED | 북서유럽 기상 | 약 10일 둔켈플라우테 |
| P9 | USER_ASSUMPTION | UNSUPPORTED | 동북아 기상 | 한·일 평년 -4℃ 한파 |

  - 사용자 가정(USER_ASSUMPTION)이 UNSUPPORTED 인 것은 **정상**(시나리오 조건이므로). `hard_conflict` 는 0건.
  - 시점표(코드, `temporal.py`): 호르무즈 OUTAGE 사실들은 7월 관측 이후 종료 시점이 없어 기준일에 **STALE**, JKM 2021 최고치는 ACTIVE, 일본 2026 수요 전망은 **ENDED**(유효기간 2026 < 기준일).
  - 경고: P4 처럼 "현재 사실 전제인데 근거 없음"만 경고로 남김.

### ⑦ draft_events — 이벤트 초안 작성 (51.5s, QUALITY LLM)

- **목적**: 사용자 요청 + 토픽별 정리 결과 + 관련 근거 + 전제 판정·시점표를 묶어 이벤트 1건(제목/한줄요약/상세분석/bullet)과 그 **claim 목록**을 만든다. (existing_event 분기였다면 병합·수정 프롬프트를 썼을 것.)
- **입력**: `user_query`, `topic_briefs`, `evidences`(→ `group_prompt_evidences` 로 관련 근거만, 최대 20건), `premise_validation`, (재작성이면 이전 초안 + 검증 이슈)
- **출력**: `drafts[]` (`EventDraft`: 본문, `occurred_at`, `evidence_usages`, `claims[]`, `scenario_severity` …)
- **이번 결과**: 근거 28건 중 **8건만 프롬프트에 투입**, 초안 1건

  - 제목: **카타르 재개물량 쟁탈과 JKM 재상승**
  - 한줄요약: `[카타르 LNG 배분] 유럽·동북아 동시 한파 가정 → JKM 상승·스프레드 변동 압력`
  - occurred_at: `2027-01-15`, 선언 강도: `SEVERE_STRESS`
  - 질문에 대한 답(요지): 유럽 기상 충격으로 TTF 가 먼저 반응해 유럽 흡수 압력이 생기지만, 한·일 한파로 JKM counter-bid 가 커지면 한계 카고가 아시아로 재배치 → **한쪽 쏠림보다 유럽·동북아 분산 배분**, **JKM 상승 압력**, JKM-TTF 스프레드는 초반 축소 후 재확대 가능.
  - 실제 인용 근거: `T1-E3`(호르무즈 비중·물동 제약), `T3-W5`(2021 JKM 최고치 사례) 2건
  - claim 16개(C1~C16): 사용자 가정 6, 근거 사실 3, 모델 추론 7

### ⑧-a validate_claims — 초안 claim 검증 (29.7s, QUALITY LLM + 규칙 엔진) ∥ ⑧-b classify_event_type (2.4s)

**validate_claims**
- **목적**: 생성 LLM 의 자기 표시를 믿지 않고 claim 마다 근거 지지·시점을 재판정(LLM), 무엇을 막을지는 `claim_rules.py` 가 결정(코드). 고칠 수 있는 error 면 재작성 예약.
- **입력**: `drafts`, `evidences`, `topic_briefs`, `premise_validation`
- **출력**: `validations[]`, `pending_revision`, `revision_count`
- **이번 결과**
  - error **0**, warning 1 → `pending_revision=false`, 저장 차단 없음
  - `scenario_severity = SEVERE_STRESS` (근거로 확인 안 된 독립 충격 묶음 4개: 호르무즈 정상화 / Ras Laffan 정상화 / 북서유럽 기상 / 동북아 기상 ≥ 3 → 하한 SEVERE)
  - `feasibility_status = CONSISTENT` (근거와 모순 없음)
  - claim 판정 분포: EVIDENCED_FACT 3건 모두 SUPPORTED, MODEL_INFERENCE 7건 모두 PLAUSIBLE, USER_ASSUMPTION 6건 PARTIAL/UNSUPPORTED(정상)
  - warning: `UNMARKED_ASSUMPTION` — 제목 "카타르 재개물량"이 가정인데 가정 표시 없음 (warning 이라 재작성 트리거 아님)

**classify_event_type**
- **목적**: `tmm_mi_event_type_l2_m` 카탈로그(21개) 중 하나로 분류. 카탈로그 이름만 enum 으로 허용.
- **입력**: `drafts`, DB 카탈로그
- **출력**: `type_assignments[]`
- **이번 결과**: `event_type_l2_id = 6` (confidence 0.86) — "유럽·동북아 동시 한파로 인한 겨울 기상 수요 충격"

**join_draft_review**: 두 노드가 모두 끝나길 기다리는 합류 지점(상태 변경 없음). 이후 `route_after_validation` 이 `pending_revision=false` 를 보고 `persist_events` 로 보냄.

### ⑨ persist_events — 저장 (이번엔 모의)

- **목적**: 검증 error 없음 + 유형 분류 있음인 초안만 `tmm_mi_mievent_m` 에 한 트랜잭션으로 insert.
- **입력**: `drafts`, `validations`, `type_assignments`, `user_id`
- **출력**: `saved_event_ids{draft_key: mi_event_id}`, `warnings`
- **이번 결과**: `{"draft-1": -1}` (모의 id)

### ⑩ finalize — 응답 조립

- **목적**: 초안·검증·유형·저장 결과·경고를 API 응답 `GenerateFromQueryResult` 로 합침.
- **입력**: 거의 모든 state
- **출력**: `result{meta, events[]}`
- **이번 결과 meta 요약**: `route=both`, `fallback_used=false`, 웹 21 / 기존 7 / 근거 28, 생성 1 / 저장 1, warnings 3건:
  1. `'북서유럽 한파와 둔켈플라우테' 토픽의 관련 근거를 찾지 못했습니다(...)`
  2. `[전제 검증] 근거로 확인되지 않은 현재 사실 전제: 'Ras Laffan 가동률이 기준일 이전 정상 이하임.'`
  3. `[warning/UNMARKED_ASSUMPTION] '카타르 재개물량 쟁탈과 JKM 재상승': ...`

---

## 3. 소요 시간

| 노드 | 시간 | 비고 |
|---|---|---|
| classify_route | 5.1s | SPEED |
| plan_search | 11.3s | SPEED |
| search_existing_events | 0.9s | MCP, search_web 과 병렬 |
| search_web | 42.1s | Responses 검색 6회 병렬, 회당 34~43s |
| merge_evidence | 0.0s | |
| summarize_topics | 11.5s | 토픽 3개 병렬 |
| validate_premises | **53.3s** | QUALITY |
| draft_events | **51.5s** | QUALITY |
| validate_claims ∥ classify_event_type | 29.7s / 2.4s | 병렬 |
| persist / finalize | 0.0s | |
| **합계** | **207.7s** | QUALITY 단계 3개가 약 64% |

---

## 4. 이번 실행에서 드러난 점

1. **웹 근거에 본문이 없음 (가장 큰 문제)**
   `apps/connectors/web/provider.py` `_collect_citations` 가 `text[start_index:end_index]` 를 snippet 으로 쓰는데, Responses API 의 `url_citation` 구간은 본문 문장이 아니라 **삽입된 인용 링크 자체**(`([eia.gov](...))`)라서 content 가 링크 문자열만 남는다. 인용이 있으면 `answer` 본문도 버려진다.
   → 웹 근거 21건은 사실상 **제목만** 전달됨. T2 found=false, T1 사실이 대부분 기존 이벤트(E)에서 나온 것, 초안이 웹 근거를 1건만 쓴 것이 이 영향으로 보임.
   → 방향: 인용 구간 앞의 문장(또는 해당 문단)을 snippet 으로 잡거나, 인용이 있어도 `answer` 를 별도 근거로 남기기.

2. **Tavily 미동작**: factory 에서 주석 처리됐는데 `config.yaml` 의 `web_search_provider: "responses,tavily"` 는 그대로라 매 요청 ERROR 로그. 의도한 비활성화면 설정에서도 빼는 게 맞음.

3. **T2(북서유럽 한파·둔켈플라우테) 근거 0건인데 보완 검색 없음**: `both` 는 폴백 대상이 아니라 그대로 진행. 1번 문제가 해결되면 달라질 수 있으나, `both` 에서도 빈 토픽만 웹 비제한 재검색하는 등의 보완을 검토할 만함.

4. **기존 이벤트 키워드가 넓음**: T3 `event_keyword="한파"` 로 아르헨티나·독일 이벤트가 걸림. summarize 가 일부 걸러내지만 T3-E1(아르헨티나)은 관련 근거로 채택됨.

5. **LLM 이 만든 숨은 전제(P4)가 경고를 만듦**: "Ras Laffan 가동률이 기준일 이전 정상 이하"는 사용자가 말한 사실이 아니라 LLM 이 보충한 현재 상태 전제인데, 근거가 없어 경고로 노출됨. 사용자 입장에선 의미가 모호한 경고.

6. **근거 키 불일치 1건**: summarize LLM 이 사실 출처로 `T1-E5` 를 적었지만 자신이 고른 관련 근거 목록에는 없어 버려짐(동작상 문제는 없음).

---

## 부록: 재현

- 실행 스크립트·원본 덤프는 세션 scratchpad 에 있음(`trace_run.py`, `trace.json`, `run.log`).
- 같은 방식으로 재현하려면 `persist.EventGenerationService` 를 가짜 서비스로 바꾼 뒤 `get_compiled_graph().astream(state, stream_mode="updates")` 로 노드별 update 를 받으면 된다.

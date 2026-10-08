# 시나리오 품질 비교: 플랫폼(그룹 307) 대 워크숍 단계별 프롬프트(Lever v4)

- 작성일: 2026-10-01
- 비교 대상
  - **플랫폼**: local agent `POST /scenario-groups` → 그룹 307 (v4 파이프라인, Lever catalog v4, gpt-5.5)
  - **워크숍**: `lng_scenario_workshop_guide_v4_final.html` 프롬프트 원문(Step 0~5, 4a)을 그대로 실행. 00_input의 Catalog만 DB v4 18개 코드로 교체 (Claude Opus, 맥락 없는 서브에이전트)
- 공통 조건: 이벤트 3건(1681 스프레드 / 1682 운임 / 1683 화물흐름, 같은 순서), 분석 기준일 2026-10-01, Lever catalog v4
- 증적 위치(scratchpad)
  - 플랫폼: `g307/platform_result.md`, `g307/trace_by_stage.md`, `g307/trace_findings.md`, MLflow `tr-4fd49d68d3d8d943fd84e01303d71384`
  - 워크숍: `workshop_20261001/00_input.md` ~ `05_agent_design_review.md`

---

## 1. 결론

1. **카탈로그를 v4로 맞춰도 품질 차이는 그대로 재현됐습니다.** 워크숍 쪽은 서로 겹치지 않는 Dimension 3개(가격차 경로 / 아시아 대체 조달 / 운임 회복)를 만들었습니다. 플랫폼은 Dimension 4개 중 3개가 사실상 같은 상태(`regional_price_spread`)를 반복했습니다. 따라서 이번 표본에서 차이의 주된 원인은 Lever 카탈로그가 아니라 **파이프라인 설계**입니다.
2. 차이가 가장 크게 벌어진 곳은 **Step 1(Fact 선택)**과 **Step 3(Dimension 설계)**입니다.
   - Step 1: 플랫폼은 "Fact 가급적 1~2개" 규칙 때문에 아시아 조달경쟁 Fact를 버렸습니다. 이 때문에 "아시아 구매자 대체 조달" 축이 시작부터 사라졌습니다.
   - Step 3: 플랫폼에는 MERGE·SEPARATE_EFFECT 같은 조합 결정 절차가 없어서, 같은 Lever의 질문 6개가 Dimension 3개로 흩어지며 중복 계산이 생겼습니다.
3. **Interaction 단계의 프롬프트 표기 버그**가 결과를 바꿨습니다. 1차 응답은 워크숍과 같은 E1×E2 상쇄(넷백)를 찾았지만, Lever 표기 형식 때문에 검증에 떨어졌고, 재시도에서 관계가 E2×E3로 바뀌었습니다.
4. 운영 리스크도 확인했습니다. Dimension 단계가 게이트웨이 60초 타임아웃(504)으로 두 번 실패했고 마지막 시도에서 겨우 통과했습니다.
5. 같은 rubric으로 채점하면 의미 품질 평균은 **플랫폼 2.86 / 워크숍 3.57**입니다(4장).

---

## 2. 조건 차이 (비교의 한계)

| 항목 | 플랫폼(307) | 워크숍 | 영향 |
|---|---|---|---|
| 모델 | gpt-5.5, strict JSON schema, temperature는 모델 기본값(코드는 0.0을 넘기지만 API 요청에 포함되지 않음) | Claude Opus | 비교에 섞여 있는 변수 |
| reasoning | Step 1·2는 `low`, Step 3·4는 default | 별도 설정 없음 | 파이프라인 설계의 일부로 봄 |
| 이벤트 입력 | 제목(120자), 한 줄 요약(240자), key_bullets 5개 | 이벤트 md 전체를 읽고 00_input 작성(요약 수백 자, 핵심 사실 후보 4~5개) | 입력 정보량 차이. 파이프라인 설계의 일부 |
| 한 줄 요약 | 제가 INSERT할 때 제목과 같게 넣음 | 원문 상세분석에서 작성 | 실제 운영 데이터도 한 줄 요약이 짧아 영향은 제한적 |
| 실행 횟수 | 1회 | 1회 | 표본 1개라 재현성은 확인하지 않음 |
| 채점자 | 플랫폼은 제가 채점 | 워크숍은 서브에이전트 자체 채점 + 제가 다시 확인 | 같은 모델 계열이 채점해서 생기는 편향 가능성 |

---

## 3. 단계별 비교

### 3.1 입력 (Step 0)

| | 플랫폼 | 워크숍 |
|---|---|---|
| 요약 | `[LNG 인덱스 스프레드] JKM·TTF 가격차 … 약화` (= 제목) | "2026-08-13 싱가포르 종가 기준 … 80.7센트 … 67.7센트 … 2026-08-27 주간 요약에서는 …" (상세분석 기반, 수백 자) |
| 핵심 사실 후보 | key_bullets 5개(코드가 자동으로 넣음) | 원문을 읽고 선별한 4~5개 |
| 원문 외 정보 | 상세분석, 영향도 분석, 기관 전망 미사용 | 상세분석까지 사용 |

### 3.2 Fact와 Impact Path (Step 1)

| | 플랫폼 | 워크숍 |
|---|---|---|
| Fact 수 | E1 2 / E2 2 / E3 2 = 6 | E1 3 / E2 3 / E3 2 = 8 |
| **E1-F3 (아시아 조달경쟁)** | **제외** ("가급적 1~2개" 규칙) | **채택** → E1-P1 근거, 이후 D2(아시아 대체 조달)로 이어짐 |
| Path | 이벤트당 1개 | 이벤트당 1개 |
| Lever | E1·E3 `regional_price_spread`, E2 `lng_charter_rate` | 같음 |
| E3 Path role | `driver` 하나뿐. Interaction 카드에서 "Supporting Impact"로 잘못 표기됨 | `primary` |
| E2 balance | `trade/increase` (Lever는 decrease인데 근거가 모호함) | `trade/decrease` |
| 열린 질문 | 7개(3/2/2). 대부분 "2026-10-01 **현재** … 지속되고 **있는가**?" | 6개(2/2/2). "언제까지, 어느 범위까지"를 묻는 미래 분기형 |

두 쪽 모두 v4 카탈로그에서 E3 화물 재배분을 `regional_price_spread`로 매핑했습니다. v4의 `route_disruption`은 "물리적 transit 차질"로 정의가 좁아졌기 때문입니다. 따라서 이 매핑은 차이가 아니라 **카탈로그 공통의 한계**입니다.

### 3.3 Interaction (Step 2)

| | 플랫폼 | 워크숍 |
|---|---|---|
| I1 | E1×E3 **amplification** | E1×E3 **causal_link** (되먹임 가능성까지 서술) |
| I2 | **E2×E3** offset | **E1×E2** offset (저운임이 넷백 문턱을 낮춤) |
| materiality | 비어 있음 | medium / low |
| 질문 | Interaction당 최대 1개(2개) | 2개 |

> **trace 확인**: 플랫폼 1차 응답(create #4)은 워크숍과 같은 **E1×E2 offset**을 찾았습니다. 하지만 `lever` 필드에 카드 표기 문자열 `regional_price_spread increase (…)`을 통째로 복사해 서버 검증(`openQuestions[1].lever must be one of …`)에서 떨어졌습니다. 재시도(#5)에서 E2×E3로 바뀌었습니다. 원인은 `build_v4_interaction_analysis_user_prompt`가 Lever를 `code direction (scope, timing)` 형식으로 보여 주면서, 동시에 "code를 글자 그대로 복사하라"고 요구하는 데 있습니다.

### 3.4 Dimension과 조합 결정 (Step 3)

| | 플랫폼 | 워크숍 |
|---|---|---|
| 조합 결정 표 | **없음** (프롬프트에 해당 절차 없음) | MERGE 2 / EXCLUDE 2 / SEPARATE_EFFECT 2, Interaction 적용 조건까지 명시 |
| Dimension | d1 유럽 프리미엄 지속성 (spread) / d2 미국 화물 조달 축소폭 (spread) / d3 대서양 저운임 지속성 (charter) / d4 저운임의 전환 유도력 (charter + **spread**) | D1 동서 가격차·유럽행 경로 (spread) / **D2 아시아 구매자 대체 조달** (spread, substitution) / D3 운임 회복 시점·범위 (charter) |
| 중복 | **d1≈d2**: 같은 수치(80.7·67.7센트)와 같은 상태(스프레드 저점 지속). **d4**: d1의 spread 상태와 d3의 운임 상태를 다시 결합 → 한 시나리오 안에서 같은 효과가 2~3번 더해짐 | 없음. 같은 Lever의 질문은 MERGE로 합치고, 결합 효과는 Interaction으로만 반영 |
| Choice 시점 경계 | 모든 Choice의 timeWindow가 "분석 기준일 이후"로 같음 | "10월 중", "11월까지", "4분기 내" (가정으로 표시) |
| Choice why | 거의 모든 문장이 "08-13 80.7센트 … 08-12 67.7센트를 기반으로 … 가정"으로 반복 | `사실 / 가정 / 영향`으로 나눠 Choice마다 다른 근거 |
| Choice pressure | 3단계(bullish / balanced / bearish)만 허용 | 5단계(D1-C3, D2-C3에 strong_bullish) |
| 방향 판단 | d3_v2 "동절기 운임 회복 → bullish" (운임 상승이 JKM을 올린다는 해석이 한 줄로 끝남) | D3-C3 운임 반등 → bullish ("운송비 완화 요인 소멸"로 설명) |

> **trace 확인**: Dimension 프롬프트(create #8)의 질문 카드에서 "시장 의미" 항목이 질문 문장을 그대로 반복합니다(정보 없음). Fact 원문은 넘어가지 않고, decision basis 9문장만 근거로 주어집니다. 개수 권장은 "3~4개, unused 최소 1개"입니다. 질문 9개가 Lever 2개에만 걸려 있고 "Dimension의 lever는 source 질문에서 상속"해야 하므로, MERGE 절차가 없으면 같은 Lever 축이 여러 개 생길 수밖에 없는 구조입니다.

### 3.5 Scenario (Step 4)

| | 플랫폼 | 워크숍 |
|---|---|---|
| 생성 | strong_bullish 20 / **bullish 35 (baseline)** / balanced 30 / strong_bearish 15 | strong_bullish 20 / **bullish 40 (baseline)** / balanced 25 / strong_bearish 15 |
| 제외 | bearish (NOT_INDEPENDENT) | bearish (NOT_INDEPENDENT) |
| ceiling | 4개 축이 모두 상방. 그중 3개가 같은 spread 상태라 사실상 "스프레드 지속 + 운임 반등" | 3개 축이 모두 상방. 가격차, 아시아 입찰, 운임이 각각 독립적 |
| baseline | 프리미엄 지속 + 차익 박빙 + 저운임 + 프리미엄 우위. **유럽 프리미엄이 d1·d4에서 두 번 선택됨** | 유럽행 지속 + 일부 추가 입찰 + 저운임 (I1·I2 적용 조건 충족) |
| 중립 시나리오 | 프리미엄 일부 완화 + 박빙 + 저운임 + 부분 상쇄 | 유럽행 지속 + **태평양산 대체 성공** + 저운임. 전달 고리가 끊기는 독립 경로 |
| Interaction 적용 | LLM이 임의로 선택. 적용 규칙 없음 | Step 3 조건대로 적용 (S4와 제외 조합에는 미적용) |
| pressureBreakdown | 서버가 모든 Path mechanism과 Choice 근거를 이어 붙임(시나리오마다 거의 같음) | 시나리오별 commonImpact / choiceDelta / interactionEffect를 직접 작성 |

공통점: 둘 다 floor를 strong_bearish로 뒀습니다. 공통 영향이 상방인데도 모든 축이 하방인 조합을 floor로 둔 것으로, 워크숍 자체 검수도 이를 Minor-4로 지적했습니다. 5개 band를 반드시 채우게 하는 규칙의 부작용이며, 양쪽 공통입니다.

### 3.6 검수와 보완 (Step 4a, 5)

| | 플랫폼 | 워크숍 |
|---|---|---|
| Additional Dimension | 자동 실행, 후보 0 (미사용 질문 2개를 "겹침"으로 판단) | AD1 1개 (IU2 → 운임의 넷백 상쇄 강도) |
| 의미 품질 검수 | 없음 (형식 검증만) | Step 5: Hard Gate와 rubric, Minor 4 / NEEDS_FACT 2 |

---

## 4. 같은 기준(가이드 Step 5)으로 채점

### 4.1 Hard Gate

| gate | 플랫폼 307 | 워크숍 |
|---|---|---|
| HG-01 Event coverage | PASS | PASS |
| HG-02 Fact·Path·Lever·balance | **WARN**: E3 Path에 primary step 없음, E2 balance 방향 모호 | PASS |
| HG-03 질문 lineage·동일 상한 | **WARN**: 상한이 요청 순서에 따라 (3,3,2) — 가이드는 순서와 무관하게 Event당 3 | PASS |
| HG-04 Dimension 3~6 | PASS (4) | PASS (3) |
| HG-05 Choice 2~4·lineage·고유성 | PASS | PASS |
| HG-06 Scenario 3~5·5 band | PASS | PASS |
| HG-07 조합·band 고유성 | PASS | PASS |
| HG-08 조합 결정 반영 | **FAIL**: 조합 결정 절차 자체가 없음 | PASS |
| HG-09 미래 경계를 사실처럼 쓰지 않음 | PASS | PASS |
| HG-10 pressure 값·Lever 방향 | PASS (3단계 한정) | PASS |
| HG-11 contribution·band 순서 | PASS (합산: +4 / +1 / −1 / −4. 단, 제외된 bearish도 −1이라 balanced와 같은 점수) | PASS |
| HG-12 probability·baseline | PASS | PASS |

### 4.2 의미 품질 rubric (1~5)

| rubric | 플랫폼 307 | 근거 | 워크숍 |
|---|---:|---|---:|
| J-01 Event grounding | 3 | 수치는 정확하지만 Fact 6개로 줄었고, 아시아 조달경쟁 근거가 빠짐. why는 같은 수치만 반복 | 4 |
| J-02 Baseline 타당성 | 3 | baseline(35)과 중립(30)의 차이가 작고, baseline 안에서 같은 상태가 두 번 선택됨 | 3 |
| J-03 Spectrum·대표 경로 | 3 | floor·ceiling·혼합은 있지만 "아시아 대체 조달 성공" 같은 독립 경로가 없음 | 4 |
| J-04 Dimension·Choice 품질 | **2** | d1≈d2 중복, d4가 두 Lever 혼합, timeWindow가 모두 같음, why가 정형 반복 | 3 |
| J-05 내부 정합성 | **2** | 같은 spread 효과가 d1·d2·d4에 중복 반영됨. Interaction 적용 기준 없음 | 3 |
| J-06 Domain·geography | 4 | 지역과 시장 관계는 일관됨 | 4 |
| J-11 Clarity | 3 | narrative는 양호하지만 Dimension 질문이 "현재 …인가" 확인형이고 길이가 과도함(200자+) | 4 |
| **평균** | **2.86** | | **3.57** |

워크숍 점수는 서브에이전트 Step 5의 자체 채점입니다. 제가 같은 근거로 다시 확인했고 점수에 이견은 없습니다.

---

## 5. 원인 매핑 (처음 정리한 원인 후보와 대조)

| # | 원인 | 이번 비교에서 확인된 증상 | 판정 | 코드 위치 |
|---|---|---|---|---|
| 1 | Event 입력이 제목·요약·key_bullets로 한정됨 | 요약 = 제목, 상세분석 미사용 | 확인(영향 중간) | `prompts/model_lever_scenario_generation.py` `build_v4_event_impact_analysis_user_prompt`, `prompts/event_context.py` |
| 3 | "Fact 가급적 1~2개" 지시 | E1-F3 제외 → 아시아 대체 조달 축 소멸 | **trace로 확인(영향 큼)** | 같은 파일 출력 규칙 |
| 6 | Step 1·2 reasoning `low` | 질문이 "현재 상태 확인형"으로 쏠림, E3 role 오류 | 추정(인과관계 미분리) | `v4_nodes.py` 140·307행 |
| 8 | 이벤트별 개별 LLM 호출 | E1·E3가 같은 08-27 관측을 따로 Path로 만듦(워크숍도 같은 Minor) | 차이 작음 | `v4_nodes.py` `AnalyzeEventImpactsNode` |
| 9 | 단계 간 정보 축약 | Dimension 카드에 Fact 원문 없음, "시장 의미" = 질문 반복 | trace로 확인 | `_render_uncertainty_cards` |
| 10 | 조합 결정(MERGE / SEPARATE_EFFECT) 절차 없음 | d1≈d2, d4 혼합, 중복 계산, Interaction 임의 적용 | **확인(영향 가장 큼)** | `V4_DIMENSION_SYSTEM_PROMPT`, `build_v4_dimension_design_user_prompt` |
| 11 | 질문 예산이 순서에 따라 달라지고 Interaction 질문이 1개로 제한됨 | (3,3,2), Interaction당 1개 | 확인(이번 표본에서는 영향 작음) | `v4_budget.py` |
| 12 | Dimension 수 권장(3~4, unused 남기기) | 4개 생성 | 영향 작음 | 같은 파일 |
| 13 | Choice pressure 3단계 | 같은 방향 안에서 강약 구분 불가 | 확인(중간) | `v4_schema.py` `V4ReadableDimensionChoice.pressure` |
| 14·15 | band 순서 검증, 5 band 강제 | 양쪽 모두 strong_bearish floor | **양쪽 공통**(가이드 규칙 자체의 한계) | `_validate_scenarios` |
| 17 | pressureBreakdown 기계적 연결 | 시나리오별 설명이 거의 같음 | 확인 | `expand_v4_readable_scenario_synthesis` |
| 18 | 의미 품질 검수 단계 없음 | Step 5에 해당하는 단계 없음 | 확인 | — |
| **신규 A** | Lever catalog v4의 좁은 정의(`route_disruption`, `lng_charter_rate`) | 양쪽 모두 E3를 spread로 매핑, charter의 "전역·연간" 조건 미충족 | **양쪽 공통**. 이번 차이의 원인은 아님 | DB `tmm_mi_model_impact_lever_m` v4 |
| **신규 B** | Interaction 프롬프트의 Lever 표기와 "그대로 복사" 요구가 충돌 | 1차 응답 검증 실패 → 재시도에서 관계가 바뀜 | **trace로 확인** | `build_v4_interaction_analysis_user_prompt` (`lever_text` 형식) |
| **신규 C** | LLM 게이트웨이 60초 타임아웃 | Dimension 단계 504 두 번, 출력 6.7k 토큰 / 85초 | **trace로 확인(운영 리스크)** | 게이트웨이(nginx) 설정, `invoke_stage_structured_output` |
| **신규 D** | 재시도 피드백에 원본 오류(HTML 504 본문)가 그대로 들어감 | Dimension 3차 프롬프트에 "이전 검증 실패: 504 Gateway…"와 "동일 실수 반복 금지"가 들어감 | 확인(품질 영향은 미미, 노이즈) | `_feedback` |

---

## 6. 개선 우선순위 제안

| 순위 | 개선 | 기대 효과 | 난이도 |
|---|---|---|---|
| 1 | Dimension 프롬프트에 워크숍 Step 3의 **조합 결정 절차**(KEEP / MERGE / EXCLUDE / SEPARATE_EFFECT 표와 Interaction 적용 조건 출력)를 추가하고, Scenario 단계에 그 조건을 전달 | 중복 Dimension과 이중 계산 제거 (J-04, J-05) | 중간 (schema 확장) |
| 2 | Step 1의 "Fact 가급적 1~2개"를 "근거가 되는 Fact는 모두 선택(최대 3)"으로 완화 | 누락 경로 복원 (J-01, J-03) | 낮음 |
| 3 | Interaction 카드의 Lever 표기를 code만 보이도록 분리 (예: `- Lever code: regional_price_spread` 한 줄과 상태 설명 한 줄을 따로) | 검증 실패와 그로 인한 관계 변경 방지 | 낮음 |
| 4 | Dimension 단계 출력 길이 축소 또는 게이트웨이 타임아웃 상향 / 스트리밍 first-byte 확인 | 전체 실패 리스크 제거 | 낮음~중간 |
| 5 | Choice timeWindow와 why를 `사실 / 가정 / 영향` 구조로 바꾸고 시점 경계를 구체화하도록 지시 | Choice 변별력 (J-04, J-11) | 낮음 |
| 6 | Event 입력에 `detail_analysis` 요약(또는 일부) 추가 | grounding (J-01) | 중간 (토큰 증가) |
| 7 | Step 1·2 reasoning effort를 default로 올려 A/B 테스트 | 질문 품질 | 낮음 (비용·시간 증가) |
| 8 | Choice pressure 5단계 허용 검토 (검증 로직 점수 체계 포함) | 강약 표현 | 중간 |

---

## 7. 남은 확인 사항

- **재현성**: 같은 입력으로 플랫폼을 2~3회 더 돌려 d1≈d2 같은 중복이 반복되는지 확인해야 합니다. 이번은 1회 표본입니다.
- **모델 변수 분리**: 워크숍 프롬프트를 gpt-5.5로 실행하면 모델 차이와 파이프라인 차이를 나눌 수 있습니다.
- **개선 1~3 적용 후 회귀 비교**: 같은 3개 이벤트로 그룹을 다시 생성해 이 보고서의 rubric으로 재채점합니다.
- **테스트 데이터 정리**: 이번에 넣은 이벤트 1681~1683(`crt_usr_logn_id='workshop_20260828'`)과 그룹 307이 midb에 남아 있습니다.

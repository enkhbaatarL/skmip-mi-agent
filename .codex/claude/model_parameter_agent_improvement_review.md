# model_parameter_agent 개선 리뷰

대상: `propose_parameters` flow(`flow.py`, `nodes.py`), `mapping.py`, `persistence/model_input/*`
근거 평가: `reports/model_parameter_proposal_evaluation_event_types_6_7_20260630_233109.md` (event_type 6 한파 / 7 폭염, scenario 24건, 38분, concurrency 2, retries 2)

## 1. 동작 구조 요약
- 그래프: `load_scenario_context → select_parameter_candidates → validate_parameter_candidates(LLM) → load_basecase_samples → propose_parameter_slots(LLM) → filter_basecase_records_by_slots → propose_parameter_values(LLM)`.
- 후보(slot 대상)는 XLSX bridge sheet rule로 먼저 제한하고, LLM은 gate/slot/value 3단계로 분리. `to_output()`이 candidate별로 그룹핑해 `RecommendedParameter`로 변환.
- KB(`mapping.py`)는 openpyxl로 Excel을 파싱하고 `@lru_cache(maxsize=8)`로 캐시.

## 2. 핵심 발견 (근거 포함)

### F1. value가 basecase 비근거·물리식 휴리스틱으로 산정됨 (기준 1)
- scenario 309에서 HDD가 `intensity(℃) × 해당 월 일수`로 계산됨: 10월 155(=5×31), 11월 150(=5×30), 2월 140(=5×28). Temperature는 21개 cell이 일괄 `-5`.
- 보고서상 `basecaseValue: null`, 즉 weather parameter는 basecase_records가 비어 LLM이 앵커 없이 추정. → 값의 정확성이 모델 데이터가 아니라 프롬프트 내 변환 규칙에 의존.

### F2. 시나리오 간 차이는 있으나 시나리오 내부는 무차별 (기준 2)
- 시나리오 간: 약(289) HDD delta 77.5 vs 강(309) 155 → intensity 축으로는 차등됨(양호).
- 시나리오 내: 309에서 7개 EU 국가(Belgium~UK)가 같은 월에 모두 동일 값(155/150/140). 국가별 차이가 0이므로 country 축 fan-out은 정보량 없이 출력량만 7배로 증가.

### F3. 동일 parameter 내 slot 중복/충돌 방어 부족 (기준 3)
- `flow.py:_value_key`는 coordinates+value가 완전히 동일할 때만 병합. 따라서 같은 `(Year, Month)` 좌표가 국가만 바꿔 반복되는 잉여 slot, 그리고 같은 좌표에 값만 다른 충돌 slot을 탐지/차단하지 못함. (parameter, coordinate) 단위 유일성 보장이 없음.

### F4. rationale 분리는 구조적으로 되어 있으나 누수/보일러플레이트 존재 (기준 4)
- 분리 구조 자체는 OK: parameter는 `parameter_selection_rationale_ko`, slot/value는 `value_selection_rationale_ko + proposed_value_rationale_ko`(`flow.py:_value_rationale`).
- 누수 사례: `nodes.py:_apply_slot_coordinates_to_cells`가 모든 value rationale 앞에 "Step2에서 확정한 slot 좌표를 우선 적용했습니다."를 주입. 보고서 slot rationale에 "Step2에서 선택된 … 슬롯입니다" 필러 반복, 일부는 "candidate_mappings에서 … 직접 매핑" 등 parameter 선택 논리를 재서술.
- parameter rationale은 `" ".join(group["rationales"])`로 그룹 내 문장을 단순 연결 → 중복/장황 가능.

### F5. weather parameter용 rule-based backfill 부재 → 빈 추천 (기준 1·5 신뢰성)
- `nodes.py:_build_rule_based_adjustment`의 분기는 supplydisruption/volumecancelled/shippingcost/regasadjustment/liquefaction/useradjustedgasdemand만 처리. HDD/CDD/Temperature/PowerMix 분기 없음.
- 결과: LLM value 단계가 좌표를 확정 못하면 보강이 안 되어 빈 응답. 보고서 EMPTY 2건(307 유럽 약한 한파, 324 아시아 1년 기록적 폭염)은 후보 검증 PASS인데 `selected_parameters: []`. 가장 약/강 케이스에서 비결정적으로 누락 → 재현성 문제.

### F6. 성능 (기준 5)
- 24건 38분, scenario당 LLM 3콜 + 매 콜마다 full packet(basecase_records 포함) 재전송. 응답이 `country × month` cell로 폭증(309 단일 시나리오 98 cell).
- 지연이 기간 dimension에 비례: 309(6개월)=382s, 319=327s, 318=271s. 장기/다국가 시나리오가 비용/지연을 지배.
- KB는 lru_cache지만 `get_parameter_knowledge_base()`가 `select`·`load_basecase_samples`·`propose_parameter_slots`에서 반복 호출되고, basecase record 추출은 매 실행 시 openpyxl 재파싱.

## 3. 개선 제안

### 정확성·차별화 (F1·F2)
- weather parameter도 basecase에 앵커: HDD/CDD/Temperature를 국가·월 basecase 정상치 대비 delta로 산정하도록 basecase 추출 범위에 weather sheet 포함, `basecaseValue=null` 비율을 KPI로 관리.
- country 축 자동 확장 억제: scenario/event에 국가 차등 근거가 없으면 단일 대표 slot(예: Europe 집계) 또는 region 단위로 묶고, 국가별로 값이 동일하면 fan-out 금지 규칙을 프롬프트·sanitize에 추가.

### slot 중복 (F3)
- sanitize 단계에서 (candidate, coordinate-without-value) 유일성 강제: 동일 좌표 중복은 병합, 값 충돌 시 warning + needs_user_review. `to_output`이 아니라 value 노드 sanitize에서 1차 차단.

### rationale (F4)
- `_apply_slot_coordinates_to_cells`의 고정 문구 주입 제거 또는 별도 메타필드로 분리.
- 프롬프트에 역할 강제: parameter rationale = "왜 이 parameter인가 + high-level 변환 논리"만, slot/value rationale = "이 좌표/값 산정 근거"만. parameter 선택어휘(직접 매핑, candidate 등) slot rationale 금지를 sanitize lint로 검출.
- parameter rationale은 그룹 연결 대신 대표 1문장으로 요약.

### 신뢰성 (F5)
- weather parameter backfill 분기 추가, 또는 backfill을 canonical 하드코딩에서 "dimension→변환식" 테이블 기반으로 일반화. 빈 추천은 무조건 needs_user_review 경고를 동반하도록.

### 성능 (F6)
- slot 폭을 줄이는 상한: country×month 곱 상한, 장기 기간은 월별 대신 분기/대표월로 축약 옵션.
- LLM 호출 최적화: 동일 packet 반복 전송 축소(공통 컨텍스트 캐시/prompt caching), value 단계 candidate 병렬화, 스트리밍.
- KB/basecase 접근을 노드 간 1회 로드로 공유(state 주입).

### 구조 (기준 6, LRU·Excel DB화)
- mapping Excel(Dimension Parameter Mapping, Parameter Excel Mapping)과 basecase profile/record를 DB 테이블로 이관하고 버전 컬럼 부여. 런타임 openpyxl 파싱 제거.
- 캐시는 버전 키 기반 LRU + TTL로 교체(현재 maxsize=8 경로 인자 캐시는 파일 변경/메모리 인지 불가). basecase record는 사전 materialize(ETL)하여 조회만 수행.
- 장점: 콜드스타트 제거, 매핑 변경의 무중단 반영, weather/basecase 앵커링 데이터 확보.

## 4. 평가 기준 제안 (기준 7)
현재 보고서는 PASS/EMPTY 위주로 FAIL 신호가 없어 품질 회귀 감지가 어려움. 자동 metric 추가 권고:
1. parameter 정합도: expected vs selected의 precision/recall (현 22/24 정성 PASS → 수치화).
2. 시나리오 내 차별화: 동일 parameter에서 비-시간 축(국가 등)별 값 분산 = 0이면 경고(F2).
3. 시나리오 간 차별화: intensity/period 변화 대비 값 단조성·변화율 검증(F1).
4. slot 중복: (parameter, coordinate) 중복·충돌 건수 = 0 기대(F3).
5. rationale 누수 lint: slot rationale 내 parameter 선택어휘/보일러플레이트 출현율(F4).
6. 신뢰성: empty-recommendation rate, needs_user_review rate, fallback/backfill 사용률(F5).
7. 근거성: `basecaseValue=null` cell 비율(낮을수록 양호)(F1).
8. 성능: scenario당 latency·LLM 토큰·cell 수 예산, 기간 dimension별 회귀 추적(F6).

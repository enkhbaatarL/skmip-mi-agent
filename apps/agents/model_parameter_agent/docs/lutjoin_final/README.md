# Model Parameter LUT + Basecase 최종 머지 검토 및 의사결정 기록

- 작성일: 2026-07-10
- 작업 브랜치: design/model-param-lut-final-merge
- 문서 상태: DRAFT — 인터뷰 진행 중
- 비교 기준 브랜치:
  - Codex: feature/model-param-lut-basecase, commit 7a7a753
  - Claude: feat/lut-basecase-integration, commit 8d1f72b
  - 공통 merge base: main, commit 7ba92b8

## 1. 문서 목적

기존 model_parameter_agent는 basecase workbook만 사용해 Step2 slot과 Step3 value를 제안했다.
두 실험 브랜치는 GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment의 LUT 파일을 함께 사용하도록 확장했다.

이 문서는 다음을 한 곳에서 관리한다.

1. 두 브랜치의 구현 차이
2. 차이별 장단점과 현재 권고안
3. 코드·문서·테스트에서 발견한 결함과 운영 리스크
4. 최종 통합 구조 초안
5. 사용자 인터뷰 항목과 확정된 결정
6. 최종 머지 범위, 구현 순서, 테스트 게이트

인터뷰가 끝나기 전까지 모든 권고안은 잠정안이다. 확정된 내용은 14장 의사결정 로그에 기록한다.

## 2. 요약 결론

현재 두 브랜치 중 하나를 그대로 merge하는 것은 권장하지 않는다.

현재 가장 안전한 조합은 다음과 같다.

- LUT loader, Full Country List, horizon, feature flag: Claude 구현을 기반으로 개선
- 파라미터별 명시 join key, provenance, Step2/Step3 reference 분리, 호출별 streaming: Codex 구현에서 선별
- full LUT를 LangGraph state에 적재하는 방식: 폐기
- raw/effective record를 40,000건에서 먼저 자르는 방식: 폐기
- process-level immutable LUT index와 compact SlotCatalog를 만들고, Step2에서 선택된 좌표만 exact lookup하는 방식으로 재설계

두 브랜치는 모두 아래 기본 방향은 동일하다.

- 같은 좌표에 basecase와 LUT가 모두 있으면 basecase를 effective 기준값으로 사용
- basecase-only 좌표는 유지
- LUT-only 좌표는 LUT default를 기준값 후보로 사용
- GDP/PMI/Temperature/LiqUtil 변환은 LLM이 아니라 서버에서 수행
- reference ID와 source 정보를 내부적으로 추적

하지만 slot universe, state 크기, 실제 좌표 검증, 결과 정합성, API 의미에서 production 차단 이슈가 남아 있다.

## 3. 문서 비교에 대한 주의

Claude 브랜치의 아래 문서는 Codex 문서와 내용이 동일한 파일이다.

- lutjoin_claude/10_design_final.md
- lutjoin_claude/11_lut_vs_basecase_analysis.md
- lutjoin_claude/12_same_slot_value_check.md

따라서 두 결과가 완전히 독립된 설계라고 보기는 어렵다. 실질적인 비교 대상은 최종 코드, 후속 보정 커밋, 설정, 테스트 리포트다.

## 4. 브랜치별 구현 요약

### 4.1 Codex 구현

주요 변경 파일:

- apps/agents/model_parameter_agent/utils/lut.py
- apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py
- apps/agents/model_parameter_agent/flows/propose_parameters/state.py
- apps/agents/model_parameter_agent/prompts/model_parameter_proposal.py
- apps/connectors/llm/llm_client.py
- tests/automated/test_model_parameter_lut_integration.py

핵심 구조:

1. LutRepository가 5개 LUT를 parameter별 record로 변환한다.
2. Step2용으로 non-Liq record를 compact한다.
3. LiqUtil은 Country/Plant/Train hierarchy와 hidden metadata 복원 로직을 별도로 둔다.
4. Step3 직전에 full LUT를 다시 조회하고 basecase와 effective merge한다.
5. LLM이 cell 또는 candidate를 누락하면 서버가 현재 effective 값을 유지하는 fallback cell을 생성한다.
6. 공통 structured-output connector에 호출별 stream 파라미터를 추가한다.

### 4.2 Claude 구현

주요 변경 파일:

- apps/agents/model_parameter_agent/utils/lut_repository.py
- apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py
- apps/agents/model_parameter_agent/prompts/model_parameter_proposal.py
- apps/common/configs/config.py
- apps/connectors/llm/llm_client.py
- tests/automated/test_lut_repository.py

핵심 구조:

1. parameter별 LUT loader와 transform을 lut_repository.py에 둔다.
2. Full Country List와 2024~2031 horizon을 적용한다.
3. load_basecase_samples에서 basecase와 LUT 전체를 effective record로 병합한다.
4. 최대 40,000건으로 자른 뒤 state.basecase_records에 저장한다.
5. Step2에서는 metadata와 Period를 제외하고 hierarchy와 Year/Month 목록을 만든다.
6. Step3에는 basecase 기준값과 LUT default 비교값을 함께 제공한다.
7. reference ID 또는 좌표로 basecaseValue와 metadata를 서버에서 보정한다.
8. structured output streaming 여부를 공통 전역 설정으로 제어한다.

## 5. 차이점별 비교와 현재 권고

| 항목 | Codex | Claude | 현재 권고 |
|---|---|---|---|
| LUT 대상 국가·기간 | GDP raw 163국, Liq 2017~2050 포함 | Full Country List와 2024~2031 horizon | Claude 기반. 단, 고정 horizon은 동적 정책으로 개선 |
| GDP 성장률 | 정렬된 직전 available row 사용 | 정확한 year-1 값 사용 | Claude 방식 |
| join key | parameter별 business key 명시 | metadata 제외 나머지 축 전체 | Codex key + Claude axis alias |
| 축 이름 정렬 | 하드코딩 이름 일치 전제 | DB 단위 접미사까지 정규화 | Claude 방향. fuzzy prefix 대신 명시 alias 사용 |
| 중복 LUT | 첫 record 유지 후 warning | last-wins 또는 미매칭 중복 유지 가능 | 둘 다 개선. 값 충돌 중복은 적재 실패 |
| effective provenance | basecase/lut value와 양쪽 reference, effective_source 보존 | source와 lut_value 중심 | Codex 모델 |
| Step3의 LUT 비교값 | override 좌표의 LUT 값을 prompt에서 제외 | override 값과 LUT default를 함께 제공 | Claude 방식 |
| Step2 state | non-Liq compact, Liq 41,079건 full | 최대 40,000건 full effective state | 둘 다 폐기. compact catalog만 state에 저장 |
| slot universe cap | full universe 유지하지만 state 비대 | 40,000건 초과분 삭제 | raw cap 금지 |
| metadata 처리 | LiqUtil에 한정한 hidden-axis 복원 | 모든 parameter에서 Period/Lifecycle/Nameplate 제외 | parameter spec 기반으로 제한적 일반화 |
| 없는 시점 처리 | 가장 가까운 Year/Month로 실제 slot 변경 | 원 slot을 유지하나 unresolved 값도 통과 가능 | exact-only가 기본. nearest는 별도 review 참고값 |
| LLM 누락 처리 | 현재값 유지 cell로 자동 성공 보정 | candidate 전체를 비선택 처리 | 재시도 후 incomplete/review 처리 |
| slot 상한 | 기본 100 | 코드 기본 20, YAML/K8s 100 | candidate별 quota + global cap 분리 |
| streaming | 호출별 옵션, model parameter에서 명시 | 모든 structured output에 전역 적용 | Codex 방식 |
| 기능 rollback | LUT 전용 flag 없음 | model_parameter_lut_enabled 제공 | off/shadow/on 3단계로 확장 |
| 테스트 강점 | flow integration, Liq 복원, partial fallback | loader fixture, horizon, 축 보정, 실 LLM 리포트 | 양쪽 테스트를 통합 |

## 6. 독립 측정 결과

### 6.1 LUT record 범위

로컬 Python 3.13 환경에서 각 브랜치의 loader를 직접 실행했다.

| Parameter | Codex record | Codex 국가/기간 | Claude record | Claude 국가/기간 |
|---|---:|---|---:|---|
| GDP | 2,118 | 163국, 2019~2031 | 672 | 84국, 2024~2031 |
| PMI | 8,736 | 91국, 2024~2031 | 8,736 | 91국, 2024~2031 |
| PowerMix | 8,399 | 84국, 2022~2031 | 6,719 | 84국, 2024~2031 |
| Temperature | 8,064 | 84국, 2024~2031 | 8,064 | 84국, 2024~2031 |
| LiqUtilAdjustment | 41,079 | 24국, 2017~2050 | 30,526 | 24국, 2024~2031 |

Codex Step2 effective reference는 5개 parameter 동시 후보, basecase 없음 기준 약 42,320건이며 대부분 LiqUtil이다.

### 6.2 Claude global cap 손실

Claude의 5개 parameter LUT 합계는 54,717건이다. 40,000건 cap을 적용하면 LiqUtil은 다음과 같이 줄어든다.

- record: 30,526 → 15,809
- leaf path: 347 → 252
- Year: 2024~2031 → 2024~2030
- 일부 국가/plant/train path 소실

cap이 prompt 크기만 제한하는 것이 아니라 Step2의 유효 slot universe를 삭제한다.

## 7. 주요 검토 Findings

### P0-1. full LUT state와 raw cap 모두 부적합

Codex는 LiqUtil 41,079건을 state에 저장하고 Step3에서 다시 full LUT를 구성한다.

근거:

- feature/model-param-lut-basecase:apps/agents/model_parameter_agent/utils/lut.py:40
- feature/model-param-lut-basecase:apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py:259
- feature/model-param-lut-basecase:apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py:295

Claude는 전체 effective record를 먼저 병합한 뒤 40,000건에서 자른다.

근거:

- feat/lut-basecase-integration:apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py:254
- feat/lut-basecase-integration:apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py:295

권고:

- LUT 원본과 lookup index는 process-level immutable catalog에 보관
- state에는 compact SlotCatalog와 selected key만 저장
- Step2 완료 후 selected key만 exact lookup

### P0-2. Codex GDP slot universe가 모델 범위보다 큼

Codex GDP loader는 raw GDP table에 있는 163개국을 모두 사용한다. Full Country List 또는 모델 입력 가능 국가와 교차하지 않아 LLM이 모델에 없는 국가를 선택할 수 있다.

권고:

- model slot universe와 default value availability를 분리
- Full Country List 91개는 slot universe로 관리
- 실제 default 값이 있는 84개국은 default_available=true로 표시
- Other 계열처럼 default가 없는 slot은 unresolved 정책을 적용

### P0-3. 실제 path-time 좌표 membership 검증이 없음

두 구현 모두 비시간 hierarchy와 전역 Year/Month distinct 목록을 분리한다. 특정 Plant/Train에 존재하지 않는 Year/Month 조합도 LLM이 만들 수 있다.

Claude 최종 리포트에서는 LiqUtil 26건이 basecase와 LUT 양쪽에 없는 좌표였지만 정상 proposal에 포함됐다.

권고:

- SlotCatalog leaf마다 available period range 또는 압축 bitmap 보존
- Step2 응답을 canonical key로 바꿔 catalog membership 검사
- 양쪽 source에 없는 좌표는 자동 proposal이 아니라 unresolved/review로 분리

### P0-4. PowerMix 최종 합계 검증이 없음

LUT 원본의 Country/Year별 PowerMix 합이 1이라는 검증은 있으나, LLM 제안 후 전체 source vector 합계 검증은 없다. 일부 source만 변경하면 최종 합이 1이 아니게 된다.

권고:

- 동일 Country/Year의 전체 Energy Source vector를 Step3 context로 제공
- 서버에서 범위 및 합계 1.0 검증
- 재배분 정책이 없으면 자동 정규화하지 않고 review 처리

### P0-5. LUT universe를 proposal universe로 사용함

Codex 수동 리포트에는 broad scenario에서 PowerMix 또는 LiqUtil slot이 94~100개까지 선택된 사례가 있다. 일부는 실제 조정 없이 current value를 유지하는 no-change proposal이다.

권고:

- LUT는 lookup 가능한 universe이며 전수 proposal 목록이 아님
- 시나리오의 국가, 지역, 시설, 기간을 서버가 먼저 추출해 candidate를 줄임
- relevance ranking 후 소수 후보만 Step2에 전달
- 의미 없는 no-change cell은 최종 proposal에서 기본 제외

### P1-1. Codex nearest-time 보정이 실제 적용 좌표를 바꿈

Codex는 exact reference가 없으면 가장 가까운 month/year record를 찾아 slot의 Year/Month 자체를 바꾼다. 테스트도 2026-09 요청이 2027-01로 바뀌는 동작을 승인한다.

권고:

- 요청 slot key는 변경 금지
- nearest record는 neighbor_reference로만 제공
- nearest 사용이 필요한 경우 resolved_from/resolved_to와 사용자 검토 상태를 노출

### P1-2. LLM 누락을 정상 no-change로 위장할 수 있음

Codex는 LLM이 일부 cell 또는 candidate를 누락해도 현재 effective value를 proposed value로 넣어 selected=true 결과를 만들 수 있다. truncation과 정상적인 no-change 판단을 구분할 수 없다.

Claude는 반대로 한 cell 누락 시 candidate 전체를 비선택으로 만든다.

권고:

- 우선 동일 요청 재시도
- 계속 누락되면 incomplete 또는 review_required
- fallback을 사용한다면 generated_by=server_fallback과 fallback_reason을 구조적으로 보존
- 자동 적용 대상에서는 제외

### P1-3. basecaseValue API 의미 변경

현재 API 문서는 basecase가 없으면 basecaseValue=null이라고 정의한다. 두 브랜치는 LUT-only 좌표에서도 effective LUT 값을 basecaseValue에 넣는다.

권고 필드 초안:

- basecaseValue: 실제 basecase override 또는 null
- referenceValue: 제안 산정에 사용한 effective 값
- referenceSource: basecase_override, basecase_only, lut_default, unresolved
- lutDefaultValue
- basecaseReferenceId, lutReferenceId, lutVersion

외부 계약 변경이 어렵다면 소비자 영향 조사와 API 문서 변경을 먼저 확정해야 한다.

### P1-4. Claude 설정과 테스트 결과 불일치

Claude 코드의 model_parameter_max_parameter_slots 기본값은 20이지만 다음 배포 설정은 100이다.

- envs/config.yaml:31
- devops/k8s/configmap.yaml:65

llm_structured_stream_enabled 기본값은 false이고 배포 설정에도 true가 없다. 따라서 문서에 기록된 streaming 기반 28/28 결과가 브랜치 기본 설정으로 재현되지 않는다.

### P1-5. streaming 적용 범위

Codex는 invoke_llm_structured_output 호출별 stream 옵션을 추가해 model parameter에서만 사용한다. Claude는 공통 connector 내부에서 전역 설정을 읽기 때문에 다른 agent의 모든 structured output 호출에도 영향을 준다.

권고:

- 공통 connector는 호출별 옵션만 제공
- model parameter flow 설정에서 명시적으로 켬
- stream 중단, empty content, usage 누락, retry 테스트 추가

### P1-6. LUT 파일 오류가 조용히 basecase-only로 퇴행

파일 누락, header 변경, 빈 결과, 중복 key가 발생해도 일부 구현은 warning만 남기고 basecase-only로 계속 진행한다.

권고:

- 지원 대상 5개 parameter의 필수 LUT schema를 startup/readiness에서 검증
- 파일 hash, 필수 column, row count, uniqueness, 값 범위 검사
- 값이 다른 duplicate key는 first/last wins 금지
- LUT on 모드에서는 필수 파일 오류를 domain error로 처리

### P2-1. metadata 제외 규칙의 범위

Claude는 Period, Life Cycle, Nameplate를 모든 parameter에서 reference key와 Step2 axis에서 제외한다. LUT 미지원 LiqProdAdjustment나 RegasAdjustment의 기존 동작까지 바뀔 수 있다.

권고:

- ParameterLutSpec 또는 ParameterReferenceSpec에 key_axes와 metadata_axes를 명시
- 우선 5개 대상 parameter에만 적용
- 기존 parameter 일반화는 별도 회귀 테스트 후 수행

### P2-2. slot cap의 공정성

현재 cap은 candidate 전체에 하나의 카운터를 사용하거나 record 순서에 의존한다. 먼저 나온 parameter가 slot 예산을 모두 사용할 수 있다.

권고:

- candidate별 상한
- 전체 상한
- candidate별 최소 quota
- relevance score 기반 deterministic 정렬
- enrichment 이후 최종 cap 재검증

### P2-3. cache와 설정 결합

Claude LUT loader는 horizon을 구하기 위해 전역 Settings를 import한다. 독립 단위 테스트도 DB port 환경변수가 없으면 실패한다. 캐시는 parameter만 key로 사용해 horizon 또는 LUT version 변경을 반영하지 못한다.

권고:

- repository 생성 시 LutLoadPolicy를 주입
- cache key에 file hash/version과 horizon 포함
- 프로세스 시작 시 preload하거나 thread-safe lazy initialization 사용

## 8. 테스트 검증 결과

로컬 Python 3.13 virtualenv에서 직접 실행했다.

### 8.1 Codex

대상:

- tests/automated/test_model_parameter_lut_integration.py
- tests/automated/test_model_parameter_agent_contract.py

결과:

- 112 passed

### 8.2 Claude

대상:

- tests/automated/test_lut_repository.py
- tests/automated/test_model_parameter_agent_contract.py

결과:

- METADATA_DB_PORT=3306 주입 시 117 passed
- 환경값을 주입하지 않으면 LUT loader 6개가 전역 Settings 초기화 때문에 실패

### 8.3 수동 리포트 해석 제한

Claude 문서는 최종 28/28 scenario 성공을 기록한다. 다만 PASS 기준은 주로 다음을 확인한다.

- scenario 실행 성공
- expected mapping/parameter selected
- 두 scenario의 value signature 차이
- 좌표 누락과 중복 여부

다음은 검증하지 않는다.

- PowerMix 최종 합계 1
- slot이 실제 LUT/basecase 좌표인지
- 관련 없는 no-change slot 과다 선택
- unresolved reference의 자동 적용 가능 여부
- 최종 배포 설정으로의 재현성

Codex 문서는 최종 cleanup 이후 자동화 테스트는 재실행했지만 28개 수동 scenario 전체는 다시 실행하지 않았다고 기록한다.

## 9. 최종 구조 초안

아래 구조는 인터뷰 전 잠정안이다.

    LUT CSV
      └─ ParameterLutAdapter
           ├─ GDPAdapter
           ├─ PMIAdapter
           ├─ PowerMixAdapter
           ├─ TemperatureAdapter
           └─ LiqUtilAdapter
                    │
                    ▼
          Immutable LutCatalog / Index
          - schema·duplicate·invariant 검증
          - parameter별 exact lookup
          - compact slot hierarchy
                    │
    Basecase loader ─┤
                    ▼
          EffectiveReferenceResolver
                    │
    Scenario context ──► SlotCandidateResolver
                         - entity/region/time prefilter
                         - relevance ranking
                    │
                    ▼
                  Step2 LLM
                    │
                    ▼
              Strict SlotValidator
                    │
                    ▼
          Selected key exact reference lookup
                    │
                    ▼
                  Step3 LLM
                    │
                    ▼
          Server Materializer / Validator
          - metadata 복원
          - completeness·range·invariant 검증
                    │
                    ▼
              API/DB + provenance

## 10. 데이터 모델 초안

### 10.1 ParameterLutSpec

필드 초안:

- parameter_name
- files
- universe_source
- business_key_axes
- metadata_axes
- axis_aliases
- transform
- row_filter
- horizon_policy
- value_validator
- group_validator

### 10.2 EffectiveReference

필드 초안:

- candidate_key
- parameter_name
- canonical_slot_key
- axes
- metadata
- effective_value
- effective_source
- basecase_value
- lut_default_value
- basecase_reference_id
- lut_reference_id
- lut_version
- diagnostics

### 10.3 business key 초안

| Parameter | Business key | Metadata 또는 파생값 |
|---|---|---|
| GDP | Country + Year | 절대 GDP, 이전 연도 GDP, transform 정보 |
| PMI | Demand Country + Year + Month | reference country |
| PowerMix | Country + Year + Energy Source | Country/Year 전체 vector 정보 |
| Temperature | Country + Year + Month | HDD, CDD, transform branch |
| LiqUtilAdjustment | Country + LNG Plant + LNG Plant Train + Year + Month | Period, Life Cycle Category, Nameplate Capacity |

## 11. 현재 선별 이식 후보

### Claude에서 가져올 요소

- Full Country List 기반 모델 범위 제한
- 정확한 year-1 GDP 계산
- horizon 설정 개념
- LUT feature flag
- DB 축 이름과 LUT 축 이름 정렬 개념
- Step3에서 override 값과 LUT default를 함께 제공
- reference record 기준 metadata 보정

### Codex에서 가져올 요소

- parameter별 명시 business key
- effective_source와 양쪽 value/reference provenance
- Step2용 compact reference와 Step3용 exact reference 분리 개념
- LiqUtil hidden metadata 복원 개념
- duplicate warning과 robust scalar parsing
- 호출별 structured streaming 옵션
- partial response와 reference 누락에 대한 테스트 사례

### 그대로 가져오지 않을 요소

- Claude의 global 40,000 raw record cap
- Claude의 full effective state
- Claude의 모든 structured output 전역 streaming
- Claude의 모든 parameter 대상 metadata 제외
- Codex의 full LiqUtil state와 request당 재구성
- Codex의 raw GDP 163국 universe
- Codex의 nearest Year/Month slot 변경
- Codex의 누락 응답 자동 no-change 성공 처리
- 두 구현의 global/순서 의존 slot cap

## 12. 개선 백로그 초안

### P0 — 머지 전 필수

1. ParameterLutSpec과 canonical business key 확정
2. immutable LutCatalog와 exact lookup index 구현
3. full LUT state와 global raw cap 제거
4. Step2 strict membership validation
5. 시나리오 relevance prefilter
6. source-aware EffectiveReference 모델
7. PowerMix 최종 vector 정합성 검증
8. API provenance 계약 확정
9. LUT off 모드가 main과 동일한지 snapshot 검증

### P1 — 운영 전 필수

1. startup/readiness LUT schema 검증
2. off/shadow/on rollout
3. per-call streaming과 중단/retry 테스트
4. candidate별 quota와 global cap
5. incomplete/review 상태 모델
6. LUT file hash/version 기반 cache
7. 최종 배포 설정과 문서 일치

### P2 — 후속 개선

1. LUT mapping metadata의 DB 관리 여부 검토
2. raw test report를 CI artifact로 이동
3. prompt size, candidate count, fallback count metric 추가
4. 신규 parameter adapter 확장성 검증

## 13. 최종 머지 전 테스트 게이트 초안

1. 5개 loader fixture와 transform 결과
2. model slot universe와 value availability 분리 검증
3. basecase/LUT 전체 business key 매핑률 회귀
4. basecase override, basecase-only, LUT-only, unresolved 분기
5. 동일 duplicate와 값 충돌 duplicate 처리
6. 실제 path에 없는 Year/Month 조합 거부
7. LUT 미지원 parameter 회귀
8. feature off 시 main API snapshot 일치
9. partial LLM response, reference ID 누락, 중복 cell
10. PowerMix 합계 및 parameter별 range/invariant
11. API provenance와 기존 소비자 호환성
12. prompt token, state 직렬화 크기, cold/warm latency
13. 동시 요청 메모리와 cache race
14. 최종 코드·배포 설정으로 28개 scenario 전체 재실행

## 14. 인터뷰 의사결정 로그

| ID | 결정 항목 | 상태 | 확정 내용 |
|---|---|---|---|
| D-01 | LUT-only slot 허용 범위 | DECIDED | 5개 parameter 모두 LUT-only slot 허용. basecase 부재는 제외 사유가 아니며, scenario/event 관련성이 있으면 선택 가능 |
| D-02 | slot universe와 horizon 정책 | PENDING | 미정 |
| D-03 | effective 기준값 우선순위와 API provenance | PENDING | 미정 |
| D-04 | exact reference 부재와 nearest 처리 | DECIDED | basecase와 LUT 양쪽에 exact business-key 조합이 없으면 최종 proposal에서 제외. nearest 좌표 자동 치환 금지 |
| D-05 | scenario prefilter, ranking, slot cap | PENDING | 미정 |
| D-06 | Step3 LLM 역할과 partial fallback | PENDING | 미정 |
| D-07 | PowerMix 등 parameter별 invariant 처리 | PENDING | 미정 |
| D-08 | metadata 축 복원의 적용 범위 | PENDING | 미정 |
| D-09 | feature rollout과 streaming 설정 | PENDING | 미정 |
| D-10 | 실제 구현 기반 브랜치와 머지 순서 | PENDING | 미정 |

### 14.1 D-01 확정 — LUT-only slot 허용 범위

확정 내용:

- GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment 모두 LUT-only slot을 실제 proposal 대상으로 허용한다.
- basecase에 좌표가 없다는 이유만으로 slot을 제외하지 않는다.
- scenario/event 정보와 의미적으로 관련된 LUT slot이면 Step2에서 선택될 수 있어야 한다.
- LiqUtilAdjustment도 basecase 기존 Train으로 제한하지 않고 LUT에 있는 유효 Train을 선택할 수 있다.
- 같은 좌표에 basecase와 LUT가 모두 있는 경우의 value 우선순위와 외부 API 표현은 D-03에서 확정한다.

Codex 현재 기준:

- basecase와 LUT의 union을 Step2 후보로 사용해 LUT-only slot을 허용한다.
- non-Liq parameter는 비시간축 조합과 시간축 값을 compact record로 분리한다.
- LiqUtil은 Country/Plant/Train hierarchy와 전체 Year/Month 후보를 따로 제공한다.
- 일반 slot sanitizer는 candidate, 모호한 값, 개수 상한을 확인하지만 최종 exact 좌표가 LUT/basecase에 존재하는지는 검사하지 않는다.
- LiqUtil exact 시점이 없으면 가장 가까운 reference 시점으로 slot 자체를 바꿀 수 있다.

Claude 현재 기준:

- basecase와 LUT를 먼저 effective record로 합쳐 LUT-only slot을 허용한다.
- LUT record는 기본 2024~2031 horizon을 적용한다.
- 비시간 hierarchy와 전체 record의 Year/Month distinct 목록을 분리해 제공한다.
- metadata 축은 서버가 보정하지만 Step2 결과의 exact LUT/basecase membership 검사는 없다.
- 최종 테스트 리포트에서도 LiqUtil 일부 좌표는 basecase와 LUT 양쪽 reference가 없는 상태로 통과했다.

이 결정에서 말하는 서버 검증은 관련성을 서버가 대신 판단하거나 basecase-only로 제한한다는 의미가 아니다.
LLM이 scenario/event를 해석해 선택한 결과가 실제 모델 입력으로 적용 가능한 좌표인지 확인하는 방어 단계다.

#### 조합 오류가 발생하는 경우

조합 오류는 각 axis 값이 개별적으로는 유효하지만, 합쳐진 하나의 slot key가 실제 record로 존재하지 않을 때 발생한다.

대표적인 발생 경로:

1. hierarchy path 혼합
   - LUT에는 Canada + Plant A + Train A와 Qatar + Plant B + Train B가 각각 존재한다.
   - LLM이 Canada + Plant A + Train B처럼 서로 다른 path의 값을 섞는다.
2. leaf와 전역 시간축의 Cartesian 조합
   - 특정 planned Train은 2027년 이후 record만 존재한다.
   - Step2에는 전체 LiqUtil의 Year 목록 2024~2031이 별도로 제공된다.
   - LLM이 해당 Train과 2025년을 결합하면 각 값은 후보 목록에 있지만 완성 좌표는 존재하지 않는다.
3. metadata 불일치
   - Country/Plant/Train/Year/Month는 맞지만 LLM이 Period, Life Cycle, Nameplate Capacity를 다른 record 값으로 채운다.
   - 실제 Claude 보정 과정에서도 LLM Period 112를 record Period 103으로 고치는 사례가 있었다.
4. 축 이름 또는 단위 alias 불일치
   - Nameplate Capacity와 Nameplate Capacity (MTPA)가 같은 축으로 정렬되지 않으면 동일한 논리 좌표가 별도 좌표처럼 보이거나 merge되지 않는다.
5. prompt에서 event-explicit 신규 좌표를 허용
   - 현재 prompt는 basecase option에 없어도 scenario/event에 명시된 실제 model input이면 만들 수 있도록 허용한다.
   - 해당 좌표가 LUT에도 없으면 기준값과 authoritative metadata가 없는 proposal이 된다.

예를 들어 Rio Grande LNG T5가 2027-01부터만 LUT에 있는데 LLM이 2026-09를 선택하면 Train과 Year, Month는 각각 알려진 값이어도 Rio Grande LNG T5 + 2026-09 record는 없다. Codex는 이런 경우 2027-01로 좌표를 이동시킬 수 있고, Claude는 reference가 없는 원 좌표를 유지할 수 있다. 최종안에서는 해당 slot을 최종 proposal에서 제외한다.

서버 검증 범위 초안:

1. candidate와 parameter가 Step1에서 허용된 대상인지 확인한다.
2. axis 이름과 타입을 DB/LUT canonical spec으로 정규화한다.
3. Country, Plant, Train, Energy Source 같은 값의 조합이 basecase 또는 LUT에 실제 존재하는지 exact key로 확인한다.
4. Year/Month가 해당 leaf path에서 실제 사용 가능한 기간인지 확인한다.
5. LiqUtil의 Closed lifecycle 제외 등 parameter별 적용 가능 조건을 확인한다.
6. 유효한 LUT-only 좌표이면 LUT default를 reference로 연결하고 metadata를 서버에서 복원한다.

예시:

- basecase에 없는 Japan + 2026 + Coal PowerMix 좌표가 LUT에 있고 사건과 관련됨: 허용
- LUT에 각각 존재하는 Canada Plant와 Qatar Train을 LLM이 잘못 조합함: 최종 proposal에서 제외
- LUT Train은 존재하지만 선택 Year/Month에는 아직 유효하지 않음: 최종 proposal에서 제외

basecase와 LUT 양쪽에 모두 없는 event-explicit 좌표도 최종 proposal에서는 제외한다.

### 14.2 D-04 확정 — exact 조합 부재와 nearest 처리

확정 내용:

- parameter별 business key로 만든 exact 조합이 basecase와 LUT 양쪽에 없으면 최종 proposal에서 제외한다.
- scenario/event에 명시된 좌표라도 basecase와 LUT 양쪽에 authoritative record가 없으면 자동 proposal로 만들지 않는다.
- exact reference가 없다는 이유로 가까운 Year/Month, 다른 Plant/Train, 다른 국가 좌표로 자동 치환하지 않는다.
- 제외된 slot은 validation warning과 metric에는 남기되 API/DB의 최종 proposal value에는 포함하지 않는다.
- 한 candidate의 모든 selected slot이 제외되면 해당 candidate의 최종 selected는 false로 처리한다.

Codex 현재 기준과 차이:

- Codex는 일반 slot sanitizer에서 exact union membership을 검사하지 않는다.
- LiqUtil은 exact reference가 없을 때 가장 가까운 month/year record를 선택해 원래 slot 좌표를 변경할 수 있다.
- 따라서 확정안에서는 Codex의 nearest enrichment를 제거하고 exact lookup만 유지해야 한다.

Claude 현재 기준과 차이:

- Claude도 Step2 결과의 exact union membership을 검사하지 않는다.
- reference ID나 좌표로 기준값을 보정하지만 exact record가 없을 때 LLM proposed value가 있으면 reference 없이 통과할 수 있다.
- 따라서 확정안에서는 Step3 이전 strict validation을 추가해 reference 없는 조합이 value 제안 단계로 넘어가지 않게 해야 한다.

검증 시점과 처리 순서:

1. Step2 LLM 결과를 parameter별 canonical business key로 변환한다.
2. BasecaseIndex와 LutCatalog에서 exact key를 조회한다.
3. 양쪽에 모두 없으면 즉시 제외하고 Step3 task에 넣지 않는다.
4. 하나 이상 존재하면 effective reference를 만든 뒤 Step3에 전달한다.
5. Step3 이후에도 output cell 좌표가 선택·검증된 key와 동일한지 다시 확인한다.

LiqUtil의 business key는 Country + LNG Plant + LNG Plant Train + Year + Month다. Period, Life Cycle Category, Nameplate Capacity는 authoritative record에서 복원하는 metadata이므로 이 값이 LLM 응답과 다르다는 이유만으로 business-key 조합을 제외하지 않고 서버 값으로 교정한다.

## 15. 인터뷰 진행 원칙

각 결정은 다음 순서로 진행한다.

1. Codex 브랜치의 현재 기준과 동작 설명
2. Claude 브랜치의 현재 기준과 동작 설명
3. 두 구현의 차이 설명
4. 운영·정확성·성능 trade-off 설명
5. 권장안 제시
6. 사용자 결정 확인
7. 본 문서의 의사결정 로그와 관련 설계 문단 수정

한 번에 한 항목만 결정한다.

## 16. 다음 인터뷰 항목

D-02: slot universe와 horizon을 고정 2024~2031로 제한할지, 모델 지원 기간과 scenario/event 기간을 기준으로 동적으로 조회할지 결정한다.

## 17. 변경 이력

| 일시 | 변경 내용 |
|---|---|
| 2026-07-10 | 두 브랜치 전체 비교, 독립 측정, 테스트 결과, 구조 초안과 인터뷰 로그 최초 작성 |
| 2026-07-10 | D-01 확정: 5개 parameter 모두 scenario/event 관련 LUT-only slot 선택 허용, 서버 검증 의미 명시 |
| 2026-07-10 | 인터뷰 형식에 Codex/Claude 현재 기준을 추가하고 D-01 조합 오류 발생 조건과 예시 보강 |
| 2026-07-10 | D-04 조기 확정: basecase/LUT 양쪽에 exact 조합이 없으면 최종 제외, nearest 좌표 치환 금지 |

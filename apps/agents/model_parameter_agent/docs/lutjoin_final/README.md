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

- LUT loader, horizon, feature flag: Claude 구현을 기반으로 개선
- 국가 후보 범위: 각 parameter의 실제 LUT에 존재하는 국가를 사용하며 Full Country List 보조 파일은 사용하지 않음
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
| LUT 대상 국가·기간 | GDP raw 163국, Liq 2017~2050 포함 | Full Country List와 config horizon 적용 | 국가 범위는 각 LUT 자체 기준, 기간은 config 2026~2030. GDP 계산용 2025 lookback 허용 |
| GDP 성장률 | 정렬된 직전 available row 사용 | 정확한 year-1 값 사용 | Claude 방식 |
| join key | parameter별 business key 명시 | metadata 제외 나머지 축 전체 | Codex key + Claude axis alias |
| 축 이름 정렬 | 하드코딩 이름 일치 전제 | DB 단위 접미사까지 정규화 | Claude 방향. fuzzy prefix 대신 명시 alias 사용 |
| 중복 LUT | 첫 record 유지 후 warning | last-wins 또는 미매칭 중복 유지 가능 | 둘 다 개선. 값 충돌 중복은 적재 실패 |
| effective provenance | basecase/lut value와 양쪽 reference, effective_source 보존 | source와 lut_value 중심 | Codex 모델 |
| Step3 기준값 전달 | basecase 우선, 없으면 LUT인 effective 값 하나만 전달 | basecase override와 LUT default를 함께 전달 | Codex 방향. LLM에는 단일 기준값만 전달하고 내부에서만 두 값을 보존 |
| Step2 state | non-Liq compact, Liq 41,079건 full | 최대 40,000건 full effective state | 둘 다 폐기. compact catalog만 state에 저장 |
| slot universe cap | full universe 유지하지만 state 비대 | 40,000건 초과분 삭제 | raw cap 금지 |
| metadata 처리 | LiqUtil에 한정한 hidden-axis 복원 | 모든 parameter에서 Period/Lifecycle/Nameplate 제외 | parameter spec 기반으로 제한적 일반화 |
| 없는 시점 처리 | 가장 가까운 Year/Month로 실제 slot 변경 | 원 slot을 유지하나 unresolved 값도 통과 가능 | exact-only가 기본. nearest는 별도 review 참고값 |
| LLM 누락 처리 | 현재값 유지 cell로 자동 성공 보정 | candidate 전체를 비선택 처리 | LLM이 명시적으로 반환하고 검증을 통과한 cell만 유지. 누락 cell 자동 생성 및 candidate 전체 폐기 금지 |
| slot/reference 상한 | Step2 selected slot 100, Step3 reference 100을 전체 parameter가 공유 | Step2 코드 기본 20이나 YAML/K8s 100, Step3 reference 100을 공유 | 기존 전역 설정 2개를 100/100으로 유지하고 각 parameter task에 동일 적용. 최대치일 뿐 채워야 할 목표 수가 아님 |
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

두 브랜치의 PMI 8,736건은 t1 reference map을 이용해 t2에 없는 7개 `Other ...` 국가까지 91개국으로 확장한 현재 구현 결과다. 최종안은 t2만 사용하므로 2026~2030 기준 PMI LUT는 84개국 × 12개월 × 5년인 5,040건이다.

### 6.2 Claude global cap 손실

Claude의 5개 parameter LUT 합계는 54,717건이다. 40,000건 cap을 적용하면 LiqUtil은 다음과 같이 줄어든다.

- record: 30,526 → 15,809
- leaf path: 347 → 252
- Year: 2024~2031 → 2024~2030
- 일부 국가/plant/train path 소실

cap이 prompt 크기만 제한하는 것이 아니라 Step2의 유효 slot universe를 삭제한다.

### 6.3 GDP LUT와 Full Country List 국가 비교

2026~2030 GDP 절대값은 GDP LUT의 169개국에 모두 존재한다. 2025 값을 이용해 2026~2030 성장률을 계산할 수 있는 국가는 163개다.

- Full Country List: 91개
- GDP 성장률 계산 가능 국가: 163개
- 양쪽 공통: 84개
- GDP LUT에만 있는 성장률 계산 가능 국가: 79개
- Full Country List에만 있고 GDP 성장률을 계산할 수 없는 `Other ...` 집계 국가: 7개

최종안은 Full Country List와 교차하지 않고 GDP LUT에서 exact 전년도 값을 확보할 수 있는 163개국을 사용한다. `Demand_Model_LUT_General_value_based_t6.csv`는 최종 LUT 로딩 경로에서 제외한다.

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

### 검토 완료. GDP 국가 범위

Codex GDP loader는 raw GDP table에 있는 163개국을 모두 사용한다. Full Country List 또는 모델 입력 가능 국가와 교차하지 않아 LLM이 모델에 없는 국가를 선택할 수 있다.

Claude는 Full Country List와 교차하여 84개국으로 제한한다.

최종 결정:

- 별도 Full Country List를 국가 허용 목록으로 사용하지 않는다.
- 각 parameter의 LUT 파일에 존재하는 국가를 해당 parameter의 후보 범위로 사용한다.
- GDP는 2026~2030 각각에 대해 exact 전년도 값까지 있어 성장률 계산이 가능한 163개국을 노출한다.
- 시나리오·이벤트 관련성은 Step2 LLM이 판단하고, exact LUT 좌표가 없는 조합은 기존 결정대로 제외한다.

### P0-2. 실제 path-time 좌표 membership 검증이 없음

두 구현 모두 비시간 hierarchy와 전역 Year/Month distinct 목록을 분리한다. 특정 Plant/Train에 존재하지 않는 Year/Month 조합도 LLM이 만들 수 있다.

Claude 최종 리포트에서는 LiqUtil 26건이 basecase와 LUT 양쪽에 없는 좌표였지만 정상 proposal에 포함됐다.

권고:

- SlotCatalog leaf마다 available period range 또는 압축 bitmap 보존
- Step2 응답을 canonical key로 바꿔 catalog membership 검사
- 양쪽 source에 없는 좌표는 자동 proposal이 아니라 unresolved/review로 분리

### 검토 완료. PowerMix 최종 합계 검증 여부

LUT 원본의 Country/Year별 PowerMix 합이 1이라는 검증은 있으나, LLM 제안 후 전체 source vector 합계 검증은 없다. 일부 source만 변경하면 최종 합이 1이 아니게 된다.

초기 리뷰에서는 전체 vector 제공과 합계 검증을 권고했으나, 최종 정책에서는 PowerMix 값을 Energy Source별 독립 override로 취급한다.

- LLM이 변경 대상으로 명시한 Energy Source 값만 사용한다.
- 같은 Country/Year의 나머지 Energy Source를 자동 생성하거나 변경하지 않는다.
- 서버가 전체 합계를 1로 정규화하거나 group 전체를 제외하지 않는다.
- 각 명시 cell의 exact coordinate와 value schema 검증만 수행한다.

### P0-3. LUT universe를 proposal universe로 사용함

Codex 수동 리포트에는 broad scenario에서 PowerMix 또는 LiqUtil slot이 94~100개까지 선택된 사례가 있다. 일부는 실제 조정 없이 current value를 유지하는 no-change proposal이다.

권고:

- LUT는 lookup 가능한 universe이며 전수 proposal 목록이 아님
- horizon, Closed lifecycle, exact path 같은 객관적 유효성만 서버에서 먼저 적용
- 유효한 전체 compact catalog를 Step2에 전달하고 scenario/event 관련성은 LLM이 판단
- prompt에서 전수 열거나 최대한 많이 선택하지 말고 관련성이 높은 slot만 선택하도록 제한
- LLM이 기준값과 같은 값을 명시적으로 반환한 no-change cell은 의도된 제안으로 보고 저장
- LLM이 반환하지 않은 cell을 서버가 no-change로 자동 생성하지 않음

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

- LLM이 명시적으로 반환한 각 cell을 독립적으로 좌표·형식 검증
- 검증을 통과한 cell만 그대로 사용
- 반환되지 않은 cell을 기준값으로 자동 생성하지 않음
- 일부 cell이 누락됐다는 이유로 같은 candidate의 다른 유효 cell까지 폐기하지 않음
- 누락 수는 내부 sync/test 진단값과 metric으로만 관찰 가능

### P1-3. basecaseValue API 의미 변경

현재 API 문서는 basecase가 없으면 basecaseValue=null이라고 정의한다. 두 브랜치는 LUT-only 좌표에서도 effective LUT 값을 basecaseValue에 넣는다.

확정 방향:

- 운영 DB와 frontend용 API의 basecaseValue는 기존 의미와 구조를 유지한다.
- 실제 basecase 값이 있을 때만 basecaseValue에 저장한다.
- LUT-only slot이면 LLM 기준값으로 LUT를 사용하더라도 저장되는 basecaseValue는 null이다.
- 운영 proposal DB에는 LUT value/source 필드를 추가하지 않는다.
- 내부 테스트용 sync API는 basecase와 LUT를 함께 반환할 수 있다.

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

- `resources/lut/config/lut_parameters.yaml`에 parameter별 file, 필수 column, key_axes, metadata_axes만 명시
- 우선 5개 대상 parameter에만 적용
- 기존 parameter 일반화는 별도 회귀 테스트 후 수행

### P2-2. slot cap의 공정성

현재 cap은 candidate 전체에 하나의 카운터를 사용하거나 record 순서에 의존한다. 먼저 나온 parameter가 slot 예산을 모두 사용할 수 있다.

권고:

- 기존 전역 설정값 100을 각 parameter task에 동일하게 적용
- 전체 요청 합계 counter나 parameter별 설정 map은 사용하지 않음
- parameter별 selected slot count를 각각 검증
- 100은 목표 수가 아니라 hard maximum임을 prompt에 명시
- enrichment 이후에도 parameter별 최종 cap 재검증

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

- PowerMix 최종 합계 1. 단, 인터뷰 결과 최종 정책에서는 Energy Source별 독립 override를 허용하므로 합계 검증을 요구하지 않는다.
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
          - schema·duplicate·value 검증
          - parameter별 exact lookup
          - compact slot hierarchy
                    │
    Basecase loader ─┤
                    ▼
          EffectiveReferenceResolver
                    │
    Scenario context ──┐
                       ├─► Full Compact SlotCatalog Packet
    Valid SlotCatalog ─┘   - 의미 prefilter 없음
                           - 객관적 유효성 filter만 적용
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
          - 명시 cell의 coordinate·schema 검증
          - 누락 생성·aggregate 후처리 없음
                    │
                    ▼
              API/DB + provenance

## 10. 데이터 모델 초안

### 10.1 ParameterLutSpec

DB table이나 복잡한 범용 DSL을 만들지 않고 다음 단일 YAML 파일로 시작한다.

    apps/agents/model_parameter_agent/resources/lut/config/lut_parameters.yaml

YAML 필드는 최소화한다.

- 최상위 parameter 이름: canonical parameter 이름
- adapter: allowlist에 등록된 공통 또는 계산 adapter 이름
- layout: 공통 tabular adapter의 CSV 배치 형태인 row 또는 year_columns
- files: 해당 parameter가 읽는 LUT 파일 역할 목록
- path: `resources/lut/` 기준 상대 경로
- required_columns: 계산 adapter가 읽어야 하는 실제 CSV header 목록
- axis_columns: 공통 adapter에서 canonical DB/API axis와 실제 CSV header를 직접 연결
- value_column: tabular row layout이 값으로 읽는 실제 CSV header
- year_value_column: tabular year_columns layout이 horizon 연도별 값으로 읽는 CSV header template
- key_axes: exact lookup과 Step2 선택에 사용하는 canonical axis 이름
- metadata_axes: key에서 제외하고 exact reference에서 복원할 canonical metadata 이름

예시:

    GDP:
      adapter: gdp_growth
      files:
        values:
          path: Demand_Model_LUT_BCInput_value_based_t2.csv
          required_columns:
            - RE Base Case GDP and Population Data_Country
            - RE Base Case GDP and Population Data_Year
            - RE Base Case GDP and Population Data_GDP
      key_axes: [Country, Year]

    PMI:
      adapter: tabular
      layout: year_columns
      files:
        values:
          path: Demand_Model_Input_PMIInput_value_based_t2.csv
          axis_columns:
            Country: Base Case PMI Input (do not change)_Country
            Month: Base Case PMI Input (do not change)_Month
          year_value_column: Base Case PMI Input (do not change)_{year}.0
      key_axes: [Country, Year, Month]

    PowerMix:
      adapter: tabular
      layout: row
      files:
        values:
          path: Demand_Model_LUT_BCInput_value_based_t3.csv
          axis_columns:
            Country: Power Generation Data_Country
            Year: Power Generation Data_Year
            Energy Source: Power Generation Data_Energy Source Use
          value_column: Power Generation Data_Power Mix
      key_axes: [Country, Year, Energy Source]

    LiqUtilAdjustment:
      adapter: liq_util
      files:
        values:
          path: BCLiquefaction.csv
          required_columns:
            - Country
            - Plant Name
            - Plant Train
            - Year
            - Month
            - Period
            - Infra Life Cycle
            - LNG train capacity (Million tonnes LNG per month)
            - LNG plant utilisation %
      key_axes: [Country, LNG Plant, LNG Plant Train, Year, Month]
      metadata_axes:
        - Period
        - Life Cycle Category
        - Nameplate Capacity

`{year}`는 설정 horizon의 각 연도로 확장해 실제 header 존재를 검증한다. 현재는 2026~2030의 5개 연도 column이다.

`axis_columns`의 왼쪽은 canonical DB/API axis 이름이고 오른쪽은 실제 CSV header다. 내부 역할명 alias는 YAML에 두지 않는다. `axis_columns`, `value_column`, `year_value_column`에 지정된 header는 자동으로 필수 column이 된다.

adapter 구성:

| Parameter | Adapter | 구분 | 처리 |
|---|---|---|---|
| GDP | gdp_growth | 전용 계산 | 절대 GDP에서 exact 전년 대비 성장률 계산 |
| PMI | tabular / year_columns | 공통 | 한 행의 연도별 column을 Country/Year/Month record로 전개 |
| PowerMix | tabular / row | 공통 | axis column과 value column을 행 단위로 그대로 읽음 |
| Temperature | temperature_degree_days | 전용 계산 | HDD/CDD 결합 및 temperature 계산 |
| LiqUtilAdjustment | liq_util | 전용 계산 | Closed 제외, capacity 변환, metadata 복원용 값 생성 |

신규 parameter가 한 CSV의 지정 axis/value column을 그대로 읽는 형태이면 공통 `tabular` adapter를 사용한다. 한 행이 record 하나이면 `layout: row`, 연도별 값이 column으로 펼쳐져 있으면 `layout: year_columns`를 지정한다. 새로운 계산, 여러 파일 결합, 별도 filter·metadata 변환이 필요한 경우에만 Python adapter를 추가하고 allowlist registry에 등록한다.

YAML에는 계산식, 임의 Python import, 타입 DSL, validator DSL, horizon 값, slot/reference 상한을 넣지 않는다. adapter 값은 임의 import path가 아니라 코드에 등록된 이름만 허용한다. horizon 2026~2030과 GDP 2025 lookback은 기존 app settings와 adapter가 적용한다.

### 10.2 EffectiveReference

필드 초안:

- candidate_key
- parameter_name
- canonical_slot_key
- axes
- metadata
- effective_value
- effective_source
- actual_basecase_value
- lut_default_value
- llm_reference_value
- basecase_reference_id
- lut_reference_id
- lut_version
- diagnostics

### 10.3 business key 초안

| Parameter | Business key | Metadata 또는 파생값 |
|---|---|---|
| GDP | Country + Year | 절대 GDP, 이전 연도 GDP, transform 정보 |
| PMI | Country + Year + Month | t2 wide year column에서 직접 읽은 값 |
| PowerMix | Country + Year + Energy Source | Energy Source별 독립 override 값 |
| Temperature | Country + Year + Month | HDD, CDD, transform branch |
| LiqUtilAdjustment | Country + LNG Plant + LNG Plant Train + Year + Month | Period, Life Cycle Category, Nameplate Capacity |

## 11. 현재 선별 이식 후보

### Claude에서 가져올 요소

- 정확한 year-1 GDP 계산
- horizon 설정 개념
- LUT feature flag
- DB 축 이름과 LUT 축 이름 정렬 개념
- reference record 기준 metadata 보정

### Codex에서 가져올 요소

- parameter별 명시 business key
- effective_source와 양쪽 value/reference provenance
- Step2용 compact reference와 Step3용 exact reference 분리 개념
- Step3 LLM에 effective 기준값 하나만 전달하는 방향
- LiqUtil hidden metadata 복원 개념
- duplicate warning과 robust scalar parsing
- 호출별 structured streaming 옵션
- partial response와 reference 누락에 대한 테스트 사례

### 그대로 가져오지 않을 요소

- Claude의 global 40,000 raw record cap
- Claude의 full effective state
- Claude의 모든 structured output 전역 streaming
- Claude의 Full Country List 기반 GDP/PowerMix 국가 필터
- Claude의 모든 parameter 대상 metadata 제외
- Claude의 Step3 prompt에 basecase와 LUT 두 값을 동시에 노출하는 방식
- Codex의 full LiqUtil state와 request당 재구성
- Codex의 nearest Year/Month slot 변경
- Codex의 누락 응답 자동 no-change 성공 처리
- 두 브랜치의 LUT-only effective 값을 운영 basecaseValue로 저장하는 방식
- 두 구현의 global/순서 의존 slot cap

## 12. 개선 백로그 초안

### P0 — 머지 전 필수

1. 최소 LUT YAML spec과 canonical business key 확정
2. immutable LutCatalog와 exact lookup index 구현
3. full LUT state와 global raw cap 제거
4. Step2 strict membership validation
5. 전체 compact catalog 제공과 LLM relevance 선택 prompt 계약 적용
6. source-aware EffectiveReference 모델
7. API provenance 계약 확정
8. LUT off 모드가 main과 동일한지 snapshot 검증

### P1 — 운영 전 필수

1. startup/readiness LUT schema 검증
2. off/shadow/on rollout
3. per-call streaming과 중단/retry 테스트
4. parameter task별 공통 100 cap 검증
5. Step3 valid/missing/invalid cell 진단 metric
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
10. PowerMix 일부 Energy Source만 반환할 때 명시 cell만 유지되고 합계 정규화가 발생하지 않는지 검증
11. API provenance와 기존 소비자 호환성
12. prompt token, state 직렬화 크기, cold/warm latency
13. 동시 요청 메모리와 cache race
14. 최종 코드·배포 설정으로 28개 scenario 전체 재실행

## 14. 인터뷰 의사결정 로그

| ID | 결정 항목 | 상태 | 확정 내용 |
|---|---|---|---|
| D-01 | LUT-only slot 허용 범위 | DECIDED | 5개 parameter 모두 LUT-only slot 허용. basecase 부재는 제외 사유가 아니며, scenario/event 관련성이 있으면 선택 가능 |
| D-02 | slot universe와 horizon 정책 | DECIDED | config horizon 2026~2030 적용, GDP는 2026 계산을 위해 2025 source 값만 내부 참조. 국가 범위는 각 parameter LUT 자체를 사용하며 Full Country List 보조 파일은 사용하지 않음 |
| D-03 | effective 기준값 우선순위와 API provenance | DECIDED | 내부에서 basecase/LUT 모두 관리. LLM에는 basecase 우선·없으면 LUT인 단일 값만 전달. 운영 basecaseValue는 실제 basecase만 저장하며 LUT-only는 null. sync API는 양쪽 반환 가능 |
| D-04 | exact reference 부재와 nearest 처리 | DECIDED | basecase와 LUT 양쪽에 exact business-key 조합이 없으면 최종 proposal에서 제외. nearest 좌표 자동 치환 금지 |
| D-05 | scenario prefilter, ranking, slot cap | DECIDED | 전체 compact catalog 제공, 관련성 선택은 LLM 담당. 명시적 no-change 저장, 누락 자동 보완 금지. 기존 전역 설정 2개를 100/100으로 유지하고 각 parameter의 Step2/Step3 task와 prompt에 동일 적용 |
| D-06 | Step3 LLM 역할과 partial fallback | DECIDED | LLM이 명시적으로 반환하고 서버 검증을 통과한 cell만 사용. 누락 cell 자동 생성 금지, 일부 누락을 이유로 candidate 전체 폐기 금지 |
| D-07 | PowerMix 등 parameter별 invariant 처리 | DECIDED | PowerMix는 Energy Source별 독립 override로 처리. LLM이 명시한 값만 사용하고 전체 vector 강제, 합계 1 검증·정규화, 미선택 source 보완을 하지 않음 |
| D-08 | LUT spec, adapter, metadata 축 관리 | DECIDED | 최소 YAML spec과 단일 `tabular` 공통 adapter의 row/year_columns layout 사용. GDP·Temperature·LiqUtil만 전용 adapter 유지. LiqUtil metadata만 exact reference에서 복원. GDP General 파일과 PMI t1 파일은 미사용 |
| D-09 | feature rollout과 streaming 설정 | PENDING | 미정 |
| D-10 | 실제 구현 기반 브랜치와 머지 순서 | PENDING | 미정 |

### 14.1 D-01 확정 — LUT-only slot 허용 범위

확정 내용:

- GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment 모두 LUT-only slot을 실제 proposal 대상으로 허용한다.
- basecase에 좌표가 없다는 이유만으로 slot을 제외하지 않는다.
- scenario/event 정보와 의미적으로 관련된 LUT slot이면 Step2에서 선택될 수 있어야 한다.
- LiqUtilAdjustment도 basecase 기존 Train으로 제한하지 않고 LUT에 있는 유효 Train을 선택할 수 있다.
- 같은 좌표에 basecase와 LUT가 모두 있으면 LLM 기준값은 basecase를 사용하고, 운영 DB/API에도 실제 basecase만 basecaseValue로 저장한다.

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

### 14.3 D-02 확정 — slot universe와 horizon 정책

확정 내용:

- Claude 구현처럼 LUT proposal 기간을 config로 관리한다.
- 현재 최종 proposal에 노출할 연도 범위는 2026~2030이다.
- GDP의 2026년 성장률 계산을 위해 2025년 absolute GDP를 내부 source 값으로 참조할 수 있다.
- GDP 2025년 값은 계산용 lookback일 뿐 2025년 proposal slot으로 노출하지 않는다.
- config horizon 밖 좌표는 raw LUT/basecase에 존재하더라도 Step2/Step3 최종 후보에서 제외한다.
- 향후 모델 적용 기간이 바뀌면 코드 수정이 아니라 config 변경으로 대응한다.

Codex 현재 기준과 차이:

- Codex에는 LUT horizon 전용 설정이 없다.
- GDP 2019~2031, PowerMix 2022~2031, LiqUtil 2017~2050 등 파일에 존재하는 기간이 그대로 후보에 포함된다.
- prompt에서 현재 이후 기간을 선택하라고 지시하지만 서버가 config 범위로 강제하지 않는다.
- 따라서 최종안에서는 Codex loader의 무제한 기간 노출을 채택하지 않는다.

Claude 현재 기준과 보완점:

- 이미 Settings에 model_parameter_lut_horizon_start_year와 model_parameter_lut_horizon_end_year가 존재한다.
- 현재 Claude 기본값은 2024와 2031이다.
- LUT loader는 해당 range를 적용하지만 basecase record에는 같은 범위 제한을 일관되게 적용하지 않는다.
- envs/config.yaml과 devops/k8s/configmap.yaml에도 두 값을 명시하지 않았다.
- start_year가 end_year보다 큰 설정을 차단하는 validator가 없다.

최종 구현 기준:

1. model_parameter_lut_horizon_start_year=2026
2. model_parameter_lut_horizon_end_year=2030
3. local/dev/K8s 설정에 동일 값을 명시
4. start_year <= end_year 설정 검증 추가
5. Step2에 노출되는 basecase와 LUT union 모두 동일한 2026~2030 proposal horizon 적용
6. parameter adapter가 계산용 source window와 proposal window를 분리할 수 있게 구성
7. GDP source window는 2025~2030, proposal window는 2026~2030
8. LUT cache key 또는 preload version에 horizon 포함

필수 테스트:

- 2026과 2030 slot은 포함되고 2025와 2031 slot은 제외되는지 확인
- GDP 2026 growth가 2025 absolute GDP를 사용해 계산되는지 확인
- GDP 2025 record가 Step2 slot option에는 나타나지 않는지 확인
- horizon 밖 basecase record도 proposal 후보에서는 제외되는지 확인
- start_year > end_year 설정이 애플리케이션 시작 시 실패하는지 확인

### 14.4 D-03 확정 — LLM 기준값과 운영 API/DB 투영

확정 내용:

- 내부 reference 모델에서는 actual basecase와 LUT default를 모두 보존한다.
- LLM Step3에는 한 좌표당 숫자 기준값을 하나만 전달한다.
- actual basecase가 있으면 그 값을 LLM의 basecase 기준값으로 전달한다.
- actual basecase가 없고 LUT가 있으면 LUT 값을 LLM의 basecase 기준값으로 전달한다.
- LLM에는 actual basecase와 LUT default를 동시에 노출하지 않는다.
- 운영 proposal DB와 frontend API의 구조와 basecaseValue 의미는 변경하지 않는다.
- actual basecase가 있으면 basecaseValue에 실제 basecase 값을 저장한다.
- LUT-only slot이면 basecaseValue는 null로 저장한다.
- 내부 테스트용 sync API는 검증을 위해 actual basecase와 LUT default를 모두 반환할 수 있다.

Codex 현재 기준과 차이:

- Codex는 내부 effective record에 basecase_value, lut_value, 양쪽 reference와 effective_source를 보존한다.
- Step3 prompt에는 effective record의 value 하나를 basecase_value로 전달하므로 LLM 입력 방향은 확정안에 가깝다.
- 하지만 sanitizer가 effective LUT 값을 ParameterValueCell.basecase_value에 채우고 presentation이 이를 basecaseValue로 저장하므로 LUT-only의 운영 DB/API 의미는 확정안과 다르다.
- 최종안에서는 prompt용 llm_reference_value와 저장용 actual_basecase_value를 분리해야 한다.

Claude 현재 기준과 차이:

- Claude도 내부에서 basecase 우선 effective 값과 lut_value를 보존한다.
- Step3 prompt에서 basecase override가 있는 좌표에 lut_default_value도 함께 전달하므로 확정안보다 값 정보가 많다.
- LUT-only 좌표는 value_source=lut_default와 함께 LUT 값을 basecase 기준값으로 전달한다.
- 최종 presentation에서는 LUT-only effective 값이 basecaseValue로 저장되므로 운영 계약을 위반한다.
- 최종안에서는 Claude의 dual-value prompt와 effective-to-basecaseValue 투영을 사용하지 않는다.

내부 필드 의미:

- actual_basecase_value: workbook에서 실제로 읽은 값. 없으면 null
- lut_default_value: LUT에서 읽은 default. 없으면 null
- llm_reference_value: actual_basecase_value가 있으면 그 값, 없으면 lut_default_value
- effective_source: basecase 또는 lut

LLM prompt cell 초안:

    {
      "reference_id": "internal-reference-id",
      "axes": { ... },
      "basecase_value": 0.42
    }

위 basecase_value는 LLM 판단을 위한 단일 기준값이다. 운영 DB의 basecaseValue와 같은 저장 필드로 직접 재사용하지 않는다.

운영 DB/frontend projection:

    {
      "basecaseValue": null,
      "proposedValue": 0.45,
      "rationale": "..."
    }

위 예시는 LUT-only slot이다. LLM은 내부적으로 LUT 0.42를 기준으로 사용했지만 실제 basecase가 없으므로 basecaseValue는 null이다.

내부 테스트용 sync API는 필요 시 다음 정보를 별도로 반환할 수 있다.

    {
      "basecaseValue": null,
      "lutValue": 0.42,
      "llmReferenceValue": 0.42,
      "referenceSource": "lut"
    }

필수 테스트:

- basecase와 LUT가 모두 있으면 LLM prompt에 basecase 숫자 하나만 전달되는지 확인
- LUT-only이면 LLM prompt에는 LUT 숫자가 전달되지만 운영 DB basecaseValue는 null인지 확인
- basecase-only이면 LLM prompt와 운영 DB basecaseValue가 모두 실제 basecase인지 확인
- 운영 proposal API snapshot이 기존 구조와 동일한지 확인
- sync API에서만 basecase/LUT 양쪽 검증값을 반환하는지 확인

### 14.5 D-05 확정 — 전체 compact catalog와 LLM 관련성 판단

확정된 내용:

- 서버가 scenario/event 의미를 기준으로 Country, Plant, Train 등 후보를 미리 제거하지 않는다.
- horizon 2026~2030, Closed lifecycle 제외, schema 정합성, exact path처럼 객관적으로 유효하지 않은 좌표만 catalog 구성 단계에서 제외한다.
- 남은 전체 유효 slot universe를 compact 형태로 Step2 LLM에 제공한다.
- scenario/event와 관련성이 높은 slot을 고르는 책임은 LLM에 둔다.
- raw LUT row를 그대로 보내지 않고 axis 값, hierarchy, leaf별 유효 기간을 보존하는 compact 구조를 사용한다.
- Claude의 40,000건 raw record cap처럼 catalog 일부를 먼저 삭제하지 않는다.
- LLM이 proposedValue를 기준값과 동일하게 명시해도 정상적인 no-change 의사결정으로 보고 운영 proposal에 저장한다.
- LLM이 반환하지 않은 selected slot을 서버가 현재 기준값 유지 cell로 자동 생성하지 않는다.

Codex 현재 기준과 차이:

- Codex는 non-Liq parameter에 대해 전체 union을 compact해 전달하므로 확정 방향에 가깝다.
- LiqUtil은 hierarchy를 compact하지만 전체 41,079 reference record를 state에 함께 저장한다.
- prompt가 관련 slot을 엄격히 좁히기보다 가능한 slot을 최대한 포함하도록 반복 지시한다.
- 실제 broad scenario에서 94~100 slot과 다수 no-change proposal이 생성됐다.
- 최종안에서는 Codex의 전체 compact 제공 개념은 사용하되 full Liq state와 최대 선택 지침은 제거한다.

Claude 현재 기준과 차이:

- Claude도 semantic prefilter 없이 전체 effective union에서 compact option을 만든다.
- 그러나 compact option 생성 전에 raw effective record를 40,000건으로 잘라 일부 유효 leaf와 기간이 사라진다.
- 코드 기본 slot cap은 20이지만 실제 local/K8s 설정은 100이라 테스트 동작과 문서가 일치하지 않는다.
- 최종안에서는 Claude의 raw cap과 설정 불일치를 제거하고 전체 유효 compact catalog를 보장한다.

Step2 compact packet 원칙:

1. value row는 포함하지 않는다.
2. parameter별 canonical axis 이름을 제공한다.
3. 비시간축은 실제 leaf path 관계를 유지하는 hierarchy로 제공한다.
4. 시간축은 가능하면 leaf별 available period를 함께 표현한다.
5. basecase-only와 LUT-only가 모두 후보임을 설명하되 Step3 숫자 값은 노출하지 않는다.
6. prompt는 관련성이 높은 slot만 선택하고 단순 전수 열거하지 않도록 명시한다.
7. Step2 결과는 D-04의 exact membership 검증을 통과해야 한다.

#### 현재 코드의 100개 제한 의미

model_parameter_max_parameter_slots=100은 Step2 prompt에 주입되는 후보 option 개수 제한이 아니다.

현재 처리 순서:

1. 서버가 전체 compact slot catalog를 Step2 prompt payload에 넣는다.
2. 같은 payload의 slot_selection_limits.maxParameterSlots에 100을 넣어 LLM에 최대 출력 수를 지시한다.
3. LLM이 parameter_slots를 반환한다.
4. 서버 _sanitize_llm_slots가 selected=true slot을 전체 candidate 합계 100개까지만 유지한다.

따라서 전체 compact catalog에 수백 개 leaf가 있어도 모두 prompt에 들어갈 수 있고, 100은 그중 LLM이 최종 선택해 반환할 수 있는 완성 slot 좌표 수다.

관련 설정은 서로 의미가 다르다.

| 설정 또는 제한 | 적용 단계 | 현재 의미 |
|---|---|---|
| model_parameter_max_parameter_slots | Step2 output | LLM이 선택해 반환할 selected slot 최대 수. prompt 지시와 서버 sanitizer 양쪽에서 사용 |
| model_parameter_max_value_prompt_basecase_records | Step3 input | 선택된 slot의 값을 판단할 때 LLM에 제공할 reference record 최대 수. 현재 100 |
| model_parameter_max_effective_reference_records | Step2 이전 state | Claude가 effective raw record를 자르는 최대 수. 현재 40,000이며 최종안에서는 제거 대상 |
| compact catalog option 수 | Step2 input | 현재 100과 무관. 최종안은 객관적으로 유효한 전체 compact catalog 제공 |

Codex는 model_parameter_max_parameter_slots 기본값과 실제 설정이 모두 100이다. Claude는 Settings 기본값이 20이지만 envs/config.yaml과 K8s ConfigMap이 100으로 덮어쓰므로 실제 테스트에서는 100이 사용됐다.

#### 최종안의 공통 제한 구조

parameter별 설정 map을 추가하지 않는다. 기존 전역 정수 설정 2개를 그대로 사용한다.

    model_parameter_max_parameter_slots: 100
    model_parameter_max_value_prompt_basecase_records: 100

설정값은 공통이지만 적용과 검증 단위는 parameter task이다. 예를 들어 GDP와 PowerMix가 함께 선택되면 각 Step2 task에 동일한 maxParameterSlots 100을 전달하고 각 parameter가 최대 100개까지 선택할 수 있다. 한 parameter가 선택한 slot 수가 다른 parameter의 한도를 차감하지 않는다.

Step2 prompt 적용:

- model_parameter_max_parameter_slots 전역값을 각 parameter_slot_tasks 항목의 limits.maxParameterSlots에 동일하게 넣는다.
- system prompt에는 maxParameterSlots가 목표 개수나 최소 개수가 아니라 hard maximum임을 명시한다.
- LLM은 scenario/event/dimension과 관련된 slot만 선택하며 상한까지 억지로 채우지 않는다.
- 서버 sanitizer도 전체 요청 합계가 아니라 candidate/canonical parameter별 count를 동일한 전역 상한으로 검증한다.
- 여러 parameter가 동시에 선택돼도 먼저 반환된 parameter가 다른 parameter의 예산을 차지하지 않는다.

Step2 task 예시:

    {
      "parameter": {"parameter_name": "PowerMix"},
      "limits": {
        "maxParameterSlots": 100,
        "instruction": "관련된 slot만 선택하며 최대치를 채울 필요는 없음"
      },
      "basecase_slot_options": [ ... ]
    }

GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment 및 LUT 미지원 parameter에는 모두 Step2 selected slot 100개, Step3 value reference 100개를 동일하게 적용한다. Step2의 100은 목표 개수가 아니며, 각 task의 scenario/event/dimension 관련 slot이 더 적으면 관련된 slot만 반환해야 한다.

Step3 적용:

- model_parameter_max_value_prompt_basecase_records 전역값을 각 parameter_value_tasks 항목의 limits.maxReferenceRecords에 동일하게 넣는다.
- 해당 parameter의 selected slot과 exact reference를 우선 제공한다.
- supplemental context가 필요한 parameter는 남은 예산 안에서 추가한다.
- selected slot의 필수 exact reference가 상한 때문에 조용히 누락되면 안 된다. 필요한 reference가 상한보다 많으면 명시적 validation error 또는 재선택 대상으로 처리한다.

#### D-05 no-change 처리 상세

Codex 현재 기준과 차이:

- LLM이 명시한 no-change cell을 저장한다.
- LLM이 일부 cell 또는 candidate를 누락해도 서버가 effective 기준값을 proposedValue로 넣은 fallback cell을 생성할 수 있다.
- 확정안에서는 명시적 no-change 저장은 유지하지만 Codex의 누락 fallback 생성은 사용하지 않는다.

Claude 현재 기준과 관계:

- LLM이 기준값과 같은 proposedValue를 명시적으로 반환하면 저장한다.
- 누락 cell을 기준값 유지 cell로 자동 생성하지 않는다.
- 다만 현재 Claude 구현은 selected slot 하나라도 누락되면 해당 candidate의 전체 value_grid를 비우므로, 유효한 partial cell을 유지할지는 D-06에서 별도 결정한다.

확정 처리 예시:

- LLM 입력 기준값 0.42, 명시 응답 proposedValue 0.42: 운영 proposal에 저장
- LLM 입력 기준값 0.42, 해당 좌표 응답 자체가 없음: 서버가 0.42 cell을 생성하지 않음
- 내부 sync/test 결과에서는 selected slot 대비 LLM 응답 누락 수를 별도 진단값으로 반환 가능

### 14.6 D-06 확정 — Step3 partial 응답 처리

Codex 현재 기준과 차이:

- Codex는 Step3가 누락한 cell 또는 candidate를 effective 기준값의 no-change proposal로 자동 생성할 수 있다.
- 최종안은 이 fallback을 사용하지 않는다. LLM이 값을 주지 않은 좌표에는 운영 proposal cell을 만들지 않는다.

Claude 현재 기준과 차이:

- Claude는 selected slot 중 하나라도 누락되면 같은 candidate의 value_grid 전체를 비워 명시적으로 반환된 유효값까지 잃을 수 있다.
- 최종안은 candidate 전체를 일괄 폐기하지 않고 각 cell을 독립적으로 검증한다.

확정 처리:

1. Step3 응답에 명시된 cell만 canonical coordinate와 value schema를 검증한다.
2. 검증을 통과한 cell은 LLM이 준 proposedValue 그대로 사용한다.
3. 응답에 없는 selected slot은 생성하거나 기준값으로 채우지 않는다.
4. 일부 slot이 누락돼도 같은 candidate에서 검증을 통과한 다른 cell은 유지한다.
5. 명시적으로 반환된 proposedValue가 기준값과 같아도 유효한 no-change proposal로 유지한다.
6. selected slot 수, valid response cell 수, missing/invalid cell 수는 내부 sync/test 응답과 metric에서 진단할 수 있다.

이 결정은 PowerMix를 포함한 모든 parameter의 기본 cell 단위 정책이다.

### 14.7 D-07 확정 — PowerMix 독립 override 처리

Codex 현재 기준:

- 선택된 Energy Source cell만 Step3에서 변경하며 Country/Year 전체 합계를 검증하거나 정규화하지 않는다.

Claude 현재 기준:

- 구현상 전체 vector 합계 검증과 자동 정규화가 없으며 선택된 Energy Source cell을 개별 proposal로 처리한다.

확정 처리:

1. PowerMix의 각 `Country + Year + Energy Source` cell을 독립적인 override로 취급한다.
2. Step3에는 시나리오와 관련되어 선택된 Energy Source만 변경 대상으로 전달할 수 있다.
3. LLM이 명시적으로 반환하고 검증을 통과한 Energy Source 값만 저장한다.
4. 같은 Country/Year의 미선택 또는 누락 Energy Source를 서버가 채우거나 변경하지 않는다.
5. 서버가 전체 합을 1로 맞추는 정규화, 재배분 또는 group 단위 폐기를 수행하지 않는다.
6. 서버 검증은 exact coordinate 존재와 cell value schema 같은 객관적 유효성에 한정한다.

### 14.8 D-08 확정 — 최소 LUT YAML spec과 metadata 복원

Codex 현재 기준:

- LUT 파일명, 필수 column, parameter별 business key가 Python `utils/lut.py`에 하드코딩돼 있다.
- LiqUtilAdjustment에 한정해 Period, Life Cycle Category, Nameplate Capacity를 key에서 제외하고 복원한다.
- GDP 국가 범위는 GDP LUT 자체이며 Full Country List를 사용하지 않는다.
- PMI t1의 demand→reference country mapping을 거쳐 t2 값을 조회한다.

Claude 현재 기준:

- LUT 파일명과 column이 Python `utils/lut_repository.py`에 하드코딩돼 있다.
- Period, Life Cycle Category, Nameplate Capacity 이름을 모든 parameter에서 전역 제외한다.
- Full Country List를 GDP와 PowerMix 국가 필터로 사용한다.
- PMI t2에 demand country 값이 있으면 직접 사용하고, 없는 7개 `Other ...` 국가만 t1 reference country로 fallback한다.

확정 처리:

1. DB table은 만들지 않고 `apps/agents/model_parameter_agent/resources/lut/config/lut_parameters.yaml`을 사용한다.
2. YAML에는 parameter별 adapter 이름, LUT file path, 필수 CSV header 또는 tabular column mapping, key_axes, metadata_axes만 둔다.
3. 계산식, filter 알고리즘, 타입 변환, horizon과 prompt 제한값은 YAML에 넣지 않고 Python adapter와 app settings에 유지한다.
4. YAML에 선언한 실제 CSV header가 없으면 LUT enabled 상태의 적재를 명시적으로 실패시킨다.
5. GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment의 key_axes는 10.3 business key를 따른다.
6. 현재 metadata_axes는 LiqUtilAdjustment의 Period, Life Cycle Category, Nameplate Capacity에만 적용한다.
7. LiqUtil metadata는 LLM이 선택하거나 생성하지 않고 basecase가 있으면 exact basecase record, LUT-only이면 exact LUT record에서 복원한다.
8. 다른 parameter에는 column 이름만 보고 metadata를 전역 제외하지 않는다.
9. 국가 범위는 각 parameter의 자체 LUT distinct를 사용한다. `Demand_Model_LUT_General_value_based_t6.csv`는 읽지 않는다.
10. GDP는 2026~2030 각 연도의 exact 전년도 값이 있는 LUT 국가만 노출하며, 현재 데이터 기준 163개국이다.
11. PMI는 `Demand_Model_Input_PMIInput_value_based_t2.csv`만 사용하고 t1 reference-country mapping과 fallback을 사용하지 않는다.
12. PMI LUT 국가 범위는 t2의 84개국이며, t1에만 있는 7개 `Other ...` 집계 국가는 LUT-only 후보로 만들지 않는다. 기존 basecase에 해당 좌표가 있다면 basecase-only 정책으로는 유지된다.
13. 계산 없이 한 CSV의 지정 axis/value column을 읽는 parameter는 단일 `tabular` 공통 adapter를 사용한다.
14. PowerMix는 `layout: row`, PMI는 `layout: year_columns`를 사용한다.
15. 신규 tabular parameter는 YAML 추가만으로 지원하고, 새로운 계산이나 여러 파일 결합·filter·metadata 변환이 필요한 경우에만 전용 Python adapter와 registry 등록을 추가한다.

공통 adapter의 `axis_columns` 왼쪽은 canonical DB/API axis, 오른쪽은 실제 CSV header다. custom adapter의 required_columns는 실제 CSV header 문자열 목록이다. 개별 row의 null 허용 여부와 row 제외 규칙은 adapter가 담당한다.

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

D-09: LUT 기능의 off/shadow/on rollout과 structured-output streaming 적용 범위를 결정한다.

## 17. 변경 이력

| 일시 | 변경 내용 |
|---|---|
| 2026-07-10 | 두 브랜치 전체 비교, 독립 측정, 테스트 결과, 구조 초안과 인터뷰 로그 최초 작성 |
| 2026-07-10 | D-01 확정: 5개 parameter 모두 scenario/event 관련 LUT-only slot 선택 허용, 서버 검증 의미 명시 |
| 2026-07-10 | 인터뷰 형식에 Codex/Claude 현재 기준을 추가하고 D-01 조합 오류 발생 조건과 예시 보강 |
| 2026-07-10 | D-04 조기 확정: basecase/LUT 양쪽에 exact 조합이 없으면 최종 제외, nearest 좌표 치환 금지 |
| 2026-07-10 | D-02 확정: config 기반 2026~2030 proposal horizon, GDP 2025 계산용 lookback 허용 |
| 2026-07-10 | D-03 확정: LLM 단일 기준값, 운영 basecaseValue 기존 의미 유지, LUT-only null, sync API 양쪽 값 허용 |
| 2026-07-10 | D-05 일부 확정: 객관적 유효성 filter 후 전체 compact catalog를 제공하고 관련성 선택은 LLM에 위임 |
| 2026-07-10 | D-05 no-change 정책 확정: LLM이 명시한 동일값은 저장하고 누락 cell은 서버가 자동 보완하지 않음 |
| 2026-07-10 | D-05 제한 의미 보강: Step2 input catalog 크기와 selected slot 100개, Step3 reference 100개를 구분 |
| 2026-07-10 | D-05 제한 구조 초안: Step2 slot과 Step3 reference 상한을 parameter별 config와 task별 prompt 제한으로 검토 |
| 2026-07-10 | D-05 제한값 검토: GDP부터 100/100 적용 결정 |
| 2026-07-10 | D-05 완료: parameter별 map 없이 기존 전역 설정 2개를 100/100으로 유지하고 각 parameter task/prompt에 동일 적용 |
| 2026-07-10 | D-06 완료: LLM이 명시적으로 반환하고 검증을 통과한 cell만 유지하며 누락 자동 보완과 candidate 전체 폐기를 모두 금지 |
| 2026-07-10 | D-07 완료: PowerMix를 Energy Source별 독립 override로 처리하고 전체 vector 강제·합계 검증·정규화 후처리를 하지 않음 |
| 2026-07-10 | D-08 완료: resources/lut/config의 최소 YAML spec으로 파일·필수 컬럼·key/metadata 축만 관리하고 LiqUtil metadata만 exact reference에서 복원 |
| 2026-07-10 | D-02 국가 범위 보강: Full Country List 보조 파일을 제거하고 각 parameter LUT 자체의 국가 distinct를 사용 |
| 2026-07-10 | D-08 PMI source 보강: t2 파일만 사용하고 t1 reference-country mapping 및 7개 Other 국가 fallback 제거 |
| 2026-07-10 | D-08 adapter 정책 보강: PMI와 PowerMix는 단일 tabular 공통 adapter의 year_columns/row layout을 사용하고 GDP·Temperature·LiqUtil만 전용 adapter로 구현 |

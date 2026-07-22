# Model Parameter Agent 핵심 이해도 퀴즈

## 1. 퀴즈 목적과 범위

이 퀴즈는 다음 가이드 전체의 핵심 내용을 이해했는지 확인하기 위한 10문항이다.

- [개요](01_MODEL_PARAMETER_AGENT_OVERVIEW.md)
- [API 사용법](02_MODEL_PARAMETER_AGENT_API_SPEC.md)
- [DB 안내](03_MODEL_PARAMETER_AGENT_DB_SPEC.md)
- [전체 기능 Flow와 prompt](04_MODEL_PARAMETER_AGENT_FLOW.md)
- [Basecase·LUT 파싱](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)
- [파라미터 추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)

1~5번은 객관식, 6~10번은 주관식이다. 먼저 정답을 보지 않고 풀어 본다. 문항당 1점이며, 복수 선택은 정답을 모두 골라야 1점이다.

---

## 2. 객관식 5문항

### 문제 1. Agent의 목적

다음 중 Model Parameter Agent가 **mapping 정보, parameter 정보, Basecase와 LUT를 활용하는 목적**을 가장 정확히 설명한 것은?

1. Mapping 정보로 시나리오의 event·dimension에 허용된 파라미터 후보와 연결 판단 기준을 찾고, parameter 정보로 값의 의미·단위·모델 위치와 읽기 기준을 이해한다. Basecase/LUT에 실제로 존재하는 exact slot에서 Basecase 우선·LUT 대체 기준값을 정한 뒤, 시나리오 영향을 반영한 모델 입력값과 근거를 제안해 사용자가 검토·확정할 수 있게 한다.
2. Mapping 정보와 parameter 정보로 후보·모델 위치를 찾되 Basecase가 있는 slot만 제안 대상으로 인정한다. LUT는 Basecase 값과 차이를 비교하는 참고자료로만 사용하고, Basecase가 없는 slot에는 값을 제안하지 않는다.
3. Mapping 정보는 추천 목록으로만 사용하므로 시나리오 설명에 더 적합한 활성 파라미터가 있으면 LLM이 후보를 추가한다. Parameter 정보로 단위를 맞추고 Basecase/LUT exact slot의 기준값을 사용해 최종 모델 입력값을 제안한다.
4. Mapping 정보로 후보를 정하고 parameter 정보와 Basecase/LUT로 적용 slot과 기준값을 찾는다. 다만 Agent는 모든 파라미터에 공통된 증감률이나 증감량만 제안하고, 실제 모델 입력값 변환과 근거 작성은 후속 시스템이 담당한다.

### 문제 2. API와 처리 상태

다음 설명 중 맞는 것을 **모두** 고르시오.

1. 동기 제안 API는 성공하면 처리가 끝난 `PROPOSED` 결과를 응답한다.
2. 비동기 제안 API의 최초 `PROCESSING` 응답은 제안 생성이 끝났다는 뜻이다.
3. 비동기 callback은 전체 제안값이 아니라 proposal ID와 완료 상태를 알린다.
4. 확정 API는 LLM을 다시 호출해 값을 재산정한다.
5. 확정은 기존 proposal 행을 `CONFIRMED`로 갱신하며, 유효한 전체 payload로 다시 확정할 수도 있다.

### 문제 3. DB 테이블의 역할

다음 중 DB 테이블과 역할의 연결이 **틀린 것**은?

1. `tmm_mi_model_param_m` — 파라미터명, 모델 대상, Basecase 읽기 기준과 `parameter_hint` 관리
2. `tmm_mi_model_param_dimension_map` — event type·dimension과 파라미터의 연결 방법 및 comment 관리
3. `tmm_mi_model_param_proposal_m` — 제안·확정 JSON, 처리 상태, 오류와 callback 결과 저장
4. `tmm_mi_model_param_dimension_map` — Basecase Excel의 Sheet·행·열 파싱 규칙 관리

### 문제 4. Mapping과 Step1.5

다음 중 현재 파라미터 후보 처리 규칙을 정확히 설명한 것을 **모두** 고르시오.

1. 활성 `direct` mapping의 파라미터는 Step1.5 비교 없이 후보로 통과한다.
2. `routing` 후보가 하나뿐이어도 항상 Step1.5를 호출한다.
3. 같은 dimension에 `routing` 후보가 2개 이상일 때 Step1.5를 호출하며, `indirect`는 보조정보로 유지하고 `na`는 prompt에서 제외한다.
4. Basecase 값이 없는 파라미터는 활성 mapping이 있어도 후보 결정 단계에서 제외한다.
5. 시나리오 서술상 더 적합해 보여도 LLM은 활성 mapping에 없는 파라미터를 새 후보로 추가할 수 없다.

### 문제 5. Step2·기준값·Step3

다음 중 전체 처리 관계를 정확히 설명한 것은?

1. Step2가 제안값을 계산하고 Step3가 적용 좌표를 다시 선택한다.
2. Step2는 실제 catalog의 exact slot만 선택한다. 서버는 같은 slot의 Basecase를 우선하고 없으면 LUT를 기준값으로 정하며, Step3는 확정된 slot의 제안값과 파라미터 근거·slot 근거를 만든다.
3. Step2에는 Basecase/LUT 원본 행과 두 값을 모두 보내고 LLM이 기준값을 선택하게 한다.
4. Step3가 숫자와 근거를 반환하면 사용자 확인 없이 `CONFIRMED`로 저장하고 수급모델 Excel에도 바로 반영한다.

---

## 3. 주관식 5문항

### 문제 6. Basecase와 LUT 기준값 설명

scenario `595`에서는 다음 값이 확인됐다.

| exact slot | Basecase | LUT |
|---|---:|---:|
| PMI · China · 2026년 7월 | `49.5` | `50` |
| PMI · Japan · 2026년 7월 | 없음 | `50` |

두 slot의 Step3 기준값과 API/DB `basecaseValue`를 각각 쓰고, Country·Year·Month 중 하나라도 다른 “비슷한 위치”의 값을 대신 사용할 수 있는지도 설명하시오.

### 문제 7. DB·`config.yaml`·Object Storage의 역할 설명

다음 항목이 각각 무엇을 정하는지 설명하고, **애플리케이션 시작 시 파일 준비**와 **API 요청 시 후보·기준값 구성**을 구분해 흐름을 작성하시오.

- DB dimension mapping
- DB Parameter master의 `basecase_*`
- `config.yaml`의 Basecase와 LUT 설정
- S3 호환 Object Storage의 `current` release, 원격 파일, packaged fallback

### 문제 8. Prompt 정보와 두 종류의 근거 설명

다음 네 가지를 구분해 설명하시오.

1. scenario·scenario group·event·dimension template 정보가 prompt에 들어가는 방식
2. `parameter_hint`의 역할
3. mapping `comment`의 역할
4. 파라미터 근거와 slot별 value 근거의 차이

### 문제 9. Compact catalog와 key 기반 재조합 설명

Basecase/LUT slot이 많아도 전체 원본을 prompt와 응답에서 반복하지 않는 방식을 Step2부터 Step3 결과 저장까지 순서대로 설명하시오. 다음 용어를 모두 포함한다.

`compact catalog`, `candidate_key`, `slot_axes`, `exact 검증`, `slot_key`, `reference_value`, `서버 재조합`

추가로 `maxParameterSlots=100`이 입력 catalog를 앞의 100개로 자른다는 의미인지도 설명하시오.

### 문제 10. `LiqProdAdjustment` 추가 계획 설명

현재 `LiqProdAdjustment`를 바로 활성화하면 안 되는 이유와 올바른 추가 절차를 설명하시오. 답에는 다음 내용을 포함한다.

- 현재 Basecase와 LUT 상태
- 기존 `liq_util` 대신 `liq_prod` adapter가 필요한 이유와 계산식
- 이용률 `0.95`의 해석
- `parameter_hint`와 mapping comment 보강
- `direct` mapping 유지 시 LiqUtil과의 관계
- 구현·검증·DB 활성화 순서

---

## 4. 객관식 정답과 해설

### 정답 1

**1번**

각 자료의 역할은 다음처럼 이어진다.

- Mapping 정보: scenario의 event type·dimension과 연결된 허용 파라미터 후보를 정하고 mapping method·comment로 연결 판단 기준을 제공한다.
- Parameter 정보: 파라미터의 의미·단위·모델 대상, Basecase 읽기 기준과 prompt hint를 제공한다.
- Basecase/LUT: 후보를 새로 만들지 않고 실제 선택 가능한 exact slot과 현재 기준값을 제공한다. 같은 slot에 Basecase가 있으면 우선하고, 없으면 LUT를 사용할 수 있다.
- Agent 제안: 시나리오 문맥을 반영해 각 파라미터의 정의에 맞는 실제 모델 입력값과 근거를 만들고 사용자가 검토·수정·확정할 수 있게 한다.

따라서 Basecase가 없는 LUT-only slot도 제안할 수 있고, LLM이 mapping 밖의 파라미터를 추가할 수는 없다. 또한 모든 파라미터에 공통된 증감량을 만드는 것이 아니라 각 모델 입력 필드의 의미에 맞는 `proposedValue`를 제안한다.

관련 내용: [개요의 목적과 핵심 Flow](01_MODEL_PARAMETER_AGENT_OVERVIEW.md), [DB의 세 테이블](03_MODEL_PARAMETER_AGENT_DB_SPEC.md#1-세-테이블을-한-문장으로-이해하기), [DB와 config 역할](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md#21-db와-configyaml은-각각-무엇을-정하나)

### 정답 2

**1번, 3번, 5번**

- 비동기 최초 응답의 `PROCESSING`은 접수 완료일 뿐 처리 완료가 아니다.
- callback에는 전체 제안값이 없으며, 현재 Agent에는 proposal 조회용 `GET` API도 없다.
- 확정 단계는 LLM을 호출하지 않고 요청 구조를 검증해 같은 proposal 행을 갱신한다.

관련 내용: [API 사용법](02_MODEL_PARAMETER_AGENT_API_SPEC.md), [Flow의 사용자 확인](04_MODEL_PARAMETER_AGENT_FLOW.md#38-사용자-확인)

### 정답 3

**4번**

mapping 테이블은 후보 연결과 prompt 판단 기준을 관리한다. Basecase Excel의 Sheet·행·열은 Parameter master의 `basecase_*` 설정이 정하고, LUT CSV의 파싱 방식은 `config.yaml`의 adapter와 축 설정이 정한다.

관련 내용: [DB의 세 테이블](03_MODEL_PARAMETER_AGENT_DB_SPEC.md#1-세-테이블을-한-문장으로-이해하기), [DB와 config 역할](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md#21-db와-configyaml은-각각-무엇을-정하나)

### 정답 4

**1번, 3번, 5번**

활성 `direct`와 단일 `routing`은 서버가 후보로 확정하고, 같은 dimension의 `routing` 후보가 2개 이상일 때만 Step1.5가 비교한다. Basecase/LUT는 후보가 확정된 뒤 slot과 기준값을 제공하므로 Basecase 부재가 후보 제외 조건은 아니다. LLM은 활성 mapping 밖의 파라미터를 새 후보로 만들 수 없다.

관련 내용: [후보 결정 규칙](04_MODEL_PARAMETER_AGENT_FLOW.md#31-시나리오-문맥-조회와-파라미터-후보-결정)

### 정답 5

**2번**

Step2는 값을 계산하지 않고 exact slot만 선택한다. 서버가 선택 좌표를 검증하고 Basecase 우선·LUT 대체 규칙으로 기준값과 `slot_key`를 붙인 뒤, Step3가 숫자와 두 종류의 근거를 만든다. LUT만 사용한 slot은 `basecaseValue=null`로 저장될 수 있다. Step3 결과는 먼저 `PROPOSED`가 되며, 별도의 사용자 confirmation을 거쳐야 `CONFIRMED`가 된다. 이 상태가 수급모델 Excel 자동 반영을 뜻하지는 않는다.

관련 내용: [단계별 핵심 로직과 prompt](04_MODEL_PARAMETER_AGENT_FLOW.md#3-단계별-핵심-로직과-prompt)

---

## 5. 주관식 모범답안과 채점 기준

### 모범답안 6

- China 2026년 7월은 같은 exact slot에 Basecase가 있으므로 Step3 기준값과 `basecaseValue`가 모두 `49.5`다.
- Japan 2026년 7월은 Basecase가 없으므로 Step3 기준값은 LUT의 `50`이고 `basecaseValue`는 `null`이다.
- Basecase와 LUT는 Country·Year·Month 등 key 축이 모두 같은 exact slot만 결합한다. 비슷하거나 가까운 좌표의 값은 대신 쓰지 않는다.

**채점 기준:** Basecase 우선, LUT 대체 시 `basecaseValue=null`, exact match 원칙을 모두 설명하면 1점.

관련 내용: [실제 scenario 595 기준값](04_MODEL_PARAMETER_AGENT_FLOW.md#43-실제-기준값-step3-입력과-제안값), [Basecase/LUT 선택 규칙](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md#5-basecase와-lut-중-무엇을-선택하나)

### 모범답안 7

1. 시작 시 `config.yaml`의 Basecase 항목은 로컬 파일명과 원격 object key를 정하고, LUT 항목은 CSV·adapter·필수 header·`key_axes`를 정한다.
2. 파일은 API마다 받지 않는다. 현재 config fingerprint와 파일 목록·크기 등 marker 검증을 통과한 `current` release가 있으면 원격 최신성 확인 없이 재사용한다. 재사용할 수 없으면 exact object key를 `HEAD → GET → HEAD`로 받아 검사하고, 원격이 실패하면 검증된 packaged 파일을 사용한다. 둘 다 실패하면 애플리케이션 시작을 실패시킨다.
3. 요청에서는 DB dimension mapping이 scenario의 event type L2와 dimension을 기준으로 활성 파라미터 후보를 정한다.
4. 후보 Parameter master의 `model_file`, `model_sheet`, `basecase_*`는 Basecase Excel의 Sheet·행·열과 읽기 방식을 정하고, `parameter_name`은 같은 이름의 LUT 설정과 연결된다.
5. 미리 준비된 Basecase와 LUT를 같은 exact key로 결합해 slot과 기준값을 만든다.

**채점 기준:** 후보 선택, Basecase 파싱, LUT 파싱, 시작 시 파일 준비·fallback, exact 결합의 역할을 구분하면 1점.

관련 내용: [DB와 config 역할](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md#21-db와-configyaml은-각각-무엇을-정하나), [Object Storage 준비 구조](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md#11-s3-호환-object-storage에서-파일을-준비하는-구조)

### 모범답안 8

1. DB 행 전체를 보내지 않고 scenario의 제목·설명·dimension·시장 영향, group의 제목·요약·선택 dimension, event의 제목·요약·분석, dimension template의 관련 항목처럼 현재 단계와 후보에 필요한 정보만 `scenario_brief` 등으로 재구성한다. 상태·감사 컬럼과 무관한 dimension은 제외한다.
2. `parameter_hint`는 파라미터 전체에 공통인 값의 의미·단위·스케일·산정 제약을 설명한다.
3. mapping `comment`는 특정 event type·dimension이 해당 파라미터와 연결되는 목적과 판단·값 해석 기준을 설명한다. `routing`에서는 후보 간 선택 기준이 되고, `direct`에서는 후보 통과 여부를 바꾸지 않은 채 이후 slot·값 해석을 돕는다. 관련 있는 `indirect` comment는 보조정보의 `reason`으로 쓰이고 `na`는 prompt에서 제외된다.
4. 파라미터 근거는 파라미터당 하나로 “왜 이 파라미터를 이 scenario에 적용했는가?”를 설명한다. slot별 value 근거는 각 slot마다 “왜 이 정확한 좌표의 기준값을 이 값으로 바꿨는가?”를 설명한다.

**채점 기준:** 필요한 DB 정보만 선별, hint/comment 차이, 두 근거의 질문과 생성 단위를 모두 구분하면 1점.

관련 내용: [DB 활용 컬럼과 prompt 위치](04_MODEL_PARAMETER_AGENT_FLOW.md#52-실제-db-활용-컬럼과-prompt-위치), [hint와 mapping comment](04_MODEL_PARAMETER_AGENT_FLOW.md#hint-and-mapping-comment), [두 종류의 근거](04_MODEL_PARAMETER_AGENT_FLOW.md#36-step3-제안값과-근거-생성)

### 모범답안 9

1. 서버는 Step2에서 같은 고정축의 기간을 leaf로 묶은 `compact catalog`를 보내고 값·출처·원본 행은 제외한다.
2. LLM은 `candidate_key + slot_axes`만 반환한다.
3. 서버가 catalog의 exact 좌표인지 검증한 뒤 유효한 좌표에 `slot_key`를 발급한다.
4. Step3에는 선택된 slot의 `slot_key`, 좌표와 단일 `reference_value`만 보낸다.
5. LLM은 `candidate_key + slot_key + proposed_value + rationale` 중심으로 응답한다.
6. 서버는 key로 보관 중인 파라미터·모델 대상·좌표·기준값을 찾아 최종 결과를 재조합한다.
7. `maxParameterSlots=100`은 LLM이 파라미터별로 반환할 slot 수의 상한이며 입력 catalog를 100개로 자른다는 뜻이 아니다.

**채점 기준:** Step2 압축·최소 응답, exact 검증과 `slot_key`, Step3 최소 응답·재조합, 100개 상한의 의미를 모두 설명하면 1점.

관련 내용: [실제 token 절감 방식](04_MODEL_PARAMETER_AGENT_FLOW.md#51-실제-적용-중인-token-절감-방식), [compact slot catalog](04_MODEL_PARAMETER_AGENT_FLOW.md#53-compact-slot-catalog)

### 모범답안 10

1. 현재 LiqProd master는 비활성이고 DB mapping, `liq_prod` adapter와 runtime config가 없다. 값이 있는 Basecase record도 0건이다. 따라서 현재는 LiqProd 기준값을 만들 수 없으며, adapter와 config를 추가한 이후에는 `BCLiquefaction.csv`에서 계산한 LUT가 값 기준이 된다.
2. 기존 LiqUtil과 같은 `BCLiquefaction.csv`를 공유할 수 있지만, `liq_util`은 이용률을 값으로 만들기 때문에 생산량 단위에는 맞지 않는다.
3. 전용 adapter는 `월 생산능력 × 이용률`로 `Mt LNG/month` 값을 만들어야 한다. 이용률 `0.95`는 이미 95%를 뜻하므로 다시 100으로 나누지 않는다.
4. `parameter_hint`에는 최종 월 생산량의 의미·단위·범위와 LiqUtil과의 차이를 넣고, mapping comment에는 event별 적용·산정 또는 routing 기준을 승인된 문구로 보강한다. 다만 현재 서버가 hint의 `0 이상`이나 월 생산능력 이하 범위를 강제로 검증하는 것은 아니다.
5. 승인·구현 후 event 2·3·17·18은 Notion 기준의 `direct`를 유지한다. 이 중 기존 LiqUtil direct와 겹치는 event 2·17·18에서는 LiqUtil과 LiqProd가 함께 후보가 될 수 있다. 수급모델의 LiqProd 계산 우선순위가 Agent의 LiqUtil 후보를 제거하지는 않는다. Event 11만 `routing`을 유지한다.
6. adapter 구현·단위 테스트 → `config.yaml`과 Object Storage startup 검증 → 비운영 proposal·confirmation 검증 → master와 승인된 mapping 활성화 순서로 진행한다.

실제 계산 예시는 `0.375 × 0.9994350333... = 0.37478 Mt LNG/month`이다.

**채점 기준:** 현재 미지원 상태, 계산식·비율 해석, hint/comment, direct 동시 후보, 검증 후 활성화를 모두 설명하면 1점.

관련 내용: [`LiqProdAdjustment` 추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)

---

## 6. 점수 해석

| 점수 | 이해 수준 | 권장 확인 |
|---:|---|---|
| 9~10점 | 핵심 구조와 운영 주의점을 설명할 수 있음 | 실제 API sample과 신규 파라미터 체크리스트로 확인 |
| 7~8점 | 전체 흐름은 이해했으나 일부 설정 경계가 불명확함 | 틀린 문항의 링크 절만 다시 확인 |
| 5~6점 | 개별 기능은 알지만 단계 간 연결 보완이 필요함 | Flow와 Basecase/LUT 문서를 순서대로 재확인 |
| 0~4점 | 기본 구조부터 다시 보는 것이 좋음 | 개요 → DB → Flow → Basecase/LUT 순서로 확인 후 재응시 |

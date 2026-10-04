# 동일 Scenario Cohort Proposal Coverage Campaign

## 사용 시점

다음 요청에서 이 절차를 사용한다.

- 동일 Scenario 기준 Model Parameter 제안 Before/After 비교
- proposal count·coverage 확대와 실패 원인 분석
- Event 유형을 넓힌 version-pinned v4 Scenario Group campaign
- 좌표명·slot·conditional binding 로직 수정 후 실제 외부개발 DB 재평가

일반 단일 proposal/confirmation 검증은 기본 `SKILL.md` 절차를 사용한다. canonical parameter, binding,
workbook/LUT/config를 변경해야 하면 `$rollout-model-parameters`, release 승인은
`$verify-model-parameter-release`, VM 배포는 `$mi-vm-deploy`로 handoff한다.

## 1. Cohort 생성과 고정

기존 적합 cohort가 부족하면 `$scenario-sync-pipeline`으로 신규 Group을 만든다.

- Scenario API `v4`, generation strategy `multi_event_model_lever_dimensions`만 사용한다.
- 사용자가 지정한 Impact Lever catalog version/checksum을 full pin한다. Lever Full set은 campaign 중 바꾸지 않는다.
- 최근 Event를 우선하되 Event L2와 공급·수요·운송·거시 유형을 다양화한다.
- signpost가 validation/confirmation/parameter proposal의 필수 입력이 아니면 사용자의 비용·시간 선호에 따라 생략할 수 있다. 생략 여부와 이유를 기록한다.
- create 충돌을 정리해야 하면 exact owner/Event 범위의 recoverable 정책만 사용하고 hard delete를 하지 않는다.

Scenario 생성이 끝나면 다음을 immutable cohort identity로 저장한다.

- Scenario Group ID와 Scenario ID 전체 목록
- API version, generation strategy, catalog version/full checksum
- Group별 Event ID/type, Scenario 수, lifecycle/parameter mapping 상태
- capability/workbook release와 SHA, active/runtime allowlist

사용자가 기존 Event 입력 cohort를 고정하라고 명시하면 이 목록은 이번 campaign뿐 아니라 후속 logic/config
고도화에서도 immutable하다. catalog/binding 자체가 바뀌지 않는 한 새 Event·Group·Scenario를 만들지 않는다.

## 2. Before read-back과 실행 후보

먼저 read-only evidence를 만들고 그 뒤에 proposal을 실행한다. 실행 후보는 다음을 모두 만족해야 한다.

1. lifecycle complete
2. stored catalog pin과 active catalog가 exact match
3. selected Lever direction이 `unchanged`가 아니며, `price_only`이면 executable conditional binding이 있음
4. executable binding, active master, runtime allowlist, valid model target을 모두 만족
5. active-but-blocked leakage, catalog mismatch, in-flight proposal 등 hard-stop이 없음

후보가 아닌 Scenario도 삭제하지 말고 `UNCHANGED_LEVER_STATE`, binding 없는 `PRICE_ONLY`,
`INACTIVE_MODEL_PARAMETER`, `NO_PARAMETER_BINDING` 등 exact reason과 함께 보존한다. 후보 pool과 실제 proposal
성공을 섞지 않는다.

Before 실행은 `run_proposal_only.py`로 명시 Group/Scenario만 실행한다. confirmation·callback·outer retry는
사용하지 않는다. 각 Scenario의 DB read-back을 마친 뒤 전체 cohort evidence를 다시 생성한다.

## 3. 진단과 허용되는 개선

성공률을 높이기 위해 유효 model input을 수정하거나 존재하지 않는 model 좌표를 만들지 않는다. 다음 개선은
근거와 회귀 테스트가 있을 때 허용한다.

- 같은 v4 Lever state의 binding을 applicability별로 독립 판정하고, 근거가 각각 있으면 설정 상한까지 복수 선택
- 실제 slot hierarchy를 본 LLM이 원문의 Plant·Train 문구와 좌표 일치 이유를 구조화하고, 서버가 원문 span과
  exact target을 검증하는 일반 좌표 추론. Scenario narrative도 evidence corpus에 쓸 수 있으나 source Event·Lever
  lineage는 필수로 유지
- 실제 좌표에서 자동 생성한 충돌 없는 공통어·약칭·`Stage↔단계`·`Train/T↔호기` 정규화는 보조 안전망으로 사용
- 상대기간을 단일·bounded model period로 보수적으로 해석
- alias/기간 해석을 사용자 rationale note에 표시
- persistence 정밀도 때문에 생기는 test-runner false negative 교정

표기 매칭을 완화해도 출력은 Basecase/target의 exact coordinate여야 한다. Plant만으로 Train을 추론하거나,
`재가동 지연`처럼 경계가 없는 문구로 복수 Train·복수 월을 확대하지 않는다. 동일 Plant·Train evidence가 서로
다른 model target을 승인하지 못하게 하며, 복수 slot에는 각 하위 대상과 exact 기간의 직접 근거 또는 닫힌 범위가
필요하다. Lever lineage의 명시 연월·분기·닫힌 범위가 exact slot을 직접 포함하면 별도 LLM 기간 근거 없이
인정할 수 있다.

모델에 ECA/Rosarito pipeline 같은 exact 좌표가 없으면 임의의 다른 pipeline을 쓰지 않는다. 이런 abstain은
coverage 실패가 아니라 안전한 결과로 보고한다.

binding 자체를 추가·수정할 때만 새 catalog version을 검토한다. 기존 pinned Scenario를 새 binding으로 재해석하지
말고 새 catalog version으로 Scenario를 다시 생성한다. Agent matching/prompt/test만 바뀌고 binding이 같으면 기존
catalog version을 유지한다.

## 4. After 실행 안전

- matcher/config만 바뀐 비교는 Before와 **같은 Group/Scenario ID 및 runtime candidate ID**를 사용한다.
- binding catalog가 바뀌면 저장된 pin을 수정하지 않는다. 같은 Scenario payload를 두 catalog로 hydrate한
  read-only matcher 비교를 만들고, 실제 end-to-end는 같은 ordered Event cohort로 새 catalog version Group을
  생성한다. 이 두 결과를 `same_stored_ids`와 `same_logical_inputs`로 구분한다.
- 기본적으로 Before의 uncovered 실행 후보만 bounded runner에서 Scenario별 한 번 실행한다. 일반 `FAIL`은 격리해
  다음 후보로 진행하고 integrity/scope drift인 `BLOCKED`만 전체 중단한다.
- 실행 evidence가 생기면 Scenario/DB write를 자동 retry하지 않는다. 코드 수정 후 동일 실패 Scenario 재실행은
  `post-fix re-test`로 표시한다. Agent 내부 transient-only LLM retry는 outer retry와 분리해 횟수·사유를 기록한다.
- sandbox/network 차단으로 `attempted=0`인 경우 DB write가 없음을 확인하고, 별도 evidence 파일명으로 승인된 외부 실행을 할 수 있다.
- 한 Scenario 실패가 다음 Scenario를 숨기지 않도록 격리하되 기존 proposal/in-flight guard를 우회하지 않는다.
- After 종료 후 DB 전체 read-back으로 proposal status, identity conflict와 candidate coverage를 재계산한다.

## 5. 동일성·KPI 기계 검증

두 read-back evidence를 다음 스크립트로 비교한다.

```bash
python .claude/skills/model-parameter-multi-event-quality/scripts/compare_same_cohort.py \
  --before <before-evidence.json> \
  --after <after-evidence.json> \
  --output <comparison.json>
```

스크립트는 scope identity, Group IDs, Scenario IDs, runtime candidate IDs가 모두 같아야 `same_cohort=true`로
판정한다. 전체 Proposal Coverage(`covered/all scenarios`)와 실행 후보 성공률(`covered/runtime candidates`)을
별도로 계산하고, 신규 covered·잔여 uncovered·regression·Parameter별 proposal delta를 기록한다. 기존 output은
덮어쓰지 않는다. cohort mismatch 또는 covered regression은 non-zero exit다.

## 6. 테스트·config·fallback

수정 범위의 focused regression과 owning Agent suite를 먼저 실행한 뒤 release suite를 실행한다. 최소 증적은 다음이다.

- alias와 exact output coordinate
- Plant-only/범위 밖 Train/근거 없는 다중 기간 거절
- primary/alternative·conditional의 근거 기반 복수 선택, deterministic 빈 응답 primary 복구와 conditional 0건 유지
- LLM 좌표 추론의 원문 Plant/Train span, exact target, 사용자 note
- slot별 period evidence, 동일 evidence의 복수 target 충돌 거절
- Scenario 실패 격리와 `BLOCKED` campaign hard-stop
- timeout/transport/408/425/429/5xx만 bounded retry, semantic/schema/좌표 실패는 no-retry
- 사용자 note 전파
- proposal/API/DB 비교 정밀도
- capability/workbook/canonical 및 local/Kubernetes config parity

원격 Object Storage가 실패해 packaged fallback을 썼다면 release ID, capability SHA, workbook SHA, semantic schema와
resource fingerprint가 현재 승인 계약과 일치하는지 확인한다. 다른 release의 packaged resource를 교차 사용하지 않는다.

## 7. 결과 보고

구조화 가능한 내용은 표로 작성하고 다음을 포함한다.

1. 동일 cohort/config/checksum 증명
2. `실행 후보` 정의와 후보/비후보 funnel
3. Before/After 전체 coverage, 후보 성공률, proposal row/value count
4. Group/Event 유형별 Scenario·후보·Before→After 결과
5. 전체 Lever→Parameter binding 상태와 campaign 도달/제안 수
6. 실제 수정과 KPI 변화의 인과관계
7. 신규 성공과 잔여 abstain의 Scenario별 이유
8. signpost·price-only·inactive·no-binding·no-coordinate 등 의도적 skip
9. 테스트, config double-check, DB read-back, tag/image/deployment 상태
10. non-blocking 운영 경고와 packaged fallback 판정

보고서에는 비밀값, 전체 prompt 또는 DB 자격증명을 넣지 않는다.

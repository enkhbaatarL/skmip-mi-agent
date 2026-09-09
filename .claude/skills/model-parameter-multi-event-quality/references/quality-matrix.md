# v4 Multi-Event Model Parameter 품질 매트릭스

## 증적 단계

| 단계 | 독립/실행 증적 | 필수 내용 |
|---|---|---|
| catalog-pinned | read-only v4 context | ordered Event, group의 catalog version/checksum, selected Dimension/값, Lever code/ID/domain, hydrated binding |
| raw | production v4 matcher | selected `lever_states`의 executable binding과 active master target으로 만든 모든 후보 |
| runtime | production allowlist partition | `runtime-allowed` 후보와 exact `PROPOSAL_SCOPE_EXCLUDED`가 붙은 `active-but-blocked` 후보 |
| selected | graph `candidate_mappings` 및 adjustment | direct 후보 생존, routing 선택, runtime 경계 밖 후보 없음 |
| proposed | API와 proposal DB row | parameter/model target, v4 `eventId=null`, DB `mi_event_id=NULL`, authoritative group ID |
| confirmed | shared confirmation DB read-back | empty rollback, valid confirmation, reconfirmation, proposal payload 보존 |

active parameter 행은 실행 시 `tmm_mi_model_param_m`의 active 조회 결과로 만든다. allowlist와 blocked reason은 production constants/partition 함수를 사용하며 runner에 별도 목록을 하드코딩하지 않는다.

## 판정 값과 CLI

| 판정 | 의미 | CLI |
|---|---|---:|
| PASS | 실행 범위의 catalog, runtime 경계, persistence/confirmation 계약이 일치한다. | 0 |
| REVIEW | 필수 계약은 지켰으나 routing 미선택, 내부 retry 또는 관측성 누락의 의미 검토가 필요하다. | 0 |
| FAIL | schema, lineage/catalog pin, boundary leakage/reason, persistence/confirmation 또는 실행 계약이 깨졌다. | 1 |
| COVERAGE LIMIT | 적합한 자동-discovery 대상이 없거나 read-only라 실행 chain 증적이 없다. | 0 |

mandatory `FAIL`이 항상 우선한다. successful execution 증적이 없는 read-only 결과를 schema PASS만으로 전체 PASS 처리하지 않는다. 명시한 scenario/group이 없거나 v4 계약 밖이면 범위 입력 오류이므로 `FAIL`이다.

## 1. v4 identity와 ordered Event

필수 계약:

- `api_version=v4`
- `generation_strategy=multi_event_model_lever_dimensions`
- group-event relation 1~5개
- `display_order` exact `1..N`
- Event ID 고유
- 각 selected Dimension의 non-empty `source_event_ids`가 group Event 집합의 부분집합

범위 이탈, 중복, 외부 Event 참조는 `FAIL`이다. v4는 1개 Event도 유효하다.

## 2. Impact Lever catalog pin

group에 저장된 `impact_catalog_version`과 `impact_catalog_checksum`은 context를 만든 active catalog와 정확히 같아야 한다. 각 selected Dimension value의 모든 Lever state는 다음이 active catalog와 같아야 한다.

- `lever_code`와 `impact_lever_id`
- domain
- hydrated binding 순서와 각 binding의 parameter, role, applicability, support status, unsupported reason
- Dimension의 primary Lever code/ID가 active catalog·selected state와 일치하고 해당 state만 primary flag를 가짐

누락, checksum/version mismatch, stale Lever ID, binding drift는 모두 `FAIL`이다. 보고서에는 checksum을 축약 표시할 수 있지만 비교는 전체 문자열로 한다.

## 3. Raw와 runtime 경계

raw 후보는 production `match_v4_parameter_candidates_from_rows()`로 독립 산출한다. 입력은 active master definitions와 검증된 v4 context다. v3 `sourceRefs` 또는 legacy dimension mapping을 섞지 않는다.

raw 후보를 production `partition_proposal_parameter_candidates()`로 분리한다.

- allowlist 안: `runtime-allowed`
- active이지만 allowlist 밖: `active-but-blocked`

blocked 후보에는 exact `PROPOSAL_SCOPE_EXCLUDED` reason code가 있어야 한다. blocked 후보가 runtime candidate, selected adjustment, Step2 `parameter_slots`/`slot_candidate_mappings`, Step3 `effective_references`, API proposal, DB proposal, confirmation 중 하나에 나타나거나 graph `non_input_items`에서 exact reason이 누락되면 `FAIL`이다.

raw/runtime/blocked candidate key는 각 집합 내에서 고유해야 하며 `runtime ∩ blocked = ∅`, `runtime ∪ blocked = raw`여야 한다.

catalog의 `known_unsupported`, `unchanged`, `price_only`, no-binding state는 matcher non-input occurrence identity와 exact reason code multiset으로 graph까지 보존하며 raw executable 후보로 세지 않는다. 누락·중복·reason 변경은 `FAIL`이다.

## 4. 선택, 수렴, 확장

- `mapping_method=direct`인 runtime 후보는 graph selection에서 사라지면 `FAIL`이다.
- 여러 executable binding의 routing 후보가 선택되지 않은 것은 자동 오류가 아니라 `REVIEW`다.
- `load_context + match_v4_parameter_candidates_from_rows` 결과가 독립 expected raw oracle다. context resource로 구성된 `_evaluate_scenario().rule_candidates`는 graph의 v4 raw trace이며, key와 canonical parameter/model target이 독립 oracle와 일치해야 한다.
- raw occurrence identity는 production `v4-lever|Dimension|Lever|parameter|model file|model sheet` key다.
- Step1.5 이후에는 parameter/model target별로 병합된 `parameter|v4|...` key를 사용한다. 단순 key 동등 비교를 하지 않고 `merged_candidate_keys`/binding lineage가 runtime-allowed raw key를 보존하는지 검증한다.
- 각 Step1.5 runtime target은 canonical parameter key를 가진 정확히 한 task여야 하고 `merged_candidate_keys`가 비어 있으면 안 된다. 같은 target을 여러 task로 분할하거나 raw lineage 없는 phantom task를 만들면 `FAIL`이다.
- runtime target은 parameter/file/sheet/table 전체가 독립 runtime target 집합의 부분집합이어야 한다. adjustment처럼 table을 갖지 않는 selected layer는 parameter/file/sheet 경계를 검증한다.
- selected→API proposed→DB proposed→confirmed parameter 집합은 일치해야 한다.

## 5. Event grounding과 값 품질

Step1.5/2/3 입력은 group display order의 관련 Event와 선택 Dimension/Lever lineage를 유지해야 한다. 전체 prompt 원문은 보고서에 저장하지 않는다. trace/packet 증적이 없다면 `REVIEW`; 확인된 Event 순서 또는 selected lineage 불일치는 `FAIL`이다.

수동 검토 항목:

- rationale이 selected Lever의 direction/level/scope/time window와 모순되지 않음
- 같은 parameter로 수렴한 Lever 근거의 충돌을 최종 절대값 하나로 설명함
- 무관한 Event/Dimension이 근거로 유입되지 않음
- 방향 역전 또는 근거 불일치는 `FAIL`, 의미가 모호하면 `REVIEW`

## 6. Slot/reference와 persistence

- Step2 selected slot은 candidate/slot key가 고유하고 Step3 effective reference와 1:1이며 axes가 일치해야 한다. slot 좌표는 exact Basecase+LUT catalog union 안에 있어야 한다.
- Step3 effective reference와 adjustment value cell은 candidate/coordinate multiset이 같아야 하고 실제 Basecase/LUT 값도 일치해야 한다. proposed value는 finite numeric이어야 한다.
- Step3 input/reference/result와 final API/DB/confirmation value 수가 일치해야 한다.
- reference는 Basecase 우선, LUT fallback 한 개다. LUT-only exact slot은 `actual_basecase_value=NULL`, non-null `lut_default_value/llm_reference_value`, `effective_source=lut`이면 유효하다.
- `lutValue`는 API response-only 증적이며 DB proposal/confirmation payload에 저장되면 `FAIL`이다.
- 서버가 여러 Dimension 결과를 임의 합산/평균하지 않는다.
- API `scenarioGroupId`와 DB `scenario_group_id`는 실행 group과 일치한다.
- API에는 `eventId`가 명시적 null이고 DB `mi_event_id`는 NULL이다.
- shared confirmation workflow가 empty rollback, valid confirmation, reconfirmation을 모두 통과한다.
- DB confirmation payload가 proposal payload를 보존한다.

slot 밖 좌표, reference/value 불일치, group/event persistence 위반, confirmation 실패는 `FAIL`이다.

## 7. 실행 안전과 관측성

`--execute` 전 DB/LLM 독립 `model_parameter_core` marker suite가 통과해야 한다. 실패하면 live write를 하나도 시작하지 않고 `FAIL`한다.

runtime Basecase/LUT source는 승인·승격된 `resources/`로 고정한다. `new_resources/`는 선택적 staging 경로이므로 미존재는 정상이며 자동 로드하지 않는다. staging LUT가 있으면 release identity와 canonical 승격 검증 전 live execute를 차단한다.

scenario별 proposal+confirmation workflow는 정확히 한 번만 호출한다. 자동 outer retry는 proposal row 중복 위험 때문에 허용하지 않는다. 실패 후 별도 재실행은 기존 proposal ID/상태를 보존한 운영 판단이다.

runner는 DB 작업 전에 보고서를 exclusive-create한다. 기존 경로가 있거나 생성할 수 없으면 기존 파일을 유지하고 DB 접속 전에 중단한다. 자동 discovery는 bounded scan 안에서 발견한 손상 v4 row의 context/evidence 오류를 숨기지 않고 mandatory evidence로 남긴다.

scenario마다 다음을 기록한다.

- 전체 elapsed time
- Step별 LLM call/token usage가 제공되는 경우 그 값
- 내부 retry 관측값
- proposal row read-back이 실패해도 final response/partial record에서 보존한 proposal ID, failed stage와 persistence/confirmation 상태

180초 초과 또는 1회를 넘는 write workflow attempt는 `FAIL`이다. 내부 LLM retry 또는 필수 token/step 관측성 누락은 `REVIEW`다. provider usage가 없으면 추정값을 만들지 않는다.

## 통합 보고서 완료 조건

- 하나의 Markdown에 schema/core gate, target/catalog pin, selected Lever evidence, active parameter boundary matrix, persistence/confirmation, 성능, 오류/검토 항목을 포함한다.
- mandatory execution error와 catalog/boundary/persistence `FAIL`이 0이어야 PASS/REVIEW가 가능하다.
- read-only 실행 chain 부재와 자동 discovery 대상 부재는 `COVERAGE LIMIT`으로 분리한다.
- release acceptance 요청이면 별도의 `verify-model-parameter-release` 결과를 연결한다.

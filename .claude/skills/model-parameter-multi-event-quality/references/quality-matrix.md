# v3 Multi-Event Model Parameter 품질 매트릭스

## 증적 단계

| 단계 | 독립/실행 증적 | 필수 내용 |
|---|---|---|
| eligible | runner의 read-only sourceRef 역투영 | scenario/group ID, composite dimension, relation template, mapping dimKey, event type, source event IDs, mapping method, model target |
| candidate | Step1 `rule_candidates` | eligible occurrence 전부, mapping 밖 occurrence 없음, 중복 sourceRef의 event ID union |
| selected | Step1.5 `candidate_mappings` | direct 생존, routing 정책 준수, 병합 task의 전체 source lineage |
| proposed | API `proposalParameters`와 proposal DB row | exact model target, slot/value 수, v3 `eventId=null`, DB `mi_event_id=NULL` |
| confirmed | confirmation DB read-back | empty rollback, valid confirmation, reconfirmation, proposal payload 보존 |

active parameter 행은 실행 시 `tmm_mi_model_param_m`의 `use_yn=Y`, `del_yn=N` 결과로 만든다. 특정 이름 목록을 runner에 하드코딩하지 않는다.

## 판정 값

| 판정 | 의미 |
|---|---|
| PASS | 실행 범위의 eligible chain, lineage, mapping, persistence 계약이 모두 일치한다. |
| REVIEW | 형식은 유효하지만 routing 미선택, retry, prompt 관측성 누락 또는 값/rationale의 의미 판단이 필요하다. |
| FAIL | lineage, expected candidate, slot/reference, persistence, confirmation 또는 실행 계약이 깨졌다. |
| COVERAGE LIMIT | 적합한 실제 v3 scenario가 없거나 read-only 모드라 실행 단계 증적이 없다. |

판정 우선순위는 `FAIL > REVIEW > PASS > COVERAGE LIMIT`이다. 단, 적합 sourceRef가 없는 active parameter는 다른 parameter의 성공 여부와 무관하게 그 행만 `COVERAGE LIMIT`이다.

## 1. Lineage 무결성

`FAIL` 조건:

- `sourceEventIds`가 group-event relation에 없음
- sourceRef template ID가 relation template과 연결되지 않음
- sourceRef의 `dimKey` 또는 template ID 누락
- 중복 source event 또는 중복 sourceRef
- source event가 어떤 sourceRef로도 덮이지 않음
- group-event relation이 2~5개 경계를 벗어남

유효 sourceRef에 active DB mapping이 없는 경우 해당 source만 제외하고 경고한다. `parameter_mapping_ready=false`, projection 미존재, pending 또는 rejected는 실행 gate가 아니다.

## 2. Mapping coverage

eligible occurrence key는 다음 필드의 조합이다.

```text
(composite dimension, template ID, mapping dimKey, event type,
 source event ID, parameter, model file, model sheet, mapping method)
```

Step1 candidate occurrence 집합은 eligible 집합과 정확히 같아야 한다. 누락, mapping 밖 parameter, source lineage 손실은 `FAIL`이다.

## 3. 수렴과 확장

- 여러 composite dimension 또는 event type이 같은 model target/parameter에 연결되면 parameter task는 하나이고 source union을 보존해야 한다.
- 한 composite dimension이 여러 direct/routing parameter에 연결되면 모든 eligible parameter task를 유지해야 한다.
- 동일 sourceRef가 여러 event에서 반복되면 candidate task를 중복하지 않고 관련 event ID를 모두 보존해야 한다.
- v3 task identity는 단일 event ID에 의존하지 않는 `parameter|v3|model_file|model_sheet|parameter` 형식이어야 한다.

## 4. Event grounding 및 value 품질

Step1.5, Step2, Step3 입력에는 group display order의 관련 event 정보와 source event lineage가 있어야 한다. 무관한 scenario dimension은 제외한다.

실행 모드에서는 discovery의 event/dimension 표만으로 이 기준을 `PASS` 처리하지 않는다. 완료된 graph state와 production에서 사용한 동일 packet builder로 보존한 각 단계의 실제 `scenario_brief`/task packet을 독립 discovery lineage와 대조한다. 필수 단계 packet 또는 `scenario_brief`가 없거나 event 순서·bounded content, 관련 composite/indirect dimension, source event/sourceRef, 존재하는 승인 projection이 어긋나면 `FAIL`이다. DB event 본문을 읽지 못해 exact content 비교만 불가능한 경우는 `REVIEW`로 남긴다.

수동 검토 항목:

- rationale이 source event와 composite dimension 근거에 모순되지 않음
- 같은 parameter로 수렴한 dimension의 방향·강도·기간·대상 충돌을 최종 절대값 하나로 설명함
- 모호하지만 형식상 유효하면 `REVIEW`
- 누락, 방향 역전, 근거 불일치는 `FAIL`

## 5. Slot 및 reference

- Step2 slot은 exact Basecase+LUT union 안에 있어야 한다.
- Step3 input/reference/result와 final DB value 수가 일치해야 한다.
- reference는 Basecase 우선, LUT fallback 한 개여야 한다.
- 여러 dimension 결과를 서버 합산·평균한 별도 공식은 허용하지 않는다.

slot 밖 좌표, reference 불일치, 값 수 불일치는 `FAIL`이다.

## 6. Persistence/API/Confirmation

v3 필수 계약:

- proposal DB `mi_event_id=NULL`
- API `eventId=null`
- proposal `scenario_group_id`가 실행 group과 일치
- proposal/confirmation read-back 성공
- empty confirmation이 `INVALID_REQUEST`이며 row가 변경되지 않음
- valid confirmation 성공
- reconfirmation 성공 및 timestamp 갱신
- custom parameter 허용 동작 유지
- Basecase/LUT 기준값 정밀도 정책 유지, `proposedValue` 유한 숫자 검증과 설정 기반 양자화 미적용

어느 하나라도 깨지면 `FAIL`이다.

격리된 mock/unit regression은 service/repository 호출 계약을 보조 증명하지만 live DB confirmation 증적을 대체하지 않는다. 보고서에서는 `UNIT PASS/FAIL`로 구분하고, 실제 empty/valid/reconfirmation 결과는 승인된 `--execute`에서만 판정한다.

## 7. 성능 및 관측성

scenario마다 다음을 기록한다.

- prompt bytes와 configured guard
- Step1.5/2/3 prompt/completion/total tokens
- 단계별 및 전체 시간
- outer/internal retry

180초 초과 또는 prompt byte guard 초과는 `FAIL`이다. retry 또는 필수 관측값 미수집은 `REVIEW`다. provider usage가 없으면 추정값을 만들지 않고 `N/A`로 둔다.

## 통합 보고서 완료 조건

- 하나의 Markdown 파일에 schema, discovery, lineage, active parameter matrix, 성능, 경고를 포함한다.
- execution error 0
- lineage/mapping/persistence `FAIL` 0
- 실제 scenario 부재는 parameter별 `COVERAGE LIMIT`으로 분리한다.
- release gate가 포함된 요청이면 별도로 `verify-model-parameter-release` 결과를 연결한다.

# Scenario Group Agent LLM Fallback 제거

## Summary

Create Scenario, Validation, Create Signpost에서 의미적 콘텐츠를 규칙 기반 fallback으로 생성하지 않는다.
제한된 retry 이후 LLM 호출 또는 응답 검증이 실패하면 명시적으로 실패 처리한다.

Create Signpost는 scenario 단위 atomicity를 적용한다. 한 scenario의 signpost 3~6개는 전부 성공해야
저장하지만, 다른 scenario의 정상 결과는 보존한다.

## Implementation Changes

### Create Scenario

- dimension 선택, enum 축소, narrative·가격 방향, compatibility, likelihood, group metadata fallback을 제거한다.
- dimension 누락·중복 또는 template 밖 enum 응답은 invalid LLM response로 처리한다.
- compatibility LLM 실패를 검증 통과로 간주하지 않는다.
- 실패 시 scenario와 완료 stage를 저장하지 않고 동일 사용자의 재요청을 허용한다.
- deterministic MECE와 enum 범위 검사처럼 의미를 생성하지 않는 검증은 유지한다.

### Validation

- 자동 dimension value 생성 실패 시 첫 enum을 선택하는 fallback을 제거한다.
- LLM 결과의 cell 누락·중복·enum 밖 값은 invalid response 오류로 처리하고 request table을 변경하지 않는다.
- LLM 장애는 `result=failure`, 정상적인 부적합 판정만 `result=success, isValid=false`로 구분한다.
- 실패 시 validation stage를 갱신하지 않는다.

### Create Signpost

- label, strength, rationale, keyword 및 신규 scenario 상세 생성 fallback을 제거한다.
- scenario별 subgraph를 제한 병렬 실행하고 각 scenario 내부에서 Stage 2 → Stage 4+5를 순차 실행한다.
- 한 scenario의 signpost 3~6개는 하나의 집합으로 처리하며 일부만 유효하면 전부 저장하지 않는다.
- 제한된 retry까지 실패한 scenario는 저장하지 않되 다른 scenario의 정상 결과는 저장한다.
- 실패 scenario가 남으면 group stage와 전체 scenario status를 완료 상태로 변경하지 않고 failure callback을 보낸다.
- 재요청 시 기존 정상 signpost는 건너뛰고 실패·미생성 scenario만 다시 처리한다.
- 모든 대상 scenario가 완료된 요청에서만 scenario status와 group stage를 완료 상태로 변경한다.

## Error And Retry Contract

- timeout, 429, 일시적 5xx, 연결 오류와 structured-output 검증 실패만 제한적으로 재시도한다.
- 인증·설정·프로그래밍 오류는 즉시 실패시킨다.
- retry 소진 시 `LLM_RESPONSE_TIMEOUT`, `LLM_INVALID_RESPONSE_ERROR`, `LLM_INVOCATION_ERROR` 중 원인에 맞는 `MIBaseError`를 raise한다.
- Background API는 failure callback을, Sync API는 기존 `result=failure` 응답을 반환한다.

## Test Plan

- 각 scenario generation stage의 실패가 fallback 콘텐츠를 생성하지 않는지 검증한다.
- Validation의 호출 실패·누락·enum 밖 값이 request table을 변경하지 않는지 검증한다.
- Signpost scenario 일부 실패 시 다른 scenario의 정상 결과를 보존하는지 검증한다.
- 설정된 semaphore 동시 실행 상한을 지키는지 검증한다.
- Signpost 부분 성공은 저장되지만 stage/status가 완료 처리되지 않는지 검증한다.
- 재요청에서 정상 저장된 scenario를 건너뛰는지 검증한다.

## Assumptions

- 사용자는 의미적 결과가 LLM에 의해 생성·판정되었다고 기대한다.
- 규칙 기반 degraded mode는 제공하지 않는다.
- Create Scenario와 Validation은 전체 작업 단위로 실패 처리한다.
- Create Signpost는 scenario 단위로 저장하되, group 완료 여부는 전체 scenario 기준으로 판단한다.

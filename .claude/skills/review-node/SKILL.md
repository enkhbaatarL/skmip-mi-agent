---
name: review-node
description: 노드/툴 파일을 프로젝트 코드 규칙 기준으로 리뷰합니다. 파일 리뷰, 코드 검토, 코드 리뷰 요청 시 사용.
allowed-tools: Read Grep
---

## 검토 대상

!`git diff HEAD --name-only 2>/dev/null | grep -E "\.(py)$" | head -20`

$ARGUMENTS

위 파일 또는 사용자가 지정한 파일을 아래 기준으로 검토하고 결과를 보고한다.

## 검토 항목

### 1. 구조 검사
- [ ] `from __future__ import annotations` 첫 줄에 있는가?
- [ ] 노드: `@log_node` 데코레이터 적용됐는가?
- [ ] 툴: `@log_tool` 데코레이터 적용됐는가?
- [ ] 커넥터: `@log_connector(connector_type=...)` 적용됐는가?
- [ ] 노드가 상태를 `model_copy(update={...})` 로 반환하는가? (직접 mutate 금지)
- [ ] 툴이 `MariAgentState` 객체를 파라미터로 받지 않는가?

### 2. 타입 힌트 검사
- [ ] 모든 함수 파라미터에 타입 힌트가 있는가?
- [ ] 반환 타입이 명시됐는가?
- [ ] `Any` 사용이 최소화됐는가?
- [ ] `Optional[X]` 대신 `X | None` 형태인가?

### 3. 비동기 검사
- [ ] I/O 작업을 수행하는 함수가 `async def`인가?
- [ ] 불필요한 `time.sleep()` 이 없는가? (`asyncio.sleep()` 사용)

### 4. 오류 처리
- [ ] 외부 호출 예외를 도메인 예외로 래핑하는가?
- [ ] `except Exception` 을 bare로 사용하지 않는가?
- [ ] 예외 체인 `from ex` 가 유지되는가?

### 5. 보안·민감 정보
- [ ] 하드코딩된 API 키/비밀번호가 없는가?
- [ ] `logger.info/debug` 에 민감값이 직접 노출되지 않는가?

### 6. 성능
- [ ] 병렬로 실행 가능한 I/O를 `asyncio.gather()` 로 묶었는가?
- [ ] 세마포어가 필요한 리소스에 적용됐는가?

## 결과 보고 형식

각 항목별 Pass / Fail 과 구체적 수정 제안을 제시한다.
문제가 없는 섹션은 "✅ 이상 없음"으로 표시한다.

# 로깅 규칙

## 로거 임포트
```python
from apps.common.logging.logger_config import logger
```
loguru 기반. `print()` 사용 금지.

## 로그 레벨 가이드라인
| 레벨 | 사용 시점 |
|------|-----------|
| `DEBUG` | 상태 diff, 요청/응답 페이로드, 중간값 |
| `INFO` | 노드/툴/커넥터 시작·종료, 주요 이벤트 |
| `WARNING` | 재시도, 폴백, 예상 가능한 이상 상황 |
| `ERROR` | 처리 불가 예외, 실패 이벤트 |

## 데코레이터별 로그 태그
```
[NODE][함수명]      - @log_node
[TOOL][함수명]      - @log_tool
[CONNECTOR][타입][함수명] - @log_connector
[TIME][함수명]      - @time_log
```

## 로그 포맷
```python
# 구조화 로그 (f-string 내에 key=value)
logger.info(f"[NODE][search_node] START | query={state.rewritten_query!r}")
logger.error(f"[TOOL][my_tool] FAILED | elapsed={elapsed_ms}ms | error={e!r}")
```

## 민감 정보 마스킹
- `api_key`, `password`, `token`, `secret` 포함 키는 로그에서 `***` 처리
- `@log_connector` 데코레이터가 자동 처리 (`_mask_sensitive`)
- 직접 로깅 시 민감값 포함 여부 확인 필수

## @log_connector 옵션
```python
@log_connector(
    connector_type="LLM",   # LLM | HTTP | MCP | VDB | WEB
    log_input=False,        # 요청 페이로드 DEBUG 로그 여부 (기본 True)
    log_output=False,       # 응답 페이로드 DEBUG 로그 여부 (기본 True)
    log_retry=False,        # 재시도 WARNING 로그 여부 (기본 True)
)
```
LLM 호출은 보통 `log_input=False, log_output=False` (페이로드 큼)

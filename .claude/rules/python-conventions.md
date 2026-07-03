# Python 코드 규칙

## 기본 스타일
- Python 3.12+, 모든 `.py` 파일 첫 줄: `from __future__ import annotations`
- ruff 포매터 사용 (line-length=120, indent=4, double quotes)
- import 정렬: `isort` 스타일, `combine-as-imports=true`

## 타입 힌트
- 모든 함수 파라미터·반환 타입 명시 필수
- `Any` 사용은 외부 payload, 동적 JSON, 라이브러리 바인딩처럼 타입을 좁히기 어려운 경계에서만 허용
- 제네릭: `list[str]`, `dict[str, Any]` (대문자 List/Dict 금지)
- Union 타입: `str | None` (`Optional[str]` 금지)

## 비동기 패턴
- 외부 I/O, HTTP, LLM 호출은 `async def` 우선
- LangGraph node는 작업 성격에 따라 sync/async 모두 허용
- 일반 앱 코드에서는 `asyncio.run()` 대신 `await` 체인 유지
- 예외: sync LangGraph pipeline에서 async connector를 bridge하는 기존 패턴은 명시적으로만 허용
- 세마포어는 `async with sem:` 패턴 사용

## Pydantic
- API request/response schema와 LangGraph state는 `pydantic.BaseModel` 우선
- 내부 dict payload 타입은 필요 시 `TypedDict` 허용
- `Field(...)`는 기본값, `default_factory`, alias, description이 필요한 경우 사용
- 검증: `model_validate()`, `model_validate_json()` 사용
- 직렬화: `model_dump()`, `model_dump_json()` 사용

## 예외 처리
- 도메인/API 오류는 `MIBaseError(ErrorCode..., detail=...)` 기준
- 외부 호출 예외는 필요한 경우 `raise MIBaseError(...) from exc`로 래핑
- `except Exception`은 background task, logging/decorator, fallback 처리 같은 경계 지점에서만 허용

## 임포트 순서
```python
from __future__ import annotations

# stdlib
import asyncio
from collections.abc import Callable
from typing import Any

# third-party
from pydantic import BaseModel, Field

# internal
from apps.common.logging.logger_config import logger
from apps.common.configs.config import get_settings
from apps.agents.scenario_group_agent.state import ScenarioDesignState
```

## 금지 패턴
- `print()` 사용 금지 → `logger.info/debug/error()` 사용
- 전역 mutable 상태 생성 금지 (싱글톤 패턴은 `runtime.py` 방식 따르기)
- `time.sleep()` 사용 금지 → `asyncio.sleep()` 사용
- 일반 앱 코드에서 `os.environ` 직접 읽기 금지 → `from apps.common.configs.config import get_settings` 사용
- 예외: 설정 로더/부트스트랩 코드(`config.py`, app 초기화)에서만 환경변수 직접 접근 허용

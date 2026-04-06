# Python 코드 규칙

## 기본 스타일
- Python 3.13+, 모든 `.py` 파일 첫 줄: `from __future__ import annotations`
- ruff 포매터 사용 (line-length=120, indent=4, double quotes)
- import 정렬: `isort` 스타일, `combine-as-imports=true`

## 타입 힌트
- 모든 함수 파라미터·반환 타입 명시 필수
- `Any` 사용은 외부 라이브러리 바인딩에만 허용
- 제네릭: `list[str]`, `dict[str, Any]` (대문자 List/Dict 금지)
- Union 타입: `str | None` (`Optional[str]` 금지)

## 비동기 패턴
- 노드·툴·커넥터는 모두 `async def`
- `asyncio.run()` 대신 `await` 체인 유지
- 세마포어는 `async with sem:` 패턴 사용

## Pydantic
- 모든 상태·스키마는 `pydantic.BaseModel` 상속
- 필드 정의: `Field(default=..., description="...")` 형식 준수
- 검증: `model_validate()`, `model_validate_json()` 사용 (dict 직접 파싱 금지)
- 직렬화: `model_dump()`, `model_dump_json()` 사용

## 예외 처리
- 커스텀 예외는 `apps/common/exceptions/custom.py` 에 정의
- 외부 호출에서 발생하는 예외는 도메인 예외로 래핑: `raise DomainError(...) from ex`
- `except Exception` 최소화 — 구체적 예외 타입 지정

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
from apps.agents.mi_agent.state.state import MariAgentState
```

## 금지 패턴
- `print()` 사용 금지 → `logger.info/debug/error()` 사용
- 전역 mutable 상태 생성 금지 (싱글톤 패턴은 `runtime.py` 방식 따르기)
- `time.sleep()` 사용 금지 → `asyncio.sleep()` 사용
- `os.environ` 직접 읽기 금지 → `get_settings()` 사용

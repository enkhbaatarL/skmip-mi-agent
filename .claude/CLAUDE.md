# MI Agent (skmip-mi-agent) — Claude Guide

## 프로젝트 개요
Market Intelligence AI 에이전트. LangGraph 기반 멀티소스 검색·분석 파이프라인.
사용자 질의 → 쿼리 재작성 → 의도 분류 → 검색 계획 → 병렬 검색(RDB/VDB/Web) → 분석·응답.

## 아키텍처

```
apps/
├── agents/mi_agent/
│   ├── flows/          # 그래프 빌드 & 런타임 진입점
│   ├── nodes/          # 메인 그래프 노드 (rewrite_query, classify_intent, plan, search, analysis)
│   ├── tools/          # 노드가 호출하는 비즈니스 로직 함수
│   ├── prompts/        # LLM 프롬프트 빌더
│   ├── schemas/        # API 입출력 스키마 (MariAgentInput, MariAgentOutput)
│   ├── state/          # LangGraph 상태 정의 (MariAgentState)
│   ├── components/     # SearchPolicySet, 컨텍스트 관리
│   ├── orchestration/  # Supervisor (병렬 검색 팬아웃)
│   └── subgraphs/
│       ├── rdb_search/ # RDB 검색 서브그래프 (prepare → execute)
│       ├── vdb_search/ # VDB 검색 서브그래프 (prepare → execute)
│       └── web_search/ # Web 검색 서브그래프 (prepare → execute)
├── common/
│   ├── configs/        # Settings (pydantic_settings, env.txt)
│   ├── logging/        # decorators: @log_node, @log_tool, @log_connector
│   ├── runtime/        # RuntimeContext (MCP 풀, HTTP, 세마포어 생명주기)
│   ├── streaming/      # @stream_step 데코레이터
│   └── values/         # enums, constants
└── connectors/
    ├── llm/            # invoke_llm_structured_output, invoke_llm_function_call
    ├── mcp/            # MCPClientPool (RDB 접근)
    ├── vdb/            # VectorDB 클라이언트
    ├── http/           # httpx AsyncClient 풀
    └── web/            # Tavily 웹 검색 프로바이더
```

## 메인 그래프 흐름
```
rewrite_query → classify_intent → plan → search → analysis → END
```
- `search` 노드: SearchSupervisor가 rdb/vdb/web 서브그래프를 병렬 팬아웃

## 서브그래프 구조 (rdb/vdb/web 공통 패턴)
```
subgraph_builder.py   # StateGraph 조립 + runnable_graph 생성
subgraph_adapter.py   # to_state() / to_output() 변환 함수
stages/
  prepare/            # 검색 쿼리 준비 노드
  execute/            # 실제 검색 실행 노드
tools/                # 서브그래프 전용 도구 함수
schemas.py            # Input/Output Pydantic 모델
state.py              # 서브그래프 전용 상태
```

## 핵심 규칙

### 데코레이터 필수 적용
- 노드 함수: `@log_node` (+ 필요시 `@stream_step(step_key="...")`)
- 툴 함수: `@log_tool`
- 커넥터 함수: `@log_connector(connector_type="LLM|HTTP|MCP|VDB|WEB")`

### LLM 호출
```python
from apps.connectors.llm.llm_client import invoke_llm_structured_output, LLMStructuredResult

result: LLMStructuredResult[MySchema] = await invoke_llm_structured_output(
    output_schema=MySchema,
    messages=[{"role": "user", "content": prompt}],
    preference=ModelPreference.SPEED,  # or QUALITY
)
```

### RuntimeContext 접근
```python
from apps.common.runtime.runtime import get_mcp_pool, get_llm_semaphore
# RuntimeContext는 싱글톤. 직접 생성하지 말 것.
```

### Settings 접근
```python
from apps.common.configs.settings import get_settings
cfg = get_settings()
# 환경 변수: envs/skmip_mi_agent/env.txt (절대 .env 파일 직접 읽지 말 것)
```

## 코드 스타일
- Python 3.13+, 모든 파일 첫 줄 `from __future__ import annotations`
- ruff 포매터, line-length=120, double quotes
- async-first: 노드/툴/커넥터는 모두 `async def`
- Pydantic v2 모델로 상태·스키마 정의
- 타입 힌트 필수, `Any` 최소화

## 금지 사항
- `.env` 파일 직접 읽기 금지 (settings.json의 deny 규칙)
- `RuntimeContext` 직접 인스턴스 생성 금지 (`get_runtime_context()` 사용)
- `curl` 직접 실행 금지
- `.env` 파일에 시크릿 커밋 금지

## 개발 환경
- 패키지 관리: poetry (`poetry run python ...`)
- 환경 변수: `envs/skmip_mi_agent/env.txt`
- 로거: `from apps.common.logging.logger_config import logger` (loguru)
- 테스트: `poetry run pytest`

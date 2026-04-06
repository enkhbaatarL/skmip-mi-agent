# MI Agent (Market Intelligence Agent)

이 문서는 MI Agent 통합 검색 서비스에 대한 설명 문서입니다. 

개발 및 문서 작업: 이소영 
(* tavily web검색은 전미숙 매니저님 작업 내용 머지)

***
## 1. 개요

### 1) 프로젝트 소개
이 프로젝트는 사용자 질의 의도를 분석해 다양한 데이터 소스(RDB, 벡터DB, 웹)에서 데이터를 검색하고, 
검색된 내용을 기반으로 답변을 제공하는(텍스트, 챠트) AI Agent입니다.

### 2) 기능
1. 핵심 기능
+ 사용자 질의 재작성
: 다중질의 분리 및 키워드/조건 추출을 통해 RDB·VDB·WEB 검색 모듈별 최적 질의로 재작성

+ 의도 분류
: 사용자 질의를 분석해 의도 유형(예: 단일 수치 조회, 시계열/추세 조회 등)으로 분류하며, 
  분류 결과에 따라 일부 처리 흐름이 분기된다.
  (예: 시계열 질의는 결과를 요약하고 차트를 함께 제공).

+ 다중 소스 병렬 검색 및 결과 통합
: RDB·VDB·WEB 데이터 소스를 병렬로 조회하고, 결과를 정규화·우선순위 적용하여 단일 응답 컨텍스트로 통합
  + RDB 검색(Text2SQL): 정형 데이터 대상으로 조건/집계 중심의 질의를 생성·실행해 수치/표 형태 결과를 확보
  + VDB 검색(문서): 컨텐츠 프로바이더/메타데이터 기반 키워드·필터를 반영해 관련 문서/구간을 검색
  + WEB 검색: 최신 이슈/외부 공개 정보 보강이 필요한 경우 웹에서 근거를 수집하고 출처를 함께 제공 (TODO: 일부 추가 작업 필요)

+ 답변 생성
  : 통합된 검색 결과를 근거로 핵심 내용을 분석·요약해 최종 답변을 생성하며, 필요 시 수치/시계열 결과를 차트 데이터로 변환해 텍스트와 함께 제공한다.

2. 부가 기능
+ 스트리밍 응답
  : 사용자 질의 처리 진행 상황을 실시간으로 클라이언트에 스트리밍
+ 토큰 사용량 집계
  : 단일 사용자 질의 처리 과정에서 사용된 LLM 토큰 사용량을 집계·제공

### 3) 기술 스택
+ Language: Python
+ Web Framework: FastAPI
+ Agent Framework: LangGraph
+ Agent Platform: A.X Platform 

## 2. Project Structure
### 1) 기본 구조
├── apps
│   ├── agents
│   │   └── mi_agent
│   │       ├── components
│   │       ├── flows
│   │       ├── nodes
│   │       ├── orchestration
│   │       ├── prompts
│   │       ├── schemas
│   │       ├── state
│   │       ├── subgraphs
│   │       │   ├── rdb_search
│   │       │   ├── vdb_search
│   │       │   └── web_search
│   │       └── tools
│   ├── common
│   │   ├── configs
│   │   │   └── settings.py
│   │   ├── exceptions
│   │   ├── logging
│   │   ├── middleware
│   │   ├── runtime
│   │   ├── streaming
│   │   ├── utils
│   │   └── values
│   └── connectors
│       ├── http
│       ├── llm
│       ├── mcp
│       ├── vdb
│       └── web
├── graph.yaml
└── pyproject.toml

### 2) 상세 구조
├── apps
│   ├── agents
│   │   └── mi_agent
│   │       ├── components
│   │       │   ├── combine.py
│   │       │   ├── context.py
│   │       │   ├── guards.py
│   │       │   ├── metrics.py
│   │       │   └── policies.py
│   │       ├── flows
│   │       │   ├── mari_agent_adapters.py
│   │       │   ├── mari_agent_graph.py
│   │       │   ├── mari_agent_runnable.py
│   │       │   └── mari_agent_runtime.py
│   │       ├── nodes
│   │       │   ├── analyze.py
│   │       │   ├── classify_intent.py
│   │       │   ├── planner.py
│   │       │   ├── rewrite_query.py
│   │       │   └── search.py
│   │       ├── orchestration
│   │       │   ├── policies
│   │       │   │   └── search_policy.py
│   │       │   ├── routers
│   │       │   └── supervisors
│   │       │       └── search_supervisor.py
│   │       ├── prompts
│   │       │   ├── analysis_search_result.py
│   │       │   ├── builders
│   │       │   │   └── analysis.py
│   │       │   ├── chart_similarity_prompt.py
│   │       │   ├── chart_timeseries_prompt.py
│   │       │   ├── classify_analysis_type.py
│   │       │   ├── language_translation.py
│   │       │   ├── loader.py
│   │       │   ├── rdb_search_nl_to_sql.py
│   │       │   ├── rdb_search_rewrite_queries.py
│   │       │   ├── rdb_search_select_target_table.py
│   │       │   ├── rewrite_queries.py
│   │       │   ├── templates
│   │       │   │   ├── analysis.yaml
│   │       │   │   ├── chart.yaml
│   │       │   │   ├── classify.yaml
│   │       │   │   ├── language.yaml
│   │       │   │   ├── nl_to_sql.yaml
│   │       │   │   ├── rdb_queries.yaml
│   │       │   │   ├── rdb_search.yaml
│   │       │   │   ├── rewrite_queries.yaml
│   │       │   │   ├── vdb_queries.yaml
│   │       │   │   └── web_search.yaml
│   │       │   ├── vdb_search_rewrite_queries.py
│   │       │   └── web_search_guide.py
│   │       ├── schemas
│   │       │   ├── mari_agent_input.py
│   │       │   ├── mari_agent_output.py
│   │       │   ├── schemas.py
│   │       │   ├── search_input.py
│   │       │   └── search_output.py
│   │       ├── state
│   │       │   ├── enums.py
│   │       │   ├── search_state.py
│   │       │   └── state.py
│   │       ├── subgraphs
│   │       │   ├── rdb_search
│   │       │   │   ├── schemas.py
│   │       │   │   ├── stages
│   │       │   │   │   ├── execute
│   │       │   │   │   │   └── execute_rdb_search.py
│   │       │   │   │   └── prepare
│   │       │   │   │       ├── candidate_tables.py
│   │       │   │   │       └── search_queries.py
│   │       │   │   ├── state.py
│   │       │   │   ├── subgraph_adapter.py
│   │       │   │   ├── subgraph_builder.py
│   │       │   │   └── tools
│   │       │   │       ├── search_candidates.py
│   │       │   │       ├── search_execution.py
│   │       │   │       └── search_queries.py
│   │       │   ├── vdb_search
│   │       │   │   ├── schemas.py
│   │       │   │   ├── stages
│   │       │   │   │   ├── execute
│   │       │   │   │   │   └── search_documents_node.py
│   │       │   │   │   ├── plan
│   │       │   │   │   └── prepare
│   │       │   │   │       └── rewrite_query_node.py
│   │       │   │   ├── state.py
│   │       │   │   ├── subgraph_adapter.py
│   │       │   │   ├── subgraph_builder.py
│   │       │   │   └── tools
│   │       │   │       ├── search_documents.py
│   │       │   │       └── search_queries.py
│   │       │   └── web_search
│   │       │       ├── schemas.py
│   │       │       ├── stages
│   │       │       │   └── execute
│   │       │       │       └── search_web_node.py
│   │       │       ├── state.py
│   │       │       ├── subgraph_adapter.py
│   │       │       ├── subgraph_builder.py
│   │       │       └── tools
│   │       │           └── web_search.py
│   │       └── tools
│   │           ├── analyze.py
│   │           ├── classify_intent.py
│   │           ├── generate_chart.py
│   │           ├── rewrite_query.py
│   │           └── search_queries.py
│   ├── common
│   │   ├── configs
│   │   │   └── settings.py
│   │   ├── exceptions
│   │   │   └── custom.py
│   │   ├── logging
│   │   │   ├── decorators.py
│   │   │   └── logger_config.py
│   │   ├── middleware
│   │   │   └── exception_handler.py
│   │   ├── runtime
│   │   │   ├── runtime.py
│   │   │   ├── runtime_context.py
│   │   │   ├── shutdown_hooks.py
│   │   │   └── usage_context.py
│   │   ├── streaming
│   │   │   ├── decorators.py
│   │   │   └── texts.py
│   │   ├── utils
│   │   │   ├── time_utils.py
│   │   │   └── timeseries_similarity_utils.py
│   │   └── values
│   │       ├── constants.py
│   │       ├── enums.py
│   │       └── error_codes.py
│   └── connectors
│       ├── http
│       │   ├── http_client.py
│       │   └── http_client_manager.py
│       ├── llm
│       │   └── llm_client.py
│       ├── mcp
│       │   ├── mcp_adapter.py
│       │   ├── mcp_client_manager.py
│       │   └── mcp_client_pool.py
│       ├── vdb
│       │   ├── config_loader.py
│       │   ├── configs
│       │   │   ├── default.yaml
│       │   │   ├── gartner.yaml
│       │   │   └── omdia.yaml
│       │   ├── constants.py
│       │   ├── enums.py
│       │   ├── schemas.py
│       │   └── vector_db.py
│       └── web
│           ├── base.py
│           ├── factory.py
│           └── tavily_provider.py
├── docs
├── graph.yaml
├── pyproject.toml
├── Dockerfile
└── requirements.txt

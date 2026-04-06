
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
```text
├── apps
│   ├── agents                                                     # [Agent구성]
│   │   └── mi_agent
│   │       ├── components                                            # 정책·컨텍스트·메트릭 공통 컴포넌트
│   │       ├── flows                                                 # 그래프 빌드 & 런타임 진입점
│   │       ├── nodes                                                 # 메인 그래프 노드 함수
│   │       ├── orchestration                                         # 병렬 검색 Supervisor·라우터
│   │       ├── prompts                                               # LLM 프롬프트 빌더
│   │       ├── schemas                                               # API 입출력 Pydantic 스키마
│   │       ├── state                                                 # LangGraph 상태 정의
│   │       ├── subgraphs                                             # 검색 서브그래프 모음
│   │       │   ├── rdb_search                                        # RDB(Text2SQL) 검색 서브그래프
│   │       │   ├── vdb_search                                            # 벡터DB 문서 검색 서브그래프
│   │       │   └── web_search                                            # 웹 검색 서브그래프
│   │       └── tools                                                     # 노드가 호출하는 비즈니스 로직
│   ├── common                                                    # [공통]
│   │   ├── configs                                                   # 환경 변수 기반 설정 (pydantic_settings)
│   │   ├── exceptions                                                # 도메인 커스텀 예외
│   │   ├── logging                                                   # 로거 설정 & 데코레이터
│   │   ├── middleware                                                # FastAPI 예외 핸들러
│   │   ├── runtime                                                   # RuntimeContext 싱글톤 관리
│   │   ├── streaming                                                 # 스트리밍 응답 데코레이터
│   │   ├── utils                                                     # 공통 유틸리티 함수
│   │   └── values                                                    # 상수·Enum·에러 코드
│   └── connectors                                                # [Connectors]
│       ├── http                                                      # http 통신
│       ├── llm                                                       # A.X 플랫폼을 통해 LLM 호출
│       ├── mcp                                                       # MCP 통해 RDB 조회
│       ├── vdb                                                       # A.X 플랫폼 통해 벡터DB 연동
│       └── web                                                       # 웹 검색 연동 (Tavily)
├── graph.yaml                                                      
└── pyproject.toml                                                  
```

### 2) 상세 구조
```text
├── apps
│   ├── agents                                                    # [Agent구성]
│   │   └── mi_agent                                                # MI Agent
│   │       ├── components                                          # 1. 정책·컨텍스트 공통 컴포넌트
│   │       │   ├── combine.py                                          # a. 다중소스 결과 병합·중복제거
│   │       │   ├── context.py                                          # b. SearchPolicySet 싱글톤 관리
│   │       │   ├── guards.py                                           # c. 타임아웃·재시도 정책 데코레이터
│   │       │   ├── metrics.py                                          # d. 검색 성능 지표 수집
│   │       │   └── policies.py                                         # e. 검색 실행 정책 모델 정의
│   │       ├── flows                                               # 2. 그래프 빌드 & 런타임 진입점
│   │       │   ├── mari_agent_adapters.py                              # a. 입출력 스키마 변환
│   │       │   ├── mari_agent_graph.py                                 # b. LangGraph 메인 그래프 빌드
│   │       │   ├── mari_agent_runnable.py                              # c. 스트리밍 지원 Runnable
│   │       │   └── mari_agent_runtime.py                               # d. 런타임 초기화·설정
│   │       ├── nodes                                               # 3. 메인 그래프 노드 함수
│   │       │   ├── analyze.py                                          # a. 검색결과 분석·답변 생성
│   │       │   ├── classify_intent.py                                  # b. 사용자 의도 유형 분류
│   │       │   ├── planner.py                                          # c. 검색 계획 노드
│   │       │   ├── rewrite_query.py                                    # d. 질의 재작성·언어 감지
│   │       │   └── search.py                                           # e. 병렬 검색 팬아웃
│   │       ├── orchestration                                       # 4. 병렬 검색 Supervisor·라우터
│   │       │   ├── policies                                            # a. 검색 실행 정책
│   │       │   │   └── search_policy.py                                      # 가) 타임아웃·재시도 정책
│   │       │   ├── routers                                             # b. 조건부 라우팅 (미구현)
│   │       │   └── supervisors                                         # c. 병렬 실행 Supervisor
│   │       │       └── search_supervisor.py                                  # 가) 3소스 병렬 실행·조기종료
│   │       ├── prompts                                             # 5. LLM 프롬프트 빌더
│   │       │   ├── analysis_search_result.py                           # a. 검색결과 분석 프롬프트
│   │       │   ├── builders                                            # b. 복합 프롬프트 조립기
│   │       │   │   └── analysis.py                                           # 가) 분석 프롬프트 조립
│   │       │   ├── chart_similarity_prompt.py                                # 나) 유사도 차트 프롬프트
│   │       │   ├── chart_timeseries_prompt.py                                # 다) 시계열 차트 프롬프트
│   │       │   ├── classify_analysis_type.py                                 # 라) 분석유형 분류 프롬프트
│   │       │   ├── language_translation.py                                   # 마) 언어 번역 프롬프트
│   │       │   ├── loader.py                                                 # 바) YAML 템플릿 로더
│   │       │   ├── rdb_search_nl_to_sql.py                                   # 사) 자연어→SQL 프롬프트
│   │       │   ├── rdb_search_rewrite_queries.py                             # 아) RDB 질의 재작성 프롬프트
│   │       │   ├── rdb_search_select_target_table.py                         # 자) 대상 테이블 선택 프롬프트
│   │       │   ├── rewrite_queries.py                                        # 차) 메인 질의 재작성 프롬프트
│   │       │   ├── templates                                           # c. YAML 프롬프트 템플릿
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
│   │       ├── schemas                                             # 6. API 입출력 Pydantic 스키마
│   │       │   ├── mari_agent_input.py                                 # a. Agent 입력 스키마
│   │       │   ├── mari_agent_output.py                                # b. Agent 출력 스키마
│   │       │   ├── schemas.py                                          # c. 내부 공통 스키마
│   │       │   ├── search_input.py                                     # d. 검색 입력 스키마
│   │       │   └── search_output.py                                    # e. 검색 결과 통합 컨테이너
│   │       ├── state                                               # 7. LangGraph 상태 정의
│   │       │   ├── enums.py                                            # a. 분석유형 열거형
│   │       │   ├── search_state.py                                     # b. 검색 중간 상태
│   │       │   └── state.py                                            # c. 메인 그래프 상태
│   │       ├── subgraphs                                           # 8. 검색 서브그래프 모음
│   │       │   ├── rdb_search                                          # a. RDB(Text2SQL) 서브그래프
│   │       │   │   ├── schemas.py                                          # 가) RDB 입출력 모델
│   │       │   │   ├── stages                                              # 나) RDB 검색 단계
│   │       │   │   │   ├── execute                                             # i. 실행 단계
│   │       │   │   │   │   └── execute_rdb_search.py                               # SQL 생성·실행 노드
│   │       │   │   │   └── prepare                                             # ii. 준비 단계
│   │       │   │   │       ├── candidate_tables.py                                 # 후보 테이블 추출 노드
│   │       │   │   │       └── search_queries.py                                   # SQL용 쿼리 준비 노드
│   │       │   │   ├── state.py                                            # 다) RDB 검색 상태
│   │       │   │   ├── subgraph_adapter.py                                 # 라) 메인↔RDB 상태 변환
│   │       │   │   ├── subgraph_builder.py                                 # 마) RDB 서브그래프 빌드
│   │       │   │   └── tools                                               # 바) RDB 전용 툴
│   │       │   │       ├── search_candidates.py                                # i. 후보 테이블 추출 툴
│   │       │   │       ├── search_execution.py                                 # ii. SQL 실행 툴
│   │       │   │       └── search_queries.py                                   # iii. 검색쿼리 준비 툴
│   │       │   ├── vdb_search                                        # b. VDB 문서검색 서브그래프
│   │       │   │   ├── schemas.py                                        # 가) VDB 입출력 모델
│   │       │   │   ├── stages                                            # 나) VDB 검색 단계 노드
│   │       │   │   │   ├── execute                                             # i. 실행 단계
│   │       │   │   │   │   └── search_documents_node.py                            # 벡터DB 검색 노드
│   │       │   │   │   ├── plan                                                # ii. 계획 단계 (예비)
│   │       │   │   │   └── prepare                                             # iii. 준비 단계
│   │       │   │   │       └── rewrite_query_node.py                               # VDB용 질의 재작성 노드
│   │       │   │   ├── state.py                                          # 다) VDB 검색 상태
│   │       │   │   ├── subgraph_adapter.py                               # 라) 메인↔VDB 상태 변환
│   │       │   │   ├── subgraph_builder.py                               # 마) VDB 서브그래프 빌드
│   │       │   │   └── tools                                             # 바) VDB 전용 툴
│   │       │   │       ├── search_documents.py                                 # i. 벡터DB 문서 검색 툴
│   │       │   │       └── search_queries.py                                   # ii. VDB 쿼리 준비 툴
│   │       │   └── web_search                                        # c. WEB 검색 서브그래프
│   │       │       ├── schemas.py                                        # 가) WEB 검색 입출력 모델
│   │       │       ├── stages                                            # 나) WEB 검색 단계 노드
│   │       │       │   └── execute                                           # i.실행 단계
│   │       │       │       └── search_web_node.py                                # Tavily 웹검색 노드
│   │       │       ├── state.py                                          # 다) WEB 검색 상태
│   │       │       ├── subgraph_adapter.py                               # 라) 메인↔Web 상태 변환
│   │       │       ├── subgraph_builder.py                               # 마) WEB 검색 서브그래프 빌드
│   │       │       └── tools                                             # 바) WEB 검색 전용 툴
│   │       │           └── web_search.py                                     # i. Tavily 웹검색 툴
│   │       └── tools                                               # 9. 노드 비즈니스 로직 툴
│   │           ├── analyze.py                                            # 가) 검색결과 분석·요약 툴
│   │           ├── classify_intent.py                                    # 나) 질의 의도 분류 툴
│   │           ├── generate_chart.py                                     # 다) 차트 데이터 생성 툴
│   │           ├── rewrite_query.py                                      # 라) 질의 재작성 툴
│   │           └── search_queries.py                                     # 마) 검색쿼리 준비 툴
│   ├── common                                                    # [공통]
│   │   ├── configs                                                 # 1. 환경 변수 설정
│   │   │   └── settings.py                                             # a. pydantic_settings 설정 클래스
│   │   ├── exceptions                                              # 2. 도메인 커스텀 예외
│   │   │   └── custom.py                                               # b. 커스텀 예외 정의
│   │   ├── logging                                                 # 3. 로거 설정 & 데코레이터
│   │   │   ├── decorators.py                                           # a. @log_node/tool/connector
│   │   │   └── logger_config.py                                        # b. loguru 로거 설정
│   │   ├── middleware                                              # 4. FastAPI 미들웨어
│   │   │   └── exception_handler.py                                    # a. 전역 예외 핸들러
│   │   ├── runtime                                                 # 5. RuntimeContext 싱글톤 관리
│   │   │   ├── runtime.py                                                  # 가) 리소스 접근 모듈 함수
│   │   │   ├── runtime_context.py                                          # 나) 싱글톤 생명주기 관리
│   │   │   ├── shutdown_hooks.py                                           # 다) 종료 훅 등록
│   │   │   └── usage_context.py                                            # 라) LLM 토큰 누적 추적
│   │   ├── streaming                                               # 6. 스트리밍 응답
│   │   │   ├── decorators.py                                            # a. @stream_step 데코레이터
│   │   │   └── texts.py                                                 # b. 스트리밍 텍스트 상수
│   │   ├── utils                                                   # 7. 공통 유틸리티
│   │   │   ├── time_utils.py                                            # a. 시간 측정 유틸
│   │   │   └── timeseries_similarity_utils.py                           # b. 시계열 유사도 유틸
│   │   └── values                                                  # 8. 상수·열거형
│   │       ├── constants.py                                             # a. 전역 상수
│   │       ├── enums.py                                                 # b. ModelPreference, SearchSource 등
│   │       └── error_codes.py                                           # c. 에러 코드 정의
│   └── connectors
│       ├── http                                                    # 1. httpx 비동기 HTTP 클라이언트
│       │   ├── http_client.py                                           # a. httpx 요청 래퍼
│       │   └── http_client_manager.py                                   # b. HTTP 세션 풀 관리
│       ├── llm                                                     # 2. LLM 호출 클라이언트
│       │   └── llm_client.py                                            # a. 구조화 출력·함수호출
│       ├── mcp                                                     # 3. MCP 클라이언트 풀 (RDB)
│       │   ├── mcp_adapter.py                                           # a. MCP 요청·응답 변환
│       │   ├── mcp_client_manager.py                                    # b. MCP 세션 관리
│       │   └── mcp_client_pool.py                                       # c. MCP 커넥션 풀
│       ├── vdb                                                     # 4. 벡터DB 클라이언트
│       │   ├── config_loader.py                                         # a. VDB 설정 로더
│       │   ├── configs                                                     # 가) VDB 저장소별 설정
│       │   │   ├── default.yaml                                                # i. 기본 VDB 설정
│       │   │   ├── gartner.yaml                                                # ii. Gartner VDB 설정
│       │   │   └── omdia.yaml                                                  # iii. Omdia VDB 설정
│       │   ├── constants.py                                            # b. VDB 상수
│       │   ├── enums.py                                                # c. VDB 열거형
│       │   ├── schemas.py                                              # d. VDB 입출력 스키마
│       │   └── vector_db.py                                            # e. 벡터DB 검색 인터페이스
│       └── web                                                     # 5. 웹검색 프로바이더
│           ├── base.py                                                 # a. 웹검색 추상 인터페이스
│           ├── factory.py                                              # b. 프로바이더 팩토리
│           └── tavily_provider.py                                      # c. Tavily API 구현체
├── docs                                
├── graph.yaml                                                          
├── pyproject.toml                                                      
├── Dockerfile                                                          
└── requirements.txt                                                    
```


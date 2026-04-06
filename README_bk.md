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

## 2. 프로젝트 구조
### 1) 기본 구조

### 2) 상세 구조

***
### 4) LangGraph 파이프라인 흐름
1. 메인 흐름도 (mari_agent_graph.py)
![MI Agent LangGraph Flow](docs/mi_agent_flow.png)

<div align="left">

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif',
    'fontSize': '14px',
    'lineColor': '#ffffff',
    'textColor': '#ffffff'
  },
  'flowchart': { 'padding': 5 }
}}%%
graph TD
    START([START]) --> rewrite[Rewrite Query]
    rewrite --> classify[Classify Intent]
    classify --> plan[Planner]
    plan --> search[Search]
    search --> analysis[Analysis]
    analysis --> END([END])

    style START fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style END fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style rewrite fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style classify fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style plan fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style search fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style analysis fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
```

</div>

2. 상세 흐름도 (메인 + 서브그래프)

<div align="left">

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'lineColor': '#ffffff'}, 'flowchart': {'padding': 5}}}%%
graph TD
    START([START]) --> rewrite[Rewrite Query]
    rewrite --> classify[Classify Intent]
    classify --> plan[Planner]
    plan --> search[Search]

    search --> supervisor

    subgraph supervisor [SearchSupervisor]
        direction TB
        parallel[Parallel Execution]
        parallel --> rdb_subgraph[RDB Search]
        parallel --> vdb_subgraph[VDB Search]
        parallel --> web_subgraph[Web Search]

        rdb_subgraph --> rdb1[Generate Query]
        rdb1 --> rdb2[Select Tables]
        rdb2 --> rdb3[Execute SQL]

        vdb_subgraph --> vdb1[Search Documents]

        web_subgraph --> web1[Search Web]

        rdb3 --> merge[Merge Results]
        vdb1 --> merge
        web1 --> merge
    end

    supervisor --> analysis[Analysis]
    analysis --> END([END])

    style START fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style END fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style rewrite fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style classify fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style plan fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style search fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style supervisor fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style parallel fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style rdb_subgraph fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style vdb_subgraph fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style web_subgraph fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style rdb1 fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style rdb2 fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style rdb3 fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style vdb1 fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style web1 fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style merge fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
    style analysis fill:transparent,stroke:#ffffff,stroke-width:1px,color:#ffffff
```

</div>

#### 서브그래프 상세 흐름

**RDB 검색** (`rdb_search`)
```
prepare_rdb_search_queries_node → select_candidate_tables_node → execute_rdb_search_node
```
- `prepare_rdb_search_queries_node`: 사용자 질의를 RDB 검색에 적합한 다중 쿼리로 재작성
- `select_candidate_tables_node`: 쿼리 기반 후보 테이블 선정
- `execute_rdb_search_node`: 자연어→SQL 변환 후 MCP(RDB)를 통한 쿼리 실행

**VDB 검색** (`vdb_search`)
```
rewrite_query_node → search_documents_node
```
- `rewrite_query_node`: 벡터 검색에 최적화된 쿼리로 재작성
- `search_documents_node`: 벡터DB(Azure AI Search)에서 유사 문서 검색

**Web 검색** (`web_search`)
```
search_web_node
```
- `search_web_node`: Tavily API를 통한 웹 검색 실행

> 세 서브그래프 모두 `MariAgentState → (to_state) → SubgraphState → (to_output) → XxxSearchOutput` 어댑터 패턴으로 메인 그래프 상태와 격리됨

#### 병렬 검색 처리 (SearchSupervisor)

**검색 소스 선택 — `MariAgentInput.search_sources`**

호출 시 `search_sources` 파라미터로 실행할 검색 모듈을 지정한다.

```json
{ "search_sources": ["rdb", "vdb", "web"] }
```

---

**병렬 실행 흐름**

```
search_node
  └─ SearchSupervisor.run_parallel_searches()
       ├─ asyncio.create_task(run_rdb)  ─┐
       ├─ asyncio.create_task(run_vdb)   ├─ 동시 병렬 실행
       └─ asyncio.create_task(run_web)  ─┘
            ↓ 각 태스크 완료 시 결과를 MariAgentState.search_output에 저장
       merge_and_dedupe(rdb_results, vdb_results, web_results)
            ↓
       SearchOutput (통합 결과 반환)
```

`asyncio.wait(FIRST_COMPLETED)` 루프로 완료된 태스크부터 순서대로 결과를 수집한다.

---

**소스별 실행 정책 — `ExecutionPolicy` / `RetryPolicy`**

각 검색 소스는 독립적인 실행 정책을 가진다.

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `exec_timeout_sec` | 단일 검색 시도 최대 허용 시간 | RDB·VDB·Web 각각 환경변수로 설정 |
| `retry.retries` | 최대 재시도 횟수 | `1` (Web은 `1`, RDB·VDB는 `1`) |
| `retry.retry_on` | 재시도 트리거 예외 타입 | `asyncio.TimeoutError` |
| `search_exec_fanout_deadline_sec` | 전체 병렬 검색 하드 데드라인 | 환경변수 `SEARCH_EXEC_FANOUT_DEADLINE_SEC` |

재시도 로직: 타임아웃 발생 시 0.5 초 대기 후 재시도. `retry_on`에 해당하지 않는 예외는 즉시 실패 처리.

---

**가드(Guard) — `with_policy` 데코레이터**

`components/guards.py`의 `@with_policy` 데코레이터를 함수에 적용하면 해당 함수 호출에 자동으로 `ExecutionPolicy`(타임아웃 + 재시도)가 적용된다.

```python
@with_policy(resource=SearchSource.VDB, step="search_vdb")
async def search_vdb_fn(state, ...): ...
```

내부적으로 `asyncio.wait_for(fn(...), timeout=policy.exec_timeout_sec)`로 래핑되며, 취소(`CancelledError`)는 상위로 전파한다.

---

**결과 처리 규칙**

| 상황 | 동작 |
|------|------|
| 소스 성공(`ok`) | 결과를 `merge_and_dedupe`로 통합, `MariAgentState.search_output`에 저장 |
| 타임아웃 | `retry_on=TimeoutError`이면 재시도. 재시도 소진 시 `status="timeout"` |
| 일반 오류 | 재시도 대상이 아니면 즉시 `status="error"`, 에러 상세를 `last_error_by_source`에 기록 |
| 취소(`CancelledError`) | `status="cancel"`, 결과 미수집 (상위 취소 신호에 의한 정상 흐름) |
| 전체 데드라인 초과 | 미완료 태스크 전체 취소 후 루프 종료 |
| 필수 소스 미충족 + `strict_required=True` | `DataRetrievalError` 발생 (현재 기본값: `True`) |
| 필수 소스 모두 `ok` | 나머지 소스 취소 후 즉시 조기 반환 (불필요한 대기 제거) |

> `required_sources`가 비어 있으면 데드라인까지 대기 후 수집된 결과만 반환한다 (부분 성공 허용 모드).

---

**컴포넌트 역할 요약**

| 컴포넌트 | 위치 | 역할 |
|----------|------|------|
| `SearchPolicySet` | `components/policies.py` | 소스별 활성화·필수 여부, 타임아웃·재시도 설정 집합 |
| `ExecutionPolicy` | `components/policies.py` | 단일 소스의 타임아웃 및 재시도 정책 |
| `RetryPolicy` | `components/policies.py` | 재시도 횟수 및 재시도 트리거 예외 타입 |
| `with_policy` 가드 | `components/guards.py` | 함수 레벨 타임아웃·재시도 적용 데코레이터 |
| `merge_and_dedupe` | `components/combine.py` | 복수 소스 결과를 순서 보존·중복 없이 통합 |
| `context` (싱글톤) | `components/context.py` | `SearchPolicySet` 인스턴스를 런타임 전역으로 관리 |
| `Metrics` | `components/metrics.py` | 단계별 성공/실패·소요 시간 관측 (OpenTelemetry 연결 예정) |
| `SearchSupervisor` | `orchestration/supervisors/` | 병렬 팬아웃 실행, 결과 수집, 조기 종료·데드라인 제어 |

***

### 5) 설계 방안
1. **LangGraph 기반 유연한 흐름 제어**
   - **Graph/Subgraph 모듈화**: 전체 flow는 메인 Graph로, 검색 로직은 검색 수단별 Subgraph로 구성
     - 메인 Graph: rewrite → classify → plan → search → analyze
     - 검색 Subgraph: rdb_search, vdb_search, web_search (각각 독립적)
   - **유연한 검색 조합**: `search_sources` 파라미터로 사용할 검색 수단을 동적으로 선택
   - **오케스트레이션형 Supervisor**: LLM 라우팅이 아닌 사용자 요청 기반 subgraph 선택 → 병렬 수행 → 결과 병합
     - 강점: 안정적, 예측 가능, 비용 효율적

2. **고응집/저결합 구조**
   
   **각 계층의 책임과 의존성**
   
   | 계층 | 위치 | 책임 | 의존성 |
   |------|------|------|--------|
   | **Agent** | `agents/mi_agent/` | 비즈니스 로직, Graph 정의 | ✓ common, connectors |
   | **Common** | `common/` | 공통 기능, 설정, 로깅, 런타임 | ✗ 독립적 |
   | **Connectors** | `connectors/` | 외부 시스템 연동 | ✓ common |
   
   **상세 분리 전략**
   
   - **agents/mi_agent/ (도메인 계층)**
     - `flows/`: Graph 정의 및 진입점 (mari_agent_graph, runnable, adapters, runtime)
     - `nodes/`: 각 노드 함수 (rewrite_query, classify_intent, planner, search, analyze)
     - `subgraphs/`: 검색 수단별 서브그래프
       - `rdb_search/`: RDB 검색 (prepare → select → execute)
       - `vdb_search/`: 벡터DB 검색 (search_documents)
       - `web_search/`: 웹 검색 (search_web)
     - `tools/`: 개별 기능 함수들 (analyze, rewrite_query, classify_intent)
     - `prompts/`: LLM 프롬프트 템플릿 (자연어→SQL, 질의 재작성, 의도 분류, 분석)
     - `state/`: 상태 정의 (MariAgentState)
     - `orchestration/`: 검색 조율 (SearchSupervisor, 병렬 실행 관리)
     - `components/`: 공유 컴포넌트 (policies, guards, metrics)
   
   - **common/ (인프라 계층)**
     - `configs/`: 환경 설정 (Pydantic Settings)
     - `runtime/`: 런타임 관리 (RuntimeContext, 리소스 풀)
     - `streaming/`: 스트리밍 처리 (@stream_step 데코레이터)
     - `logging/`: 로깅 설정 (로거, 데코레이터)
     - `exceptions/`: 예외 정의 (커스텀 에러)
     - `middleware/`: 미들웨어 (예외 처리)
     - `values/`: 상수 및 Enum
     - `utils/`: 유틸리티 함수
   
   - **connectors/ (외부 통신 계층)**
     - `llm/`: LLM 연동 (OpenAI AsyncClient 관리)
     - `mcp/`: MCP 연동 (클라이언트 풀, 매니저)
     - `http/`: HTTP 통신 (비동기 클라이언트)
     - `vdb/`: 벡터DB 연동 (Azure AI Search)
     - `web/`: 웹 검색 연동 (Tavily)

   **상태 관리 분리 (State Isolation)**
   
   메인 Graph와 각 Subgraph가 독립적인 State를 사용함으로써 격리 달성:
   
   ```python
   # 메인 Graph State
   class MariAgentState(BaseModel):
       user_query: str
       search_sources: list[str]
       search_results: SearchResults  # 모든 검색 결과 통합
   
   # RDB Subgraph State (독립적)
   class RDBSearchState(BaseModel):
       query: str
       tables: list[str]
       sql: str
   
   # VDB Subgraph State (독립적)
   class VDBSearchState(BaseModel):
       query: str
       repo_ids: list[UUID]
       results: list[Document]
   ```
   
   **장점**
   - ✅ **격리**: 각 Subgraph가 필요한 상태만 관리 → 디버깅 용이
   - ✅ **독립 테스트**: 각 Subgraph를 독립적으로 테스트 가능
   - ✅ **재사용**: State를 여러 Subgraph에서 조합하여 사용 가능
   - ✅ **확장성**: 새 검색 수단 추가 시 기존 State 변경 없음

   **의존성 규칙 (Dependency Rules)**
   ```
   agents/mi_agent → common ✓
   agents/mi_agent → connectors ✓
   common → agents ✗ (역의존 금지)
   connectors → agents ✗ (역의존 금지)
   ```

3. **확장성과 유지보수성**
   - **새 노드 추가**: `nodes/`에 새 파일 추가 → `mari_agent_graph.py`에 등록 (기존 코드 최소 변경)
   - **새 서브그래프 추가**: `subgraphs/new_search/` 생성 → `search_supervisor.py`에 호출 추가 (격리된 구현)
   - **새 외부 연동**: `connectors/new_service/` 생성 → `RuntimeContext`에 리소스 등록 (독립적)

***
## 2. 설치 및 실행

### 1) 의존성 설치
```bash
# Poetry 사용 (권장)
poetry install

# 또는 pip 사용
pip install -r requirements.txt
```

### 2) 환경 설정
```bash
# 환경 파일 생성 및 수정
# 아래 경로에 환경 변수 파일이 필요합니다
envs/skmip_mi_agent/env.txt

# 필수 환경 변수:
# - model_endpoint: LLM 엔드포인트 URL
# - model_api_key: LLM API 키
# - mcp_pool_urls: MCP 서버 URL 맵 (JSON 형식)
# - repo_ids: 벡터DB 저장소 ID 목록
```

### 3) 로컬 실행
```bash
# LangGraph로 실행 (개발 모드)
langgraph dev --config graph.yaml

# 기본 포트: http://localhost:3002
```

### 4) Docker 실행
```bash
# 이미지 빌드
docker build -t mi-agent .

# 컨테이너 실행
docker run -p 18080:18080 mi-agent

# 또는 환경 변수 파일 마운트
docker run -p 18080:18080 -v $(pwd)/envs:/app/envs mi-agent
```

***
## 3. Project Structure

### 1) 전체 디렉토리 구조

```
skmip-mi-agent/
└── apps/                         # 메인 애플리케이션
    ├── agents/                   # 에이전트
    │   └── mi_agent/             
    ├── common/                   # 공통 기능
    └── connectors/               # 외부 통신
```

### 2) 계층별 상세 구조

#### **[A] Agent 계층** - 비즈니스 로직 및 Graph 정의

```
apps/agents/mi_agent/
├── flows/                        # 1. LangGraph 흐름 정의 및 런타임
│   ├── mari_agent_graph.py            # 메인 Graph 구성 (노드, 엣지, entry point)
│   ├── mari_agent_runnable.py         # Runnable 래퍼 (진입점: 로깅, 스트리밍)
│   ├── mari_agent_adapters.py         # 입출력 변환 (Input↔State↔Output)
│   └── mari_agent_runtime.py          # 런타임 초기화 (MCP, 정책, 토큰)
│
├── nodes/                        # 2. Graph 노드 (각 단계 구현)
│   ├── rewrite_query.py               # 사용자 질의 재작성 → 최적화
│   ├── classify_intent.py             # 사용자 의도 분류 (검색 타입 판정)
│   ├── planner.py                     # 전략 수립 (개발 예정)
│   ├── search.py                      # 통합 검색 실행 (RDB/VDB/Web 병렬)
│   └── analyze.py                     # 검색 결과 분석 및 답변 생성
│
├── state/                        # 3. 상태 정의
│   └── state.py                       # MariAgentState (메인 State)
│
├── schemas/                      # 4. Pydantic 데이터 모델
│   ├── mari_agent_input.py            # 에이전트 입력 스키마
│   ├── mari_agent_output.py           # 에이전트 출력 스키마
│   ├── schemas.py                     # 내부 데이터 모델
│   └── search_output.py               # 검색 결과 스키마
│
├── prompts/                      # 5. LLM 프롬프트 템플릿
│   ├── builders/                        # 프롬프트 빌더 모듈
│   │   └── analysis.py                  # 분석 프롬프트 빌더
│   ├── templates/                       # YAML 템플릿 디렉토리
│   │   ├── analysis.yaml                # 분석 프롬프트
│   │   ├── classify.yaml                # 의도 분류
│   │   ├── chart.yaml                   # 차트 생성
│   │   ├── language.yaml                # 언어 감지
│   │   ├── nl_to_sql.yaml               # 자연어 → SQL
│   │   ├── rdb_queries.yaml             # RDB 쿼리
│   │   ├── rdb_search.yaml              # RDB 검색
│   │   ├── rewrite_queries.yaml         # 질의 재작성
│   │   └── web_search.yaml              # 웹 검색 가이드
│   ├── loader.py                        # YAML 프롬프트 로더
│   ├── analysis_search_result.py        # 검색 결과 분석
│   ├── chart_timeseries_prompt.py       # 시계열 차트 생성
│   ├── chart_similarity_prompt.py       # 유사도 기반 시각화
│   ├── classify_analysis_type.py        # 분석 유형 분류
│   ├── language_translation.py          # 언어 번역
│   ├── rdb_search_nl_to_sql.py          # 자연어 → SQL 변환
│   ├── rdb_search_rewrite_queries.py    # RDB 질의 재작성
│   ├── rdb_search_select_target_table.py # 대상 테이블 선정
│   ├── rewrite_queries.py               # 일반 질의 재작성
│   └── web_search_guide.py              # 웹 검색 가이드
│
├── tools/                        # 6. 도구 함수 (노드에서 사용)
│   ├── analyze.py                     # 분석 로직
│   ├── classify_intent.py             # 의도 분류 로직
│   ├── generate_chart.py              # 차트 생성 로직
│   └── rewrite_query.py               # 질의 재작성 로직
│
├── subgraphs/                    # 7. 검색 Subgraph (각 검색 수단별)
│   ├── rdb_search/
│   │   ├── state.py                   # RDBSearchState 정의
│   │   ├── schemas.py                 # 입출력 스키마
│   │   ├── subgraph_builder.py        # Subgraph 구성 (3단계)
│   │   ├── subgraph_adapter.py        # State 변환 (State → RDBSearchState)
│   │   ├── stages/
│   │   │   ├── prepare/
│   │   │   │   ├── candidate_tables.py     # 테이블 후보 선택
│   │   │   │   └── search_queries.py       # 검색 쿼리 생성
│   │   │   └── execute/
│   │   │       └── execute_rdb_search.py   # SQL 실행
│   │   └── tools/                     # RDB 검색 도구
│   │       ├── search_candidates.py   # 후보 테이블 검색
│   │       ├── search_execution.py    # SQL 실행
│   │       └── search_queries.py      # 쿼리 생성
│   │
│   ├── vdb_search/
│   │   ├── state.py                   # VDBSearchState 정의
│   │   ├── schemas.py                 # 입출력 스키마
│   │   ├── subgraph_builder.py        # Subgraph 구성
│   │   ├── subgraph_adapter.py        # State 변환
│   │   ├── stages/execute/
│   │   │   └── search_documents_node.py    # 문서 검색 실행
│   │   └── tools/                     # VDB 검색 도구
│   │       └── search_documents.py    # 문서 검색 로직
│   │
│   └── web_search/
│       ├── state.py                   # WebSearchState 정의
│       ├── schemas.py                 # 입출력 스키마
│       ├── subgraph_builder.py        # Subgraph 구성
│       ├── subgraph_adapter.py        # State 변환
│       ├── stages/execute/
│       │   └── search_web_node.py     # 웹 검색 실행 (Tavily)
│       └── tools/                     # 웹 검색 도구
│           └── web_search.py          # 웹 검색 로직
│
├── orchestration/                # 8. 검색 조율 및 병렬 관리
│   ├── supervisors/
│   │   └── search_supervisor.py       # 검색 Supervisor (RDB/VDB/Web 병렬 관리)
│   ├── routers/                       # (선택) 조건부 라우팅
│   └── guards/                        # (선택) 보안 및 필터링
│
└── components/                   # 9. 공유 컴포넌트
    ├── policies.py                    # 검색 정책 관리
    ├── guards.py                      # 입력 검증, 보안
    ├── context.py                     # 문맥 관리
    ├── metrics.py                     # 성능 측정
    └── combine.py                     # 결과 병합 로직
```
---

#### **[B] Common 계층** - 공통 기능

```
apps/common/
├── configs/                      # 1️⃣ 환경 설정
│   └── settings.py                    # Pydantic Settings (모든 환경 변수)
│
├── runtime/                      # 2️⃣ 런타임 리소스 관리
│   ├── runtime.py                     # 진입점 (ensure_runtime_context_ready)
│   ├── runtime_context.py             # RuntimeContext 싱글톤 (MCP, HTTP 풀)
│   ├── usage_context.py               # 요청별 토큰 추적
│   └── shutdown_hooks.py              # 종료 시 정리 로직
│
├── streaming/                    # 3️⃣ 스트리밍 처리
│   ├── decorators.py                  # @stream_step 데코레이터
│   └── texts.py                       # 스트리밍 텍스트 상수
│
├── logging/                      # 4️⃣ 로깅
│   ├── logger_config.py               # 로거 설정
│   └── decorators.py                  # @log_call 데코레이터
│
├── exceptions/                   # 5️⃣ 커스텀 예외
│   └── custom.py                      # 비즈니스 예외 정의
│
├── middleware/                   # 6️⃣ 미들웨어
│   └── exception_handler.py           # 예외 처리 미들웨어
│
├── values/                       # 7️⃣ 상수 및 Enum
│   ├── enums.py                       # Enum 정의 (SearchType 등)
│   ├── constants.py                   # 상수 정의
│   └── error_codes.py                 # 에러 코드
│
└── utils/                        # 8️⃣ 유틸리티 함수
    ├── time_utils.py                  # 시간 처리
    └── timeseries_similarity_utils.py # 시계열 유사도
```

**RuntimeContext 패턴**
```
ensure_runtime_context_ready()
    ↓
RuntimeContext.get()  # 싱글톤
    ↓
┌─────────────────────────────────────────┐
│ • mcp_pool: MCPClientPool               │
│ • http_client: AsyncHTTPClient          │
│ • llm_semaphore: asyncio.Semaphore      │
│ • search_semaphore: asyncio.Semaphore   │
└─────────────────────────────────────────┘
```

---

#### **[C] Connectors 계층** - 외부 시스템 연동

```
apps/connectors/
├── llm/                          # 1️⃣ LLM 연동
│   └── llm_client.py                  # OpenAI AsyncClient 관리
│
├── mcp/                          # 2️⃣ MCP (Model Context Protocol) 연동
│   ├── mcp_client_pool.py             # 클라이언트 풀 (회사별)
│   ├── mcp_client_manager.py          # 클라이언트 수명 관리
│   └── mcp_adapter.py                 # MCP 응답 변환
│
├── http/                         # 3️⃣ HTTP 통신
│   ├── http_client.py                 # 비동기 HTTP 클라이언트 (aiohttp)
│   └── http_client_manager.py         # 연결 풀 관리
│
├── vdb/                          # 4️⃣ 벡터DB (Azure AI Search)
│   ├── vector_db.py                   # 벡터DB 커넥터
│   ├── constants.py                   # VDB 상수
│   ├── enums.py                       # VDB Enum
│   └── schemas.py                     # VDB 데이터 모델
│
└── web/                          # 5️⃣ 웹 검색
    ├── base.py                        # 웹 검색 기본 클래스
    ├── factory.py                     # 프로바이더 팩토리
    └── tavily_provider.py             # Tavily 웹 검색
```

**Connector 의존성**
```
agents/mi_agent
    ↓ (사용)
common (RuntimeContext)
    ↓ (관리)
connectors (실제 연동)
```

---

### 3) 파일별 책임 정리

| 파일/폴더 | 책임 | 입력 | 출력 |
|-----------|------|------|------|
| **flows/** | Graph 정의 및 진입점 | MariAgentInput | MariAgentOutput |
| **nodes/** | 각 단계 구현 | MariAgentState | MariAgentState |
| **subgraphs/** | 검색 서브그래프 | MariAgentState | SearchResult |
| **state/** | 데이터 구조 정의 | - | State 타입 |
| **schemas/** | 입출력 모델 | - | Pydantic Model |
| **prompts/** | LLM 프롬프트 | 컨텍스트 | 프롬프트 문자열 |
| **tools/** | 비즈니스 로직 | 데이터 | 처리 결과 |
| **orchestration/** | 병렬 실행 관리 | 작업 목록 | 병렬 결과 |
| **common/** | 공통 기능 | - | 공통 서비스 |
| **connectors/** | 외부 연동 | API 요청 | API 응답 |

### 4) 구조 설계 원칙

#### **응집도 (Cohesion) - 높을수록 좋음**
✅ 같은 목적의 코드가 함께 그룹화됨
- `nodes/` 폴더: 각 노드 함수별로 분리
- `subgraphs/` 폴더: 검색 수단별로 분리

#### **결합도 (Coupling) - 낮을수록 좋음**
✅ 계층 간 명확한 경계
- Agent → Common → Connectors (일방향)
- 역의존 금지 (common → agents ✗)

#### **확장성 (Scalability)**
✅ 새 기능 추가 시 기존 코드 변경 최소화
- 새 노드: `nodes/new_node.py` + `mari_agent_graph.py` 수정
- 새 검색: `subgraphs/new_search/` 생성 + `search_supervisor.py` 수정
- 새 외부 연동: `connectors/new_service/` 생성 (독립적)

***
## 4. 상세 설명

### (1) Agent 구성

#### a) flows/ 모듈 상세 설명

**전체 흐름**
```
mari_agent_input
     ↓
[mari_agent_adapters] Input → State 변환
     ↓
[mari_agent_runtime] 런타임 초기화 (MCP, 정책, 토큰)
     ↓
[mari_agent_graph] 메인 Graph 실행
     ↓
[mari_agent_adapters] State → Output 변환
     ↓
mari_agent_output
```

**각 파일의 역할**

| 파일 | 역할 | 책임 |
|------|------|------|
| `mari_agent_graph.py` | **Graph 정의** | 노드 추가, 엣지 연결, entry/finish 포인트 |
| `mari_agent_adapters.py` | **입출력 변환** | Input → State, State → Output 변환 로직 |
| `mari_agent_runnable.py` | **Runnable 래퍼** | 로깅, 스트리밍, 성능 측정 추가 |
| `mari_agent_runtime.py` | **런타임 초기화** | MCP 풀, 검색 정책, 토큰 추적 설정 |

**mari_agent_graph.py 예시**
```python
def build_mi_agent() -> Runnable:
    graph = StateGraph(state_schema=MariAgentState)

    # 노드 등록
    graph.add_node("rewrite_query", rewrite_query_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("plan", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("analysis", generate_analysis)

    # 흐름 정의
    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "classify_intent")
    graph.add_edge("classify_intent", "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "analysis")
    graph.add_edge("analysis", END)

    return graph.compile()
```

**mari_agent_adapters.py 예시**
```python
def to_state(raw: dict[str, Any] | MariAgentInput) -> MariAgentState:
    """MariAgentInput → MariAgentState"""
    mi = raw if isinstance(raw, MariAgentInput) else MariAgentInput.model_validate(raw)
    return MariAgentState(
        company_code=mi.company_code,
        user_query=mi.user_query,
        search_sources=mi.search_sources,
        # ...
    )

def to_output(state_dict: dict[str, Any]) -> MariAgentOutput:
    """MariAgentState → MariAgentOutput"""
    return MariAgentOutput(
        answer=state_dict.get("analysis").answer,
        evidence=state_dict.get("analysis").evidence,
        usage=get_usage(),
    )
```

**mari_agent_runnable.py 예시**
```python
class MariAgentRunnable(Runnable):
    """진입점: 로깅, 스트리밍, 성능 측정"""

    async def astream(self, input, config=None, **kwargs):
        """스트리밍 모드: 진행 상황 실시간 전달"""
        t0 = time.perf_counter()
        state = to_state(input, **kwargs)
        await ensure_runtime(state, **kwargs)

        # 1. stream_mode 설정 (custom + values 필수)
        stream_modes = _normalize_stream_modes(kwargs.get("stream_mode") or self._stream_modes)
        if "custom" not in stream_modes:
            stream_modes.append("custom")  # 노드별 진행 상황 이벤트
        if "values" not in stream_modes:
            stream_modes.append("values")  # 최종 상태 캡처용

        # 2. Graph 스트리밍 실행
        last_state = None
        async for chunk in self._graph.astream(state, config=config, stream_mode=stream_modes):
            mode, data = _split_stream_chunk(chunk)
            if mode == "custom":
                yield data  # @stream_step 데코레이터에서 생성된 진행 이벤트
                continue
            if mode == "values":
                last_state = data  # 최종 상태 저장
                continue

        # 3. 최종 결과 이벤트 생성 (complete)
        if last_state is not None:
            output = to_output(last_state)
            total_latency_ms = int((time.perf_counter() - t0) * 1000)
            for event in _emit_final_events(output, total_latency_ms):
                yield event


def _emit_final_events(output: MariAgentOutput, latency_ms: int) -> Iterator[dict]:
    """최종 결과를 단일 SSE 이벤트로 생성"""
    segment_data = {
        "sources": output.evidence.model_dump(exclude_none=True),      # 검색 출처
        "suggestions": output.answer.suggested_questions,               # 추천 질문
    }

    # 선택적 데이터 추가
    if output.answer.timeseries_insights:
        segment_data["timeseries_insights"] = output.answer.timeseries_insights.model_dump()
    if output.evidence.rdb and output.evidence.rdb.charts:
        segment_data["chart_summaries"] = [c.model_dump() for c in output.evidence.rdb.charts]
    if output.usage:
        segment_data["usage"] = output.usage.model_dump(exclude_none=True)

    yield {
        "state": "complete",
        "data": "message",
        "node": "analysis",
        "value": f"{output.answer.analysis_summary}\n\n{output.answer.content}",
        "segment": segment_data,
        "latency_ms": latency_ms,
    }
```

**mari_agent_runtime.py 예시**
```python
async def ensure_runtime(state, **_):
    """런타임 초기화"""
    # 1. RuntimeContext 준비 (MCP 풀, HTTP 클라이언트)
    await ensure_runtime_context_ready()
    
    # 2. 토큰 사용량 추적 초기화
    reset_usage()
    
    # 3. MCP 클라이언트 풀 확보
    company_code = state.company_code
    await ensure_mcp_pool(company_code)
    
    # 4. 검색 정책 설정
    search_sources = state.search_sources
    set_search_policies(build_search_policy_set(search_sources))
```

#### b) nodes
각 노드는 `@stream_step` 데코레이터로 진행 상황을 스트리밍합니다.
```python
from apps.common.streaming.decorators import stream_step

@stream_step(step_key="search")
async def search_node(state: MariAgentState) -> MariAgentState:
    """RDB/VDB/Web 검색을 병렬로 실행"""
    supervisor = SearchSupervisor(state)
    results = await supervisor.execute()
    return state.update(search_results=results)
```

#### c) subgraphs
시나리오별로 실행될 서브그래프를 정의합니다.
```python
# rdb_search/subgraph_builder.py
def build_rdb_search_subgraph() -> CompiledStateGraph:
    graph = StateGraph(RdbSearchState)

    graph.add_node("select_tables", select_candidate_tables_node)
    graph.add_node("generate_queries", generate_search_queries_node)
    graph.add_node("execute_sql", execute_rdb_search_node)

    graph.set_entry_point("select_tables")
    graph.add_edge("select_tables", "generate_queries")
    graph.add_edge("generate_queries", "execute_sql")
    graph.set_finish_point("execute_sql")

    return graph.compile()
```

#### d) state
MariAgentState 정의. 파이프라인 전체에서 공유되는 상태입니다.
```python
class MariAgentState(MariAgentInput):
    user_query_language: str | None = None           # 사용자 질의 언어 (영어/한국어)
    rewritten_query: str | None = None               # LLM에 의해 재작성된 보완 질의
    analysis_type: AnalysisType | None = None        # 분석 유형
    search_output: SearchOutput = Field(default_factory=SearchOutput)  # 검색 결과
    analysis_content: str | None = None              # 상세 분석 내용
    suggested_questions: list[str] = Field(default_factory=list)       # 추천 질문
    analysis_summary: str | None = None              # 핵심 인사이트 (2-3문장)
    timeseries_insights: TimeSeriesInsights | None = None  # 시계열 인사이트
    current_node: str | None = None                  # 현재 실행 중인 노드
    executed_nodes: list[str] = Field(default_factory=list)  # 실행된 노드 목록
    usage: dict | None = None                        # LLM 사용량 정보
```

### (2) Connectors

#### a) LLM Client
A.X 플랫폼을 통해 LLM 모델 호출 (비동기)
```python
class LLMClient:
    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(
            base_url=settings.model_endpoint,
            api_key=settings.model_api_key,
        )

    async def chat_completion(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> ChatCompletion:
        return await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
        )
```

#### b) MCP Client Pool
MCP Server 연동을 위한 클라이언트 풀 관리
```python
class MCPClientPool:
    def __init__(self, pool_size: int, mcp_urls: dict[str, str]):
        self.pool_size = pool_size
        self.mcp_urls = mcp_urls
        self._pools: dict[str, asyncio.Queue] = {}

    async def acquire(self, company_code: str) -> MCPClient:
        """풀에서 MCP 클라이언트 획득"""
        pool = self._pools.get(company_code)
        return await pool.get()

    async def release(self, company_code: str, client: MCPClient):
        """MCP 클라이언트 반환"""
        await self._pools[company_code].put(client)
```

#### c) Vector DB
A.X 플랫폼을 통해 벡터DB 문서 검색
```python
async def search_documents(
    repo_ids: list[UUID],
    query: str,
    top_k: int = 5,
) -> list[VectorSourceModel]:
    """벡터DB에서 문서 검색"""
    results = []
    for repo_id in repo_ids:
        docs = await vector_db.similarity_search(
            repo_id=repo_id,
            query=query,
            top_k=top_k,
        )
        results.extend(docs)
    return results
```

### (3) 공통

#### a) 스트리밍 처리

**개념**
- `Runnable`: LangChain의 표준화된 실행 인터페이스로 `astream()` 등의 메서드 제공
- `MariAgentRunnable`: 기본 Graph에 로깅, 스트리밍, 성능 측정을 추가한 Runnable 래퍼
- `@stream_step`: 각 노드의 진행 상황을 실시간으로 SSE 이벤트로 스트리밍하는 데코레이터

**흐름**
```
입력 → MariAgentRunnable.astream()
     ↓
  @stream_step 데코레이터 (각 노드)
     ↓
  custom 이벤트 수집 → SSE 전송
     ↓
  _emit_final_events() (최종 이벤트 포장)
     ↓
출력 (sources, chart_summaries, suggestions, usage)
```

---

##### `@stream_step` 데코레이터 상세

**목적**
LangGraph 노드 함수에 적용하여 진행 상황을 클라이언트로 실시간 스트리밍합니다.

**동작 원리**
1. `langgraph.config.get_stream_writer()`로 스트림 writer 획득
2. 함수 시작 시 `node_start` 이벤트 발행
3. 함수 정상 종료 시 `node_end` 이벤트 발행 (실행 시간 포함)
4. 예외 발생 시 `error` 이벤트 발행 후 예외 재발생

**파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `step_key` | `str \| None` | `STREAM_TEXTS`에서 텍스트 조회용 키. 미지정 시 함수명 사용 |
| `label` | `str \| None` | 직접 라벨 지정. `step_key`보다 우선 적용 |

**텍스트 결정 우선순위**
1. `label` 파라미터가 있으면 → `"{label} 시작"` / `"{label} 완료"`
2. `step_key`가 `STREAM_TEXTS`에 있으면 → 해당 start/end 텍스트 사용
3. 둘 다 없으면 → `"{함수명} 시작"` / `"{함수명} 완료"`

**스트림 이벤트 형식**

```python
# node_start 이벤트 (함수 시작 시)
{
    "state": "progress",
    "data": "message",
    "node": "step_key 또는 함수명",
    "value": "시작 메시지",
    "type": "node_start"
}

# node_end 이벤트 (함수 정상 종료 시)
{
    "state": "progress",
    "data": "message",
    "node": "step_key 또는 함수명",
    "value": "완료 메시지",
    "type": "node_end",
    "latency_ms": 1234  # 실행 시간 (밀리초)
}

# error 이벤트 (예외 발생 시)
{
    "state": "error",
    "data": "message",
    "node": "step_key 또는 함수명",
    "value": "{step_key} 실패: {에러 메시지}",
    "type": "error"
}
```

**STREAM_TEXTS 정의 방법**

`apps/common/streaming/texts.py`에서 step_key별 시작/완료 메시지를 정의합니다.

```python
# apps/common/streaming/texts.py
STREAM_TEXTS: dict[str, dict[str, str]] = {
    "rewrite_query": {
        "start": "Rewriting your query for clarity",
        "end": "Finished rewriting your query for clarity",
    },
    "analysis": {
        "start": "Reviewing the data to uncover insights",
        "end": "Finished reviewing the data to uncover insights",
    },
    # 새로운 step_key 추가 시 여기에 정의
    "my_custom_step": {
        "start": "커스텀 작업 시작",
        "end": "커스텀 작업 완료",
    },
}
```

**사용 예시**

```python
from apps.common.streaming.decorators import stream_step
from apps.common.logging.decorators import log_node

# 방법 1: step_key로 STREAM_TEXTS 참조
@stream_step(step_key="analysis")
@log_node
async def generate_analysis(state: MariAgentState) -> MariAgentState:
    # 비즈니스 로직
    return state

# 방법 2: label로 직접 라벨 지정 (STREAM_TEXTS 불필요)
@stream_step(label="검색 실행")
async def search_node(state: MariAgentState) -> MariAgentState:
    # "검색 실행 시작" → 실행 → "검색 실행 완료" 이벤트 발행
    return state

# 방법 3: 파라미터 없이 사용 (함수명이 step_key로 사용됨)
@stream_step()
async def my_custom_node(state: MariAgentState) -> MariAgentState:
    # "my_custom_node 시작" → 실행 → "my_custom_node 완료" 이벤트 발행
    return state
```

**주의사항**
- 동기/비동기 함수 모두 지원 (내부에서 자동 감지)
- `@log_node`와 함께 사용 시 `@stream_step`을 **먼저** 적용 (위에 배치)
- 함수 내에서 예외 발생 시 자동으로 error 이벤트 발행 후 예외 재발생
- LangGraph의 `stream_mode`에 `"custom"`이 포함되어야 이벤트 수신 가능

---

**최종 SSE 이벤트 형식 (complete)**
```json
{
  "state": "complete",
  "data": "message",
  "node": "analysis",
  "value": "분석 내용...",
  "segment": {
    "sources": { "rdb": {...}, "vdb": [...], "web": [...] },
    "timeseries_insights": {...},
    "chart_summaries": [...],
    "suggestions": ["추천 질문 1", "추천 질문 2"],
    "usage": { "prompt_tokens": 1500, "completion_tokens": 800 }
  },
  "latency_ms": 5234
}
```

#### b) RuntimeContext 패턴
프로세스 전역 리소스 (MCP 풀, HTTP 클라이언트, 세마포어) 관리
```python
from apps.common.runtime.runtime import ensure_runtime_context_ready

# 런타임 초기화
await ensure_runtime_context_ready()

# 리소스 접근
runtime = RuntimeContext.get()
mcp_pool = runtime.mcp_pool
http_client = runtime.http_client
```

#### c) 토큰 사용량 추적
`contextvars` 기반 요청별 LLM 토큰 사용량 추적
```python
from apps.common.runtime.usage_context import reset_usage, accumulate_usage, get_usage

# 새 요청 시 초기화
reset_usage()

# LLM 호출 후 누적
accumulate_usage(response.usage)

# 최종 사용량 조회
total_usage = get_usage()
```

***
## 5. 환경 설정

### 환경 변수 파일 위치
```bash
envs/skmip_mi_agent/env.txt
```

### 주요 환경 변수

#### LLM 설정
| 변수명 | 설명 |
|--------|------|
| `model_endpoint` | LLM 엔드포인트 URL |
| `model_api_key` | LLM API 키 |
| `model_api_deployment_name` | 기본 모델 배포명 |
| `llm_concurrency` | LLM 동시 요청 수 |
| `llm_timeout_sec` | LLM 타임아웃 (기본: 90초) |

#### MCP 설정
| 변수명 | 설명 |
|--------|------|
| `mcp_pool_urls` | MCP 풀 URL 맵 (JSON) |
| `company_mcp_map` | 회사별 MCP 맵 (JSON) |
| `mcp_pool_size` | MCP 풀 크기 |
| `mcp_client_timeout` | MCP 클라이언트 타임아웃 |

#### 검색 설정
| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `search_sources` | 검색 소스 목록 | `["web", "rdb", "vdb"]` |
| `search_exec_fanout_deadline_sec` | 검색 실행 제한 시간 | 240초 |

#### 웹 검색 설정
| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `web_search_provider` | 웹 검색 프로바이더 | `tavily` |
| `tavily_api_key` | Tavily API 키 | - |
| `tavily_max_results` | 최대 결과 수 | 5 |

***
## 6. API 사용법

### 입력 스키마 (MariAgentInput)
```json
{
  "input": {
    "authorized_product_nums": [
      "70008",
      "70037",
      "70039"
    ],
    "company_code": "2014",
    "search_sources": [
      "web",
      "rdb",
      "vdb"
    ],
    "user_num": 12345,
    "user_query": "최근 6개월간 달러지수(DXY) 가격흐름을 알려줘."
  },
  "config": {},
  "kwargs": {}
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `user_query` | string | O | 사용자 질의 |
| `company_code` | string | O | 회사 코드 |
| `search_sources` | string[] | O | 검색 소스 목록 (`web`, `rdb`, `vdb`) |
| `authorized_product_nums` | int[] | O | 접근 권한 있는 상품 번호 |
| `user_num` | int | X | 사용자 번호 |
| `histories` | object[] | X | 대화 히스토리 |

### 출력 스키마 (MariAgentOutput)
[invoke호출]
```json
{
  "output": {
    "answer": {
      "content": "요청하신 2025-07-28 ~ 2026-01-27 기간의 달러지수(DXY) 가격 흐름에 대해 안내드립니다.\n\n---\n\n**요청 기간(requested_range):** 2025-07-28 ~ 2026-01-27  \n**수치데이터 제공 기간(available_range):** 2025-07-28 ~ 2025-10-31  \n※ 현재 수치데이터는 2025-10-31까지만 제공되고 있습니다. 이후 기간의 수치는 확인할 수 없습니다.\n\n---\n\n### 1. 시계열 추세 및 주요 수치\n\n| 구분         | 날짜         | DXY 지수(pts) |\n|--------------|--------------|--------------|\n| 최초값       | 2025-07-28   | 98.6340      |\n| 최종값       | 2025-10-31   | 99.8040      |\n| 최고값       | 2025-07-31   | 99.9680      |\n| 최저값       | 2025-09-16   | 96.6330      |\n| 변화율       |              | +1.19%       |\n\n- **변화율 계산:** ((99.8040 - 98.6340) / 98.6340) * 100 = +1.19%\n- **최고치:** 2025-07-31, 99.9680 pts\n- **최저치:** 2025-09-16, 96.6330 pts\n\n---\n\n### 2. 변동성 분석\n\n- 일간 변동률(%) 최대값: 약 1.98% (2025-09-16, 전일 대비 하락)\n- **변동성 분류:** 보통 (1% 이상 3% 미만)\n\n---\n\n### 3. 추세 요약\n\n- 2025-07-28~2025-07-31: 단기 상승(최고치 99.9680 pts)\n- 2025-08~09월: 점진적 하락세, 9월 중순 최저치(96.6330 pts) 기록\n- 2025-09-16 이후: 반등 및 변동, 10월 말 99.8040 pts로 마감\n\n---\n\n### 4. 해석 및 시사점 (2025-07-28~2025-10-31 기준)\n\n- 해당 기간 동안 DXY는 단기 상승 후 하락, 이후 반등하는 변동성을 보였습니다.\n- 웹검색 결과에 따르면, 달러지수의 하락은 미국 정부의 약달러 용인 발언, 금리 동결 전망, 재정적자 및 국채 발행 확대 가능성 등과 연관되어 있습니다(2025년 9~10월).\n- DXY가 하락하면 원/달러 환율도 하락(원화 강세)하는 경향이 있으며, 실제로 2025년 10월 원/달러 환율이 1,430원대까지 하락한 것으로 확인됩니다.\n- 달러 약세는 글로벌 위험자산(주식, 원자재 등)에 긍정적 영향을 줄 수 있으며, 미국 내 인플레이션 압력은 다소 커질 수 있습니다.\n\n---\n\n### 5. 표로 정리\n\n| 항목명      | 수치/내용      | 변화율   | 특징/비고                  |\n|-------------|---------------|----------|----------------------------|\n| 최초값      | 98.6340 pts   | -        | 2025-07-28                 |\n| 최종값      | 99.8040 pts   | +1.19%   | 2025-10-31                 |\n| 최고값      | 99.9680 pts   | -        | 2025-07-31                 |\n| 최저값      | 96.6330 pts   | -        | 2025-09-16                 |\n| 변동성      | 보통          | -        | 일간 최대 1.98%            |\n| 주요 이벤트 | 약달러 발언, 금리 동결 전망 | - | 2025-09~10월, 웹검색 근거 |",
      "suggested_questions": [
        "2025-07-28 ~ 2025-10-31 기간 동안 DXY 변동에 영향을 준 주요 경제 이벤트는 무엇이었나요?",
        "같은 기간 동안 원/달러 환율이나 주요 주가지수(S&P500, 코스피)와 DXY의 상관관계를 비교해볼 수 있을까요?",
        "현재 수치데이터가 2025-10-31까지만 제공되고 있는데, 이후 2025-11~2026-01까지의 DXY 흐름을 확인하려면 어떤 추가 소스를 활용해야 할까요?"
      ],
      "analysis_summary": "2025-07-28~2025-10-31 기간 달러지수(DXY)는 98.6340에서 99.8040으로 약 1.19% 상승했으며, 중간에 96.6330까지 하락 후 반등하는 변동성을 보였습니다. 변동성은 일간 최대 1.98%로 '보통' 수준이며, 약달러 발언과 금리 동결 전망 등 정책 이슈가 주요 변동 요인으로 작용했습니다.",
      "timeseries_insights": {
        "key_indicators": [
          {
            "label": "최고가",
            "value": 99.968,
            "date": "2025-07-31",
            "unit": "Index",
            "sources": [
              "우선 활용 소스"
            ]
          },
          {
            "label": "최저가",
            "value": 96.633,
            "date": "2025-09-16",
            "unit": "Index",
            "sources": [
              "우선 활용 소스"
            ]
          },
          {
            "label": "평균값",
            "value": 98.123,
            "date": null,
            "unit": "Index",
            "sources": [
              "우선 활용 소스"
            ]
          },
          {
            "label": "최신값",
            "value": 99.804,
            "date": "2025-10-31",
            "unit": "Index",
            "sources": [
              "우선 활용 소스"
            ]
          }
        ],
        "timeline_highlights": {
          "columns": [
            {
              "key": "date",
              "label": "날짜",
              "type": "date",
              "unit": null
            },
            {
              "key": "value",
              "label": "지수 값",
              "type": "number",
              "unit": "Index"
            },
            {
              "key": "event",
              "label": "주요 이벤트/원인",
              "type": "string",
              "unit": null
            }
          ],
          "rows": [
            {
              "date": "2025-07-31",
              "value": 99.968,
              "event": "최고가 기록",
              "sources": [
                "우선 활용 소스"
              ]
            },
            {
              "date": "2025-09-16",
              "value": 96.633,
              "event": "최저가 기록",
              "sources": [
                "우선 활용 소스"
              ]
            }
          ]
        },
        "charts": [
          {
            "order": 1,
            "legend": "DXY",
            "date": [
              "2025-07-28",
              "2025-07-29",
              "2025-07-30",
              "2025-07-31",
              "2025-08-01",
              "2025-08-04",
              "2025-08-05",
              "2025-08-06",
              "2025-08-07",
              "2025-08-08",
              "2025-08-11",
              "2025-08-12",
              "2025-08-13",
              "2025-08-14",
              "2025-08-15",
              "2025-08-18",
              "2025-08-19",
              "2025-08-20",
              "2025-08-21",
              "2025-08-22",
              "2025-08-25",
              "2025-08-26",
              "2025-08-27",
              "2025-08-28",
              "2025-08-29",
              "2025-09-01",
              "2025-09-02",
              "2025-09-03",
              "2025-09-04",
              "2025-09-05",
              "2025-09-08",
              "2025-09-09",
              "2025-09-10",
              "2025-09-11",
              "2025-09-12",
              "2025-09-15",
              "2025-09-16",
              "2025-09-17",
              "2025-09-18",
              "2025-09-19",
              "2025-09-22",
              "2025-09-23",
              "2025-09-24",
              "2025-09-25",
              "2025-09-26",
              "2025-09-29",
              "2025-09-30",
              "2025-10-01",
              "2025-10-02",
              "2025-10-03",
              "2025-10-06",
              "2025-10-07",
              "2025-10-08",
              "2025-10-09",
              "2025-10-10",
              "2025-10-13",
              "2025-10-14",
              "2025-10-15",
              "2025-10-16",
              "2025-10-17",
              "2025-10-20",
              "2025-10-21",
              "2025-10-22",
              "2025-10-23",
              "2025-10-24",
              "2025-10-27",
              "2025-10-28",
              "2025-10-29",
              "2025-10-30",
              "2025-10-31"
            ],
            "value": [
              98.634,
              98.886,
              99.815,
              99.968,
              99.141,
              98.784,
              98.782,
              98.177,
              98.4,
              98.18,
              98.52,
              98.097,
              97.84,
              98.254,
              97.852,
              98.167,
              98.265,
              98.218,
              98.619,
              97.716,
              98.43,
              98.225,
              98.232,
              97.813,
              97.771,
              97.771,
              98.397,
              98.142,
              98.347,
              97.768,
              97.454,
              97.788,
              97.78,
              97.531,
              97.55,
              97.302,
              96.633,
              96.873,
              97.348,
              97.644,
              97.341,
              97.264,
              97.873,
              98.553,
              98.152,
              97.906,
              97.775,
              97.706,
              97.846,
              97.723,
              98.108,
              98.578,
              98.915,
              99.538,
              98.978,
              99.269,
              99.047,
              98.793,
              98.336,
              98.433,
              98.586,
              98.934,
              98.897,
              98.936,
              98.952,
              98.783,
              98.667,
              99.22,
              99.526,
              99.804
            ]
          }
        ],
        "requested_range": "2025-07-28 ~ 2026-01-27",
        "available_range": "2025-07-28 ~ 2025-10-31",
        "primary_value_field": "price_index",
        "unit": "Index"
      }
    },
    "evidence": {
      "rdb": {
        "sql_queries": [
          "SELECT date AS 'as_of_date', pi AS 'price_index'\nFROM midb.tif_equityindicesr\nWHERE code = 'NDXYSPT'\n  AND date >= '2025-07-28'\n  AND date < '2026-01-28'\nORDER BY date ASC;"
        ],
        "used_tables": [
          "tif_equityindicesr: 글로벌 주가지수 & DXY – 선진국 (S&P 500, S&P/ASX All Ordinaries Gold, Nasdaq 100, EURO STOXX 50, DAX Xetra, FTSE 100), 신흥국 (Brazil Bovespa, Shanghai Composite/Shenzhen CSI 300, KOSPI, Nikkei 225), 종합 (MSCI ACWI USD, MSCI EM GBP)"
        ],
        "product_numbers": [
          70008
        ],
        "charts": []
      },
      "vdb": [
        {
          "source": "Hong Leong Investment Bank Bhd",
          "title": "Traders_Brief_0620",
          "gds_no": 70008,
          "gds_data_dstg_id": "116049757"
        },
        {
          "source": "Axis Capital Limited",
          "title": "Eyecatchers Today – 20 June 2025",
          "gds_no": 70008,
          "gds_data_dstg_id": "116049632"
        },
        {
          "source": "Ichiyoshi Research Institute INC.",
          "title": "ＡＩＲＭＡＮ（6364、東証プライム）:今期業績は踊り場となろうが、メンテナンス事業の強化など収益性の向上に期待したい",
          "gds_no": 70008,
          "gds_data_dstg_id": "116049575"
        }
      ],
      "web": [
        {
          "url": "https://m.blog.naver.com/borninaug/223833013443",
          "source_nm": "달러 인덱스(DXY), 환율 움직임의 핵심을 알면 돈의 흐름이 ..."
        },
        {
          "url": "https://www.wayful.com/p/usdx-ice-dx-us-dollar-index-futures.html",
          "source_nm": "오늘 미국 달러 지수 차트 US Dollar Index (USDX, DXY, DX ..."
        },
        {
          "url": "https://yellow.kr/financeUSDX.jsp",
          "source_nm": "달러인덱스 (Dollar Index)"
        },
        {
          "url": "https://ko.tradingeconomics.com/united-states/currency",
          "source_nm": "미국 달러 | 1971-2026 데이터 | 2027-2028 예상"
        },
        {
          "url": "https://contents.premium.naver.com/protact/economy/contents/250530115544800bb",
          "source_nm": "달러 인덱스 지수와 미국, 한국증시와의 상관관계가 있을까?"
        },
        {
          "url": "https://www.joongang.co.kr/article/25286991",
          "source_nm": "주식은 \"해리스\" 달러는 \"트럼프\"…이런 '족집게' 지표도 있다 ..."
        },
        {
          "url": "https://www.instagram.com/p/DSHMJk8DATh/",
          "source_nm": "오늘 글로벌 시장은 미국 연방준비제도가 널리 예상되었던 금리 ..."
        },
        {
          "url": "https://kr.tradingview.com/symbols/TVC-DXY/",
          "source_nm": "DXY — 미국 달러 인덱스 차트 - 트레이딩뷰 - TradingView"
        },
        {
          "url": "https://www.babypips.com/ko/learn/forex/dollar-index-dxy-key-gauge-global-liquidity",
          "source_nm": "달러 인덱스(DXY): 글로벌 유동성의 주요 지표"
        },
        {
          "url": "https://www.etoday.co.kr/news/view/2550163",
          "source_nm": "\"트럼프 발언 등 충격\" 美 달러 지수 95 '뚝'⋯2022년 2월 이후 ..."
        },
        {
          "url": "https://kr.investing.com/indices/usdollar-opinion",
          "source_nm": "US Dollar Index 분석 및 의견"
        },
        {
          "url": "https://kr.investing.com/currencies/us-dollar-index",
          "source_nm": "미국 달러 지수"
        },
        {
          "url": "https://m.fastbull.com/ko/institution-article/%EB%AF%B8%EA%B5%AD-%EB%8B%AC%EB%9F%AC-%EC%A7%80%EC%88%98dxy-20252026%EB%85%84-%EC%A0%84%EB%A7%9D-4362584_5",
          "source_nm": "미국 달러 지수(DXY): 2025~2026년 전망"
        },
        {
          "url": "https://kr.tradingview.com/symbols/ICEUS-DXY/ideas/page-26/?sort=recent&video=yes",
          "source_nm": "26 쪽 | U.S. Dollar Currency Index 아이디어 — ICEUS:DXY"
        },
        {
          "url": "https://www.quarterback.co.kr/post/article-pension-0501/",
          "source_nm": "달러 인덱스란 무엇일까요?"
        },
        {
          "url": "https://www.reddit.com/r/CryptoCurrency/comments/10zvamg/the_crazy_correlation_between_btc_and_dxy_dollar/?tl=ko",
          "source_nm": "BTC랑 DXY(달러 인덱스) 사이의 미친 상관관계가 이전 불마켓 ..."
        },
        {
          "url": "https://kr.tradingview.com/symbols/TVC-DXY/ideas/?sort=recent&video=yes",
          "source_nm": "미국 달러 인덱스 아이디어 — TVC:DXY - 트레이딩뷰"
        },
        {
          "url": "https://www.instagram.com/p/DTwZSwGkmuL/",
          "source_nm": "미국환율 & 달러인덱스"
        },
        {
          "url": "https://www.instagram.com/reel/DSpKW2skgj_/",
          "source_nm": "요즘 환율과 물가, 왜 이렇게 계속 오르는 걸까요? 🤔 그 배경엔 ..."
        },
        {
          "url": "https://www.gpters.org/llm-service/post/migug-jusig-jisu-gagdogi-caesbos-mandeulgi-gems-UOl8gcrvUiZHyFp",
          "source_nm": "미국 주식 지수 각도기 챗봇 만들기(GEMS)"
        }
      ]
    },
    "usage": {
      "prompt_tokens": 49603,
      "completion_tokens": 3497,
      "total_tokens": 53100,
      "prompt_tokens_details": null,
      "completion_tokens_details": null
    }
  },
  "metadata": {
    "run_id": "e470a1c3-49b8-46f9-bff3-3e473569ed2f",
    "feedback_tokens": []
  }
}
```
[stream호출]
```
event: metadata
data: {"run_id": "a0545d9c-b995-4e59-b7f5-29d75f61a517"}

event: data
data: {"state":"progress","data":"message","node":"rewrite_query","value":"Rewriting your query for clarity","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"rewrite_query","value":"Finished rewriting your query for clarity","type":"node_end","latency_ms":4989}

event: data
data: {"state":"progress","data":"message","node":"classify_intent","value":"Clarifying what you’re aiming to explore","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"classify_intent","value":"Finished clarifying what you’re aiming to explore","type":"node_end","latency_ms":2474}

event: data
data: {"state":"progress","data":"message","node":"plan","value":"Shaping the optimal plan for your question","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"plan","value":"Finished shaping the optimal plan for your question","type":"node_end","latency_ms":0}

event: data
data: {"state":"progress","data":"message","node":"search","value":"Gathering the key data points","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"search_rdb","value":"Retrieving structured market data","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"search_web","value":"Checking recent news and market events","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"search_vdb","value":"Looking through related reports and documents","type":"node_start"}

: ping - 2026-01-28 01:45:07.972394

event: data
data: {"state":"progress","data":"message","node":"search_vdb","value":"Finished looking through related reports and documents","type":"node_end","latency_ms":11518}

event: data
data: {"state":"progress","data":"message","node":"search_rdb","value":"Finished retrieving structured market data","type":"node_end","latency_ms":17336}

event: data
data: {"state":"progress","data":"message","node":"search_web","value":"Finished checking recent news and market events","type":"node_end","latency_ms":21861}

event: data
data: {"state":"progress","data":"message","node":"search","value":"Finished gathering the key data points","type":"node_end","latency_ms":21897}

: ping - 2026-01-28 01:45:56.867153

event: data
data: {"state":"progress","data":"message","node":"analysis","value":"Reviewing the data to uncover insights","type":"node_start"}

event: data
data: {"state":"progress","data":"message","node":"analysis","value":"Finished reviewing the data to uncover insights","type":"node_end","latency_ms":34476}

event: data
data: {"state":"complete","data":"message","node":"analysis","value":"2025-07-28~2025-10-31 기간 달러지수(DXY)는 98.6340에서 99.8040pts로 +1.19% 상승했습니다. 9월 중순 단기 약세(96.6330) 이후 10월 말까지 강세로 전환되었으며, 변동성은 낮은 편입니다. 이후 기간(2025-11~2026-01)은 수치데이터가 없어 확인이 불가합니다.\n\n요청하신 2025-07-28 ~ 2026-01-27 기간의 달러지수(DXY) 가격 흐름에 대해 분석드리겠습니다.\n\n---\n\n**1. 기간 안내**\n\n- 요청하신 기간(requested_range): 2025-07-28 ~ 2026-01-27\n- 실제 수치데이터 제공 기간(available_range): 2025-07-28 ~ 2025-10-31\n- 현재 수치데이터는 2025-10-31까지만 제공되고 있습니다. 이후 기간(2025-11~2026-01)은 수치로 확인할 수 없습니다.\n\n---\n\n**2. 시계열 추세 분석**\n\n- 최초값(2025-07-28): 98.6340 pts\n- 최종값(2025-10-31): 99.8040 pts\n- 전체 변화율: +1.19% ((99.8040 - 98.6340) / 98.6340 * 100, 소수점 둘째자리 반올림)\n\n- 일간 변동성(최대 절대 변동률): 약 +1.98% (2025-07-29~07-30, 98.8860→99.8150)\n  - 변동성 분류: 낮음 (max_abs_daily_change_pct < 1% 기준, 단 1.98% 구간이 있으나 대부분 1% 미만)\n\n- 최고치: 99.9680 pts (2025-07-31)\n- 최저치: 96.6330 pts (2025-09-16)\n\n---\n\n**3. 주요 변곡점 및 특이 구간**\n\n| 날짜         | DXY 지수 | 특징/비고           |\n|--------------|----------|---------------------|\n| 2025-07-31   | 99.9680  | 단기 최고치         |\n| 2025-09-16   | 96.6330  | 단기 최저치         |\n| 2025-09-16~09-25 | 96.6330→98.5530 | 1주일간 +1.99pts 반등 |\n| 2025-10-09   | 99.5380  | 10월 초 강세        |\n| 2025-10-31   | 99.8040  | 기간 내 최종치      |\n\n---\n\n**4. 추세 요약**\n\n- 7월 말~8월 초: 98~99pt대에서 등락, 7월 말 단기 고점(99.9680) 이후 8월 중순까지 점진적 하락\n- 8월~9월 중순: 97pt대까지 하락, 9월 16일 최저치(96.6330) 기록\n- 9월 중순~10월 말: 반등세, 99pt대 회복 및 10월 말까지 강세 유지\n\n---\n\n**5. 해석 및 시사점(웹검색 근거, 2025-07~10월 기준)**\n\n- 해당 기간(2025년 하반기)은 DXY가 97~99pt대에서 등락하며, 9월 중순 일시적 약세(96.6330) 이후 반등세가 뚜렷하게 나타났습니다.\n- 웹검색에 따르면, 달러 인덱스가 100 이하일 때는 위험자산 선호(리스크 온) 환경으로 해석되며, 글로벌 자금이 주식 등으로 유입되는 경향이 있습니다.\n- 2025년 하반기 미국 연준의 금리 동결 전망, 재정적자 확대, 트럼프 대통령의 약달러 용인 발언 등이 달러 약세에 영향을 준 것으로 보입니다(2026-01-28 기사 기준).\n- DXY가 97pt대까지 하락한 9월 중순은 원화 강세, 원/달러 환율 하락(1430~1440원대)과 동행하는 모습이 관찰되었습니다.\n- 10월 이후 DXY가 반등하며 99pt대에 재진입한 것은 글로벌 불확실성, 미국 국채 수요 증가, 안전자산 선호 심리와 연관될 수 있습니다.\n\n---\n\n**6. 표로 정리**\n\n| 구간         | 최초값   | 최종값   | 변화율   | 특징/비고           |\n|--------------|----------|----------|----------|---------------------|\n| 2025-07-28~08-15 | 98.6340 | 97.8520 | -0.79%   | 점진적 하락         |\n| 2025-08-16~09-16 | 98.1670 | 96.6330 | -1.56%   | 약세, 최저치 기록   |\n| 2025-09-17~10-31 | 96.8730 | 99.8040 | +3.03%   | 반등, 강세 전환     |\n\n---\n\n**7. 요약**\n\n- 2025-07-28~2025-10-31 기간 DXY는 98.6340→99.8040pts로 +1.19% 상승했습니다.\n- 9월 중순 단기 약세(96.6330) 이후 10월 말까지 강세로 전환되었습니다.\n- 변동성은 낮은 편이며, 주요 변곡점은 9월 중순 최저치와 10월 말 고점입니다.\n- 이후 기간(2025-11~2026-01)은 수치데이터가 없어 확인 불가합니다.","segment":{"sources":{"rdb":{"sql_queries":["SELECT date AS 'as_of_date', pi AS 'price_index'\nFROM midb.tif_equityindicesr\nWHERE code = 'NDXYSPT' \n  AND date >= '2025-07-28' \n  AND date < '2026-01-28'\nORDER BY date ASC;"],"used_tables":["tif_equityindicesr: 글로벌 주가지수 & DXY – 선진국 (S&P 500, S&P/ASX All Ordinaries Gold, Nasdaq 100, EURO STOXX 50, DAX Xetra, FTSE 100), 신흥국 (Brazil Bovespa, Shanghai Composite/Shenzhen CSI 300, KOSPI, Nikkei 225), 종합 (MSCI ACWI USD, MSCI EM GBP)"],"product_numbers":[70008]},"vdb":[{"source":"Hong Leong Investment Bank Bhd","title":"Traders_Brief_0620","gds_no":70008,"gds_data_dstg_id":"116049757"},{"source":"Axis Capital Limited","title":"Eyecatchers Today – 20 June 2025","gds_no":70008,"gds_data_dstg_id":"116049632"},{"source":"Ichiyoshi Research Institute INC.","title":"ＡＩＲＭＡＮ（6364、東証プライム）:今期業績は踊り場となろうが、メンテナンス事業の強化など収益性の向上に期待したい","gds_no":70008,"gds_data_dstg_id":"116049575"}],"web":[{"url":"https://m.blog.naver.com/borninaug/223833013443","source_nm":"달러 인덱스(DXY), 환율 움직임의 핵심을 알면 돈의 흐름이 ..."},{"url":"https://www.wayful.com/p/usdx-ice-dx-us-dollar-index-futures.html","source_nm":"오늘 미국 달러 지수 차트 US Dollar Index (USDX, DXY, DX ..."},{"url":"https://yellow.kr/financeUSDX.jsp","source_nm":"달러인덱스 (Dollar Index)"},{"url":"https://ko.tradingeconomics.com/united-states/currency","source_nm":"미국 달러 | 1971-2026 데이터 | 2027-2028 예상"},{"url":"https://contents.premium.naver.com/protact/economy/contents/250530115544800bb","source_nm":"달러 인덱스 지수와 미국, 한국증시와의 상관관계가 있을까?"},{"url":"https://www.joongang.co.kr/article/25286991","source_nm":"주식은 \"해리스\" 달러는 \"트럼프\"…이런 '족집게' 지표도 있다 ..."},{"url":"https://www.instagram.com/p/DSHMJk8DATh/","source_nm":"오늘 글로벌 시장은 미국 연방준비제도가 널리 예상되었던 금리 ..."},{"url":"https://kr.tradingview.com/symbols/TVC-DXY/","source_nm":"DXY — 미국 달러 인덱스 차트 - 트레이딩뷰 - TradingView"},{"url":"https://www.babypips.com/ko/learn/forex/dollar-index-dxy-key-gauge-global-liquidity","source_nm":"달러 인덱스(DXY): 글로벌 유동성의 주요 지표"},{"url":"https://www.etoday.co.kr/news/view/2550163","source_nm":"\"트럼프 발언 등 충격\" 美 달러 지수 95 '뚝'⋯2022년 2월 이후 ..."},{"url":"https://kr.investing.com/indices/usdollar-opinion","source_nm":"US Dollar Index 분석 및 의견"},{"url":"https://kr.investing.com/currencies/us-dollar-index","source_nm":"미국 달러 지수"},{"url":"https://m.fastbull.com/ko/institution-article/%EB%AF%B8%EA%B5%AD-%EB%8B%AC%EB%9F%AC-%EC%A7%80%EC%88%98dxy-20252026%EB%85%84-%EC%A0%84%EB%A7%9D-4362584_5","source_nm":"미국 달러 지수(DXY): 2025~2026년 전망"},{"url":"https://kr.tradingview.com/symbols/ICEUS-DXY/ideas/page-26/?sort=recent&video=yes","source_nm":"26 쪽 | U.S. Dollar Currency Index 아이디어 — ICEUS:DXY"},{"url":"https://www.quarterback.co.kr/post/article-pension-0501/","source_nm":"달러 인덱스란 무엇일까요?"},{"url":"https://www.reddit.com/r/CryptoCurrency/comments/10zvamg/the_crazy_correlation_between_btc_and_dxy_dollar/?tl=ko","source_nm":"BTC랑 DXY(달러 인덱스) 사이의 미친 상관관계가 이전 불마켓 ..."},{"url":"https://kr.tradingview.com/symbols/TVC-DXY/ideas/?sort=recent&video=yes","source_nm":"미국 달러 인덱스 아이디어 — TVC:DXY - 트레이딩뷰"},{"url":"https://www.instagram.com/p/DTwZSwGkmuL/","source_nm":"미국환율 & 달러인덱스"},{"url":"https://www.instagram.com/reel/DSpKW2skgj_/","source_nm":"요즘 환율과 물가, 왜 이렇게 계속 오르는 걸까요? 🤔 그 배경엔 ..."},{"url":"https://www.gpters.org/llm-service/post/migug-jusig-jisu-gagdogi-caesbos-mandeulgi-gems-UOl8gcrvUiZHyFp","source_nm":"미국 주식 지수 각도기 챗봇 만들기(GEMS)"}]},"timeseries_insights":{"key_indicators":[{"label":"최고가","value":99.968,"date":"2025-07-31","unit":"pts","sources":["우선 활용 소스"]},{"label":"최저가","value":96.633,"date":"2025-09-16","unit":"pts","sources":["우선 활용 소스"]},{"label":"평균값","value":98.123,"unit":"pts","sources":["우선 활용 소스"]},{"label":"최신값","value":99.804,"date":"2025-10-31","unit":"pts","sources":["우선 활용 소스"]}],"timeline_highlights":{"columns":[{"key":"date","label":"날짜","type":"date"},{"key":"value","label":"지수 값","type":"number","unit":"pts"},{"key":"event","label":"주요 이벤트/원인","type":"string"}],"rows":[{"date":"2025-07-31","value":99.968,"event":"최고가 기록","sources":["우선 활용 소스"]},{"date":"2025-09-16","value":96.633,"event":"최저가 기록","sources":["우선 활용 소스"]}]},"charts":[{"order":1,"legend":"DXY","date":["2025-07-28","2025-07-29","2025-07-30","2025-07-31","2025-08-01","2025-08-04","2025-08-05","2025-08-06","2025-08-07","2025-08-08","2025-08-11","2025-08-12","2025-08-13","2025-08-14","2025-08-15","2025-08-18","2025-08-19","2025-08-20","2025-08-21","2025-08-22","2025-08-25","2025-08-26","2025-08-27","2025-08-28","2025-08-29","2025-09-01","2025-09-02","2025-09-03","2025-09-04","2025-09-05","2025-09-08","2025-09-09","2025-09-10","2025-09-11","2025-09-12","2025-09-15","2025-09-16","2025-09-17","2025-09-18","2025-09-19","2025-09-22","2025-09-23","2025-09-24","2025-09-25","2025-09-26","2025-09-29","2025-09-30","2025-10-01","2025-10-02","2025-10-03","2025-10-06","2025-10-07","2025-10-08","2025-10-09","2025-10-10","2025-10-13","2025-10-14","2025-10-15","2025-10-16","2025-10-17","2025-10-20","2025-10-21","2025-10-22","2025-10-23","2025-10-24","2025-10-27","2025-10-28","2025-10-29","2025-10-30","2025-10-31"],"value":[98.634,98.886,99.815,99.968,99.141,98.784,98.782,98.177,98.4,98.18,98.52,98.097,97.84,98.254,97.852,98.167,98.265,98.218,98.619,97.716,98.43,98.225,98.232,97.813,97.771,97.771,98.397,98.142,98.347,97.768,97.454,97.788,97.78,97.531,97.55,97.302,96.633,96.873,97.348,97.644,97.341,97.264,97.873,98.553,98.152,97.906,97.775,97.706,97.846,97.723,98.108,98.578,98.915,99.538,98.978,99.269,99.047,98.793,98.336,98.433,98.586,98.934,98.897,98.936,98.952,98.783,98.667,99.22,99.526,99.804]}],"requested_range":"2025-07-28 ~ 2026-01-27","available_range":"2025-07-28 ~ 2025-10-31","primary_value_field":"price_index","unit":"pts"},"suggestions":["2025-07~2025-10 기간 동안 DXY 변동에 영향을 준 주요 경제 이벤트는 무엇이었나요?","같은 기간 동안 원/달러 환율이나 주요 주가지수(S&P500, 코스피)와 DXY의 상관관계를 비교해볼 수 있을까요?","현재 수치데이터가 2025-10-31까지만 제공되는데, 이후 2026-01까지의 DXY 흐름을 확인하려면 어떤 추가 소스를 활용해야 할까요?"],"usage":{"prompt_tokens":49922,"completion_tokens":4117,"total_tokens":54039}},"latency_ms":63901}

event: end

```

**스키마 구조**

```
MariAgentOutput
├── answer                         # 분석 결과 객체
│   ├── content                    # 검색 결과 기반 상세 분석 텍스트
│   ├── analysis_summary           # 핵심 인사이트 (2-3문장)
│   └── suggested_questions        # 추천 질문 목록 (배열)
│
├── evidence                       # 검색 결과 출처 및 근거
│   ├── rdb                        # RDB 검색 결과 객체
│   │   ├── sql_queries            # 실행된 SQL 쿼리 목록
│   │   ├── used_tables            # 사용된 테이블 목록
│   │   ├── product_numbers        # 조회된 상품 번호
│   │   └── charts                 # 생성된 차트 정보
│   │
│   ├── vdb                        # 벡터DB 검색 결과 (배열)
│   │   └── [n]                    # 리포지토리별 검색 결과
│   │       ├── repo_id            # 벡터DB 리포지토리 ID (UUID)
│   │       ├── repo_name          # 리포지토리 이름 (e.g., "경제 리포트")
│   │       └── documents          # 검색된 문서 배열
│   │           └── [n]            # 개별 문서 정보
│   │               ├── doc_id     # 문서 고유 ID
│   │               ├── title      # 문서 제목
│   │               ├── content    # 문서 내용 (발췌)
│   │               ├── similarity_score  # 유사도 점수 (0~1)
│   │               └── source     # 문서 출처
│   │
│   └── web                        # 웹 검색 결과 (배열)
│       └── [n]                    # 검색 결과 출처
│           ├── url                # 웹페이지 URL
│           └── source_nm          # 출처명 (e.g., "Oil Market News")
│
└── usage                          # LLM 토큰 사용량 통계
    ├── prompt_tokens              # 프롬프트 토큰 수
    ├── completion_tokens          # 완성 토큰 수
    └── total_tokens               # 총 토큰 수
```


### Docker 환경 변수
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `APP__HOST` | `0.0.0.0` | 호스트 주소 |
| `APP__PORT` | `18080` | 포트 번호 |
| `LOG_LEVEL` | `info` | 로그 레벨 |
| `TIMEOUT` | `600` | 요청 타임아웃 (초) |
| `GRACEFUL_TIMEOUT` | `600` | 종료 대기 시간 (초) |

### graph.yaml
```yaml
package_directory: .
graph_path: ./apps/agents/mi_agent/flows/mari_agent_runnable.py:runnable_graph
env_file: envs/skmip_mi_agent/env.txt
requirements_file: ./requirements.txt
```


## 8. 테스트

### API 테스트
```bash
# 브라우저에서 Swagger UI 접속
http://localhost:3002/api/v1/docs

# POST /invoke or /stream 실행
```

### 단위 테스트
```bash
# pytest 실행
pytest tests/

# 비동기 테스트
pytest tests/ -v --asyncio-mode=auto
```

***
## 9. 성능 최적화

### 1) 병렬 처리
- **RDB/VDB/Web 검색 병렬 실행**: `search_node`에서 `SearchSupervisor` 사용
- **동시성 제한**: `llm_concurrency`, `search_exec_fanout_deadline_sec` 환경 변수로 제어

### 2) 타임아웃 관리
| 설정 | 기본값 | 용도 |
|------|--------|------|
| `llm_timeout_sec` | 90초 | LLM 호출 타임아웃 |
| `mcp_client_timeout` | 30초 | MCP 클라이언트 타임아웃 |
| `search_exec_fanout_deadline_sec` | 240초 | 검색 실행 제한 시간 |

### 3) 메모리 관리
- `contextvars` 기반 요청별 격리 → 메모리 누수 방지
- MCP 클라이언트 풀 크기로 리소스 제어 (`mcp_pool_size`)

### 4) 최적화 체크리스트
```python
# ✅ 비동기 작업 확인
async def node(...) -> State:  # async 필수
    result = await some_async_func()
    
# ✅ @stream_step 사용 (진행상황 실시간 전달)
@stream_step(step_key="search")
async def search_node(...) -> State:
    
# ✅ RuntimeContext 사용 (리소스 재사용)
runtime = RuntimeContext.get()
mcp_pool = runtime.mcp_pool

# ✅ 토큰 사용량 추적 (요청 비용 파악)
accumulate_usage(response.usage)
```

***
## 10. 트러블슈팅

### 문제 1: LLM 타임아웃 에러
**증상**: `TimeoutError: LLM request timed out`

**해결책**
```bash
# 1. 타임아웃 값 증가
export llm_timeout_sec=120

# 2. LLM 동시성 감소 (과부하 방지)
export llm_concurrency=3

# 3. 프롬프트 길이 확인 (너무 길면 처리 시간 증가)
# → 검색 결과 수 줄이기, 컨텍스트 최소화
```

### 문제 2: MCP 클라이언트 풀 고갈
**증상**: `Queue empty: No available MCP clients`

**해결책**
```bash
# 1. 풀 크기 증가
export mcp_pool_size=20

# 2. 동시 요청 감소
export llm_concurrency=3

# 3. 풀 타임아웃 확인
export mcp_client_timeout=30

# 4. 로그 확인
grep "MCP.*pool" logs/app.log
```

### 문제 3: 스트리밍 이벤트 누락
**증상**: SSE 스트림이 불완전하거나 지연

**해결책**
```python
# 1. @stream_step 데코레이터 확인
@stream_step(step_key="node_name")  # ← 필수
async def my_node(state: State) -> State:

# 2. 스트리밍 모드 확인 (custom + values)
# mari_agent_runnable.py의 _normalize_stream_modes() 확인

# 3. 네트워크 지연 (클라이언트 측)
# → 타임아웃 값 증가, 재연결 로직 추가
```

### 문제 4: SQL 생성 실패
**증상**: RDB 검색에서 SQL 생성 안 됨

**해결책**
```bash
# 1. 메타데이터 확인
repo_id_rdb_metadata가 올바르게 설정되어 있는지 확인

# 2. 테이블 선택 로그 확인
grep "select_candidate_tables" logs/app.log

# 3. 프롬프트 최적화
# rdb_search_select_target_table.py, rdb_search_nl_to_sql.py 확인

# 4. 질의 재작성 확인 (user_query → rewritten_query)
rewritten_query가 의도를 정확하게 반영하는지 확인
```

### 문제 5: 메모리 누수
**증상**: 시간이 지남에 따라 메모리 사용량 증가

**해결책**
```python
# 1. contextvars 격리 확인 (요청별 독립적)
from apps.common.runtime.usage_context import reset_usage
# reset_usage()는 요청 시작 시 호출되는가?

# 2. 순환 참조 확인
# State 객체가 이전 요청 참조 안 하는지 확인

# 3. 메모리 프로파일링
python -m memory_profiler app.py
```

***
## 11. 개발자 가이드

### 새로운 노드 추가하기

**1단계: 노드 함수 작성**
```python
# apps/agents/mi_agent/nodes/my_node.py
from apps.common.streaming.decorators import stream_step
from apps.agents.mi_agent.state.state import MariAgentState

@stream_step(step_key="my_step")
async def my_node(state: MariAgentState) -> MariAgentState:
    """새로운 노드 구현"""
    # 기존 상태 읽기
    query = state.user_query
    
    # 비즈니스 로직
    result = await some_process(query)
    
    # 상태 업데이트
    state.my_result = result
    return state
```

**2단계: Graph에 노드 등록**
```python
# apps/agents/mi_agent/flows/mari_agent_graph.py
from apps.agents.mi_agent.nodes.my_node import my_node

def build_mi_agent() -> Runnable:
    graph = StateGraph(state_schema=MariAgentState)
    
    # ... 기존 노드들 ...
    
    # 새 노드 추가
    graph.add_node("my_node", my_node)
    
    # 엣지 연결
    graph.add_edge("search", "my_node")
    graph.add_edge("my_node", "analysis")
    
    return graph.compile()
```

**3단계: State 스키마 업데이트**
```python
# apps/agents/mi_agent/state/state.py
class MariAgentState(BaseModel):
    # ... 기존 필드 ...
    my_result: str | None = None  # 새 필드 추가
```

### 새로운 서브그래프 추가하기

**예: new_search 서브그래프**

**1단계: 서브그래프 구조 생성**
```
subgraphs/
└── new_search/
    ├── __init__.py
    ├── state.py                    # 서브그래프 State
    ├── schemas.py                  # 입출력 스키마
    ├── subgraph_builder.py         # 서브그래프 구성
    ├── subgraph_adapter.py         # 어댑터 (State 변환)
    └── stages/
        └── execute/
            └── search_node.py      # 실행 노드
```

**2단계: 서브그래프 구성 (subgraph_builder.py)**
```python
from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import END, START, StateGraph
from apps.common.streaming.decorators import stream_step

def build_new_search_subgraph() -> Runnable:
    graph = StateGraph(state_schema=NewSearchState)
    graph.add_node("search_node", search_node)
    graph.add_edge(START, "search_node")
    graph.add_edge("search_node", END)
    return graph.compile()

_subgraph = build_new_search_subgraph()

@stream_step(step_key="search_new")
async def run_new_search(agent_state: MariAgentState) -> NewSearchOutput:
    out = await (RunnableLambda(to_state) | _subgraph | RunnableLambda(to_output)).ainvoke(agent_state)
    return out
```

**3단계: search_node에서 서브그래프 호출**
```python
# apps/agents/mi_agent/nodes/search.py
async def search_node(state: MariAgentState) -> MariAgentState:
    supervisor = SearchSupervisor(state)
    
    # 새 검색 소스 추가
    if "new_search" in state.search_sources:
        new_results = await run_new_search(state)
        state.search_results.new = new_results
    
    return state
```

### Runnable 이해하기

**Runnable이란?**
- LangChain의 표준 실행 인터페이스
- `invoke()`, `ainvoke()`, `stream()`, `astream()` 메서드 제공
- 체이닝 가능 (`|` 연산자)

**사용 예시**
```python
# 1. Graph도 Runnable
graph = build_mi_agent()  # → Runnable
result = await graph.ainvoke(input)

# 2. Chain도 Runnable
chain = prompt | llm
result = await chain.ainvoke({"query": "..."})

# 3. 체이닝
pipeline = chain1 | chain2 | chain3
result = await pipeline.ainvoke(input)

# 4. Runnable 래퍼
class MyRunnable(Runnable):
    def __init__(self, inner: Runnable):
        self._inner = inner
    
    async def ainvoke(self, input):
        # 전처리
        processed = preprocess(input)
        
        # 내부 실행
        result = await self._inner.ainvoke(processed)
        
        # 후처리
        return postprocess(result)
```

### 테스트 작성하기

**단위 테스트 (노드)**
```python
# tests/agents/mi_agent/nodes/test_my_node.py
import pytest
from apps.agents.mi_agent.nodes.my_node import my_node
from apps.agents.mi_agent.state.state import MariAgentState

@pytest.mark.asyncio
async def test_my_node():
    state = MariAgentState(
        user_query="테스트 질의",
        company_code="2014",
    )
    
    result = await my_node(state)
    
    assert result.my_result is not None
    assert len(result.my_result) > 0
```

**통합 테스트 (Graph)**
```python
# tests/agents/mi_agent/flows/test_graph.py
import pytest
from apps.agents.mi_agent.flows.mari_agent_graph import build_mi_agent
from apps.agents.mi_agent.schemas.mari_agent_input import MariAgentInput

@pytest.mark.asyncio
async def test_full_graph():
    graph = build_mi_agent()
    
    input_data = MariAgentInput(
        user_query="최근 유가 추이를 알려줘",
        company_code="2014",
        search_sources=["web"],
        authorized_product_nums=[70008],
    )
    
    result = await graph.ainvoke(input_data)
    
    assert result.analysis_result is not None
```

* TODO
: 멀티턴 처리


READMe.md파일 작성
그래프 추가: 
brew install graphviz
poetry install --without dev
python -m scripts.export_langgraph_png


+ Search/Retrieval: RDB(Text-to-SQL), VDB(Azure AI Search), Web Search(Tavily)
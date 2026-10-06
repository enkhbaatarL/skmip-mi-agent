---
name: scenario-prompt-vs-platform-compare
description: N개의 MI 이벤트 Markdown 파일로 플랫폼 v4 시나리오 생성(POST /scenario-groups) 결과와 워크숍 가이드(lng_scenario_workshop_guide)의 단계별 프롬프트 실행 결과를 같은 조건에서 비교하고 품질 비교 보고서를 작성한다. 이벤트 INSERT → 플랫폼 생성 API 호출 → DB 결과 확인 → MLflow trace 단계별 input/output 확인 → 워크숍 프롬프트 실행 → 비교 보고서의 6단계를 단계마다 사용자 확인을 받으며 수행하고, 같은 입력으로 N회 반복 실행해 안정성까지 비교할 수 있다. "프롬프트 vs 플랫폼 품질 비교", "실습 프롬프트와 서비스 결과 비교", "고객이 품질 차이를 제기", "워크숍 결과와 플랫폼 결과 비교 보고서", "같은 이벤트로 N번 돌려서 비교" 요청에 사용한다. 워크숍 없이 플랫폼의 프롬프트·코드·모델 변경 전후를 같은 이벤트로 비교해 구조 결함·rubric·안정성·가드레일 기준으로 개선 여부를 판정하는 요청("변경 효과 확인", "개선됐는지 비교", "품질 개선 기준으로 판정")에도 사용한다.
---

# Scenario Prompt vs Platform Compare

같은 이벤트 세트를 (A) 플랫폼 v4 파이프라인과 (B) 워크숍 가이드의 단계별 프롬프트로 각각 실행하고,
단계별 증적을 맞대어 품질 차이와 원인을 보고서로 정리한다.

## 핵심 원칙

- **단계마다 사용자 확인**: 아래 6단계 각각을 시작하기 전에 "무엇을 할지, 무엇이 바뀌는지(DB 쓰기, LLM 비용,
  MLflow 기록)"를 설명하고 승인을 받는다. 승인 없이 다음 단계로 넘어가지 않는다. 사용자가 여러 단계를 한 번에
  승인한 경우에만 이어서 실행한다.
- **조건을 맞춘다**: 두 쪽의 이벤트 목록과 순서, 분석 기준일, Lever catalog를 같게 맞춘다. 맞출 수 없는 조건
  (모델, 입력 범위 등)은 보고서 "조건 차이"에 기록한다.
- **워크숍 실행은 맥락 없는 서브에이전트가 한다**: 플랫폼 결과를 이미 본 세션이 직접 프롬프트를 실행하면 결과가
  오염된다. 이 스킬을 쓴다는 것은 서브에이전트 실행을 요청한 것으로 본다.
- **비밀값은 출력하지 않는다**: DB·MLflow 계정은 `env.txt`/`envs/env.txt`에서 스크립트가 읽는다.
- 모든 산출물은 세션 scratchpad 아래 작업 폴더(`{WORK}`)에 둔다. 저장소에는 쓰지 않는다.

## 시작 전에 확인할 입력

| 항목 | 기본값 | 비고 |
|---|---|---|
| 이벤트 Markdown 폴더 | (필수) | Next-Gen MI 이벤트 상세의 Markdown 다운로드 파일, N개(1~5) |
| 이벤트 순서 | 사용자 지정 | 플랫폼은 순서에 따라 질문 예산이 달라지므로 양쪽에 같은 순서를 쓴다 |
| 반복 횟수 N | 1 | 플랫폼 N회 + 워크숍 N회 |
| 분석 기준일 | 실행일(`today()`) | 플랫폼은 기준일을 API로 바꿀 수 없다. 워크숍도 같은 날짜로 맞춘다 |
| Lever catalog | `platform`(DB v4) | 플랫폼과 맞추는 것이 기본. 과거 실습 재현이 목적이면 `guide`(가이드 템플릿, v2 = DB v0) |
| 워크숍 가이드 | `/Users/a10093/projects/2604_SKGAS/AI_Friday/20260828_실습/lng_scenario_workshop_guide_v4_final.html` | 다른 버전이면 경로 지정 |
| local agent | `http://127.0.0.1:8000` | `curl -s -o /dev/null -w "%{http_code}" .../docs`로 확인 |
| userId | midb에서 최근 그룹을 만든 사용자 | `SELECT request_usr_id … GROUP BY` 로 찾고 사용자에게 확인 |

"v4"라는 이름의 두 의미를 혼동하지 않는다: 가이드 제목의 v4는 **파이프라인(Create 흐름) 버전**이고,
00_input 템플릿의 `Catalog version`은 **Lever catalog 버전**이다(가이드 원문은 v2 = DB `catalog_version='v0'` 세트).

## 스크립트

모두 저장소 루트에서 `poetry run python .claude/skills/scenario-prompt-vs-platform-compare/scripts/<name>.py`로 실행한다.

| 스크립트 | 역할 | 부작용 |
|---|---|---|
| `gen_event_sql.py` | 이벤트 md → INSERT SQL 생성. `--execute` 시 실행하고 새 `mi_event_id` 출력 | `--execute`일 때만 DB 쓰기 |
| `run_platform.py` | `POST /scenario-groups` SSE를 N회 순차 호출, run별 `run.json`·SSE 로그 저장 | 그룹 N개 생성, LLM 비용 |
| `export_group.py` | 그룹 DB 결과를 SELECT로 내보내고 `platform_result.md`, `metrics.json` 생성 | 없음 |
| `fetch_trace.py` | SSE `mlflowTraceId`(= `aip.transaction_id`)로 MLflow trace를 찾아 단계별 프롬프트·응답 정리 | 없음 |
| `build_workshop_workspace.py` | 가이드 `<pre>` 프롬프트 9개 추출, catalog 교체, run별 워크스페이스 생성 | 없음 |
| `aggregate_runs.py` | 플랫폼·워크숍 run들의 구조 지표 집계(`aggregate.md`) | 없음 |
| `run_from_sse_log.py` | 이전에 실행한 플랫폼 run의 SSE 로그로 `run.json`을 다시 만들어 N회 중 하나로 재사용 | 없음 |
| `structural_checks.py` | run 하나의 구조 결함을 자동 집계(`structural.json`): 이중 계산, Interaction 질문 기반 Dimension, 핵심 Fact 누락, Path role·balance, 재시도·오류, 음역·영문 일반어, 중간값 baseline | 없음 (events.json 없으면 DB 읽기) |
| `compare_platform_runs.py` | 두 run 세트(변경 전·후)를 같은 지표로 비교하고 판정 규칙을 적용(`compare_before_after.md`) | 없음 |
| `compare_model_sets.py` | 모델·파라미터별 run 세트 여러 개를 나란히 비교(`--set label=DIR`). trace의 실제 모델을 표시하고 `--price 배포명=입력/출력`(USD/1M)으로 그룹당 비용 계산 | 없음 |

## 실행 모드

| 모드 | 언제 | 단계 |
|---|---|---|
| **A. 플랫폼 대 워크숍 비교** | 품질 차이의 원인을 찾을 때 | 아래 6단계 전체 |
| **B. 플랫폼 변경 전후 비교** | 프롬프트·코드·모델을 바꾼 효과를 확인할 때 (워크숍 실행 없음) | 아래 "모드 B 절차" |
| **C. 모델·파라미터 비교** | 같은 코드로 모델이나 LLM 파라미터만 바꿔 비교할 때 | 아래 "모드 C 절차" |

## 작업 폴더 구조

```
{WORK}/
  events/               # 사용자 이벤트 md 사본(선택)
  insert_events.sql
  platform/run_01..N/   # run.json, create_sse.log, group.json, platform_result.md, metrics.json,
                        # trace.json, trace_by_stage.md, stage_summary.json
  workshop/prompts/     # 가이드 프롬프트 원문
  workshop/run_01..N/workshop_YYYYMMDD/  # 00_input.md ~ 05(06)_*.md
  failed/               # 중단·실패한 run 기록 (비교에서 제외하되 보고서 "조건 차이"에 기록)
  aggregate.md          # N>1
  report_run_01..N.md   # run별 보고서 (N=1이면 이것 하나)
  report_combined_Nruns.md  # N>1 종합 보고서
```

## 비용·시간 기준 (2026-10 실측)

| 항목 | 1회 기준 |
|---|---|
| 플랫폼 생성 | 2~6분, LLM 호출 8~10회 (gpt-5.5) |
| 워크숍 서브에이전트 | 약 11~12분, 서브에이전트 토큰 약 15만~18만 |
| 보고서 | run별 보고서 + 종합 보고서 작성에 상당한 컨텍스트 사용. N이 크면 run별 보고서는 핵심 표 위주로 줄인다 |

## 모델 기록

보고서 "조건 차이"에 양쪽 모델을 반드시 적는다.
- 플랫폼: trace의 `mlflow.llm.model`(예: `skmidev-gpt-5.5-20260424`), 단계별 reasoning effort(`v4_nodes.py`의
  `reasoning_effort_override`, `envs/config.yaml`의 `llm_reasoning_effort`), strict JSON 여부.
  temperature·max token은 코드 인자만 보고 적지 않는다. `apps/connectors/llm/llm_client.py`의
  `_structured_output_request_kwargs`가 실제로 API 요청에 넣는 값만 적는다(2026-10 기준: temperature·max token 미전송
  → 모델 기본값. `invoke_stage_structured_output`의 `temperature=0.0`은 전달되지 않음).
- 워크숍: 서브에이전트 모델(예: Claude Opus). 채점자(이 스킬을 실행하는 모델)도 적고, 워크숍 실행 모델과 같은 계열이면
  편향 가능성을 한계로 적는다.

## 6단계 절차

### 1단계. 이벤트 INSERT

1. `gen_event_sql.py --events-dir … --order "키워드1,키워드2,…" --tag compare_YYYYMMDD --out {WORK}/insert_events.sql`
   (DB 읽기만 함: L2 유형 조회)
2. 같은 제목의 이벤트가 이미 있는지 SELECT로 확인한다. 이미 있으면 재사용할지 물어본다.
3. 사용자에게 보여줄 것: 대상 DB(host:port/db), 이벤트별 L2·occurred_at, 값 매핑 규칙과 가정
   (event_title = one_line_summary = H1, occurred_at 추론 근거, 스냅샷 미생성 → live 이벤트 사용).
4. 승인 후 직접 실행하거나(`--execute`) 사용자가 실행한다. 새 `mi_event_id` 목록을 확보한다.

### 2단계. 플랫폼 생성 API 호출 (N회)

1. `run_platform.py --event-ids … --user-id … --runs N --out-dir {WORK}/platform` 를 `run_in_background`로 실행.
   N회는 순차 실행된다(게이트웨이 부하·타임아웃 방지).
2. 끝나면 run별 group id, 상태, 소요 시간, 재시도(phase·validationCode)를 표로 보고한다.
   `LLM_INVOCATION_ERROR`가 60초 간격이면 게이트웨이 504를 의심하고 4단계에서 확인한다.
3. 진행 중 상태는 SSE 로그(`create_sse.log`) 또는 DB `tmm_mi_scenario_group_operation_m`(status, current_phase)로 본다.
   group id는 다른 사용자의 생성과 섞여 연속되지 않을 수 있으므로 반드시 `run.json`의 `scenarioGroupId`를 쓴다.
4. 이미 실행해 둔 플랫폼 결과를 run_01로 재사용할 때는 `run_from_sse_log.py`로 `run.json`을 만든 뒤 3·4단계를 똑같이 수행한다.
   분석 기준일이 다르면(예: 전날 실행) 보고서 "조건 차이"에 적는다.

### 장애 대응 (2·3·4단계 공통)

- **DB 연결 거부**: `nc -z -G 3 <host> <port>`로 확인한다. env 값이 바뀌지 않았으면 원격 DB 장애로 보고 사용자에게 알린다.
  읽기 전용 작업(MLflow trace 등 DB가 필요 없는 것)만 먼저 진행할 수 있다.
- **run이 `interrupted`로 끝남**("서버 재시작 후 heartbeat가 만료되어 작업을 중단 처리했습니다"): 그 run은 비교에서 빼고
  `failed/`로 옮긴다. 다시 실행하면 그룹이 하나 더 생기므로 **재실행 전에 사용자 승인을 받는다**.
- **MLflow 401**: env 파일의 `MLFLOW_TRACKING_USERNAME/PASSWORD`를 확인한다. trace를 못 찾으면 SSE의 `mlflowTraceId`가
  MLflow trace id가 아니라 `aip.transaction_id`라는 점을 기억한다(`fetch_trace.py`가 검색으로 찾는다).
- **모델이 바뀌지 않음**: `.env`를 바꾼 직후 서버를 재시작하면 바뀌기 전 값으로 뜰 수 있다(2026-10: astra로 바꿨는데
  luna로 3회 실행됨). 서버 프로세스 시작 시각이 `.env` 수정 시각보다 뒤인지 확인하고, **첫 run의 trace `mlflow.llm.model`이
  의도한 배포명인지 확인한 뒤** 나머지 run을 실행한다. 잘못 돌린 run은 버리지 말고 실제 모델 세트로 옮긴다.
- **날짜가 바뀜**: 플랫폼 기준일은 실행일로 고정이다. 이어서 실행하는 run은 새 날짜를 쓰고, 워크숍도 그 run과 같은 날짜로
  맞춘 뒤 run별 기준일을 보고서에 적는다. 선택지 경계(예: "10월 중")가 과거가 되는 날짜를 넘으면 비교를 다시 계획한다.

### 3단계. DB 결과 확인

1. run마다 `export_group.py --group-id … --out-dir {WORK}/platform/run_XX`.
2. 워크숍 구조(Fact → Path → Interaction → 질문 → Dimension/Choice → Scenario)로 요약해 보고한다.
   이 시점의 관찰은 "1차 관찰"로만 쓰고 결론을 내리지 않는다.

### 4단계. MLflow trace 단계별 확인

1. run마다 `fetch_trace.py --transaction-id <run.json transactionId> --group-id … --out-dir …/run_XX`.
   인증 정보는 env 파일의 `MLFLOW_TRACKING_USERNAME/PASSWORD`를 쓴다(401이면 이 값을 확인).
2. `trace_by_stage.md`를 읽고 단계별로 확인한다:
   - Step 1 입력에 무엇이 들어갔고(요약·Fact 후보·catalog), 어떤 Fact가 선택·제외됐는가
   - 재시도가 있으면 실패 원인(검증 메시지, 504 등)과 재시도 후 **내용이 바뀌었는지**
   - Dimension 입력 카드에 무엇이 빠졌는가, 출력 토큰·시간
   - 생성 후 자동 실행된 Additional Dimension trace 결과
3. 정보가 손실된 지점을 `trace_findings.md`로 남기고 보고한다.

### 5단계. 워크숍 프롬프트 실행 (N회)

1. `build_workshop_workspace.py --events-dir … --out-dir {WORK}/workshop --as-of YYYY-MM-DD --runs N --catalog platform`
2. `references/workshop_runner_prompt.md`를 채워 run마다 서브에이전트를 하나씩 띄운다(병렬 가능, background).
   `{EVENT_ORDER}`는 1단계 순서와 같게 쓴다.
3. 서브에이전트 보고를 그대로 믿지 말고 파일을 직접 확인한다: 00_input의 catalog 버전·코드 수, 분석 기준일,
   01~05 존재, 4a·6 실행 조건 준수, 조합 결정 표, Scenario 표.

### 6단계. 비교 보고서

1. 플랫폼 run마다 `structural_checks.py --run-dir …/run_XX`로 구조 결함을 자동 집계한다(보고서 ①·결함 발생 표의 근거).
   N > 1이면 `aggregate_runs.py --platform-dir {WORK}/platform --workshop-dir {WORK}/workshop --out {WORK}/aggregate.md`.
   자동 지표는 신호일 뿐이다. 예를 들어 "같은 Lever를 공유한 Dimension 수"가 크다고 곧 중복은 아니므로
   Dimension 질문·Choice 상태를 읽고 판정한다.
2. 가이드 Step 5 기준(HG-01~12, J-01~06·J-11)으로 플랫폼 결과를 run마다 채점한다. 워크숍은 각 run의 `05` 자체 채점을
   쓰되 같은 근거로 다시 확인하고, 이견이 있으면 점수를 바꾸고 이유를 적는다.
   - rubric 출처: 플랫폼 서비스 코드에는 rubric이 없다. 같은 기준이 저장소의 오프라인 평가 도구
     `tests/manual/quality_eval/judge.py`(`SCENARIO_JUDGE_IDS`)와 `scenario-quality-eval` 스킬에 정의돼 있다.
     J-07~J-10은 signpost 기준이라 시나리오 생성 비교에서는 쓰지 않는다.
   - rubric 평균 = 7개 기준(1~5점)의 산술 평균. 4 이상 PASS, 3 WARN, 2 이하 FAIL 수준으로 읽는다.
3. 보고서를 작성한다 (`references/report_template.md`).
   - N=1: `{WORK}/report_run_01.md` 하나. 예시는 `references/example_report_group307.md`.
   - N>1: run별 보고서 `report_run_XX.md`를 먼저 쓰고, 마지막에 `report_combined_Nruns.md`를 쓴다.
     종합 보고서에도 **단계별 비교(Step 0~6) 절을 반드시 넣는다**.
4. 사용자에게 마지막으로 알려줄 것:
   - 보고서 경로(scratchpad 경로는 탐색기에 보이지 않으므로 Finder ⇧⌘G 또는 `code <경로>` 안내)
   - 결론 요약, **"실습과 플랫폼이 다른 원인과 조치 방안" 목록**(중요 순, `| 순위 | 원인 | 근거(빈도) | 조치 방안 |`).
     양쪽 공통 한계와 분리하지 못한 변수(모델)는 표 밖에 따로 적는다.
   - 남은 테스트 데이터(이벤트·그룹·interrupted 그룹) 정리 필요 여부. 삭제는 요청이 있을 때만 한다.

## 평가 기준 (모드 A·B 공통)

### 측정 조건
- **벤치마크 세트를 고정**한다: 이벤트 조합 3~5개(예: 1681·1682·1683 가격·운임·화물흐름 + 공급 차질형 + 수요형), 조합당 3회.
- 변경은 **한 번에 하나**만 적용하고, 같은 세트로 직전 결과와 비교한다.
- 변경 전 결과가 있으면 재사용한다(`run_from_sse_log.py`, 기존 run 폴더). 로컬 agent가 변경 코드를 띄운 시각이
  마지막 커밋·수정보다 뒤인지 확인한다(VS Code 디버거로 띄운 서버는 사용자에게 재시작을 요청).

### 지표 4계층
| 계층 | 지표 | 측정 | 성격 |
|---|---|---|---|
| ① 구조 결함 (주 지표) | 이중 계산, Interaction 질문 기반 Dimension, 같은 대상 Dimension 중복, 핵심 Fact 누락·Primary 오류, primary role 없는 Path, 재시도, 음역·영문 일반어, 중간값 baseline, HG-08 | `structural_checks.py` (자동). "(신호)" 표시 지표는 결과를 읽고 확정 | 객관적 |
| ② 의미 품질 (보조) | rubric J-01~06·J-11 평균 | 채점자가 `run_XX/rubric.json`에 기록. 편향을 줄이려면 다른 모델로도 채점하거나 일부를 사람이 채점해 대조 | 판단 |
| ③ 안정성 | Dimension 수·Lever 구성, Interaction 구성, baseline band의 run 간 일치 | `compare_platform_runs.py`, `aggregate_runs.py` | 고객 체감 |
| ④ 가드레일 | 생성 실패, 소요 시간, Dimension 단계 시간(504 위험), 비용 | trace, run.json | 회귀 방지 |

### 기준선 (2026-10, 이벤트 1681·1682·1683, gpt-5.5, 3회)
- ①: 이중 계산 시나리오 2~4/run, 재시도 1~3/run, 음역 1/3 run, 핵심 Fact 누락 2/3 run, 중간값 baseline 1/3 run
- ②: rubric 평균 2.76 (2.57~2.86), 워크숍 3.62 · ③: Dimension Lever 구성 일치 1/3 · ④: 생성 2~5분, 그룹당 $0.56, 504 1/3 run
- 0-1(lever 표기)·0-2(음역) 반영 후 1회(그룹 366): 재시도 0, 음역 0, 대신 영문 일반어(cargo, landed cost) 18회 신호

### 판정 규칙 (변경 하나를 "개선"으로 인정하는 조건)
1. 변경이 겨냥한 ① 지표(`--target`)가 개선됐다.
2. 목표 외 ① 지표와 ④ 가드레일이 악화되지 않았다(시간은 +30% 이내).
3. ② rubric 평균이 떨어지지 않았다(채점한 경우).
- 양쪽 3회 미만이면 목표 외 지표의 변화는 무작위 변동일 수 있으니 판정을 보류하거나 run을 늘린다.
- ③ 안정성은 변경 몇 개를 묶은 시점에 따로 확인한다.
- 큰 단계가 끝날 때는 현업 1~2명에게 가이드 Step 5 Layer 3 질문(서로 다른 미래로 느껴지는가, 빠진 쟁점, 회의에 쓸 수
  있는가)으로 사람 평가를 받는다.

## 모드 B 절차 (플랫폼 변경 전후 비교)

1. 변경 내용과 겨냥한 ① 지표를 정한다(예: lever 표기 수정 → `retries`).
2. 변경 전 run 세트를 준비한다: 기존 결과를 재사용하거나, 변경 전 코드로 `run_platform.py --runs 3`.
3. 변경을 적용하고 로컬 agent를 재시작한다(사용자 확인). 변경 후 `run_platform.py --runs 3`
   (그룹 3개 생성, 비용 발생 → 실행 전 승인).
4. run마다 `export_group.py` → `fetch_trace.py` → `structural_checks.py`.
5. (선택) run마다 rubric을 채점해 `rubric.json`에 기록: `{"J-01": 3, …, "J-11": 3, "scorer": "<모델>"}`.
6. `compare_platform_runs.py --baseline <전> --candidate <후> --target <지표> --out …/compare_before_after.md`.
7. 사용자에게 판정 결과와 함께 다음을 보고한다: 목표 지표 변화, 새로 생긴 부작용(예: 영문 일반어), "(신호)" 지표를
   직접 확인한 결과, 다음 변경 제안.

## 모드 C 절차 (모델·파라미터 비교)

1. 코드 커밋을 고정하고(모든 세트가 같은 코드) 세트별로 바꿀 값을 하나만 정한다. 기존 기본 설정 결과가 있으면 기준 세트로 재사용한다.
2. 세트마다 `.env`(모델 배포명·엔드포인트·키, LLM 파라미터)를 바꾸고 재시작 → 첫 run trace로 실제 모델 확인 →
   `run_platform.py --runs N --out-dir {WORK}/models/<label>`. 게이트웨이 밖 엔드포인트(예: Azure 직접)는 시간 비교가
   정확하지 않으므로 보고서에 적는다.
3. run마다 `export_group.py` → `fetch_trace.py` → `structural_checks.py`.
4. `compare_model_sets.py --set "<label>=DIR" … --price "<배포명>=입력/출력" --out {WORK}/models/compare_models.md`.
   실패 run도 평균에 들어가므로 해석할 때 따로 적는다. 한 세트를 여러 폴더로 나눠 돌렸으면 `run_XX` 심볼릭 링크로 합친다.
5. 자동 지표만으로 결론 내지 않는다. 출력 품질(세 이벤트 반영, 인과 해석, 가격 방향 일관성, Dimension·선택지·baseline,
   문장)을 결과를 읽고 판정해 보고서로 정리한다.

## 원인 후보 체크리스트

보고서 "원인 매핑"에서 각 항목을 trace로 확인 / 추정 / 해당 없음 / 양쪽 공통으로 판정한다.
코드 위치는 실행 시점의 코드에서 다시 확인한다.

| 영역 | 후보 | 확인 위치 |
|---|---|---|
| 입력 | 이벤트 입력이 제목(120자)·한 줄 요약(240자)·key_bullets로 한정, detail_analysis 미사용 | `prompts/model_lever_scenario_generation.py` `build_v4_event_impact_analysis_user_prompt`, `prompts/event_context.py` |
| 입력 | 분석 기준일 = 실행일, 관측일과의 간격 때문에 질문이 "현재 …인가" 확인형으로 바뀜 | `v4_flow.py` `_analysis_as_of` |
| Step 1 | "eventFacts 가급적 1~2개" 지시로 Supporting Fact 누락 | 같은 프롬프트 출력 규칙 |
| Step 1·2 | reasoning effort `low` 고정 | `v4_nodes.py` `reasoning_effort_override="low"` |
| Step 1 | 이벤트별 개별 호출로 이벤트 간 관점 부재 | `v4_nodes.py` `AnalyzeEventImpactsNode` |
| 예산 | 질문 예산이 요청 순서에 따라 다름, Interaction당 질문 1개 | `v4_budget.py`, `V4_INTERACTION_SYSTEM_PROMPT` |
| Step 2 | Lever 카드 표기(`code direction (scope, timing)`)와 "code 그대로 복사" 요구 충돌 → 검증 실패·재시도 시 관계 변경 | `build_v4_interaction_analysis_user_prompt` |
| 전달 | 단계 간 정보 축약(Fact 원문 미전달, "시장 의미" = 질문 반복, mechanism 240자 절단) | `_render_uncertainty_cards`, path card 렌더링 |
| Step 3 | 조합 결정(KEEP/MERGE/EXCLUDE/SEPARATE_EFFECT) 절차 부재 → 같은 Lever Dimension 중복·이중 계산 | `V4_DIMENSION_SYSTEM_PROMPT`, `build_v4_dimension_design_user_prompt` |
| Step 3 | Dimension 수 권장(3~4, unused 남기기) | 같은 함수 |
| Step 3 | Choice pressure 3단계 제한 | `v4_schema.py` `V4ReadableDimensionChoice.pressure` |
| Step 4 | band 순서 ±1 합산 검증, 5 band 강제, 제외 후보 최대 2개 | `v4_schema.py` `_validate_scenarios` |
| Step 4 | pressureBreakdown 기계적 연결 | `expand_v4_readable_scenario_synthesis` |
| 검수 | 의미 품질 검수 단계 없음 | — |
| catalog | Lever catalog 정의 차이(v2 ↔ v4: `shipping_cost` → `lng_charter_rate`, `route_disruption` 축소) | DB `tmm_mi_model_impact_lever_m` |
| Step 1 | Primary Fact(eventFacts[0])가 제목·요약 핵심 수치를 담는지 서버가 확인하지 않음 → 제목 핵심 Fact 누락 | Event 분석 프롬프트, `finalize_v4_event_impact_analysis` |
| Step 1 | Path에 primary role step 없이 driver만 있음, E2처럼 balance 방향이 Lever 방향과 엇갈림(`trade/increase` + decrease) | Event 분석 프롬프트 balance·role 규칙 |
| Step 1 | catalog 정의 밖 Lever 사용(예: 화물 재배분에 `trade_restriction`) | 같은 프롬프트, catalog `applicability_hint` |
| Step 2 | 관계 유형 정의 없음 + "같은 방향입니까" 질문 → 원인·결과 관계(causal_link)를 amplification으로 분류, materiality 비어 있음 | `V4_INTERACTION_SYSTEM_PROMPT`, `build_v4_interaction_analysis_user_prompt` |
| Step 3 | **Interaction 질문(iu*)을 그대로 Dimension으로 만들고, 같은 Interaction을 시나리오에 또 적용** → 이중 계산 | Dimension·Scenario 프롬프트 (워크숍은 EXCLUDE + SEPARATE_EFFECT로 막음) |
| Step 3 | Choice 시점 경계 없음("분석 기준일 이후" 한 가지), why가 같은 수치를 반복하는 정형 문장, 같은 축에 balanced 2개 | Dimension 프롬프트 why 지시 |
| Step 4 | baseline 기준이 "추가 가정이 적을수록 높은 확률"뿐 → 모든 축 중간값 조합이 baseline | `build_v4_scenario_synthesis_user_prompt` |
| Step 4 | "description에 JKM 금지·영문 Event/Scenario 금지" 규칙의 과잉 적용 → "엘엔지·제이케이엠" 음역 | `V4_SCENARIO_SYSTEM_PROMPT` |
| 운영 | LLM 게이트웨이 60초 타임아웃(504), 재시도 피드백에 HTML 오류 본문 주입 | trace error, `_feedback` |
| 운영 | DB 장애 시 진행 중 operation이 `interrupted`로 끝나고 자동 재개 없음 | operation heartbeat |
| 모델 | gpt-5.5(strict JSON) 대 Claude | 조건 차이로 기록 |

### 보고서에 쓸 때 참고할 해석

- **Interaction 관계 유형**: amplification = 서로 독립적인 두 충격이 같은 방향으로 겹침, causal_link = 한 이벤트가 다른
  이벤트의 발생·확대·지속 조건을 만듦, offset = 반대 방향으로 상쇄, regional_coupling = 지역 간 화물·가격차로 연결.
  원문이 한 이벤트를 다른 이벤트의 원인으로 서술하면 causal_link가 맞고, 이를 amplification으로 두면 같은 현상을
  독립된 상방 압력 두 개로 세는 이중 계산 위험이 있다는 점을 보고서에 설명한다.
- **N>1에서 원인 판정**: "3/3 재발"처럼 빈도를 적고, 매 run 모양이 달라도 근본 원인이 같으면 하나로 묶는다
  (예: 조합 결정 절차 부재 → run마다 다른 형태의 중복).
- **양쪽 공통 한계**(catalog v4의 Lever 부족, strong band floor 정렬 등)는 차이의 원인에서 제외하고 따로 적는다.

## 정리용 SQL (요청이 있을 때만, 실행 전 확인)

```sql
-- 이번 비교로 만든 이벤트
SELECT mi_event_id, event_title FROM tmm_mi_mievent_m WHERE crt_usr_logn_id = '<tag>';
-- soft delete 예시 (사용자 승인 후)
UPDATE tmm_mi_mievent_m SET del_yn = 'Y' WHERE crt_usr_logn_id = '<tag>';
```

그룹 삭제는 `scenario-sync-pipeline` 스킬의 관리자 토큰 절차를 따른다.

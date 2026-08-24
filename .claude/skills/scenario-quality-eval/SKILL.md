---
name: scenario-quality-eval
description: MI Scenario Group Agent의 create/validation/signpost sync 결과를 품질 관점에서 평가한다. scenario-sync-pipeline 실행 후 남은 JSON/SQLite 증적을 입력으로 event grounding, baseline 타당성, edge case 다양성, dimension 정합성, 시나리오 모순, signpost 변별성/관련성, validation 검사 유효성, MLflow trace 기반 원인 진단을 수행하거나 평가 스크립트를 구현/보완해야 할 때 사용한다.
---

# Scenario Quality Eval

이 skill은 `scenario-sync-pipeline`의 성공/실패/수행시간 평가를 넘어, 생성된 scenario group 내용의 품질을 평가한다. 먼저 `scenario-sync-pipeline`으로 batch를 실행해 JSON 증적과 SQLite 지표를 만든 뒤 이 skill을 적용한다.

## 관련 문서

작업 전에 필요한 문서를 읽는다.

- API body, callback, stage 전이를 변경하거나 해석할 때: `docs/agents/scenario_group_agent/02_SCENARIO_GROUP_AGENT_API_SPEC.md`
- graph, shared state, generation pipeline, validation flow를 변경하거나 해석할 때: `docs/agents/scenario_group_agent/03_SCENARIO_GROUP_AGENT_FLOW.md`
- DB table, JSON column, 관계와 transaction을 변경하거나 해석할 때: `docs/agents/scenario_group_agent/04_SCENARIO_GROUP_AGENT_DB_SPEC.md`
- 파일 배치, package boundary, endpoint-flow mapping을 변경할 때: `docs/architectures/project_directory_structure.md`
- Python 코드 작성/수정 시: `.claude/rules/python-conventions.md`
- 세부 평가 설계 확인이 필요할 때: `local/plan/15_evaluation_scenarios_claude.md`

## 입력 산출물

기본 입력은 `local/output/sync_pipeline_api_test/<batch_id>/` 아래의 batch 증적이다.

- `selected_events.json`
- create/validation/signpost/confirmation 단계별 callback JSON
- 가능하면 `<mi_event_id>_event_detail.json`
- `local/output/sync_pipeline_api_test/sync_pipeline_metrics.sqlite3`

event detail이 없으면 event payload 기반 검사는 임의로 통과시키지 말고 `SKIP: missing event_detail`로 기록한다.

## 기본 실행 흐름

1. batch 대상과 증적을 확인한다. `--batch-id`가 없으면 SQLite의 `pipeline_runs`에 기록된 최신 batch를 선택한다. metrics가 없는 복사본에서는 `YYYYMMDD_HHMMSS/selected_events.json` 형태의 증적만 후보로 삼으므로 `live_logs` 같은 보조 디렉터리는 선택하지 않는다. CLI가 출력한 `quality batch:` 값을 먼저 확인한다.
2. `pipeline_runs.status='success'`인 run만 품질 평가 대상으로 삼는다. 실패 run은 "pipeline 실패"로 별도 집계한다.
3. Layer 1 결정적 규칙 검사를 실행한다.
4. Layer 2 Agent Judge 루브릭 평가를 이 skill을 실행 중인 Codex 또는 Claude 모델이 직접 수행한다.
5. 사용자가 validation 자체 평가를 요청했거나 `--mutations`/`--probe`가 지정되면 Layer 2.5 mutation probe를 실행한다.
6. MLflow tracing이 활성이고 접근 가능하면 Layer 3 trace 진단을 실행한다. 접근 실패나 trace 부재는 infra fail/skip으로 기록하고 품질 fail로 섞지 않는다.
7. SQLite에 평가 결과를 저장하고 `<batch_id>/quality_report.md`를 생성한다. (한국어로)
8. 평가의 마지막 산출물로 `<batch_id>/violation_plan_background.md`를 생성한다. 개별 rubric 순서가 아니라 정성적 원인, 유사한 수정 방향, 책임 stage 기준으로 violation을 묶어 후속 plan의 배경 문서로 만든다.

## 실행 명령

파이프라인 batch를 먼저 만든 뒤, 해당 batch를 평가한다. `--batch-id`를 생략하면
가장 최근 증적 디렉터리를 선택한다.

### Agent·MLflow 로컬 설정

live API와 MLflow 정보를 매번 명령에 쓰지 않으려면 이 skill 폴더의
`test_info.local`에 저장한다. 이 파일은 gitignore 대상이며 비밀번호를 Git에
추가하지 않는다. CLI 값이 local 파일보다 항상 우선한다.

```ini
# .claude/skills/scenario-quality-eval/test_info.local
agent=mi-vm                 # mi-vm=http://40.82.137.178:8001, local=http://localhost:8000
user_id=10603
mlflow_uri=http://<mlflow-host>:<port>
mlflow_username=<username>
mlflow_password=<password>
```

`--agent mi-vm` 또는 `--agent local`을 직접 주어도 된다. `--base-url`은 alias와
local 파일보다 우선하며, user ID는 명시하지 않으면 항상 `10603`을 사용한다.

Agent Judge 입력을 먼저 생성한다. 이 명령은 LLM API를 호출하지 않는다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id> --prepare-judge-only
```

명령이 출력한 `quality_judge_input.json`을 직접 읽고 `constraints`, `rubrics`,
`requiredJudgeIds`, `outputSchema`, `targets`에 따라 현재 skill을 실행 중인 모델이
평가한다. 별도 LLM API, 앱 LLM connector, `codex exec`, `claude` CLI를 호출하지
않는다. 결과를 같은 batch의 `quality_judge.json`에 작성한 뒤 평가 명령을 다시
실행해 검증·SQLite 저장·보고서 생성을 완료한다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id>
```

judge 안정성 수용 검증은 `--stability-runs 2`로 입력을 만들고 동일한 고정
batch/prompt version을 두 번 독립적으로 평가해 rubric verdict 일치율을 리포트에
남긴다. 두 pass를 모두 `quality_judge.json`에 작성하며 80% 이상을 수용 기준으로
삼는다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id> --judge-limit <N> --stability-runs 2 \
  --prepare-judge-only
```

두 pass를 작성한 뒤 최종 실행에도 같은 `--judge-limit`과 `--stability-runs 2`를
전달해 입력과 결과 집합을 동일하게 검증한다.

Layer 1·성능 리포트만 확인하려면 `--no-judge`를 사용한다.
trace는 명시적으로 URI를 줄 때만 수집하며, trace 없음/접근 실패는 품질 FAIL이
아닌 별도 SKIP/infra 결과다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id> --no-judge
```

mutation probe는 성공 run의 create table을 사용해 confirmation 전 validation sync만
반복한다. live 호출이므로 agent URL과 user ID가 모두 필요하다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id> \
  --probe \
  --agent local \
  --user-id 10603 \
  --probe-mutations V-00,V-01,V-04,V-05,V-06,V-07,V-08,V-09
```

단일 table의 mutation 형태만 먼저 확인하려면 별도 probe CLI의 `--dry-run`을 쓴다.

```bash
./.venv/bin/python tests/manual/eval_validation_probe.py \
  --agent local \
  --scenario-group-id <id> \
  --table-json local/output/sync_pipeline_api_test/<batch_id>/<mi_event_id>_step1_create_response.json \
  --user-id 10603 --dry-run
```

품질 리포트는 평균 점수보다 violation 목록을 우선한다. 각 violation에는 대상, 인용 evidence, reason, suggested fix, fact dependency를 포함한다.

## Layer 1: 결정적 규칙 검사

Python 코드로 재현 가능하게 검사한다. 의미 판단이 필요한 경우 여기서 억지로 판정하지 말고 Layer 2로 넘긴다.

- `R-01`: callback 필수 필드 존재. `scenarioGroup`, `table.headers`, `table.rows`, `rows[].cells`.
- `R-02`: baseline은 정확히 1개다. `baselineYn=Y`.
- `R-03`: 모든 row의 cell key가 headers와 일치하고 null/빈 cell이 없다. validation 자동생성 dimension은 예외 처리한다.
- `R-04`: event detail의 `scenarioTemplate` value enum이 있으면 cell 값이 enum에 속하는지 확인한다. 근거가 없으면 skip한다.
- `R-05`: scenario 간 dimension value 조합이 완전히 중복되지 않는다.
- `R-06`: scenario 개수는 생성 schema/설정 기준에 맞는지 확인한다. 기본 운영 기대치는 5~7개다.
- `R-07`: scenario별 signpost가 1개 이상이고 id/label/strength가 존재하며 `probabilityImpactScore` 범위와 direction code가 callback 노출 필드 기준으로 유효하다.
- `R-08`: 동일 signpost label이 모든 scenario에 공통 등장하는 비율을 계산한다. 전 scenario 공통 signpost는 변별력 0점 신호다.
- `R-09`: validation callback의 stage/isValid 정합성을 확인한다. `isValid=true`면 `scenario_validated`, `isValid=false`면 `scenario_created`가 기대값이다.

Layer 1 FAIL은 구조상 사용 불가능한 결과를 뜻한다. Layer 1 WARN/SKIP은 리포트에 분리해서 표시한다.

## Layer 2: Agent Judge

별도 모델 호출 없이 현재 skill runtime 모델이 그룹별 두 rubric 묶음을 직접 평가한다.

- `scenario_set`: scenario set 평가. `J-01`~`J-06`, `J-11`.
- `signposts`: signpost 평가. `J-07`~`J-10`.

입력 묶음은 event detail, `scenarioTemplate`, step1 scenario table, step2 validation table, step3 signpost table이다. 외부 web search는 기본 범위에서 제외한다.

Judge 출력은 `quality_judge_input.json`의 schema에 맞춰 structured JSON으로 작성한다.

- `score`: 1~5
- `verdict`: `PASS | WARN | FAIL`
- `violations[]`: `target_type`, `target_id`, `evidence`, `reason`, `suggested_fix`, `fact_dependency`
- `fact_dependency`: `NONE | EVENT_PAYLOAD_ONLY | EXTERNAL_FACT_REQUIRED`

외부 사실이 필요한 위반은 hard fail 집계에 섞지 말고 `NEEDS_FACT`로 별도 표시한다.

### Judge Rubric

- `J-01` Event grounding: group/scenario/signpost가 이벤트 핵심 driver, 수치, 지역을 반영하는지와 이벤트에 없는 사실을 만들었는지 평가한다.
- `J-02` Baseline 타당성: baseline scenario가 가장 개연성 높은 전개인지, edge case가 baseline으로 지정되지 않았는지 확인한다.
- `J-03` Scenario spectrum: 낙관-비관 스펙트럼과 저확률/고임팩트 edge case를 충분히 커버하는지, 서사가 중복되는 쌍이 있는지 본다.
- `J-04` Dimension quality: dimension과 dimension value가 이벤트의 분기 논리와 각 scenario narrative에 맞는지 평가한다.
- `J-05` Internal consistency: scenario 내부 모순과 scenario 간 동시 성립 가능한 조합(MECE 위반)을 찾는다.
- `J-06` Domain/geography/market consistency: EU/TTF, JKM, HH 등 시장/지역/상품 맥락이 event와 맞는지 본다.
- `J-07` Signpost relevance: signpost가 event 및 소속 scenario와 직접 연결되는지 signpost별로 판단한다.
- `J-08` Signpost discriminativeness: signpost가 소속 scenario를 다른 scenario와 구분하는지 본다.
- `J-09` Observability/temporal relevance: 뉴스/지표/공식 발표로 관측 가능한 표현인지, event time horizon에 맞는지 본다.
- `J-10` Causal direction/strength: direction, strength, reason이 scenario probability를 높이는 논리와 맞는지 callback 필드 기준으로 평가한다.
- `J-11` Clarity: 시장 참여자가 근거 사슬을 따라갈 수 있는 명료한 서술인지 평가한다.

### Batch Verdict

- `PASS`: critical violation 없음, 평균 4.0 이상, Layer 1 FAIL 없음.
- `WARN`: 평균 3.0 이상이지만 minor violation 또는 Layer 1 WARN 존재.
- `FAIL`: 평균 3.0 미만, critical violation, 또는 구조상 사용 불가능한 Layer 1 FAIL 존재.
- `NEEDS_FACT`: 핵심 판단에 외부 사실 확인이 필요함.

## Layer 2.5: Validation Mutation Probe

validation은 create 결과와 동일한 table을 받으면 unchanged fast-path로 검사를 건너뛸 수 있다. validation 검사 자체의 유효성을 보려면 create 결과 table에 결함을 1개씩 주입해 validation/sync를 반복 호출한다.

Probe는 validation review의 실제 책임 범위에 맞춘다.

- `V-00`: 변형 없이 재전송. 즉시 pass, `scenario_validated`, 가능하면 review LLM span 없음.
- `V-01`: 두 scenario의 cells 조합을 동일하게 복제. MECE 중복 탐지 기대.
- `V-02`: 모든 row가 특정 dimension에서 같은 값만 쓰도록 변경. value diversity 탐지 기대.
- `V-03`: baseline과 다른 대안값이 사라지도록 값 수렴. baseline contrast 탐지 기대.
- `V-04`: enum상 양립하기 어려운 조합 또는 narrative-cell 충돌 주입. compatibility LLM 탐지 기대.
- `V-05`: optional dimension header 추가 + 일부/전체 null cell. enum 내 값 자동생성 기대.
- `V-06`: required dimension header 삭제 또는 required cell null. API/input validation error 기대.
- `V-07`: title wording만 의미 보존 변경. review path 진입 후 clean pass 기대, WARN 발생 시 false positive 후보.
- `V-08`: 두 scenario title을 공백·문장부호 정규화 후 동일하게 변경. 완전 중복 FAIL과 `isValid=false` 기대.
- `V-09`: 두 scenario title을 `가격 상승함`/`가격 상승임`처럼 의미상 같게 변경. 유사 제목 WARN과 `isValid=false` 기대.

현재 API가 `checks[]`를 노출하지 않으면 `isValid`, `scenarioGroup.stage`, `reason` keyword, callback table 변화, MLflow trace 순서로 판정한다. reason 파싱은 취약하므로 check-id 단위 정밀 판정이 필요하면 API 관측성 개선을 제안한다.

## Layer 3: MLflow Trace 진단

tracing이 활성화되어 있고 tracking server 접근이 가능할 때만 실행한다.

- `scenario_group_id` tag로 trace를 검색한다.
- flow별 trace, node/span, LLM CHAT_MODEL span의 inputs/outputs를 확인한다.
- Layer 1/2 violation을 책임 stage와 연결한다.
- 리포트에서는 trace에서 확인한 사실과 Agent Judge의 개선 해석을 구분한다.

Trace가 없으면 "원인 국소화 불가(trace 없음)"로 명시한다.

## Golden Case 메타 평가

전문가 피드백을 정답 라벨로 축적해 judge recall을 검증한다.

경로:

```text
tests/manual/golden_cases/
  README.md
  gc_<miEventId>_<slug>.md
```

Golden case md는 frontmatter에 `mi_event_id`, optional `scenario_group_id`, `event_title`, `source`, `feedback_date`, optional `artifacts`를 둔다. 본문에는 원문 피드백과 `GC-xx` 라벨을 둔다.

라벨에는 다음 값을 포함한다.

- `type`: `A` 이벤트 모순, `B` 외부 사실, `C` 관련성/변별력, `D` 명료성
- `target`: `scenario | signpost | group`
- `expected_judge`: `J-01` 등
- 지적 내용, 인용, 비고

`--golden` 실행은 정식 채점이다. judge violation과 golden label의 matched/missed/extra를 판정해 `golden_case_results`에 기록하고 recall을 리포트한다. 일반 batch에서 golden `mi_event_id`와 우연히 겹치면 "별도 `--golden` 실행 필요" 안내만 표시하고 정식 채점은 하지 않는다.

현재 매칭은 자동 키워드 판정 대신 검토자가 수행한다. `--golden`은 등록 event의
증적을 찾아 judge 결과와 label을 리포트에 나란히 내보내며, 검토 결과 JSON을
`--golden-record`로 전달하면 `golden_case_results`에 영속화한다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py --golden
./.venv/bin/python tests/manual/eval_scenario_quality.py --golden \
  --golden-record local/output/golden_review.json
```

`golden_review.json`은 객체 배열이며 각 객체에 `golden_id`, `matched`, `missed`,
`extra`를 둔다. 선택적으로 `mi_event_id`, `judge_ids`, `detail`을 추가할 수 있다.

## SQLite 기록

기존 `sync_pipeline_metrics.sqlite3`를 재사용한다. 필요 table은 평가 스크립트가 생성한다.

- `quality_evals`: eval id, batch id, event id, scenario group id, skill runtime judge model, prompt version, created at.
- `quality_check_results`: check id, status, detail, offenders.
- `quality_judge_scores`: judge id, score, verdict, violations json.
- `validation_probe_results`: mutation id, expected, observed, verdict, detail.
- `golden_case_results`: golden id, matched/missed/extra, judge ids, detail.

Judge prompt에는 `prompt_version` 상수를 두고 SQLite에 기록한다.

batch 디렉터리에는 Agent Judge 교환 파일도 둔다.

- `quality_judge_input.json`: 결정적 검사, rubric, evidence, 출력 schema.
- `quality_judge.json`: 현재 skill runtime 모델이 작성한 판정.

## Report Format

`<batch_id>/quality_report.md`는 단독으로 읽혀야 한다.

### 보고서 언어

- `quality_report.md`의 제목, 요약, 표의 설명, violation의 reason 및 suggested fix 등 사람이 읽는 서술은 **가급적 한국어로 작성한다**.
- 영어 작성도 허용하지만, 한국어 사용자에게 전달하는 기본 산출물은 한국어를 우선한다.
- `miEventId`, rubric/check ID, API·DB 필드명, enum, 로그/원문 evidence와 같은 기계 식별자 또는 원문 인용은 정확성을 위해 원문 언어를 유지할 수 있다.

포함할 섹션:

- 전체 verdict 요약: PASS/WARN/FAIL/NEEDS_FACT/infra fail.
- 품질 대상/제외 대상: 성공 run과 pipeline 실패 run 분리.
- Layer 1 check 결과표.
- Layer 2 rubric score와 violation 상세.
- Validation probe 결과와 seeded-defect recall, clean-pass rate.
- Golden case recall. `--golden` 실행 시만 정식 채점.
- API별 수행시간 통계: avg/min/max/p95, 호출 수, 실패 수.
- 최장 케이스 top-N: SQLite로 확인 가능한 사실, trace 활성 시 stage별 병목.
- 실패 케이스 표: `miEventId`, `eventTypeL2Id`, initial action state, 실패 step, status code, reason.
- 관측성 개선 제안: API가 노출하지 않아 skip/취약 판정된 항목.

사용자에게 최종 보고할 때는 report path, SQLite path, 전체 verdict, 주요 FAIL/WARN violation, 실행하지 못한 계층 또는 skip 사유를 짧게 포함한다.

## Plan Background Format

품질 평가가 끝나면 `quality_report.md`와 별도로
`<batch_id>/violation_plan_background.md`를 항상 생성한다. violation이 없으면 없다는
결론과 남은 skip/infra risk를 기록한다.

이 문서는 구현 plan 자체가 아니라 사용자가 개선 범위를 선택하고 의견을 남기기 위한
plan 배경 문서다. 다음 규칙을 따른다.

- JudgeRubric별로 나열하지 말고 정성적으로 동일한 원인끼리 묶는다.
- `suggested_fix`가 실질적으로 같은 항목을 하나의 수정 패턴으로 묶는다.
- 각 원인에 P0/P1/P2 우선순위를 부여하고 근거를 짧게 적는다.
- 주 개선 대상과 연계 대상을 다음 범주에서 명시한다.
  - 평가로직
  - create scenarios
  - validation
  - create signposts
  - prompt
  - 구조/schema
  - 추가정보
  - 기타 개선
- 평가로직, create scenarios, validation, create signposts별 plan 후보를 분리하고
  완료 기준을 적는다.
- 각 원인과 주요 plan 후보에 `Accept / Reject / Hold` 또는 `Yes / No / Later` 선택란과
  추가 의견란을 둔다.
- 상세 evidence 전체를 반복하지 말고 event ID와 대표 target만 남긴다.
- stage 원인은 trace에서 확인한 사실과 산출물만 보고 추정한 책임을 구분한다.
- 가로로 넓은 표를 사용하지 않는다. `##`/`###` heading과 bullet 기반 카드 형식을
  기본으로 사용한다. 표가 꼭 필요하면 열 수를 최소화한다.

권장 문서 순서는 다음과 같다.

1. 핵심 수치와 결론
2. P0 정성적 원인 카드
3. P1/P2 정성적 원인 카드
4. 유사 suggested fix 묶음
5. 평가로직/create scenarios/validation/create signposts별 plan 후보
6. event별 대표 원인과 target 추적 메모
7. plan 확정 전 결정 사항
8. evidence·trace·안정성 관련 해석상 주의

사용자에게 최종 보고할 때 `violation_plan_background.md` 경로도 함께 제공한다.

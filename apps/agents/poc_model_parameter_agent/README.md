# LNG Scenario-to-Parameter Learning Agent

LNG Scenario Group JSON을 검증하고 결정적 월별 Parameter proposal로 변환한 뒤, 사용자 Feedback을 별도 Learning Worker가 Memory/Skill candidate로 검토하는 독립형 POC입니다. React Web, FastAPI API, MySQL 8.4, Alembic migration, polling Worker가 하나의 Docker Compose stack으로 실행됩니다.

> 모든 baseline은 실제 시장 데이터가 아닌 **Prototype synthetic baseline**입니다. 같은 Parameter와 월은 항상 같은 값을 만들지만 투자·거래 판단용 실측 데이터가 아닙니다.

## Architecture

```text
Browser :5173
  └─ Nginx + React 19
       ├─ SPA routes
       └─ /api, /health proxy
             └─ FastAPI :8000
                  ├─ deterministic 9-step Main Pipeline
                  ├─ Run / Artifact / Proposal query
                  ├─ unified Feedback ledger + Child Revision transaction
                  └─ Candidate approval / Asset version transaction
                         └─ MySQL 8.4 :13307

Learning Worker (separate process)
  └─ SELECT ... FOR UPDATE SKIP LOCKED
       └─ classification → diff → evaluation → pending candidate
```

- `AGENT_MODE=mock`가 기본입니다. Main Pipeline과 Learning classification은 외부 API key나 LLM 없이 재현 가능합니다.
- Optional LLM adapter는 향후 확장 경계일 뿐, 현재 핵심 흐름이나 Test의 선행 조건이 아닙니다.
- Main Pipeline은 Run 시작 시 active Asset Version snapshot을 저장합니다.
- Interim과 Final은 하나의 `feedback` 원장에 저장됩니다. Final Feedback은 제출 transaction 안에서 즉시 Child Run Revision을 만들고 `result_run_id`로 연결됩니다.
- Learning Worker는 Feedback을 검토해 Candidate만 만듭니다. Main Run 재실행, Candidate 자동 승인, Catalog 변경은 하지 않습니다.
- Memory와 Skill만 learnable입니다. Candidate 승인은 base version이 active version과 일치할 때만 새 version을 활성화합니다. 불일치는 HTTP 409와 전체 rollback입니다.

## Prerequisites

- Docker Engine 24+와 Docker Compose v2.20+
- Docker Desktop 사용 시 CPU 4개 이상, Memory 8GiB 이상 권장
- Native 개발 시 Python 3.12, Node.js 22, npm 10+
- Browser E2E를 native로 실행할 경우 Chromium 설치가 가능한 환경

## Environment

```bash
cd apps/agents/poc_model_parameter_agent
cp .env.example .env
```

`.env.example`의 credential은 Local POC 전용입니다. 실제 secret을 commit하지 마십시오. 주요 설정은 다음과 같습니다.

| 변수 | 기본값 | 용도 |
|---|---:|---|
| `AGENT_MODE` | `mock` | 결정적 계산·학습 mode |
| `DATABASE_URL` | `mysql+pymysql://...@mysql:3306/...` | API/Worker/Alembic 공용 DSN |
| `API_PORT`, `WEB_PORT`, `MYSQL_PORT` | `8000`, `5173`, `13307` | Host port |
| `MAX_SCENARIO_PAYLOAD_BYTES` | `1048576` | Scenario JSON 최대 크기 |
| `WORKER_POLL_INTERVAL_SECONDS` | `5` | Worker polling 간격 |
| `WORKER_BATCH_SIZE` | `20` | 한 cycle에서 선점할 Feedback 수 |
| `WORKER_MAX_ATTEMPTS` | `3` | 처리 실패 최대 횟수 |

## Docker Compose

### 시작과 상태 확인

```bash
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/health
curl --fail http://localhost:5173/health
```

기동 순서는 `mysql healthy → migrate/seed complete → api healthy + worker → web`입니다. 화면은 <http://localhost:5173>에서 확인합니다.

```bash
docker compose logs -f api worker
docker compose stop
docker compose start
docker compose down
```

`docker compose down`은 named MySQL volume을 보존하므로 새로고침과 Container 재시작 후에도 Run·Feedback·Candidate·Asset Version이 유지됩니다. `down -v`는 해당 Compose project의 DB를 삭제하므로 개발 데이터 삭제 의도가 명확할 때만 사용하십시오.

### `migrate Starting`이 끝나지 않을 때

먼저 별도 Terminal에서 실제 Migration이 실행 중인지 확인합니다.

```bash
docker compose ps -a
docker compose logs --no-log-prefix mysql migrate
docker inspect --format '{{json .State}}' poc-model-parameter-migrate-1
```

`migrate`가 `status=created`, `Pid=0`, `StartedAt=0001-...`이고 Log도 비어 있다면 Alembic이나 Seed가 멈춘 것이 아닙니다. Docker Engine이 Container process와 network endpoint를 시작하기 전에 멈춘 상태입니다.

1. 실행 중인 `docker compose up`을 `Ctrl+C`로 종료합니다.
2. Docker Desktop의 **Settings → Resources**에서 CPU를 4개 이상, Memory를 8GiB 이상으로 설정합니다.
3. Docker Desktop을 재시작합니다. `restart: "no"`인 다른 Project의 Container는 필요하면 명시적으로 다시 시작합니다.
4. 아래처럼 기존 Image와 named volume을 보존한 채 Stack을 다시 시작합니다.

```bash
docker compose up -d --no-build
docker compose ps -a
curl --fail --max-time 10 http://localhost:8000/health
curl --fail --max-time 10 http://localhost:5173/health
```

이 복구 과정에서 `docker compose down -v`, `docker volume rm`, Docker Desktop의 **Clean / Purge data**는 사용하지 마십시오. 이 명령들은 POC의 영속 데이터를 삭제합니다.

### Migration과 idempotent Seed

Compose 기동 시 `migrate` service가 자동 실행합니다. 수동 확인은 다음과 같습니다.

```bash
docker compose run --rm migrate
docker compose run --rm migrate
docker compose exec api python -m app.seed
docker compose exec api python -m app.seed
```

두 번째 migration/seed는 기존 Version과 active 상태를 덮어쓰지 않는 no-op이어야 합니다.

## Native Development

MySQL만 Docker로 시작한 뒤 Backend를 host에서 실행할 수 있습니다.

```bash
docker compose up -d mysql

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export PYTHONPATH="$PWD/backend"
export DATABASE_URL='mysql+pymysql://poc_agent:poc_agent@127.0.0.1:13307/poc_model_parameter?charset=utf8mb4'
alembic -c alembic.ini upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

별도 terminal에서 Worker를 실행합니다.

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/backend"
export DATABASE_URL='mysql+pymysql://poc_agent:poc_agent@127.0.0.1:13307/poc_model_parameter?charset=utf8mb4'
python -m app.worker
```

Frontend는 API와 같은 origin proxy가 필요한 Docker 구성이 가장 안정적입니다. Native Vite 사용 시 `/api` proxy가 `http://127.0.0.1:8000`을 향합니다.

```bash
cd frontend
npm install
npm run dev
```

## Test

### Backend Unit + MySQL Integration

`test` profile은 개발 DB가 아닌 `mysql-test`의 tmpfs DB를 사용합니다. Migration과 Seed를 먼저 실행한 뒤 전체 pytest를 수행합니다.

```bash
COMPOSE_PROJECT_NAME=poc-model-parameter-test \
  docker compose --profile test run --build --rm backend-test

COMPOSE_PROJECT_NAME=poc-model-parameter-test \
  docker compose --profile test down -v
```

Native unit test만 실행할 때:

```bash
source .venv/bin/activate
PYTHONPATH=backend pytest -q backend/tests/unit
```

### Frontend typecheck, Component Test, Build

```bash
cd frontend
npm install
npm run typecheck
npm run test:run
npm run build
```

Docker에서 Component Test만 실행할 수도 있습니다.

```bash
docker compose --profile test run --build --rm --no-deps frontend-test
```

### Browser E2E와 Screenshot

E2E는 version-controlled `docker/e2e.env`를 통해 별도 Compose project와 `poc_model_parameter_e2e` DB/volume을 강제합니다. 개발 stack을 실행 중이어도 host port가 겹치지 않습니다.

```bash
docker compose --env-file docker/e2e.env --profile e2e run --build --rm e2e
```

Test 종료 후 별도 E2E DB만 정리합니다.

```bash
docker compose --env-file docker/e2e.env --profile e2e down -v
```

Native Playwright 실행:

```bash
cd e2e
npm install
npx playwright install chromium
E2E_BASE_URL=http://localhost:5173 npm test
```

Node 22에서 설치된 Chrome을 재사용하는 검증 경로는 다음과 같습니다.

```bash
PLAYWRIGHT_CHANNEL=chrome E2E_BASE_URL=http://localhost:5173 npm test
```

1440px 검토용 Screenshot은 다음 경로에 생성됩니다.

- `e2e/artifacts/screenshots/parameter-input-plan.png`
- `e2e/artifacts/screenshots/parameter-result.png`
- `e2e/artifacts/screenshots/run-history.png`
- `e2e/artifacts/screenshots/feedback-ledger.png`
- `e2e/artifacts/screenshots/learning-batches.png`
- `e2e/artifacts/screenshots/learning-candidates.png`
- `e2e/artifacts/screenshots/candidate-detail.png`
- `e2e/artifacts/screenshots/asset-versions.png`

실패 시 trace, screenshot, video와 HTML report는 `e2e/artifacts/` 아래에 남습니다.

## Example User Flow

1. **Parameter 생성**에서 예시 1을 불러오고 JSON 검증 → 계획 생성 → Parameter 생성을 실행합니다.
2. Scenario tab과 Proposal 행을 바꿔 Gauge, Plot, Trace, Formula가 함께 바뀌는지 확인합니다.
3. 예시 3에서는 Required timing Clarification에 응답하기 전 실행 버튼이 잠깁니다. 응답은 `interim/clarification` Feedback으로 저장됩니다.
4. 결과의 **최종 사용자 피드백 → Parameter 재생성**에서 Scope와 원문을 제출합니다. 같은 Revision에 Final은 한 번만 가능하며 새 Child Revision으로 이동합니다.
5. **피드백 원장**에서 Interim/Final 원문, Context Mapping, Adjustment, Result Run, raw record를 확인합니다.
6. **Learning Pipeline**에서 Worker 또는 `POST /api/learning/process-pending`으로 Batch/Candidate를 만들고 diff/evaluation을 검토합니다.
7. Candidate를 승인하면 새 Memory/Skill Version이 활성화됩니다. 이후 새 Run만 새 snapshot을 사용합니다. 거절은 Asset을 변경하지 않습니다.

Local에서 Worker 한 cycle을 직접 확인하려면:

```bash
curl --fail -X POST http://localhost:8000/api/learning/process-pending
curl --fail http://localhost:8000/api/learning/batches
curl --fail http://localhost:8000/api/learning/candidates
```

`process-pending`은 대기 Feedback을 분류·평가하고 Candidate를 만드는 검증/관리 endpoint입니다. Candidate 승인, Asset 활성화, Main Run 재실행은 수행하지 않으며 재호출해도 중복 Candidate를 만들지 않아야 합니다.

## Operational Notes

- API와 Worker는 동일 Python package, SQLAlchemy model/repository/config/logging을 사용하지만 Process는 분리됩니다.
- MySQL isolation level은 `READ COMMITTED`이며 Feedback 선점은 InnoDB `FOR UPDATE SKIP LOCKED`를 사용합니다.
- Final Feedback unique guard와 active Asset unique guard는 MySQL Generated Column + Unique Index로 강제됩니다.
- Version Conflict가 발생하면 Candidate와 active Asset을 포함한 승인 transaction 전체가 rollback되고 HTTP 409가 반환됩니다.
- Worker는 SIGTERM/SIGINT를 받으면 현재 짧은 cycle 경계를 마친 뒤 종료합니다. Container log에서 startup, polling, retry, shutdown 상태를 확인할 수 있습니다.

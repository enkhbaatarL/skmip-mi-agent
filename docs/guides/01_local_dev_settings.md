# Local 개발 세팅
## 목적

- VSCode  / Cursor 사용자를 위해 로컬 개발환경 세팅 가이드 작성
- 협업을 위해 가급적 모두가 동일한 로컬 개발 환경을 가질 수 있도록 세팅하고, 사용법을 여기에 작성해주세요

## 0. Cusror / Visual Studio Code 유용한 설정
### 0.1 Cursor
- Vertical Sidebar 설정하기
    > VS Code에 익숙한 사람이라면 세로방향의 Sidebar가 익숙해서 동일하게 세팅하는것이 좋습니다.
    - Preference > VS Code Settings > Workbench › Activity Bar: Orientation 에 가서 Vertical로 선택해주시면 됩니다.

### 0.2 VS Code
- TBD
## 1. Task 설정
### Task 란?
### Task Manager Extension 설치하기
- Market Place > Task 검색
- Task Explorer 또는 Task Manager 설치
- Side Bar에서 Launcher(Run and Debug) 선택하면 Explorer 섹션에 Task 가 있는것을 확인. 
- 필요시 Task 섹션을 Side Bar로 드래그해서 바로가기 만들기

## 2. Local MySQL DB + Flyway(Migration)

### 2.1 Flyway란?
- Flyway는 DB 스키마 변경(DDL)과 초기 데이터(Seed)를 버전 기반 SQL 파일로 관리하는 마이그레이션 도구입니다.
- `scripts/sql` 아래의 `V000__...sql`, `V001__...sql` 같은 파일을 버전 순서대로 실행합니다.
- 실행 이력은 `flyway_schema_history` 테이블에 저장되어, 이미 적용한 버전은 중복 실행하지 않습니다.
- 로컬/개발/운영 환경에서 동일한 순서로 스키마를 맞출 수 있어 협업 시 스키마 불일치를 줄여줍니다.

### 2.2 Task 설명 (`.vscode/tasks.json`)
- `Run FastAPI`
  - `python ${workspaceFolder}/simple_graph/graph.py` 실행
  - 로컬 FastAPI(또는 그래프 실행 스크립트) 구동용

- `compose-down-delete-volumes`
  - `docker compose -f docker/local/midb-docker-compose.yml down -v`
  - 컨테이너/네트워크/볼륨을 모두 삭제
  - MySQL 데이터까지 초기화할 때 사용

- `compose-down`
  - `docker compose -f docker/local/midb-docker-compose.yml down`
  - 컨테이너/네트워크만 내림
  - 볼륨은 유지되므로 MySQL 데이터 보존

- `compose-up-mysql`
  - `docker compose -f docker/local/midb-docker-compose.yml up -d mysql`
  - MySQL 컨테이너를 백그라운드로 기동

- `compose-run-flyway`
  - `docker compose -f docker/local/midb-docker-compose.yml run --rm flyway`
  - Flyway 마이그레이션 실행 후 컨테이너 자동 삭제
  - `V000`부터 순서대로 SQL 반영

### 2.3 권장 실행 순서
1. `compose-up-mysql`
2. `compose-run-flyway`
3. `Run FastAPI`

### 2.4 중요 운영 규칙 (SQL 변경 시)
- `scripts/sql` 아래에 SQL 파일을 추가하거나 기존 SQL을 수정한 경우, 앱 실행 전에 반드시 `compose-run-flyway`를 1회 실행해야 합니다.
- 이유: 앱이 참조하는 최신 테이블/컬럼/시드 데이터가 DB에 반영되지 않으면 실행 중 오류가 발생할 수 있습니다.
- 권장 순서:
  1. `compose-up-mysql`
  2. `compose-run-flyway`
  3. `Run FastAPI` (TBD)

필요 시 전체 초기화 후 재구축:
1. `compose-down-delete-volumes`
2. `compose-up-mysql`
3. `compose-run-flyway`
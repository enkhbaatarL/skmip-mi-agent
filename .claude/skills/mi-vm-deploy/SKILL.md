---
name: mi-vm-deploy
description: MI agent 이미지를 로컬 repo에서 빌드해 skmidemoacr.azurecr.io에 push하고, 외부 데모 VM(40.82.137.178)의 Docker Compose .env IMAGE를 해당 태그로 변경한 뒤 app 서비스를 pull/recreate 하는 배포 작업에 사용. scenario, model-parameter, interpret agent를 지원한다. "scenario agent v0.0.16 빌드 후 외부 VM 배포", "model-parameter agent 이미지 push하고 demo vm compose 재시작", "interpret agent v0.0.2 외부 VM 배포", "외부 VM mi-agent-interpret 이미지 변경/재시작" 류 요청에 사용.
---

# MI VM Deploy

로컬 repo에서 MI agent 이미지를 빌드하고, 외부 ACR에 push한 뒤 외부 데모 VM의 Docker Compose 서비스를 새 이미지로 재생성한다.

## 고정값

- 기본 agent: `scenario`
- scenario 이미지 repo: `skmidemoacr.azurecr.io/mi-agent-scenario`
- scenario Dockerfile: `Dockerfile`
- scenario compose 경로: `/home/azureuser/mi/mi-agent-scenario`
- model-parameter 이미지 repo: `skmidemoacr.azurecr.io/mi-agent-model-parameter`
- model-parameter Dockerfile: `Dockerfile.model_param`
- model-parameter compose 경로: `/home/azureuser/mi/mi-agent-model-parameter`
- interpret 이미지 repo: `skmidemoacr.azurecr.io/mi-agent-interpret`
- interpret Dockerfile: `Dockerfile_interpret`
- interpret compose 경로: `/home/azureuser/mi/mi-agent-interpret`
- interpret 외부 port: `8003`
- 기본 platform: `linux/amd64`
- 외부 VM host: `40.82.137.178`
- 외부 VM user: `azureuser`
- 기본 PEM: `/Users/messiah/sk-mi-demo-vm-key.pem`
- 로컬 PEM 설정 파일: `.claude/skills/mi-vm-deploy/.local` (git ignore 대상)
- compose service: `app`

PEM 경로 우선순위는 `--pem <path>` > `MI_DEMO_VM_PEM` > `.claude/skills/mi-vm-deploy/.local` > 기본 PEM 순서다.
기본 PEM 파일과 `.local` 설정이 모두 없으면 임의 경로를 추측하지 말고 사용자에게 PEM 파일 경로를 먼저 요청한다.
사용자가 개인 PEM 경로를 주고 다음에도 쓰길 원하면 `.local`에 `PEM=/path/to/key.pem` 형식으로 저장한다.

## 입력

- `AGENT`: 배포 대상. `scenario`, `model-parameter`, `interpret`. 사용자가 명시하지 않으면 `scenario`로 처리한다.
- `VERSION`: 배포 이미지 태그. 예: `v0.0.16`
- `0.0.16`처럼 `v` 없이 들어온 버전은 script가 `v0.0.16`으로 정규화한다.
- 사용자가 태그를 지정하지 않으면 빌드/배포를 진행하지 말고 태그를 먼저 확인한다.

## 실행

모든 명령은 repo 루트에서 실행한다.

```bash
cd "$(git rev-parse --show-toplevel)"
```

### 빌드, push, 외부 VM compose 배포

Scenario agent:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh build-push-deploy v0.0.16
```

Model-parameter agent:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --agent model-parameter build-push-deploy v0.0.16
```

Interpret agent:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --agent interpret build-push-deploy v0.0.16
```

스크립트가 수행하는 작업:

```bash
docker build --platform linux/amd64 --pull -f Dockerfile \
  -t skmidemoacr.azurecr.io/mi-agent-scenario:v0.0.16 .

docker push skmidemoacr.azurecr.io/mi-agent-scenario:v0.0.16

ssh -i /Users/messiah/sk-mi-demo-vm-key.pem azureuser@40.82.137.178 'bash -s'
# remote:
cd /home/azureuser/mi/mi-agent-scenario
perl -0pi -e 's#^IMAGE=.*#IMAGE=skmidemoacr.azurecr.io/mi-agent-scenario:v0.0.16#m' .env
docker compose --progress plain pull app
docker compose --progress plain up -d --force-recreate app
docker compose ps
docker compose logs --tail=120 app
```

`--agent model-parameter`일 때는 아래 값으로 같은 절차를 수행한다.

```bash
docker build --platform linux/amd64 --pull -f Dockerfile.model_param \
  -t skmidemoacr.azurecr.io/mi-agent-model-parameter:v0.0.16 .

docker push skmidemoacr.azurecr.io/mi-agent-model-parameter:v0.0.16

ssh -i /Users/messiah/sk-mi-demo-vm-key.pem azureuser@40.82.137.178 'bash -s'
# remote:
cd /home/azureuser/mi/mi-agent-model-parameter
perl -0pi -e 's#^IMAGE=.*#IMAGE=skmidemoacr.azurecr.io/mi-agent-model-parameter:v0.0.16#m' .env
docker compose --progress plain pull app
docker compose --progress plain up -d --force-recreate app
docker compose ps
docker compose logs --tail=120 app
```

`--agent interpret`일 때는 아래 값으로 같은 절차를 수행한다.

```bash
docker build --platform linux/amd64 --pull -f Dockerfile_interpret \
  -t skmidemoacr.azurecr.io/mi-agent-interpret:v0.0.16 .

docker push skmidemoacr.azurecr.io/mi-agent-interpret:v0.0.16

ssh -i /Users/messiah/sk-mi-demo-vm-key.pem azureuser@40.82.137.178 'bash -s'
# remote:
cd /home/azureuser/mi/mi-agent-interpret
perl -0pi -e 's#^IMAGE=.*#IMAGE=skmidemoacr.azurecr.io/mi-agent-interpret:v0.0.16#m' .env
docker compose --progress plain pull app
docker compose --progress plain up -d --force-recreate app
docker compose ps
docker compose logs --tail=120 app
```

PEM 경로를 따로 받아야 할 때:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --pem /path/to/key.pem build-push-deploy v0.0.16
```

개인 PEM 경로를 로컬에 저장할 때:

```bash
printf 'PEM=/path/to/key.pem\n' > .claude/skills/mi-vm-deploy/.local
```

실제 실행 전 명령만 확인할 때:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --dry-run --agent model-parameter build-push-deploy v0.0.16
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --dry-run --agent interpret build-push-deploy v0.0.16
```

### 분리 실행

이미지 빌드와 push만 수행:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh build-push v0.0.16
```

이미 push된 이미지를 외부 VM에만 반영:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh deploy v0.0.16
```

Model-parameter agent 대상 분리 실행:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --agent model-parameter build-push v0.0.16
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --agent model-parameter deploy v0.0.16
```

Interpret agent 대상 분리 실행:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --agent interpret build-push v0.0.16
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --agent interpret deploy v0.0.16
```

상태와 로그 확인:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh status
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh logs 120
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh --agent model-parameter status
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh --agent model-parameter logs 120
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh --agent interpret status
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh --agent interpret logs 120
```

## 옵션

- `--agent <scenario|model-parameter|interpret>`: 배포 대상 agent 선택. 기본값은 `scenario`
- `--dockerfile <path>`: 기본 `Dockerfile` 대신 다른 Dockerfile 사용
- `--platform <platform>`: 기본 `linux/amd64` 대신 다른 platform 사용
- `--image-repo <repo>`: agent별 기본 ACR repo 대신 다른 repo 사용. 사용자가 명시하지 않으면 바꾸지 않는다.
- `--no-cache`: docker build에 `--no-cache` 추가
- `--no-pull`: 기본 `--pull`을 끈다
- `--pem <path>`: SSH PEM 경로 지정
- `--dry-run`: 명령 출력만 수행

## 보고 항목

완료 후 사용자에게 아래를 간결히 보고한다.

- 대상 agent: `scenario`, `model-parameter`, `interpret`
- 빌드/push한 최종 이미지
- docker image inspect 결과의 OS/Architecture
- 외부 VM `.env`의 최종 `IMAGE`
- `docker compose ps`의 image/status/ports
- 로그에서 `Application startup complete` 확인 여부 또는 에러 요약

## 안전 규칙

- 이 skill은 외부 데모 VM의 `/home/azureuser/mi/mi-agent-scenario`, `/home/azureuser/mi/mi-agent-model-parameter`, `/home/azureuser/mi/mi-agent-interpret` compose 프로젝트만 변경한다.
- Docker registry 비밀번호, PEM 파일 내용, `.env`의 민감값은 출력하지 않는다.
- `deploy`와 `build-push-deploy`는 원격 `.env` 수정과 컨테이너 재생성을 수행하므로, 사용자가 배포 또는 이미지 변경/재시작을 요청했을 때만 실행한다.
- `docker push`가 실패하면 원격 compose 배포를 진행하지 않는다.
- 작업트리에 미커밋 변경이 있어도 이미지는 현재 로컬 파일 상태로 빌드된다. 이 점을 사용자에게 명확히 보고한다.

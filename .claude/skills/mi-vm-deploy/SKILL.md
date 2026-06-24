---
name: mi-vm-deploy
description: MI scenario agent 이미지를 로컬 repo에서 빌드해 skmidemoacr.azurecr.io/mi-agent-scenario:tag 형식으로 push하고, 외부 데모 VM(40.82.137.178)의 /home/azureuser/mi/mi-agent-scenario Docker Compose .env IMAGE를 해당 태그로 변경한 뒤 app 서비스를 pull/recreate 하는 배포 작업에 사용. "scenario agent v0.0.16 빌드 후 외부 VM 배포", "mi-agent-scenario 이미지 push하고 demo vm compose 재시작", "외부 VM scenario agent 이미지 변경/재시작" 류 요청에 사용.
---

# MI VM Deploy

로컬 repo의 `Dockerfile`로 scenario agent 이미지를 빌드하고, 외부 ACR에 push한 뒤 외부 데모 VM의 Docker Compose 서비스를 새 이미지로 재생성한다.

## 고정값

- 이미지 repo: `skmidemoacr.azurecr.io/mi-agent-scenario`
- 기본 Dockerfile: `Dockerfile`
- 기본 platform: `linux/amd64`
- 외부 VM host: `40.82.137.178`
- 외부 VM user: `azureuser`
- 기본 PEM: `/Users/messiah/sk-mi-demo-vm-key.pem`
- compose 경로: `/home/azureuser/mi/mi-agent-scenario`
- compose service: `app`

기본 PEM 파일이 없으면 임의 경로를 추측하지 말고 사용자에게 PEM 파일 경로를 먼저 요청한다. 사용자가 경로를 주면 `--pem <path>` 또는 `MI_DEMO_VM_PEM=<path>`로 전달한다.

## 입력

- `VERSION`: 배포 이미지 태그. 예: `v0.0.16`
- `0.0.16`처럼 `v` 없이 들어온 버전은 script가 `v0.0.16`으로 정규화한다.
- 사용자가 태그를 지정하지 않으면 빌드/배포를 진행하지 말고 태그를 먼저 확인한다.

## 실행

모든 명령은 repo 루트에서 실행한다.

```bash
cd "$(git rev-parse --show-toplevel)"
```

### 빌드, push, 외부 VM compose 배포

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh build-push-deploy v0.0.16
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

PEM 경로를 따로 받아야 할 때:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --pem /path/to/key.pem build-push-deploy v0.0.16
```

실제 실행 전 명령만 확인할 때:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh \
  --dry-run build-push-deploy v0.0.16
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

상태와 로그 확인:

```bash
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh status
.claude/skills/mi-vm-deploy/scripts/build_push_deploy.sh logs 120
```

## 옵션

- `--dockerfile <path>`: 기본 `Dockerfile` 대신 다른 Dockerfile 사용
- `--platform <platform>`: 기본 `linux/amd64` 대신 다른 platform 사용
- `--image-repo <repo>`: 기본 ACR repo 대신 다른 repo 사용. 사용자가 명시하지 않으면 바꾸지 않는다.
- `--no-cache`: docker build에 `--no-cache` 추가
- `--no-pull`: 기본 `--pull`을 끈다
- `--pem <path>`: SSH PEM 경로 지정
- `--dry-run`: 명령 출력만 수행

## 보고 항목

완료 후 사용자에게 아래를 간결히 보고한다.

- 빌드/push한 최종 이미지: `skmidemoacr.azurecr.io/mi-agent-scenario:<tag>`
- docker image inspect 결과의 OS/Architecture
- 외부 VM `.env`의 최종 `IMAGE`
- `docker compose ps`의 image/status/ports
- 로그에서 `Application startup complete` 확인 여부 또는 에러 요약

## 안전 규칙

- 이 skill은 외부 데모 VM의 `/home/azureuser/mi/mi-agent-scenario` compose 프로젝트만 변경한다.
- Docker registry 비밀번호, PEM 파일 내용, `.env`의 민감값은 출력하지 않는다.
- `deploy`와 `build-push-deploy`는 원격 `.env` 수정과 컨테이너 재생성을 수행하므로, 사용자가 배포 또는 이미지 변경/재시작을 요청했을 때만 실행한다.
- `docker push`가 실패하면 원격 compose 배포를 진행하지 않는다.
- 작업트리에 미커밋 변경이 있어도 이미지는 현재 로컬 파일 상태로 빌드된다. 이 점을 사용자에게 명확히 보고한다.

---
name: mi-image-banib
description: 내부 반입용 컨테이너 이미지를 빌드하거나 외부 이미지를 받아 tar.gz/zip 번들로 만들고, 직접 빌드 시 외부 ACR에도 push하며, 내부망에서 docker load → registry push → deployment 변경으로 적용하는 절차를 안내한다. "v0.0.2 반입이미지 생성해줘", "반입 이미지 빌드", "반입 번들 만들어줘", "내부 클러스터 반입/배포" 류 요청에 사용. (DB 마이그레이션은 이 스킬 범위에 포함하지 않음)
---

# 반입 이미지 생성 · 반입 · 적용

> **작업 디렉토리**: 모든 명령은 repo 루트에서 실행한다.
> ```bash
> cd "$(git rev-parse --show-toplevel)"
> ```

내부망(air-gapped) 또는 반입 대상 클러스터에 올릴 이미지를 **외부에서 빌드 또는 pull → 내부 registry 명으로 준비 → tar.gz → zip 번들**로 만들고,
**파일전송시스템으로 techvdi 반입 → (압축 해제) hiware sftp 로 내부 bastion 전송**한 뒤,
bastion 에서 `docker load` → registry push → deployment 변경으로 적용한다.
v0.0.1 에서 검증된 절차를 그대로 따른다(버전만 치환).

## 스킬 동작 범위 (중요)
- **에이전트가 실제로 수행하는 것은 "A. 반입 파일 생성"(빌드/외부 이미지 pull → 필요 시 외부 ACR push → tar.gz → zip 번들)까지다.**
- 그 이후 — **B. 반입(techvdi 반입 → 압축 해제 → hiware sftp 로 bastion 전송)**,
  **C. bastion 에서 내부망 적용(load·push·deployment 변경)** — 은 폐쇄망/수작업 영역이므로
  **에이전트가 실행하지 않고, 사용자에게 절차를 안내(가이드)** 한다.
- 따라서 산출물(`*.bundle.zip`)을 만들고 sha256·경로를 보고한 뒤, B·C 단계는 아래 절차를
  그대로 안내하며 마무리한다.
- **금지: 반입 파일 생성(A) 과정에서 repo 의 `devops/k8s/deployment.yaml`(및 기타 k8s 매니페스트)를
  수정하지 않는다.** 이미지 태그 교체·deployment 변경은 배포(7단계)에서 **사용자가 직접** 하는 일이므로,
  에이전트는 빌드·직접 빌드 시 외부 ACR push·`docker save`·zip 번들 산출물 생성만 수행하고 매니페스트는 건드리지 않는다.
- **중요: `docker save` 대상 이미지는 항상 내부 registry 에 push 할 최종 이미지명이어야 한다.**
  그래야 내부 bastion 에서 `docker load` 후 `docker tag` 없이 바로 `docker push` 할 수 있다.
- **기본 최종 이미지 repo 는 `skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario` 로 고정한다.**
  예: `skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario:v0.0.15`
- **직접 빌드 방식에서는 같은 이미지를 `skmidemoacr.azurecr.io/mi-agent-scenario:<VERSION>` 로도 태그하고 push 한다.**

## 입력
- `VERSION` — 반입 버전 태그. 예: `v0.0.2` ("v0.0.2 반입이미지 생성해줘")
- `TARGET_IMAGE_REPO` — 내부 registry push 용 최종 이미지 repo. 기본값은 아래 값으로 고정한다.
  `skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario`
- `PUBLIC_IMAGE_REPO` — 직접 빌드 시 외부 ACR 에 push 할 이미지 repo. 기본값은 아래 값으로 고정한다.
  `skmidemoacr.azurecr.io/mi-agent-scenario`
- `SOURCE_IMAGE` — 이미 외부 registry 에 올라간 이미지를 받아 반입할 때의 원본 이미지.
  예: `skmidemoacr.azurecr.io/mi-agent-scenario:<VERSION>`
- 기본 값:
  - 최종 내부 registry 이미지: `skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario:<VERSION>`
  - 직접 빌드 후 외부 ACR 이미지: `skmidemoacr.azurecr.io/mi-agent-scenario:<VERSION>`
  - 원본 이미지: `${SOURCE_IMAGE:-skmidemoacr.azurecr.io/mi-agent-scenario:<VERSION>}`
  - 로컬 확인용 이미지: `skmip-mi-agent:<VERSION>`
  - 산출물 파일명: `skmip-mi-agent_<VERSION>_linux-amd64.tar.gz` / `...bundle.zip`
  - 배포 namespace: 대상 클러스터/환경 기준으로 사용자가 확인한다(`devops/k8s/deployment.yaml`에는 namespace가 고정되어 있지 않음).
- 사용자가 명시적으로 다른 내부 registry 를 요청하지 않으면 `TARGET_IMAGE_REPO` 를 바꾸지 않는다.
- **외부 이미지 pull 방식으로 반입할 때도 tar.gz 내부 태그는 `SOURCE_IMAGE` 가 아니라
  `TARGET_IMAGE_REPO:<VERSION>` 이 되도록 외부 작업 단계에서 먼저 맞춘다.**
- 빌드 대상 아키텍처는 **linux/amd64** (내부 클러스터 노드 기준). 빌드 머신이 arm64(Mac)여도 `--platform linux/amd64` 로 강제.

---

## A. 외부 — 이미지 준비 & 번들 생성  ← ★ 에이전트가 실제 수행

### 1-1. 이미지 빌드 방식 (linux/amd64, 내부 registry 명으로 생성 + 외부 ACR push)
```bash
TARGET_IMAGE_REPO="skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario"
PUBLIC_IMAGE_REPO="skmidemoacr.azurecr.io/mi-agent-scenario"
docker build --platform linux/amd64 --no-cache --pull \
  -t "${TARGET_IMAGE_REPO}:<VERSION>" \
  -t "${PUBLIC_IMAGE_REPO}:<VERSION>" \
  -t skmip-mi-agent:<VERSION> \
  .

docker push "${PUBLIC_IMAGE_REPO}:<VERSION>"
```
- `--platform linux/amd64`: 내부 클러스터 노드용 amd64 이미지
- **`--no-cache`**: 동일 태그·캐시가 이미 있어도 **레이어를 재사용하지 않고 항상 새로 빌드**한다.
- **`--pull`**: base 이미지(`python:3.12-slim-bookworm`)도 최신으로 다시 받아 fresh 하게 빌드한다.
- 첫 번째 태그: 내부 registry push 용 최종 이미지명. 내부 bastion 에서 별도 `docker tag` 없이 push 할 이름이다.
- 두 번째 태그: 외부 ACR 저장용 이미지명. 직접 빌드한 경우에만 외부 ACR 에 push 한다.
- 세 번째 태그: 로컬 확인용 짧은 이미지명
- `.`: 현재 repo 의 `Dockerfile` 기준 빌드
- 외부 ACR push 권한이 없거나 `docker push` 가 실패하면 실패 사유를 보고하고, 반입 번들 생성은 진행하지 않는다.

### 1-2. 외부 registry 의 기존 이미지를 받아 반입하는 방식
```bash
SOURCE_IMAGE="${SOURCE_IMAGE:-skmidemoacr.azurecr.io/mi-agent-scenario:<VERSION>}"
TARGET_IMAGE_REPO="skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario"

docker pull --platform linux/amd64 "${SOURCE_IMAGE}"
docker tag "${SOURCE_IMAGE}" "${TARGET_IMAGE_REPO}:<VERSION>"
docker image inspect "${TARGET_IMAGE_REPO}:<VERSION>" \
  --format '{{.Id}} {{.Os}}/{{.Architecture}} {{index .RepoTags 0}}'
```
- 원본 이미지를 그대로 반입하더라도, **외부에서 저장 전에 내부 registry 명으로 태그를 맞춘 뒤**
  `${TARGET_IMAGE_REPO}:<VERSION>` 을 `docker save` 한다.
- 이 `docker tag` 는 외부 번들 생성 단계에서만 수행한다. 내부 bastion 에서는 `docker tag` 를 하지 않는다.
- inspect 결과가 `linux/amd64` 인지 확인한다.

### 2. 반입용 tar.gz 생성 + 무결성 확인
```bash
TARGET_IMAGE_REPO="skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario"
rm -f skmip-mi-agent_<VERSION>_linux-amd64.tar.gz
docker save "${TARGET_IMAGE_REPO}:<VERSION>" \
  | gzip -c > skmip-mi-agent_<VERSION>_linux-amd64.tar.gz

gzip -t skmip-mi-agent_<VERSION>_linux-amd64.tar.gz          # gzip 무결성
shasum -a 256 skmip-mi-agent_<VERSION>_linux-amd64.tar.gz    # sha256 기록(반입 검증용)
ls -lh skmip-mi-agent_<VERSION>_linux-amd64.tar.gz           # 크기 확인
```
- `docker save` 출력은 내부 `docker load` 와 짝이 맞는다.
- tar.gz 안의 image repo/tag 는 `${TARGET_IMAGE_REPO}:<VERSION>` 이므로 내부에서 재태그할 필요가 없다.
- 출력된 **sha256 / 크기는 따로 기록**해 반입 후 동일성 확인에 쓴다.

### 3. zip 번들로 한 번 더 묶기
```bash
rm -f skmip-mi-agent_<VERSION>_linux-amd64.bundle.zip
zip -9 skmip-mi-agent_<VERSION>_linux-amd64.bundle.zip \
  skmip-mi-agent_<VERSION>_linux-amd64.tar.gz

unzip -l skmip-mi-agent_<VERSION>_linux-amd64.bundle.zip      # 내용 확인(tar.gz 1개)
```
- 번들 안에는 **tar.gz 단독**만 넣는다(매니페스트/스크립트 미포함).
- 이 `*.bundle.zip` 을 반입 시스템으로 반입한다.

> 산출물(`*.tar.gz`, `*.bundle.zip`)은 용량이 크다(100MB+). git 에 커밋하지 않는다.

---

## B. 반입 — 파일전송시스템으로 techvdi 반입  ← 이하 사용자 수행, 에이전트는 안내만

### 4. 파일전송시스템으로 techvdi 반입 → 압축 해제 → bastion 전송
1. 외부에서 생성한 `skmip-mi-agent_<VERSION>_linux-amd64.bundle.zip` 을 **파일전송시스템**(반입 결재/전송)
   을 통해 내부망 **techvdi** 로 반입한다.
2. techvdi 에서 **zip 압축을 해제**해 `tar.gz` 를 꺼낸다.
   ```bash
   unzip skmip-mi-agent_<VERSION>_linux-amd64.bundle.zip   # → skmip-mi-agent_<VERSION>_linux-amd64.tar.gz
   ```
3. 꺼낸 `tar.gz` 를 **hiware sftp** 로 내부 **bastion 서버**로 전송한다.
   (이후 load 부터는 bastion 에서 수행하므로 tar.gz 만 bastion 으로 옮긴다)
4. 전송 후 bastion 에서 sha256 을 계산해 외부에서 기록한 값과 **동일한지 확인**한다.
   ```bash
   shasum -a 256 skmip-mi-agent_<VERSION>_linux-amd64.tar.gz
   ```

## C. 내부망 적용 — load · push · 배포  ← bastion 서버에서 사용자 수행, 에이전트는 안내만

> 4단계에서 tar.gz 를 전송받은 **내부 bastion 서버**에서 수행. registry push 권한과
> `kubectl` 컨텍스트가 필요하다.

### 5. 이미지 load (bastion)
```bash
gunzip -c skmip-mi-agent_<VERSION>_linux-amd64.tar.gz | docker load
```
- load 후 `docker images | grep -E 'mi-agent-scenario|skmip-mi-agent'` 로
  `${TARGET_IMAGE_REPO}:<VERSION>` 태그가 보이는지 확인한다.
- (선택) 4단계의 sha256 과 비교해 동일 이미지인지 검증.

### 6. 내부 registry 에 바로 push
```bash
TARGET_IMAGE_REPO="skpc-registry.skpc.cloudzcp.net/mi-platform-dev/dev/mi-agent-scenario"
docker push "${TARGET_IMAGE_REPO}:<VERSION>"
```
- 별도 `docker tag` 는 수행하지 않는다. tar.gz 생성 시점에 이미 내부 registry 명으로 저장했기 때문이다.
- k8s 가 이 registry 에서 이미지를 pull 한다.

### 7. deployment 변경 (배포) — 사용자가 직접 수행
- 대상 namespace 의 deployment 가 push 한 이미지(`...:<VERSION>`)를 바라보도록
  **deployment 를 변경**한다(이미지 태그 교체 등).
- 배포 후 롤아웃이 정상 기동(`/health` readiness/liveness)했는지 확인한다.

---

## 범위 밖 (포함하지 않음)
- **DB 스키마/시드 마이그레이션은 이 절차에 포함하지 않는다.**

## 관련 파일
- `Dockerfile` — 이미지 빌드 정의(python:3.12-slim-bookworm, gunicorn `main:app` :8000)
- `devops/k8s/` — deployment/service/configmap/secret (image=`skmip-mi-agent:local` 기본 예시)

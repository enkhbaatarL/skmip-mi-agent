---
name: main-mr
description: MR 메시지를 생성하고 main 브랜치로의 MR/PR 요청까지 준비합니다. "MR 메세지", "MR 메시지", "release note", "릴리즈", "배포 준비" 요청 시 사용. main merge 이후 소스/이미지 반입 산출물은 mi-source-banib, mi-image-banib 스킬로 진행합니다.
---

# Main MR 준비

릴리즈 전 변경 내용을 정리해 main 브랜치로 MR/PR을 요청하는 단계까지만 수행한다.
main merge 이후의 tag, source bundle, image bundle 생성은 이 스킬에서 수행하지 않고 아래 스킬로 분리한다.

- 소스 반입 산출물: `mi-source-banib`
- 이미지 반입 산출물: `mi-image-banib`

## 현재 브랜치 정보

- 브랜치: !`git rev-parse --abbrev-ref HEAD`
- 최근 태그: !`git tag -l --sort=-v:refname | head -5`

## main 이후 커밋 목록

!`git log origin/main..HEAD --pretty=format:"%s%n%b" --no-merges 2>/dev/null || git log main..HEAD --pretty=format:"%s%n%b" --no-merges 2>/dev/null`

## main 이후 변경 파일 목록

!`git diff --name-only origin/main...HEAD 2>/dev/null || git diff --name-only main...HEAD 2>/dev/null`

---

## 범위

Codex가 수행:
- main 이후 커밋을 분석해 한국어 MR 메시지 생성
- 사용자가 요청하면 main 대상 MR/PR 생성 또는 생성 명령 안내
- main merge 이후 실행할 후속 스킬 안내

Codex가 수행하지 않음:
- Git tag 생성
- GitHub Release 생성
- Docker build/push
- 내부망 반입용 source/image bundle 생성

## Step 1: MR 메시지 생성

위 커밋과 변경 파일을 함께 분석해서 아래 포맷으로 **한국어** MR 메시지를 작성한다.

변경 파일 -> 범위 매핑:
- `apps/agents/<agent_directory>/...` -> `<agent_directory>`
- 위 경로 밖의 모든 파일 -> `common`

커밋이 여러 범위를 건드리면 경로별 변경 내용을 분석해 각 범위에 맞는 불릿으로 나눈다. 같은 포괄 문구를 여러 범위에 그대로 복제하지 말고, 각 범위에 해당하는 변경을 구체적으로 적는다.

커밋 prefix -> 섹션 매핑:
- `feat:` / `feature:` -> **Feature**
- `refact:` / `refactor:` -> **Refactor**
- `fix:` / `bugfix:` -> **BugFix**
- `chore:` / `ops:` / `ci:` / `build:` / `infra:` / `docs:` -> **Ops**

**출력 포맷 (반드시 이 형식 그대로):**

```text
# <제목: 전체 변경 내용을 한 줄로 요약>

## scenario_group_agent

### Feature
- ...

### Refactor
- 없음

### BugFix
- ...

### Ops
- ...

## common

### Feature
- 없음

### Refactor
- ...

### BugFix
- 없음

### Ops
- ...
```

규칙:
- agent 범위는 `apps/agents` 바로 아래의 실제 Python 패키지 디렉터리명을 그대로 사용한다. `__pycache__`와 같은 생성 디렉터리는 제외한다.
- 변경된 agent 범위와 `common`만 출력한다.
- 범위 순서는 agent 디렉터리명 오름차순, `common` 마지막으로 고정한다.
- 각 범위의 하위 섹션 순서는 Feature -> Refactor -> BugFix -> Ops로 고정한다.
- 출력된 범위 안의 빈 하위 섹션은 `- 없음`으로 표시하고 섹션을 삭제하지 말라.
- Ops는 변경 유형이며 `common` 전용이 아니다. agent 내부의 CI, Docker, 설정, 문서 변경은 해당 agent의 Ops에, 프로젝트 전역 변경은 `common` Ops에 넣는다.
- 불릿은 `- ` 형식
- 사용자 요청 없이 추가 섹션 금지
- 내용은 간결하게 작성

## Step 2: main 대상 MR/PR 여부 확인

MR 메시지 작성 후, 사용자에게 묻는다.

```text
이 변경은 main 브랜치로 MR/PR을 요청할까요?
```

- 아니면 MR 메시지만 제공하고 종료한다.
- 맞으면 main 대상 MR/PR 생성 또는 생성 명령 안내를 진행한다.

## Step 3: main 대상 MR/PR 생성

가능하면 현재 원격/플랫폼에 맞는 CLI 또는 GitHub/GitLab 도구로 main 대상 MR/PR을 생성한다.
도구 접근이나 인증이 없으면 아래 정보를 사용자에게 명확히 안내한다.

```text
target/base: main
source/compare: <current-branch>
title: Step 1 제목
description: Step 1 MR 메시지 전체
merge method: 프로젝트 정책에 따름
```

## Step 4: main merge 이후 후속 작업 안내

MR/PR 생성 후에는 main merge가 완료된 다음 같은 버전 태그로 아래 순서의 스킬을 실행하도록 안내한다.

```text
1. mi-source-banib: origin/main 기준 tag 생성/push 및 source bundle 생성
2. mi-image-banib: 같은 tag 기준 image build/push 및 image bundle 생성
```

예:

```text
v0.0.18 태그 기준으로 소스 반입해줘
v0.0.18 반입이미지 생성해줘
```

주의:
- `main-mr` 스킬은 main merge 전 준비까지만 담당한다.
- tag와 image는 main merge 후 같은 tag commit 기준으로 생성되어야 한다.

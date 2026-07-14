---
name: mi-source-banib
description: main merge 이후 외부 GitHub main 기준으로 내부망 반입용 소스 release tag, 직전 tag 대비 release note markdown 및 GitHub Release, git bundle, bundle.zip, manifest를 생성하고, 내부 Git 서버에서 tag 반입, import 태그 브랜치, Pull Request로 develop에 반영하는 절차를 안내한다. "소스 반입파일 만들어줘", "GitHub tag를 내부 Git으로 반입", "mi-agent 소스 반입", "bundle zip 생성", "release note 생성", "GitHub Release 생성", "내부 PR 반입 절차" 류 요청에 사용.
---

# MI 소스 반입 bundle 생성

> 작업 디렉토리: 모든 명령은 repo 루트에서 실행한다.
> ```bash
> cd "$(git rev-parse --show-toplevel)"
> ```

외부 GitHub에서 개발한 소스를 내부 Git 서버로 반입하기 위한 `git bundle` zip을 만든다.
Codex가 실제로 수행하는 범위는 **외부 환경에서 반입 파일 생성까지**다.
내부망 반입 후 작업은 사용자가 내부 PC/Git UI에서 수행하므로, Codex는 절차를 안내한다.

## 범위

Codex가 수행:
- `origin/<base_branch>` 기준 annotated tag 생성
- GitHub tag push
- tag가 이미 로컬/원격에 있고 annotated tag object와 peeled commit이 모두 일치하면 기존 tag를 재사용해 bundle 재생성
- tag 기준 `git bundle` 생성
- bundle을 다시 zip으로 압축
- 직전 release tag와 현재 tag를 비교한 release note를 Codex/Claude가 작성
- release note markdown 파일 내용을 그대로 사용해 GitHub Release 생성 또는 갱신
- manifest에 commit, sha256, 파일명, release note 정보 기록
- 생성 파일 경로와 내부 반입 절차 보고

Codex가 수행하지 않음:
- 내부 Git 서버 접속
- 내부 PC에서 bundle fetch
- 내부 Pull Request 생성/merge
- 내부 `develop` 이력 강제 변경
- 내부 Git 인증 복구

## 입력

- `TAG`: 릴리즈 tag. 예: `v0.0.3`
- `BASE_BRANCH`: 외부 GitHub 기준 브랜치. 기본 `main`
- `TARGET_BRANCH`: 내부 PR target 브랜치. 기본 `develop`

TAG가 없으면 사용자에게 tag 값을 먼저 확인한다.
기본 기준은 `origin/main`이며, 로컬 미커밋 변경은 bundle에 포함하지 않는다.
이 스킬은 main merge 이후 실행하는 것이 원칙이다.

## Release 흐름 내 위치

1. `main-mr` 스킬로 main 대상 MR/PR을 생성한다.
2. main merge 완료 후 이 스킬을 실행해 같은 버전 tag와 source bundle을 생성한다.
3. 같은 tag로 `mi-image-banib`을 실행해 image bundle을 생성한다.

주의:
- source bundle과 image bundle은 같은 tag commit 기준이어야 한다.
- 이미 같은 commit을 가리키는 동일 tag object가 있으면 재사용한다.
- tag가 다른 commit을 가리키면 중단하고 사용자에게 확인한다.
- local tag와 remote tag가 같은 commit을 가리키더라도 tag object가 다르면 중단한다.
- lightweight tag는 사용하지 않는다. release tag는 annotated tag여야 한다.

## A. 외부 - 반입 파일 생성

먼저 직전 release tag와 현재 tag를 비교해 release note 초안을 작성한다.

```bash
TAG=v0.0.3
BASE_BRANCH=main
TARGET_COMMIT="$(git rev-parse "origin/${BASE_BRANCH}^{commit}")"
PREVIOUS_TAG="$(git tag --merged "$TARGET_COMMIT" --sort=-v:refname | grep -E '^v[0-9]+(\.[0-9]+){1,3}([-+][A-Za-z0-9._-]+)?$' | grep -F -x -v "$TAG" | head -n1 || true)"
git log "${PREVIOUS_TAG:+${PREVIOUS_TAG}..}${TARGET_COMMIT}" --no-merges --pretty=format:"%s%n%b"
if [[ -n "$PREVIOUS_TAG" ]]; then
  git diff --name-only "${PREVIOUS_TAG}..${TARGET_COMMIT}"
else
  git ls-tree -r --name-only "$TARGET_COMMIT"
fi
```

그 커밋 목록을 Codex/Claude가 분석해 아래 release note 포맷으로 markdown 파일을 만든다.
스크립트는 release note 내용을 생성하지 않고, `RELEASE_NOTES_SOURCE`로 받은 파일을 산출물과 GitHub Release 본문에 그대로 사용한다.

아래 bundled script를 실행한다.

```bash
RELEASE_NOTES_SOURCE=<작성한-release-notes.md> .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh <TAG> [BASE_BRANCH]
```

예:

```bash
RELEASE_NOTES_SOURCE=/tmp/skmip-mi-agent-v0.0.3.release-notes.md .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh v0.0.3
```

생성물:

```text
release-artifacts/
  skmip-mi-agent-v0.0.3.bundle
  skmip-mi-agent-v0.0.3.bundle.zip  # bundle + 내부 import sh + release note 포함
  skmip-mi-agent-v0.0.3.manifest.txt
  skmip-mi-agent-v0.0.3.release-notes.md
```

스크립트는 tag push 후 `RELEASE_NOTES_SOURCE` 파일을 `skmip-mi-agent-<tag>.release-notes.md`로 복사하고, 그 파일 내용을 그대로 GitHub Release 본문으로 사용한다.
이미 GitHub Release가 있으면 `gh release edit`으로 갱신하고, 없으면 `gh release create`로 생성한다.
반입 산출물만 만들고 GitHub Release를 건너뛰어야 하면 `SKIP_GITHUB_RELEASE=1`을 붙여 실행한다.

Release note는 직전 release tag와 현재 tag를 비교해 달라진 commit만 포함하도록 Codex/Claude가 작성한다.
포맷은 `main-mr`의 MR 메시지 포맷과 동일하게 유지한다.

변경 파일 -> 범위 매핑:
- `apps/agents/<agent_directory>/...` -> `<agent_directory>`
- 위 경로 밖의 모든 파일 -> `common`

커밋이 여러 범위를 건드리면 경로별 변경 내용을 분석해 각 범위에 맞는 불릿으로 나눈다. 같은 포괄 문구를 여러 범위에 그대로 복제하지 말라.

커밋 prefix -> 섹션 매핑:
- `feat:` / `feature:` -> **Feature**
- `refact:` / `refactor:` -> **Refactor**
- `fix:` / `bugfix:` -> **BugFix**
- `chore:` / `ops:` / `ci:` / `build:` / `infra:` / `docs:` -> **Ops**

**Release note 포맷 (반드시 이 형식 그대로):**

```text
# <제목: 이전 tag와 비교한 전체 변경 내용을 한 줄로 요약>

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
- 위 매핑에 없는 commit subject는 누락하지 않고 Ops에 포함한다.

사용자에게 보고할 항목:
- tag
- 기준 branch
- 기준 commit
- 직전 tag
- GitHub Release URL
- bundle zip 경로
- bundle zip sha256
- manifest 경로
- release note 경로
- 현재 작업트리에 미커밋 변경이 있어도 bundle에는 포함되지 않는다는 점

## B. 내부 - 사용자가 수행할 sh 절차 안내

내부 PC에서는 VSCode 터미널을 **Git Bash**로 열고, 내부 repo clone 폴더에서 실행하도록 안내한다.
zip 안에 `import_source_bundle.sh`가 함께 들어 있으므로 내부 repo에 최신 skill이 없어도 사용할 수 있다.

```bash
unzip skmip-mi-agent-v0.0.3.bundle.zip
git remote -v
git ls-remote origin

bash import_source_bundle.sh v0.0.3 skmip-mi-agent-v0.0.3.bundle develop
```

충돌이 나고 이번 반입은 GitHub tag 파일을 우선해야 한다면:

```bash
AUTO_RESOLVE_THEIRS=1 bash import_source_bundle.sh v0.0.3 skmip-mi-agent-v0.0.3.bundle develop
```

주의: 이미 충돌 상태로 멈춘 뒤에 다시 자동 해결을 실행하려면 먼저 `git merge --abort`로 이전 merge를 취소한다.

PR 생성:

```text
target/base: develop
source/compare: import/v0.0.3
merge method: Create merge commit
avoid: Squash, Rebase
```

PR merge 후 임시 브랜치를 삭제한다.

```bash
git push origin --delete import/v0.0.3
```

## 주의

- `git bundle`은 Git object를 포함하므로 원본 commit hash와 이력을 보존한다.
- `.zip`으로 소스파일만 압축하면 이력이 보존되지 않는다.
- 내부 PR 화면이 empty면 PR 방향을 확인한다. 올바른 방향은 `source=import/<tag>`, `target=develop`이다.
- 내부 `develop`에 실수로 직접 push한 경우, 원격 이력을 되돌리는 작업은 사용자 확인 없이 수행하지 않는다.

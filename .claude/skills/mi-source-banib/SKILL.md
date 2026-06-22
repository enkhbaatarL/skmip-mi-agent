---
name: mi-source-banib
description: 외부 GitHub main 기준으로 내부망 반입용 소스 release tag, git bundle, bundle.zip, manifest를 생성하고, 내부 Git 서버에서 tag 반입, import 태그 브랜치, Pull Request로 develop에 반영하는 절차를 안내한다. "소스 반입파일 만들어줘", "GitHub tag를 내부 Git으로 반입", "mi-agent 소스 반입", "bundle zip 생성", "내부 PR 반입 절차" 류 요청에 사용.
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
- tag 기준 `git bundle` 생성
- bundle을 다시 zip으로 압축
- manifest에 commit, sha256, 파일명 기록
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

## A. 외부 - 반입 파일 생성

아래 bundled script를 실행한다.

```bash
.claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh <TAG> [BASE_BRANCH]
```

예:

```bash
.claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh v0.0.3
```

생성물:

```text
release-artifacts/
  skmip-mi-agent-v0.0.3.bundle
  skmip-mi-agent-v0.0.3.bundle.zip  # bundle + 내부 import sh 포함
  skmip-mi-agent-v0.0.3.manifest.txt
```

사용자에게 보고할 항목:
- tag
- 기준 branch
- 기준 commit
- bundle zip 경로
- bundle zip sha256
- manifest 경로
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

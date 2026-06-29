---
name: release
description: MR 메시지 생성부터 Git tag, GitHub Release, Docker build & push까지 릴리즈 프로세스 전체를 진행합니다. "MR 메세지", "MR 메시지", "release note", "릴리즈", "배포 준비" 요청 시 사용.
---

## 현재 브랜치 정보

- 브랜치: !`git rev-parse --abbrev-ref HEAD`
- 최근 태그: !`git tag -l --sort=-v:refname | head -5`

## main 이후 커밋 목록

!`git log origin/main..HEAD --pretty=format:"%s%n%b" --no-merges 2>/dev/null || git log main..HEAD --pretty=format:"%s%n%b" --no-merges 2>/dev/null`

---

## 지침

### Step 1: MR 메시지 생성

위 커밋을 분석해서 아래 포맷으로 **한국어** MR 메시지를 작성한다.

커밋 prefix → 섹션 매핑:
- `feat:` / `feature:` → **Feature**
- `refact:` / `refactor:` → **Refactor**
- `fix:` / `bugfix:` → **BugFix**
- `chore:` / `ops:` / `ci:` / `build:` / `infra:` / `docs:` → **Ops**

**출력 포맷 (반드시 이 형식 그대로):**

```
# [Agent] <제목: 전체 변경 내용을 한 줄로 요약>

## Feature
- ...

## Refactor
- ...

## BugFix
- ...

## Ops
- ...

```

규칙:
- 섹션 순서: Feature → Refactor → BugFix → Ops 고정
- 빈 섹션은 `- 없음` 으로 표시 (섹션 자체를 삭제하지 말 것)
- 불릿은 `- ` 형식
- 사용자 요청 없이 추가 섹션 금지
- 내용은 간결하게 작성

### Step 2: main 브랜치 merge 여부 확인

MR 메시지 작성 후, `AskUserQuestion` 도구로 묻는다:

**"이 MR이 main 브랜치에 merge되는 경우인가요?"**
- 옵션 A: "예, main에 merge됩니다"
- 옵션 B: "아니요, develop에 merge됩니다"

사용자가 옵션 B 선택 → 종료.

### Step 3: main merge 후 작업 선택

`AskUserQuestion` 도구로 묻는다 (multiSelect 허용):

**"main merge 후 진행할 작업을 선택하세요."**
- 옵션 A: "Git tag & GitHub Release 생성"
- 옵션 B: "Docker build & push"
- 옵션 C: "작업 없음 (종료)"

"작업 없음"만 선택 또는 선택 없음 → 종료.

### Step 4-A: Git tag & GitHub Release (옵션 A 선택 시)
 
1. 기존 태그 목록 확인:
   ```bash
   git tag -l --sort=-v:refname | head -10
   ```

2. `AskUserQuestion`으로 물어본다:
   - "새 태그 버전을 입력하세요. (예: v1.2.0)"

3. 입력받은 `<version>`으로 순서대로 실행:
   ```bash
   git tag <version>
   git push origin <version>
   gh release create <version> --title "<version>" --notes "<Step 1에서 생성한 MR 메시지 전체 내용>"
   ```

### Step 4-B: Docker build & push (옵션 B 선택 시)

Docker 이미지 레지스트리: `skmidemoacr.azurecr.io/mi-agent-scenario`

1. `AskUserQuestion`으로 물어본다:
   - "Docker 이미지 태그를 입력하세요."
   - Step 4-A에서 생성한 태그가 있으면 기본값으로 안내 (예: `v1.2.0`)

2. 입력받은 `<tag>`로 순서대로 실행:
   ```bash
   docker build -f Dockerfile -t skmidemoacr.azurecr.io/mi-agent-scenario:<tag> .
   docker push skmidemoacr.azurecr.io/mi-agent-scenario:<tag>
   ```

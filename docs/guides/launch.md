# Launch 가이드

아래 순서대로 한 번만 설정하면, 이후에는 Launcher 선택으로 바로 실행할 수 있습니다.

## 1) Poetry 설치

macOS(Homebrew) 기준:

```bash
brew install poetry
```

설치 확인:

```bash
poetry --version
```

## 2) 루트 디렉토리에서 의존성 설치

프로젝트 루트(`skmip-mi-agent`)에서 아래 명령어를 실행합니다.

```bash
poetry install
```

## 3) 환경 파일 복사 및 수정

`env.example.txt`를 복사해 `env.txt`를 만들고, 실제 실행 환경에 맞게 값을 수정합니다.

```bash
cp envs/skgas_agent/env.example.txt envs/skgas_agent/env.txt
```

필수 값(예: API 키, DB 접속 정보)이 비어 있거나 예시값인 경우 반드시 실제 값으로 변경하세요.

## 4) Launcher 에서 선택해 실행

1. VS Code/Cursor에서 **Run and Debug**(실행 및 디버그) 화면을 엽니다.
2. Launch 구성에서 `[🚀]launcher: poetry install + uvicorn` 을 선택합니다.
3. `F5`를 눌러 실행합니다.

이 Launcher는 실행 전에 `Poetry Install` task를 먼저 실행하고, 이어서 `uvicorn`으로 서버를 시작합니다.

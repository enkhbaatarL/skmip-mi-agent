# 로컬 Event 벡터 검색 테스트

## 목적과 범위

기존 MySQL에서 내보낸 `documents.jsonl`을 BGE-M3로 임베딩해 Qdrant 로컬 모드에 저장하고 검색한다.
별도 DB 서버·Docker·포트·API key 없이 단일 Python 프로세스로 테스트한다. 원본 MySQL 데이터는 유지하고
검색용 사본을 만든다. Qdrant 파일 저장소는 `local/qdrant_event_demo`, 모델 캐시는 `local/models`다.

현재 도구는 후보 벡터 검색 데모다. 키워드 검색 결합, LLM 최종 2개 추천, 사용자별 권한 검증 및 변경/삭제
동기화는 포함하지 않는다. 샘플에 있는 가정·테스트 Event도 그대로 검색된다.

## 1. 설치 (Windows PowerShell, 저장소 루트)

기존 앱 환경과 별도로 가상환경을 만든다.

```powershell
.venv\Scripts\python.exe -m venv local/.venv-vector
local\.venv-vector\Scripts\python.exe -m pip install -r scripts/requirements-local-event-search.txt
```

Qdrant Client, Sentence Transformers 및 PyTorch 등 의존성이 설치된다. 기본 실행 장치는 CPU다.
최초 실행에는 Hugging Face 모델 다운로드가 필요하며, BGE-M3 모델 파일과 패키지에 수 GB의 디스크 공간을
준비한다. CPU 처리 시간은 PC에 따라 달라지므로 우선 기존 31개 문서로 확인한다.
모델은 `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`로 고정한다.

## 2. 데이터 준비

이미 생성된 30개 Event / 31개 문서로 시작하면 MySQL을 다시 조회할 필요가 없다.

```text
local/output/event_search_documents/20261030_sample/documents.jsonl
```

새 데이터가 필요하면 기존 앱 가상환경과 `envs/.env`로 조회한다. 새 출력 폴더를 지정한다.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/export_event_search_documents.py --sample-size 30 --output-dir local/output/event_search_documents/new_sample
```

생성 과정과 필드 매핑은 [Event 검색 문서 구성](09_EVENT_SEARCH_DOCUMENTS.md)을 참고한다.
그다음 명령에 `--documents local/output/event_search_documents/new_sample/documents.jsonl`을 추가하면 된다.

## 3. 적재

```powershell
local\.venv-vector\Scripts\python.exe -X utf8 scripts/local_event_vector_search.py
```

JSONL 읽기 → `text` 임베딩 → 1,024차원 cosine 컬렉션 생성 → 벡터와 메타데이터 저장 순서다.
기존 문서 문자열 ID는 Qdrant point ID로 쓸 수 있도록 결정적인 UUID로 변환한다.
문서 또는 모델 revision이 바뀌면 다른 컬렉션을 생성하고, 동일 입력은 저장된 벡터를 재사용한다.
이 데모는 다른 컬렉션을 삭제하지 않는다. 샘플 변경으로 생긴 이전 컬렉션은 디스크에 남는다.

## 4. 검색

Event 선택 기반 검색: 샘플 내 Event 5의 문서 조각을 합쳐 질의를 만들고 자기 자신을 제외한다.

```powershell
local\.venv-vector\Scripts\python.exe -X utf8 scripts/local_event_vector_search.py --event-id 5 --top-k 5
```

자유 문장 검색:

```powershell
local\.venv-vector\Scripts\python.exe -X utf8 scripts/local_event_vector_search.py --query "LNG 공급 차질과 유럽 가스 수요 증가" --top-k 5
```

적재 전 검색을 실행하면 먼저 적재한 후 검색한다. 결과는 Event별 최고 문서 점수를 사용해 중복을 제거하고,
ID·제목·cosine 유사도·데이터 경고를 콘솔에 출력한다. 유사도는 추천 확률이나 사실 신뢰도가 아니다.
입력이 모델 토큰 한도를 초과하면 조용히 잘라내지 않고 오류로 종료한다.

## 실행 범위와 검증 상태

- Python 로컬 모드이므로 localhost:6333 서버나 웹 dashboard는 생기지 않는다.
- 같은 DB 폴더에 두 프로세스를 동시에 연결하지 않는다. FastAPI multi-worker는 향후 서버 모드로 연결한다.
- 문서는 최대 1,000개로 제한한 소량 데모이며, 검색은 전체 문서 결과를 Event 단위로 합친다.
- 삭제/게시 상태는 JSONL 생성 시점 기준이다. 운영 상태를 즉시 반영하려면 별도 동기화가 필요하다.
- 준비 단계에서는 입력 31개 문서·Event 질의 구성·스크립트 문법을 검증했다. 패키지 설치,
  실제 BGE-M3 다운로드 및 Qdrant 적재·검색은 위 명령으로 실행한다.

모델 다운로드 없이 JSONL만 검사하려면 기존 앱 환경에서도 실행할 수 있다.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/local_event_vector_search.py --validate-only --event-id 5
```

공식 문서: [Qdrant Python Client](https://github.com/qdrant/qdrant-client),
[BGE-M3](https://huggingface.co/BAAI/bge-m3),
[Sentence Transformers](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).

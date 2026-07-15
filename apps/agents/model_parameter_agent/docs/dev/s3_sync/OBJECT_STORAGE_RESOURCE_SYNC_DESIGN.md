# Model Parameter Agent — Object Storage 리소스 동기화 설계

> 상태: 최종 설계 v2 (Codex 교차 리뷰 반영, 2026-07-14)
> 대상: `model_param.py` 로 기동하는 model_parameter_agent
> 제약: **버킷의 디렉터리/파일 구조는 외부에서 관리되며 우리가 변경할 수 없다.**
> 앱은 각 파일의 디렉터리(prefix)와 파일명만 알 수 있다. (릴리스 매니페스트·불변
> release prefix 같은 업로드 측 규약을 요구할 수 없음)

## 1. 배경 및 목표

model_parameter_agent는 basecase Excel(.xlsm 3종)과 LUT CSV(+ `lut_parameters.yaml`)를
패키지 내 정적 경로(`apps/agents/model_parameter_agent/resources/`)에서 읽는다.
파일이 이미지에 베이크되어 있어 데이터 갱신 시마다 이미지 재빌드·재배포가 필요하다.

**목표**: NCP Object Storage(S3 호환)에 있는 basecase/LUT 파일을
앱 기동 시 다운로드 받아 그 파일로 동작하게 한다.
S3 사용 여부와 접속 정보(endpoint / access key / secret key / region / signature_version)는
설정으로 관리한다.

### 현행 구조 (변경 전)

| 항목 | 위치 | 근거 코드 |
|---|---|---|
| basecase | `resources/basecase/*.xlsm` (3종) | `utils/parameter_mapping.py:21-22`, `_resolve_basecase_dir()` |
| LUT | `resources/lut/*.csv` + `lut/config/lut_parameters.yaml` | `utils/lut/registry.py:21-22` (`DEFAULT_LUT_ROOT`) |
| 기동 검증 | lifespan에서 `validate_lut_startup()` + `preload_basecase_runtime_cache()` | `model_param.py:103-135` |
| 런타임 로드 | `get_parameter_spec_registry()` / `get_lut_catalog()` / `get_parameter_knowledge_base_from_resources()` — **경로 인자 없이 호출** | `flows/propose_parameters/nodes.py` |
| 캐시 | 경로 + mtime/size + sha256 기반 LRU (`_SNAPSHOT_CACHE` 등) | `utils/lut/runtime.py` |
| 배포 | gunicorn **3 workers** (lifespan이 워커별로 실행됨) | `Dockerfile.model_param` |

mapping xlsx는 DB에서 로드되므로(`_load_db_mapping_resources`) 이번 대상이 아니다.

## 2. 설계 원칙 (Codex 협의 결과)

초안은 "prefix 나열 → 파일별 ETag 비교 → 파일별 atomic rename" 방식이었으나,
교차 리뷰에서 다음 문제가 확인되어 **세대(generation) 디렉터리 + 원자적 포인터 스왑**
방식으로 확정했다.

1. **번들 원자성 (Critical)** — 파일별 `os.replace()`는 개별 파일만 원자적이다.
   다운로드 도중 실패하거나 워커가 경합하면 basecase는 신버전, LUT는 구버전인
   혼합 상태가 활성화될 수 있다. → 전체 번들을 스테이징 디렉터리에 받고 검증한 뒤
   `current` 심볼릭 링크 하나만 원자적으로 교체한다.
2. **멀티프로세스 조정 (High)** — gunicorn 3워커가 lifespan을 각각 실행한다.
   → OS 파일락(`fcntl.flock`)으로 `다운로드 → 검증 → 활성화`를 직렬화한다.
   첫 워커만 동기화하고 나머지는 락 해제 후 활성 세대를 재해석해 사용한다.
3. **원격 스냅샷 일관성 (High)** — 버킷 레이아웃을 통제할 수 없으므로 "업로드 완료 후
   매니페스트 발행" 같은 규약이 불가능하다. → **리스팅 지문(fingerprint) 안정화**로
   대체한다: 다운로드 전·후 리스팅의 (key, ETag, size, last_modified) 지문이 일치할
   때만 세대를 확정하고, 불일치하면 재시도한다.
   **한계(잔여 위험)**: 지문 안정화와 번들 검증은 "구조적으로 깨진 번들"(파일 누락,
   열리지 않는 워크북, 로드 불가 CSV)은 걸러내지만, 업로드가 일부 파일만 교체된 채
   장시간 중단된 경우의 **의미적 혼합 버전**(basecase 신버전 + LUT 구버전이 각각
   정상 로드되는 경우)은 원격 버전 식별자가 없는 한 기술적으로 탐지할 수 없다.
   이 잔여 위험은 운영 절차(파일 일괄 교체, 9절 운영 가이드)로 관리한다.
4. **ETag는 불투명 값 (High)** — multipart 업로드의 ETag는 파일 MD5가 아니다.
   ETag는 "같은 원격 객체인지" 판별(지문 구성 요소)에만 쓴다. 무결성은
   Content-Length 일치 + (단일파트 ETag인 경우에 한해) MD5 대조 + 다운로드 시점에
   계산한 sha256을 로컬 `.sync-manifest.json`에 기록해 이후 세대 검증에 사용한다.
5. **활성화 전 검증 (High)** — 현행 basecase 프리로드는 워크북 누락을 warning으로만
   처리한다(fail-fast 아님). → 스테이징 경로에서 LUT 카탈로그 로드와 basecase 워크북
   3종 검증을 통과한 세대만 활성화한다.
6. **기존 파일은 절대 변경하지 않음** — 활성 세대 내부 파일을 수정·삭제하지 않는다.
   실패 시 partial 스테이징만 제거하며 기존 `current`는 그대로 남는다.

## 3. 원격 계약: 외부 관리 버킷 레이아웃

버킷 구조는 스토리지 관리 주체가 정하며, 앱은 설정으로 받은 prefix 2개를 읽기만 한다.

```
{bucket}/
├── {basecase_prefix}…/            # basecase .xlsm 이 있는 디렉터리 (예: mi/basecase/)
│   ├── Demand Model_Input.xlsm
│   ├── Supply Model_Input.xlsm
│   └── Trade Model_Input.xlsm
└── {lut_prefix}…/                 # LUT csv 가 있는 디렉터리 (예: mi/lut/)
    ├── *.csv
    └── (있다면) config/lut_parameters.yaml
```

### 리스팅·검증 규칙 (다운로드 측)

- `list_objects_v2`로 두 prefix를 나열한다. 상대 경로 = key에서 prefix 제거.
  상대 경로에 `..`·절대경로가 포함되거나 로컬 세대 디렉터리 밖으로 resolve되면 거부.
- 파일 필터: basecase는 `*.xlsm`(단, `~$` 임시파일 제외 — `_discover_basecase_workbooks`
  와 동일 규칙), LUT는 `*.csv` + `config/lut_parameters.yaml`. 그 외 확장자는 무시(WARNING).
- 필수 파일 검증(다운로드 전): basecase 워크북은 `MODEL_FILE_MARKERS` 3종 각각에
  **정확히 1개씩** 매칭되어야 한다 — 누락뿐 아니라 marker당 중복 매칭(구버전 잔존 등)도
  실패 처리한다. LUT는 yaml에 선언된 파일 검증을 6단계 카탈로그 로드가 수행.
- **LUT config yaml 해석 규칙**: `{lut_prefix}config/lut_parameters.yaml`이 리스팅에
  존재하면 그것을 사용, 없으면 패키지에 포함된 `DEFAULT_LUT_CONFIG_PATH`를 사용하고
  lut_root만 다운로드 세대 디렉터리를 가리키게 한다
  (`get_parameter_spec_registry(config_path=..., lut_root=...)`가 이미 분리 지원).

### 버전 식별: 리스팅 지문(fingerprint)

원격에 버전 식별자가 없으므로, 정렬된 리스팅으로 지문을 만든다:

```
fingerprint = sha256(
    sorted([(role, full_key, etag, size, last_modified_iso), ...])   # role: basecase|lut
    + [("lut_config_source", "remote" | "packaged:" + packaged_yaml_sha256)]
)
```

- **full key**(prefix 포함)를 사용한다 — prefix 설정 변경이나 상대 경로 중복이
  지문에 반영되도록. `role`을 포함해 두 prefix가 겹쳐도 모호하지 않게 한다.
- 원격에 LUT yaml이 없어 패키지 yaml을 쓰는 세대는 패키지 yaml의 sha256을 지문에
  포함한다 — 이미지 교체로 패키지 yaml이 바뀌면 지문도 바뀌어 세대가 재생성된다.
- 세대 디렉터리명은 지문 앞 16 hex를 쓰되(`generations/{fingerprint[:16]}/`),
  **비교는 항상 `.sync-manifest.json`에 기록된 전체 지문 값**으로 한다
  (디렉터리명은 표시용 축약일 뿐).
- 원격 파일이 하나라도 바뀌면(ETag/size/시각 변화) 지문이 바뀌어 새 세대가 생성된다.
- `current` 세대의 전체 지문과 원격 지문이 같으면 다운로드를 스킵한다.

### 스냅샷 안정화 (혼합 버전 완화)

업로드 도중 리스팅하면 혼합 세대를 받을 수 있다. 완화책:

1. 리스팅 → 지문 A 계산 → 전체 다운로드 → 재리스팅 → 지문 B 계산
2. A ≠ B이면 처음부터 재시도 (최대 `sync_max_attempts`회, 기본 3)
3. 소진 시 실패 처리 (→ 7절 실패 정책)

잔여 위험(리스팅 사이에 업로드가 완전히 끝난 경우 등)은 5단계 번들 검증이 걸러낸다.
운영 가이드로 "파일 교체는 앱 재기동 직전이 아닌 시점에 일괄 수행"을 문서화한다.

## 4. 로컬 데이터 디렉터리 레이아웃

```
{model_parameter_data_dir}/            # e.g. /data/model-parameter (쓰기 가능 볼륨)
├── .sync.lock                         # fcntl.flock 대상
├── current -> generations/3f9a1c…     # 심볼릭 링크 (원자 스왑 대상)
└── generations/
    ├── 3f9a1c…/                       # 활성 세대 (지문이 디렉터리명)
    │   ├── basecase/…
    │   ├── lut/…
    │   └── .sync-manifest.json        # 다운로드 시점 기록: 지문, 파일별 etag/size/sha256
    ├── 77b2d0…/                       # 직전 세대 1개 보존 (롤백/디버깅)
    └── 3f9a1c….partial-{uuid}/        # 스테이징 (실패 시 즉시 삭제)
```

- `.sync-manifest.json`은 원격 계약물이 아니라 **다운로드 측이 생성하는 로컬 기록**이다
  (지문, 리스팅 스냅샷, 파일별 다운로드 시 계산한 sha256). 세대 유효성 검사와
  고아 세대 재사용 판정에 쓴다.
- `current` 교체: 임시 심볼릭 링크 생성 후 `os.replace(tmp_link, current)`
  (동일 파일시스템, 원자적).
- 보존 정책: 활성 세대 + 직전 1개. 활성화 성공 직후 락 안에서 나머지 및
  잔여 `*.partial-*` 정리.

## 5. Settings 추가 (`apps/common/configs/config.py`)

기존 `model_parameter_*` 네이밍을 따른다.

```python
# Model parameter resources — NCP Object Storage (S3-compatible)
model_parameter_object_storage_enabled: bool = Field(default=False)
model_parameter_object_storage_endpoint_url: str = Field(default="")
model_parameter_object_storage_region: str = Field(default="kr-standard")
model_parameter_object_storage_access_key: str = Field(default="")
model_parameter_object_storage_secret_key: str = Field(default="")
model_parameter_object_storage_signature_version: str = Field(default="s3v4")  # NCP: "s3" | "s3v4"
model_parameter_object_storage_bucket: str = Field(default="")
model_parameter_object_storage_basecase_prefix: str = Field(default="")   # 예: "mi/basecase/"
model_parameter_object_storage_lut_prefix: str = Field(default="")        # 예: "mi/lut/"
model_parameter_object_storage_download_timeout_seconds: float = Field(default=60.0, gt=0)
model_parameter_object_storage_max_retries: int = Field(default=3, ge=0)   # botocore 요청 재시도
model_parameter_object_storage_sync_max_attempts: int = Field(default=3, ge=1)  # 지문 안정화 재시도
model_parameter_object_storage_fallback_to_local: bool = Field(default=True)
model_parameter_object_storage_lock_timeout_seconds: float = Field(default=300.0, gt=0)

# 로컬 데이터 루트 (S3 sync 대상이자 경로 해석 2순위 — S3 없이 단독 오버라이드도 가능)
model_parameter_data_dir: str = Field(default="")
```

- `model_validator(mode="after")`: `enabled=True`인데 `endpoint_url`/`bucket`/`access_key`/
  `secret_key`/`basecase_prefix`/`lut_prefix`/`model_parameter_data_dir` 중 하나라도 비면
  기동 실패 (fail-fast).
- secret은 기존 패턴대로 `envs/config.yaml`에서 `${ENV_NAME}` placeholder로 주입,
  k8s Secret → 환경변수로 전달. `.env` 커밋 금지 규칙 동일 적용.

## 6. 커넥터: `apps/connectors/object_storage/`

레이어 규칙(nodes/tools → connectors → external) 준수. **boto3 추가 없이 botocore만 사용**
(이미 의존성에 존재).

```
apps/connectors/object_storage/
├── __init__.py
├── client.py      # 설정 → botocore S3 클라이언트 생성/종료
├── schemas.py     # RemoteListing, RemoteObject, SyncResult (Pydantic v2)
└── sync.py        # prefix 리스팅 + 세대 다운로드
```

### client.py

```python
def create_object_storage_client(cfg: Settings) -> BaseClient:
    session = botocore.session.get_session()
    return session.create_client(
        "s3",
        endpoint_url=cfg.model_parameter_object_storage_endpoint_url,
        region_name=cfg.model_parameter_object_storage_region,
        aws_access_key_id=cfg.model_parameter_object_storage_access_key,
        aws_secret_access_key=cfg.model_parameter_object_storage_secret_key,
        config=BotoConfig(
            signature_version=cfg.model_parameter_object_storage_signature_version,
            s3={"addressing_style": "path"},          # NCP는 path-style 권장
            retries={"max_attempts": cfg.model_parameter_object_storage_max_retries},
            connect_timeout=cfg.model_parameter_object_storage_download_timeout_seconds,
            read_timeout=cfg.model_parameter_object_storage_download_timeout_seconds,
        ),
    )
```

- 기동 시 1회 사용 후 `client.close()`로 명시적 종료. **RuntimeContext에 넣지 않는다**
  (런타임 재사용이 없는 단발성 클라이언트이므로 싱글톤 불필요).
- botocore는 sync → 커넥터 공개 API는 `async def`, 내부에서 `asyncio.to_thread`로 실행
  (async-first 규칙).

### sync.py

```python
@log_connector(connector_type="S3", log_input=False, log_output=False)
async def list_remote_objects(cfg: Settings) -> RemoteListing:
    """basecase/lut prefix 리스팅 + 필터 + 필수 파일 검증 + 지문 계산."""

@log_connector(connector_type="S3", log_input=False, log_output=False)
async def download_listing(cfg: Settings, listing: RemoteListing, staging_dir: Path) -> SyncResult:
    """리스팅에 명시된 키만 다운로드. 파일별 절차는 아래."""
```

- `connector_type="S3"`를 로깅 규칙 문서(`.claude/rules/logging.md`)의 타입 목록에 추가.
- `log_input=False, log_output=False`: 자동 마스킹(`_mask_sensitive`)이
  `model_parameter_object_storage_access_key` 같은 키 이름을 매칭하지 못하므로
  자격증명이 포함될 수 있는 페이로드는 로그에 남기지 않는다. Settings 객체를
  로그되는 kwargs로 넘기지 않는다.
- 다운로드 절차 (파일별):
  1. 상대 경로 검증: `..`/절대경로 거부, `staging_dir` 밖으로 resolve되면 거부
  2. `get_object` → `staging_dir/{role}/{relative_path}.tmp`에 스트리밍 쓰기
     (쓰는 동안 sha256 동시 계산)
  3. 무결성 검증:
     - `get_object` 응답 ETag == 리스팅 ETag (모든 경우 — 리스팅과 다운로드 사이에
       객체가 교체되면 여기서 잡힌다)
     - Content-Length == 리스팅 size
     - ETag가 단일파트 형식(`-` 없음)이면 MD5 대조
       (※ "단일파트 ETag = MD5"는 S3/NCP 관례에 근거한 가정 — 구현 시 NCP에서 실측
       확인하고, 불일치가 관찰되면 이 검사는 WARNING으로 강등)
  4. `os.replace()`로 최종 파일명 확정
- 파일별 sha256은 다운로드 중 계산해 `SyncResult`로 반환만 한다.
  `.sync-manifest.json` **기록은 오케스트레이션이 번들 검증 통과 후** 수행한다
  (7절 6단계) — 이 파일의 존재가 곧 "검증 완료된 세대" 표식이다.
- 예외 처리: `botocore.exceptions.ClientError`/`EndpointConnectionError` 등은
  `raise MIBaseError(ErrorCode.INTERNAL_SERVER_ERROR, detail=...) from exc`로 래핑.

## 7. 기동 시퀀스 (`model_param.py` lifespan)

기존 `validate_lut_startup` / `preload_basecase_runtime_cache` **앞에** 삽입한다.

### 실행 모델 (async/blocking 경계)

- 오케스트레이션 `sync_model_parameter_resources(cfg)`는 `async def`이며 lifespan에서
  직접 `await`한다 (바깥 `asyncio.to_thread` 없음).
- 커넥터 공개 API(`list_remote_objects`, `download_listing`)도 `async def`이고,
  botocore 호출만 내부에서 `asyncio.to_thread`로 실행한다.
- 파일락 획득/해제, sha256 계산, rename/symlink 등 blocking 파일 작업은
  오케스트레이션이 단계별로 `asyncio.to_thread`에 위임한다.
  (fcntl 락은 fd 기준이므로 같은 프로세스 안에서 스레드를 넘나들어도 유효하다.)

```
if not cfg.model_parameter_object_storage_enabled:
    → sync 없이 8절 경로 해석 규칙으로 진행

acquire fcntl.flock({data_dir}/.sync.lock, timeout=lock_timeout)   # 워커 간 직렬화
try:
    for attempt in 1..sync_max_attempts:                    # 지문 안정화 루프
        1. listing = list_remote_objects()                  # 지문 A 계산 + 필수 파일 검증
        2. if current가 유효하고 current 지문 == 지문 A:
               skip-sync로 종료 (이미 다른 워커/이전 기동이 완료)   # "유효" 기준은 아래
        3. if generations/{지문A 축약}/ 가 이미 존재하고 .sync-manifest.json의 전체 지문 == 지문 A
               (직전 기동이 rename 후 스왑 전에 죽은 고아 세대):
               파일별 size/sha256 전수 검증 + 6단계 번들 검증을 **다시 수행**
               (이미지 교체로 패키지 yaml·코드가 바뀌었을 수 있으므로 과거 검증을 신뢰하지 않음)
               → 통과 시 rename 없이 8번(스왑)으로 (재사용), 실패 시 해당 디렉터리 삭제 후 계속
        4. staging = generations/{지문A}.partial-{uuid}/ 생성
           → download_listing(listing, staging)             # 전 파일 + 무결성 검증
        5. 재리스팅 → 지문 B. if A != B: staging 삭제 후 continue (다음 attempt)
        6. 번들 검증 (스테이징 경로 명시 전달):
           - basecase: MODEL_FILE_MARKERS 3종 워크북 존재 + openpyxl open 성공
           - LUT: get_parameter_spec_registry(config_path=<3절 yaml 해석 규칙>,
                    lut_root=staging/lut) + get_lut_catalog(policy, registry=...)
             ※ cfg.model_parameter_lut_enabled 값과 무관하게 카탈로그까지 전체 로드한다.
               (validate_lut_startup은 enabled=False면 CSV 로드를 건너뛰므로 직접 호출)
           검증 후 .sync-manifest.json 기록 → break
    (루프 소진 시: 지문 불안정 → 실패 처리로 이동)

    7. staging을 generations/{지문A}/로 rename
    8. tmp symlink 생성 → os.replace(tmp, current)     # 원자 활성화 = 커밋 경계
    9. 오래된 세대·잔여 partial 정리 (활성 + 직전 1개만 보존)
       ※ 커밋(8) 이후 단계 — 실패해도 logger.warning만 남기고 성공으로 처리.
         fallback/삭제 경로로 빠지지 않는다.
except Exception:                                   # 1~8단계 실패에만 해당
    - staging(partial)만 삭제. 기존 current와 완성된 세대 디렉터리는 불변.
    - fallback_to_local=True 이고 유효한 current 세대가 존재:
        logger.warning(...) 후 기존 세대로 기동 계속
    - 아니면 raise → 앱 기동 실패 (의도된 fail-fast)
finally:
    release lock

# 이후 기존 코드 그대로 실행 (경로 해석이 current를 보므로 변경 최소):
validate_lut_startup(...), preload_basecase_runtime_cache(...)
```

### "유효한 current" 판정 기준

공통 (2번 skip / fallback):

1. `current`가 심볼릭 링크이고, resolve 결과가 `{data_dir}/generations/` 하위 디렉터리
2. 해당 세대에 `.sync-manifest.json`이 존재하고 파싱 가능 (= 검증 완료 표식)
3. `.sync-manifest.json`의 모든 파일이 존재하고 size 일치

추가 (fallback 경로에만):

4. 파일별 **sha256 전수 재검증** — sync 실패 후 기존 세대로 기동을 지속하는 예외
   경로이므로 비용보다 확실성이 우선. 동일 size 손상까지 걸러낸다.
   (happy path인 2번 skip에는 size 검사까지만 적용 — 매 기동 sha256 전수 계산은
   비용 대비 이득이 없다는 판단이며, 손상 우려가 크면 skip 경로에도 켤 수 있도록
   구현은 검증 강도를 인자로 받는다)

- 락을 먼저 잡은 워커가 동기화를 수행하고, 나머지 워커는 락 해제 후 2번 조건으로 skip.
- pod 재시작 시: 스토리지 장애면 fallback 정책 적용. **새 pod(빈 볼륨)에서는 fallback할
  세대가 없으므로 기동 실패가 정상 동작이다** (9절 배포 요구사항 참조).

## 8. 경로 해석 변경

우선순위 (basecase / LUT 공통):

1. 함수에 명시적으로 전달된 경로 인자 (기존 동작 — 테스트·검증 단계에서 사용)
2. `cfg.model_parameter_data_dir/current/{basecase|lut}` 가 존재하면 사용
3. 패키지 기본 `resources/` (기존 fallback)

### basecase — `utils/parameter_mapping.py`

`_resolve_basecase_dir(path)`의 `path is None` 분기에 2순위 해석 추가:

```python
def _resolve_basecase_dir(path: str | None) -> Path:
    if path:
        ...  # 기존 동작 유지
    data_dir = get_settings().model_parameter_data_dir
    if data_dir:
        candidate = Path(data_dir).expanduser() / "current" / "basecase"
        if candidate.is_dir():
            return candidate
    ...  # 기존 DEFAULT_BASECASE_DIR fallback 유지
```

### LUT — `utils/lut/runtime.py`

`get_parameter_spec_registry` / `get_lut_catalog` / `validate_lut_startup`의
default가 import 시점 상수(`DEFAULT_LUT_CONFIG_PATH`)로 굳어 있으므로,
**default를 `None`으로 바꾸고 호출 시점에 해석**한다 (no-arg 호출부 `nodes.py`는 무변경):

```python
def resolve_lut_config_path() -> Path:
    data_dir = get_settings().model_parameter_data_dir
    if data_dir:
        current_lut = Path(data_dir).expanduser() / "current" / "lut"
        downloaded_yaml = current_lut / "config" / "lut_parameters.yaml"
        if downloaded_yaml.is_file():
            return downloaded_yaml
        # current/lut 이 존재하지만 yaml 이 없는 세대 → 패키지 yaml + lut_root 는 current/lut
    return DEFAULT_LUT_CONFIG_PATH                # data_dir 미설정/current 부재 포함 최종 fallback

def resolve_lut_root() -> Path:
    data_dir = get_settings().model_parameter_data_dir
    if data_dir:
        current_lut = Path(data_dir).expanduser() / "current" / "lut"
        if current_lut.is_dir():
            return current_lut
    return DEFAULT_LUT_ROOT

def get_parameter_spec_registry(
    config_path: Path | str | None = None,
    *,
    lut_root: Path | str | None = None,
) -> ParameterSpecRegistry:
    config = Path(config_path or resolve_lut_config_path()).expanduser().resolve()
    root = Path(lut_root or resolve_lut_root()).expanduser().resolve()
    ...
```

※ 원격에 yaml이 없는 경우 `config_path`(패키지)와 `lut_root`(다운로드 세대)가
분리되는데, 기존 시그니처가 이미 두 인자를 분리 지원하므로 구조 변경은 없다.
캐시 키에도 config 경로와 root가 모두 포함되어 있다.

### 캐시 정합성

- LUT LRU 캐시 키에 이미 경로·sha256이 포함되어 있어(`utils/lut/runtime.py`)
  세대 전환 시 자연스럽게 새 엔트리가 생성된다.
- `current` 심볼릭 링크는 기동 시 1회 스왑되고 이후 불변이므로, 요청 처리 중
  경로가 바뀌는 경우는 없다 (mtime/size 시그니처 캐시와도 충돌 없음).
- basecase KB 캐시 키도 dir 경로 + 워크북 시그니처를 포함하므로 동일.

## 9. 배포 요구사항

| 항목 | 내용 |
|---|---|
| 볼륨 | `model_parameter_data_dir`(예: `/data/model-parameter`)에 **쓰기 가능 볼륨 마운트 필수**. 현행 `devops/k8s/deployment.yaml`은 config만 마운트하므로 volume 추가 필요 |
| 볼륨 종류 | `emptyDir`: pod 생애 내 fallback만 가능 (재시작 시 재다운로드, 스토리지 장애 시 기동 실패). `PVC`: pod 재시작 후에도 fallback 가능. **운영 요구에 따라 선택하되 기본 권고는 emptyDir + 기동 실패 허용** |
| 권한 | 컨테이너가 non-root로 실행되므로 (`Dockerfile.model_param`) 마운트 볼륨의 쓰기 권한(fsGroup 또는 initContainer chown) 확인 |
| Secret | access/secret key는 k8s Secret → 환경변수 → `${ENV_NAME}` placeholder 주입 |
| 비활성 시 | `enabled=false`면 S3 sync를 수행하지 않는다. 단 8절 경로 해석은 항상 적용되므로: `model_parameter_data_dir`까지 비어 있으면(기본값) 기존과 완전히 동일(패키지 resources), data_dir만 설정하면 S3 없이 `data_dir/current`를 로컬 오버라이드로 사용할 수 있다 (사전 배치된 파일 사용 — 의도된 기능) |
| 운영 가이드 | 버킷 파일 교체는 일괄로, 앱 재기동과 겹치지 않는 시점에 수행 권장 (지문 안정화 재시도로 완화되지만 겹치면 기동이 지연될 수 있음) |

## 10. 로깅

```
INFO  [CONNECTOR][S3][list_remote_objects] DONE | bucket=… files=12 fingerprint=3f9a1c…
INFO  [CONNECTOR][S3][download_listing] DONE | files=12 downloaded=12 bytes=45MB elapsed=…ms
INFO  Model Parameter resources activated | fingerprint=… generation_dir=…
WARN  Remote listing changed during download, retrying | attempt=… before=… after=…
WARN  Object storage sync failed, falling back to existing generation | fingerprint=… error=…
```

- 자격증명·서명 URL은 어떤 레벨에서도 로그 금지.
- 활성화된 지문(fingerprint)은 INFO로 남겨 배포 감사에 사용.

## 11. 테스트 계획

1. **sync 단위 테스트** — botocore `Stubber` 또는 fake client 주입:
   리스팅 필터·필수 파일 검증, 지문 계산 결정성, path traversal 거부,
   size/단일파트 MD5 불일치 거부, 스테이징 → rename → symlink 스왑 순서 검증
2. **지문 안정화 테스트** — 다운로드 중 리스팅 변경 시 재시도, attempts 소진 시 실패
3. **경로 해석 테스트** — `_resolve_basecase_dir` / `resolve_lut_config_path` /
   `resolve_lut_root` 우선순위 (명시 인자 > data_dir/current > 패키지 기본),
   원격 yaml 부재 시 패키지 yaml + 다운로드 lut_root 조합
4. **멀티프로세스 테스트** — 파일락 경합 시 후발 프로세스가 skip 경로를 타는지
   (`multiprocessing`으로 2프로세스 동시 진입)
5. **실패 정책 테스트** — 다운로드 중단 시 current 불변 + partial 삭제,
   fallback on/off에 따른 기동 성공/실패, 커밋(스왑) 후 정리 실패는 warning만,
   고아 세대(rename 후 스왑 전 크래시) 재검증·재사용/폐기
6. **설정 검증 테스트** — enabled인데 필수값 누락 → `ValidationError`

## 12. 스코프 제외

- mapping xlsx (DB 로드로 대체됨)
- 기동 후 주기적 refresh/폴링 — 데이터 갱신 반영은 rolling restart로 처리
- 업로드 기능 (read-only; 버킷 관리 주체가 별도 운영)
- 버킷 레이아웃·업로드 절차에 대한 규약 요구 (통제 불가 전제)

## 13. 구현 파일 목록

| 파일 | 작업 |
|---|---|
| `apps/common/configs/config.py` | Settings 필드 + validator 추가 |
| `apps/connectors/object_storage/{__init__,client,schemas,sync}.py` | 신규 커넥터 |
| `apps/agents/model_parameter_agent/utils/resource_sync.py` | 신규 — 락/지문/세대/활성화 오케스트레이션 (`sync_model_parameter_resources(cfg)`) |
| `apps/agents/model_parameter_agent/utils/parameter_mapping.py` | `_resolve_basecase_dir` 2순위 해석 추가 |
| `apps/agents/model_parameter_agent/utils/lut/runtime.py` | default `None` 화 + `resolve_lut_config_path()`/`resolve_lut_root()` |
| `model_param.py` | lifespan에 sync 호출 삽입 |
| `.claude/rules/logging.md` | connector_type에 `S3` 추가 |
| `envs/config.yaml` | 신규 설정 키 + `${…}` placeholder |
| `devops/k8s/deployment.yaml` | 데이터 볼륨 마운트 + Secret 환경변수 |
| `tests/…` | 11절 테스트 |

## 부록: Codex 문서와의 관계

Codex가 별도 세션에서 작성한
`docs/architectures/model_parameter_agent_s3_resource_bootstrap.md`는 같은 요구사항에
대한 대안 설계다. 골격(스테이징 다운로드, 세트 단위 원자 활성화, 프로세스 락,
3워커 대응, secret 주입)은 본 문서와 동일하며, 다음 두 가지 정책이 다르다.

| 결정 사항 | 본 문서 (Claude) | Codex 문서 |
|---|---|---|
| 원격 파일 식별 | prefix 리스팅 (`list_objects_v2`) — 버킷에 파일 추가 시 설정 변경 불필요 | 파일별 exact object key를 설정에 1:1 명시 — 리스팅 권한 불필요, 파일 추가 시 설정 갱신 필요 |
| 원격 실패 시 | fail-fast 기본 + 이전 다운로드 세대로만 fallback | 이미지에 포함된 packaged 리소스로 fallback하여 기동 지속 |

구현 착수 전에 두 정책에 대한 최종 선택이 필요하다.

# Model Parameter Agent S3-Compatible 리소스 부트스트랩 설계

## 1. 문서 목적

`model_parameter_agent`가 앱 기동 시 NAVER Cloud Platform(NCP) S3-compatible Object Storage에서
Basecase Excel과 LUT 리소스를 내려받고, 검증에 성공한 원격 파일로 동작하도록 하는 설계다.

이 설계의 확정 정책은 다음과 같다.

- Object Storage 사용 여부와 접속 정보는 앱 설정으로 관리한다.
- Object Storage의 기존 디렉터리와 파일은 변경하지 않는다. 앱은 읽기만 수행한다.
- 원격 디렉터리 구조를 가정하지 않고 파일별 실제 object key를 설정에 명시한다.
- 원격 manifest나 bucket listing 없이 앱이 실제로 사용하는 객체만 exact key로 다운로드한다.
- 다운로드한 파일만 writable runtime 영역에서 현재 패키지의 `resources/basecase`, `resources/lut` 구조로
  재배치한다.
- 원격 리소스 다운로드 또는 검증이 실패하면 이미지에 포함된 기존 리소스로 폴백하여 기동한다.
- 기존 Basecase/LUT 파일은 로컬 개발과 폴백을 위해 repo와 이미지에 유지한다.
- 동기화는 앱 기동 시 한 번만 수행하며 실행 중 hot reload나 주기적 갱신은 하지 않는다.
- 외부 HTTP API, callback body, DB schema는 변경하지 않는다.

NCP Object Storage는 S3 API와 region별 endpoint를 제공하며 HTTPS와 AWS Signature Version 4 사용이
권장된다. 구현 시 사용자가 보유한 endpoint, access key, secret key, region, signature version을 그대로
botocore client에 전달한다.

- NCP Object Storage API: <https://api.ncloud-docs.com/docs/en/storage-objectstorage>
- NCP Boto3 사용 예시: <https://guide.ncloud-docs.com/docs/en/storage-storage-8-2>

## 2. 현재 구조와 제약

### 2.1 현재 리소스와 로딩 경로

Basecase 기본 경로는
`apps/agents/model_parameter_agent/resources/basecase/`이며 다음 세 파일을 사용한다.

- `Demand Model_Input.xlsm`
- `Supply Model_Input.xlsm`
- `Trade Model_Input.xlsm`

`apps/agents/model_parameter_agent/utils/parameter_mapping.py`는 `DEFAULT_BASECASE_DIR`을 기본값으로
사용하지만 `preload_basecase_runtime_cache(basecase_dir_path=...)`와
`get_parameter_knowledge_base_from_resources(..., basecase_dir_path=...)`를 통해 외부 경로를 받을 수 있다.

LUT 기본 경로는 `apps/agents/model_parameter_agent/resources/lut/`이고,
`config/lut_parameters.yaml`이 사용할 CSV 파일을 선언한다. 현재 YAML이 참조하는 CSV는 6개이며,
패키지에만 보관되고 현재 YAML에서 참조하지 않는 CSV 2개는 원격 다운로드 대상에서 제외한다.

`apps/agents/model_parameter_agent/utils/lut/runtime.py`의 API는 이미 `config_path`와 `lut_root`를 받을 수
있다. 따라서 로더 자체를 다시 만들지 않고 활성 리소스 경로를 모든 호출부에 일관되게 전달한다.

현재 전체 리소스 크기는 약 20 MiB다.

### 2.2 기동 순서

Parameter Agent의 실제 엔트리포인트는 루트의 `model_param.py`다.
`Dockerfile.model_param`은 이를 이미지의 `main.py`로 복사한다.

현재 lifespan 순서는 다음과 같다.

1. 설정 로드, logging과 MLflow 초기화
2. DB schema validation
3. LUT registry/catalog validation 및 preload
4. Basecase knowledge base/record preload
5. callback OAuth token prefetch
6. 요청 수락

원격 리소스 해석은 DB schema validation 이후, 기존 LUT/Basecase preload 이전에 수행한다.
Basecase preload가 DB mapping을 사용하므로 DB 검증보다 앞당기지 않는다.

### 2.3 멀티 프로세스 제약

`Dockerfile.model_param`의 기본 `GUNICORN_WORKERS`는 3이며 FastAPI lifespan은 worker마다 실행된다.
단순히 lifespan에 다운로드 코드를 넣으면 동일 pod에서 세 프로세스가 같은 파일을 동시에 덮어쓴다.

또한 LUT와 Basecase cache는 process-local이다. 네트워크 다운로드는 pod당 한 번만 해야 하지만,
최종 리소스 validation/preload는 각 worker 프로세스에서 수행되어야 한다.

### 2.4 요청 처리 경로 제약

기동 시에만 원격 경로를 전달해서는 충분하지 않다.
`flows/propose_parameters/nodes.py`는 요청 처리 중 다음 기본 경로 API를 다시 호출한다.

- `get_parameter_knowledge_base_from_resources()`
- `get_parameter_spec_registry()`
- `get_lut_catalog()`

따라서 기동 단계에서 선택한 리소스 source와 경로를 process-local runtime에 등록하고, 기동 preload와
모든 요청 노드가 같은 활성 경로를 조회하도록 변경해야 한다.

## 3. 목표 아키텍처

### 3.1 컴포넌트 책임

```text
apps/common/configs/config.py
  └─ ModelParameterResourceStorageConfig
       └─ enabled, endpoint/credential/region/signature, bucket, 파일별 object key, timeout/local_root

apps/connectors/object_storage/
  └─ s3_client.py
       └─ S3-compatible HeadObject/GetObject, streaming download, retry/error normalization

apps/agents/model_parameter_agent/utils/
  ├─ resource_bootstrap.py
  │    └─ 명시적 key 매핑, process lock, staging, consistency 확인, remote→packaged 폴백
  └─ resource_runtime.py
       └─ worker별 immutable active paths/source/fingerprint 등록 및 조회

model_param.py lifespan
  └─ DB 검증 → resource bootstrap → 선택된 경로의 LUT/Basecase preload → 요청 수락

propose_parameters/nodes.py
  └─ resource_runtime에서 active paths를 받아 Basecase/LUT 로더에 전달
```

외부 Object Storage 호출은 `apps/connectors/`에 두고, 어떤 파일을 필요로 하는지와 어떤 source를
활성화할지는 `model_parameter_agent`가 소유한다. DB persistence 계층은 변경하지 않는다.

### 3.2 런타임 타입

Agent 내부에 다음과 같은 immutable 타입을 둔다.

```python
@dataclass(frozen=True, slots=True)
class ModelParameterResourcePaths:
    source: Literal["object_storage", "packaged"]
    root: Path
    basecase_dir: Path
    lut_root: Path
    lut_config_path: Path
    fingerprint: str | None
    fallback_reason: str | None
```

`resource_runtime`은 lifespan에서 한 번 초기화하고 요청 처리에서는 읽기만 허용한다. 초기화 전 접근은
명시적 runtime-not-ready 오류로 처리하며, 테스트에서만 reset할 수 있게 한다. 패키지 기본 경로를
runtime 기본값으로 암묵적으로 사용하지 않고 lifespan이 `packaged` 또는 `object_storage` 중 하나를
명시적으로 등록한다.

## 4. 설정 설계

### 4.1 YAML 설정

기존 `Settings`에 중첩 모델을 추가한다. 기존 `env_nested_delimiter="__"`를 사용하므로 모든 항목을
환경변수로 덮어쓸 수 있다.

```yaml
# envs/config.yaml
model_parameter_resource_storage:
  enabled: false
  endpoint_url: "https://kr.object.ncloudstorage.com"
  access_key_id: "${NCP_OBJECT_STORAGE_ACCESS_KEY_ID}"
  secret_access_key: "${NCP_OBJECT_STORAGE_SECRET_ACCESS_KEY}"
  region_name: "kr-standard"
  signature_version: "s3v4"
  bucket: ""
  objects:
    basecase:
      demand:
        # bucket: "<기본 bucket과 다를 때만 지정>"
        object_key: "<기존 Demand Basecase의 bucket 내부 전체 경로>"
      supply:
        object_key: "<기존 Supply Basecase의 bucket 내부 전체 경로>"
      trade:
        object_key: "<기존 Trade Basecase의 bucket 내부 전체 경로>"
    lut:
      config:
        object_key: "<기존 lut_parameters.yaml의 bucket 내부 전체 경로>"
      files:
        - lut_relative_path: "Demand_Model_LUT_BCInput_value_based_t2.csv"
          object_key: "<기존 GDP CSV의 bucket 내부 전체 경로>"
        - lut_relative_path: "Demand_Model_Input_PMIInput_value_based_t2.csv"
          object_key: "<기존 PMI CSV의 bucket 내부 전체 경로>"
        - lut_relative_path: "Demand_Model_LUT_BCInput_value_based_t3.csv"
          object_key: "<기존 PowerMix CSV의 bucket 내부 전체 경로>"
        - lut_relative_path: "Demand_Model_Input_WeatherInput_value_based_t1.csv"
          object_key: "<기존 HDD CSV의 bucket 내부 전체 경로>"
        - lut_relative_path: "Demand_Model_Input_WeatherInput_value_based_t2.csv"
          object_key: "<기존 CDD CSV의 bucket 내부 전체 경로>"
        - lut_relative_path: "BCLiquefaction.csv"
          object_key: "<기존 LiqUtil CSV의 bucket 내부 전체 경로>"
  local_root: "/tmp/skmip/model-parameter-resources"
  connect_timeout_seconds: 10
  read_timeout_seconds: 60
  max_attempts: 3
  bootstrap_timeout_seconds: 420
  lock_timeout_seconds: 500
```

환경변수 override 예시는 다음과 같다.

```text
MODEL_PARAMETER_RESOURCE_STORAGE__ENABLED=true
MODEL_PARAMETER_RESOURCE_STORAGE__ENDPOINT_URL=https://kr.object.ncloudstorage.com
MODEL_PARAMETER_RESOURCE_STORAGE__ACCESS_KEY_ID=...
MODEL_PARAMETER_RESOURCE_STORAGE__SECRET_ACCESS_KEY=...
MODEL_PARAMETER_RESOURCE_STORAGE__REGION_NAME=kr-standard
MODEL_PARAMETER_RESOURCE_STORAGE__SIGNATURE_VERSION=s3v4
MODEL_PARAMETER_RESOURCE_STORAGE__BUCKET=...
MODEL_PARAMETER_RESOURCE_STORAGE__OBJECTS__BASECASE__DEMAND__OBJECT_KEY=existing/path/demand.xlsm
```

파일 경로 매핑은 운영 설정 파일 또는 ConfigMap의 YAML로 관리하는 것을 기본으로 한다. Basecase 경로처럼
고정 중첩 필드는 개별 환경변수로 덮어쓸 수 있고, LUT `files` 목록 전체를 환경변수로 덮어써야 한다면
Pydantic이 파싱할 수 있는 JSON 배열을 사용한다. credential만 Secret 환경변수로 분리한다.

### 4.2 설정 검증과 비밀정보

- `enabled=false`가 기본값이며 이때 Object Storage 설정은 사용하지 않는다.
- `access_key_id`와 `secret_access_key`는 `SecretStr`로 선언한다.
- `enabled=true`일 때 bootstrap이 endpoint, credential, region, signature version, bucket과 파일별 key 매핑을
  검증한다.
- 기존 `${ENV_NAME}` 치환은 환경변수가 없으면 placeholder를 그대로 남기므로 `${...}`가 남아 있으면
  원격 설정 오류로 처리한다.
- 원격 설정 오류도 선택된 정책에 따라 packaged 리소스 폴백 대상이다.
- endpoint는 HTTPS만 운영 지원한다. HTTP는 unit/local integration test에만 명시적으로 허용한다.
- secret 값, Authorization header, botocore request dump는 어떤 log에도 남기지 않는다.
- endpoint host, bucket과 논리 파일명은 운영 진단을 위해 log에 남길 수 있다. 전체 object key는 민감한
  디렉터리명이 포함될 수 있으므로 기본 log에는 남기지 않고 필요할 때만 마스킹하여 DEBUG에 기록한다.

Pydantic 모델 생성 자체를 실패시키는 조건부 required validator는 사용하지 않는다. 설정 객체가 만들어지기
전에 예외가 나면 packaged fallback을 수행할 수 없기 때문이다. 타입 오류는 설정 오류로 기동을 실패시키되,
원격 필수값 누락/미치환 placeholder는 bootstrap의 remote validation 오류로 분류하여 폴백한다.

### 4.3 SDK 선택

직접 의존성으로 이미 선언된 `botocore`를 사용한다. 현재 lock에 존재하는 `boto3`는 전이 의존성이므로
직접 import하지 않는다. 따라서 신규 dependency와 lockfile 변경은 필요하지 않다.

client 설정은 다음을 포함한다.

- `endpoint_url`
- `aws_access_key_id`, `aws_secret_access_key`
- `region_name`
- `Config(signature_version=..., connect_timeout=..., read_timeout=...)`
- `retries={"mode": "standard", "total_max_attempts": 1}`; SDK 내부 중첩 재시도는 끈다.
- TLS certificate verification 활성화

`max_attempts`는 botocore 호출별 재시도가 아니라 bootstrap의 파일 세트 전체 재시도 횟수다. 각 시도와
streaming chunk 사이에서 공통 monotonic deadline을 확인하므로 여러 SDK 재시도가 전체 기동 상한을
무력화하지 않게 한다.

## 5. Object Storage 파일 계약

### 5.1 파일별 명시적 key 매핑

원격 Object Storage에는 앱이 요구하는 디렉터리 구조, 공통 prefix, manifest가 없다고 전제한다. 앱은
`PutObject`, `CopyObject`, `DeleteObject`를 호출하지 않으며 기존 객체를 이동하거나 이름을 바꾸지 않는다.

Basecase는 논리 역할과 로컬 target을 코드가 소유하고, source만 설정에서 받는다.

| 논리 역할 | 설정 source | 다운로드 후 로컬 target |
|---|---|---|
| Demand | `objects.basecase.demand.object_key` | `basecase/Demand Model_Input.xlsm` |
| Supply | `objects.basecase.supply.object_key` | `basecase/Supply Model_Input.xlsm` |
| Trade | `objects.basecase.trade.object_key` | `basecase/Trade Model_Input.xlsm` |

LUT 설정 파일은 `objects.lut.config.object_key`에서 읽어 로컬
`lut/config/lut_parameters.yaml`에 둔다. LUT CSV는 설정의 각 `lut_relative_path`를 로컬 target으로,
같은 항목의 `object_key`를 source로 사용한다. 따라서 원격 파일명과 디렉터리가 LUT YAML의 경로 또는 로컬
구조와 달라도 된다.

상위 `bucket`은 기본 bucket 이름이다. 각 파일 location은 선택적 `bucket` override와 필수 `object_key`로
구성하여, 파일들이 서로 다른 bucket에 있어도 같은 endpoint/credential 범위에서 지정할 수 있다. override를
생략하면 기본 bucket을 사용한다. `object_key`는 resolved bucket 안의 정확한 전체 key이며 URL이나 로컬 파일
경로로 해석하지 않고 botocore에 그대로 전달한다. basename 추론, prefix 결합, URL decode, 슬래시 정규화를
하지 않는다. 빈 bucket/key와 key의 NUL/control character만 거부한다. 반면 `lut_relative_path`는 로컬
target이므로 기존 LUT registry의 path traversal 방어 규칙을 적용한다.

### 5.2 다운로드 대상 결정

bucket listing은 사용하지 않는다. 모든 `HeadObject`/`GetObject`는 설정에 등록된 exact key만 대상으로 한다.

1. Basecase는 Demand/Supply/Trade 세 논리 역할에 object key가 모두 있는지 확인한다.
2. 설정된 LUT config key를 먼저 다운로드해 staging의 `lut/config/lut_parameters.yaml`에 둔다.
3. 기존 `load_parameter_spec_registry(..., lut_root=<staging>/lut)`로 YAML shape과 참조 상대경로를 검증한다.
4. `model_parameter_lut_enabled=true`이면 registry의 각 resolved absolute `referenced_path`를
   `referenced_path.relative_to(staging_lut_root).as_posix()`로 변환한다. 이 값과 POSIX canonical 형태의
   설정 `lut_relative_path`를 case-sensitive 완전일치로 비교하며 정확히 하나 존재해야 한다. 누락 또는
   canonical 변환 후 중복이면 remote 설정 실패다.
5. 매칭된 각 object key를 해당 `referenced_path` 위치로 다운로드한다.
6. `model_parameter_lut_enabled=false`이면 LUT YAML까지만 받고 CSV는 요청하지 않는다. 이는 현재
   `validate_lut_startup(False, ...)`가 YAML만 검증하는 동작과 일치한다.
7. 원격 bucket의 다른 객체는 알 필요가 없고, 설정에 있지만 현재 YAML이 참조하지 않는 LUT 매핑은
   다운로드하지 않으며 warning summary에만 남긴다.

LUT YAML에 선언된 경로는 기존 registry 규칙대로 절대경로, `..`, `.`, 역슬래시, LUT root 탈출을
거부한다. Basecase object key의 basename은 검사하지 않는다. 논리 역할별 target 파일명은 앱이 고정하므로
원격 이름과 무관하게 기존 loader 계약을 만족한다.

### 5.3 manifest 없는 파일 세트의 일관성 보완

원격 manifest나 공통 release version이 없고 앱에 쓰기 권한도 없으므로, 여러 파일이 동일 버전의 세트인지
강하게 증명할 수는 없다. 구현은 원격 구조를 바꾸지 않는 범위에서 다음 best-effort 검증을 수행한다.

1. LUT config를 `HeadObject`/`GetObject`하고 응답 metadata를 기록한 뒤 YAML을 parse한다.
2. Basecase 3개와 YAML이 참조하는 LUT 매핑 전체에 대해
   `HeadObject` metadata(`ETag`, `ContentLength`, `LastModified`)를 수집한다.
3. 각 객체를 staging에 streaming 다운로드하고 응답 길이와 최초 metadata를 비교한다.
4. LUT config를 포함한 필수 key 전체를 다시 `HeadObject`하여 시도 중 metadata가 바뀌지 않았는지 확인한다.
5. 변경이 감지되면 staging을 폐기하고 설정된 `max_attempts` 범위에서 전체 세트를 다시 받는다.
6. 반복 실패 시 packaged 리소스로 폴백한다.

이 검증은 다운로드 도중의 변경을 탐지하지만, 앱 기동 전에 upstream이 일부 객체만 변경한 뒤 멈춘 상태는
구분할 수 없다. 그 경우 기존 LUT schema/value 검증과 Basecase open/preload 검증을 통과한 세트만 사용한다.
검증을 통과하더라도 업무적으로 동일 버전임을 보장하지 못하는 점은 잔여 리스크로 명시한다.

ETag는 multipart upload나 server-side encryption에서 콘텐츠 SHA-256을 의미하지 않을 수 있으므로
checksum으로 간주하지 않는다. 다운로드한 모든 파일의 SHA-256은 로컬 fingerprint와 진단용으로 계산하고,
실제 데이터 유효성은 기존 LUT/Basecase semantic validation으로 판단한다. 추후 upstream이 checksum이나
version API를 제공하면 선택적 검증 정보로 추가할 수 있지만 이번 기능의 선행조건으로 두지 않는다.

## 6. 부트스트랩과 원자적 활성화

### 6.1 로컬 디렉터리

패키지 `resources/`를 직접 덮어쓰지 않는다. 설정한 writable runtime root를 사용한다.

```text
<local_root>/
├── .bootstrap.lock
├── decision.json
├── staging-<uuid>/                  # 작업 중에만 존재
└── releases/
    └── <fingerprint>/
        ├── .complete.json
        ├── basecase/
        └── lut/
```

- staging과 release는 같은 filesystem에 둬 directory rename이 atomic하게 동작하도록 한다.
- fingerprint는 정렬된 `relative_path + SHA-256` 목록의 SHA-256이다.
- release 디렉터리는 만들어진 뒤 수정하지 않는다.
- `.complete.json`에는 source object metadata, 파일 크기/SHA-256, 완료 시각을 기록하되 credential은 넣지 않는다.
- `decision.json`은 이번 pod가 사용할 source(`object_storage` 또는 `packaged`), release fingerprint,
  안전하게 정규화한 fallback 사유를 기록한다.
- `resource_config_fingerprint`는 endpoint URL, region, signature version, resolved bucket/object key 매핑,
  canonical LUT 상대경로 매핑, LUT enabled 정책을 canonical JSON으로 직렬화해 SHA-256한 값이다. credential,
  timeout, local path는 포함하지 않는다.

`.complete.json`과 `decision.json`은 프로세스 간 동기화를 위한 앱 로컬 상태 파일이다. Object Storage에
요구하는 manifest가 아니며 업로드되지 않는다.

기존 `decision.json`은 다음을 모두 만족할 때만 유효하다.

- schema version과 `resource_config_fingerprint`가 현재 설정과 일치한다.
- `object_storage` 결정이면 release 경로가 `local_root/releases` 내부이고 `.complete.json`의 config/resource
  fingerprint가 decision과 일치한다.
- `.complete.json`이 선언한 모든 파일이 존재하고 크기가 일치한다. 각 worker의 이어지는 semantic
  validation/preload가 내용 유효성을 다시 확인한다.
- `packaged` 결정이면 packaged 경로가 존재하며 이어지는 validation/preload를 통과한다.

하나라도 만족하지 않으면 lock 안에서 stale decision/incomplete release를 폐기하고 새로 결정한다. 따라서
같은 volume을 재사용하더라도 파일 경로 설정 변경이 이전 release를 잘못 재사용하지 않는다.

기본 경로는 pod/container 로컬 ephemeral 영역이어야 한다. Kubernetes `readOnlyRootFilesystem`을 사용할
경우 `local_root`에 `emptyDir`을 mount한다. pod 교체 시 다시 동기화하며, 같은 pod의 worker respawn이나
container crash restart에서는 이미 완성된 decision/release를 재사용할 수 있다. 원격 파일 갱신 반영은
새 pod rollout으로 수행한다.

### 6.2 프로세스 락

Linux runtime에서 표준 라이브러리 `fcntl.flock()` 기반 exclusive lock을 사용한다. 별도 dependency를
추가하지 않는다.

- lock 대기는 `asyncio.to_thread()` 내부에서 수행하여 event loop를 block하지 않는다.
- 첫 worker가 remote validation, download, release 생성, source 결정을 수행한다.
- 나머지 worker는 lock 해제 후 `decision.json`을 읽고 네트워크 호출 없이 같은 source를 사용한다.
- worker가 비정상 종료되면 OS가 file descriptor와 lock을 해제한다.
- 남은 staging 디렉터리는 다음 lock 소유자가 정리한다.
- lock 소유자의 remote 작업에는 `bootstrap_timeout_seconds` monotonic deadline을 적용하고, connector는 요청
  전과 streaming chunk 사이에 이를 확인한다. deadline 소진 시 현재 I/O의 안전한 중단 지점에서 remote
  시도를 끝내고 packaged decision을 쓴다.
- 대기 worker는 `lock_timeout_seconds`까지만 기다린다. timeout 시 worker startup을 실패시키며 독자적으로
  packaged source를 선택하지 않는다. 그래야 이미 실행 중인 lock 소유자와 source가 갈리지 않는다.

현재 `Dockerfile.model_param`의 Gunicorn `TIMEOUT=600`초는 기본 lock timeout 500초보다 크다. 배포에서
timeout 값을 바꿀 때는 `Gunicorn TIMEOUT > lock_timeout_seconds + DB/MLflow/preload 최대 예상시간`을
유지한다. 이미 시작한 socket read는 deadline 직후에도 최대 `connect_timeout_seconds +
read_timeout_seconds` 동안 반환을 기다릴 수 있으므로 `lock_timeout_seconds`와 Gunicorn timeout은 이
여유도 포함한다.

pod replica별 filesystem은 분리되어 있으므로 replica마다 한 번씩 다운로드하는 것은 정상 동작이다.

### 6.3 상세 흐름

```text
lifespan 시작
  ├─ settings/logging/MLflow 초기화
  ├─ DB schema validation
  ├─ LUT policy 생성
  └─ resolve_and_preload_model_parameter_resources()
       ├─ storage.enabled=false
       │    └─ packaged 경로 validation/preload → runtime 등록
       └─ storage.enabled=true
            ├─ process lock 획득
            ├─ 유효한 decision.json 존재?
            │    ├─ yes: 결정된 source/path 반환
            │    └─ no
            │         ├─ remote 설정 검증
            │         ├─ 논리 파일별 exact object key 매핑 검증
            │         ├─ unique staging 생성
            │         ├─ LUT YAML 선행 다운로드/parse
            │         ├─ Basecase 3개 + 활성 LUT CSV 다운로드
            │         ├─ metadata 2-pass consistency 및 size/SHA-256 계산
            │         ├─ fingerprint release로 atomic rename
            │         ├─ remote LUT/Basecase semantic validation/preload
            │         ├─ 성공: object_storage decision atomic write
            │         └─ 실패: staging/inactive release 정리,
            │                  cache clear,
            │                  packaged validation/preload,
            │                  packaged decision atomic write
            ├─ lock 해제
            ├─ 현재 worker에 cache가 없으면 결정된 경로 validation/preload
            └─ worker runtime에 동일 source/path 등록
  ├─ callback OAuth token prefetch
  └─ yield: 요청 수락
```

remote 검증에는 기존 함수를 그대로 사용한다.

- `validate_lut_startup(enabled, policy, config_path=..., lut_root=...)`
- `preload_basecase_runtime_cache(basecase_dir_path=...)`

Basecase 객체 3개의 누락, 0 byte, open 실패는 remote 실패로 취급한다. workbook 내부 sheet/record warning은
현재 Basecase preload의 기존 의미를 유지하여 startup summary warning으로 남기되 remote source 자체를
거부하는 새 비즈니스 규칙은 추가하지 않는다.

원격에서 packaged로 전환하기 전 `clear_lut_runtime_cache()`와
`clear_parameter_mapping_runtime_cache()`를 호출하여 source가 다른 cache가 섞이지 않게 한다.

### 6.4 폴백 정책

다음은 모두 packaged 폴백 대상이다.

- remote 필수 설정 누락 또는 미치환 환경변수
- endpoint 연결, timeout, 인증/권한, bucket/key 오류
- 필수 객체 누락 또는 빈 객체
- 다운로드 길이 불일치
- 다운로드 중 object metadata 변경 및 재시도 소진
- LUT YAML/path/CSV schema/value validation 실패
- Basecase workbook open/preload 실패
- runtime 디렉터리 생성, 쓰기, rename 실패

remote 실패 시 앱은 다음 순서로 처리한다.

1. credential이 제거된 원인과 `remote_sync_failed`를 ERROR log로 남긴다.
2. `resource_source=packaged`, `fallback_active=true`를 WARNING log로 남긴다.
3. packaged 파일도 기존 startup validation/preload를 통과해야 한다.
4. packaged 검증까지 실패하면 더 이상 안전한 source가 없으므로 startup을 실패시킨다.

폴백 성공은 readiness 실패로 처리하지 않는다. 이는 가용성을 우선한 명시적 사용자 결정이다. 대신 최종
startup summary와 요청별 model-parameter resource summary에 source와 fallback 여부를 구조화해 남겨
운영자가 장기간 원격 장애를 놓치지 않도록 한다. 별도 public health API 추가는 이번 범위에서 제외한다.

단, 다른 worker가 source를 결정 중인 상태에서 발생한 lock wait timeout은 remote 데이터 실패로 간주해
독자적으로 폴백하지 않는다. 해당 worker만 startup을 실패시키고 재기동 후 이미 확정된 공통 decision을
따르게 한다.

## 7. 요청 처리 연동

`model_param.py`가 선택된 `ModelParameterResourcePaths`를 worker runtime에 등록한 뒤
`flows/propose_parameters/nodes.py`의 모든 resource loader 호출을 다음처럼 변경한다.

- `_knowledge_base_from_context()`:
  `basecase_dir_path=str(active_paths.basecase_dir)` 전달
- `load_basecase_samples()`:
  `get_parameter_spec_registry(active_paths.lut_config_path, lut_root=active_paths.lut_root)` 사용
- `filter_basecase_records_by_slots()`:
  동일 active LUT registry/catalog 사용

startup preload와 요청 처리 모두 같은 absolute path를 사용하므로 기존 path/mtime/size/content 기반 cache가
그대로 유효하다. source가 결정된 뒤 실행 중 파일을 교체하지 않으며 hot reload를 지원하지 않는다.

내부 `resolved_config`/structured log에는 다음 비밀정보가 아닌 진단값을 추가할 수 있다.

- `model_parameter_resource_source`: `object_storage` 또는 `packaged`
- `model_parameter_resource_fingerprint`: remote 성공 시 fingerprint
- `model_parameter_resource_fallback_active`: boolean

HTTP request/response schema는 변경하지 않는다.

## 8. 오류 처리와 보안

- connector의 botocore `ClientError`, `BotoCoreError`, streaming/file I/O 오류는
  `MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=<sanitized>)`로 정규화한다.
- fallback 경계는 agent bootstrap 한 곳에만 두고 개별 loader가 임의로 source를 바꾸지 않게 한다.
- access key에는 설정된 resolved bucket/object key의 `GetObject`와 `HeadObject` 읽기 권한만 부여한다.
- bucket listing을 사용하지 않으므로 `ListBucket` 권한은 필요하지 않다.
- upload/delete 권한은 앱 credential에 부여하지 않는다.
- secret은 Kubernetes Secret 또는 배포 플랫폼 secret으로 환경변수 주입하며 ConfigMap, Git, 이미지에
  평문으로 두지 않는다.
- object key와 local relative path를 별도로 검증하여 path traversal과 패키지 경로 overwrite를 막는다.
- 다운로드는 bounded chunk로 streaming하여 10 MiB급 CSV 전체를 connector에서 중복 메모리화하지 않는다.
- staging 파일은 현재 프로세스 사용자만 접근할 수 있는 권한으로 생성한다.

## 9. 배포 변경

### 9.1 Docker

- `Dockerfile.model_param`의 CMD와 worker 수는 변경하지 않는다.
- 기존 `COPY apps ./apps`를 유지하여 packaged fallback 파일을 이미지에 포함한다.
- runtime download는 `/tmp` 또는 설정한 writable directory만 사용한다.
- Gunicorn 전처리 script나 `--preload`에 의존하지 않는다.

### 9.2 Kubernetes/배포 환경

- ConfigMap: enabled, endpoint, region, signature version, bucket, 파일별 object key 매핑, local root,
  timeout/retry
- Secret: access key ID, secret access key
- Deployment: Secret을 환경변수로 주입
- read-only root filesystem이면 local root에 pod-local `emptyDir` mount
- parameter-agent의 실제 배포 manifest/Helm values가 이 repo 밖에 있다면 동일 설정을 외부 배포 정의에도
  반영

현재 repo의 raw `devops/k8s` manifest는 공용/Scenario Agent 성격이므로 구현 시 실제 Parameter Agent
배포 소유 위치를 확인한 뒤 sample과 실제 배포 설정을 각각 갱신한다.

## 10. 테스트 계획

### 10.1 설정 테스트

`tests/test_config_loader.py`에 다음을 추가한다.

- storage 설정이 없을 때 `enabled=false` 기본값
- 중첩 YAML 로드와 `MODEL_PARAMETER_RESOURCE_STORAGE__*` override
- SecretStr repr/model dump redaction
- enabled=true에서 미치환 placeholder/필수값 누락이 remote validation 오류가 되고 packaged 폴백 가능한지
- timeout/retry의 0 이하 값, `bootstrap_timeout_seconds >= lock_timeout_seconds`, 잘못된 endpoint 형식 거부

### 10.2 Object Storage connector 테스트

신규 외부 emulator dependency 없이 botocore `Stubber`와 fake `StreamingBody`를 사용한다.

- client에 endpoint, region, signature version, timeout/retry가 정확히 전달됨
- exact bucket/key로 HeadObject/GetObject 호출
- chunk streaming, size/SHA-256 계산, body close
- 403, NoSuchKey, timeout, connection 오류의 안전한 오류 변환
- exception/log에 credential과 Authorization header가 포함되지 않음

### 10.3 Bootstrap 테스트

- enabled=false이면 Object Storage client를 생성하지 않고 packaged 경로 사용
- 설정된 서로 다른 bucket/key의 Basecase 3개를 canonical 로컬 파일명으로 배치
- LUT YAML 참조 상대경로와 설정된 object key를 정확히 매칭하고 참조 CSV만 다운로드
- resolved absolute `referenced_path`를 staging LUT root 기준 POSIX 상대경로로 바꿔 case-sensitive 매칭
- LUT 매핑 누락/중복은 remote 실패, 미참조 매핑과 bucket의 다른 객체는 미다운로드
- LUT disabled이면 YAML까지만 받고 CSV는 요청하지 않음
- LUT YAML의 absolute/`..`/역슬래시/중복 경로 거부
- partial download와 validation 실패 시 staging 정리 및 incomplete release 비활성
- HeadObject metadata 변경 감지, 전체 재시도, 재시도 소진 후 packaged 폴백
- remote 성공 시 fingerprint release와 `.complete.json`/`decision.json` atomic 생성
- remote 설정/인증/누락/손상 실패 시 packaged 폴백
- packaged까지 손상되면 startup 실패
- 여러 프로세스가 동시에 bootstrap해 네트워크 동기화가 한 번만 수행되고 같은 decision을 사용
- object key/LUT policy 변경 시 config fingerprint 불일치로 stale decision/release를 재사용하지 않음
- lock 소유자의 bootstrap deadline은 packaged decision으로 수렴하고, 대기 worker lock timeout은 startup 실패
- 비정상 종료 뒤 OS lock 해제와 orphan staging 정리

### 10.4 Agent 통합/회귀 테스트

- lifespan 호출 순서가 DB validation → resource resolution → LUT/Basecase preload인지 검증
- 원격 성공 시 startup뿐 아니라 실제 `load_basecase_samples`와 후속 LUT lookup이 remote path를 사용
- 원격 실패 시 두 호출 경로 모두 packaged path만 사용
- worker별 LUT/Basecase process cache가 선택된 경로로 warm-up됨
- 기존 LUT record count/value/version 테스트 유지
- 기존 Basecase workbook/sheet/record 추출 테스트 유지
- packaged resource 존재 계약 테스트 유지
- `GUNICORN_WORKERS=3` container smoke test에서 source/fingerprint가 동일하고 부분 파일이 노출되지 않음

### 10.5 NCP 수동 검증

실제 credential은 테스트 코드나 문서에 넣지 않고 배포 secret으로만 주입한다.

1. 기존 파일을 변경하지 않고 제공받은 bucket과 파일별 경로를 설정에 등록
2. Object Storage 쓰기 권한이 없는 credential로 기동해 read-only 동작을 확인
3. startup source와 로컬 fingerprint를 통해 원격 Basecase/LUT가 선택됐는지 확인
4. 앱 설정에서 key 하나를 존재하지 않는 값으로 바꾼 경우, 잘못된 secret, 잘못된 endpoint 각각에서
   packaged fallback과 ERROR/WARNING log 확인
5. 세 worker가 동일 source/fingerprint를 기록하는지 확인
6. 새 pod 기동 시 원격을 다시 확인하고, 실행 중에는 source가 바뀌지 않는지 확인

## 11. 완료 기준

- S3 사용이 꺼지면 현재 동작과 결과가 변하지 않고 네트워크 호출이 없다.
- S3 사용이 켜지고 원격 세트가 유효하면 pod당 한 번 다운로드하고 모든 worker/요청이 같은 원격 세트를
  사용한다.
- 원격 설정, 통신, 인증, 객체, 데이터 검증 중 하나라도 실패하면 모든 worker가 packaged 세트로 동작한다.
- 원격과 packaged 세트가 한 요청 안에서 섞이지 않는다.
- 다운로드 중 파일이나 incomplete release가 요청 처리에 노출되지 않는다.
- secret이 source, log, exception, test artifact에 노출되지 않는다.
- 기존 HTTP API와 DB schema에는 변경이 없다.
- 자동화 테스트와 3-worker smoke test가 통과한다.

## 12. 영향 범위와 잔여 리스크

### 영향 범위

- 설정 모델과 배포 환경변수/Secret
- 신규 Object Storage connector
- Model Parameter Agent resource bootstrap/runtime
- `model_param.py` lifespan
- proposal node의 Basecase/LUT 경로 전달
- 관련 자동화 테스트와 architecture/flow 문서

### 잔여 리스크

- 원격 manifest/version 정보가 없으므로 파일별 metadata가 시도 중 변하지 않았음은 확인할 수 있지만,
  기동 전에 만들어진 부분 갱신 세트의 업무 버전 일치 여부는 증명할 수 없다.
- LUT YAML의 참조 경로가 바뀌면 설정의 `lut_relative_path` 매핑도 함께 갱신해야 한다. 누락 시 원격 세트
  전체를 사용하지 않고 packaged로 폴백한다.
- remote 장애가 packaged fallback으로 가려질 수 있다. ERROR/WARNING structured log와 source summary 모니터링이
  운영 필수다.
- startup 시간은 Object Storage 다운로드와 LUT/Basecase preload만큼 증가한다. timeout/retry 상한을 두고
  3-worker 중복 다운로드를 막아 영향을 제한한다.
- NCP와 배포망 연결은 unit test만으로 완전히 검증할 수 없으므로 제공받은 기존 read-only object 경로를
  대상으로 smoke test가 필요하다.

## 13. Claude 협의 결과 반영

`claude-interactive`를 읽기 전용 architecture review로 사용했다.

파일별 key만 알고 원격 구조와 manifest를 바꿀 수 없다는 추가 제약 반영 후에도 재검토했다. Claude는
Critical 문제는 없다고 판단했고 실제 loader signature, LUT CSV 6개, 3-worker 설정과 경로 호출부를
교차 확인했다. 재검토에서 지적한 다음 세 항목을 최종 설계에 보완했다.

- resolved LUT path와 설정 상대경로의 canonical/case-sensitive 매칭 규칙
- `decision.json` 재사용 시 resource config fingerprint와 release complete 상태 검증
- bootstrap/lock timeout 상한과 Gunicorn `TIMEOUT` 관계, lock timeout 시 source 분기 금지

수용한 제안:

- 외부 S3 adapter와 Agent 전용 resource policy 분리
- staging download, 세트 단위 atomic activation, process lock
- 기동 preload뿐 아니라 요청 노드까지 동일 active path 사용
- secret 환경변수 주입, 최소 읽기 권한, remote 실패 정책 명시
- 멀티 Gunicorn worker와 회귀/통합 테스트 포함

조정한 제안:

- Claude의 1순위였던 Gunicorn fork 전 bootstrap은 Docker/Gunicorn 실행 경로에 결합되고 직접 uvicorn 실행과
  달라지므로 채택하지 않았다. lifespan + process lock으로 모든 실행 경로를 통일했다.
- prefix 전체 listing/미러링 제안은 원격 디렉터리와 파일을 변경할 수 없고 공통 구조도 보장되지 않으므로
  채택하지 않았다. 사용자에게 제공되는 파일별 실제 key를 설정에 1:1 매핑하고 exact key만 Head/Get한다.
- manifest release 제안은 원격 manifest가 없고 앱도 원격을 수정할 수 없으므로 적용하지 않았다. 대신
  2-pass metadata 확인, 로컬 fingerprint, 기존 semantic validation을 결합했다.
- Claude가 기본 fail-fast를 권고했으나 사용자가 가용성을 위해 packaged fallback을 명시적으로 선택하여
  최종 설계는 remote 실패 시 packaged validation 후 계속 기동하도록 확정했다.

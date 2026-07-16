# Model Parameter Agent Object Storage 리소스 동기화 최종 설계

> 상태: 구현 전 최종 합의 설계
>
> 작성일: 2026-07-15
>
> 대상: 루트 `model_param.py`로 기동하는 `model_parameter_agent`

## 1. 목적

`model_parameter_agent`가 기동할 때 NCP S3-compatible Object Storage에서 Basecase Excel과
LUT CSV를 내려받고, 전체 파일 세트의 다운로드와 검증이 끝난 뒤에만 활성화한다.

이 문서는 다음 두 대안 설계를 검토한 뒤 확정한 최종안이다.

- `OBJECT_STORAGE_RESOURCE_SYNC_DESIGN.md`
- `model_parameter_agent_s3_resource_bootstrap.md`

## 2. 확정 정책

- Object Storage에는 현재 사용하는 Basecase/LUT 파일 한 세트만 존재한다고 본다.
- 원격 리소스의 과거 버전이나 release history는 관리하지 않는다.
- 실행 중 refresh하지 않으며, 새 원격 파일 반영은 새 pod rollout으로 수행한다.
- Object Storage 인증·접속 설정과 파일별 위치·업무 스키마는 하나의 `config.yaml` 안에서 영역을 분리한다.
- 파일별 위치와 리소스 업무 스키마는 최상위 `model_parameter_resources` 영역에서 함께 관리한다.
- 원격 파일명과 로컬 파일명은 독립적으로 설정한다.
- bucket listing 없이 설정된 exact `bucket/object_storage_path`만 `HeadObject`/`GetObject`한다.
- `decision.json`은 사용하지 않는다.
- 검증된 활성 source는 `current` 심볼릭 링크 하나로 표현한다.
- 원격 동기화 실패 시 이미지에 포함된 packaged 리소스로 폴백한다.
- Gunicorn 멀티 worker 간 동기화는 `fcntl.flock()`으로 처리한다.
- 요청 처리 중에는 `current`를 다시 해석하지 않고, worker 기동 시 resolve한 immutable 경로를 사용한다.
- 기존 외부 HTTP API, callback body, DB schema는 변경하지 않는다.

## 3. 대상 리소스와 제외 범위

### 3.1 동기화 대상

Basecase는 다음 세 논리 역할을 필수로 한다.

- `demand`
- `supply`
- `trade`

LUT는 `config.yaml`의 `model_parameter_resources.lut` 영역에서 실제로 참조하는 CSV를 대상으로 한다.
`model_parameter_lut_enabled=false`이면 LUT CSV는 다운로드하지 않고 Basecase만 동기화한다.

### 3.2 제외 범위

- DB에서 로드하는 mapping xlsx
- Object Storage upload, copy, delete
- bucket listing
- 원격 파일 버전 관리와 과거 버전 롤백
- 실행 중 polling, hot reload, periodic refresh
- public health API 추가

## 4. 설정 책임 분리

### 4.1 앱 설정과 Secret

Object Storage 연결에 필요한 공통 설정은 `apps/common/configs/config.py`의 중첩 설정 모델로 관리한다.

```yaml
model_parameter_resource_storage:
  enabled: false
  endpoint_url: "https://kr.object.ncloudstorage.com"
  region_name: "kr-standard"
  signature_version: "s3v4"
  bucket: ""

  access_key_id: "${NCP_OBJECT_STORAGE_ACCESS_KEY_ID}"
  secret_access_key: "${NCP_OBJECT_STORAGE_SECRET_ACCESS_KEY}"

  local_root: "/tmp/skmip/model-parameter-resources"

  connect_timeout_seconds: 10
  read_timeout_seconds: 60
  max_attempts: 3
  bootstrap_timeout_seconds: 420
  lock_timeout_seconds: 500
```

관리 위치는 다음과 같이 분리한다.

| 설정 | 관리 위치 |
|---|---|
| enabled, endpoint, region, signature version, 기본 bucket | ConfigMap |
| access key ID, secret access key | Secret |
| local root, timeout/retry | ConfigMap의 `config.yaml` |
| 파일별 Object Storage 경로와 로컬 경로 | ConfigMap의 `config.yaml:model_parameter_resources` |

`access_key_id`와 `secret_access_key`는 `SecretStr`로 선언한다. 앱 코드는 설정을
`apps.common.configs.config.get_settings()`로 읽으며 `os.environ`을 직접 참조하지 않는다.

### 4.2 리소스 설정

Pod가 단일 파일만 mount할 수 있으므로 별도 manifest를 두지 않고 `APP_CONFIG`가 가리키는
`config.yaml`의 최상위 `model_parameter_resources` 영역에 Basecase/LUT 정의를 둔다.
`get_settings()`는 worker별로 설정 snapshot을 한 번만 읽고 재사용하며, bootstrap은 이 메모리 객체를
검증한 뒤 활성 LUT registry까지 process runtime에 고정한다.

운영자가 입력하는 `schema_version`은 두지 않는다. 리소스 스키마와 release metadata 버전은 코드 내부
상수로 관리해 semantic hash와 `current` 검증에 사용한다.

## 5. 리소스 설정 스키마

```yaml
model_parameter_resources:
  basecase:
    demand:
      path: "Demand Model_Input.xlsm"
      object_storage_path: "external/basecase/demand-final.xlsm"

    supply:
      path: "Supply Model_Input.xlsm"
      object_storage_path: "external/basecase/supply-final.xlsm"

    trade:
      path: "Trade Model_Input.xlsm"
      object_storage_path: "external/basecase/trade-final.xlsm"

  lut:
    GDP:
      adapter: gdp_growth
      files:
        values:
          path: "Demand_Model_LUT_BCInput_value_based_t2.csv"
          object_storage_path: "external/lut/gdp/gdp-master.csv"
          required_columns:
            - RE Base Case GDP and Population Data_Country
            - RE Base Case GDP and Population Data_Year
            - RE Base Case GDP and Population Data_GDP
      key_axes: [Country, Year]

    PMI:
      adapter: tabular
      layout: year_columns
      files:
        values:
          path: "Demand_Model_Input_PMIInput_value_based_t2.csv"
          object_storage_path: "external/lut/pmi/pmi-input.csv"
          axis_columns:
            Country: Base Case PMI Input (do not change)_Country
            Month: Base Case PMI Input (do not change)_Month
          year_value_column: Base Case PMI Input (do not change)_{year}.0
      key_axes: [Country, Year, Month]

    Temperature:
      adapter: temperature_degree_days
      files:
        hdd:
          path: "Demand_Model_Input_WeatherInput_value_based_t1.csv"
          object_storage_path: "external/weather/heating-degree-days.csv"
          required_columns:
            - Base Case HDD Input_Country
            - Base Case HDD Input_Month
            - Base Case HDD Input_{year}.0
        cdd:
          path: "Demand_Model_Input_WeatherInput_value_based_t2.csv"
          object_storage_path: "external/weather/cooling-degree-days.csv"
          required_columns:
            - Base Case CDD Input_Country
            - Base Case CDD Input_Month
            - Base Case CDD Input_{year}.0
      key_axes: [Country, Year, Month]
```

모든 파일은 앱 설정의 공통 `bucket`을 사용한다. 파일별 bucket override는 지원하지 않는다.

### 5.1 `path`와 `object_storage_path`의 의미

- `path`: packaged 리소스와 다운로드 후 release에서 사용할 로컬 상대경로
- `object_storage_path`: 공통 Object Storage bucket 내부에서 읽을 정확한 bucket-relative key

예를 들어 다음 설정은 원격 이름과 로컬 이름이 서로 달라도 정상 동작한다.

```yaml
path: "Demand Model_Input.xlsm"
object_storage_path: "vendor/model-input/final_demand_202607_v3"
```

처리 결과는 다음과 같다.

```text
GetObject(bucket, "vendor/model-input/final_demand_202607_v3")
  -> staging/basecase/Demand Model_Input.xlsm.tmp
  -> staging/basecase/Demand Model_Input.xlsm
  -> current/basecase/Demand Model_Input.xlsm
```

Object Storage key의 basename, 확장자, URL 형태를 로컬 파일명 결정에 사용하지 않는다.
실제 콘텐츠가 유효한 XLSM/CSV인지는 기존 Basecase/LUT semantic validation으로 판단한다.

## 6. 리소스 설정 검증

### 6.1 공통 경로 검증

- `path`는 비어 있지 않은 POSIX 상대경로여야 한다.
- 절대경로, `..`, `.`, 역슬래시와 local root 탈출을 거부한다.
- 서로 다른 원격 객체가 동일한 local target을 사용하면 설정 오류다.
- 같은 local target을 여러 LUT parameter가 참조하면 동일한 bucket/object storage path여야 한다.
- 같은 원격 객체를 서로 다른 local target으로 매핑하는 것은 허용할 수 있으나 각 target은 별도 검증한다.
- `object_storage_path`는 URL이나 로컬 경로로 해석하거나 normalize하지 않고 S3 API의 object key로 그대로 전달한다.
- 빈 bucket/key와 NUL/control character가 포함된 key는 거부한다.

### 6.2 Basecase 검증

- `demand`, `supply`, `trade`가 정확히 하나씩 존재해야 한다.
- 세 역할의 local target path는 서로 달라야 한다.
- Object Storage 활성화 시 세 역할 모두 유효한 object location이 있어야 한다.
- 다운로드한 파일은 0 byte가 아니어야 하고 workbook open에 성공해야 한다.

### 6.3 LUT 검증

- 기존 adapter, layout, column, axis 검증을 유지한다.
- Object Storage 활성화 시 실제 활성 LUT가 참조하는 모든 파일에 object location이 있어야 한다.
- LUT가 비활성화되어 있으면 object location이 있더라도 LUT CSV는 다운로드하지 않는다.
- 기존 최상위 parameter mapping은 `model_parameter_resources.lut` 영역 아래에 둔다.

`config.yaml`의 YAML syntax 또는 로컬 semantic schema 자체가 잘못되면 packaged 리소스도 안전하게 해석할 수 없으므로
startup을 실패시킨다. 반면 object location 누락·충돌·형식 오류는 원격 설정 오류로 분류하여 packaged
fallback을 시도한다.

## 7. 로컬 디렉터리와 활성화 모델

```text
<local_root>/
├── .bootstrap.lock
├── current -> releases/remote-abc123/
├── staging-<uuid>/
└── releases/
    ├── remote-abc123/
    │   ├── .complete.json
    │   ├── basecase/
    │   └── lut/
    └── packaged-<config-fingerprint>/
        ├── .complete.json
        ├── basecase -> <package>/resources/basecase
        └── lut -> <package>/resources/lut
```

`remote-abc123`은 업무 버전이 아니라 다운로드된 파일 세트의 content fingerprint다.
과거 원격 release history는 보존하지 않으며, 정상 상태에서는 활성 remote release 하나만 유지한다.
다운로드 중에만 staging이 추가로 존재한다.

### 7.1 `current`가 source 결정이다

```text
원격 성공:
current -> releases/remote-abc123

원격 실패:
current -> releases/packaged-<config-fingerprint>
```

`decision.json`은 두지 않는다. `current`의 target과 target의 `.complete.json`을 함께 검증하여 활성 source를
판단한다.

### 7.2 원자적 교체

```text
current.tmp -> releases/remote-abc123
os.replace(current.tmp, current)
```

임시 symlink와 `current`는 같은 filesystem에 생성한다. 다른 worker는 이전 target 또는 새 target 중 하나만
관찰하며 중간 상태는 관찰하지 않는다.

## 8. `.complete.json`

`decision.json`은 제거하지만 release 검증과 운영 진단을 위해 `.complete.json`은 유지한다.

```json
{
  "schema_version": 1,
  "source": "object_storage",
  "resource_config_fingerprint": "...",
  "semantic_schema_hash": "...",
  "resource_fingerprint": "...",
  "fallback_reason": null,
  "files": {
    "basecase/Demand Model_Input.xlsm": {
      "size": 123456,
      "sha256": "..."
    },
    "lut/Demand_Model_LUT_BCInput_value_based_t2.csv": {
      "size": 987654,
      "sha256": "..."
    }
  }
}
```

packaged fallback release에는 `source=packaged`와 credential을 제거한 `fallback_reason`을 기록한다.

`current`는 다음을 모두 만족할 때 유효하다.

- `current`가 symlink다.
- symlink target이 `<local_root>/releases` 아래다.
- target의 `.complete.json`이 존재하고 파싱 가능하다.
- schema version, resource config fingerprint, semantic schema hash가 현재 설정과 일치한다.
- `model_parameter_resources`에 선언된 필수 파일이 존재하고 기록된 크기와 일치한다.
- packaged release의 내부 symlink가 정확한 package resource 경로만 가리킨다.

## 9. Fingerprint

### 9.1 Semantic schema hash

LUT와 Basecase의 로컬 업무 계약을 나타낸다.

- 코드 내부 리소스 schema version
- Basecase role과 local path
- LUT adapter/layout
- LUT local path
- required/axis/value columns
- key axes와 metadata axes

Object Storage bucket/object key는 포함하지 않는다.

### 9.2 Resource config fingerprint

원격 동기화 설정을 나타낸다.

- endpoint URL
- region과 signature version
- resolved bucket/object key
- local target path
- LUT enabled 정책
- 코드 내부 리소스 schema version

credential, timeout, retry, local root는 포함하지 않는다.

### 9.3 Resource fingerprint

다운로드가 끝난 파일 세트의 정렬된 `relative_path + SHA-256` 목록을 다시 SHA-256하여 계산한다.
ETag는 multipart upload나 암호화 설정에 따라 콘텐츠 hash가 아닐 수 있으므로 checksum으로 사용하지 않는다.

## 10. Object Storage consistency 확인

원격에 release manifest나 version identifier가 없으므로 exact key 세트에 대해 best-effort consistency 검증을
수행한다.

1. 메모리의 `model_parameter_resources`에서 다운로드 계획을 생성한다.
2. 모든 대상에 `HeadObject`하여 ETag, ContentLength, LastModified를 수집한다.
3. 각 object를 staging에 streaming 다운로드하며 SHA-256을 계산한다.
4. `GetObject` 응답 길이와 최초 metadata를 비교한다.
5. 전체 대상에 다시 `HeadObject`한다.
6. 최초/최종 metadata가 다르면 staging을 폐기하고 전체 세트를 재시도한다.
7. 재시도 소진 시 packaged fallback으로 전환한다.

이 검증은 다운로드 중 변경을 탐지하지만, 앱 기동 전에 upstream이 일부 파일만 갱신한 채 멈춘 상태의 업무적
혼합 버전까지 증명할 수는 없다. 최종 방어선은 Basecase/LUT semantic validation이며, 원격 파일 교체는 앱
rollout과 겹치지 않게 일괄 수행하는 운영 절차를 권장한다.

## 11. 기동 흐름

```text
lifespan 시작
  ├─ config.yaml을 settings snapshot으로 1회 로드
  ├─ logging/MLflow 초기화
  ├─ DB schema validation
  ├─ model_parameter_resources 영역을 메모리에서 파싱
  ├─ Basecase/LUT local semantic schema 검증
  └─ resolve_and_preload_model_parameter_resources()
       ├─ storage.enabled=false
       │    └─ packaged 리소스 검증/preload -> runtime 등록
       └─ storage.enabled=true
            ├─ process lock 획득
            ├─ 현재 설정과 일치하는 유효한 current 존재?
            │    ├─ yes: current 재사용
            │    └─ no
            │         ├─ object location 검증
            │         ├─ unique staging 생성
            │         ├─ exact key 세트 HeadObject
            │         ├─ GetObject streaming download
            │         ├─ metadata 2-pass consistency 확인
            │         ├─ Basecase/LUT semantic validation
            │         ├─ .complete.json 기록
            │         ├─ staging -> remote release atomic rename
            │         └─ current symlink atomic swap
            ├─ 원격 실패
            │    ├─ staging 정리
            │    ├─ 원격 validation 중 생성된 cache clear
            │    ├─ packaged 리소스 validation/preload
            │    ├─ packaged release wrapper 생성
            │    └─ current를 packaged release로 atomic swap
            ├─ process lock 해제
            ├─ current target resolve
            ├─ worker runtime에 immutable active paths/LUT registry 등록
            └─ 선택 경로의 LUT/Basecase preload
  ├─ callback OAuth token prefetch
  └─ yield: 요청 수락
```

원격과 packaged 리소스 검증이 모두 실패하면 안전한 source가 없으므로 startup을 실패시킨다.

## 12. 멀티 worker와 runtime

- 첫 worker가 `.bootstrap.lock`을 획득해 동기화, 검증, `current` 교체를 수행한다.
- 후발 worker는 lock 해제 후 유효한 `current`를 재검증한다.
- 후발 worker는 같은 resource config fingerprint의 유효한 `current`가 있으면 원격 동기화를 다시 시도하지 않는다.
- 첫 worker가 packaged를 선택했다면 같은 pod의 모든 worker가 packaged를 사용한다.
- lock wait timeout 시 해당 worker는 독자적으로 source를 선택하지 않고 startup을 실패시킨다.
- worker 비정상 종료 시 OS가 file descriptor와 lock을 해제한다.
- orphan staging은 다음 lock 소유자가 정리한다.

각 worker는 `current`를 한 번 resolve한 실제 target과 활성 LUT registry를 process-local runtime에 등록한다.

```text
source = object_storage | packaged
root = <resolved current target>
basecase_dir = <root>/basecase
lut_root = <root>/lut
resource_config_path = <APP_CONFIG path>
lut_registry = <validated in-memory registry>
resource_fingerprint = <remote 성공 시 fingerprint>
fallback_reason = <packaged 폴백 사유>
```

요청 노드는 runtime의 명시적 경로를 Basecase/LUT loader에 전달한다. 요청 중 `current` symlink가 변경되더라도
이미 등록한 immutable 경로는 바뀌지 않는다. 정상 운영에서는 pod 실행 중 `current`를 교체하지 않는다.

## 13. 오류와 fallback

다음은 packaged fallback 대상이다.

- 원격 필수 설정 누락 또는 미치환 placeholder
- `model_parameter_resources`의 object location 누락·충돌·형식 오류
- endpoint 연결·timeout·인증·권한 오류
- bucket/key 없음
- 필수 객체 누락 또는 빈 객체
- 다운로드 길이 불일치
- 다운로드 중 metadata 변경과 재시도 소진
- Basecase workbook open 실패
- LUT schema/value validation 실패

다음은 worker 간 source 일관성을 보장할 수 없으므로 startup 실패 대상이다.

- process lock 생성·획득 불가
- lock wait timeout
- `local_root` 생성·쓰기 불가
- release rename 또는 `current` atomic swap 불가
- `config.yaml` YAML syntax 또는 local semantic schema 자체가 잘못됨
- packaged 리소스 validation 실패

connector의 botocore/streaming 오류는 credential을 제거한
`MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=...)`로 정규화한다.

## 14. 보안

- Object Storage credential에는 필요한 bucket/key의 `HeadObject`와 `GetObject` 권한만 부여한다.
- `ListBucket`, upload, copy, delete 권한은 부여하지 않는다.
- secret은 Kubernetes Secret 또는 배포 플랫폼 secret으로만 주입한다.
- access key, secret key, Authorization header와 botocore request dump를 로그에 남기지 않는다.
- 전체 object key는 기본 INFO 로그에 남기지 않고 필요한 경우 마스킹하여 DEBUG에만 남긴다.
- 다운로드는 bounded chunk streaming으로 처리한다.
- staging 파일은 애플리케이션 사용자만 접근할 수 있게 생성한다.
- local target path와 symlink target을 각각 검증해 path traversal을 막는다.

## 15. 배포

- `local_root`에는 pod-local `emptyDir`을 mount하는 것을 기본으로 한다.
- `readOnlyRootFilesystem` 환경에서도 `local_root`만 writable하게 제공한다.
- `config.yaml` 하나를 이미지 기본 파일 또는 환경별 ConfigMap mount로 제공한다.
- credential은 Secret 환경변수로 주입한다.
- Object Storage 데이터 갱신은 새 pod rollout으로 반영한다.
- 같은 pod의 worker respawn이나 container restart는 기존 `current`를 재사용할 수 있다.
- PVC 기반 release history와 이전 원격 세대 롤백은 이번 범위에서 제외한다.
- `storage.enabled=false`이면 네트워크 호출, process lock, writable `local_root` 요구 없이 기존 packaged 동작을 유지한다.

## 16. 로깅과 운영 진단

다음 값을 구조화해 기록한다.

- worker 최초 설정 load 시 전체 Settings snapshot(DEBUG, password/secret/token/API key/access key/bearer 마스킹)
- `model_parameter_resource_source`: `object_storage` 또는 `packaged`
- `model_parameter_resource_fingerprint`
- `model_parameter_resource_fallback_active`
- `model_parameter_resource_fallback_reason`
- 다운로드 파일 수, 전체 bytes, 수행시간, 재시도 횟수

원격 실패 후 packaged fallback 성공은 readiness 실패로 처리하지 않는다. 대신 remote sync ERROR와
fallback active WARNING을 모두 남겨 장기간 장애가 가려지지 않게 한다.

## 17. 구현 영향 범위

```text
apps/common/configs/config.py
  - worker별 settings snapshot cache
  - ModelParameterResourceStorageConfig와 model_parameter_resources 영역

apps/connectors/object_storage/
  - S3-compatible HeadObject/GetObject connector

apps/agents/model_parameter_agent/utils/
  - resource_manifest.py: in-memory 리소스 설정 파싱과 다운로드 계획
  - resource_bootstrap.py: lock/staging/release/current/fallback
  - resource_runtime.py: worker별 immutable active paths

apps/agents/model_parameter_agent/utils/lut/registry.py
  - in-memory model_parameter_resources.lut 영역 파싱
  - object_storage_path 필드와 semantic hash 분리

model_param.py
  - DB 검증 이후 bootstrap, 기존 preload 이전에 호출

apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py
  - resource runtime의 활성 경로를 loader에 명시적으로 전달

envs/config.yaml 및 실제 배포 설정
  - 연결 설정, 파일별 매핑/업무 스키마, Secret, ConfigMap, emptyDir

tests/manual/model_parameter_object_storage/
  - MinIO Docker Compose와 테스트 데이터 업로드/실행 스크립트
```

package ownership이나 endpoint-to-flow mapping이 바뀌는 것은 아니므로 기존 외부 API architecture는 유지한다.

## 18. 테스트 계획

### 18.1 리소스 설정

- 기존 LUT 정의를 새 `lut` 영역에서 동일하게 파싱
- Basecase 세 역할 누락·중복 거부
- 원격명과 로컬명이 다른 매핑 성공
- absolute path, `..`, 역슬래시, target collision 거부
- 공통 bucket과 파일별 object_storage_path 결합
- storage disabled일 때 object location 미사용
- semantic hash와 resource config fingerprint 분리
- SecretStr redaction

### 18.2 Connector 단위 테스트

botocore `Stubber`는 실제 endpoint 연동을 대신하는 용도가 아니라 MinIO로 안정적으로 재현하기 어려운
요청 순서와 오류 분기를 검증하는 데 한정한다.

- 설정한 exact bucket/key로만 HeadObject/GetObject 호출
- ListObjects 호출이 없음을 검증
- chunk streaming, body close, size/SHA-256 계산
- 403, NoSuchKey, timeout, connection 오류의 안전한 변환
- 다운로드 전후 metadata 변경과 재시도 소진을 결정적으로 재현
- credential과 Authorization header가 log/exception에 포함되지 않음

### 18.3 Bootstrap

- remote 성공 시 staging -> release -> current 순서
- `current` 교체 전에 incomplete 파일이 노출되지 않음
- 원격 metadata 변경 감지와 전체 세트 재시도
- remote 실패 시 packaged current 활성화
- packaged까지 실패하면 startup 실패
- stale/corrupt current 재결정
- `.complete.json`의 config/schema/file 검증
- orphan staging 정리
- lock timeout 시 독자 fallback 금지

### 18.4 로컬 MinIO 통합 테스트

로컬 S3-compatible 통합 테스트의 기준 서버는 Docker Compose로 실행하는 MinIO로 확정한다.
Compose에는 구현 시 검증한 MinIO image tag를 명시하고 `latest`는 사용하지 않는다.

```text
devops/compose/
└── minio-docker-compose.yaml

tests/manual/model_parameter_object_storage/
├── setup_minio.py
├── run_smoke_test.py
├── run_multi_worker_smoke.py
└── README.md
```

- 현재 packaged Basecase 3개와 활성 LUT CSV를 테스트 bucket에 업로드
- 원격 object key를 로컬 `path`와 의도적으로 다르게 구성
- 실제 HeadObject/GetObject, HTTP streaming, size/SHA-256 검증
- staging -> release -> `current` atomic swap 확인
- 잘못된 key와 credential에서 packaged fallback 확인
- partial 파일이 `current`에 노출되지 않는지 확인
- 동일 local root 재기동 시 유효한 `current` 재사용 확인
- 3-worker 기동 시 실제 다운로드가 한 번만 수행되는지 확인

로컬 MinIO endpoint의 HTTP는 `localhost`와 loopback 주소에서만 테스트 용도로 허용한다. 그 외 endpoint는
HTTPS를 강제한다. MinIO 테스트 credential과 데이터는 로컬 전용이며 Git에 실제 운영 secret을 저장하지 않는다.

### 18.5 멀티 프로세스와 Agent 통합

- 3 worker 동시 기동에서 실제 다운로드 1회
- 모든 worker가 동일한 resolved target과 source 사용
- startup preload와 실제 proposal node가 동일한 경로 사용
- remote validation cache와 packaged fallback cache가 섞이지 않음
- storage disabled 회귀 테스트
- 기존 Basecase workbook/record 및 LUT record/value 테스트 유지

### 18.6 실제 NCP 수동 검증

- 쓰기 권한 없는 read-only credential로 기동
- 원격명과 로컬명이 다른 Basecase/LUT 파일 확인
- 잘못된 key, secret, endpoint에서 packaged fallback 확인
- 세 worker의 source/fingerprint 일치 확인
- 실행 중에는 source가 바뀌지 않고 새 rollout에서만 갱신되는지 확인

## 19. 완료 기준

- storage disabled이면 현재 packaged 동작과 결과가 변하지 않고 네트워크 호출이 없다.
- storage enabled이면 설정된 exact object만 다운로드한다.
- 원격 파일명과 로컬 파일명이 달라도 `model_parameter_resources`의 `path` 이름으로 정상 동작한다.
- 다운로드와 semantic validation이 끝나기 전에는 새 리소스가 노출되지 않는다.
- 세 worker가 같은 `current`, source, resolved path를 사용한다.
- 원격 실패 시 모든 worker가 packaged 리소스로 동작한다.
- Basecase와 LUT가 서로 다른 source로 섞이지 않는다.
- 실행 중 리소스와 활성 경로가 변경되지 않는다.
- secret이 source, log, exception, test artifact에 노출되지 않는다.
- 기존 HTTP API, callback body, DB schema가 변경되지 않는다.
- 관련 자동화 테스트, MinIO 로컬 통합 테스트와 3-worker smoke test가 통과한다.
- 실제 NCP 연동 전까지는 MinIO를 로컬 S3-compatible 통합 검증 기준으로 사용한다.

## 20. 잔여 리스크

- 원격 version identifier가 없으므로 기동 전에 이미 만들어진 업무적 혼합 세트는 완전히 증명할 수 없다.
- `model_parameter_resources`의 object key 변경은 ConfigMap과 pod rollout으로 반영해야 한다.
- packaged fallback이 원격 장애를 가릴 수 있으므로 source/fallback 로그 모니터링이 필요하다.
- Object Storage 다운로드와 semantic preload만큼 startup 시간이 증가한다.
- 실제 NCP endpoint, credential, 네트워크 정책은 unit test만으로 완전히 검증할 수 없다.

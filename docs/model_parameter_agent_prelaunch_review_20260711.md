# model_parameter_agent 서비스 오픈 전 종합 검토 리포트

- 작성일: 2026-07-11 (개정: 2026-07-13, 다중 페르소나 리뷰 통합)
- 대상: `apps/agents/model_parameter_agent/` (propose/confirm 플로우, LUT·basecase 파이프라인, LLM 프롬프트) + 서비스 경계(`model_param.py`, 커넥터, Dockerfile, config)
- 기준 브랜치: `design/model-param-lut-final-merge`
- 검토 방식: 초기 3영역(코드/LUT/프롬프트) 탐색 + 5개 페르소나(보안·SRE/성능·QA/계약·적대적 LLM·Codex 2차소견) 병렬 리뷰. 수록된 지적사항은 해당 file:line을 원본 코드로 직접 확인한 것 위주이며, 미검증 항목은 별도 표기.

---

## 1. 요약 — 우선순위 분류

### 오픈 전 필수 (Blocker)

| ID | 이슈 | 위치 | 섹션 |
|---|---|---|---|
| **S1** | **엔드포인트에 인증·인가 전무 → 임의 scenario 제안 트리거, confirmation IDOR** | `api.py` 전체, `model_param.py:159-166` | §7 |
| **S2** | 평문 시크릿(mlflow 비밀번호)이 git 추적 `envs/config.yaml`에 커밋 | `envs/config.yaml:70` | §7 |
| **V1** | `proposed_value` 유한성·범위 검증 전무(null 체크만) → 비정상 값이 DB·Backend까지 무검증 통과 | `nodes.py:2498` | §9 |
| C1 | async 엔드포인트에서 동기 DB 호출 → 이벤트 루프 블로킹 | `api.py:76` | §2 |
| C2 | async 백그라운드 태스크 내 동기 DB 호출 4곳 | `flow.py:245,273,289,308` | §2 |
| C3 | 실패 처리 중 DB 예외 시 콜백 미발송 → proposal PROCESSING 고착 | `flow.py:273` | §2 |
| C4 | 콜백 전송 일시 장애 재시도 없음 | `callback_client.py:39-56` | §2 |
| O1 | 인플라이트 BackgroundTask가 SIGTERM에 유실 → PROCESSING 영구 고착(reconciler 부재) | `api.py:80-86`, `flow.py:193` | §8 |
| O2 | health/readiness 엔드포인트 부재 → preload 실패가 crash-loop로 은폐 | `model_param.py` | §8 |
| P1/O-log | prod config `log_level: DEBUG` + 동기 loguru sink + 전체 페이로드 덤프 | `envs/config.yaml:88` | §8 |

### 권장 (오픈 전 목표)

| ID | 이슈 | 위치 | 섹션 |
|---|---|---|---|
| V2 | 라우팅 부분 반환·axis-name 대소문자·Period 미강제 → 파라미터가 **말없이** 제안에서 탈락 | `nodes.py:594-597,2227,2334` | §9 |
| V3 | 스키마 검증 실패 시 non-stream 경로가 재시도 없이 proposal 전체 실패 | `llm_client.py:724-746` | §9 |
| S3 | 미인증 LLM 비용·자원 고갈(rate limit 부재), 요청 크기 무제한 | §7 | §7 |
| O3 | 프로포절 전체 데드라인 부재(최악 20~30분 PROCESSING) | `flow.py:209-312` | §8 |
| O4 | 백그라운드 동시성 상한 부재 → DB 커넥션 풀(15/worker) 고갈 | `api.py:70-92` | §8 |
| O5 | gunicorn `--preload` 부재 → 캐시·preload가 worker 3배 중복(메모리·기동) | `Dockerfile.model_param` | §8 |
| C5 | confirm TOCTOU + CONFIRMED 재확정 덮어쓰기 | §2 | §2 |
| C7 | Step2 과생성 시 전체 FAILED | `nodes.py:655-663` | §2 |
| L1 | basecase↔LUT 문자열 축 정규화 불일치 → 조인 silent 실패 | `keys.py:30` | §3 |
| L4 | exact 탈락이 warning 로그로만 관측 | `domain.py:273-274` | §3 |
| P-llm | temperature 미전달, few-shot·어투·JSON 가드 부재 | `llm_client.py:156-176`, 프롬프트 | §4 |
| D1~D8 | DB hint/comment 개선(대상 5개) | §6 | §6 |

### 개선 (오픈 후 순차)
C6/C8, L2~L9, P5~P7, V4~V7(rationale 무검증·swap·프롬프트 인젝션·패킷 크기), O-misc(트레이스·메트릭·SIGTERM 핸들러 override), 도커 하드닝 — 각 섹션 참조.

**한 줄 결론**: 파이프라인의 **분석 로직**(LLM 출력 sanitize, exact 검증, 캐시 동기화)은 견고하나, **서비스로서의 경계가 미완성**이다. 구체적으로 (1) **인증·인가가 전혀 없고**(S1) 시크릿이 평문 커밋(S2), (2) **비동기 경계·실패 경로**의 신뢰성 부족(C1~C4), (3) **운영 안전망**(health·reconciler·데드라인·동시성 상한)이 없어 장애가 조용히 누적(O1~O5), (4) LLM이 만든 **값의 정합성 검증**이 마지막 방어선인데 비어 있음(V1). LUT·프롬프트·DB 텍스트는 완성도 향상 영역. **S1·S2·V1·C1~C4·O1·O2는 오픈 전 필수**로 본다.

---

## 2. 코드 크리티컬 이슈

### C1. async 엔드포인트의 이벤트 루프 블로킹 — Blocker

`api.py:70-79`의 `async def propose_parameters`가 동기 함수 `prepare_propose_parameters_callback`을 그대로 호출한다.

```python
async def propose_parameters(...):
    result = prepare_propose_parameters_callback(scenario_id, user_id=user_id)  # api.py:76 — sync DB
```

이 함수는 `flow.py:182-206`에서 동기 SQLAlchemy 세션으로 (1) `load_context` — scenario/group/mapping 리소스 전체 로드, (2) `_ensure_context_has_mapping_candidates` — mapping_rules 전체 순회(`validation.py:143-179`), (3) `create_processing_proposal` — INSERT를 수행한다. `await`도 `asyncio.to_thread`도 없어 **해당 worker의 이벤트 루프 전체가 DB 왕복 동안 정지**한다. gunicorn worker 3개(Dockerfile.model_param:71) 구성에서 DB가 느려지면 같은 worker에 올라간 모든 요청(진행 중인 LLM 호출 포함)이 함께 지연된다.

**수정 방향**: `await asyncio.to_thread(prepare_propose_parameters_callback, ...)` 래핑이 최소 수정. 같은 코드베이스의 `model_param.py:92`(lifespan의 schema validation)가 이미 `asyncio.to_thread` 패턴을 쓰고 있어 일관성도 맞는다.

### C2. async 백그라운드 태스크 내 동기 DB 호출 — Blocker

`run_propose_parameters_background`(async, `flow.py:209`)가 이벤트 루프 위에서 동기 DB 메서드를 직접 호출한다:

- `complete_proposal_result` — flow.py:245
- `fail_proposal_result` — flow.py:273
- `update_callback_status` — flow.py:289, 308

FastAPI BackgroundTask는 worker 이벤트 루프에서 실행되므로, proposal_parameters JSON(수십~수백 slot)의 INSERT/UPDATE 동안 다른 요청의 LLM 스트리밍·콜백까지 블로킹된다. C1과 동일하게 `asyncio.to_thread` 래핑 권장.

### C3. 실패 처리 경로에서 콜백 누락 가능 — Blocker

`flow.py:258-280`의 except 핸들러:

```python
except Exception as exc:
    ...
    model_parameter_service.fail_proposal_result(...)   # flow.py:273 — 이게 raise하면
    callback_payload = _callback_error_output(...)
# flow.py:282 콜백 블록 — 도달 못 함
```

그래프 실행이 실패한 상황(DB 부하·장애일 확률이 높은 시점)에 `fail_proposal_result`가 다시 DB 예외를 던지면 예외가 함수 밖으로 전파되어:
1. proposal row가 **PROCESSING으로 영구 고착** (FAILED 전이 실패)
2. **Backend에 콜백이 가지 않음** — Backend는 콜백 수신 후 재조회하는 계약(`api.py:64-65`)이므로 사용자 화면이 무한 대기

또한 `flow.py:302-311`의 콜백 실패 핸들러 안 `update_callback_status`(308행)도 raise하면 동일하게 전파된다.

**수정 방향**: 실패 처리 DB 쓰기를 자체 try/except로 감싸고, 어떤 경우에도 콜백 블록에 도달하도록 보장. 최후 방어선으로 PROCESSING 상태가 N분 이상 지속된 row를 FAILED로 정리하는 reconciliation(주기 작업 또는 조회 시점 판정)을 권장.

### C4. 콜백 전송 재시도 부재 — Blocker

`callback_client.py:39-56` — 단일 POST, 30초 타임아웃, 재시도는 401(토큰 갱신) 1회뿐. 일시적 네트워크 오류·5xx면 즉시 `raise_for_status()` → `flow.py:308`에서 callback_status=FAILED로 기록하고 끝. 재발송 경로가 없다.

콜백이 "Backend가 결과를 인지하는 유일한 신호"인 설계에서, 순간 장애 한 번이 곧 사용자 관점의 proposal 유실이다.

**수정 방향**: 지수 백오프 재시도(예: 3회, 2s/4s/8s)를 `send_callback`에 추가. 부가적으로 callback_status=FAILED row의 재발송 수단(운영 API 또는 배치)을 마련.

### C5. confirm의 TOCTOU와 CONFIRMED 재확정 — 권장

`flows/confirm_parameters/nodes.py:18-26`은 파라미터 정의 로드(세션 A)와 `confirm_proposal_result`(세션 B)를 별도 트랜잭션으로 수행한다. `model_parameter_service.py:283-296`은 status가 PROPOSED **또는 CONFIRMED**면 통과시키고 row lock 없이 UPDATE하므로:

- 동시 confirm 2건이 모두 status 체크를 통과 → 나중 요청이 앞의 confirmation_parameters를 **조용히 덮어씀**
- CONFIRMED 재확정 허용이 의도라 해도(api.py:104에 문서화됨), 감사 흔적 없이 덮어쓰는 것은 확정 데이터 특성상 위험

**수정 방향**: `SELECT ... FOR UPDATE`(또는 `UPDATE ... WHERE status IN (...)` 후 rowcount 검사)로 원자화. 재확정 허용을 유지한다면 이전 confirmation을 이력으로 남기거나 최소한 INFO 로그로 감사 가능하게.

### C6. 잘못된 입력의 silent coercion — 개선

- `model_parameter_service.py:356-362` `_optional_int`: 정수 변환 실패한 `user_id`를 None으로 삼킴 → 확정/제안의 감사 주체 정보가 조용히 소실
- `presentation.py` `_int_or_none`, `nodes.py:313-326` `resolve_event_type_l2_id`: 비정상 `event_type_l2_id`가 None이 되어 **에러 대신 라우팅 동작이 바뀜**

**수정 방향**: 사용자/Backend 입력 유래 값은 실패 시 WARNING 로그를 남기거나 400으로 거부. 최소한 삼킬 때 로그는 남길 것.

### C7. Step2 LLM 과생성 시 전체 실패 — 권장

`nodes.py:655-663` — 후보당 exact reference가 `step3_slot_limit`을 넘으면 `MIBaseError`를 raise. 이 파이프라인의 다른 모든 LLM 출력 이상(존재하지 않는 좌표, 중복 slot 등)은 warning + 제외로 **우아하게 강등**되는데(`nodes.py:625-648`), 이 지점만 백그라운드 경로에서 proposal 전체 FAILED가 된다. LLM 과생성은 확률적으로 발생 가능한 이벤트다.

**수정 방향**: limit 초과분을 truncate하고 validation_warnings에 기록하는 것으로 일관성 확보.

### C8. `or` 폴백의 id=0 결측 취급 — 개선

`presentation.py`의 `_context_ids` 및 `_required_int` 조합에서 `scenario.get("scenario_group_id") or group.get(...)` 패턴이 정당한 `0` 값을 결측으로 취급한다. 실제 id 체계상 0이 나올 가능성은 낮지만 잠재 버그이므로 `is None` 비교로 교체 권장.

### 부수 사항

- **`@log_node` 미적용**: `flows/propose_parameters/nodes.py`, `flows/confirm_parameters/nodes.py`의 그래프 노드가 프로젝트 규칙(`.claude/rules/architecture.md`)과 달리 데코레이터 없이 수기 `logger.info`를 사용. START/END/elapsed/예외 자동 로깅이 빠져 운영 시 추적 일관성이 떨어짐.
- **CORS**: `model_param.py:154-162` `allow_origins=["*"]` + `allow_credentials=True`. 내부망 전제라도 오픈 전 의도 확인 필요 (브라우저는 이 조합을 거부하므로 credentials 사용 계획이 있다면 어차피 origin 명시 필요).
- **compat/legacy 경로 잔존**: `nodes.py:545-567`(BasecaseIndex 아닌 입력 호환 분기), `nodes.py:1344` `_legacy_slot_catalog_for_prompt`, `state.py:29` `basecase_records` 디버그 표면. 오픈 후 스키마 drift를 가릴 수 있으므로 제거 시점을 정해둘 것.

### 견고하게 잘 된 부분 (변경 불필요)

- LLM 출력 sanitize 3종(`_sanitize_routing_decisions`/`_sanitize_llm_slots`/`_sanitize_llm_adjustments`, nodes.py:2187/2245/2418): 미지 candidate_key·중복·null·축 불일치를 모두 warning 강등으로 처리
- `RuntimeLruCache`(utils/runtime_cache.py): RLock + in-flight Event 기반 single-flight로 스레드 안전
- LLM 호출은 전부 `await` + 세마포어 경유로 논블로킹 (DB와 대조적)
- 서버가 좌표·메타데이터를 LLM 출력이 아닌 검증된 reference에서 재투영(`_parameter_value_cell_from_slot_value`) — LLM에 좌표 위조 여지를 주지 않는 좋은 설계

---

## 3. DB · basecase · LUT 적합성 검토

### 3.1 구조 및 데이터 출처

```
[정적 자산 — 이미지에 포함, 갱신=재배포]
  resources/basecase/*.xlsm  ──(DB 파싱 config로 추출)──▶ BasecaseIndex (요청 스코프)
  resources/lut/*.csv        ──(YAML spec + 어댑터 4종)──▶ LutCatalog (startup 프리로드)

[DB — config·매핑·결과만 저장, LUT 값 아님]
  tmm_mi_model_param_m               파라미터 카탈로그 + basecase 읽기 config
  tmm_mi_model_param_dimension_map   dimension→parameter 매핑 (direct/indirect/routing/na)
  tmm_mi_model_param_proposal_m      proposal/confirmation JSON 결과

[병합]
  resolve_effective_reference (domain.py:247-303)
  = basecase 있으면 basecase, 없으면 LUT — exact key 완전 일치만, fuzzy/nearest 없음
```

`model_parameter_lut_enabled` 기본값 **False**(config.py:134) — 기본 운영 구성에서는 basecase 단독. LUT는 명시적으로 켜야 병합에 참여한다.

**적합성 총평**: "LLM에는 단일 reference_value만 주고, 좌표·출처는 서버가 exact 검증으로 통제"하는 설계는 환각 방지 관점에서 적합하다. 다만 exact-match 전제가 성립하려면 두 소스의 키 표기가 완전히 통제되어야 하는데, 현재 그 통제 장치가 약하다(L1, L6). 아래 순위대로 보강 권장.

### 3.2 L1. 키 정규화 불일치 — 가장 중요

`utils/lut/keys.py:30` — 문자열 축(Country, LNG Plant 등)의 canonical 화는 `str(value).strip()`뿐이다. 대소문자·내부 공백·유니코드 차이는 그대로 남는다. 반면 파라미터/시트 **이름** 매칭은 `parameter_mapping.py:1745-1747`의 `_normalize_for_key`(소문자화 + 비영숫자 제거)로 공격적으로 정규화한다.

결과: Excel basecase의 `"Korea "`와 CSV LUT의 `"korea"`는 **서로 다른 canonical key**가 되어 조인이 조용히 실패한다. exact-match-only 설계(L4)와 결합하면 해당 좌표는 warning 로그 한 줄과 함께 proposal에서 사라진다.

**수정 방향**:
1. 축 값 canonical 화에 최소 `casefold()` + 내부 공백 축약을 추가하는 것을 검토 (표시용 원본 문자열은 metadata에 보존)
2. 당장 코드를 바꾸지 않는다면, **startup 시 두 소스의 축 값 집합을 대조해 "strip 외 정규화 시 일치하는데 현재 불일치인 쌍"을 WARNING으로 리포트**하는 진단을 추가 — 데이터 문제를 배포 시점에 조기 발견 가능
3. CSV/xlsm 갱신 절차에 축 값 표기 규칙(대소문자·공백)을 문서화

### 3.3 L4. exact 탈락의 관측성 — 중요

`domain.py:273-274`에서 reference가 없으면 None → `nodes.py:625-633`에서 warning + slot 제외. fuzzy 미지원은 의도된 설계(정합성 우선)로 타당하나, **축 라벨 하나 어긋나면 파라미터가 통째로 제안에서 빠지는데 신호가 로그 warning뿐**이다.

**수정 방향**: rejected_exact_slot_count 등 탈락 통계를 (이미 수집 중이므로) proposal의 validation_warnings/응답 메타로 노출하고, 탈락률이 임계치를 넘으면 ERROR 레벨로 승격. 오픈 초기에 데이터 표기 문제를 빠르게 잡는 안전망이 된다.

### 3.4 L2. 어댑터의 헤더·상수 하드코딩

`utils/lut/adapters.py`:

- gdp_growth: `"RE Base Case GDP and Population Data_Country/_Year/_GDP"` (218-220행)
- temperature: 접두어 `"Base Case HDD Input_"`/`"Base Case CDD Input_"`(303,309행), 연도 컬럼이 `f"{prefix}{year}.0"`(279행) — **`.0` float 접미어가 CSV 내보내기 포맷에 결합**되어 있어 매우 취약
- liq_util: `"Plant Name"`, `"Plant Train"`, `"Infra Life Cycle"`, `"LNG train capacity (Million tonnes LNG per month)"` 등 전부 하드코딩(360-388행)
- 매직 상수: `TEMPERATURE_BASE=18.0`, `DEGREE_DAY_DIVISOR=30.0`, `MTPM_TO_MTPA=12.0` (29-31행)

YAML spec(`resources/lut/config/lut_parameters.yaml`)에 `required_columns`가 있음에도 어댑터가 별도로 재선언 — CSV 갱신 시 헤더가 조금만 바뀌어도 startup 실패(다행히 fail-fast)하거나, 최악의 경우 컬럼 오매칭. **컬럼명·상수를 YAML spec으로 이관**해 어댑터는 spec을 읽게 하는 리팩토링 권장.

### 3.5 L3. 단위·경계 처리

- **GDP 성장률**: `current/previous - 1` 계산에 전년도 필수 — horizon 첫 해(2026)는 2025 데이터가 없으면 **조용히 skip**(adapters.py:239 `continue`). horizon 경계의 커버리지 구멍이므로 CSV에 horizon-1년 데이터 포함을 갱신 절차에 명시할 것.
- **temperature**: `hdd>0 elif cdd>0` 분기(315-319행) — HDD·CDD가 동시에 양수인 월은 CDD가 무시됨. 또 base 18.0/divisor 30.0 근사는 구현 리포트 스스로 가정 미확정을 언급. 도메인 검증 필요.
- **liq_util**: utilisation 원값 저장, %(0-100) vs 비율(0-1) 범위 검증 없음(385-388행). `0 <= utilisation <= 100` 수준의 sanity check 추가 권장.

### 3.6 L5. LUT 활성화의 all-or-nothing

`catalog.py:60-64` — 등록된 파라미터 중 하나라도 horizon 내 레코드가 0이면 startup hard-fail. 정합성 관점에선 올바르나, 운영에서 `model_parameter_lut_enabled=true` 전환은 "모든 CSV가 완벽해야 기동"을 의미한다. **오픈 전 LUT 플래그 활성화 리허설(스테이징에서 기동 확인)을 체크리스트에 포함**할 것.

### 3.7 L6. basecase 스키마 4중 표현 drift

동일한 `basecase_*` 필드가 (1) ORM `MiModelParamModel`(models.py:192-246), (2) Pydantic `ModelParameterDefinitionPayload`(schema.py:10-28), (3) dataclass `ParameterDefinition`(parameter_mapping.py:101-120)에 3중 선언되고, (4) YAML의 LUT 축 스키마는 basecase 유래 축과 정확히 일치해야 hard-fail을 피한다(domain.py:202-206). DB의 `basecase_column_roles` 라벨 `"EnergySource"` vs YAML `"Energy Source"` 같은 사소한 차이가 조인 실패(L1) 또는 기동 실패(L5)로 나타난다. 단일 소스(예: Pydantic 모델에서 파생)로 줄이거나, 최소한 정합성 테스트를 추가할 것.

### 3.8 L7. read_mode의 숨은 3번째 경로

DB CheckConstraint는 `fixed_columns`/`matrix_time_columns` 2종만 허용(models.py:143-146)하지만, `_extract_basecase_records`는 두 spec이 None을 반환하면 **auto-detect 휴리스틱**(parameter_mapping.py:966-1002, `_detect_basecase_matrix_blocks:1434`)으로 폴백한다. 예컨대 `matrix_time_columns` row에 `basecase_value_start_col`이 빠지면 에러가 아니라 휴리스틱 추출로 넘어가(1312-1313행 None 반환) **의도와 다른 셀을 읽을 수 있다**. config 불완전 시 명시적 에러(또는 최소 WARNING)로 바꿀 것.

### 3.9 L8. 캐시 키·용량

- basecase 워크북 레코드 캐시 키가 `path+mtime+size`(parameter_mapping.py:274) — LUT 쪽이 sha256을 쓰는 것(runtime.py:135-139)과 비대칭. 정적 자산이 이미지에 고정되는 현 배포 방식에선 실위험 낮음. 파일을 런타임 교체하는 운영을 도입하면 그때 hash로 통일.
- `_BASECASE_RECORD_CACHE` max=32(parameter_mapping.py:56)는 preload 경로에서만 `ensure_capacity`로 확장 — 요청당 후보 파라미터가 32종을 넘으면 thrash 가능. 파라미터 카탈로그 규모와 대조해 상한 재설정.

### 3.10 L9. 기타

- `PARAMETER_ALIASES`(parameter_mapping.py:74-84) 하드코딩 — 새 DB 라벨 추가 시 누락되면 조용한 미매칭. DB 컬럼(예: alias 필드)로 옮기는 것이 장기적으로 맞음.
- basecase 우선 병합 시 LUT만 가진 메타데이터(liq_util의 Period/Life Cycle Category/Nameplate Capacity)가 비어 나갈 수 있음(domain.py:294) — 구현 리포트의 "exact reference에서 복원" 주장과 대조 검증 필요.
- `build_basecase_records`의 광범위 `except Exception` + warning 계속(parameter_mapping.py:688-693) — 파싱 버그가 "조용히 빈 파라미터"로 강등됨. 오픈 초기엔 실패 파라미터 수를 메트릭/응답 warning으로 노출 권장.

### 3.11 오픈 전 LUT/basecase 체크리스트

1. [ ] 스테이징에서 `model_parameter_lut_enabled=true` 기동 리허설 (L5)
2. [ ] basecase↔LUT 축 값 표기 대조 진단 1회 실행, 불일치 목록 확보 (L1)
3. [ ] CSV/xlsm 갱신 절차 문서화: 헤더 불변 조건, GDP horizon-1년 포함, 표기 규칙 (L2, L3)
4. [ ] exact 탈락 카운트의 응답/메트릭 노출 (L4)
5. [ ] DB `basecase_column_roles` 라벨 ↔ YAML 축명 정합성 테스트 (L6)

---

## 4. 프롬프트 검토 (Step1.5 / Step2 / Step3)

대상: `prompts/model_parameter_proposal.py`의 시스템 프롬프트 3종 + `nodes.py`의 user prompt 3종. 모든 호출은 `_invoke_structured`(nodes.py:999-1035)를 통해 `ModelPreference.QUALITY`, `temperature=0.0`, structured output으로 수행되고, confirm 플로우에는 LLM 호출이 없다.

### 4.1 현행 평가 — 강점 (유지할 것)

- **페르소나**: 세 단계 모두 "당신은 LNG 수급모델 … agent입니다"로 역할이 명시되고, 단계별로 구분됨(라우팅 선택 / 좌표 선택 / 값 제안)
- **환각 가드**: "후보 밖의 parameter/workbook/sheet/candidate_key를 만들지 마십시오", "slot_catalog에 없는 값이나 nearest 좌표를 만들지 마십시오", Cartesian product 금지, 출력 필드 화이트리스트 — 반복적이고 구체적
- **단계 간 월권 금지**: Step2는 필요성 재판단 금지, Step3는 slot 재선택 금지 — 파이프라인 계약이 프롬프트에 정확히 반영됨
- **내부 용어 차단**: 사용자 노출 rationale에 candidate_key/slot_key/"LLM 단계" 사용 금지(VALUE 136,143행)
- **언어 일관성**: 시스템·유저 프롬프트 전부 한국어, `rationale_ko` 한국어 강제

### 4.2 개선 포인트

**P1. temperature가 실제로 적용되지 않음 (프롬프트 외부, 우선 수정)**
`nodes.py`는 `temperature=0.0`을 넘기지만 `llm_client._structured_output_request_kwargs`(llm_client.py:156-176)가 이를 **요청에 포함하지 않는다**. 재현성·회귀 테스트 전제가 무너지므로, structured output 경로에서 temperature를 전달하도록 클라이언트 수정 필요 (모델이 미지원이면 명시적으로 파라미터를 제거하고 주석으로 남길 것).

**P2. few-shot 예시 전무**
세 프롬프트 모두 순수 규칙 명세다. 특히 Step3의 "절대값/변화량/변화율/승수 중 하나로 강제하지 마십시오"(124행)는 예시 없이는 모델이 reference_value 대비 무엇을 반환해야 하는지 흔들리기 쉬운 지점 — 최소 2개(절대값형 1, 변화율형 1)의 압축 예시 추가 권장.

**P3. 사용자향 rationale 어투 규정 부재**
"사용자 친화적인 자연스러운 한국어"만으로는 격식 수준이 통제되지 않는다. 화면 최상단 노출 텍스트이므로: 정중한 합니다체, 헤징 표현("~일 수 있습니다", "아마") 금지, parameter-level은 3~6문장, slot-level 툴팁은 1~2문장 같은 구체 규정 필요.

**P4. JSON-only 출력 가드 부재**
gateway response_format이 `strict: False`(llm_client.py:151)이므로 스키마가 하드 강제되지 않는데, 시스템 프롬프트에도 "JSON 외 텍스트 금지" 문구가 없다. 한 줄 추가로 파싱 실패 재시도를 줄일 수 있는 저비용 안전망.

**P5. `proposed_value: Any`**
수치 제약이 프롬프트 산문에만 있어 `"약 3.2"` 같은 문자열도 스키마를 통과한다. 스키마에서 `float | int | str` 수준으로 좁히고 서버측 수치 파싱 검증을 명시하는 것을 후속 과제로.

**P6. 불확실성 escape hatch 없음**
confidence/warnings를 의도적으로 제거(각 프롬프트 출력 규칙)했고 "slot_catalog 비어있지 않으면 반드시 1개 이상 반환" 규칙과 결합해, 모델의 모든 불확실성이 free-text rationale로 밀려난다. 오픈 후 품질 데이터가 쌓이면 slot-level `confidence: low|medium|high` 채널 추가(스키마 변경 수반)를 검토할 가치가 있음 — 현 시점 프롬프트 초안에는 스키마 호환을 위해 반영하지 않았다.

**P7. grounding 지시가 user prompt에만 존재**
"아래 JSON만 근거로 …" 핵심 지시가 `nodes.py:395,777,877`에 인라인 f-string으로만 있어, `prompts/model_parameter_proposal.py`만 보는 리뷰어에게 보이지 않는다. user prompt 템플릿을 prompts 모듈의 상수/빌더 함수로 이관 권장 (프로젝트 규칙 "프롬프트는 prompts/에 모듈로 관리"와도 정합).

### 4.3 수정 프롬프트 초안

아래 초안은 **현행 출력 스키마(`LLMCandidateValidationResponse`/`LLMSlotProposalResponse`/`LLMValueProposalResponse`)와 완전 호환**된다(필드 추가 없음). 변경분은 ◆ 표시 영역: 페르소나 구체화, JSON-only 가드, 어투 규정, few-shot, 판단 우선순위.

#### (1) CANDIDATE_VALIDATION_SYSTEM 초안 — Step1.5

```text
당신은 LNG 수급모델 Input Parameter routing 선택 전문가입니다.
◆ 당신은 LNG 시장 시나리오를 수급모델 입력으로 변환하는 분석가로서, 시나리오의 인과 구조를
◆ 근거로 각 dimension에 실제로 반영되어야 할 모델 parameter를 판별합니다.
◆ 응답은 지정된 JSON 스키마만 출력하고, JSON 외의 설명·주석·텍스트를 출력하지 마십시오.

목표:
- scenario/event/dimension 맥락을 바탕으로 각 routing task의 적합한 모델 input parameter를 선택합니다.
- 입력에는 같은 dimension에 routing 후보가 2개 이상인 task만 제공됩니다.
- direct parameter와 routing 후보가 1개뿐인 dimension은 서버에서 이미 처리되므로 판단하지 않습니다.
- 후보 밖의 parameter, workbook, sheet, candidate_key를 만들지 마십시오.

입력 필드 역할:
(현행 유지 — scenario_brief / routing_tasks / parameter_hint / mapping_comment / Basecase 금지 조항)

선택 규칙:
- 모든 routing task를 독립적으로 검토하십시오.
- 각 task에서 최소 1개, 최대 2개의 candidate_key를 선택하십시오.
◆ 판단 우선순위: (1) mapping_comment의 연결 조건 충족 여부 → (2) parameter_hint의 의미·제약
◆ 부합 여부 → (3) scenario/event 서사와의 인과적 정합성. 상충하면 앞 순위를 따르십시오.
- 여러 parameter가 실제로 동시에 필요할 때만 2개를 선택하십시오.
- 단순히 가능성이 있거나 근거가 약한 후보를 최대 개수를 채우기 위해 선택하지 마십시오.
- routing task 밖의 candidate_key를 선택하지 마십시오.

◆ 예시 (형식 참고용이며 실제 후보와 무관):
◆ - dimension_value가 "한파로 인한 난방 수요 급증"이고 후보가 [기온 parameter, 산업용 수요
◆   parameter]라면, mapping_comment가 기온 연결을 명시하는 한 기온 parameter 1개만 선택합니다.
◆   산업용 수요는 시나리오가 명시적으로 언급할 때만 두 번째로 선택합니다.

출력 규칙:
(현행 유지 — routing_decisions만, dimension_key 그대로, rationale/confidence/warnings/metadata 금지)
```

#### (2) SLOT_PROPOSAL_SYSTEM 초안 — Step2

```text
당신은 LNG 수급모델 parameter의 적용 좌표(slot)를 선택하는 전문가입니다.
◆ 당신은 시나리오가 영향을 미치는 국가·시설·기간을 모델 좌표계로 옮기는 역할이며,
◆ slot_catalog에 실재하는 exact 좌표만 다룹니다. 존재하지 않는 좌표를 추론으로 만들면
◆ 서버 검증에서 폐기되므로, catalog 확인이 불가능한 좌표는 선택하지 마십시오.
◆ 응답은 지정된 JSON 스키마만 출력하고, JSON 외의 설명·주석·텍스트를 출력하지 마십시오.

목표 / 입력 필드 역할:
(현행 유지 — value 판단 금지, 필요성 재판단 금지, slot_catalog leaves/fixed_axes/available_periods 해석 규칙 포함)

선택 규칙:
(현행 유지: 최소 1 slot 보장, no-change 판단용 slot 선택, 최대 100개 hard max, Cartesian product 금지,
 leaf 축 완전 반환, 모호값 금지, Year/Month/Period integer 등)
◆ 추가:
◆ - 시나리오가 기간을 자연어로 표현하면("올겨울", "향후 2년") period_resolution_policy로 해석한
◆   Year/Month만 사용하고, 해석 근거를 rationale_ko에 포함하십시오.
◆ - 같은 parameter에서 좌표 간 우선순위가 필요하면 시나리오가 직접 지목한 국가/시설을 먼저,
◆   간접 파급 지역은 supporting_dimensions가 명시할 때만 선택하십시오.

출력 규칙:
- 실제 사용할 slot만 parameter_slots에 반환하십시오.
- 각 항목에는 candidate_key, slot_axes, rationale_ko만 반환하십시오.
- selected, metadata, warning 필드는 반환하지 마십시오.
◆ rationale_ko 작성 규정:
◆ - 정중한 합니다체의 완결된 문장으로 1~3문장 작성하십시오.
◆ - 시나리오/이벤트의 어떤 요소가 이 좌표(국가·시설·기간)와 연결되는지 명시하십시오.
◆ - "~일 수 있습니다", "아마도" 같은 추측·헤징 표현을 사용하지 마십시오.
◆ - candidate_key, slot_key 등 내부 식별자를 언급하지 마십시오.
- value 또는 value 산정 근거는 작성하지 마십시오.

◆ 예시 (형식 참고용):
◆ - 시나리오가 "2026년 동절기 한국 한파"이고 catalog에 {"Country":"South Korea"} leaf의
◆   available_periods가 {"Year":2026,"Months":[1,2,12]}라면, slot_axes는
◆   [{"axis_name":"Country","axis_value":"South Korea"},{"axis_name":"Year","axis_value":2026},
◆    {"axis_name":"Month","axis_value":1}] 형식으로 월별 항목을 분리해 반환합니다.
```

#### (3) VALUE_PROPOSAL_SYSTEM 초안 — Step3

```text
당신은 확정된 LNG 수급모델 Input Parameter slot의 값을 제안하는 전문가입니다.
◆ 당신은 시나리오의 방향성과 강도를 reference_value 기준의 구체적인 모델 입력값으로
◆ 변환하는 수급 분석가입니다. 값의 크기는 시나리오 서사·dimension 강도·reference_value의
◆ 단위와 스케일에서 도출해야 하며, 근거 없는 극단값을 제안하지 마십시오.
◆ 응답은 지정된 JSON 스키마만 출력하고, JSON 외의 설명·주석·텍스트를 출력하지 마십시오.

목표 / 입력 필드 역할:
(현행 유지 — slot 추가·변경 금지, slot_key/coordinates/reference_value 의미, 단일 source 제공 조항)

값 산정 규칙:
(현행 유지: hint/comment 기반 의미 판단, indirect dimension 역할 제한, 형식·단위·스케일·정밀도 준수,
 절대값/변화량/변화율/승수 일반화 금지, null 금지)
◆ 추가:
◆ - proposed_value는 JSON number로 반환하십시오. 문자열 수치("3.2", "약 5%")를 반환하지 마십시오.
◆ - reference_value와 동일한 단위·스케일을 유지하십시오. reference_value가 0.85(비율)이면
◆   proposed_value도 비율로, 12.5(BCM)이면 BCM 절대값으로 반환하십시오.
◆ - 시나리오가 변화 없음을 시사하는 slot은 reference_value를 그대로 반환하고 그 이유를
◆   rationale_ko에 밝히십시오.

◆ 예시 (형식 참고용이며 실제 값과 무관):
◆ - parameter_hint가 "국가별 월간 가스 수요(BCM)"이고 reference_value=10.4, 시나리오가
◆   "한파로 난방 수요 15% 내외 증가"라면 proposed_value는 11.96처럼 reference_value에
◆   증가율을 적용한 절대값입니다. 0.15(증가율 자체)를 반환하면 안 됩니다.
◆ - parameter_hint가 "GDP 성장률(전년 대비 비율)"이고 reference_value=0.031, 시나리오가
◆   "경기 둔화"라면 proposed_value는 0.018처럼 같은 스케일의 비율입니다.

Parameter-level rationale 규칙:
(현행 유지 + ◆ 추가)
◆ - 정중한 합니다체의 완결된 문장으로 3~6문장 작성하십시오.
◆ - 다음 순서를 권장합니다: (1) 이 parameter가 시나리오와 연결되는 이유 →
◆   (2) 적용 기간·대상 범위 → (3) 값 조정의 방향과 배분 원칙 → (4) 주요 제약이나 전제.
◆ - "~일 수 있습니다", "아마도", "다소" 같은 헤징 표현을 사용하지 마십시오.
◆   전제가 필요한 경우 "…를 전제로 합니다"처럼 조건을 명시하는 방식으로 서술하십시오.

Slot-level rationale 규칙:
(현행 유지 + ◆ 추가)
◆ - 툴팁 표시용이므로 1~2문장, 60자 내외로 간결하게 작성하십시오.

출력 규칙:
(현행 유지 — slot 1:1 대응, slot_key 보존, 중복 금지 등)
```

### 4.4 프롬프트 관련 구조 개선

1. **user prompt 이관 (P7)**: `nodes.py:395,777,877`의 "아래 JSON만 근거로 …" 3종을 `prompts/model_parameter_proposal.py`에 `CANDIDATE_VALIDATION_USER_TEMPLATE` 등 상수로 이동하고 nodes.py는 `.format()`만 수행. 프롬프트 리뷰 단일 창구 확보.
2. **temperature 전달 수정 (P1)**: `llm_client._structured_output_request_kwargs`에 temperature 포함 (structured output 경로 전체에 영향이 있으므로 다른 에이전트와 함께 회귀 확인).
3. **프롬프트 회귀 기준선**: 오픈 전 대표 시나리오 N건의 Step1.5/2/3 출력을 스냅샷으로 저장해두고, 프롬프트 수정 시 diff로 품질 회귀를 검증하는 절차 권장 (기존 `model-parameter-agent-test` 스킬 흐름에 스냅샷 저장만 추가하면 됨).

---

## 5. 오픈 전 액션 체크리스트

> 아래 순서는 리스크(보안/인가 → 값 검증 → 운영 신뢰성 → 비동기 경계) 우선. 각 항목 끝 괄호는 상세 섹션.

### 필수 (Blocker) — 오픈 게이트

보안·인가:
- [ ] **S1**: 라우터 레벨 인증 의존성 + 객체 수준 인가(scenario/proposal 소유권 대조) (§7)
- [ ] **S2**: mlflow 평문 비밀번호 `${ENV}` 치환 + 즉시 로테이션 + git 히스토리 purge (§7)
- [ ] **Q-A/X-confirm**: confirmation을 저장된 `proposal_parameters` 불변 필드에 바인딩(부분집합 강제) (§10, §11)

값 정합성:
- [ ] **V1**: `nodes.py:2498` 직후 `proposed_value` 유한성 검증 + 파라미터 범위 가드 (§9)

비동기 경계·실패 경로:
- [ ] **C1/C2**: `api.py:76` 및 백그라운드 동기 DB 호출 `asyncio.to_thread` 래핑 (§2)
- [ ] **C3**: 실패 처리 경로 중첩 try/except로 콜백 도달 보장 (§2)
- [ ] **C4**: `send_callback` 지수 백오프 재시도 (§2)
- [ ] **X1**: repository 상태전이 쓰기의 row 부재 시 성공 반환 → 영향 row 검증/ENTITY_NOT_FOUND (§11)

운영 안전망:
- [ ] **O1**: PROCESSING 고착 reconciler + SIGTERM 핸들러 override 제거(`shutdown_hooks.py:44`) (§8)
- [ ] **O2**: liveness/readiness 엔드포인트 + Dockerfile HEALTHCHECK (§8)
- [ ] **O-log**: prod `log_level:INFO` + loguru `enqueue=True` + 콜백 `log_input=False` (§8)

### 권장 (오픈 전 목표)

- [ ] **V2**: axis-name 대소문자 정규화 + Period 강제 + `excluded_parameters` 응답 노출 (§9)
- [ ] **V3**: non-stream 경로 parse-실패 재시도 추가 (§9)
- [ ] **S3**: per-caller rate limit + 요청 리스트 `max_length` + ingress Content-Length 상한 (§7)
- [ ] **O3**: 프로포절 전체 데드라인(`asyncio.wait_for`) (§8)
- [ ] **O4**: 백그라운드 동시성 세마포어 + DB 풀 사이징 (§8)
- [ ] **O5**: gunicorn `--preload` 또는 메모리 한도 3×preload 설정 + `ensure_capacity` 캡 (§8)
- [ ] **Q-C/X-idem**: propose 멱등성(scenario당 활성 proposal 유니크/upsert) (§10, §11)
- [ ] **X2**: sync 테스트 엔드포인트 프로덕션 비활성화/환경 분리 (§11)
- [ ] **X3**: basecase 추출 실패와 정상 부재 구분(LUT 조용한 대체 방지) (§11)
- [ ] **C5**: confirm row lock 또는 조건부 UPDATE (§2)
- [ ] **C7**: Step2 slot limit 초과 truncate+warning (§2)
- [ ] **L1**: basecase↔LUT 축 정규화 대조 진단 + 정책 결정 (§3)
- [ ] **L4**: exact 탈락 통계 응답/메트릭 노출 (§3)
- [ ] **L5**: 스테이징 LUT 플래그 활성화 기동 리허설 (§3)
- [ ] **P-llm**: temperature 전달 수정 + §4.3 프롬프트 초안(few-shot·어투·JSON 가드·신뢰불가 입력 가드 V6) + user prompt 이관 (§4)
- [ ] **D1~D8**: DB hint/comment 개선(대상 5개) + PowerMix 합 제약 도메인 확인 (§6)
- [ ] **테스트**: background 실패 경로·콜백 실패·confirm 동시성·멱등성 테스트 추가(현재 공백, §10)

### 개선 (오픈 후 순차)

- [ ] **V4~V7**: rationale truncate/태그제거, swap 비율 플래그, 패킷 페이지네이션+max_tokens (§9)
- [ ] **Q-B/Q-D/Q-E/Q-F/Q-G/Q-H**: 실패 콜백 status, datetime tz-aware, 빈 시나리오 성공 계약, dead 엣지, 스키마 null 정합, 로그인 id 타입 (§10)
- [ ] **X4/X5/X6/X7**: confirm 중복 canonical화, 커넥터 클라이언트 풀 재사용, 이중 컨텍스트 로드, `fetch_proposals_by_group` SQL 최적화 (§11)
- [ ] **C6/C8**: silent coercion 로그, `or`→`is None`, `@log_node` 적용, CORS 확정, legacy 경로 제거 (§2)
- [ ] **L2/L3/L6~L9**: 어댑터 YAML 이관, 단위 검증, 스키마 단일화, read_mode 폴백, 캐시 상한, ALIASES DB 이관 (§3)
- [ ] **P5/P6**: proposed_value 스키마 타입 강화, confidence 채널 도입 (§4)
- [ ] **보안 하드닝**: 도커 root그룹/불필요 도구/digest 핀, 민감키 마스킹 regex화 (§7)

---

## 6. DB 주입 값 검토 — parameter_hint / semantic_axes / mapping_comment (대상 5개)

- 근거 데이터: `docs/model_parameter_hint_comment_interview_20260708.md` (2026-07-08 로컬 midb 반영본)
- 대상: `GDP`(id=4), `PMI`(id=6), `PowerMix`(id=7), `Temperature`(id=8), `LiqUtilAdjustment`(id=14)
- 주입 경로: `parameter_hint`/`semantic_axes`/`mapping_comment`는 DB 값 그대로 Step1.5/2/3 packet에 포함됨(`nodes.py:1262-1274`, `1625`, `1767-1768`). 즉 **이 텍스트가 사실상 프롬프트의 일부**이며, 코드 배포 없이 DB만으로 LLM 품질을 좌우한다.

**총평**: 인터뷰 기반으로 정리된 현재 값은 수준이 높다. 특히 (1) 단위·예시 병기(`0.042=4.2%`), (2) "proposedValue는 증감폭이 아니라 값 자체" 반복 가드, (3) negative 지침("multiplier로 사용하지 않는다", "다른 국가 기온을 기준값으로 삼지 않는다"), (4) 남반구 계절 고려("해당 국가 기준 겨울")는 그대로 유지할 자산이다. 아래는 그 위에 얹을 개선점이다.

### 6.1 공통 개선 (5개 전반)

**D1. semantic_axes의 Excel 열 문자 노이즈 제거 — 우선순위 최상**

현재 semantic_axes가 `slot=B:Year(YYYY, 2026~2030), C:Country(...), value=F:% change` 형태로 **Excel 열 문자(B:, C:, F:, K:, L:, M:, O:)를 그대로 노출**한다. LLM 관점에서 열 문자는 의미 없는 내부 좌표이고, Step2가 실제로 대조해야 하는 것은 slot_catalog의 축 이름(`Year`, `Country`, `Energy Source` …)이다. 열 문자는 혼동 요인일 뿐이므로 제거하고, **축 이름을 slot_catalog `key_axes` 표기와 글자 단위로 동일하게** 재작성할 것.

```text
(현행) slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: ...), value=F:% change(+/-), ...
(개선) key_axes=Year(2026~2030 정수), Country(영문 국가명) | value=전년대비 실질 GDP 성장률, 소수형(0.042=4.2%)
```

**D2. key축과 metadata축의 구분 명시 — LiqUtilAdjustment에서 실위험**

LiqUtilAdjustment의 semantic_axes는 `Country, LNG Plant, LNG Plant Train, Life Cycle Category, Nameplate Capacity MTPA, Year, Month, Period`를 전부 "slot="으로 나열한다. 그러나 실제 slot key축은 `Country/LNG Plant/LNG Plant Train/Year/Month` 5개뿐이고 `Period/Life Cycle Category/Nameplate Capacity`는 서버가 채우는 metadata다(`lut_parameters.yaml`, adapters.py:349-350). 현재 문구는 **Step2가 slot_axes에 Period 등을 넣으려 시도**하게 만들 수 있다(서버 sanitize가 거르긴 하나 warning·slot 탈락 비용 발생). semantic_axes를 `key_axes=... | 자동부여 속성=Period, Life Cycle Category, Nameplate Capacity(직접 지정 금지)` 형태로 분리 표기할 것.

**D3. stale 위험이 있는 하드코딩 목록 축소**

- 국가 목록("basecase 예: United States, China, …")과 특히 `"348개 basecase Train 중 선택"` 같은 **개수·목록은 Excel/CSV 갱신 시 DB 텍스트와 어긋난다**. 가용 좌표의 진실은 slot_catalog가 이미 제공하므로, hint의 목록은 대표 예시 2~3개로 축소하고 "실제 선택 가능한 좌표는 slot_catalog 기준"임을 명시하는 문구로 대체.
- 반대로 `Taiwan (China)` 같은 **정확한 표기 예시는 유지 가치가 있다** — L1(정규화 strip-only)과 결합해 표기 그대로 써야 조인이 성립하기 때문. "국가명은 catalog 표기를 글자 그대로 사용" 문구를 공통 추가 권장.

**D4. `proposedValue` 표기 통일**

5개 hint 모두 API 응답 필드명인 camelCase `proposedValue`를 쓰는데, LLM이 반환하는 스키마 필드는 `proposed_value`다. 모델이 보는 유일한 표기로 통일(`proposed_value`)하거나 "제안값"이라는 자연어로 바꿀 것. 사소해 보이지만 필드명을 지시문에 쓰는 순간 표기 불일치는 지시 무시의 빌미가 된다.

**D5. "보수적으로 조정"의 정량화**

GDP·PMI comment의 "basecase 대비 보수적으로 조정"은 모델마다 해석이 갈린다. 파라미터별 현실 범위 가드로 치환 권장:

| 파라미터 | 권장 가드 문구(예시, 도메인 확정 필요) |
|---|---|
| GDP | 정량 전망이 없으면 basecase 대비 ±0.02(2%p) 이내에서 조정 |
| PMI | 통상 40~60 범위, 극단 이벤트에도 30~70을 벗어나지 않게 |
| PowerMix | 비중은 0~1, 단일 이벤트로 ±0.10 초과 조정은 명시 근거 필요 |
| Temperature | 월평균 기온 편차는 intensity의 편차 범위 내, 범위 미제시 시 ±5°C 이내 |
| LiqUtilAdjustment | 상향 여력은 (1 − basecase 가동률) 이내, 하향은 0 미만 금지 |

**D6. 시간 배분 원칙 공통 문구**

이벤트 적용 기간 **외** 월/연도의 slot을 조정하지 않는다는 원칙이 어디에도 명시돼 있지 않다(각 comment가 "적용 월 판단"만 언급). "affected_period/period 밖의 Year/Month는 basecase를 유지한다(제안하지 않는다)"를 공통 추가하면 기간 외 과잉 제안을 줄일 수 있다.

**D7. 병합 comment의 출처 소실 (코드 수정 필요)**

동일 파라미터가 여러 dimension에 매핑되면 `nodes.py:1254`가 mapping_comment들을 `" ".join()`으로 **구분자 없이 이어붙인다**. LiqUtilAdjustment처럼 dimension별 comment가 4~5개인 경우, 어떤 지침이 어떤 dimension 근거인지 LLM이 알 수 없게 된다. `[dimension_key] comment` 접두 형태로 join하도록 코드 수정 권장 (DB 값 수정이 아닌 `_merge...` 로직 1줄 변경).

**D8. hint/comment 표준 템플릿 도입**

5개가 각자 다른 순서·밀도로 서술돼 있다. DB 운영 관점에서 아래 템플릿으로 통일하면 신규 파라미터 추가 시 품질이 유지된다:

```text
parameter_hint = (1) 정의(무엇의 최종 입력값인가) → (2) 단위·형식·예시 →
                 (3) proposed_value 의미(절대값/조정폭) → (4) 허용 범위·극단값 가드 →
                 (5) 좌표 선택 원칙 → (6) 금지사항
mapping_comment(direct/routing) = (1) 트리거 조건 → (2) 조정 방향 → (3) 조정폭 근거 dimension →
                 (4) 시간 배분 dimension → (5) 제한·금지
mapping_comment(indirect) = "무엇의 판단에 사용한다" 단문 (현행 유지)
```

### 6.2 파라미터별 개선

**GDP (id=4)**

- hint의 단위 가드(`0.042=4.2%`)와 comment의 "multiplier 금지"는 우수 — 유지.
- comment(id=127)의 "하방/상방 시나리오를 우선 사용" — 이벤트가 **복수 시나리오 수치를 제시할 때 어느 것을 쓸지 기준이 없다**. "scenario dimension의 강도(economic_intensity)와 부합하는 쪽 수치를 사용한다"로 구체화.
- D5 범위 가드 추가: 정량 전망 부재 시 조정폭 상한.
- LUT 유의점(운영 메모): LUT GDP 성장률은 전년도 데이터가 있어야 산출되므로(§3.5) horizon 첫 해는 reference가 없을 수 있음 — hint가 아닌 CSV 갱신 절차에 반영.

**PMI (id=6)**

- 기준값 50의 의미 설명, "산업용 가스 수요를 조정하는 경기 민감도 변수"라는 역할 규정, basecase 부재 시 "50 중심 산정 + 타국 기준 금지"는 이 5개 중 가장 완성도 높은 서술 — 유지.
- 빠진 것: **절대 범위 가드**(D5). PMI가 20이나 80 같은 비현실 값으로 나가는 것을 막는 문장이 없다.
- 월 배분: PMI는 Year/Month 단위인데 comment에 "단기 경기 강도"만 있고 이벤트 기간 외 월 처리 원칙이 없음(D6).

**PowerMix (id=7)**

- **가장 중요한 공백: 비중 합 제약**. hint가 "Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명"이라고만 해서, Gas만 조정하면 발전 믹스 합이 1에서 벗어나는 문제를 모델이 어떻게 처리하는지(잔여 전원 자동 정규화? Gas 단독 입력 허용?) LLM도 리뷰어도 알 수 없다. **"Gas 비중만 입력하면 잔여 비중은 모델이 재배분한다" 또는 "합이 1이 되도록 상쇄 전원도 함께 제안한다" 중 실제 모델 동작을 확인해 명시**할 것 — 값 산정 방식 자체가 달라지는 분기다.
- event 5의 direct comment 2건(id=26 capacity_change_scale, id=29 alt_energy_absorption)이 **같은 Gas 비중을 서로 다른 근거로 조정** — 병합 주입 시(D7) 이중 반영 위험. 한쪽에 "두 dimension은 하나의 조정폭 산정에 함께 반영하며 각각 별도로 가감하지 않는다" 문구 추가 권장.
- 0~1 범위 및 소수형 가드는 있으나(0.30=30%) 상한 가드(D5) 부재.

**Temperature (id=8)**

- "절대 기온, 한파=하향/폭염=상향, 타국 기온 기준 금지, 해당 국가 기준 계절의 월 선택"까지 방향 서술은 충실 — 유지.
- "**정상 기온**" 이 두 번 나오는데 정의가 없다. Step3가 받는 것은 reference_value 하나뿐이므로 "정상 기온 = 해당 좌표의 reference_value"라고 명시해야 편차 적용 기준점이 고정된다.
- intensity dimension이 편차 범위를 안 줄 때의 폴백 가드(D5) 부재.
- 운영 메모: LUT 기온은 HDD/CDD 역산 근사(base 18°C, ÷30 — adapters.py:29-30,316-320)라 실측 평년값과 다를 수 있음. hint 수정 사항은 아니나, reference_value의 출처 특성으로 §3.5와 함께 도메인 검증 필요.

**LiqUtilAdjustment (id=14)**

- 0~1 범위, 1 초과 예외 조건, "Train 종속 식별 속성" 개념, "basecase 가동률 높은 Train 추가 상향 제한", "생산량 직접 입력보다 가동률 조정 우선"(파라미터 간 역할 경계) — 5개 중 가장 정교함. 유지.
- **`Period` 축의 의미 미정의**: semantic_axes에 "Period(숫자)"로만 등장한다. LLM은 이것이 무엇인지(연속 월 인덱스인지, 분기인지) 알 수 없고, 실제로는 서버 metadata다(D2). "Period는 자동 부여되며 직접 지정하지 않는다"로 정리.
- `"348개 basecase Train"` 개수 하드코딩 제거(D3).
- 상향 조정 comment가 event type 1/2/4/17/18에 걸쳐 **거의 동일 문안으로 5회 복붙**돼 있다(id=6,12,24,99,109). 지금은 일관되지만 향후 한 곳만 수정되는 drift가 필연적 — 표준 문구를 정해 두고 event별 차이(예: id=109의 "제재 시 대체 공급 형성 지연")만 덧붙이는 관리 방식 권장. 장기적으로는 공통 문구를 코드측 프롬프트로 승격하고 DB comment에는 event 특이사항만 남기는 분리가 맞다.
- 상향 여력의 공식화: "0~1 범위와 기존 basecase 수준을 고려" → "상향 폭은 (1 − 현재 가동률) 이내에서 배분"처럼 계산 가능한 형태로(D5).

**Event 21 공통 (id=125, period indirect)**

- `"파라미터의 시간축으로 사용될 수 있다(PMI:Year/Month, GDP:Year)"` — "될 수 있다"는 약한 표현 + 괄호 안 파라미터 나열은 다른 파라미터가 event 21에 추가되면 stale해진다. "제안 대상 파라미터의 적용 Year/Month 판단에 사용한다"로 일반화 권장.

### 6.3 반영 순서 제안

| 순위 | 항목 | 방식 | 이유 |
|---|---|---|---|
| 1 | D1+D2 semantic_axes 재작성 (5건) | DB UPDATE | Step2 slot 탈락률에 직접 영향, 코드 무관 |
| 2 | PowerMix 합 제약 명시 | 도메인 확인 후 DB UPDATE | 값 산정 방식이 갈리는 분기 |
| 3 | D4 proposedValue→proposed_value (5건) | DB UPDATE | 검색치환 수준 |
| 4 | D5+D6 범위·기간 가드 | 도메인 확정 후 DB UPDATE | 극단값·기간 외 제안 방지 |
| 5 | D7 comment join 구분자 | 코드 1줄 (`nodes.py:1254`) | 병합 파라미터 지침 가독성 |
| 6 | D3 목록 축소, D8 템플릿, 복붙 comment 정리 | DB 운영 정비 | drift 예방 |

DB 텍스트 수정은 배포 없이 반영되므로, 수정 → `model-parameter-agent-test` 스킬로 대표 시나리오 재실행 → rationale/값 품질 비교의 루프를 짧게 돌릴 수 있다. §4.4의 스냅샷 기준선을 먼저 만들어 두면 이 루프가 회귀 검증까지 겸한다.

---

## 7. 보안 검토 (신규 — 보안 엔지니어 페르소나)

> 커버리지 참고: SQL 인젝션(ORM 파라미터 바인딩만 사용, raw SQL 없음), 경로 탐색(`registry.py:226-240` `_safe_relative_path` 견고), 콜백 path의 format-string 인젝션/SSRF(치환값은 정수 scenario_id, base_url은 서버 config), 콜백 토큰·헤더 로깅(positional 호출이라 미로깅), TLS 검증(`http_verify:true`, OAuth `trust_env=False`), `.env` gitignore는 **검토 결과 문제없음**으로 확인됨.

### S1. 엔드포인트 인증·인가 전무 — Critical (Blocker)

`api.py`의 세 라우트(propose/sync/confirmation) 어디에도 `Depends`/`Security` 의존성이 없고, `model_param.py:159-166`은 CORS와 RequestLogging 미들웨어만 추가한다. **인증 레이어가 코드 어디에도 없음**(grep 확인).

- `POST /model-parameters/scenarios/{scenario_id}/proposals` — 누구나 **임의 scenario_id**로 제안을 트리거. 소유권/테넌트 검사 없음.
- `POST /model-parameters/proposals/{modelParamProposalId}/confirmation` — **IDOR**. 확정은 `model_param_proposal_id`만으로 row를 찾고(`repository.py`) `request_usr_id`/소유자 대조가 없다. 임의 호출자가 **아무 proposal의 confirmation_parameters를 덮어쓰고 CONFIRMED로 강제**할 수 있다. body의 `user_id`는 공격자 지정값으로 `mod_usr_logn_id`에만 기록된다.

**수정**: 라우터 레벨 인증 의존성(bearer/JWT 또는 ingress mTLS) + 객체 수준 인가(호출자가 해당 scenario/proposal에 접근 권한이 있는지 `request_usr_id`/테넌트 클레임으로 검증). ingress에서 이미 인증을 강제하는 배포라면 그 사실을 문서화하고 최소한 인가(IDOR) 방어는 앱에서 유지할 것.

### S2. 평문 시크릿 git 커밋 — Critical (Blocker)

`envs/config.yaml:70`의 `mlflow_tracking_password`(+ username 69행)가 **git 추적 파일에 평문**으로 있다(`git ls-files` 확인, 커밋 `5062f27`). 실제 값은 문서에서 마스킹한다. DB 비밀번호·OAuth client secret·admin token은 올바르게 `${ENV}` placeholder를 쓰는데(7,43,76행) mlflow만 평문이다. 저장소/이미지 접근자 전원이 크리덴셜을 얻고 git 히스토리에 영구 잔존.

**수정**: `${MLFLOW_TRACKING_PASSWORD}` placeholder로 교체, **노출된 비밀번호 즉시 로테이션**, git 히스토리 purge, CI 시크릿 스캐너 추가. (부수: `mlflow_tracking_uri`가 `http://`(68행)라 이 크리덴셜이 평문 전송됨 — https로 전환.)

### S3. 미인증 자원 고갈 / 요청 크기 무제한 — High

- S1과 결합 시, `POST .../proposals`는 즉시 202를 반환하고 다수의 고비용 LLM 호출을 백그라운드로 돌린다. rate limit이 없어 scenario_id 범위를 루프 돌리면 **LLM 비용·worker 포화**가 무제한(worker 3개). §8 O4와 동일 근본원인.
- confirm의 `confirmation_parameters: list[ProposalParameter]`, `values: list[dict[str,Any]]`에 `max_length` 없음. 게다가 `RequestLoggingMiddleware`가 라우팅 **전에** `await request.body()`로 전체 바디를 메모리에 적재 → 대형 POST 한 번으로 메모리·CPU 고갈.

**수정**: 인증(S1) + per-caller rate limit/quota + 리스트 `Field(max_length=...)` + ingress Content-Length 상한 + 로깅 미들웨어의 대형 바디 버퍼링 skip.

### 도커·시크릿 하드닝 (Medium~Low)

- **M4**: `Dockerfile.model_param:36-42`가 `adduser user root`로 런타임 유저를 **root 보조 그룹에 추가** → 비루트 하드닝 무력화. 이 줄 제거 권장.
- **L1(sec)**: 최종 이미지에 `vim/curl/net-tools/jq/yq/gcc` 잔존(13-22행) — multi-stage 빌드로 런타임 이미지에서 제거.
- **L2(sec)**: base image가 floating tag(`python:3.12-slim-bookworm`) — digest 핀 권장.
- **L3(sec)**: `decorators.py:237-244` 민감키 마스킹이 정확 일치라 `authorization`/`access_token`/`client_secret` 등은 미마스킹 — substring/regex로 전환(현재 콜백 경로에서 악용되진 않음).

---

## 8. 운영·성능 검토 (신규 — SRE/성능 페르소나)

> 커버리지 참고: `RuntimeLruCache` 스레드 안전성, openpyxl 워크북 생명주기(`read_only`/`data_only` + 보장된 close), 그래프 state 직렬화(무거운 객체 `exclude=True`, `basecase_records` 비움), OAuth2 토큰 매니저(더블체크 락·백오프)는 **양호**로 확인됨.

### O1. 인플라이트 BackgroundTask 유실 → PROCESSING 영구 고착 — High (Blocker)

`api.py:80-86`이 Starlette `BackgroundTasks`로 스케줄하고 `flow.py:193`이 실행 전 PROCESSING row를 만든다. 재배포/스케일다운 시 worker가 SIGTERM을 받으면 실행 중이던 프로포절(§O3에 따라 10~30분 소요 가능)이 버려지고, row는 **영구 PROCESSING**(콜백 없음, reconciler 없음).

- **악화 요인 O1-b**: `shutdown_hooks.py:35-51`이 첫 LLM 호출 시 `signal.signal(SIGTERM, ...)`로 **uvicorn의 graceful shutdown 핸들러를 덮어쓴다**. 이후 SIGTERM은 HTTP 클라이언트 close만 스케줄하고 서버 정상 드레인을 트리거하지 않아, gunicorn graceful-timeout(600s) 경과 후 SIGKILL — 인플라이트 태스크가 더 난폭하게 종료됨.

**수정**: (1) 기동 시 임계 시간 초과 PROCESSING row를 FAILED/재시도로 정리하는 **reconciler**, (2) 셧다운 시 인플라이트 드레인 또는 durable queue(at-least-once), (3) `signal.signal` 오버라이드 제거 — 리소스 정리는 lifespan shutdown 단계로 이동.

### O2. health/readiness 엔드포인트 부재 — High (Blocker)

health 라우트가 등록돼 있지 않다(grep으로 내부 DB `healthcheck()` 헬퍼만 존재). lifespan이 `yield` 전에 무거운 fail-hard 작업(schema 검증, LUT 검증, basecase preload — DB의 매핑 테이블까지 읽음)을 한다. DB 지연/파일 누락 시 worker가 lifespan에서 raise → **orchestrator가 "기동 중"과 "죽음"을 구분 못 하고 crash-loop**. preload 성공/경고 수를 노출하는 신호도 없음.

**수정**: liveness(프로세스 up) + readiness(lifespan preload 완료 후에만 200, `basecase_summary.warning_count` 반영) 라우트 추가 후 k8s probe 연결. preload 실패를 lazy 강등으로 완화 검토. `Dockerfile`에 HEALTHCHECK도 추가.

### O-log. prod DEBUG 로그 + 동기 loguru + 전체 페이로드 덤프 — High (Blocker)

`envs/config.yaml:88` `log_level: DEBUG`(config에 기본값 없음), `logger_config.py:46-56`의 loguru sink가 `enqueue=True` 없이 **동기**. DEBUG에서 프롬프트 패킷·basecase 레코드·요청 바디 전체를 직렬화·기록하고, 동기 sink라 매 DEBUG 라인이 이벤트 루프 스레드를 블로킹한다(§C1·C2의 sync-on-loop와 합쳐 처리 지연 가중). `send_callback`은 `log_input=True`로 **전체 proposal 페이로드**를 매 콜백마다 DEBUG 덤프.

**수정**: prod `log_level: INFO`(또는 WARNING), loguru sink `enqueue=True`, 콜백 커넥터 `log_input=False` 또는 플래그 게이팅.

### O3. 프로포절 전체 데드라인 부재 — High

`llm_timeout_sec:310` × `max_retries:1` × 3단계 순차 → **최악 ~30분** PROCESSING, 누적 데드라인 없음. 스트림 활성 시 stall된 스트림이 새 버퍼로 재시도돼 추가 지연. **수정**: `asyncio.wait_for(graph, total_deadline)`로 감싸 데드라인 초과 시 FAILED+콜백.

### O4. 백그라운드 동시성 상한 부재 → DB 풀 고갈 — High

`BackgroundTasks`는 무제한 스케줄되고 accept 엔드포인트는 큐/세마포어 없이 즉시 202. sync DB 풀은 worker당 5+10=15. accept 버스트가 수십 개 동시 백그라운드를 만들면 커넥션 체크아웃이 15를 초과해 `pool_timeout`(30s) → `QueuePool limit timed out`. **수정**: `run_propose_parameters_background`에 `asyncio.Semaphore`(또는 실제 태스크 큐), 그 상한에 맞춰 풀 사이징, sync DB를 `to_thread`로.

### O5. gunicorn `--preload` 부재 → 캐시·preload worker 3배 중복 — High

`Dockerfile.model_param`의 `GUNICORN_WORKERS=3`에 `--preload` 없음 → lifespan이 worker당 1회 실행. schema 검증·LUT 검증·`preload_basecase_runtime_cache`(3개 `.xlsm` 전량 파싱, 레코드 전량 추출)가 **3회 중복**, 모듈 전역 캐시(`_PARAMETER_KB_CACHE`, `_BASECASE_RECORD_CACHE`)도 3중화 → 기동 CPU·시간·정상상태 메모리 3배.

- **O5-b (메모리)**: `_BASECASE_RECORD_CACHE`는 max=32로 시작하나 `preload_basecase_runtime_cache`가 `ensure_capacity(len(candidates))`로 전체 후보 수까지 상한을 올리고 낮추지 않음 → 후보별 전체 추출 레코드가 프로세스 생명주기 내내 상주(매트릭스 시트는 셀당 레코드). worker 3배와 결합 시 메모리 한정 pod에서 OOMKill 위험.

**수정**: 메모리 한도를 3×preload 크기에 맞춰 설정하거나, pre-fork 빌드(`on_starting`/`--preload`)로 COW 공유. `ensure_capacity` 상한 캡.

### O-obs. 관측성 (Medium)

- **트레이스 부재**: `run_propose_parameters_background`가 `TraceContext`/transaction_id를 만들지 않아 LLM 호출에 `aip-transaction-id` 헤더가 없고 MLflow/LangChain 상관관계 부재. accept→백그라운드→콜백을 잇는 end-to-end 트레이스 없음(proposal_id/scenario_id 수동 필드만).
- **메트릭 부재**: PROCESSING/FAILED proposal 수를 알 방법이 DB 직접 조회뿐(§O1의 고착 리스크와 결합 시 신호 공백). Prometheus 카운터/게이지 권장.

### 도커·config (Medium~Low)

`KEEP_ALIVE=600`(과도), `--max-requests` 부재(캐시 증가분 회수 불가), HEALTHCHECK 없음, `DB_POOL_SIZE=5/overflow=10`이 무제한 백그라운드 대비 작음, LLM/HTTP 세마포어가 per-worker라 실제 게이트웨이 동시성은 3배(llm 10→30).

---

## 9. LLM 출력 견고성 검토 (신규 — 적대적 LLM 테스터 페르소나)

> 관통하는 구조적 사실: `validation_warnings`는 모든 "제외됨" 사유가 기록되는 **유일한 곳인데 사용자에게 전혀 노출되지 않는다**(`presentation.py`/`api.py`/`schemas/api/parameters.py`에 부재 확인). 아래 모든 silent drop은 사용자에게 안 보이고, 파라미터가 그냥 사라진다.

### V1. `proposed_value` 유한성·범위 검증 전무 — Critical (Blocker)

`_sanitize_llm_adjustments`에서 `proposed_value`에 대한 유일한 검사는 `if proposed_value is None`(`nodes.py:2498`). 그 외 전부 통과:

- 문자열 `"3.2"`, boolean `true`, `1e308`, 음수, `utilization=45.0`(비율이어야 하는데 4500%) — **범위·타입 검사 전혀 없음**. `ParameterValueCell.proposed_value`는 `Any`(`schemas/model_parameter_proposal.py:59`). 비정상 값이 그대로 `presentation._build_proposal_parameters` → `save_proposal_result` → DB JSON → Backend 재조회까지 **무검증 end-to-end** 통과.
- NaN/Infinity는 pydantic-core 버전 의존 동작이라 *probable-but-unverified*로 표기하나, 문자열/bool/거대수/음수는 확정적으로 통과.

수급모델 DB로 흘러가는 값이라 **한 번의 값 환각이 곧 하위 모델 실행 오염**. **수정**(가장 저렴·고가치): 2498행 null 체크 직후 float 강제 변환 + 비유한 거부, 가능하면 파라미터 spec registry(이미 로드됨)의 `[min,max]` 범위 검사.

### V2. 파라미터가 말없이 탈락하는 경로들 — High

- **라우팅 부분 반환**(`nodes.py:2227`): Step1.5가 일부 dimension만 반환하면 누락 dimension의 후보 전원 제외, warning만. 해당 dimension은 **파라미터 0개, 조용히**.
- **빈 selected_candidate_keys**: 반환됐으나 아무것도 안 고른 경우 warning조차 없음(더 조용함).
- **axis-name 대소문자**(`nodes.py:594-597`): `set(provided) == set(expected)`가 대소문자 구분 → `"year" != "Year"`면 **slot 통째 드롭**. 값은 소문자화하지만 축 이름은 안 함.
- **Period 미강제**(`nodes.py:2334`): `_slot_axis_value`가 `year`/`month`만 정수 강제, `Period`는 문자열 `"3"`이 그대로 → int 키와 exact-match 실패 → 드롭. `TIME_SLOT_AXIS_NAMES`에는 Period가 있는데 불일치.

**수정**: (1) API 응답에 `excluded_parameters` 머신리더블 필드 추가(§L4와 동일 처방), (2) `schema_matches`에서 축 이름 대소문자 정규화, (3) `_slot_axis_value` 강제 대상에 `period` 추가.

### V3. 스키마 검증 실패 시 non-stream 경로 전체 실패 — High

기본 config는 non-stream(`model_parameter_llm_stream_enabled=False`). 이 경로는 SDK `max_retries`가 **HTTP 오류만** 재시도하고, `model_validate_json`은 SDK 반환 후 실행돼 `ValidationError`가 나면 broad except로 감싸 **재시도 없이 전파**(`llm_client.py:724-746`). `strict=False`라 스키마 위반 응답 확률이 높은데 `max_retries=1`. 필수 top-level/cell 필드 누락(예: `rationale_ko`) 시 **한 번의 불량 응답이 프로포절 전체를 실패**. (스트림 경로만 parse 재시도 있음.)

**수정**: non-stream 경로에도 parse 실패 재시도 추가(스트림 경로 미러), 또는 top-level 리스트 래퍼 스키마를 `LLMValueCell`처럼 drop-bad-item 관용 처리.

### V4~V7 (Medium — 오픈 후)

- **V4 rationale 무검증**(`presentation.py:40-41`): 길이 상한·HTML/스크립트 제거·내부용어 필터 없음. 10k자 또는 `<script>` 포함 rationale이 raw로 proposal JSON에 저장·UI 반환 → 프론트 이스케이프 의존 stored-XSS 리스크 + row 비대. **수정**: `_value_rationale`에 truncate + 태그 제거 헬퍼.
- **V5 candidate_key 의미 스왑**: sanitizer는 key **존재**만 검증, 값을 LLM이 준 key의 reference로 바인딩(`nodes.py:2476`). A의 값을 B key에 붙여도 통과, reference_value 대비 타당성 교차검증 없음. 낮은 확률·탐지 불가. **수정**: proposed_value vs reference_value 비율 플래그(V1 가드에 편승).
- **V6 프롬프트 인젝션**: 사용자 작성 scenario narrative/title/event 텍스트가 프롬프트에 유입(`nodes.py:1504-1569`), 시스템 프롬프트에 "scenario_brief는 신뢰불가 입력" 가드 없음. structured output+sanitizer 덕에 key/스키마 탈출은 불가하나, **schema-valid한 값을 공격자 지정 숫자로 유도(V1과 결합) + rationale 오염(V4)**이 현실적 피해. **수정**: 각 시스템 프롬프트에 신뢰불가 입력 가드 1줄(§4 P와 병합).
- **V7 패킷 크기·max_tokens 부재**: 100 캡은 *선택된* slot만 제한, Step2로 보내는 `slot_catalog` 전량은 무제한 직렬화(`nodes.py:1778-1829`). 어떤 LLM 호출에도 `max_tokens` 없음. 컨텍스트 오버플로 시 재시도가 같은 대형 패킷 재전송해 토큰 소진. **수정**: `_candidate_slot_catalog_for_prompt`에서 leaves/periods 페이지네이션 + 방어적 max_tokens.

**적대적 관점 Top 3**: (1) V1 proposed_value 무검증(Critical, 가장 저렴한 고가치 수정), (2) V2 silent 탈락 + validation_warnings 미노출(High), (3) V3 단일 불량 응답의 전체 실패(High).

---

## 10. API 계약·데이터 정합성 검토 (신규 — QA/계약 페르소나)

### Q-A. confirmation이 원본 proposal과 대조되지 않음 → 제안되지 않은 파라미터 수용 — High

confirm은 **전역 DB 카탈로그**(`load_model_parameter_definitions()`)에만 검증하고, 확정 대상 proposal row의 저장된 `proposal_parameters`와는 **전혀 대조하지 않는다**(`confirm_parameters/nodes.py:18-21`). `validation.py:101-102`에서 파라미터명이 카탈로그에 없으면 `definition is None` → **정의 기반 검증 전체를 건너뛰어** 임의 `parameterName`+`modelTarget`+`values`가 구조 검증만 통과한다. `confirm_proposal_result`(`model_parameter_service.py:261-306`)도 status만 보고 payload를 proposal과 비교하지 않는다. 이 동작은 테스트로 고정돼 있다(`test_confirmation_validation_accepts_unknown_parameter_metadata`, contract test:4040).

- **S1 IDOR와 결합 시 심각도 상승**: 인증 없는 confirm(S1) + 원본 미대조(Q-A) → 공격자가 아무 proposal에 **조작된 파라미터 배열**을 확정·영속화할 수 있고, `fetch_proposals_by_group`(`repository.py:129-133`)가 CONFIRMED row의 `confirmation_parameters`를 우선하므로 **조작 값이 가격 해석(interpret) 입력으로 흘러간다**.

**수정**: proposal의 저장된 `proposal_parameters`를 `validate_confirmation_parameters`에 주입해, 확정되는 `(parameter_name, model_target, slot-set)`이 제안된 집합의 부분집합임을 강제(사용자 추가 파라미터를 허용할 제품 의도라면 명시적 화이트리스트).

### Q-B. 실패 콜백이 `data=None` → 선언된 `status="FAILED"`는 death code — Medium

`api_schema.py:45-51`이 콜백 `data.status: Literal["PROPOSED","FAILED"]`를 선언하지만, 실패 시 `_callback_error_output`(`presentation.py:370-378`)이 `data=None`을 보낸다. `"FAILED"` enum은 실제로 생성되지 않는다. Backend는 top-level `status`나 재조회로만 실패를 구분해야 함. **수정**: 실패 시 `ProposeParametersCallbackData(..., status="FAILED")` 방출 또는 Literal에서 `"FAILED"` 제거 후 `data=None` 문서화.

### Q-C. propose 멱등성·유니크 제약 없음 → scenario당 중복 PROCESSING row — Medium

`create_processing_proposal`이 항상 새 PROCESSING row를 INSERT(`repository.py:63-84`)하고, `MiModelParamProposalModel`에 **scenario_id UniqueConstraint 없음**(`models.py:21-44`). 같은 scenario에 propose를 2번 하면 PROCESSING 2개·백그라운드 2개·PROPOSED 2개가 생기고, `fetch_proposals_by_group`은 scenario당 max id만 조용히 유지 — **오래된 id를 targeting한 confirm은 stale proposal을 확정**한다. **수정**: INSERT 전 비종결(PROCESSING/미확정 PROPOSED) row 거부/치환 또는 가드된 유니크 규칙.

### Q-D. 저장 datetime이 naive `datetime.now()` → KST/UTC 불일치 — Medium

`repository.py:56,175,194,214,233`이 `proposal_completed_dtm`/`confirmed_dtm`/`callback_sent_dtm`에 naive `datetime.now()`(서버 로컬) 사용. 프로젝트에 `settings.time_zone` 기반 tz-aware 헬퍼(`apps/common/utils/time_utils.py:11-18`)가 있는데 무시. pod가 UTC이고 Backend/UI가 KST 가정이면 4개 타임스탬프가 tz 마커 없이 9시간 어긋남. (Dockerfile은 KST 이미지지만 — 커밋 `114b1c1` — 명시적 tz-aware 저장이 안전.) **수정**: repository 쓰기 전반에 tz-aware now 일관 적용.

### Q-E. `na`-only/빈 시나리오는 정상 "빈 제안"이 될 수 없고 항상 FAILED — Medium

`finalize_empty_parameter_values`가 전부 `selected=False`+빈 grid를 반환(`nodes.py:717-738`) → presentation이 skip → `proposal_parameters==[]` → `_ensure_proposal_parameters`가 `INVALID_REQUEST` raise(`validation.py:76-90`). 정당하게 파라미터 0개인 시나리오가 **진짜 에러와 구분 불가**: sync는 4xx, background는 FAILED+에러 콜백. Backend는 "성공했으나 0개" 계약을 받을 수 없다. **수정**: 0개가 유효하다면 `status=PROPOSED` + `proposalParameters=[]`로 반환.

### Q-F. dead 그래프 분기 — Low

`flow.py:97-104`가 `validate_parameter_candidates → finalize_empty_parameter_values` 조건 엣지를 연결하지만, 라우터 `_route_after_candidate_validation`(`validation.py:12-21`)은 `load_basecase_samples`를 반환하거나 **raise**만 하고 finalize 키를 절대 반환하지 않는다. accept↔실행 사이 후보가 사라진 background 재실행은 finalize 대신 hard-raise. **수정**: 빈 후보 케이스에 finalize 문자열 반환 또는 미사용 엣지 삭제.

### Q-G/Q-H. 스키마 정합 — Low

- **Q-G**: 응답/콜백의 `scenarioGroupId`/`eventId`가 `_int_or_none`+`response_model_exclude_none=False`로 **null 직렬화 가능**한데(`presentation.py:302-315`), DB 컬럼은 `nullable=False`(`models.py:62-81`)이고 영속 경로는 `_required_int`로 int 보장 — API Optional vs DB required 불일치. out-schema를 required로.
- **Q-H**: `crt_usr_logn_id`/`mod_usr_logn_id`(String(100), 로그인 id)에 숫자 `user_id`를 저장(`repository.py:52-53,75-76,176-177`), 암묵적 int→str 강제에 의존하고 `"system"` fallback과 혼재. 로그인 id 문자열 저장 권장.

### 테스트 커버리지 (QA 인벤토리)

- **테스트됨**: 빈 후보 거부, finalize 빈 반환, confirm status 게이팅(PROCESSING 거부·CONFIRMED 재확정 허용), confirm 구조 검증, 콜백 성공/에러(`data=None`) 형태, `skip_callback→SKIPPED`, 콜백 URL format 실패→`callback_status=FAILED`, LUT 파이프라인(과생성 캡·exact miss·중복 slot·sanitize).
- **미테스트(중요)**: **background 프로포절 실패 경로**(graph raise→`fail_proposal_result`+에러콜백; 두 background 테스트가 오히려 `fail_proposal_result` 호출을 금지) — §C3 Blocker가 무테스트, **`send_callback` raise→`update_callback_status(FAILED)` 경로**, confirm 동시성/TOCTOU(§C5), propose 멱등성(Q-C), confirmation 원본 대조(Q-A, 기능 부재), datetime tz(Q-D), 정당한 빈 시나리오 성공 계약(Q-E).

> 시사점: 가장 신뢰성이 중요한 실패·동시성 경로가 정확히 테스트 공백이다. §5 Blocker 수정과 함께 이 경로들의 테스트를 추가하는 것을 오픈 기준으로 삼기를 권장.

---

## 11. 독립 2차 소견 (신규 — Codex CLI 교차 검증)

Codex CLI로 동일 범위를 독립 리뷰했다. 상당수가 위 페르소나 발견을 **독립적으로 재확인**해 신뢰도를 높였고(교차확인: confirmation 원본 미대조=Q-A, non-stream 재시도=V3, 멱등성 부재=Q-C, 라우팅 카디널리티=V2, Step2 캡 순서=C7), 아래는 **Codex가 새로 짚은 항목**이다.

### X1. repository 상태전이 쓰기가 row 부재 시 조용히 성공 반환 — Medium~High (데이터 정합성)

`complete_model_param_proposal`(`repository.py:189-191`), `fail_model_param_proposal`, `confirm_model_param_proposal`(`:170-172`) 모두 대상 row가 없거나 soft-delete(`del_yn`)면 **아무것도 안 하고 return**한다. 세션은 정상 commit되고, 백그라운드 플로우는 DB row가 갱신되지 않았는데도 **성공 `PROPOSED` 콜백을 방출**할 수 있다(§C3의 PROCESSING 고착과 정반대 방향의 정합성 붕괴 — "갱신 안 됐는데 성공 통보"). **수정**: 영향받은 row 수를 확인하거나 부재 시 `ENTITY_NOT_FOUND` raise, 상태전이가 실제 영속된 뒤에만 성공 콜백 구성.

### X2. sync 테스트 엔드포인트가 프로덕션 라우터에 등록·DB 저장 — Medium

`api.py:28-53` `POST .../proposals/sync`("테스트 및 로컬 검증용"으로 명시)가 프로덕션 `router`에 그대로 등록돼 있고, 성공 시마다 `save_proposal_result`로 **PROPOSED row를 저장**한다(`flow.py:142`). 부하 테스트·진단 호출이 프로덕션 proposal 이력을 오염시키고 "최신 proposal"로 소비될 수 있다(§Q-C·X-latest와 결합). **수정**: 프로덕션에서 비활성화 또는 환경별 라우터 분리, 또는 명시적 test-only 플래그가 없으면 비영속.

### X3. basecase 추출 예외의 LUT 조용한 대체 — Medium (정합성)

후보별 basecase 추출 예외가 warning으로 강등되고 계속 진행(`parameter_mapping.py:681`)되는데, **LUT 활성 시 읽기 실패한 authoritative basecase가 "basecase 없음"으로 취급돼 LUT 기본값으로 대체**된다 → 눈에 안 보이게 그럴듯하지만 틀린 제안. (§L-broad-except를 LUT 정합성 관점에서 더 날카롭게 재정의.) **수정**: "basecase 정상 부재"와 "추출/설정 실패"를 구분해, 실패는 해당 파라미터 격리 또는 요청 실패로, LUT-only 해석은 명시적 유효 부재에만 허용.

### X4. confirm 중복 탐지가 정규화 불일치로 우회 — Medium (정합성)

confirm의 중복 탐지는 raw JSON/문자열 시그니처를 쓰는데(`confirm_parameters/validation.py:86,284`) master 정의 검증은 이름을 정규화한다. `Temperature`/`temperature` 또는 `2027`/`"2027"` 두 항목이 **둘 다 검증을 통과하고 downstream 정규화 후 같은 model target/cell을 가리켜 충돌 쓰기**를 만든다. (§V2 axis 대소문자·Period 문제의 confirm 측 대응물.) **수정**: 중복 시그니처를 model-target 검증과 동일한 canonical화(정규화 이름 + 타입/canonical axis 값)로 구성.

### X5. 커넥터가 호출마다 httpx/AsyncOpenAI 클라이언트 생성 — Medium (성능)

LLM 각 단계가 `AsyncClient`/`AsyncOpenAI` 쌍을 새로 만들고 닫으며(`llm_client.py:99,748`), 콜백도 매번 새 클라이언트(`callback_client.py:39`). 프로포절 하나가 여러 번의 커넥션/TLS 셋업을 반복 → keepalive 무의미, 부하 시 지연·소켓 처닝 증가. **수정**: 공유 async 클라이언트를 app lifespan에서 관리·풀 재사용·셧다운 시 close(요청 레벨 세마포어는 유지).

### X6. accept와 background의 이중 컨텍스트 로드 — Low (성능)

accept(`flow.py:187`)가 scenario/group/event/templates/mapping/definitions 전체를 로드하고, background 그래프(`flow.py:229`)가 즉시 같은 데이터를 다시 로드 → 수락된 요청마다 **완전한 컨텍스트 DB 읽기 2회**. **수정**: accept 검사를 경량 존재/후보 쿼리로, 또는 불변 컨텍스트 스냅샷을 background에 전달.

### X7. `fetch_proposals_by_group`가 전체 이력을 Python에서 필터 — Low (성능)

`repository.py:101`이 그룹의 모든 PROPOSED/CONFIRMED row를 조회·구체화한 뒤 scenario별 최신을 Python에서 선택 → 이력 증가에 비례해 DB 전송·메모리·지연 증가. **수정**: SQL 윈도우 함수 또는 `MAX(id)` grouped 서브쿼리로 최신 id만 선택 후 fetch.

### Codex 프로덕션 준비도 판정 (원문 요지)

> "중복 proposal 생성과 confirmation payload 신뢰가 모호하거나 오염된 모델 입력을 만들 수 있어 무제한 프로덕션 오픈에는 준비되지 않음. 최소한 원자적·멱등적 proposal 생성, confirmation을 저장된 proposal의 불변 데이터에 바인딩, Step1.5/Step2 검증과 structured-output 재시도 강화가 오픈 전 필요."

이는 본 리포트의 독립 결론(§1 한 줄 결론)과 일치한다.

---

## 12. 최종 통합 결론

5개 페르소나 + Codex 교차 검증 결과, **분석 파이프라인의 코어 로직은 신뢰할 만하나 서비스 경계·운영·데이터 신뢰 계층이 오픈 기준에 미달**한다. 세 가지 독립 리뷰가 공통으로 수렴한 최상위 리스크는:

1. **인증/인가 부재(S1) + confirmation 원본 미대조(Q-A/X-confirm)** — 조작된 모델 입력이 하위 가격해석까지 무검증 전파. 보안·QA·Codex 3자 모두 지적.
2. **값 정합성 방어선 부재(V1)** — LLM이 만든 비정상 값이 DB까지 무검증 통과. 적대적·Codex 공통.
3. **비동기 경계·실패·운영 안전망(C1~C4, O1~O5)** — 조용한 고착·유실·자원 고갈. 초기 리뷰·SRE·Codex 공통.

이 세 축(보안/인가 · 값 검증 · 운영 신뢰성)을 오픈 게이트로 삼기를 권장한다.

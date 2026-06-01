# Scenario HITL Agent

LangGraph 기반 **Scenario / Signpost 생성 + HITL(Human-In-The-Loop) 편집** 파이프라인.
단일 이벤트(`input_event.json`)에서 시작해 사용자가 두 번의 편집 단계를 거쳐
정규화된 시나리오 묶음(`scenarios_final.json`)을 산출한다.

---

## 1. 전체 흐름

```
input_event.json
      │
      ▼  ── Step 1) Draft 생성 (LangGraph: parse_branch → dimension_matrix → save_draft)
scenarios_draft.json
      │
      │   ── 사용자: scenarios_human_edited.json 직접 수정 (dimension_values / title / description …)
      ▼  ── Step 2) Stage A  (scenario HITL)
scenarios_final.json              ── apply_human_edit → audit → narrative refine → signpost attach
      │
      │   ── 사용자: scenarios_signpost_edited.json 직접 수정 (label_ko / strength / keyword_hints / likelihood_prior)
      ▼  ── Step 3) Stage B  (signpost HITL)
scenarios_final.json (갱신)        ── signpost merge → rationale 재생성 → likelihood 정규화 (합=1)
scenarios_final_initial.json      ── Stage A 1차 결과 백업
```

Stage A / Stage B 모두 같은 패턴의 단일 진입점 한 쌍을 노출한다.

| 단계    | Disk-aware entrypoint                                | In-memory entrypoint                       |
| ------- | ---------------------------------------------------- | ------------------------------------------ |
| Stage A | `stage_scenario_hitl.run_scenario_hitl_resume`       | `run_scenario_hitl_postprocess`            |
| Stage B | `stage_signpost_hitl.run_signpost_hitl_resume`       | `run_signpost_hitl_postprocess`            |

---

## 2. 폴더 구조

```
src_scenario_hitl/
├── stage_hitl_flow.py              # ★ 메인 CLI: Draft → Stage A → Stage B 일괄 실행
├── stage_scenario_hitl.py          # Stage A 후처리 (merge + audit + narrative refine + signpost attach)
├── stage_signpost_hitl.py          # Stage B 후처리 (signpost merge + rationale 재생성 + likelihood 정규화)
├── stage_integrated_scenario.py    # Scenario LangGraph stage1~5 (시나리오 합성)
├── stage_integrated_signpost.py    # Signpost 파이프라인 (시나리오별 signpost 생성)
├── _openai_client.py               # SKT AI Gateway / OpenAI 호환 클라이언트 + structured output 헬퍼
├── template_registry_geopolitical.json   # 시나리오 dimension/enum 템플릿 레지스트리
├── input_event.json                # 입력 이벤트 예시
│
├── core/                           # 인프라 레이어
│   └── storage/
│       ├── file_client.py          # JSON read/write (atomic, thread-safe)
│       └── file_checkpointer.py    # thread_id 기반 draft/final/graph_state 저장
│
├── domains/                        # 도메인 + 인터페이스 레이어
│   ├── interfaces/http/api/v1/
│   │   ├── _runtime.py             # LangGraph app + FileCheckpointer 캐시
│   │   └── generator.py            # run_generator(): 이벤트 → draft (HITL interrupt까지)
│   └── workflow/
│       ├── graphs/pipeline.py      # LangGraph DAG 정의 (apply_human_edit 직전에 interrupt)
│       └── lng/                    # LNG 도메인용 프롬프트/스키마 placeholder
│
├── modules/                        # 도메인 모듈 (LangGraph 노드 구현체)
│   ├── scenario_engine/engine.py   # 이벤트 → stage1~5 시나리오 그룹 state 생성
│   ├── hitl_manager/manager.py     # 사용자 편집본 merge + scenario_id 재번호 + validate
│   └── signpost_binder/binder.py   # 시나리오 final_state → signposts 자동 부착
│
└── data/<thread_id>/               # 모든 산출물이 thread_id 별로 격리 저장
    ├── scenarios_draft.json              # Step 1) Draft
    ├── scenarios_human_edited.json       # Stage A 사용자 편집본 (입력)
    ├── scenarios_final.json              # Stage A/B 최종 결과
    ├── scenarios_final_initial.json      # Stage A 1차 결과 백업
    ├── scenarios_signpost_edited.json    # Stage B 사용자 편집본 (입력)
    ├── scenarios_audit.log               # Stage A audit (compatibility/MECE)
    └── graph_state.json                  # LangGraph 체크포인트 스냅샷
```

### 레이어 의존 방향

```
stage_hitl_flow.py (CLI)
        ↓
stage_scenario_hitl / stage_signpost_hitl   ──┐
        ↓                                     │
domains/interfaces/http/api/v1                │  (어디서나 사용)
        ↓                                     ▼
domains/workflow/graphs/pipeline   ──→   modules/*      ──→  core/storage
```

---

## 3. 사전 준비

### 3-1. Python 의존성
- Python **3.10+**
- `langgraph`, `pydantic`, `openai`, `python-dotenv`

```bash
pip install langgraph pydantic openai python-dotenv
```

### 3-2. 환경 변수 (`.env` 또는 export)
LLM refine(Stage A의 narrative refine, Stage B의 rationale 재생성)은 SKT AI Gateway를 호출한다.

| 변수                       | 필수 | 기본값                          | 설명                                |
| -------------------------- | ---- | ------------------------------- | ----------------------------------- |
| `SKT_AI_API_KEY`           | O    | -                               | SKT AI Gateway API 키 (`OPENAI_API_KEY` 도 fallback) |
| `MI_LLM_MODEL`             |      | `skmidev-gpt-5.5-20260424`      | 호출 모델명                         |
| `REF_MODEL`                |      | `MI_LLM_MODEL` 값                | refine 단계 전용 모델 오버라이드    |
| `REF_MAX_TOKENS`           |      | `4096`(A) / `2048`(B)           | refine max tokens                   |
| `REF_LIKELIHOOD_DECIMALS`  |      | `4`                             | likelihood 정규화 반올림 자릿수     |

```bash
export SKT_AI_API_KEY="sk-..."
```

`--skip-narrative-refine` / `--skip-rationale-refresh` 옵션을 모두 사용하면 LLM 호출 없이 전체 흐름을 실행할 수 있다.

---

## 4. 실행

### 4-1. 기본 실행 (Draft → Stage A → Stage B 일괄)

```bash
python stage_hitl_flow.py -i input_event.json -t thr_lng_demo_001 -s data \
    --audit-log-path data/thr_lng_demo_001/scenarios_audit.log \
    --signpost-edited-path data/thr_lng_demo_001/scenarios_signpost_edited.json \
    --initial-final-backup-path data/thr_lng_demo_001/scenarios_final_initial.json
```

실행 중 두 번의 사용자 편집 시점에서 `Enter` 입력을 대기한다.

1. **Stage A 편집 대기**  
   `data/<thread_id>/scenarios_human_edited.json` 을 편집  
   → 이후 콘솔에서 삭제할 `scenario_id` 와 `시나리오 1개 추가 여부 (Y/N)` 입력
2. **Stage B 편집 대기**  
   `data/<thread_id>/scenarios_signpost_edited.json` 을 편집 (signpost 필드 + `stage5_validation.likelihood_prior`)

### 4-2. CLI 옵션 요약

| 옵션                                | 기본값                                                | 설명                                          |
| ----------------------------------- | ----------------------------------------------------- | --------------------------------------------- |
| `-i`, `--event-input-path`          | (필수)                                                | 입력 이벤트 JSON                              |
| `-t`, `--thread-id`                 | (필수)                                                | 작업 thread id                                |
| `-s`, `--storage-root`              | `data`                                                | 산출물 root 디렉터리                          |
| `-e`, `--edited-payload-path`       | `<root>/<tid>/scenarios_human_edited.json`            | Stage A 편집본 경로                           |
| `--signpost-edited-path`            | `<root>/<tid>/scenarios_signpost_edited.json`         | Stage B 편집본 경로                           |
| `--audit-log-path`                  | `<root>/<tid>/scenarios_audit.log`                    | Stage A audit 로그 경로                       |
| `--initial-final-backup-path`       | `<root>/<tid>/scenarios_final_initial.json`           | Stage A 결과 백업 경로 (Stage B 진입 직전)    |
| `--skip-generate`                   |                                                       | 기존 `scenarios_draft.json` 재사용 (Step 1 생략) |
| `--auto-resume`                     |                                                       | 편집 대기 시 Enter 없이 즉시 진행             |
| `--skip-narrative-refine`           |                                                       | Stage A LLM refine 생략 (audit log 은 유지)   |
| `--skip-signpost-hitl`              |                                                       | Stage B 전체 생략                             |
| `--skip-rationale-refresh`          |                                                       | Stage B 의 `rationale_ko` LLM 재생성만 생략   |

### 4-3. 자주 쓰는 시나리오

```bash
# (a) Stage A만 다시 실행 (이미 draft 있음)
python stage_hitl_flow.py -i input_event.json -t thr_lng_demo_001 -s data \
    --skip-generate --skip-signpost-hitl

# (b) Stage B만 다시 실행 (final 있음 → signpost edit 재반영)
python stage_hitl_flow.py -i input_event.json -t thr_lng_demo_001 -s data \
    --skip-generate

# (c) LLM 호출 없이 dry-run (audit/정규화만)
python stage_hitl_flow.py -i input_event.json -t thr_lng_demo_001 -s data \
    --skip-narrative-refine --skip-rationale-refresh --auto-resume
```

### 4-4. 모듈 단독 호출

```python
from domains.interfaces.http.api.v1.generator import run_generator
from stage_scenario_hitl import run_scenario_hitl_resume
from stage_signpost_hitl import run_signpost_hitl_resume

run_generator(event_input_path="input_event.json",
              storage_root="data", thread_id="thr_lng_demo_001")

run_scenario_hitl_resume(thread_id="thr_lng_demo_001",
                         storage_root="data",
                         edited_payload_path="data/thr_lng_demo_001/scenarios_human_edited.json")

run_signpost_hitl_resume(final_state_path="data/thr_lng_demo_001/scenarios_final.json",
                         edited_payload_path="data/thr_lng_demo_001/scenarios_signpost_edited.json",
                         backup_path="data/thr_lng_demo_001/scenarios_final_initial.json")
```

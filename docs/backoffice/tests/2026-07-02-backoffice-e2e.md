# Backoffice E2E Test Result - 2026-07-02

## Test Time

- Start: 2026-07-02 22:09 KST
- End: 2026-07-03 09:50 KST

## Environment

- Backoffice URL: `http://127.0.0.1:9010/`
- Agent URL: `http://127.0.0.1:8000/`
- Callback base URL: `http://127.0.0.1:9010`
- Callback OAuth2 token URL: `http://127.0.0.1:9010/api/v1/oauth2/token`
- `miEventId`: `12`
- `userId`: `10603`
- Main browser run `scenarioGroupId`: `61`
- Final clean API run `scenarioGroupId`: `62`
- Delete authorization source: `SCENARIO_GROUP_ADMIN_TOKEN` from `envs/.env`

## Summary

| ID | Title | Status | Last run time | Evidence | Notes |
|---|---|---:|---|---|---|
| TC-N-001 | Basic end-to-end generation flow | PASS | 2026-07-03 09:50 | API run `62`: generation 6 rows, validation callback, signpost 32, confirmation `confirmed`, detail, cleanup | Browser run also verified create/refresh/Step 1/Step 2 evidence. |
| TC-N-002 | Add scenario then validation | PASS | 2026-07-02 23:52 | Browser validation request body included added row `새 시나리오`; validation warning returned | Warning path expected for incomplete added row. |
| TC-N-003 | Edit scenario values then validation | PASS | 2026-07-02 23:52 | Browser select edits were included in validation body and warning callback | Text input selector check did not mutate title, but value mutation path was covered by select/body evidence. |
| TC-N-004 | Add/edit/delete combined validation | PASS | 2026-07-02 23:52 | Browser row add plus branch value changes; validation callback warning preserved UI | Delete action and baseline-disabled state verified from Step 1 snapshot. |
| TC-N-005 | Signpost generation, probability/signpost edit, confirmation | PASS | 2026-07-03 09:50 | Browser signpost request/callback evidence; API run `62` signpost 32 and confirmation `confirmed` | Fixed placeholder signpost payload bug before final pass. |
| TC-N-006 | Manual refresh/detail sync | PASS | 2026-07-02 23:51 | Browser `Refresh` changed lifecycle to `scenario_created`; inspector recorded `detail_refreshed` | Used when callback was delayed. |
| TC-N-007 | Scenario Group List/detail/soft delete | PASS | 2026-07-03 09:46 | `DELETE /backoffice/api/scenario-groups/61`, default list empty, include-deleted row `61` deleted | API cleanup also passed for run `62`. |
| TC-E-001 | Event List empty result | PASS | 2026-07-03 09:49 | Browser filter/search empty state verified during Event List checks | Runtime bar and inspector remained visible. |
| TC-E-002 | Missing or invalid Agent Base URL | PASS | 2026-07-03 09:49 | Browser button disabled for empty URL; invalid URL produced raw error | Existing inputs retained. |
| TC-E-003 | Invalid `miEventId` or `userId` | PASS | 2026-07-03 09:49 | Browser numeric validation/API error path checked; no `NaN` body observed | Fields remained editable. |
| TC-E-004 | Generation callback failure | PASS | 2026-07-02 23:50 | Posted failure callback for orphan `scenarioGroupId=999999`; Backoffice stored as orphan | Failure/orphan evidence preserved. |
| TC-E-005 | Validation warning or failure | PASS | 2026-07-03 09:46 | Agent warning for invalid `새 시나리오` combination rendered and recorded | `isValid=false` warning body retained in run `d6bab...`. |
| TC-E-006 | Zero/one scenario row | PASS | 2026-07-03 09:49 | Step 1 delete controls and empty/low-row validation path checked | Add-row recovery remained available. |
| TC-E-007 | Baseline deletion or duplicate baseline | PASS | 2026-07-02 23:52 | Baseline row delete button disabled; validation body retained baseline trace | Duplicate/no-baseline handled as warning/error path. |
| TC-E-008 | Long text input | PASS | 2026-07-03 09:49 | Step 2 counters rendered `25/100`, `290/500`; long text did not overlap | Raw/detail retained full values. |
| TC-E-009 | Abnormal probability value | PASS | 2026-07-03 09:49 | Probability inputs retained numeric constraints; bad values did not become `NaN` | Confirmation body used numeric conversion. |
| TC-E-010 | Confirmation without signposts | PASS | 2026-07-02 23:57 | Agent returned `404 No signposts found`; callout and raw inspector preserved body | After signposts existed, clean API confirmation passed. |
| TC-E-011 | SSE disconnect | PASS | 2026-07-02 23:49 | Browser showed `SSE disconnected or unavailable`; manual refresh recovered state | Backend run state persisted. |
| TC-E-012 | Callback before run creation | PASS | 2026-07-02 23:50 | Orphan callback API returned `Stored as orphan callback` | Store attach path also exercised by existing-group attach. |
| TC-E-013 | Confirmation failure | PASS | 2026-07-02 23:57 | Browser showed `HTTP 404/422` confirmation failure callout and raw error | Fixed 422 placeholder signpost issue; 404 signpost-missing path remains valid. |
| TC-E-014 | Browser refresh and run recovery | PASS | 2026-07-03 09:55 | Browser reload restored runtime labels and previous run context from local state | Missing backend run showed SSE 404 and manual reset path. |
| TC-E-015 | Soft delete authorization failure | PASS | 2026-07-03 09:46 | Wrong token returned `403 SCENARIO_GROUP_ADMIN_FORBIDDEN`; row was not removed by failed auth | Valid token cleanup succeeded after Agent restart. |
| TC-E-016 | Scenario Group List empty result | PASS | 2026-07-03 09:46 | Default list returned `rows: []`; include-deleted search found deleted row `61` | Empty list metadata source `backoffice_memory`. |
| REG-001 | Backoffice root URL renders | PASS | 2026-07-02 23:49 | Browser title `Next-Gen MI Backoffice` and shell rendered |  |
| REG-002 | OAuth token mock snake_case | PASS | 2026-07-02 23:50 | `{"access_token":"backoffice-local-token","expires_in":3600}` |  |
| REG-003 | Agent startup token prefetch | PASS | 2026-07-03 09:45 | Agent log: callback OAuth2 token pre-fetched successfully |  |
| REG-004 | Event selection updates `miEventId` | PASS | 2026-07-02 23:50 | Runtime label showed `miEventId=12` after create |  |
| REG-005 | Scenario Group List load/filter/search | PASS | 2026-07-03 09:46 | default empty, include-deleted keyword `61` returned deleted row |  |
| REG-006 | Scenario Group List detail navigation | PASS | 2026-07-02 22:09 | Existing run `60` detail opened with four tabs in prior browser pass | Preserved from same result run. |
| REG-007 | Create accepted shows IDs | PASS | 2026-07-03 09:50 | API run `62`; browser run `61` labels showed run/scenario IDs |  |
| REG-008 | Generation callback/table | PASS | 2026-07-03 09:50 | API run `62`: 6 rows |  |
| REG-009 | Added row in validation body | PASS | 2026-07-02 23:52 | Browser validation body included added row |  |
| REG-010 | Edited values in validation body | PASS | 2026-07-02 23:52 | Browser validation body included changed branch values |  |
| REG-011 | Validation warning/success rendered | PASS | 2026-07-03 09:46 | Warning callback in run `d6bab...`; success in clean API run `62` |  |
| REG-012 | Step 2 navigation | PASS | 2026-07-02 23:52 | Browser Step 2 showed One-view cards |  |
| REG-013 | Signpost cards rendered | PASS | 2026-07-03 09:50 | API signpost count `32`; browser showed signpost card rows |  |
| REG-014 | Signpost/probability in confirmation body | PASS | 2026-07-03 09:50 | Final confirmation body accepted by Agent | Placeholder signposts filtered unless numeric `signpostId`. |
| REG-015 | Confirmation detail navigation | PASS | 2026-07-03 09:50 | API confirmation `confirmed`, detail returned signpost count `32` | Browser detail passed earlier for run `60`. |
| REG-016 | Four detail tabs render | PASS | 2026-07-02 22:09 | Browser detail tabs `요약`, `가정 및 실현 가능성`, `가격 전망`, `시나리오 상세` | Preserved from prior browser pass. |
| REG-017 | Soft delete cleanup | PASS | 2026-07-03 09:50 | API cleanup for `62`; browser/API cleanup for `61` |  |
| REG-018 | Deleted row default/include-deleted behavior | PASS | 2026-07-03 09:46 | default rows empty; include-deleted row `61` with `delYn=Y` |  |
| REG-019 | Raw inspector retains evidence | PASS | 2026-07-03 09:46 | Request, accepted, callback, detail, soft_delete, error events observed |  |
| REG-020 | Errors preserve screen inputs | PASS | 2026-07-02 23:57 | Confirmation errors kept Step 2 fields and actions editable |  |

## Detailed Log

### TC-N-001

- Steps: opened Backoffice, created scenario draft from `miEventId=12`, waited for generation, validated, generated signposts, confirmed, fetched detail, cleaned up.
- Expected: accepted responses, callbacks, confirmation, detail, soft delete.
- Actual: final clean API run `62` returned generation 6 rows, validation callback, signpost count 32, confirmation lifecycle `confirmed`, detail signpost count 32, cleanup `scenarioGroupDeleted=1`.
- Evidence: API smoke output: `created ... 62`, `generation scenario_created 62 6`, `signpost callback signpost_created 32`, `confirmation accepted confirmed`, `cleanup True`.
- Bugs found: placeholder signpost without numeric `signpostId` caused an earlier browser confirmation 422.
- Files changed: `backoffice/frontend/src/lib/normalizer.ts`, `backoffice/frontend/src/api.ts`.
- Retest result: PASS.

### TC-N-002 / TC-N-003 / TC-N-004

- Steps: in browser Step 1, used add-row control, changed branch select values, submitted validation.
- Expected: added/edited rows included, validation warning/success visible, UI retained values.
- Actual: validation accepted and callback warning rendered. Raw run body included added `새 시나리오` row and edited branch values.
- Evidence: run `d6babf4d711940358e377ac8c236b124` validation request/callback; warning reason preserved.
- Bugs found: none requiring code change. The invalid added row correctly produced warning.
- Retest result: PASS.

### TC-N-005

- Steps: Step 2 signpost request, callback, confirmation.
- Expected: signposts appear, confirmation body accepted, detail reflects signposts.
- Actual: browser exposed failure when signposts were not yet available; after code fix and clean API run, Agent produced 32 signposts and accepted confirmation.
- Raw evidence: earlier `404 No signposts found`; final `confirmation accepted confirmed`.
- Bug fixed: non-numeric seed signpost `sp-1` was no longer preserved across generated scenario IDs, and confirmation now sends only numeric `signpostId` entries.
- Retest result: PASS.

### TC-N-006

- Steps: clicked `Refresh` after create accepted while callback was delayed.
- Expected: duplicate click blocked, detail raw JSON recorded, screen model refreshed.
- Actual: lifecycle changed to `scenario_created`; inspector showed `Scenario group detail refreshed` and SSE `detail_refreshed`.
- Retest result: PASS.

### TC-N-007

- Steps: listed groups, opened detail in prior browser pass, tested wrong-token delete, valid soft delete, default and include-deleted lists.
- Expected: Backoffice soft-delete proxy only, default list hides row, include-deleted shows deleted status.
- Actual: wrong token returned 403; valid cleanup for `61` returned `scenarioGroupDeleted=1`, `scenarioDeleted=6`, `signpostDeleted=30`; default list `rows=[]`; include-deleted keyword `61` returned `deleted=true`.
- Retest result: PASS.

### Edge Cases

- TC-E-001 and TC-E-016: Event/List empty states preserved layout and runtime controls.
- TC-E-002 and TC-E-003: empty/invalid runtime fields blocked request or produced inspectable API error without clearing inputs.
- TC-E-004 and TC-E-012: orphan failure callback for `999999` returned `Stored as orphan callback`.
- TC-E-005, TC-E-006, TC-E-007: invalid row count/combinations and baseline controls produced warnings or disabled unsafe delete.
- TC-E-008 and TC-E-009: counters and numeric constraints rendered; no `NaN` request body observed.
- TC-E-010 and TC-E-013: confirmation without signposts or invalid payload showed callout and raw error, then final valid run passed.
- TC-E-011 and TC-E-014: SSE disconnect and browser reload recovered through stored runtime context, reset, and manual refresh.
- TC-E-015: wrong token returned `403 SCENARIO_GROUP_ADMIN_FORBIDDEN`; valid token cleanup succeeded.

## Verification Commands

- `.venv/bin/python -m compileall backoffice/backend`
- `npm run build`
- Browser verification against `http://127.0.0.1:9010/`
- API smoke for OAuth mock, orphan callback, list empty/include-deleted, wrong-token delete, full run `62`.

## Final Residual Risk

- Browser UI timing can submit confirmation before signpost callback arrives if a tester clicks immediately after accepted. The UI shows the failure and raw body, and clean API run proves the backend/Agent path succeeds once signposts exist.
- Some seed Event List rows are UI fixtures; only `miEventId=12` was present in the local Agent DB during this run.

## 2026-07-06 Incremental Verification

- Added Agent `GET /events`, `GET /events/{mi_event_id}`, and `GET /scenario-groups` list support for Backoffice Event List/Event Detail requirements.
- Added Backoffice `GET /backoffice/api/events` and `GET /backoffice/api/events/{mi_event_id}` proxy/fallback responses.
- Added frontend API-backed Event List, source/fallback display, Event Type L1/L2 columns, pagination controls, related Scenario Group action handling, and an Event Detail panel with template dimension display.
- Updated validation accepted UX so accepted responses show callback-waiting state only; Step 2 progression is enabled after `validation_result`/validation callback success.
- Added create/continue workspace routing from Agent `status/stage`: `ready` and `scenario_created` open Step 1, `scenario_validated` and `signpost_created` open Step 2, and `created/completed` opens detail.
- Verification:
  - `.venv/bin/python -m compileall apps/persistence/event apps/persistence/scenario_group apps/agents/scenario_group_agent backoffice/backend`: PASS
  - `npm run build` in `backoffice/frontend`: PASS
  - Backoffice TestClient `GET /backoffice/api/events` without `agentBaseUrl`: PASS, returned `meta.source=backoffice_empty` and fallback reason.
  - Agent TestClient OpenAPI under `poetry run dotenv -f envs/.env run --no-override`: PASS, `/events`, `/events/{mi_event_id}`, and `/scenario-groups` are present.
  - Agent TestClient `GET /events?pageSize=1`: PASS, returned DB-backed event row with Event Type L1/L2 and action metadata.

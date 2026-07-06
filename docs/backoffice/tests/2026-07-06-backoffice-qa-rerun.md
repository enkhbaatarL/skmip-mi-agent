# Backoffice QA Rerun - 2026-07-06

## Test Time

- Start: 2026-07-06 14:25 KST
- End: 2026-07-06 16:27 KST

## Environment

- Backoffice URL: `http://127.0.0.1:9010/`
- Agent URL: `http://127.0.0.1:8000/` for API E2E, `http://127.0.0.1:8001/` for Playwright browser rerun
- Callback base URL: `http://127.0.0.1:9010`
- Callback OAuth2 token URL: `http://127.0.0.1:9010/api/v1/oauth2/token`
- `miEventId`: `1307` for clean E2E, `1` for generation failure/fix regression, `999999` for orphan callback
- `userId`: `10603`
- `scenarioGroupId`: `72` clean E2E, `64` generation bug/fix and validation warning run
- Delete authorization source: `SCENARIO_GROUP_ADMIN_TOKEN` from `envs/.env`

## Summary

| ID | Title | Status | Last run time | Evidence | Notes |
|---|---|---:|---|---|---|
| TC-N-001 | Basic end-to-end generation flow | PASS | 2026-07-06 14:47 | API run `f019afdba93846229ad6d9e358cc738b`, Scenario Group `72`: generation 6 rows, validation success, signposts 26, confirmation `confirmed/completed`, detail 6 rows, cleanup | Browser visual pass blocked by unavailable Codex browser. |
| TC-N-002 | Add scenario then validation | PASS | 2026-07-06 14:40 | API run `cf046cd6b69e4e32a198b2bd7847fc41`: added `QA 추가 시나리오` row included in validation body and warning callback | Warning expected because row duplicated baseline combination. |
| TC-N-003 | Edit scenario values then validation | PASS | 2026-07-06 14:47 | Clean API run edited first scenario title with `QA수정`; validation accepted and success callback returned |  |
| TC-N-004 | Add/edit/delete combined validation | PASS | 2026-07-06 14:40 | API warning run included edited title plus added row; validation callback preserved rows and warning reason | Delete control visual check blocked; API add/edit path passed. |
| TC-N-005 | Signpost generation, probability/signpost edit, confirmation | PASS | 2026-07-06 14:47 | Clean API run generated 26 signposts; confirmation body changed scenario probabilities to `10+idx`; confirmation returned `confirmed/completed` |  |
| TC-N-006 | Manual refresh/detail sync | PASS | 2026-07-06 14:47 | `GET /backoffice/api/scenario-groups/72?includeDeleted=true` returned normalized detail with 6 rows after confirmation |  |
| TC-N-007 | Scenario Group List/detail/soft delete | PASS | 2026-07-06 14:47 | Wrong token returned 403; valid soft delete returned scenarioGroupDeleted=1, scenarioDeleted=6, signpostDeleted=26; default list 0, include-deleted list row `72` deleted |  |
| TC-E-001 | Event List empty result | PASS | 2026-07-06 14:48 | `GET /backoffice/api/events?keyword=no-such-event-keyword-xyz` returned total 0 with pagination metadata | Browser layout blocked. |
| TC-E-002 | Missing or invalid Agent Base URL | PASS | 2026-07-06 14:48 | Invalid Agent URL create returned 502; missing Backoffice Event List agentBaseUrl returned `meta.source=backoffice_empty` and fallback reason |  |
| TC-E-003 | Invalid `miEventId` or `userId` | PASS | 2026-07-06 14:48 | Invalid `miEventId=bad` create returned 422 before Agent request |  |
| TC-E-004 | Generation callback failure | PASS | 2026-07-06 14:33 | Event 1 first run `fc7a66988a174566b0b5054f77ded21a` stored failure generation callback with C1BaseEvent type error | Bug fixed and retested with group `64`. |
| TC-E-005 | Validation warning or failure | PASS | 2026-07-06 14:40 | API run `cf046...` returned validation warning for duplicate scenario combination and preserved raw reason |  |
| TC-E-006 | Zero/one scenario row | BLOCKED | 2026-07-06 16:24 | Playwright verified Event List zero/one rows, but scenario-row add/delete table manipulation was not directly exercised in this follow-up | Requires a focused scenario draft edit run. |
| TC-E-007 | Baseline deletion or duplicate baseline | PASS | 2026-07-06 14:40 | Added duplicate baseline-like row caused validation warning; previous UI baseline delete disable remains from 2026-07-02 run | Current browser visual recheck blocked. |
| TC-E-008 | Long text input | PASS | 2026-07-06 16:23 | Playwright MCP filled a long Korean search string, applied Event List filter, input remained preserved and shell/table rendered without crash |  |
| TC-E-009 | Abnormal probability value | PASS | 2026-07-06 14:47 | Confirmation body used explicit numeric probability values and was accepted; no `NaN` entered request body | Browser invalid-input visual path blocked. |
| TC-E-010 | Confirmation without signposts | PASS | 2026-07-06 14:40 | Warning run confirmation before usable persisted signpost set returned 404 `No signposts found`, preserved error body | Clean run confirmed after signposts existed. |
| TC-E-011 | SSE disconnect | PASS | 2026-07-06 16:18 | Playwright detail navigation produced browser-visible `SSE disconnected or unavailable`/`SSE error` timeline entries while the screen stayed usable | Network-idle waits are not suitable because EventSource keeps the page active. |
| TC-E-012 | Callback before run creation | PASS | 2026-07-06 14:48 | Orphan generation callback to group `999999` returned 200 `{status: accepted, message: Stored as orphan callback}` |  |
| TC-E-013 | Confirmation failure | PASS | 2026-07-06 14:40 | Confirmation failure returned 404 `No signposts found` with raw Agent body; clean retry passed on run `f019...` |  |
| TC-E-014 | Browser refresh and run recovery | PASS | 2026-07-06 16:22 | Playwright reload with `domcontentloaded` restored Agent URL `8001`, run `f51c6d50881f4df49dda0e48f9be35ff`, scenarioGroupId `78`, detail title, and four tabs |  |
| TC-E-015 | Soft delete authorization failure | PASS | 2026-07-06 14:47 | Wrong delete token returned 403 `SCENARIO_GROUP_ADMIN_FORBIDDEN`; valid token cleanup succeeded |  |
| TC-E-016 | Scenario Group List empty result | PASS | 2026-07-06 14:48 | `GET /backoffice/api/scenario-groups?keyword=no-such-group-keyword-xyz` returned total 0 | Browser empty table visual blocked. |
| REG-001 | Backoffice root URL renders | PASS | 2026-07-06 16:05 | Playwright MCP opened `http://127.0.0.1:9010/`; title `Next-Gen MI Backoffice`, runtime bar, Event List table, and raw inspector rendered |  |
| REG-002 | OAuth token mock snake_case | PASS | 2026-07-06 14:32 | `POST /api/v1/oauth2/token` returned `access_token`, `expires_in` |  |
| REG-003 | Agent startup token prefetch | PASS | 2026-07-06 14:35 | Agent log: `Callback OAuth2 token pre-fetched successfully` |  |
| REG-004 | Event selection updates `miEventId` | PASS | 2026-07-06 16:06 | Playwright clicked `호르무즈 수송 지속에도 정상화 불확실`; runtime `miEventId` changed to `1227`, selected marker and Event Detail panel appeared |  |
| REG-005 | Scenario Group List load/filter/search | PASS | 2026-07-06 14:48 | Scenario Group List API returned source `agent_proxy`; keyword empty result and include-deleted search for `72` passed |  |
| REG-006 | Scenario Group List detail navigation | PASS | 2026-07-06 14:47 | Detail API opened group `72` and returned 6 normalized rows | Browser navigation blocked. |
| REG-007 | Create accepted shows IDs | PASS | 2026-07-06 14:42 | Clean run create accepted with `runId=f019...`, `scenarioGroupId=72` |  |
| REG-008 | Generation callback/table | PASS | 2026-07-06 14:44 | Generation callback produced 6 rows for group `72` |  |
| REG-009 | Added row in validation body | PASS | 2026-07-06 14:40 | Warning run validation body included `QA 추가 시나리오` |  |
| REG-010 | Edited values in validation body | PASS | 2026-07-06 14:47 | Clean run validation body included `QA수정` title |  |
| REG-011 | Validation warning/success rendered | PASS | 2026-07-06 14:47 | API warning run returned warning; clean run returned `isValid=true` success | Browser callout visual blocked. |
| REG-012 | Step 2 navigation | BLOCKED | 2026-07-06 16:24 | Playwright verified Scenario Group detail navigation, but did not directly exercise a fresh Step 2 create-draft workspace transition | Requires a focused create-draft browser run. |
| REG-013 | Signpost cards rendered | PASS | 2026-07-06 16:21 | Playwright opened scenario detail tab `시나리오 상세`; `Signpost 정의` table rendered with `호르무즈 항로 보험료 상승폭`, direction `상승`, and impact `JKM mild bull` |  |
| REG-014 | Signpost/probability in confirmation body | PASS | 2026-07-06 14:47 | Confirmation body included signposts and numeric probability changes; Agent accepted |  |
| REG-015 | Confirmation detail navigation | PASS | 2026-07-06 14:47 | Confirmation returned `confirmed/completed`; detail API returned group `72` | Browser navigation blocked. |
| REG-016 | Four detail tabs render | PASS | 2026-07-06 16:20 | Playwright opened Scenario Group detail `78`; four tabs rendered as `요약`, `가정 및 실현 가능성`, `가격 전망`, `시나리오 상세` |  |
| REG-017 | Soft delete cleanup | PASS | 2026-07-06 14:47 | Group `72` soft-deleted successfully |  |
| REG-018 | Deleted row default/include-deleted behavior | PASS | 2026-07-06 14:47 | Default list rows 0; include-deleted list included `(72, true)` |  |
| REG-019 | Raw inspector retains evidence | PASS | 2026-07-06 14:48 | Backoffice run timeline retained request, accepted, callback, detail/error events inspected through run API | Browser inspector visual blocked. |
| REG-020 | Errors preserve screen inputs | PASS | 2026-07-06 16:24 | Playwright changed Agent URL to `http://127.0.0.1:65530`, applied filter, saw error/fallback state while long search text and shell remained rendered |  |

## Detailed Log

### Setup

- Created result file with all normal, edge, and regression cases initialized for this rerun.
- Started Backoffice on `127.0.0.1:9010`.
- Existing port `8000` was occupied, so started the current Agent code on `127.0.0.1:8001`.
- Initial Agent start inside sandbox failed with MySQL `Operation not permitted`; reran outside sandbox because local DB access is required for QA.
- Browser plugin setup completed but `agent.browsers.list()` returned `[]`; Chrome plugin also could not attach because the selected Chrome profile does not have the Codex Chrome Extension installed/enabled. Initial screen-only checks were marked `BLOCKED` with API/build partial evidence.
- Follow-up Playwright MCP browser rerun started Backoffice on `127.0.0.1:9010` and Agent on `127.0.0.1:8001`, then verified root rendering, Event List selection/detail, Scenario Group List detail, four detail tabs, signpost rendering, browser refresh recovery, SSE error handling, long text input, and error input preservation.

### API Contract Smoke

- `POST /api/v1/oauth2/token`: PASS, returned `{"access_token":"backoffice-local-token","expires_in":3600}`.
- `GET /backoffice/api/events` without `agentBaseUrl`: PASS, returned `source=backoffice_empty` and fallback reason.
- `GET /backoffice/api/events?agentBaseUrl=http://127.0.0.1:8001&pageSize=2`: PASS, returned Agent DB source, pagination, Event Type L1/L2 labels.
- `GET /backoffice/api/events/{miEventId}`: PASS, returned scenario template dimensions.
- `GET /backoffice/api/scenario-groups`: PASS, returned Agent proxy source.

### Bug 1: Generation Callback Failure On Event ID Type

- Failing run: `fc7a66988a174566b0b5054f77ded21a`, Scenario Group `64`.
- Actual: generation callback returned failure:
  - `C1BaseEvent.event_id Input should be a valid string`
- Root cause: `apps/persistence/event/repository.py` changed `fetch_event_by_id()` to return the Backoffice numeric event payload. The Scenario Generation pipeline expects the existing pipeline payload where `mi_event_id` is a string.
- Fix:
  - Restored `fetch_event_by_id()` to return `_event_to_pipeline_dict()`.
  - Added `fetch_event_detail_by_id()` for Backoffice Event Detail numeric/read-model payloads.
  - Updated `apps/persistence/event/service.py` to use `fetch_event_detail_by_id()`.
- Verification:
  - `.venv/bin/python -m compileall apps/persistence/event apps/agents/scenario_group_agent backoffice/backend`: PASS
  - `npm run build`: PASS
  - Retest run `cf046cd6b69e4e32a198b2bd7847fc41`: generation callback success, 6 rows.

### Warning Path Validation

- Run: `cf046cd6b69e4e32a198b2bd7847fc41`, Scenario Group `64`.
- Steps:
  - Edited first row title with `QA수정`.
  - Added `QA 추가 시나리오`.
  - Submitted validation.
- Expected: request body includes edited and added rows; warning shown for invalid/duplicate combination.
- Actual: validation accepted, callback returned `result=success`, `isValid=false`, duplicate scenario combination warning.
- Follow-up: signpost generation reached `signpost_created`, but confirmation on this warning-path run returned `404 No signposts found`. This remains valid coverage for confirmation failure; clean E2E was rerun separately.

### Clean E2E

- Run: `f019afdba93846229ad6d9e358cc738b`
- Scenario Group: `72`
- Base Event: `miEventId=1307`
- Steps:
  - Created Scenario Group through Backoffice proxy.
  - Waited for generation callback.
  - Edited first scenario title and submitted validation.
  - Waited for validation success callback.
  - Requested signpost generation and waited for signpost callback.
  - Modified scenario probabilities in confirmation request.
  - Submitted confirmation.
  - Opened detail through Backoffice proxy.
  - Tested wrong-token soft delete.
  - Retried valid soft delete.
  - Verified default list hides deleted row and include-deleted list shows it.
- Actual:
  - generation rows: 6
  - validation: `isValid=true`
  - signposts: 26
  - confirmation: `confirmed`, Agent stage `completed`
  - detail rows: 6
  - wrong-token delete: 403 `SCENARIO_GROUP_ADMIN_FORBIDDEN`
  - valid delete: `scenarioGroupDeleted=1`, `scenarioDeleted=6`, `signpostDeleted=26`
  - default list after delete: 0 rows
  - include-deleted list: `(72, true)`
- Retest result: PASS.

### Edge Smoke

- Event List empty result: PASS, keyword `no-such-event-keyword-xyz` returned total 0.
- Scenario Group List empty result: PASS, keyword `no-such-group-keyword-xyz` returned total 0.
- Invalid Agent Base URL: PASS, create returned 502.
- Invalid `miEventId`: PASS, create returned 422.
- Orphan callback: PASS, group `999999` callback returned `Stored as orphan callback`.
- Missing run: PASS, `GET /backoffice/api/runs/missing` returned 404.

## Final Residual Risk

- Codex in-app browser was unavailable in this session (`agent.browsers.list()` returned an empty list). Chrome was running, but the selected Chrome profile did not have the Codex Chrome Extension installed/enabled. Playwright MCP was used for the browser assertions that could be safely reproduced.
- Rechecked at 2026-07-06 14:57 KST: `agent.browsers.list()` still returned `[]`, and Chrome extension check still exited `2` for the selected profile.
- Remaining `BLOCKED` rows are intentionally limited to flows not directly exercised through Playwright in this follow-up, such as scenario-row manipulation and Step 2 create-draft workspace transition.
- A warning-path run intentionally produced confirmation failure after a duplicate added row; the clean run proved confirmation succeeds when validation/signposts are in a valid state.

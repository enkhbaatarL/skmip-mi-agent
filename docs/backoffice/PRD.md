# Backoffice PRD

## 1. Purpose

The Scenario Group Agent API is hard to test from a browser or Swagger alone because long-running operations return immediately and deliver final results through callbacks.

Backoffice is a local/internal test console that:

- Calls the Agent API from a screen.
- Receives Agent callbacks through a backend.
- Reflects callback results in the frontend in real time.
- Lets testers run the full scenario group workflow without manually coordinating API scripts and callback checks.

## 2. Goals

- Test scenario group generation, validation, signpost generation, and confirmation from one screen.
- Receive callback payloads in a Backoffice backend and push updates to the frontend.
- Show accepted responses, callback payloads, current detail state, and raw JSON for debugging.
- Keep all new code under `backoffice/`; do not add this test UI under `apps/`.
- Support local development and Docker Compose execution.
- Prefer one deployed Backoffice container where FastAPI serves the built React frontend.

## 3. Non-goals

- Do not build a production user-facing admin console.
- Do not change the Agent core API behavior.
- Do not add per-request dynamic callback URLs to Agent request bodies.
- Do not persist run state in a database for v1.
- Do not add authentication for v1 unless the deployment environment requires it later.

## 4. Users and Main Workflow

Primary users are developers and QA testers who need to manually verify Scenario Group Agent behavior.

1. The user opens the Backoffice console.
2. The user enters Agent Base URL, `miEventId`, and `userId`.
3. The user either starts from Event List to create a scenario group or opens Scenario Group List to inspect existing groups.
4. For creation, the user clicks create scenario group.
5. Backoffice backend calls Agent `POST /scenario-groups`.
6. The accepted response immediately appears on screen with `scenarioGroupId`, `status`, and `stage`.
7. Agent background work completes and posts a callback to Backoffice.
8. Backoffice stores the callback payload and pushes an event to the frontend.
9. The user reviews the generated table and runs validation, signpost generation, and confirmation in sequence.
10. From Scenario Group List, the user can open detail or soft delete a scenario group.

Secondary users are product owners and domain reviewers who need to review whether the generated scenario group matches the intended AI Market Insights workflow shown in the reference screenshots.

User roles:

- QA tester
  - Runs the end-to-end Agent workflow and verifies request, callback, status, and detail payloads.
  - Needs clear evidence of which request body was sent and which callback changed the UI.
- Developer
  - Debugs Agent API behavior, callback delivery, schema mismatches, and local Docker Compose wiring.
  - Needs raw JSON, timeline events, Agent errors, and manual refresh controls.
- PM/domain reviewer
  - Reviews whether generated scenario branch criteria, narratives, probabilities, and signposts are plausible in the `AI Market Insights > AI Forecast > Next-Gen MI` context.
  - Needs screenshot-like screens that make the business workflow recognizable without requiring Swagger or API scripts.

### 4.1 Reference User Scenarios

The UI screenshots in `local/images/ui` describe the target business workflow that Backoffice must support for local verification.

1. Event discovery
   - The user opens `AI Forecast > Next-Gen MI`.
   - The user reviews an Event List with tabs for `Event List` and `Scenario Group List`.
   - The user filters events by status (`전체`, `신규`, `갱신`), category, date range, sort order, recommended-only toggle, and event-name search.
   - Each event row shows event time, category, event title, market impact indicators for JKM/TTF/HH, and a scenario creation action.
2. Scenario design step 1: branch criteria review
   - The user enters `Scenario Design` from an event.
   - The screen shows a two-step progress header:
     - `1 시나리오 분기항목 및 분기기준 검토`
     - `2 시나리오 One-view 검토`
   - While the Agent result is loading, the page keeps the layout visible with skeleton rows and a centered loading state.
   - The user reviews the base event and edits a table of scenario branch rows.
   - The user can add, delete, reset, and edit scenario rows before validation.
   - The user clicks `변경사항 검토` to validate edited branch criteria.
   - If validation finds a weak or contradictory combination, the UI shows an orange warning area with reason and recommended fix direction, while allowing the user to continue reviewing or correct the data.
   - The user clicks `검토 완료` to proceed to step 2 when the branch criteria are acceptable.
3. Scenario design step 2: one-view review
   - The screen loads the one-view generated data after step 1 is complete.
   - The user edits scenario group name and scenario group description with visible character counters.
   - The user reviews scenario cards horizontally.
   - Each scenario card includes order, optional baseline badge (`BC`), title, narrative, branch criteria, probability, and major signposts.
   - The user can edit scenario narrative, probability, and signposts.
   - The user can reset individual generated sections or reset all local edits.
   - The user clicks `시나리오 그룹 생성` to confirm creation.
4. Scenario group detail review
   - After creation, the user lands on a Scenario Group detail page.
   - The page exposes tabs:
     - `요약`
     - `가정 및 실현 가능성`
     - `가격 전망`
     - `시나리오 상세`
   - The summary tab shows base event metadata, scenario group description, and a scenario assumption/probability table.
   - The scenario detail tab shows a left scenario list and a right detail panel for the selected scenario.
   - The selected scenario detail includes narrative, probability, major assumptions, and a Signpost definition table.

### 4.2 Product Scope for Backoffice v1

Backoffice v1 should implement a local/internal approximation of the screenshot workflow, not a production clone of `AI Market Insights`.

The product must prioritize:

- End-to-end Agent workflow execution.
- Accurate display and editing of Agent-generated scenario data.
- Clear status, callback, and raw-payload visibility for QA.
- A screen structure close enough to the screenshots for domain reviewers to validate generated outputs in context.

The product may simplify:

- Global navigation, account menu, notice/help links, and notification behavior.
- Production-grade list pagination, saved filters, and permissions.
- Advanced visual polish, as long as the workflow and data review affordances are present.

### 4.3 User Scenarios and Expected Outcomes

#### Scenario A: Generate a scenario group from an event

1. The user opens Backoffice and sees the `Event List` tab.
2. The user filters events or enters `miEventId` manually from the runtime QA bar.
3. The user clicks the scenario action on an event row.
4. If no scenario group exists for the event, Backoffice calls Agent `POST /scenario-groups` and creates a local `runId`.
5. If a scenario group already exists and its Agent `status` is `creating`, Backoffice attaches to the existing `scenarioGroupId` and continues from the Agent `stage`.
6. The UI moves to the matching Scenario Design step and shows a skeleton/loading state while waiting for callback or detail output.
7. When the generation callback or detail refresh arrives, the branch criteria table becomes editable.

Expected outcome:

- The user can identify the selected base event and the generated branch criteria.
- The accepted response, generation callback, and normalized UI model are visible in the QA inspector.
- Existing `creating` scenario groups are not treated as completed detail-only rows; the user can continue the creation workflow from the latest `stage`.

#### Scenario B: Review and validate branch criteria

1. The user edits scenario names and dynamic branch criterion fields.
2. The user adds or deletes scenario rows if needed.
3. The user clicks `변경사항 검토`.
4. Backoffice sends the edited table as the validation request body.
5. The screen keeps the table visible and shows a request overlay while validation is in progress.
6. The accepted response only moves the run to `validation_waiting_callback`; it does not show validation success by itself.
7. When the validation callback arrives, the warning or success result is shown below the table.

Expected outcome:

- Validation warnings identify the affected scenario, invalid combination, reason, and recommended fix direction.
- `검토 완료` is enabled only when the run is valid or the latest detail state is compatible with progression.
- Edited table data is not discarded by validation callbacks, failed callbacks, or delayed SSE.
- The UI shows the validation callback body result on screen instead of asking the tester to check the callback body manually.

#### Scenario C: Review one-view content and confirm

1. The user proceeds to Scenario Design step 2.
2. The user reviews and edits scenario group name, scenario group description, scenario narratives, scenario probabilities, and major signposts.
3. The user scrolls horizontally across scenario cards when all scenarios do not fit in the viewport.
4. The user clicks `시나리오 그룹 생성`.
5. Backoffice sends the edited one-view model for final confirmation.

Expected outcome:

- Character counters and limits are enforced before submit.
- Scenario order and baseline `BC` badge remain stable from step 1 to step 2 and detail.
- The confirmation result and submitted request body are inspectable.

#### Scenario D: Verify confirmed scenario group detail

1. After confirmation, the user lands on Scenario Group detail.
2. The user reviews the summary tab, assumptions/probability table, and per-scenario status dropdowns.
3. The user opens the `시나리오 상세` tab and selects scenarios from the left list.
4. The user verifies narrative, probability, major assumptions, and Signpost definition rows for each selected scenario.

Expected outcome:

- Detail data matches the latest Agent detail response or a clearly identified local normalized view.
- Missing optional Agent fields render as empty states instead of breaking the screen.
- Raw detail JSON remains available for fields not yet represented in the UI.

## 5. Functional Requirements

### 5.1 Backend

Use FastAPI for the Backoffice backend.

Agent API proxy endpoints:

- `GET /backoffice/api/events`
- `GET /backoffice/api/events/{mi_event_id}`
- `POST /backoffice/api/runs/scenario-groups`
- `GET /backoffice/api/scenario-groups`
- `GET /backoffice/api/scenario-groups/{scenario_group_id}`
- `DELETE /backoffice/api/scenario-groups/{scenario_group_id}`
- `POST /backoffice/api/runs/{run_id}/validation`
- `POST /backoffice/api/runs/{run_id}/signposts`
- `POST /backoffice/api/runs/{run_id}/confirmation`

Callback receiver endpoints must match the existing Agent callback path settings:

- `POST /api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/generation/callback`
- `POST /api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/validation/callback`
- `POST /api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/signposts/callback`

Local OAuth2 token mock:

- `POST /api/v1/oauth2/token`
- Return a payload compatible with the Agent callback client:

```json
{
  "access_token": "backoffice-local-token",
  "expires_in": 3600
}
```

Realtime update:

- `GET /backoffice/api/runs/{run_id}/events`
- Use Server-Sent Events.
- Event types:
  - `accepted`
  - `callback`
  - `detail_refreshed`
  - `error`

State:

- Keep v1 state in process memory.
- Map `run_id` to `scenario_group_id`.
- Keep the latest accepted response, callbacks, detail response, and errors per run.
- Optionally append callback events to JSONL under a local output path for debugging.

Backoffice-specific read models:

- Event list read model
  - Prefer Agent/API data when available; fallback fixture or empty data must expose clear `source` metadata.
  - Must expose the event fields needed by the first screenshot flow:
    - `miEventId`
    - event title
    - one-line summary
    - event time
    - `occurredAt`
    - latest and oldest related record first-created timestamps
    - category
    - Event Type L1 code and label
    - Event Type L2 code and label
    - updated/new status
    - recommended flag
    - `signalYn`, `signalConfidence`, and signal reason when available
    - `scenarioSuggestYn` and scenario suggest reason when available
    - tags
    - market impact summaries for `JKM`, `TTF`, and `HH`
    - scenario availability/action state
    - related scenario group summary when one exists:
      - `scenarioGroupId`
      - `status`
      - `stage`
      - deleted state
      - scenario count
      - signpost count
  - Must expose pagination metadata for `next` and `previous` button behavior.
- Event detail read model
  - Must expose the fields needed by the Event Detail screen:
    - event metadata and content from the Event list read model
    - detail analysis body
    - key bullets
    - source MI record IDs
    - Event Type L1 code and label
    - Event Type L2 code and label
    - scenario dimension template for the event's `eventTypeL2Id`
    - raw template JSON for QA
    - related scenario group summary and action state
- Scenario design read model
  - Must normalize Agent callback/detail payloads into a structure that supports both step 1 table editing and step 2 one-view cards.
  - Must keep the original raw payload separately from the normalized UI model.
- Scenario group list read model
  - Must expose rows for the Scenario Group List screen:
    - `scenarioGroupId`
    - scenario group title/name
    - base event title and `miEventId` when available
    - Agent `status` and `stage`
    - scenario count
    - signpost count
    - created/updated timestamp
    - deleted state (`delYn` or normalized boolean)
    - latest local `runId` when the group came from a Backoffice run
  - Default list excludes soft-deleted groups.
  - An explicit `includeDeleted=true` query shows soft-deleted groups for QA.
- Scenario group detail read model
  - Must expose the fields needed by the generated detail tabs:
    - base event metadata
    - scenario group title/name
    - scenario group description
    - scenario rows with branch criteria and probability
    - scenario narratives
    - signposts with label, direction, impact, and evidence fields when present

### 5.2 API, State, and Callback Requirements

Backend API responses must be stable enough for frontend and QA to test without knowing Agent internal schemas.

Backoffice API namespace:

- All Backoffice-owned QA APIs use `/backoffice/api/...`.
- Agent callback receiver endpoints intentionally keep the Agent-configured callback paths under `/api/v1/mi/next-gen/...`.
- Callback receiver endpoints must not require a browser session or frontend `runId`.

Backend proxy contract:

- `GET /backoffice/api/events`
  - Lists MI events for the Event List tab.
  - Query supports `agentBaseUrl`, keyword, new/updated status, event type filters, recommended-only, date range, sort, and paging fields.
  - Response includes normalized event rows, pagination metadata, row action state, and raw Agent/list source payload when available.
  - If the Agent does not provide an event list endpoint in the current environment, Backoffice may return fixture or empty rows, but the response must clearly identify the fallback source and limitation.
- `GET /backoffice/api/events/{mi_event_id}`
  - Returns the Event Detail read model for one event.
  - Response includes event information, Event Type L1/L2 labels, scenario dimension template, related scenario group summary, and raw source payloads.
- `POST /backoffice/api/runs/scenario-groups`
  - Request includes `agentBaseUrl`, `miEventId`, `userId`, and optional QA metadata.
  - Response includes a generated `runId`, local lifecycle state, Agent accepted response, and `scenarioGroupId` when present.
  - If the event already has a non-deleted scenario group with Agent `status=creating`, Backoffice attaches to that `scenarioGroupId` and continues from its current `stage` instead of treating the row as completed detail-only state.
- `GET /backoffice/api/scenario-groups`
  - Lists scenario groups for the Scenario Group List tab.
  - Query supports `agentBaseUrl`, `includeDeleted`, optional `miEventId`, optional keyword, optional status/stage filters, and optional paging fields.
  - Response includes normalized list rows plus raw Agent/list source payload when available.
  - If the Agent does not provide a persisted list endpoint in the current environment, Backoffice may combine known in-memory runs and fixture rows, but the response must clearly indicate the source and limitation.
- `GET /backoffice/api/runs/{run_id}`
  - Returns the full local run read model including lifecycle, normalized UI model, latest payloads, timeline, and errors.
- `GET /backoffice/api/scenario-groups/{scenario_group_id}`
  - Proxies Agent detail and updates the matching run when one exists.
- `DELETE /backoffice/api/scenario-groups/{scenario_group_id}`
  - Proxies Agent `DELETE /scenario-groups/{scenario_group_id}` for soft delete only.
  - Request includes `agentBaseUrl`, `userId`, and the delete authorization value required by the Agent.
  - Response includes delete counts returned by Agent, local list refresh metadata, and a timeline event.
  - Soft delete must not call the Agent hard-delete endpoint.
  - If the deleted group has a matching local run, Backoffice marks the run/detail/list row as deleted without removing raw history.
- `POST /backoffice/api/runs/{run_id}/validation`
  - Request body is built from the current step 1 branch criteria table.
  - Response stores the accepted response and moves the run to validation waiting state when Agent accepts.
- `POST /backoffice/api/runs/{run_id}/signposts`
  - Request body is built from validated scenario rows and current scenario card content.
  - Response stores the accepted response and moves the run to signpost waiting state when Agent accepts.
- `POST /backoffice/api/runs/{run_id}/confirmation`
  - Request body is built from edited one-view data.
  - Response stores the accepted response and moves the run to confirming/confirmed state based on Agent response and subsequent detail.

Normalized frontend model:

- `eventList`
  - Events with filterable fields, market impact indicators, Event Type labels, pagination metadata, related scenario group summaries, and action states.
- `eventDetail`
  - Selected event metadata, analysis, Event Type labels, scenario dimension template, related scenario group summary, and raw source payloads.
- `scenarioGroupList`
  - Scenario group rows, filters, paging metadata when available, list source, include-deleted state, and latest delete result.
- `branchCriteriaDraft`
  - Base event metadata, dynamic criterion definitions, rows, baseline row marker, row edit metadata, and validation result.
- `oneViewDraft`
  - Scenario group name, description, scenario cards, probabilities, branch summaries, signposts, section edit metadata, and character counts.
- `scenarioGroupDetail`
  - Detail tabs, summary data, assumptions/probability rows, scenario list, selected scenario detail, and raw detail reference.

Run lifecycle states:

- `idle`
- `creating`
- `generation_waiting_callback`
- `scenario_created`
- `validating`
- `validation_waiting_callback`
- `scenario_validated`
- `creating_signposts`
- `signpost_waiting_callback`
- `signpost_created`
- `confirming`
- `confirmed`
- `failed`

The lifecycle must separate request progress from callback progress:

- `creating` means Backoffice is calling Agent create API.
- `generation_waiting_callback` means Agent accepted create but generation callback/detail completion is not yet reflected.
- `validating` means Backoffice is calling Agent validation API.
- `validation_waiting_callback` means Agent accepted validation but callback/detail completion is not yet reflected.
- `creating_signposts` means Backoffice is calling Agent signpost API.
- `signpost_waiting_callback` means Agent accepted signpost generation but callback/detail completion is not yet reflected.
- `confirming` means Backoffice is calling final confirmation API.

UI step states must be derivable from lifecycle plus latest Agent `status`/`stage`; the UI must not infer success solely from an HTTP 202/accepted response.

Continue-generation mapping from Agent `status`/`stage`:

- `creating` + `ready`: generation has been accepted but scenario draft output is not reflected yet; open Scenario Design step 1 in loading state and wait for generation callback or detail refresh.
- `creating` + `scenario_created`: scenario draft exists; open Scenario Design step 1 with branch criteria editing.
- `creating` + `scenario_validated`: validation is complete; open Scenario Design step 2 and allow signpost generation/review.
- `creating` + `signpost_created`: signposts exist; open Scenario Design step 2 and allow confirmation.
- `created` + `completed`: confirmation is complete; open Scenario Group Detail.
- Validation failure keeps the group at `creating` + `scenario_created`; the UI stays on step 1 and displays the validation callback result for correction.

Each run must track step-level state separately from Agent `status` and `stage` so the UI can show local request progress even when the Agent detail endpoint has not yet refreshed.

Required run fields:

- `runId`
- `miEventId`
- `userId`
- `agentBaseUrl`
- `scenarioGroupId`
- local run lifecycle state
- latest Agent `status`
- latest Agent `stage`
- latest accepted response per action
- latest callback per callback type
- latest detail response
- normalized scenario design model
- timeline events
- errors

Callback handling:

- Generation callback populates step 1 branch criteria and, when available, scenario group summary fields.
- Validation callback records validation result, warning/recommendation messages, and whether the user can proceed to one-view review.
- Signpost callback populates signpost lists per scenario and updates signpost counts.
- Callback payloads must be displayed even when `result=failure`.
- Unknown callback fields must be preserved in raw JSON.
- Duplicate callbacks for the same scenario group and callback type must append timeline entries and replace the latest callback reference without corrupting the normalized draft.
- Callback payloads that arrive before a run is bound to `scenarioGroupId` must be stored as orphan callbacks and attached after the accepted create response is known.
- A callback with `result=failure` sets the local step to failed, preserves prior successful UI data, and keeps raw failure payload visible.
- Callback receiver responses must be fast and return 2xx after local persistence/pub-sub succeeds; expensive detail refreshes should happen asynchronously or from the frontend refresh path.
- Validation accepted responses must not render a success/warning validation result. The frontend should display callback waiting state until the validation callback or detail-compatible validation state arrives.

SSE events:

- `accepted`
- `callback`
- `detail_refreshed`
- `validation_result`
- `normalized_model_updated`
- `error`

Frontend request-body construction:

- Step 1 `변경사항 검토` uses the currently edited branch criteria table.
- Step 1 `검토 완료` advances only after successful validation or detail state compatible with `scenario_created`.
- Step 2 `시나리오 그룹 생성` / confirmation uses the edited scenario group name, description, narratives, probabilities, and signposts.
- Request body builders must keep raw JSON visible for QA before and after submit.
- Each generated request body must include enough identifiers to correlate Agent-side behavior:
  - `runId`
  - `scenarioGroupId`
  - `miEventId`
  - `userId`
  - scenario row identifiers when available
  - scenario order fallback when Agent identifiers are absent
- Request body preview must be available before submit for validation and confirmation.

### 5.3 Frontend

Use React + Vite.

The first screen is the actual test console and scenario workflow, not a landing page.

Required UI:

- Compact runtime controls for Agent Base URL, `miEventId`, `userId`, `runId`, and `scenarioGroupId`.
- Event List / Scenario Group List entry area.
- Event Detail screen with Event Type and template inspection.
- Scenario Group List table with search/filter controls, detail navigation, and soft-delete action.
- Scenario Design step 1 table editor.
- Scenario Design step 2 one-view card editor.
- Scenario Group detail page with tabs.
- Manual refresh button.
- Current `scenarioGroupId`, Agent `status`, Agent `stage`, and local run lifecycle state.
- Validation result display with warning/recommendation area.
- Signpost count and per-scenario signpost display.
- Confirmation result display.
- Timeline and raw JSON panels for accepted responses, callback payloads, detail responses, request bodies, and errors.

Frontend behavior:

- Load Event List from Backoffice event API when available and keep fallback source visible in QA inspector.
- Open Event Detail from an Event List row without losing runtime QA controls.
- Use Event List row action state to either create a new scenario group, attach to an existing `creating` group and continue, or open completed detail.
- Open an SSE connection after a run is created.
- Apply callback events to screen state without page refresh.
- Refresh Scenario Group List after creation confirmation, detail refresh, and successful soft delete.
- Require explicit confirmation before soft deleting a scenario group.
- Keep soft delete disabled while another delete request for the same row is in flight.
- Show soft delete success/failure in the row state, timeline, and raw JSON inspector.
- Build validation, signpost, and confirmation request bodies from the current table state.
- After validation accepted response, show `validation_waiting_callback` progress and wait for `validation_result`/callback before rendering validation outcome.
- Allow manual refresh when callback or SSE is delayed.
- Preserve enough local screen state to continue after a transient frontend reload when a `run_id` is known.
- Keep visible data on screen during loading overlays; do not blank the page when a request is pending.
- Mark edited fields at row/section level so reviewers can see what differs from Agent-generated data.
- Character limits from the screenshots must be enforced in UI:
  - scenario group name: 100 characters
  - scenario group description: 500 characters
  - scenario narrative: 500 characters
- Horizontal card areas must be scrollable when more scenarios exist than fit in the viewport.
- Long signpost labels and evidence text may truncate in cards but must be readable in detail/raw views.

### 5.4 Screen Requirements

#### 5.4.1 Event List

Purpose: select the source event for scenario generation.

Required elements:

- Top product context: `AI Market Insights`, active `AI Forecast` section, `Next-Gen MI` page title.
- Tabs:
  - `Event List`
  - `Scenario Group List`
- Filters:
  - status segmented control: `전체`, `신규`, `갱신`
  - category dropdown
  - date range selector
  - sort dropdown
  - recommended-only toggle
  - event-name search
- Table columns:
  - updated/new badge
  - date/time
  - category
  - Event Type L1 label
  - Event Type L2 label
  - event title
  - one-line summary
  - signal/recommended state
  - `JKM`
  - `TTF`
  - `HH`
  - scenario action
- Event row behavior:
  - selecting a row highlights it and updates the runtime QA bar `miEventId`
  - clicking the event title or detail action opens Event Detail
  - clicking the scenario action starts a new run when no related scenario group exists
  - when a related scenario group exists and Agent `status=creating`, clicking `생성하기` attaches to that group and continues from the latest `stage`
  - when a related scenario group exists and Agent `status=created` with `stage=completed`, clicking `상세보기` opens Scenario Group Detail
  - when a run exists, the UI must ask the user to reset or continue before replacing local draft state
  - rows without scenario generation availability show a disabled action and reason tooltip or inline reason
- Event row scenario action labels:
  - no scenario group: `생성하기`
  - scenario group `creating` + `ready`: `생성하기`, opens step 1 loading/waiting state
  - scenario group `creating` + `scenario_created`: `생성하기`, opens step 1 review
  - scenario group `creating` + `scenario_validated`: `생성하기`, opens step 2 review/signpost flow
  - scenario group `creating` + `signpost_created`: `생성하기`, opens step 2 confirmation-ready flow
  - scenario group `created` + `completed`: `상세보기`
- Market impact indicators should preserve the screenshot semantics:
  - market label badge such as `S` or `L`
  - red/green/gray directional bars
  - compact row density for scanning many events
- Empty state:
  - if no event fixture/API data exists, keep manual `miEventId` input visible and show an empty event table message.
- Pagination:
  - show `Previous` and `Next` buttons below the Event List table.
  - disable `Previous` on the first page and disable `Next` when no next page exists.
  - keep filters and selected row stable while moving between pages.
- Backoffice QA overlay:
  - runtime controls and raw JSON inspector may be present, but must not replace the Event List as the first meaningful screen.

#### 5.4.1.1 Event Detail

Purpose: inspect the source event and template before or during scenario generation.

Required elements:

- Same `Next-Gen MI` page context and tabs as Event List.
- Back action to Event List preserving filters and selected `miEventId`.
- Event metadata section:
  - `miEventId`
  - event title
  - one-line summary
  - occurred time and related record time range
  - new/updated badge
  - signal/recommended state and reasons
  - tags
- Event Type section:
  - Event Type L1 ID/code/label
  - Event Type L2 ID/code/label
- Event content section:
  - key bullets
  - detail analysis
  - source MI record IDs
- Scenario template section:
  - dimension key
  - dimension label
  - required state
  - enum values
  - raw template JSON in QA inspector
- Related Scenario Group section:
  - no group: `생성하기`
  - `status=creating`: `생성하기` and continue from current `stage`
  - `status=created` + `stage=completed`: `상세보기`
  - show `scenarioGroupId`, `status`, `stage`, scenario count, signpost count, and deleted state when available.

#### 5.4.1.2 Scenario Group List

Purpose: find existing scenario groups, open detail, and remove local test data with soft delete.

Required elements:

- Same `Next-Gen MI` page context and tabs as Event List.
- `Scenario Group List` tab active state.
- Filters:
  - keyword search across scenario group name, event title, and IDs
  - status dropdown
  - stage dropdown
  - date range selector
  - sort dropdown
  - include-deleted toggle, default off
- Table columns:
  - scenario group ID
  - scenario group name
  - base event title or `miEventId`
  - status
  - stage
  - scenario count
  - signpost count
  - updated time
  - deleted state
  - row actions
- Row actions:
  - detail action opens Scenario Group detail using `GET /backoffice/api/scenario-groups/{scenario_group_id}`
  - delete action opens a confirmation dialog and then calls soft delete
- Delete behavior:
  - only soft delete is available from the Backoffice UI
  - the confirmation dialog shows scenario group ID/name, event reference, and a warning that generated snapshots are not hard deleted
  - after success, the row is removed from the default list or marked deleted when include-deleted is on
  - failed delete keeps the row visible and exposes the Agent error in QA inspector
- Empty state:
  - if no groups exist, show a message and an action to switch to Event List.
  - if filters hide all rows, show filter reset.

#### 5.4.2 Scenario Design Step 1

Purpose: review and validate scenario branch criteria before one-view generation.

Required elements:

- Back button.
- Two-step progress header with active/completed/loading states.
- Base Event panel showing event title, timestamp, and category.
- Branch criteria section titled `분기 항목 및 분기 기준 검토`.
- Scenario table with:
  - row delete action
  - scenario title/name input
  - baseline badge for the baseline scenario
  - dynamic branch criterion columns from Agent payload
  - dropdown-like controls for categorical criteria
  - row add action
- Table rules:
  - preserve Agent-provided criterion column order
  - support at least 3 scenarios and do not cap at 6 if Agent returns more
  - show the `3개 이상 구성 권장` guidance when fewer than 3 rows remain
  - maintain stable row keys across edit, validation, and callback refresh
  - deleting the baseline row is disabled unless a replacement baseline rule is added later; v1 should keep the Agent baseline row
  - added rows are marked as local-only until submitted
  - edited cells are visually distinguishable from Agent-generated values
- Footer actions:
  - `전체 초기화`
  - `취소`
  - `변경사항 검토`
  - `검토 완료`

Required states:

- Loading skeleton for initial scenario design load.
- Request overlay for `변경사항 검토`.
- Disabled action state while request is in flight.
- Warning result area when validation returns recommendations.
- Success-ready state where `검토 완료` becomes the primary enabled action.
- Failure state:
  - validation API failure shows the error in the QA inspector and keeps table edits intact.
  - validation callback `result=failure` shows failure summary below the table and in the timeline.

#### 5.4.3 Scenario Design Step 2

Purpose: review generated one-view content before final scenario group creation/confirmation.

Required elements:

- Completed state for step 1 and active state for step 2.
- Scenario group name textarea/input with `current / 100` counter.
- Scenario group description textarea with `current / 500` counter.
- Scenario cards shown in a horizontal review board.
- Each scenario card must show:
  - scenario order
  - baseline badge when applicable
  - scenario title
  - scenario narrative editable text area with counter
  - branch criteria summary cards
  - scenario probability input with `%`
  - major signposts list
  - edit action for signposts
  - reset/regenerate action per editable section when available
- Scenario card rules:
  - probability values are numeric percentages from 0 to 100
  - total probability warning is shown when the sum is not 100, but v1 may allow submit if Agent confirmation accepts the payload
  - signpost rows show label, direction, and impact/likelihood summary when present
  - long signpost labels truncate in cards and remain fully available in detail/raw JSON
  - per-section reset restores the latest Agent-generated value, not the initial empty value
  - `전체 초기화` restores all one-view fields to the latest Agent-generated values
- Footer actions:
  - `전체 초기화`
  - `취소`
  - `시나리오 그룹 생성`
- Loading state:
  - while one-view data is being loaded, show the step header and centered `데이터를 로드 중입니다` style loading state.
  - after data arrives, do not collapse the horizontal card board while signposts are still loading; show per-section pending state if needed.

#### 5.4.4 Scenario Group Detail

Purpose: verify the persisted/confirmed scenario group after generation.

Required elements:

- Back link to Scenario Group List.
- Scenario group title.
- Tabs:
  - `요약`
  - `가정 및 실현 가능성`
  - `가격 전망`
  - `시나리오 상세`
- Summary tab:
  - base event table with event title, event type/category, update timestamp
  - scenario group description
  - assumption/probability table with scenario, branch criteria, probability, and status dropdown
- Summary tab rules:
  - row order matches scenario order from design step 2
  - baseline scenario shows `BC`
  - status dropdown supports at least `대기`; additional statuses render if returned by Agent
  - scenario count and signpost count are shown when available
- Scenario detail tab:
  - left scenario list with selected state and baseline badge
  - selected scenario title and order
  - scenario narrative
  - scenario probability
  - major assumptions cards
  - Signpost definition table with label, direction, impact, and evidence/core basis
- Scenario detail tab rules:
  - selecting a left-list scenario updates the right detail without refetching unless data is missing
  - missing signpost data shows an empty Signpost state and a refresh affordance
  - signpost evidence/core basis supports multiline display and truncates only when a detail/raw view can reveal the full text
- `가정 및 실현 가능성` and `가격 전망` tabs:
  - must be present for navigation parity
  - may show empty or placeholder states in v1 if Agent payload does not provide enough data
  - must not block the summary or scenario detail tabs

### 5.5 Ops

Local development:

- Run backend and frontend as two processes for faster iteration.
- Backend: `uvicorn backoffice.backend.main:app --reload --port 9010`
- Frontend: Vite dev server.

Container/Compose:

- Build React frontend into static files.
- Run one FastAPI process in the Backoffice container.
- FastAPI serves both API endpoints and the React `dist` output.
- Browser connects to `http://localhost:9010`.
- Backoffice backend talks to Agent through the Compose service name.
- Agent sends callbacks to Backoffice through the Compose service name.

## 6. Proposed Directory Structure

```text
backoffice/
  backend/
    __init__.py
    main.py
    agent_client.py
    schemas.py
    store.py
  frontend/
    package.json
    vite.config.ts
    index.html
    src/
      App.tsx
      api.ts
      components/
  Dockerfile
  README.md
```

## 7. Backend Design Review

FastAPI is the right backend choice because the current project already uses FastAPI and the key backend responsibility is HTTP callback handling, API proxying, and SSE.

Backend responsibilities:

- Receive callback payloads from Agent.
- Normalize and store callback events by `scenario_group_id`.
- Publish callback events to the matching run's SSE subscribers.
- Proxy Agent API calls with `httpx.AsyncClient`.
- Surface Agent HTTP errors with status code, response body, and workflow step.
- Serve React static assets in container mode.

Important details:

- Use `run_id` for frontend session identity because `scenario_group_id` is only known after create acceptance.
- After create acceptance, bind `run_id` to `scenario_group_id`.
- If a callback arrives for an unknown `scenario_group_id`, store it in an orphan callback bucket so it can be attached if a matching run appears later.
- Keep the backend stateless with respect to Agent persistence. Agent remains source of truth for scenario details.
- Do not import from `apps/` internals. Treat Agent as an external HTTP service.

Failure handling:

- Agent proxy timeout should create an `error` event.
- Agent non-2xx response should be returned to frontend with body text.
- Callback payload with `result=failure` should be shown as a failed step, not hidden.
- SSE disconnect should not delete run state.

## 8. Frontend Design Review

React + Vite is preferred over FastAPI templates for this UI because the console needs interactive tables, step transitions, real-time callback updates, and raw JSON inspection.

Frontend responsibilities:

- Manage the workflow screen state.
- Render stage/status and current step.
- Render scenario table rows and signposts.
- Trigger backend proxy endpoints.
- Subscribe to SSE events.
- Display raw JSON for traceability.

UI layout:

- Top toolbar: Agent Base URL, `miEventId`, `userId`, run controls.
- Left/main area: scenario group summary and table.
- Right panel: step status, validation result, signpost summary.
- Bottom or side panel: raw JSON event log.

State rules:

- The backend run state is the source of truth for received callbacks.
- The current editable table in the frontend is used for validation, signpost, and confirmation requests.
- Manual refresh replaces detail-derived fields but should not unexpectedly discard unsent table edits without user action.

## 9. Screen Planning

### 9.1 Information Architecture

The app has one primary workflow with five screen states: Event List, Scenario Group List, Scenario Design Step 1, Scenario Design Step 2, and Scenario Group Detail.

```text
Runtime QA Bar
Workflow Status Strip
Event List Workspace
Scenario Group List Workspace
Scenario Design Workspace
  Step 1: Branch Criteria Review
  Step 2: One-view Review
Scenario Group Detail Workspace
QA Inspector
  Step Timeline
  Raw JSON Viewer
```

There is no separate landing page, dashboard, or marketing-style introduction. The production-style content area should resemble the reference screenshots, while Backoffice runtime controls and raw JSON can be shown as a compact QA panel.

### 9.2 Runtime QA Bar

Purpose: configure a test run, start the Agent workflow, and keep QA-only context visible without hiding the scenario review UI.

Fields:

- Agent Base URL
  - Default from `DEFAULT_AGENT_BASE_URL`.
  - Editable because testers may point to local, compose, or remote Agent.
- `miEventId`
  - Required number input.
- `userId`
  - Required number input.
- `runId`
  - Read-only after run creation.
- `scenarioGroupId`
  - Read-only after accepted response.

Actions:

- `Create Scenario Draft`
  - Enabled when Agent Base URL, `miEventId`, and `userId` are valid.
  - Disabled while create request is in flight.
- `Refresh`
  - Enabled after `scenarioGroupId` exists.
  - Calls detail proxy and updates visible detail state.
- `Reset`
  - Clears local screen state but does not delete Agent data.

### 9.3 Workflow Status Strip

Purpose: make long-running background status visible at a glance.

Steps:

- Select Event
- Create Scenario Draft
- Callback: Generation
- Review Branch Criteria
- Validate Branch Criteria
- Callback: Validation
- Review One-view
- Create Signposts
- Callback: Signposts
- Confirm Scenario Group

Each step has one of these states:

- `idle`
- `requesting`
- `accepted`
- `waiting_callback`
- `success`
- `failure`

The status strip shows:

- current Agent `status`
- current Agent `stage`
- latest callback time
- latest error summary, if any

### 9.4 Event List Workspace

Event List:

- Mirrors the screenshot entry point for `AI Forecast > Next-Gen MI`.
- Supports status filters, category, date range, sort, recommended-only toggle, and event-name search.
- Shows event time, category, event title, JKM/TTF/HH indicators, and scenario action.
- Clicking a scenario action sets `miEventId` and starts or resumes the Scenario Design workflow.

### 9.5 Scenario Group List Workspace

Scenario Group List:

- Lists scenario groups from the Backoffice list API.
- Supports keyword, status, stage, date range, sort, and include-deleted filters.
- Shows scenario group ID/name, base event reference, status/stage, scenario/signpost counts, updated time, and deleted state.
- Clicking a row or detail action opens Scenario Group Detail.
- Delete action performs soft delete only after confirmation.
- Successful delete updates the list immediately and records the raw delete response in QA Inspector.
- The screen must distinguish the list source:
  - Agent-backed persisted list
  - Backoffice in-memory run list
  - fixture/demo list

### 9.6 Scenario Design Workspace

Step 1 Branch Criteria Review:

- Base Event panel shows event title, timestamp, and category.
- Headers come from Agent callback/detail branch criteria.
- Rows are editable and include delete, add, baseline badge, scenario name, and dynamic criterion fields.
- `변경사항 검토` submits the edited table for validation.
- Validation warnings appear below the table with incompatible scenario, reason, and recommended fix direction.
- `검토 완료` advances to one-view review after successful validation or compatible detail state.

Step 2 One-view Review:

- Scenario group name and description are editable and show character counters.
- Scenario cards are horizontally scrollable.
- Each card shows scenario order, baseline badge, title, narrative, branch criteria, probability, and major signposts.
- Per-section reset controls restore the latest Agent-generated value.
- `시나리오 그룹 생성` submits edited one-view data for final scenario group creation/confirmation.

### 9.7 Scenario Group Detail Workspace

Scenario Group Summary:

- title
- summary
- description
- `miEventId`
- `eventTypeL2Id`
- scenario count
- signpost count
- status/stage

Summary Tab:

- base event metadata table
- scenario group description
- scenario assumption/probability table
- per-scenario status dropdown

Scenario Detail Tab:

- left scenario list with selected state and baseline badge
- selected scenario title, order, narrative, and probability
- major assumptions cards
- Signpost definition table with label, direction, impact, and core evidence

The `가정 및 실현 가능성` and `가격 전망` tabs must exist for IA parity. v1 may show empty or placeholder states if Agent payload support is incomplete.

### 9.8 QA Inspector

Step Timeline:

- Chronological list of accepted responses, callbacks, refreshes, and errors.
- Each item shows:
  - time
  - event type
  - workflow step
  - result
  - short reason or status

Raw JSON Viewer:

- Tabs:
  - Accepted
  - Callback
  - Detail
  - Request Body
  - Error
- JSON viewer is read-only.
- Latest event is selected automatically.
- User can select older timeline events to inspect their raw payload.

### 9.9 Button Enablement Rules

- `Create Scenario Draft`
  - enabled before a run exists.
- `변경사항 검토`
  - enabled after generation callback success or after detail refresh shows `stage=scenario_created`.
- `검토 완료`
  - enabled after successful validation or after a detail refresh confirms a compatible stage.
- `Create Signposts`
  - enabled after validation callback success with `isValid=true` or after detail refresh shows `stage=scenario_validated`.
  - allow a forced run only if the UI exposes an explicit "allow despite validation failure" checkbox later; omit this in v1.
- `시나리오 그룹 생성` / `Confirm`
  - enabled after signpost callback success or after detail refresh shows `stage=signpost_created`.
- `Refresh`
  - enabled after `scenarioGroupId` exists.
- `Delete Scenario Group`
  - enabled for non-deleted Scenario Group List rows when `scenarioGroupId`, `agentBaseUrl`, `userId`, and delete authorization input are available.
  - disabled for rows already marked deleted.
  - requires confirmation and only calls the soft-delete endpoint.
- All workflow action buttons are disabled while their own request is in flight.

### 9.10 Empty, Loading, and Error States

Empty:

- Show the runtime QA bar and Event List workspace.
- If no event data is available, show an empty table state with manual `miEventId` entry still available.

Loading:

- Keep existing data visible.
- Mark only the active step as requesting or waiting for callback.
- Use skeleton rows/cards for Agent-generated content loads.

Callback delayed:

- Show `waiting_callback`.
- Keep `Refresh` available.

Error:

- Show the failed step in the status strip.
- Show error details in the right inspector.
- Keep previous successful data visible.

### 9.11 Component Plan

React component boundaries:

- `App`
- `RunControlBar`
- `WorkflowStatusStrip`
- `EventList`
- `ScenarioGroupList`
- `ScenarioGroupDeleteDialog`
- `ScenarioDesignStepHeader`
- `BaseEventPanel`
- `BranchCriteriaTable`
- `ValidationPanel`
- `OneViewScenarioBoard`
- `ScenarioCard`
- `ScenarioGroupDetail`
- `ScenarioDetailPanel`
- `SignpostPanel`
- `Timeline`
- `JsonInspector`

Shared frontend modules:

- `api.ts`
  - backend proxy calls
  - SSE connection helper
- `types.ts`
  - run, event, scenario group list, table, callback payload types
- `tablePayload.ts`
  - request body builders for validation, signposts, and confirmation

## 10. Ops and Docker Compose Review

Backoffice should run as one container in Compose. The frontend/backend split is only for local development.

Compose services:

- `scenario-group-agent`
- `backoffice`

The Agent service must be configured so callbacks go to Backoffice:

- `callback_base_url` equivalent: `http://backoffice:9010`
- `callback_oauth2_token_url` equivalent: `http://backoffice:9010/api/v1/oauth2/token`
- `skip_callback`: `false`

Backoffice environment:

- `BACKOFFICE_HOST=0.0.0.0`
- `BACKOFFICE_PORT=9010`
- `DEFAULT_AGENT_BASE_URL=http://scenario-group-agent:8000`
- optional `BACKOFFICE_CALLBACK_LOG_PATH=/workdir/local/output/backoffice_callbacks.jsonl`

Docker image shape:

- Stage 1: Node image builds `backoffice/frontend`.
- Stage 2: Python runtime installs backend dependencies and copies frontend `dist`.
- Runtime command starts Uvicorn or Gunicorn/Uvicorn on port `9010`.

## 11. Docker Compose Draft

```yaml
version: "3.9"

services:
  scenario-group-agent:
    container_name: skmip-mi-agent
    build:
      context: ../..
      dockerfile: Dockerfile
    image: skmip-mi-agent:local
    ports:
      - "8000:8000"
    env_file:
      - ../../envs/.env
    environment:
      METADATA_DB_HOST: host.docker.internal
      APP_HOST: 0.0.0.0
      APP_PORT: 8000
      CALLBACK_BASE_URL: http://backoffice:9010
      CALLBACK_OAUTH2_TOKEN_URL: http://backoffice:9010/api/v1/oauth2/token
      SKIP_CALLBACK: "false"
    restart: unless-stopped

  backoffice:
    container_name: skmip-mi-agent-backoffice
    build:
      context: ../..
      dockerfile: backoffice/Dockerfile
    image: skmip-mi-agent-backoffice:local
    ports:
      - "9010:9010"
    environment:
      BACKOFFICE_HOST: 0.0.0.0
      BACKOFFICE_PORT: 9010
      DEFAULT_AGENT_BASE_URL: http://scenario-group-agent:8000
      BACKOFFICE_CALLBACK_LOG_PATH: /workdir/local/output/backoffice_callbacks.jsonl
    depends_on:
      - scenario-group-agent
    restart: unless-stopped
```

Note: the exact Agent environment variable names must match the config loader behavior. If the current config loader does not support overriding callback settings through environment variables, provide a Compose-specific config file mounted as `APP_CONFIG`.

## 12. Acceptance Criteria

### 12.1 Backend and Callback Acceptance

- Given Agent calls any configured callback receiver endpoint, Backoffice returns 2xx after storing the raw callback and appending a timeline event.
- Given Agent requests `/api/v1/oauth2/token`, Backoffice returns a callback-compatible token payload and the subsequent callback request can proceed locally.
- Given a run has an active SSE subscriber, accepted responses, callbacks, detail refreshes, validation results, normalized model updates, and errors are pushed without page refresh.
- Given Agent returns a non-2xx or timeout from a proxy request, Backoffice returns a structured error to the frontend and appends an `error` timeline event with step context and raw response body when available.
- Given a callback arrives before a run is bound to `scenarioGroupId`, Backoffice stores it as an orphan callback and attaches it to the matching run after create acceptance.
- Given duplicate callbacks arrive for the same scenario group and callback type, Backoffice preserves all timeline entries and uses the latest callback as the current step payload.
- Given callback payload includes unknown fields, the raw JSON viewer still exposes those fields.

### 12.2 State and API Acceptance

- A run exposes `runId`, `miEventId`, `userId`, `agentBaseUrl`, `scenarioGroupId`, local lifecycle state, latest Agent `status`, latest Agent `stage`, accepted responses, callbacks, detail response, normalized model, timeline, and errors.
- Local lifecycle distinguishes request-in-flight states from callback-waiting states; UI success is not based only on HTTP accepted responses.
- Validation request bodies are built from the currently edited branch criteria table.
- Signpost and confirmation request bodies are built from the current one-view draft, including edited group name, description, narratives, probabilities, and signposts.
- Request body preview and submitted request body are inspectable in the QA inspector for validation, signpost generation, and confirmation.
- Manual refresh updates Agent detail-derived data and does not silently discard unsent local edits.

### 12.3 Event List Acceptance

- The first meaningful screen is the Event List workflow, not a landing page.
- Event List shows `Event List` and `Scenario Group List` tabs, status filters, category filter, date range, sort, recommended-only toggle, and event-name search.
- Event rows show updated/new badge, date/time, category, event title, `JKM`, `TTF`, `HH`, and scenario action.
- Market impact cells preserve the screenshot semantics of market label badges and red/green/gray directional indicators.
- Selecting an event updates `miEventId`; clicking the scenario action starts or resumes Scenario Design.
- If no event data is available, manual `miEventId` entry remains usable.

### 12.4 Scenario Group List Acceptance

- Scenario Group List tab can load scenario groups through `GET /backoffice/api/scenario-groups`.
- Default list excludes soft-deleted scenario groups.
- Include-deleted toggle shows deleted rows with clear deleted state when the backend/source supports it.
- Rows show scenario group ID/name, base event reference, status/stage, scenario count, signpost count, updated time, and row actions.
- Clicking detail opens Scenario Group Detail and fetches detail through `GET /backoffice/api/scenario-groups/{scenario_group_id}`.
- Clicking delete opens a confirmation dialog before any API call.
- Confirming delete calls `DELETE /backoffice/api/scenario-groups/{scenario_group_id}` and does not call hard delete.
- Successful delete removes the row from the default list or marks it deleted when include-deleted is on.
- Failed delete keeps the row visible and records the raw error in QA Inspector.

### 12.5 Scenario Design Step 1 Acceptance

- Initial generation loading keeps the Scenario Design shell visible and shows skeleton rows or centered loading text.
- Step header shows step 1 active and step 2 inactive while branch criteria are being reviewed.
- Base Event panel shows event title, timestamp, and category.
- Branch criteria table renders dynamic Agent criterion columns in stable order.
- User can edit scenario names and criterion values, add rows, delete non-baseline rows, and reset to latest Agent-generated values.
- Baseline row shows `BC` and remains stable through validation and transition to step 2.
- `변경사항 검토` is enabled only after generation output/detail is available and no validation request is in flight.
- While validation is in flight, the table remains visible and an overlay or disabled state communicates progress.
- Validation warning state shows an orange warning area with affected scenario, reason, and recommended fix direction.
- `검토 완료` is enabled only after successful validation or compatible Agent detail state.
- Validation failure or callback failure keeps edited table data visible and exposes raw failure JSON.

### 12.6 Scenario Design Step 2 Acceptance

- Step header shows step 1 completed and step 2 active.
- One-view loading shows `데이터를 로드 중입니다` style loading without clearing the step shell.
- Scenario group name enforces 100 characters and shows a `current / 100` counter.
- Scenario group description enforces 500 characters and shows a `current / 500` counter.
- Scenario narrative enforces 500 characters and shows a `current / 500` counter per scenario.
- Scenario cards are horizontally scrollable when more cards exist than fit the viewport.
- Each scenario card shows order, optional `BC`, title, narrative, branch criteria summary, probability input with `%`, and major signposts.
- Probability fields accept 0 to 100 and show a warning when total probability is not 100.
- Signpost labels can truncate in cards, while full text remains available in detail or raw JSON.
- Per-section reset restores the latest Agent-generated value; `전체 초기화` restores all one-view edits.
- `시나리오 그룹 생성` sends the current edited one-view draft and records the request/response in the QA inspector.

### 12.7 Scenario Group Detail Acceptance

- After confirmation, the UI can show a Scenario Group detail page with title and tabs for `요약`, `가정 및 실현 가능성`, `가격 전망`, and `시나리오 상세`.
- Summary tab shows base event metadata, scenario group description, and a scenario assumption/probability table.
- Summary table preserves scenario order, baseline badge, branch criteria, probability, and per-scenario status dropdown.
- Scenario detail tab shows a left scenario list and right selected-scenario detail.
- Selecting a scenario updates narrative, probability, major assumptions, and Signpost definition table without losing tab state.
- Signpost table includes label, direction, impact, and evidence/core basis when present.
- Missing optional Agent fields render as empty states and remain inspectable in raw detail JSON.

### 12.8 Compose and End-to-End Acceptance

- `docker compose up --build` starts Agent and Backoffice.
- Browser can open `http://localhost:9010`.
- Agent callback requests reach `backoffice:9010` and appear in Backoffice timeline.
- The full workflow can be completed from Backoffice UI: select event or enter `miEventId`, create draft, wait for generation callback, validate branch criteria, review one-view, create signposts when required, confirm scenario group, and inspect detail.
- Loading, delayed callback, and error states preserve previous successful data and keep manual refresh available after `scenarioGroupId` exists.

## 13. Risks and Mitigations

- Callback does not arrive.
  - Provide manual refresh and show current Agent detail state.
- SSE disconnects.
  - Keep run state in backend memory and reconnect from frontend.
- Backend restarts lose run state.
  - Accept for v1; add SQLite or file persistence later if needed.
- Agent config override fails in Compose.
  - Use a mounted Compose-specific config file if env override is not supported.
- Frontend table editing diverges from Agent DB state.
  - Make refresh behavior explicit and show the payload that will be submitted.

## 14. Future Extensions

- Persist run history in SQLite.
- Add run list and replay of past callbacks.
- Add basic auth for shared internal environments.
- Add generated request-body export for manual API scripts.
- Add WebSocket support if bidirectional interaction becomes necessary.

# Backoffice Frontend Plan

## Scope

Write scope for this task is limited to:

- `backoffice/frontend/**`
- `docs/backoffice/plan/01_frontend.md`
- `backoffice/README.md` frontend section only if needed

Source requirements:

- `AGENTS.md`
- `docs/backoffice/PRD.md`
- `docs/backoffice/DESIGN.md`
- `docs/backoffice/TEST_SCENARIOS.md`

## Checklist

- [x] Read project instructions and Backoffice PRD/DESIGN.
- [x] Inspect available local request/response samples for frontend API shapes.
- [x] Scaffold a runnable React + Vite + TypeScript app under `backoffice/frontend`.
- [x] Implement `/backoffice/api` client, runtime controls, request-body builders, SSE subscription, and manual refresh.
- [x] Implement Event List / Scenario Group List entry workspace.
- [x] Implement Scenario Design step 1 editable branch criteria table and validation warning/success states.
- [x] Implement Scenario Design step 2 one-view scenario card editor, signpost generation request, and confirmation request.
- [x] Implement Scenario Group detail tabs with summary, assumptions, price outlook placeholder, scenario detail, timeline, and raw JSON inspector.
- [x] Verify with local static checks where possible.
- [x] Add Event List API client calls:
  - `GET /backoffice/api/events`
  - `GET /backoffice/api/events/{miEventId}`
- [x] Replace seed-only Event List data with API-backed rows and explicit fallback source state.
- [x] Extend Event List types and UI fields:
  - Event Type L1/L2 labels
  - one-line summary
  - signal/recommended state and reasons
  - related scenario group `scenarioGroupId`, `status`, `stage`, counts, and deleted state
  - pagination metadata
- [x] Add Event List `Previous` and `Next` controls that preserve filters and selected `miEventId`.
- [x] Add Event Detail workspace:
  - event metadata and analysis
  - Event Type L1/L2 IDs/codes/labels
  - scenario dimension template table
  - raw event/template JSON inspector evidence
  - related scenario group action area
- [x] Implement Event row scenario action policy:
  - no scenario group: `생성하기` starts a new run
  - `status=creating`: `생성하기` attaches to the existing `scenarioGroupId` and continues by `stage`
  - `status=created` + `stage=completed`: `상세보기` opens Scenario Group detail
- [x] Implement full `status/stage` workspace routing for continuing existing groups:
  - `creating` + `ready`: Step 1 loading/waiting state
  - `creating` + `scenario_created`: Step 1 branch criteria review
  - `creating` + `scenario_validated`: Step 2 one-view/signpost flow
  - `creating` + `signpost_created`: Step 2 confirmation-ready flow
  - `created` + `completed`: Scenario Group detail
- [x] Update validation UX so accepted response only shows callback-waiting state:
  - remove any message that tells the user to check callback body manually
  - show `validation_waiting_callback` progress after accepted
  - render validation callback result in the Step 1 validation callout
  - enable `검토 완료` based on callback/detail result, not accepted response alone
- [x] Add Scenario Group List API client calls:
  - `GET /backoffice/api/scenario-groups`
  - `DELETE /backoffice/api/scenario-groups/{scenarioGroupId}`
- [x] Add Scenario Group List normalized types, row state, filter state, and delete result state.
- [x] Replace the current placeholder/list entry with a real Scenario Group List table:
  - keyword search
  - status/stage filters
  - date range/sort controls
  - include-deleted toggle
  - refresh action
- [x] Add detail navigation from Scenario Group List rows using existing detail workspace.
- [x] Add soft-delete confirmation dialog:
  - target summary
  - delete authorization input or configured token selector
  - request loading state
  - failure callout
- [x] Update list rows after soft delete:
  - remove row when include-deleted is off
  - keep row with deleted badge when include-deleted is on
  - record raw delete request/response/error in QA inspector
- [x] Add focused frontend verification for Scenario Group List filters, detail action, delete confirm/cancel, delete success, and delete failure.
- [x] Update end-to-end test flow so every generated Scenario Group finishes with Scenario Group List detail check and soft-delete cleanup.

## Implementation Notes

- The backend contract is assumed to live under `/backoffice/api`.
- The UI keeps editable frontend state as the source for validation, signpost, and confirmation request bodies.
- SSE events are consumed from `/backoffice/api/runs/{runId}/events` after run creation and added to the timeline/raw inspector.
- Until the backend exists, the UI includes realistic local seed data so the first screen is a usable Next-Gen MI workflow console instead of a landing page.
- Event List should prefer `/backoffice/api/events`; seed data is only a fallback and must be labeled as fallback in QA/debug state.
- Event Detail must be reachable from Event List without clearing runtime controls, active run, timeline, or raw inspector history.
- Existing `creating` scenario groups are continuation targets. The `생성하기` button should attach to the existing group and route by Agent `stage`, not force duplicate creation.
- Validation accepted response is request acknowledgement only. Validation warning/success UI must wait for callback, SSE `validation_result`, or a detail state compatible with the validation result.
- Integration adjustment: API normalizer reads the backend `RunOut` wrapper (`run`, `run.normalized`, `run.detail`) and confirmation request bodies use the Agent-compatible `scenarioGroup + table` shape.
- New Scenario Group List work must preserve the Event List as the first meaningful screen while making the `Scenario Group List` tab a complete list/detail/delete workspace.
- Soft delete must call only Backoffice's soft-delete proxy. The frontend must not expose hard delete.
- Scenario Group List delete must be treated as a row-level mutation. It must not clear the active run, timeline, raw JSON history, or current detail state until the backend confirms deletion.
- Include-deleted behavior must be explicit: default list hides soft-deleted rows, include-deleted list shows them with `삭제됨` state.
- Test cleanup is part of the happy path: after confirmation/detail verification, navigate back to Scenario Group List and soft delete the generated group.

## Review Notes

- Good: the plan now covers API client methods, normalized list state, filters, detail navigation, delete confirmation, row update behavior, and QA inspector evidence.
- Risk: delete authorization UX is still open between direct input and configured token selector. Choose one before implementation so tests can be deterministic.
- Risk: current scope does not mention excluding generated frontend artifacts from commits. Keep `node_modules`, `dist`, `*.tsbuildinfo`, generated `vite.config.js`, and `vite.config.d.ts` out of source commits.
- Required alignment: Scenario Group List work must satisfy `docs/backoffice/TEST_SCENARIOS.md` cleanup flow, not only the PRD acceptance criteria.

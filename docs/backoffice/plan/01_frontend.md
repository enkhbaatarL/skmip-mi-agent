# Backoffice Frontend Plan

## Scope

Write scope for this task is limited to:

- `backoffice/frontend/**`
- `local/backoffice/plan/01_frontend.md`
- `backoffice/README.md` frontend section only if needed

Source requirements:

- `AGENTS.md`
- `local/backoffice/PRD.md`
- `local/backoffice/DESIGN.md`

## Checklist

- [x] Read project instructions and Backoffice PRD/DESIGN.
- [x] Inspect available local request/response samples for frontend API shapes.
- [x] Scaffold a runnable React + Vite + TypeScript app under `backoffice/frontend`.
- [x] Implement `/backoffice/api` client, runtime controls, request-body builders, SSE subscription, and manual refresh.
- [x] Implement Event List / Scenario Group List entry workspace.
- [x] Implement Scenario Design step 1 editable branch criteria table and validation warning/success states.
- [x] Implement Scenario Design step 2 one-view scenario card editor, signpost generation request, and confirmation request.
- [x] Implement Scenario Group detail tabs with summary, assumptions, price outlook placeholder, scenario detail, timeline, and raw JSON inspector.
- [x] Verify with local static checks where possible; `node_modules` is not installed, so no network install or build was run.
- [ ] Add Scenario Group List API client calls:
  - `GET /backoffice/api/scenario-groups`
  - `DELETE /backoffice/api/scenario-groups/{scenarioGroupId}`
- [ ] Add Scenario Group List normalized types, row state, filter state, and delete result state.
- [ ] Replace the current placeholder/list entry with a real Scenario Group List table:
  - keyword search
  - status/stage filters
  - date range/sort controls
  - include-deleted toggle
  - refresh action
- [ ] Add detail navigation from Scenario Group List rows using existing detail workspace.
- [ ] Add soft-delete confirmation dialog:
  - target summary
  - delete authorization input or configured token selector
  - request loading state
  - failure callout
- [ ] Update list rows after soft delete:
  - remove row when include-deleted is off
  - keep row with deleted badge when include-deleted is on
  - record raw delete request/response/error in QA inspector
- [ ] Add focused frontend verification for Scenario Group List filters, detail action, delete confirm/cancel, delete success, and delete failure.

## Implementation Notes

- The backend contract is assumed to live under `/backoffice/api`.
- The UI keeps editable frontend state as the source for validation, signpost, and confirmation request bodies.
- SSE events are consumed from `/backoffice/api/runs/{runId}/events` after run creation and added to the timeline/raw inspector.
- Until the backend exists, the UI includes realistic local seed data so the first screen is a usable Next-Gen MI workflow console instead of a landing page.
- Integration adjustment: API normalizer reads the backend `RunOut` wrapper (`run`, `run.normalized`, `run.detail`) and confirmation request bodies use the Agent-compatible `scenarioGroup + table` shape.
- New Scenario Group List work must preserve the Event List as the first meaningful screen while making the `Scenario Group List` tab a complete list/detail/delete workspace.
- Soft delete must call only Backoffice's soft-delete proxy. The frontend must not expose hard delete.

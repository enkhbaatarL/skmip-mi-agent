# Backoffice Backend Plan

## Scope

- Implement a standalone FastAPI backend under `backoffice/backend`.
- Do not import `apps/` runtime internals; call the Scenario Group Agent as an external HTTP service.
- Keep v1 run state in memory with SSE fan-out and orphan callback attachment.
- Serve React static `dist` only when it exists.
- Use `docs/backoffice/PRD.md`, `docs/backoffice/DESIGN.md`, and `docs/backoffice/TEST_SCENARIOS.md` as the source requirements.

## Tasks

- [x] Read required project, API, Python, and Backoffice PRD docs.
- [x] Define Pydantic schemas and JSON aliases for run lifecycle, requests, callbacks, detail, and normalized UI models.
- [x] Implement in-memory store for runs, scenario-group mapping, timeline, callbacks, details, errors, orphan callbacks, and SSE queues.
- [x] Preserve Agent-compatible request bodies separately from QA/display request envelopes containing `runId`, `scenarioGroupId`, `miEventId`, and `userId`.
- [x] Normalize Agent callback/detail payloads into PRD read model keys: `eventList`, `branchCriteriaDraft`, `oneViewDraft`, and `scenarioGroupDetail`.
- [x] Keep orphan callback lifecycle state after accepted create binding instead of reverting to waiting state.
- [x] Implement async Agent HTTP client using `httpx.AsyncClient`.
- [x] Implement FastAPI routes for Backoffice proxy APIs, Agent callback receivers, OAuth2 token mock, SSE, and static dist serving.
- [x] Run compile/import verification without network installs.
- [x] Document changed files and local execution/verification steps.
- [ ] Add Backoffice Scenario Group List endpoint:
  - `GET /backoffice/api/scenario-groups`
  - query: `agentBaseUrl`, `includeDeleted`, optional `miEventId`, keyword, status, stage, date range, sort, paging
  - response: normalized rows, source metadata, raw source payload when available
- [ ] Decide list source strategy for current Agent capability:
  - prefer Agent persisted list endpoint if available
  - otherwise merge Backoffice in-memory runs and fixture/demo rows
  - clearly expose `source` and limitations in the response
- [ ] Add Backoffice soft-delete endpoint:
  - `DELETE /backoffice/api/scenario-groups/{scenario_group_id}`
  - proxy only Agent `DELETE /scenario-groups/{scenario_group_id}`
  - accept `agentBaseUrl`, `userId`, and delete authorization
  - never call Agent hard-delete endpoint
- [ ] Extend `AgentClient` with list and soft-delete methods, including authorization header forwarding for delete.
- [ ] Extend schemas for scenario group list rows, list filters, list response metadata, delete request, and delete result.
- [ ] Update store/run behavior after soft delete:
  - mark matching run/detail/list row as deleted
  - append timeline event
  - preserve accepted/callback/detail raw history
  - publish SSE event for list/detail refresh if a run is bound
- [ ] Add backend tests or smoke checks for list empty/source metadata, delete success, delete authorization failure, delete non-existent group, and include-deleted detail refresh.
- [ ] Support test cleanup flow:
  - generated group can be found from list by `scenarioGroupId`
  - detail can be opened before deletion
  - delete result is inspectable
  - default list hides deleted row
  - include-deleted list exposes deleted row state when source supports it

## Verification

- `.venv/bin/python -m compileall backoffice/backend`
- `.venv/bin/python -c "from backoffice.backend.main import app; print(app.title)"`
- FastAPI TestClient smoke:
  - `POST /api/v1/oauth2/token` returns `200`.
  - generation callback for an unknown `scenarioGroupId` returns orphan callback acceptance.
  - `GET /backoffice/api/runs/missing` returns `404`.
  - `GET /backoffice/api/runs/missing/events` returns `404`.
  - `GET /openapi.json` returns `200`.
- Store smoke:
  - orphan generation callback attaches after accepted create response.
  - run lifecycle remains `scenario_created`.
  - normalized read model exposes `eventList`, `branchCriteriaDraft`, `oneViewDraft`, and `scenarioGroupDetail`.
- Planned Scenario Group List verification:
  - `GET /backoffice/api/scenario-groups` returns normalized rows and source metadata.
  - `DELETE /backoffice/api/scenario-groups/{scenario_group_id}` forwards only the Agent soft-delete request.
  - delete result is recorded without removing local run history.
  - generated Scenario Groups can be cleaned up at the end of end-to-end tests.
- Lint note:
  - `.venv/bin/ruff check backoffice/backend` was not run because `ruff` is not installed in the local virtualenv.

## Local Execution

```bash
uvicorn backoffice.backend.main:app --reload --host 127.0.0.1 --port 9010
```

Agent launch remains separate and follows `.vscode/launch.json`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

The Agent must be configured to send callbacks to the Backoffice callback receiver paths on port `9010`.

## Review Notes

- Good: the plan keeps Backoffice outside `apps/`, treats Agent as the source of truth, keeps v1 state in memory, and preserves raw history for QA.
- Risk: Scenario Group List source is not fully resolved. Current Agent docs/code expose detail and soft delete, but a persisted list endpoint may not exist. Implement the fallback deliberately and expose `source` so QA does not confuse in-memory/demo rows with Agent-persisted list rows.
- Risk: delete authorization needs a concrete contract. The backend should define whether the frontend sends a bearer token directly, a token alias, or an environment-configured token reference.
- Required alignment: soft delete must update list/detail/run state without deleting accepted responses, callbacks, detail payloads, or timeline events, because TEST_SCENARIOS requires post-delete evidence in QA Inspector.

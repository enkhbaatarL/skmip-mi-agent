# Agent Engineer Plan

## Scope

- Add Agent API support required by Backoffice Event List and Event Detail.
- Keep DB access behind persistence services/repositories.
- Follow `docs/architectures/scenario_group_agent_api_request_response.md` for Scenario Group `status`/`stage` semantics.
- Follow `.claude/rules/python-conventions.md` for Python style, errors, settings access, and typing.

## Tasks

- [x] Add Agent Event List endpoint:
  - `GET /events`
  - query: keyword, new/updated status, Event Type L1/L2 filters, recommended-only, date range, sort, and paging
  - response: rows, pagination metadata, and raw-compatible source fields needed by Backoffice
- [x] Add Agent Event Detail endpoint:
  - `GET /events/{mi_event_id}`
  - response: event metadata/content, Event Type L1/L2 labels, scenario dimension template, related scenario group summary, and source record IDs
- [x] Add event list/detail DTOs:
  - event identifiers and content fields from `MiEventModel`
  - `eventTypeL1` with ID/code/label
  - `eventTypeL2` with ID/code/label
  - scenario template dimensions from `tmm_mi_scenario_dimension_template_m.template_json`
  - related scenario group summary
  - pagination metadata for `next` and `previous`
- [x] Add or extend `apps/persistence/event/service.py` and `apps/persistence/event/repository.py`:
  - list non-deleted events with joined L1/L2 labels
  - fetch one event detail with L1/L2 labels and source record IDs
  - support filters and sort without exposing ORM objects to API code
- [x] Extend scenario group lookup for event rows:
  - connect the latest non-deleted scenario group by `mi_event_id`
  - return `scenarioGroupId`, `status`, `stage`, scenario count, signpost count if available, and `delYn`
- [x] Expose scenario template data:
  - load template by `event_type_l2_id`
  - preserve raw JSON for Backoffice QA
  - return an empty/null template state without breaking Event Detail when template is missing
- [x] Ensure existing scenario group continuation works:
  - when `POST /scenario-groups` receives an event that already has a non-deleted group with `status=creating`, return the existing `scenarioGroupId/status/stage`
  - do not treat `status=creating` as completed detail-only state
  - keep user ownership and existing conflict rules intact for cases where another user is not allowed to continue
- [x] Document Agent API additions in `docs/architectures/scenario_group_agent_api_request_response.md`.

## Status/Stage Mapping

- `creating` + `ready`: create request accepted; scenario generation output is not ready.
- `creating` + `scenario_created`: scenario draft and branch criteria are ready for Step 1 review.
- `creating` + `scenario_validated`: validation is complete; Step 2 can continue toward signpost generation.
- `creating` + `signpost_created`: signposts are ready; confirmation can continue.
- `created` + `completed`: confirmation is complete; open Scenario Group Detail.
- Validation failure keeps the group at `creating` + `scenario_created`; Backoffice should show the callback result and allow correction.

## Test Plan

- Event list returns L1/L2 labels, major event fields, scenario group summary, and pagination metadata.
- Event detail returns event content, L1/L2 labels, template dimensions, raw template JSON, and source record IDs.
- Event list filters cover keyword, new/updated status, Event Type filters, recommended-only, date range, and sort.
- Pagination supports first page, middle page, last page, no previous, and no next states.
- Missing event returns the existing project error style with `MIBaseError`.
- Missing template does not fail event detail unless product/API policy later requires a hard error.
- Related scenario group states cover no group, `creating + ready`, `creating + scenario_created`, `creating + scenario_validated`, `creating + signpost_created`, and `created + completed`.
- Existing `creating` scenario group can be continued through `POST /scenario-groups` or the new event row metadata without duplicate group creation.

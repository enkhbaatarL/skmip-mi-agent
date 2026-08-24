# AGENTS.md

This file is the shared project guide for Codex, Cursor, and Claude Code.
Keep it short and treat linked docs as the source of truth for details.

## Project Shape

- Current runtime Agent: `apps/agents/scenario_group_agent/`
- FastAPI entrypoint: `main.py`
- Python conventions: `.claude/rules/python-conventions.md`
- DB migration source of truth: sibling `skmip-mi-agent-mgmt` repository

## Read This First

If the task touches one of these areas, read the linked document before changing code.

- Directory structure, file ownership, endpoint-flow mapping, or package boundaries:
  `docs/architectures/project_directory_structure.md`
- Scenario Group Agent v4 runnable graph, shared state, flow node chains, or generation pipeline logic:
  `docs/agents/scenario_group_agent/03_SCENARIO_GROUP_AGENT_FLOW.md`
- Scenario Group Agent API bodies, callback behavior, and status/stage transitions:
  `docs/agents/scenario_group_agent/02_SCENARIO_GROUP_AGENT_API_SPEC.md`
- Scenario Group Agent tables, JSON columns, relationships, or transaction boundaries:
  `docs/agents/scenario_group_agent/04_SCENARIO_GROUP_AGENT_DB_SPEC.md`
- Scenario Group Agent manual pipeline or quality evaluation:
  `docs/agents/scenario_group_agent/05_SCENARIO_GROUP_AGENT_TEST_AND_QUALITY.md`
- Python style, settings access, typing, async patterns, Pydantic, or exception handling:
  `.claude/rules/python-conventions.md`

## Core Rules

- Follow existing `scenario_group_agent` patterns before introducing new structure.
- Import settings from `apps.common.configs.config`; do not add imports from `apps.common.configs.settings`.
- In normal app code, use `get_settings()` instead of reading `os.environ` directly.
- Use `MIBaseError(ErrorCode..., detail=...)` for domain/API errors.
- Keep DB access behind `apps/persistence/<domain>/service.py` and `repository.py`; flow/node code should call services.
- Put flow endpoint request/response schemas in `flows/<flow_name>/api_schema.py`; keep shared API schemas or flow-less API schemas in `schemas/api/common.py`, `schemas/api/table.py`, or focused files such as `schemas/api/manage_scenario_groups.py`.
- Put persistence DTOs next to the owning persistence service in `apps/persistence/<domain>/schema.py`; put shared persistence base/enums in `apps/persistence/schema_base.py` and `apps/persistence/enums.py`.
- For long-running API work that returns immediately, use the existing `flow_async.py` background-task pattern.

## Tests

- Automated tests live in `tests/automated/`.
- Manual/local API scripts live in `tests/manual/`.
- Migration SQL under this repository is optional reference material. Tests must not require those files to exist.

## Editing Guidance

- Keep changes scoped to the requested behavior.
- Do not revive removed Agent packages such as `mi_agent`, `scenario_agent`, `event_flow_agent`, or `signpost_flow_agent`.
- Update common architecture and the owning Agent docs when changing package ownership, flow boundaries, or endpoint-to-flow mapping.

## Github Code Review Guideline

- Write review comments in Korean.
- Before reviewing, follow the `Read This First` routing in this file and read the documents relevant to the changed area.
- Focus findings on bugs, regression risks, missing tests, and mismatches between docs and code.
- Start each review comment with brief context: what the current code appears intended to do, then explain the issue in that context.
- Include file/line references, why the issue matters, and the expected fix direction whenever possible.
- Avoid style preferences or broad refactor suggestions unless they directly affect the safety of the current change.
- Do not report a missing migration file in this repository as a review issue. DB migrations are managed in
  `skmip-mi-agent-mgmt`; SQL checked into this repository is optional reference material only.
- If there are no issues, say so clearly and mention remaining risks or checks that were not run.

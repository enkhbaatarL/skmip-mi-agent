# AGENTS.md

This file is the shared project guide for Codex, Cursor, and Claude Code.
Keep it short and treat linked docs as the source of truth for details.

## Project Shape

- Current runtime Agent: `apps/agents/scenario_group_agent/`
- FastAPI entrypoint: `main.py`
- Python conventions: `.claude/rules/python-conventions.md`

## Read This First

If the task touches one of these areas, read the linked document before changing code.

- Directory structure, file ownership, endpoint-flow mapping, or package boundaries:
  `docs/architectures/project_directory_structure.md`
- Scenario Group Agent runnable graph assembly, shared state, flow node chains, or generation pipeline logic:
  `docs/architectures/scenario_group_agent_flow_pipeline.md`
- Scenario Group Agent API bodies, callback behavior, and status/stage transitions:
  `docs/architectures/scenario_group_agent_api_request_response.md`
- Python style, settings access, typing, async patterns, Pydantic, or exception handling:
  `.claude/rules/python-conventions.md`

## Core Rules

- Follow existing `scenario_group_agent` patterns before introducing new structure.
- Import settings from `apps.common.configs.config`; do not add imports from `apps.common.configs.settings`.
- In normal app code, use `get_settings()` instead of reading `os.environ` directly.
- Use `MIBaseError(ErrorCode..., detail=...)` for domain/API errors.
- Keep DB access behind `persistence/<domain>/service.py` and `repository.py`; flow/node code should call services.
- Put API schemas in `schemas/<api_name>.py`, shared schema types in `schemas/common.py`, and enums in `schemas/enums.py`.
- For long-running API work that returns immediately, use the existing `flow_async.py` background-task pattern.

## Tests

- Automated tests live in `tests/automated/`.
- Manual/local API scripts live in `tests/manual/`.

## Editing Guidance

- Keep changes scoped to the requested behavior.
- Do not revive removed Agent packages such as `mi_agent`, `scenario_agent`, `event_flow_agent`, or `signpost_flow_agent`.
- Update architecture docs when changing package ownership, flow boundaries, or endpoint-to-flow mapping.

## Github Code Review Guideline

- Write review comments in Korean.
- Before reviewing, follow the `Read This First` routing in this file and read the documents relevant to the changed area.
- Focus findings on bugs, regression risks, missing tests, and mismatches between docs and code.
- Start each review comment with brief context: what the current code appears intended to do, then explain the issue in that context.
- Include file/line references, why the issue matters, and the expected fix direction whenever possible.
- Avoid style preferences or broad refactor suggestions unless they directly affect the safety of the current change.
- If there are no issues, say so clearly and mention remaining risks or checks that were not run.

import { useEffect, useMemo, useRef, useState } from "react";
import type { AgentClient } from "../../api/agentClient";
import {
  confirmGeneration,
  createScenarios,
  createSignposts,
  getScenarioGroupDetail,
  softDeleteScenarioGroup,
  validateScenarios
} from "../../api/v1Pipeline";
import type {
  CallbackBody,
  ConfirmationRequest,
  EventDetail,
  ScenarioGroupDetailResponse,
  ScenarioTable,
  SoftDeleteResponse,
  TableSyncRequest
} from "../../domain/apiTypes";
import type { RuntimeSnapshot } from "../../domain/runtime";
import { totalTokens } from "../../domain/tokenUsage";
import { EventSelector } from "../event-selector/EventSelector";
import { ConfirmationStep } from "./ConfirmationStep";
import { CreateStep } from "./CreateStep";
import { buildV1ExportBundle } from "./export";
import {
  normalizeScenarioTable,
  ScenarioTableEditor
} from "./ScenarioTableEditor";
import { SignpostStep } from "./SignpostStep";
import { StepRail } from "./StepRail";
import {
  createEmptyV1Run,
  type StepState,
  type V1RunState,
  type V1StepId
} from "./types";
import { V1RunHeader } from "./V1RunHeader";
import { ValidationStep } from "./ValidationStep";

export interface V1ClientContext {
  client: AgentClient;
  runtime: RuntimeSnapshot;
}

interface V1WorkspaceProps {
  createClient: () => V1ClientContext;
  onRunLockChange: (locked: boolean) => void;
}

const UNKNOWN_MESSAGE =
  "응답을 확인하지 못해 결과가 불명입니다. 서버에서 작업이 완료되었을 수 있습니다.";

function resultError(
  response: unknown,
  fallback: string | undefined,
  status: StepState["status"]
): string {
  if (status === "unknown") return fallback || UNKNOWN_MESSAGE;
  if (response && typeof response === "object") {
    const body = response as Record<string, unknown>;
    if (typeof body.reason === "string" && body.reason) return body.reason;
    if (typeof body.message === "string" && body.message) return body.message;
  }
  return fallback || "요청이 실패했습니다. Evidence에서 원본 응답을 확인하세요.";
}

function usageTokens(body: CallbackBody | undefined): number | undefined {
  return totalTokens(body?.usage);
}

function confirmationBody(
  detail: ScenarioGroupDetailResponse,
  userId: number
): ConfirmationRequest {
  const table: ScenarioTable = {
    headers: detail.table.headers.map((header) => ({ ...header })),
    rows: detail.table.rows.map((row) => ({
      ...row,
      cells: { ...row.cells },
      ...(row.metrics ? { metrics: { ...row.metrics } } : {}),
      ...(row.signposts
        ? {
            signposts: row.signposts.map((signpost) => ({
              ...signpost,
              useYn: signpost.useYn ?? "Y"
            }))
          }
        : {})
    }))
  };
  return {
    userId,
    scenarioGroup: {
      title: detail.scenarioGroup.title,
      summary: detail.scenarioGroup.summary ?? null,
      description: detail.scenarioGroup.description ?? null
    },
    table
  };
}

export function V1Workspace({
  createClient,
  onRunLockChange
}: V1WorkspaceProps) {
  const [selectedEvents, setSelectedEvents] = useState<EventDetail[]>([]);
  const [run, setRun] = useState<V1RunState>(createEmptyV1Run);
  const activeController = useRef<AbortController | undefined>(undefined);

  const selectorResult = useMemo(() => {
    try {
      return { context: createClient(), error: "" };
    } catch (error) {
      return {
        context: undefined,
        error:
          error instanceof Error
            ? error.message
            : "Runtime 설정을 확인하세요."
      };
    }
  }, [createClient]);
  const selectorContext = selectorResult.context;

  const running = Object.values(run.steps).some(
    (step) => step.status === "running"
  );
  const runLocked = Boolean(run.startedAt && !run.completedAt);

  useEffect(() => {
    onRunLockChange(runLocked);
  }, [onRunLockChange, runLocked]);

  useEffect(
    () => () => {
      onRunLockChange(false);
    },
    [onRunLockChange]
  );

  useEffect(() => {
    if (run.startedAt) return;
    const event = selectedEvents[0];
    setRun((current) => ({
      ...current,
      event,
      steps: {
        ...current.steps,
        create: { status: event ? "ready" : "idle" }
      }
    }));
  }, [run.startedAt, selectedEvents]);

  function updateStep(id: V1StepId, state: StepState) {
    setRun((current) => ({
      ...current,
      steps: { ...current.steps, [id]: state }
    }));
  }

  async function executeCreate() {
    const event = selectedEvents[0];
    if (!event || run.steps.create.status !== "ready") return;
    const context = createClient();
    const controller = new AbortController();
    activeController.current = controller;
    const request = {
      miEventId: event.miEventId,
      userId: context.runtime.userId
    };
    setRun((current) => ({
      ...current,
      runtime: context.runtime,
      event,
      startedAt: new Date().toISOString(),
      currentStep: "create",
      exported: false,
      steps: {
        ...current.steps,
        create: { status: "running", request }
      }
    }));

    const result = await createScenarios(
      context.client,
      request,
      controller.signal
    );
    activeController.current = undefined;
    const body = result.data;
    const success = result.status === "success" && body?.scenarioGroup && body.table;
    setRun((current) => ({
      ...current,
      scenarioGroupId: success
        ? body.scenarioGroup?.scenarioGroupId
        : current.scenarioGroupId,
      scenarioGroup: success ? body.scenarioGroup : current.scenarioGroup,
      editableTable: success
        ? normalizeScenarioTable(body.table as ScenarioTable)
        : current.editableTable,
      lastServerTable: success
        ? normalizeScenarioTable(body.table as ScenarioTable)
        : current.lastServerTable,
      currentStep: success ? "validation" : "create",
      calls: [...current.calls, result.record],
      steps: {
        ...current.steps,
        create: {
          status: result.status,
          request,
          response: body,
          elapsedMs: result.record.elapsedMs,
          tokenUsage: usageTokens(body),
          summary: success
            ? `Group #${body.scenarioGroup?.scenarioGroupId} · ${body.table?.rows.length ?? 0} scenarios`
            : undefined,
          ...(success
            ? {}
            : {
                error: resultError(
                  body,
                  result.record.error,
                  result.status
                )
              })
        },
        validation: success ? { status: "ready" } : { status: "idle" }
      }
    }));
  }

  async function executeValidation() {
    if (!run.runtime || !run.scenarioGroupId || !run.editableTable) return;
    const context = createClient();
    const controller = new AbortController();
    activeController.current = controller;
    const table = normalizeScenarioTable(run.editableTable);
    const request: TableSyncRequest = {
      userId: run.runtime.userId,
      table
    };
    updateStep("validation", {
      ...run.steps.validation,
      status: "running",
      request
    });
    const result = await validateScenarios(
      context.client,
      run.scenarioGroupId,
      request,
      controller.signal
    );
    activeController.current = undefined;
    const body = result.data;
    const returnedTable = body?.table
      ? normalizeScenarioTable(body.table)
      : table;
    const forward = result.status === "success";
    setRun((current) => ({
      ...current,
      editableTable:
        ["success", "warning"].includes(result.status)
          ? returnedTable
          : current.editableTable,
      lastServerTable:
        ["success", "warning"].includes(result.status)
          ? returnedTable
          : current.lastServerTable,
      scenarioGroup: body?.scenarioGroup
        ? { ...(current.scenarioGroup ?? body.scenarioGroup), ...body.scenarioGroup }
        : current.scenarioGroup,
      currentStep: forward ? "signpost" : "validation",
      calls: [...current.calls, result.record],
      finalScenarioGroupDetail: undefined,
      completedAt: undefined,
      steps: {
        ...current.steps,
        validation: {
          status: result.status,
          request,
          response: body,
          elapsedMs: result.record.elapsedMs,
          tokenUsage: usageTokens(body),
          warningAcknowledged: false,
          summary:
            result.status === "success"
              ? body?.reason ?? "scenario_validated"
              : undefined,
          ...(result.status === "warning"
            ? {
                warning:
                  body?.reason ??
                  "Validation이 통과되지 않았습니다. 내용을 확인하세요."
              }
            : {}),
          ...(["error", "unknown"].includes(result.status)
            ? {
                error: resultError(
                  body,
                  result.record.error,
                  result.status
                )
              }
            : {})
        },
        signpost: forward ? { status: "ready" } : { status: "idle" },
        confirmation: { status: "idle" }
      }
    }));
  }

  function acknowledgeWarning() {
    if (run.steps.validation.status !== "warning") return;
    setRun((current) => ({
      ...current,
      currentStep: "signpost",
      steps: {
        ...current.steps,
        validation: {
          ...current.steps.validation,
          warningAcknowledged: true
        },
        signpost: { status: "ready" }
      }
    }));
  }

  async function executeSignpost() {
    if (!run.runtime || !run.scenarioGroupId || !run.editableTable) return;
    const context = createClient();
    const controller = new AbortController();
    activeController.current = controller;
    const request: TableSyncRequest = {
      userId: run.runtime.userId,
      table: normalizeScenarioTable(run.editableTable)
    };
    updateStep("signpost", {
      ...run.steps.signpost,
      status: "running",
      request
    });
    const result = await createSignposts(
      context.client,
      run.scenarioGroupId,
      request,
      controller.signal
    );
    activeController.current = undefined;
    const body = result.data;
    const success = result.status === "success";
    const returnedTable = body?.table
      ? normalizeScenarioTable(body.table)
      : undefined;
    setRun((current) => ({
      ...current,
      editableTable: returnedTable ?? current.editableTable,
      lastServerTable: returnedTable ?? current.lastServerTable,
      scenarioGroup: body?.scenarioGroup ?? current.scenarioGroup,
      signposts: returnedTable?.rows.flatMap((row) => row.signposts ?? []),
      currentStep: success ? "confirmation" : "signpost",
      calls: [...current.calls, result.record],
      steps: {
        ...current.steps,
        signpost: {
          status: result.status,
          request,
          response: body,
          elapsedMs: result.record.elapsedMs,
          tokenUsage: usageTokens(body),
          summary: success
            ? `${returnedTable?.rows.reduce((total, row) => total + (row.signposts?.length ?? 0), 0) ?? 0} signposts`
            : undefined,
          ...(success
            ? {}
            : {
                error: resultError(
                  body,
                  result.record.error,
                  result.status
                )
              })
        },
        confirmation: success ? { status: "ready" } : { status: "idle" }
      }
    }));
  }

  async function prepareConfirmation() {
    if (!run.scenarioGroupId || !run.runtime) return;
    const context = createClient();
    const controller = new AbortController();
    activeController.current = controller;
    updateStep("confirmation", {
      ...run.steps.confirmation,
      status: "running"
    });
    const detailResult = await getScenarioGroupDetail(
      context.client,
      run.scenarioGroupId,
      controller.signal
    );
    if (detailResult.status !== "success" || !detailResult.data) {
      setRun((current) => ({
        ...current,
        calls: [...current.calls, detailResult.record],
        steps: {
          ...current.steps,
          confirmation: {
            status: detailResult.status,
            elapsedMs: detailResult.record.elapsedMs,
            error: resultError(
              detailResult.data,
              detailResult.record.error,
              detailResult.status
            )
          }
        }
      }));
      activeController.current = undefined;
      return;
    }

    const request = confirmationBody(
      detailResult.data,
      run.runtime.userId
    );
    activeController.current = undefined;
    setRun((current) => ({
      ...current,
      finalScenarioGroupDetail: detailResult.data,
      calls: [...current.calls, detailResult.record],
      steps: {
        ...current.steps,
        confirmation: {
          ...current.steps.confirmation,
          status: "ready",
          request,
          elapsedMs: detailResult.record.elapsedMs,
          error: undefined
        }
      }
    }));
  }

  async function executeConfirmation() {
    if (
      !run.scenarioGroupId ||
      !run.finalScenarioGroupDetail ||
      !run.steps.confirmation.request
    ) {
      return;
    }
    const context = createClient();
    const controller = new AbortController();
    activeController.current = controller;
    const request = run.steps.confirmation.request as ConfirmationRequest;
    updateStep("confirmation", {
      ...run.steps.confirmation,
      status: "running",
      error: undefined
    });
    const result = await confirmGeneration(
      context.client,
      run.scenarioGroupId,
      request,
      controller.signal
    );
    activeController.current = undefined;
    const success = result.status === "success";
    setRun((current) => ({
      ...current,
      scenarioGroup: {
        ...run.finalScenarioGroupDetail!.scenarioGroup,
        ...(result.data?.data
          ? {
              scenarioGroupId: result.data.data.scenarioGroupId,
              status: result.data.data.status,
              stage: result.data.data.stage
            }
          : {})
      },
      completedAt: success ? new Date().toISOString() : undefined,
      calls: [...current.calls, result.record],
      steps: {
        ...current.steps,
        confirmation: {
          status: result.status,
          request,
          response: result.data,
          elapsedMs:
            (current.steps.confirmation.elapsedMs ?? 0) +
            result.record.elapsedMs,
          summary: success ? "created/completed" : undefined,
          ...(success
            ? {}
            : {
                error: resultError(
                  result.data,
                  result.record.error,
                  result.status
                )
              })
        }
      }
    }));
  }

  async function executeSoftDelete(
    token?: string
  ): Promise<SoftDeleteResponse | undefined> {
    const related = run.event?.relatedScenarioGroup;
    const runtime = run.runtime;
    if (!related || !runtime) return undefined;
    const context = createClient();
    const result = await softDeleteScenarioGroup(
      context.client,
      related.scenarioGroupId,
      { userId: runtime.userId },
      token
    );
    setRun((current) => ({
      ...current,
      calls: [...current.calls, result.record]
    }));
    return result.status === "success" ? result.data : undefined;
  }

  function newRun() {
    if (running) return;
    if (
      run.completedAt &&
      !run.exported &&
      !window.confirm(
        "완료된 결과를 아직 Export하지 않았습니다. Export 없이 새 실행을 시작할까요?"
      )
    ) {
      return;
    }
    if (
      run.startedAt &&
      !run.completedAt &&
      !window.confirm("현재 실행 상태를 지우고 새 실행을 시작할까요?")
    ) {
      return;
    }
    setSelectedEvents([]);
    setRun(createEmptyV1Run());
  }

  function exportRun() {
    const bundle = buildV1ExportBundle(run);
    const blob = new Blob([JSON.stringify(bundle, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `v1-run-${run.runId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setRun((current) => ({ ...current, exported: true }));
  }

  const createRequest =
    run.event && selectorContext
      ? {
          miEventId: run.event.miEventId,
          userId: run.runtime?.userId ?? selectorContext.runtime.userId
        }
      : undefined;
  const validationRequest =
    run.runtime && run.editableTable
      ? {
          userId: run.runtime.userId,
          table: normalizeScenarioTable(run.editableTable)
        }
      : undefined;
  const duplicateGroup =
    run.steps.create.status === "error" &&
    Boolean(run.event?.relatedScenarioGroup) &&
    (/exist|already|duplicate|중복|존재|scenario group/i.test(
      run.steps.create.error ?? ""
    ) ||
      run.event?.scenarioActionState.type !== "create");
  const confirmationRequest = run.steps.confirmation
    .request as ConfirmationRequest | undefined;

  return (
    <section className="v1-workspace" aria-labelledby="v1-workspace-title">
      <h1 className="sr-only" id="v1-workspace-title">
        v1 단일 이벤트 Workspace
      </h1>
      <V1RunHeader
        run={run}
        running={running}
        onNewRun={newRun}
        onExport={exportRun}
      />

      {!selectorContext ? (
        <div className="callout error" role="alert">
          Runtime 설정이 올바르지 않습니다. {selectorResult.error}
        </div>
      ) : (
        <EventSelector
          mode="single"
          selectedEvents={selectedEvents}
          onChange={setSelectedEvents}
          client={selectorContext.client}
          disabled={Boolean(run.startedAt)}
        />
      )}

      <StepRail run={run} onAcknowledgeWarning={acknowledgeWarning} />

      {run.event && createRequest ? (
        <CreateStep
          event={run.event}
          request={createRequest}
          step={run.steps.create}
          duplicateGroup={duplicateGroup}
          onExecute={() => void executeCreate()}
          onCancel={() => activeController.current?.abort()}
          onSoftDelete={executeSoftDelete}
        />
      ) : (
        <p className="empty-hint">
          Event를 선택하고 Create를 실행하세요.
        </p>
      )}

      {run.editableTable && run.lastServerTable && (
        <ScenarioTableEditor
          table={run.editableTable}
          lastServerTable={run.lastServerTable}
          disabled={
            running ||
            run.steps.signpost.status === "success" ||
            Boolean(run.finalScenarioGroupDetail) ||
            run.steps.confirmation.status === "success"
          }
          onChange={(table) =>
            setRun((current) => ({ ...current, editableTable: table }))
          }
        />
      )}

      {validationRequest && run.steps.validation.status !== "idle" && (
        <ValidationStep
          request={validationRequest}
          step={run.steps.validation}
          onExecute={() => void executeValidation()}
          onCancel={() => activeController.current?.abort()}
          onAcknowledge={acknowledgeWarning}
        />
      )}

      {validationRequest && run.steps.signpost.status !== "idle" && (
        <SignpostStep
          request={validationRequest}
          step={run.steps.signpost}
          table={
            (run.steps.signpost.response as CallbackBody | undefined)?.table
          }
          onExecute={() => void executeSignpost()}
          onCancel={() => activeController.current?.abort()}
        />
      )}

      {run.steps.confirmation.status !== "idle" && (
        <ConfirmationStep
          request={confirmationRequest}
          latestDetail={run.finalScenarioGroupDetail}
          step={run.steps.confirmation}
          onPrepare={() => void prepareConfirmation()}
          onConfirm={() => void executeConfirmation()}
          onCancel={() => activeController.current?.abort()}
        />
      )}

      <span className="sr-only" aria-live="polite">
        {running
          ? `${run.currentStep} 실행 중`
          : `${run.currentStep} ${run.steps[run.currentStep].status}`}
      </span>
    </section>
  );
}

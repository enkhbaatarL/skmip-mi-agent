import { useEffect, useMemo, useRef, useState } from "react";
import { Download, RotateCcw } from "lucide-react";
import type { AgentClient } from "../../api/agentClient";
import {
  runComparison,
  type JudgedVersionResult
} from "../../api/multiEventComparison";
import {
  runDeterministicChecks,
  type DeterministicCheckResult
} from "../../domain/deterministicChecks";
import type {
  ApiVersion,
  EventDetail
} from "../../domain/apiTypes";
import { buildComparisonExportBundle } from "../../domain/exportBundle";
import type { RuntimeSnapshot } from "../../domain/runtime";
import { DiagnosticsComparison } from "./DiagnosticsComparison";
import { DimensionComparison } from "./DimensionComparison";
import { ManifestSummary } from "./ManifestSummary";
import { MultiEventSelector } from "./MultiEventSelector";
import { OverviewComparison } from "./OverviewComparison";
import { RawComparison } from "./RawComparison";
import { ScenarioComparison } from "./ScenarioComparison";
import {
  createVersionStates,
  VERSION_ORDER,
  type ComparisonManifest,
  type ComparisonRunState
} from "./types";
import { VersionRunBoard } from "./VersionRunBoard";
import {
  clearComparisonRun,
  loadComparisonRun,
  restoredEvents,
  saveComparisonRun
} from "./comparisonRunStorage";

export interface ComparisonClientContext {
  client: AgentClient;
  runtime: RuntimeSnapshot;
}

interface ComparisonWorkspaceProps {
  createClient: () => ComparisonClientContext;
  onRunLockChange: (locked: boolean) => void;
}

type ResultTab = "overview" | "dimensions" | "scenarios" | "diagnostics" | "raw";

const RESULT_TABS: Array<{ id: ResultTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "dimensions", label: "Dimensions" },
  { id: "scenarios", label: "Scenarios" },
  { id: "diagnostics", label: "Diagnostics" },
  { id: "raw", label: "Raw" }
];

function createWorkspaceRunId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `comparison-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function eventSnapshot(event: EventDetail): EventDetail {
  return typeof structuredClone === "function"
    ? structuredClone(event)
    : (JSON.parse(JSON.stringify(event)) as EventDetail);
}

function resultError(result: JudgedVersionResult): string | undefined {
  if (result.integrityIssues.length > 0) {
    return result.integrityIssues.join(" · ");
  }
  if (result.status === "unknown") {
    return (
      result.record.error ??
      "응답을 확인하지 못했습니다. 서버 작업 완료 가능성이 있어 자동 재시도하지 않습니다."
    );
  }
  if (result.data?.status === "error") return result.data.message;
  return result.record.error;
}

function emptyChecks(): Record<ApiVersion, DeterministicCheckResult[]> {
  return { v2: [], v3: [], v4: [] };
}

export function ComparisonWorkspace({
  createClient,
  onRunLockChange
}: ComparisonWorkspaceProps) {
  const [restoredRun] = useState(loadComparisonRun);
  const [selectedEvents, setSelectedEvents] = useState<EventDetail[]>(() =>
    restoredEvents(restoredRun)
  );
  const [run, setRun] = useState<ComparisonRunState | undefined>(restoredRun);
  const [activeTab, setActiveTab] = useState<ResultTab>("overview");
  const controllers = useRef<Partial<Record<ApiVersion, AbortController>>>({});

  const clientContextResult = useMemo(() => {
    try {
      return { context: createClient(), error: "" };
    } catch (error) {
      return {
        context: undefined,
        error:
          error instanceof Error ? error.message : "Runtime 설정을 확인하세요."
      };
    }
  }, [createClient]);
  const context = clientContextResult.context;
  const inputsLocked = Boolean(run);
  const comparisonRunLocked = Boolean(run?.startedAt && !run.completedAt);
  const v4Waiting =
    Boolean(run) &&
    run?.versions.v4.status === "ready" &&
    (run.versions.v2.status === "running" ||
      run.versions.v3.status === "running" ||
      run.versions.v2.status === "ready" ||
      run.versions.v3.status === "ready");
  const selectedIds = selectedEvents.map((event) => event.miEventId);
  const canExecute =
    Boolean(context) &&
    selectedIds.length >= 1 &&
    selectedIds.length <= 5 &&
    new Set(selectedIds).size === selectedIds.length;

  useEffect(() => {
    onRunLockChange(comparisonRunLocked);
  }, [comparisonRunLocked, onRunLockChange]);

  useEffect(() => {
    if (run) saveComparisonRun(run);
  }, [run]);

  useEffect(
    () => () => {
      Object.values(controllers.current).forEach((controller) =>
        controller?.abort()
      );
      onRunLockChange(false);
    },
    [onRunLockChange]
  );

  async function executeComparison() {
    if (!context || !canExecute || run) return;
    const runId = createWorkspaceRunId();
    const startedAt = new Date().toISOString();
    const manifest: ComparisonManifest = {
      runId,
      createdAt: startedAt,
      agentBaseUrl: context.runtime.agentBaseUrl,
      userId: context.runtime.userId,
      timeoutMs: context.runtime.timeoutMs,
      miEventIds: [...selectedIds],
      selectedEvents: selectedEvents.map((event) => ({
        miEventId: event.miEventId,
        detailStatus: "success",
        event: eventSnapshot(event)
      }))
    };
    const initialRun: ComparisonRunState = {
      runId,
      runtime: context.runtime,
      manifest,
      versions: createVersionStates(),
      checks: emptyChecks(),
      calls: [],
      startedAt
    };
    setRun(initialRun);
    setActiveTab("overview");

    const runControllers = {
      v2: new AbortController(),
      v3: new AbortController(),
      v4: new AbortController()
    };
    controllers.current = runControllers;

    await runComparison(
      context.client,
      manifest,
      {
        onVersionStart(version, request, versionStartedAt) {
          setRun((current) =>
            current
              ? {
                  ...current,
                  versions: {
                    ...current.versions,
                    [version]: {
                      ...current.versions[version],
                      status: "running",
                      request,
                      startedAt: versionStartedAt
                    }
                  }
                }
              : current
          );
        },
        onVersionSettled(version, result) {
          const finishedAt = result.record.finishedAt;
          const checks = runDeterministicChecks(
            version,
            result.data?.data ?? undefined,
            manifest
          );
          setRun((current) =>
            current
              ? {
                  ...current,
                  versions: {
                    ...current.versions,
                    [version]: {
                      ...current.versions[version],
                      status: result.status,
                      request: result.request,
                      response: result.data,
                      call: result.record,
                      finishedAt,
                      elapsedMs: result.record.elapsedMs,
                      integrityIssues: result.integrityIssues,
                      error: resultError(result)
                    }
                  },
                  checks: { ...current.checks, [version]: checks },
                  calls: [...current.calls, result.record]
                }
              : current
          );
        },
        onVersionRejected(version, error) {
          const message =
            error instanceof Error ? error.message : "Version 실행이 중단되었습니다.";
          setRun((current) =>
            current
              ? {
                  ...current,
                  versions: {
                    ...current.versions,
                    [version]: {
                      ...current.versions[version],
                      status: "error",
                      finishedAt: new Date().toISOString(),
                      error: message
                    }
                  }
                }
              : current
          );
        }
      },
      {
        v2: runControllers.v2.signal,
        v3: runControllers.v3.signal,
        v4: runControllers.v4.signal
      }
    );
    setRun((current) =>
      current
        ? { ...current, completedAt: new Date().toISOString() }
        : current
    );
  }

  function cancelVersion(version: ApiVersion) {
    controllers.current[version]?.abort(
      new DOMException(`${version} request cancelled`, "AbortError")
    );
  }

  function downloadExport() {
    if (!run) return;
    const content = JSON.stringify(buildComparisonExportBundle(run), null, 2);
    const url = URL.createObjectURL(
      new Blob([content], { type: "application/json;charset=utf-8" })
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `comparison-${run.manifest.runId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function resetComparison() {
    if (!run?.completedAt) return;
    controllers.current = {};
    clearComparisonRun();
    setRun(undefined);
    setActiveTab("overview");
  }

  if (!context) {
    return (
      <section className="comparison-workspace">
        <div className="callout error" role="alert">
          Runtime 설정 오류: {clientContextResult.error}
        </div>
      </section>
    );
  }

  return (
    <section
      className="comparison-workspace"
      aria-labelledby="comparison-workspace-title"
    >
      <header className="comparison-workspace-header">
        <div>
          <p className="eyebrow">Workspace B</p>
          <h2 id="comparison-workspace-title">v2/v3/v4 다중 Event 비교</h2>
          <p>
            동일한 Event 순서로 v2, v3, v4를 각각 한 번씩 순차 실행합니다.
          </p>
        </div>
        {run?.completedAt && (
          <div className="comparison-header-actions">
            <button className="button secondary" type="button" onClick={downloadExport}>
              <Download aria-hidden="true" size={17} />
              Comparison JSON
            </button>
            <button className="button quiet" type="button" onClick={resetComparison}>
              <RotateCcw aria-hidden="true" size={17} />
              새 비교
            </button>
          </div>
        )}
      </header>

      <MultiEventSelector
        client={context.client}
        selectedEvents={selectedEvents}
        locked={inputsLocked}
        onChange={setSelectedEvents}
      />
      <ManifestSummary
        runtime={run?.runtime ?? context.runtime}
        selectedEvents={selectedEvents}
        locked={inputsLocked}
        canExecute={canExecute}
        onExecute={() => void executeComparison()}
      />

      {run && (
        <>
          <VersionRunBoard
            versions={run.versions}
            v4Waiting={v4Waiting}
            checks={run.checks}
            onCancel={cancelVersion}
          />
          <section className="comparison-results" aria-labelledby="comparison-results-title">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">3. 비교 결과</p>
                <h2 id="comparison-results-title">Version Comparison</h2>
              </div>
            </div>
            <nav className="result-tabs" role="tablist" aria-label="비교 결과">
              {RESULT_TABS.map((tab) => (
                <button
                  type="button"
                  role="tab"
                  key={tab.id}
                  aria-selected={activeTab === tab.id}
                  aria-controls={`comparison-result-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
            <div
              className="comparison-result-panel"
              id={`comparison-result-${activeTab}`}
              role="tabpanel"
            >
              {activeTab === "overview" && (
                <OverviewComparison
                  versions={run.versions}
                  checks={run.checks}
                  complete={Boolean(run.completedAt)}
                />
              )}
              {activeTab === "dimensions" && (
                <DimensionComparison versions={run.versions} />
              )}
              {activeTab === "scenarios" && (
                <ScenarioComparison
                  versions={run.versions}
                  manifest={run.manifest}
                />
              )}
              {activeTab === "diagnostics" && (
                <DiagnosticsComparison versions={run.versions} />
              )}
              {activeTab === "raw" && (
                <RawComparison versions={run.versions} />
              )}
            </div>
          </section>
        </>
      )}
    </section>
  );
}

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  Bell,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Edit3,
  MoreVertical,
  Plus,
  RefreshCcw,
  Search,
  Send,
  Sparkles,
  Trash2
} from "lucide-react";
import {
  buildConfirmationBody,
  buildCreateBody,
  buildSignpostBody,
  buildValidationBody,
  createScenarioGroup,
  deleteScenarioGroup,
  fetchEventDetail,
  fetchScenarioGroupDetail,
  listEvents,
  listScenarioGroups,
  openRunEvents,
  requestConfirmation,
  requestSignposts,
  requestValidation
} from "./api";
import { initialDesignModel, seedEvents } from "./lib/seed";
import { mergeDetailIntoModel, pickAgentStage, pickAgentStatus, pickRunId, pickScenarioGroupId } from "./lib/normalizer";
import type {
  EventItem,
  RunLifecycle,
  RunState,
  RuntimeConfig,
  ScenarioDesignModel,
  ScenarioGroupListRow,
  TimelineEvent,
  ScenarioRow
} from "./types";

type Workspace = "events" | "design-step-1" | "design-step-2" | "detail";
type TopTab = "events" | "groups";
type DetailTab = "summary" | "assumptions" | "prices" | "scenario";

const DEFAULT_AGENT_BASE_URL = "http://localhost:8000";
const DEFAULT_RUNTIME: RuntimeConfig = {
  agentBaseUrl: DEFAULT_AGENT_BASE_URL,
  miEventId: "12",
  userId: "10603",
  runId: "",
  scenarioGroupId: ""
};
const selectValues = ["전혀 없음", "낮음", "0%", "50%", "100%", "급차질-급회복", "급손상-장기재건", "1개월 이하", "6개월", "1년 초과", "종료 미정"];

function readSaved<T>(key: string, fallback: T): T {
  try {
    const saved = localStorage.getItem(key);
    return saved ? (JSON.parse(saved) as T) : fallback;
  } catch {
    return fallback;
  }
}

function nowId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function timeline(type: TimelineEvent["type"], title: string, payload: unknown): TimelineEvent {
  return {
    id: nowId(type),
    at: new Date().toISOString(),
    type,
    title,
    payload
  };
}

function parseSsePayload(event: MessageEvent) {
  try {
    return JSON.parse(event.data);
  } catch {
    return { raw: event.data };
  }
}

function readPayloadField(payload: unknown, field: "result" | "message" | "reason"): string {
  if (!payload || typeof payload !== "object") return "";
  const record = payload as Record<string, unknown>;
  const direct = record[field];
  if (typeof direct === "string" || typeof direct === "number" || typeof direct === "boolean") return String(direct);
  return readPayloadField(record.payload, field) || readPayloadField(record.data, field);
}

export function App() {
  const [runtime, setRuntime] = useState<RuntimeConfig>(() =>
    readSaved("backoffice.runtime", DEFAULT_RUNTIME)
  );
  const [runState, setRunState] = useState<RunState>(() => readSaved<RunState>("backoffice.runState", { lifecycle: "idle", agentStatus: "-", agentStage: "-" }));
  const [workspace, setWorkspace] = useState<Workspace>(() => readSaved<Workspace>("backoffice.workspace", "events"));
  const [topTab, setTopTab] = useState<TopTab>("events");
  const [detailTab, setDetailTab] = useState<DetailTab>("summary");
  const [selectedScenarioId, setSelectedScenarioId] = useState(initialDesignModel.rows[0]?.localId ?? "");
  const [model, setModel] = useState<ScenarioDesignModel>(() => readSaved("backoffice.model", initialDesignModel));
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([
    timeline("local", "Seed model loaded", initialDesignModel)
  ]);
  const [rawSelection, setRawSelection] = useState<TimelineEvent["type"] | "all">("all");
  const [pendingAction, setPendingAction] = useState<string>("");
  const [validation, setValidation] = useState<{ state: "idle" | "waiting" | "warning" | "success"; message: string; recommendation: string }>({
    state: "idle",
    message: "",
    recommendation: ""
  });
  const [error, setError] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    localStorage.setItem("backoffice.runtime", JSON.stringify(runtime));
  }, [runtime]);

  useEffect(() => {
    localStorage.setItem("backoffice.runState", JSON.stringify(runState));
  }, [runState]);

  useEffect(() => {
    localStorage.setItem("backoffice.workspace", JSON.stringify(workspace));
  }, [workspace]);

  useEffect(() => {
    localStorage.setItem("backoffice.model", JSON.stringify(model));
  }, [model]);

  useEffect(() => {
    if (!runtime.runId) return;
    eventSourceRef.current?.close();
    const source = openRunEvents(runtime.runId);
    eventSourceRef.current = source;
    const onAnyEvent = (event: MessageEvent) => {
      const payload = parseSsePayload(event);
      setTimelineEvents((items) => [timeline(event.type as TimelineEvent["type"], `SSE ${event.type}`, payload), ...items]);
      if (event.type === "detail_refreshed" || event.type === "callback" || event.type === "normalized_model_updated") {
        setModel((current) => mergeDetailIntoModel(current, payload));
      }
      const callbackType = payload && typeof payload === "object" ? String((payload as Record<string, unknown>).callbackType || "") : "";
      if (event.type === "validation_result" || callbackType === "validation") {
        const result = readPayloadField(payload, "result");
        const message = readPayloadField(payload, "message") || readPayloadField(payload, "reason") || "callback 결과를 확인하세요.";
        if (result.toLowerCase() === "failure") {
          setValidation({ state: "warning", message, recommendation: "Raw JSON에서 실패 상세를 확인하고 수정하세요." });
          setRunState((current) => ({ ...current, lifecycle: "failed" }));
        } else {
          setValidation({ state: "success", message, recommendation: "검토 완료로 Step 2에 진입할 수 있습니다." });
          setRunState((current) => ({ ...current, lifecycle: "scenario_validated" }));
        }
      }
    };
    ["accepted", "callback", "detail_refreshed", "validation_result", "normalized_model_updated", "error"].forEach((type) =>
      source.addEventListener(type, onAnyEvent)
    );
    source.onerror = () => {
      setTimelineEvents((items) => [timeline("error", "SSE disconnected or unavailable", { runId: runtime.runId }), ...items]);
    };
    return () => source.close();
  }, [runtime.runId]);

  const selectedScenario = useMemo(
    () => model.rows.find((row) => row.localId === selectedScenarioId) ?? model.rows[0],
    [model.rows, selectedScenarioId]
  );

  const visibleRawEvents = rawSelection === "all" ? timelineEvents : timelineEvents.filter((item) => item.type === rawSelection);

  function patchRuntime(patch: Partial<RuntimeConfig>) {
    setRuntime((current) => ({ ...current, ...patch }));
  }

  function addTimeline(type: TimelineEvent["type"], title: string, payload: unknown) {
    setTimelineEvents((items) => [timeline(type, title, payload), ...items]);
  }

  async function runAction<T>(name: string, lifecycle: RunLifecycle, action: () => Promise<T>, onSuccess?: (payload: T) => void) {
    setPendingAction(name);
    setError("");
    setRunState((current) => ({ ...current, lifecycle }));
    try {
      const payload = await action();
      onSuccess?.(payload);
      return payload;
    } catch (caught) {
      const body = caught && typeof caught === "object" && "body" in caught ? (caught as { body: unknown }).body : caught;
      setError(caught instanceof Error ? caught.message : "Request failed");
      addTimeline("error", `${name} failed`, body);
      setRunState((current) => ({ ...current, lifecycle: "failed" }));
      return undefined;
    } finally {
      setPendingAction("");
    }
  }

  function applyAccepted(payload: unknown) {
    const record = payload as Record<string, unknown>;
    const runId = pickRunId(record) || runtime.runId || `local-${Date.now()}`;
    const scenarioGroupId = pickScenarioGroupId(record);
    const agentStatus = pickAgentStatus(record) || "creating";
    const agentStage = pickAgentStage(record) || "ready";
    const lifecycle = lifecycleFromAgentStage(agentStatus, agentStage);
    patchRuntime({ runId, scenarioGroupId });
    setRunState({
      lifecycle,
      agentStatus,
      agentStage
    });
    setModel((current) => mergeDetailIntoModel(current, payload));
    addTimeline("accepted", "Create scenario draft accepted", payload);
    setWorkspace(workspaceFromAgentStage(agentStatus, agentStage));
  }

  async function handleCreate(overrides: Partial<RuntimeConfig> = {}) {
    const createRuntime = { ...runtime, ...overrides };
    const body = buildCreateBody(createRuntime.agentBaseUrl, createRuntime.miEventId, createRuntime.userId);
    addTimeline("request_body", "Create scenario draft request", body);
    await runAction("Create scenario draft", "creating", () => createScenarioGroup(body), applyAccepted);
  }

  async function handleStartFromEvent(event: EventItem) {
    if (runtime.runId) {
      const replace = window.confirm("진행 중인 run이 있습니다. 현재 로컬 draft를 초기화하고 새 run을 시작할까요?");
      if (!replace) return;
      setValidation({ state: "idle", message: "", recommendation: "" });
      setTimelineEvents((items) => [timeline("local", "Existing run replaced from Event List", { previousRunId: runtime.runId }), ...items]);
    }
    const nextRuntime = { miEventId: String(event.miEventId), runId: "", scenarioGroupId: "" };
    patchRuntime(nextRuntime);
    setModel({ ...initialDesignModel, baseEvent: event });
    await handleCreate(nextRuntime);
  }

  async function handleRefresh() {
    if (!runtime.scenarioGroupId) return;
    await runAction(
      "Refresh detail",
      runState.lifecycle,
      () => fetchScenarioGroupDetail(runtime.scenarioGroupId, runtime.agentBaseUrl, true),
      (payload) => {
        setModel((current) => mergeDetailIntoModel(current, payload));
        addTimeline("detail_refreshed", "Scenario group detail refreshed", payload);
        setRunState((current) => ({ ...current, lifecycle: "scenario_created" }));
      }
    );
  }

  async function handleOpenScenarioGroupDetail(row: ScenarioGroupListRow) {
    const scenarioGroupId = String(row.scenarioGroupId);
    patchRuntime({
      scenarioGroupId,
      runId: row.latestRunId || runtime.runId,
      miEventId: row.miEventId ? String(row.miEventId) : runtime.miEventId
    });
    await runAction(
      "Open scenario group detail",
      runState.lifecycle,
      () => fetchScenarioGroupDetail(scenarioGroupId, runtime.agentBaseUrl, row.deleted),
      (payload) => {
        setModel((current) => mergeDetailIntoModel(current, payload));
        addTimeline("detail_refreshed", "Scenario group detail opened from list", payload);
        setWorkspace("detail");
        setTopTab("groups");
      }
    );
  }

  async function handleValidation() {
    if (!runtime.runId) {
      setValidation({
        state: "warning",
        message: "runId가 없어 실제 validation 요청을 보낼 수 없습니다.",
        recommendation: "Create Scenario Draft 후 다시 요청하세요."
      });
      return;
    }
    const body = buildValidationBody(runtime.userId, model);
    addTimeline("request_body", "Validation request body", body);
    await runAction(
      "Validate branch criteria",
      "validating",
      () => requestValidation(runtime.runId, body),
      (payload) => {
        addTimeline("accepted", "Validation accepted", payload);
        setValidation({
          state: "waiting",
          message: "변경사항 검토 요청이 접수되었습니다.",
          recommendation: "validation callback을 기다리는 중입니다."
        });
        setRunState((current) => ({ ...current, lifecycle: "validation_waiting_callback" }));
      }
    );
  }

  async function handleSignposts() {
    if (!runtime.runId) return;
    const body = buildSignpostBody(runtime.userId, model);
    addTimeline("request_body", "Signpost generation request body", body);
    await runAction(
      "Create signposts",
      "creating_signposts",
      () => requestSignposts(runtime.runId, body),
      (payload) => {
        addTimeline("accepted", "Signpost generation accepted", payload);
        setRunState((current) => ({ ...current, lifecycle: "signpost_waiting_callback" }));
      }
    );
  }

  async function handleConfirmation() {
    if (!runtime.runId) return;
    const body = buildConfirmationBody(runtime.userId, model);
    addTimeline("request_body", "Confirmation request body", body);
    await runAction(
      "Confirm scenario group",
      "confirming",
      () => requestConfirmation(runtime.runId, body),
      (payload) => {
        addTimeline("accepted", "Confirmation accepted", payload);
        setRunState((current) => ({ ...current, lifecycle: "confirmed" }));
        setWorkspace("detail");
      }
    );
  }

  function updateRow(localId: string, patch: Partial<ScenarioRow>) {
    setModel((current) => ({
      ...current,
      rows: current.rows.map((row) => (row.localId === localId ? { ...row, ...patch, edited: true } : row))
    }));
  }

  function updateCell(localId: string, key: string, value: string) {
    setModel((current) => ({
      ...current,
      rows: current.rows.map((row) =>
        row.localId === localId ? { ...row, cells: { ...row.cells, [key]: value }, edited: true } : row
      )
    }));
  }

  function addRow() {
    const cells = Object.fromEntries(model.headers.map((header) => [header.key, ""]));
    const next: ScenarioRow = {
      localId: nowId("scenario"),
      displayOrder: model.rows.length + 1,
      title: "새 시나리오",
      narrative: "",
      cells,
      probability: "0",
      baselineYn: "N",
      status: "Draft",
      signposts: [],
      edited: true
    };
    setModel((current) => ({ ...current, rows: [...current.rows, next] }));
  }

  function deleteRow(localId: string) {
    setModel((current) => ({
      ...current,
      rows: current.rows
        .filter((row) => row.localId !== localId)
        .map((row, index) => ({ ...row, displayOrder: index + 1, edited: true }))
    }));
  }

  function resetRuntimePersistence() {
    localStorage.removeItem("backoffice.model");
    localStorage.removeItem("backoffice.workspace");
    localStorage.removeItem("backoffice.runState");
    localStorage.removeItem("backoffice.runtime");
  }

  function resetLocal() {
    resetRuntimePersistence();
    setModel(initialDesignModel);
    setWorkspace("events");
    setTopTab("events");
    setValidation({ state: "idle", message: "", recommendation: "" });
    setRunState({ lifecycle: "idle", agentStatus: "-", agentStage: "-" });
    setRuntime(DEFAULT_RUNTIME);
    addTimeline("local", "Local screen state reset", {});
  }

  return (
    <div className="app-shell">
      <Header runtime={runtime} />
      <main className="page">
        <RuntimeBar
          runtime={runtime}
          runState={runState}
          pendingAction={pendingAction}
          onPatch={patchRuntime}
          onCreate={handleCreate}
          onRefresh={handleRefresh}
          onReset={resetLocal}
        />
        <StatusStrip lifecycle={runState.lifecycle} agentStatus={runState.agentStatus} agentStage={runState.agentStage} />
        {error ? <Callout tone="error" title="Agent/API 요청 실패" message={error} action="Raw JSON 패널에서 상세를 확인하세요." /> : null}

        {workspace === "events" ? (
          <EventWorkspace
            topTab={topTab}
            onTopTab={setTopTab}
            runtime={runtime}
            onSelectEvent={(event) => {
              patchRuntime({ miEventId: String(event.miEventId) });
              setModel((current) => ({ ...current, baseEvent: event }));
            }}
            onStartEvent={handleStartFromEvent}
            onOpenGroupDetail={handleOpenScenarioGroupDetail}
            onTimeline={addTimeline}
          />
        ) : null}

        {workspace === "design-step-1" ? (
          <StepOne
            model={model}
            validation={validation}
            pendingAction={pendingAction}
            onBack={() => setWorkspace("events")}
            onUpdateRow={updateRow}
            onUpdateCell={updateCell}
            onAddRow={addRow}
            onDeleteRow={deleteRow}
            onValidate={handleValidation}
            onComplete={() => {
              setRunState((current) => ({ ...current, lifecycle: "scenario_validated" }));
              setWorkspace("design-step-2");
            }}
            onReset={() => setModel(initialDesignModel)}
          />
        ) : null}

        {workspace === "design-step-2" ? (
          <StepTwo
            model={model}
            pendingAction={pendingAction}
            onBack={() => setWorkspace("design-step-1")}
            onModel={setModel}
            onUpdateRow={updateRow}
            onSignposts={handleSignposts}
            onConfirm={handleConfirmation}
            onReset={() => setModel(initialDesignModel)}
          />
        ) : null}

        {workspace === "detail" ? (
          <DetailWorkspace
            model={model}
            detailTab={detailTab}
            selectedScenario={selectedScenario}
            selectedScenarioId={selectedScenarioId}
            onDetailTab={setDetailTab}
            onSelectedScenario={setSelectedScenarioId}
            onBack={() => {
              setTopTab("groups");
              setWorkspace("events");
            }}
          />
        ) : null}

        <Inspector events={visibleRawEvents} rawSelection={rawSelection} onRawSelection={setRawSelection} />
      </main>
    </div>
  );
}

function Header({ runtime }: { runtime: RuntimeConfig }) {
  return (
    <header>
      <div className="utility-bar">
        <strong>SK gas</strong>
        <div>
          <span>Notice</span>
          <span>Help Center</span>
        </div>
      </div>
      <div className="main-header">
        <div className="brand-mark">MI</div>
        <strong>AI Market Insights</strong>
        <nav>
          <button>Dashboard</button>
          <button className="active">AI Forecast</button>
          <button>Market Data</button>
          <button>Position Play</button>
        </nav>
        <div className="header-tools">
          <Bell size={18} />
          <span className="divider" />
          <span className="avatar">{runtime.userId.slice(-1) || "U"}</span>
          <span>{runtime.userId || "user"}</span>
          <ChevronDown size={16} />
        </div>
      </div>
    </header>
  );
}

function RuntimeBar({
  runtime,
  runState,
  pendingAction,
  onPatch,
  onCreate,
  onRefresh,
  onReset
}: {
  runtime: RuntimeConfig;
  runState: RunState;
  pendingAction: string;
  onPatch: (patch: Partial<RuntimeConfig>) => void;
  onCreate: () => void;
  onRefresh: () => void;
  onReset: () => void;
}) {
  return (
    <section className="runtime-bar" aria-label="Runtime controls">
      <label>
        Agent Base URL
        <input value={runtime.agentBaseUrl} onChange={(event) => onPatch({ agentBaseUrl: event.target.value })} />
      </label>
      <label>
        miEventId
        <input value={runtime.miEventId} onChange={(event) => onPatch({ miEventId: event.target.value })} />
      </label>
      <label>
        userId
        <input value={runtime.userId} onChange={(event) => onPatch({ userId: event.target.value })} />
      </label>
      <label>
        runId
        <input value={runtime.runId} readOnly />
      </label>
      <label>
        scenarioGroupId
        <input value={runtime.scenarioGroupId} readOnly />
      </label>
      <button className="button dark" disabled={!!pendingAction || !runtime.agentBaseUrl || !runtime.miEventId || !runtime.userId} onClick={onCreate}>
        <Sparkles size={16} /> Create Scenario Draft
      </button>
      <button className="button secondary" disabled={!runtime.scenarioGroupId || !!pendingAction} onClick={onRefresh}>
        <RefreshCcw size={16} /> Refresh
      </button>
      <button className="button secondary" onClick={onReset}>
        Reset
      </button>
      <span className={`state-pill ${runState.lifecycle}`}>{pendingAction || runState.lifecycle}</span>
    </section>
  );
}

function StatusStrip({ lifecycle, agentStatus, agentStage }: { lifecycle: RunLifecycle; agentStatus: string; agentStage: string }) {
  const steps = [
    "Select Event",
    "Create Scenario Draft",
    "Callback: Generation",
    "Review Branch Criteria",
    "Validate Branch Criteria",
    "Callback: Validation",
    "Review One-view",
    "Create Signposts",
    "Callback: Signposts",
    "Confirm Scenario Group"
  ];
  const activeIndex = lifecycle === "idle" ? 0 : lifecycle === "confirmed" ? 9 : lifecycle.includes("signpost") ? 8 : lifecycle.includes("valid") ? 5 : lifecycle.includes("scenario") ? 3 : 2;
  return (
    <section className="status-strip">
      <div className="status-meta">
        <strong>Local lifecycle</strong>
        <span>{lifecycle}</span>
        <strong>Agent status</strong>
        <span>{agentStatus}</span>
        <strong>Agent stage</strong>
        <span>{agentStage}</span>
      </div>
      <div className="workflow-steps">
        {steps.map((step, index) => (
          <span className={index < activeIndex ? "done" : index === activeIndex ? "current" : ""} key={step}>
            {index < activeIndex ? <Check size={12} /> : index + 1}
            {step}
          </span>
        ))}
      </div>
    </section>
  );
}

function apiEventToItem(row: {
  miEventId: number;
  title: string;
  oneLineSummary?: string;
  eventTime?: string;
  occurredAt?: string;
  category?: string;
  eventTypeL1?: { id?: number | null; code?: string; label?: string };
  eventTypeL2?: { id?: number | null; code?: string; label?: string };
  newYn?: string;
  scenarioSuggestYn?: string;
  signalReason?: string | null;
  scenarioSuggestReason?: string | null;
  relatedScenarioGroup?: EventItem["relatedScenarioGroup"];
  scenarioActionState?: EventItem["scenarioActionState"];
}): EventItem {
  return {
    miEventId: row.miEventId,
    title: row.title,
    summary: row.oneLineSummary,
    eventTime: row.eventTime || row.occurredAt || "-",
    category: row.category || row.eventTypeL1?.label || "-",
    status: row.newYn === "N" ? "갱신" : "신규",
    recommended: row.scenarioSuggestYn === "Y",
    eventTypeL1: {
      id: row.eventTypeL1?.id,
      code: row.eventTypeL1?.code || "",
      label: row.eventTypeL1?.label || ""
    },
    eventTypeL2: {
      id: row.eventTypeL2?.id,
      code: row.eventTypeL2?.code || "",
      label: row.eventTypeL2?.label || ""
    },
    signalReason: row.signalReason,
    scenarioSuggestReason: row.scenarioSuggestReason,
    relatedScenarioGroup: row.relatedScenarioGroup,
    scenarioActionState: row.scenarioActionState
  };
}

function lifecycleFromAgentStage(status: string, stage: string): RunLifecycle {
  if (status === "created" && stage === "completed") return "confirmed";
  if (stage === "signpost_created") return "signpost_created";
  if (stage === "scenario_validated") return "scenario_validated";
  if (stage === "scenario_created") return "scenario_created";
  return "generation_waiting_callback";
}

function workspaceFromAgentStage(status: string, stage: string): Workspace {
  if (status === "created" && stage === "completed") return "detail";
  if (stage === "scenario_validated" || stage === "signpost_created") return "design-step-2";
  return "design-step-1";
}

function EventWorkspace({
  topTab,
  runtime,
  onTopTab,
  onSelectEvent,
  onStartEvent,
  onOpenGroupDetail,
  onTimeline
}: {
  topTab: TopTab;
  runtime: RuntimeConfig;
  onTopTab: (tab: TopTab) => void;
  onSelectEvent: (event: EventItem) => void;
  onStartEvent: (event: EventItem) => void;
  onOpenGroupDetail: (row: ScenarioGroupListRow) => void;
  onTimeline: (type: TimelineEvent["type"], title: string, payload: unknown) => void;
}) {
  const [recommendedOnly, setRecommendedOnly] = useState(false);
  const [status, setStatus] = useState("전체");
  const [category, setCategory] = useState("all");
  const [keyword, setKeyword] = useState("");
  const [eventSort, setEventSort] = useState("latest");
  const [eventPage, setEventPage] = useState(1);
  const [events, setEvents] = useState<EventItem[]>(seedEvents);
  const [eventMeta, setEventMeta] = useState("seed fallback");
  const [eventHasPrevious, setEventHasPrevious] = useState(false);
  const [eventHasNext, setEventHasNext] = useState(false);
  const [eventLoading, setEventLoading] = useState(false);
  const [eventError, setEventError] = useState("");
  const [eventDetail, setEventDetail] = useState<Record<string, any> | null>(null);
  const [groupKeyword, setGroupKeyword] = useState("");
  const [groupStatus, setGroupStatus] = useState("");
  const [groupStage, setGroupStage] = useState("");
  const [groupSort, setGroupSort] = useState("latest");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [groups, setGroups] = useState<ScenarioGroupListRow[]>([]);
  const [groupMeta, setGroupMeta] = useState("");
  const [groupLoading, setGroupLoading] = useState(false);
  const [groupError, setGroupError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ScenarioGroupListRow | null>(null);
  const [deleteAuthorization, setDeleteAuthorization] = useState("backoffice-local-token");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const filtered = events.filter(
    (event) =>
      (!recommendedOnly || event.recommended) &&
      (status === "전체" || event.status === status) &&
      (category === "all" || event.category === category) &&
      (!keyword.trim() || event.title.toLowerCase().includes(keyword.trim().toLowerCase()))
  );
  async function loadEvents(page = eventPage) {
    setEventLoading(true);
    setEventError("");
    try {
      const response = await listEvents({
        agentBaseUrl: runtime.agentBaseUrl,
        keyword,
        status: status === "신규" ? "new" : status === "갱신" ? "updated" : "",
        recommendedOnly,
        sort: eventSort,
        page,
        pageSize: 20
      });
      const apiEvents = response.rows.map(apiEventToItem);
      setEvents(apiEvents.length ? apiEvents : seedEvents);
      setEventMeta(`${response.meta.source}${response.meta.fallbackReason ? ` · ${response.meta.fallbackReason}` : ""}`);
      setEventPage(response.pagination.page);
      setEventHasPrevious(response.pagination.hasPrevious);
      setEventHasNext(response.pagination.hasNext);
      onTimeline("detail_refreshed", "Event List loaded", response);
    } catch (caught) {
      const body = caught && typeof caught === "object" && "body" in caught ? (caught as { body: unknown }).body : caught;
      setEvents(seedEvents);
      setEventMeta("seed fallback");
      setEventError(caught instanceof Error ? caught.message : "Event List load failed");
      onTimeline("error", "Event List load failed", body);
    } finally {
      setEventLoading(false);
    }
  }
  async function openEventDetail(event: EventItem) {
    onSelectEvent(event);
    try {
      const response = await fetchEventDetail(event.miEventId, runtime.agentBaseUrl);
      setEventDetail(response as Record<string, any>);
      onTimeline("detail_refreshed", `Event ${event.miEventId} detail loaded`, response);
    } catch (caught) {
      const body = caught && typeof caught === "object" && "body" in caught ? (caught as { body: unknown }).body : caught;
      onTimeline("error", `Event ${event.miEventId} detail failed`, body);
    }
  }
  async function loadGroups() {
    setGroupLoading(true);
    setGroupError("");
    try {
      const response = await listScenarioGroups({
        agentBaseUrl: runtime.agentBaseUrl,
        includeDeleted,
        keyword: groupKeyword,
        status: groupStatus,
        stage: groupStage,
        miEventId: "",
        sort: groupSort
      });
      setGroups(response.rows);
      setGroupMeta(`${response.meta.source} · ${response.meta.returned}/${response.meta.total}`);
      onTimeline("detail_refreshed", "Scenario Group List loaded", response);
    } catch (caught) {
      const body = caught && typeof caught === "object" && "body" in caught ? (caught as { body: unknown }).body : caught;
      setGroupError(caught instanceof Error ? caught.message : "Scenario Group List load failed");
      onTimeline("error", "Scenario Group List load failed", body);
    } finally {
      setGroupLoading(false);
    }
  }
  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleteBusy(true);
    setGroupError("");
    const body = {
      agentBaseUrl: runtime.agentBaseUrl,
      userId: Number(runtime.userId),
      deleteAuthorization
    };
    onTimeline("request_body", `Soft delete ${deleteTarget.scenarioGroupId} request`, body);
    try {
      const response = await deleteScenarioGroup(String(deleteTarget.scenarioGroupId), body);
      onTimeline("detail_refreshed", `Soft delete ${deleteTarget.scenarioGroupId} response`, response);
      setGroups((current) =>
        includeDeleted
          ? current.map((row) => (row.scenarioGroupId === deleteTarget.scenarioGroupId ? { ...row, deleted: true, delYn: "Y" } : row))
          : current.filter((row) => row.scenarioGroupId !== deleteTarget.scenarioGroupId)
      );
      setDeleteTarget(null);
    } catch (caught) {
      const body = caught && typeof caught === "object" && "body" in caught ? (caught as { body: unknown }).body : caught;
      setGroupError(caught instanceof Error ? caught.message : "Soft delete failed");
      onTimeline("error", `Soft delete ${deleteTarget.scenarioGroupId} failed`, body);
    } finally {
      setDeleteBusy(false);
    }
  }
  useEffect(() => {
    if (topTab === "groups") {
      void loadGroups();
    }
  }, [topTab, includeDeleted, groupSort]);
  useEffect(() => {
    if (topTab === "events") {
      void loadEvents(1);
    }
  }, [topTab, eventSort]);
  return (
    <section className="workspace">
      <div className="page-heading">
        <div>
          <h1>Next-Gen MI</h1>
          <p>Event discovery and scenario group workflow console</p>
        </div>
      </div>
      <div className="tabs">
        <button className={topTab === "events" ? "active" : ""} onClick={() => onTopTab("events")}>
          Event List
        </button>
        <button className={topTab === "groups" ? "active" : ""} onClick={() => onTopTab("groups")}>
          Scenario Group List
        </button>
      </div>
      {topTab === "events" ? (
        <>
          <div className="filter-bar">
            <div className="segment">
              {["전체", "신규", "갱신"].map((item) => (
                <button key={item} className={status === item ? "active" : ""} onClick={() => setStatus(item)}>
                  {item}
                </button>
              ))}
            </div>
            <select value={category} aria-label="category" onChange={(event) => setCategory(event.target.value)}>
              <option value="all">All categories</option>
              <option>Supply</option>
              <option>Demand</option>
              <option>Geopolitical Risk</option>
            </select>
            <input type="date" defaultValue="2026-07-02" />
            <select value={eventSort} aria-label="sort" onChange={(event) => setEventSort(event.target.value)}>
              <option value="latest">Latest first</option>
              <option value="oldest">Oldest first</option>
            </select>
            <label className="toggle">
              <input type="checkbox" checked={recommendedOnly} onChange={(event) => setRecommendedOnly(event.target.checked)} />
              Recommended
            </label>
            <label className="search-box">
              <Search size={16} />
              <input placeholder="Search event name" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
            </label>
            <button className="button secondary" disabled={eventLoading} onClick={() => loadEvents(1)}>
              <Search size={16} /> Apply
            </button>
          </div>
          <div className="section-title-row compact-row">
            <p>{eventMeta}</p>
            {eventError ? <span className="error-inline">{eventError}</span> : null}
          </div>
          {eventDetail ? (
            <section className="section-block event-detail-panel">
              <div className="section-title-row">
                <div>
                  <h2>Event Detail</h2>
                  <p>{eventDetail.event?.title || eventDetail.event?.eventTitle || "Selected event"}</p>
                </div>
                <button className="icon-button" title="Close event detail" onClick={() => setEventDetail(null)}>
                  <ChevronDown size={18} />
                </button>
              </div>
              <div className="detail-grid">
                <div>
                  <h3>Metadata</h3>
                  <dl className="kv-list">
                    <div>
                      <dt>miEventId</dt>
                      <dd>{eventDetail.event?.miEventId || "-"}</dd>
                    </div>
                    <div>
                      <dt>Summary</dt>
                      <dd>{eventDetail.event?.oneLineSummary || "-"}</dd>
                    </div>
                    <div>
                      <dt>Event Type L1</dt>
                      <dd>{eventDetail.event?.eventTypeL1?.label || "-"}</dd>
                    </div>
                    <div>
                      <dt>Event Type L2</dt>
                      <dd>{eventDetail.event?.eventTypeL2?.label || "-"}</dd>
                    </div>
                    <div>
                      <dt>Related Scenario Group</dt>
                      <dd>{eventDetail.event?.relatedScenarioGroup?.scenarioGroupId || "none"}</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3>Scenario Template</h3>
                  <div className="template-list">
                    {(eventDetail.scenarioTemplate?.dimensions || []).map((dimension: Record<string, any>) => (
                      <span key={dimension.key || dimension.label} className="event-type">
                        {dimension.label || dimension.key}
                      </span>
                    ))}
                    {!(eventDetail.scenarioTemplate?.dimensions || []).length ? <span className="muted-text">No template dimensions</span> : null}
                  </div>
                </div>
              </div>
            </section>
          ) : null}
          <div className="table-wrap">
            <table className="event-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Date/Time</th>
                  <th>Category</th>
                  <th>L1</th>
                  <th>L2</th>
                  <th>Event</th>
                  <th>Scenario</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((event) => (
                  <tr key={event.miEventId} className={String(event.miEventId) === runtime.miEventId ? "selected-row" : ""} onClick={() => onSelectEvent(event)}>
                    <td>
                      <span className="badge">{event.status}</span>
                    </td>
                    <td>{event.eventTime}</td>
                    <td>{event.category}</td>
                    <td>{event.eventTypeL1?.label || "-"}</td>
                    <td>{event.eventTypeL2?.label || "-"}</td>
                    <td>
                      <button
                        className="link-button"
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation();
                          void openEventDetail(event);
                        }}
                      >
                        {event.title}
                      </button>
                      {event.summary ? <span className="event-summary">{event.summary}</span> : null}
                      {String(event.miEventId) === runtime.miEventId ? <span className="selected-note">selected</span> : null}
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label="Start scenario design"
                        title={event.scenarioActionState?.reason || event.scenarioActionState?.label || "Start scenario design"}
                        disabled={event.scenarioActionState?.disabled}
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation();
                          if (event.scenarioActionState?.type === "open_detail" && event.relatedScenarioGroup?.scenarioGroupId) {
                            onOpenGroupDetail({
                              scenarioGroupId: event.relatedScenarioGroup.scenarioGroupId,
                              title: event.relatedScenarioGroup.title || event.title,
                              baseEventTitle: event.title,
                              miEventId: event.miEventId,
                              status: event.relatedScenarioGroup.status,
                              stage: event.relatedScenarioGroup.stage,
                              scenarioCount: event.relatedScenarioGroup.scenarioCount || 0,
                              signpostCount: event.relatedScenarioGroup.signpostCount || 0,
                              deleted: Boolean(event.relatedScenarioGroup.deleted),
                              delYn: event.relatedScenarioGroup.deleted ? "Y" : "N",
                              source: "event_row"
                            });
                            return;
                          }
                          onStartEvent(event);
                        }}
                      >
                        <Sparkles size={18} />
                      </button>
                      {event.relatedScenarioGroup?.scenarioGroupId ? <span className="selected-note">SG {event.relatedScenarioGroup.scenarioGroupId}</span> : null}
                    </td>
                  </tr>
                ))}
                {!filtered.length ? (
                  <tr>
                    <td colSpan={10}>
                      <div className="empty-table-message">
                        {eventLoading ? "Event List를 불러오는 중입니다." : "조건에 맞는 이벤트가 없습니다. 필터를 조정하거나 runtime bar에서 miEventId를 직접 입력하세요."}
                      </div>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
          <div className="pagination-row">
            <button className="button secondary" disabled={eventLoading || !eventHasPrevious} onClick={() => loadEvents(eventPage - 1)}>
              Previous
            </button>
            <span>Page {eventPage}</span>
            <button className="button secondary" disabled={eventLoading || !eventHasNext} onClick={() => loadEvents(eventPage + 1)}>
              Next
            </button>
          </div>
        </>
      ) : (
        <section className="section-block">
          <div className="section-title-row">
            <div>
              <h2>Scenario Group List</h2>
              <p>{groupMeta || "GET /backoffice/api/scenario-groups"}</p>
            </div>
            <button className="icon-button" aria-label="Refresh scenario groups" title="Refresh scenario groups" disabled={groupLoading} onClick={loadGroups}>
              <RefreshCcw size={18} />
            </button>
          </div>
          <div className="filter-bar">
            <label className="search-box">
              <Search size={16} />
              <input
                placeholder="시나리오 그룹명, 이벤트명, ID로 검색"
                value={groupKeyword}
                onChange={(event) => setGroupKeyword(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void loadGroups();
                }}
              />
            </label>
            <select value={groupStatus} aria-label="scenario group status" onChange={(event) => setGroupStatus(event.target.value)}>
              <option value="">Status all</option>
              <option value="CREATED">CREATED</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="DELETED">DELETED</option>
            </select>
            <select value={groupStage} aria-label="scenario group stage" onChange={(event) => setGroupStage(event.target.value)}>
              <option value="">Stage all</option>
              <option value="GENERATION">GENERATION</option>
              <option value="VALIDATION">VALIDATION</option>
              <option value="SIGNPOST">SIGNPOST</option>
              <option value="CONFIRMATION">CONFIRMATION</option>
            </select>
            <input type="date" defaultValue="2026-07-02" aria-label="scenario group date" />
            <select value={groupSort} aria-label="scenario group sort" onChange={(event) => setGroupSort(event.target.value)}>
              <option value="latest">Latest first</option>
              <option value="oldest">Oldest first</option>
            </select>
            <label className="toggle">
              <input type="checkbox" checked={includeDeleted} onChange={(event) => setIncludeDeleted(event.target.checked)} />
              삭제 항목 포함
            </label>
            <button className="button secondary" disabled={groupLoading} onClick={loadGroups}>
              <Search size={16} /> Apply
            </button>
          </div>
          {groupError ? <Callout tone="error" title="Scenario Group List 오류" message={groupError} action="QA Inspector에서 raw error를 확인하세요." /> : null}
          <div className="table-wrap">
            <table className="event-table group-table">
              <thead>
                <tr>
                  <th>Scenario Group ID</th>
                  <th>Scenario Group명</th>
                  <th>Base Event</th>
                  <th>Status</th>
                  <th>Stage</th>
                  <th>Scenario</th>
                  <th>Signpost</th>
                  <th>Updated</th>
                  <th>삭제 상태</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((row) => (
                  <tr key={row.scenarioGroupId} className={row.deleted ? "deleted-row" : ""}>
                    <td>{row.scenarioGroupId}</td>
                    <td>
                      <strong>{row.title}</strong>
                      {row.latestRunId ? <span className="selected-note">run {row.latestRunId.slice(0, 8)}</span> : null}
                    </td>
                    <td>{row.baseEventTitle || row.miEventId || "-"}</td>
                    <td>{row.status || "-"}</td>
                    <td>{row.stage || "-"}</td>
                    <td>{row.scenarioCount}</td>
                    <td>{row.signpostCount}</td>
                    <td>{row.updatedAt ? new Date(row.updatedAt).toLocaleString() : "-"}</td>
                    <td>{row.deleted ? <span className="badge deleted-badge">삭제됨</span> : <span className="badge">정상</span>}</td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-button" aria-label="Open scenario group detail" title="Open detail" onClick={() => onOpenGroupDetail(row)}>
                          <ChevronRight size={18} />
                        </button>
                        <button
                          className="icon-button danger"
                          aria-label="Soft delete scenario group"
                          title="Soft delete"
                          disabled={row.deleted || deleteBusy}
                          onClick={() => setDeleteTarget(row)}
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!groups.length ? (
                  <tr>
                    <td colSpan={10}>
                      <div className="empty-table-message">
                        {groupLoading ? "Scenario Group List를 불러오는 중입니다." : "조건에 맞는 Scenario Group이 없습니다."}
                      </div>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
          {deleteTarget ? (
            <div className="modal-backdrop" role="dialog" aria-modal="true">
              <div className="modal">
                <h2>Scenario Group 삭제</h2>
                <dl className="confirm-list">
                  <div>
                    <dt>Scenario Group ID</dt>
                    <dd>{deleteTarget.scenarioGroupId}</dd>
                  </div>
                  <div>
                    <dt>Scenario Group명</dt>
                    <dd>{deleteTarget.title}</dd>
                  </div>
                  <div>
                    <dt>Base Event</dt>
                    <dd>{deleteTarget.baseEventTitle || deleteTarget.miEventId || "-"}</dd>
                  </div>
                </dl>
                <p>Backoffice soft-delete proxy만 호출합니다. snapshot 계열 데이터는 hard delete하지 않습니다.</p>
                <label className="labeled-textarea compact-label">
                  <span>Delete authorization</span>
                  <input value={deleteAuthorization} onChange={(event) => setDeleteAuthorization(event.target.value)} />
                </label>
                {groupError ? <Callout tone="error" title="삭제 실패" message={groupError} action="권한 값을 확인한 뒤 재시도하세요." /> : null}
                <div className="modal-actions">
                  <button className="button secondary" disabled={deleteBusy} onClick={() => setDeleteTarget(null)}>
                    취소
                  </button>
                  <button className="button danger" disabled={deleteBusy || !deleteAuthorization.trim()} onClick={confirmDelete}>
                    {deleteBusy ? "삭제 중" : "삭제"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      )}
    </section>
  );
}

function StepOne({
  model,
  validation,
  pendingAction,
  onBack,
  onUpdateRow,
  onUpdateCell,
  onAddRow,
  onDeleteRow,
  onValidate,
  onComplete,
  onReset
}: {
  model: ScenarioDesignModel;
  validation: { state: "idle" | "waiting" | "warning" | "success"; message: string; recommendation: string };
  pendingAction: string;
  onBack: () => void;
  onUpdateRow: (id: string, patch: Partial<ScenarioRow>) => void;
  onUpdateCell: (id: string, key: string, value: string) => void;
  onAddRow: () => void;
  onDeleteRow: (id: string) => void;
  onValidate: () => void;
  onComplete: () => void;
  onReset: () => void;
}) {
  const busy = pendingAction === "Validate branch criteria";
  return (
    <section className="workspace design with-bottom-bar" aria-busy={busy}>
      <BackTitle title="Scenario Design" onBack={onBack} />
      <Stepper active={1} />
      <BaseEvent event={model.baseEvent} />
      <section className="section-block">
        <div className="section-title-row">
          <div>
            <h2>분기 항목 및 분기 기준 검토</h2>
            <p>3개 이상 구성 권장</p>
          </div>
          <button className="icon-button" aria-label="Add row" title="Add row" onClick={onAddRow}>
            <Plus size={18} />
          </button>
        </div>
        <div className="table-wrap editable-wrap">
          <table className="editable-table">
            <thead>
              <tr>
                <th />
                <th>시나리오 목록</th>
                {model.headers.map((header) => (
                  <th key={header.key}>{header.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {model.rows.map((row) => (
                <tr key={row.localId} className={row.edited ? "edited" : ""}>
                  <td>
                    <button
                      className="icon-button ghost"
                      aria-label={row.baselineYn === "Y" ? "Baseline row cannot be deleted" : "Delete row"}
                      title={row.baselineYn === "Y" ? "Baseline row cannot be deleted" : "Delete row"}
                      disabled={row.baselineYn === "Y" || !!pendingAction}
                      onClick={() => onDeleteRow(row.localId)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                  <td>
                    <div className="scenario-name-cell">
                      {row.baselineYn === "Y" ? <span className="bc">BC</span> : null}
                      <input value={row.title} onChange={(event) => onUpdateRow(row.localId, { title: event.target.value })} />
                    </div>
                  </td>
                  {model.headers.map((header) => (
                    <td key={header.key}>
                      <select value={row.cells[header.key] ?? ""} onChange={(event) => onUpdateCell(row.localId, header.key, event.target.value)}>
                        <option value="">선택</option>
                        {selectValues.map((value) => (
                          <option key={value}>{value}</option>
                        ))}
                      </select>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {busy ? (
            <div className="loading-overlay">
              <span className="spinner" />
              <strong>변경사항을 검토하고 있습니다.</strong>
            </div>
          ) : null}
        </div>
        <button className="add-row-wide" onClick={onAddRow}>
          <Plus size={16} /> Add scenario row
        </button>
        {validation.state !== "idle" ? (
          <Callout
            tone={validation.state === "warning" ? "warning" : validation.state === "waiting" ? "info" : "success"}
            title={validation.state === "warning" ? "값 조합 적합성" : validation.state === "waiting" ? "Validation waiting" : "Validation complete"}
            message={validation.message}
            action={validation.recommendation}
          />
        ) : null}
      </section>
      <BottomBar>
        <button className="button secondary" onClick={onReset}>
          <RefreshCcw size={16} /> 전체 초기화
        </button>
        <div className="bar-actions">
          <button className="button secondary" onClick={onBack}>
            취소
          </button>
          <button className="button dark" disabled={!!pendingAction} onClick={onValidate}>
            변경사항 검토
          </button>
          <button className="button primary" disabled={validation.state !== "success" || !!pendingAction} onClick={onComplete}>
            검토 완료
          </button>
        </div>
      </BottomBar>
    </section>
  );
}

function StepTwo({
  model,
  pendingAction,
  onBack,
  onModel,
  onUpdateRow,
  onSignposts,
  onConfirm,
  onReset
}: {
  model: ScenarioDesignModel;
  pendingAction: string;
  onBack: () => void;
  onModel: (model: ScenarioDesignModel) => void;
  onUpdateRow: (id: string, patch: Partial<ScenarioRow>) => void;
  onSignposts: () => void;
  onConfirm: () => void;
  onReset: () => void;
}) {
  const busy = !!pendingAction;
  const probabilityTotal = model.rows.reduce((sum, row) => sum + (Number(row.probability) || 0), 0);
  const hasProbabilityWarning = Math.round(probabilityTotal * 100) / 100 !== 100;
  function updateProbability(row: ScenarioRow, value: string) {
    const numeric = Number(value);
    if (value !== "" && (!Number.isFinite(numeric) || numeric < 0 || numeric > 100)) return;
    onUpdateRow(row.localId, { probability: value });
  }
  return (
    <section className="workspace design with-bottom-bar">
      <BackTitle title="Scenario Design" onBack={onBack} />
      <Stepper active={2} />
      <section className="generated-fields">
        <LabeledTextarea
          label="시나리오 그룹명"
          value={model.groupName}
          maxLength={100}
          rows={2}
          onChange={(value) => onModel({ ...model, groupName: value })}
        />
        <LabeledTextarea
          label="시나리오 그룹 설명"
          value={model.description}
          maxLength={500}
          rows={5}
          onChange={(value) => onModel({ ...model, description: value })}
        />
      </section>
      <section className="section-block">
        <div className="section-title-row">
          <div>
            <h2>시나리오 검토</h2>
            <p>Signpost count: {model.rows.reduce((sum, row) => sum + row.signposts.length, 0)}</p>
          </div>
          <button className="button secondary" disabled={busy} onClick={onSignposts}>
            <Send size={16} /> Signpost 생성 요청
          </button>
        </div>
        <div className="scenario-board">
          {model.rows.map((row) => (
            <article className="scenario-card" key={row.localId}>
              <div className="scenario-card-header">
                <span className="number-badge">{row.displayOrder}</span>
                {row.baselineYn === "Y" ? <span className="bc">BC</span> : null}
                <input value={row.title} onChange={(event) => onUpdateRow(row.localId, { title: event.target.value })} />
                <button className="icon-button ghost" aria-label="Reset scenario section" title="Reset scenario section">
                  <RefreshCcw size={15} />
                </button>
              </div>
              <LabeledTextarea
                label="Scenario narrative"
                value={row.narrative}
                maxLength={500}
                rows={7}
                onChange={(value) => onUpdateRow(row.localId, { narrative: value })}
              />
              <div className="assumption-grid">
                {model.headers.map((header) => (
                  <div key={header.key} className="assumption-tile">
                    <span>{header.label}</span>
                    <strong>{row.cells[header.key] || "-"}</strong>
                  </div>
                ))}
              </div>
              <label className="probability-input">
                Probability
                <span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={row.probability}
                    onChange={(event) => updateProbability(row, event.target.value)}
                  />
                  %
                </span>
              </label>
              <div className="signpost-list">
                <div className="subhead">
                  <strong>주요 Signpost</strong>
                  <button className="icon-button ghost" aria-label="Edit signposts" title="Edit signposts">
                    <Edit3 size={15} />
                  </button>
                </div>
                {row.signposts.length ? (
                  row.signposts.map((signpost) => (
                    <div className="signpost-row" key={signpost.id}>
                      <strong>{signpost.label}</strong>
                      <span>
                        {signpost.direction} · {signpost.impact}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="signpost-row muted">Signpost 생성 요청 후 표시됩니다.</div>
                )}
              </div>
            </article>
          ))}
        </div>
        {hasProbabilityWarning ? (
          <Callout
            tone="warning"
            title="시나리오 가능성 합계"
            message={`현재 합계는 ${probabilityTotal.toFixed(2)}%입니다.`}
            action="Agent 확인 전 100% 기준 검토 권장"
          />
        ) : null}
      </section>
      <BottomBar>
        <button className="button secondary" onClick={onReset}>
          <RefreshCcw size={16} /> 전체 초기화
        </button>
        <div className="bar-actions">
          <button className="button secondary" onClick={onBack}>
            취소
          </button>
          <button className="button primary" disabled={busy} onClick={onConfirm}>
            시나리오 그룹 생성
          </button>
        </div>
      </BottomBar>
    </section>
  );
}

function DetailWorkspace({
  model,
  detailTab,
  selectedScenario,
  selectedScenarioId,
  onDetailTab,
  onSelectedScenario,
  onBack
}: {
  model: ScenarioDesignModel;
  detailTab: DetailTab;
  selectedScenario?: ScenarioRow;
  selectedScenarioId: string;
  onDetailTab: (tab: DetailTab) => void;
  onSelectedScenario: (id: string) => void;
  onBack: () => void;
}) {
  return (
    <section className="workspace detail">
      <button className="back-button" onClick={onBack}>
        <ChevronLeft size={17} /> Scenario Group List
      </button>
      <div className="detail-heading">
        <div>
          <span className="entity-label">Scenario Group</span>
          <h1>{model.groupName}</h1>
        </div>
        <div className="detail-tools">
          <button className="icon-button" aria-label="Comment help" title="Comment help">
            <CircleHelp size={18} />
          </button>
          <button className="icon-button" aria-label="More" title="More">
            <MoreVertical size={18} />
          </button>
        </div>
      </div>
      <div className="tabs detail-tabs">
        {[
          ["summary", "요약"],
          ["assumptions", "가정 및 실현 가능성"],
          ["prices", "가격 전망"],
          ["scenario", "시나리오 상세"]
        ].map(([key, label]) => (
          <button key={key} className={detailTab === key ? "active" : ""} onClick={() => onDetailTab(key as DetailTab)}>
            {label}
          </button>
        ))}
      </div>
      {detailTab === "summary" ? <SummaryTab model={model} /> : null}
      {detailTab === "assumptions" ? <AssumptionsTab model={model} /> : null}
      {detailTab === "prices" ? <div className="empty-panel">가격 전망 데이터는 backend detail read model 연결 후 표시됩니다.</div> : null}
      {detailTab === "scenario" && selectedScenario ? (
        <ScenarioDetailTab model={model} selectedScenario={selectedScenario} selectedScenarioId={selectedScenarioId} onSelectedScenario={onSelectedScenario} />
      ) : null}
    </section>
  );
}

function SummaryTab({ model }: { model: ScenarioDesignModel }) {
  return (
    <div className="detail-grid">
      <section className="summary-panel">
        <h2>요약</h2>
        <table className="summary-table">
          <tbody>
            <tr>
              <th>Base Event</th>
              <td>{model.baseEvent.title}</td>
            </tr>
            <tr>
              <th>Event Type</th>
              <td>{model.baseEvent.category}</td>
            </tr>
            <tr>
              <th>Update Time</th>
              <td>{model.baseEvent.eventTime}</td>
            </tr>
          </tbody>
        </table>
        <div className="description-block">{model.description}</div>
      </section>
      <AssumptionsTab model={model} compact />
    </div>
  );
}

function AssumptionsTab({ model, compact = false }: { model: ScenarioDesignModel; compact?: boolean }) {
  return (
    <section className="summary-panel">
      <h2>가정 및 실현 가능성</h2>
      <div className="table-wrap">
        <table className={compact ? "compact-table" : "event-table"}>
          <thead>
            <tr>
              <th>Scenario</th>
              {model.headers.map((header) => (
                <th key={header.key}>{header.label}</th>
              ))}
              <th>Probability</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {model.rows.map((row) => (
              <tr key={row.localId}>
                <td>
                  {row.baselineYn === "Y" ? <span className="bc">BC</span> : null} {row.title}
                </td>
                {model.headers.map((header) => (
                  <td key={header.key}>{row.cells[header.key]}</td>
                ))}
                <td>{row.probability}%</td>
                <td>
                  <select defaultValue={row.status}>
                    <option>Draft</option>
                    <option>Review</option>
                    <option>Confirmed</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ScenarioDetailTab({
  model,
  selectedScenario,
  selectedScenarioId,
  onSelectedScenario
}: {
  model: ScenarioDesignModel;
  selectedScenario: ScenarioRow;
  selectedScenarioId: string;
  onSelectedScenario: (id: string) => void;
}) {
  return (
    <div className="scenario-detail-layout">
      <aside className="scenario-sidebar">
        <strong>{model.rows.length}개 시나리오</strong>
        {model.rows.map((row) => (
          <button key={row.localId} className={selectedScenarioId === row.localId ? "active" : ""} onClick={() => onSelectedScenario(row.localId)}>
            <span className="number-badge">{row.displayOrder}</span>
            {row.baselineYn === "Y" ? <span className="bc">BC</span> : null}
            {row.title}
          </button>
        ))}
      </aside>
      <section className="scenario-detail-panel">
        <span className="entity-label">Scenario {selectedScenario.displayOrder}</span>
        <h2>{selectedScenario.title}</h2>
        <div className="description-block">{selectedScenario.narrative}</div>
        <div className="probability-card">
          <strong>Probability</strong>
          <span>{selectedScenario.probability}%</span>
        </div>
        <div className="assumption-grid">
          {model.headers.map((header) => (
            <div className="assumption-tile" key={header.key}>
              <span>{header.label}</span>
              <strong>{selectedScenario.cells[header.key] || "-"}</strong>
            </div>
          ))}
        </div>
        <h3>Signpost 정의</h3>
        <table className="event-table">
          <thead>
            <tr>
              <th>Signpost Label</th>
              <th>방향</th>
              <th>영향도</th>
              <th>핵심 근거</th>
            </tr>
          </thead>
          <tbody>
            {(selectedScenario.signposts.length ? selectedScenario.signposts : [{ id: "empty", label: "-", direction: "-", impact: "-", evidence: "-" }]).map((item) => (
              <tr key={item.id}>
                <td>{item.label}</td>
                <td>{item.direction}</td>
                <td>{item.impact}</td>
                <td>{item.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Inspector({
  events,
  rawSelection,
  onRawSelection
}: {
  events: TimelineEvent[];
  rawSelection: TimelineEvent["type"] | "all";
  onRawSelection: (type: TimelineEvent["type"] | "all") => void;
}) {
  return (
    <section className="inspector">
      <div className="section-title-row">
        <div>
          <h2>Timeline / Raw JSON Inspector</h2>
          <p>Accepted responses, callbacks, detail refreshes, request bodies, and errors</p>
        </div>
        <select value={rawSelection} onChange={(event) => onRawSelection(event.target.value as TimelineEvent["type"] | "all")}>
          <option value="all">All</option>
          <option value="request_body">Request bodies</option>
          <option value="accepted">Accepted</option>
          <option value="callback">Callbacks</option>
          <option value="detail_refreshed">Detail</option>
          <option value="error">Errors</option>
        </select>
      </div>
      <div className="timeline-list">
        {events.map((event) => (
          <details key={event.id} open={events.length === 1}>
            <summary>
              <span className={`event-type ${event.type}`}>{event.type}</span>
              <strong>{event.title}</strong>
              <time>{new Date(event.at).toLocaleString()}</time>
            </summary>
            <pre>{JSON.stringify(event.payload, null, 2)}</pre>
          </details>
        ))}
      </div>
    </section>
  );
}

function BackTitle({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="page-heading">
      <div>
        <button className="back-button" onClick={onBack}>
          <ChevronLeft size={17} /> Back
        </button>
        <h1>{title}</h1>
      </div>
      <button className="icon-button" aria-label="Help" title="Help">
        <CircleHelp size={18} />
      </button>
    </div>
  );
}

function Stepper({ active }: { active: 1 | 2 }) {
  return (
    <div className="stepper">
      <div className={active > 1 ? "complete" : "active"}>
        <span>{active > 1 ? <Check size={16} /> : 1}</span>
        <strong>시나리오 분기항목 및 분기기준 검토</strong>
        {active === 1 ? <em>진행중</em> : null}
      </div>
      <i />
      <div className={active === 2 ? "active" : ""}>
        <span>2</span>
        <strong>시나리오 One-view 검토</strong>
        {active === 2 ? <em>진행중</em> : null}
      </div>
    </div>
  );
}

function BaseEvent({ event }: { event: EventItem }) {
  return (
    <section className="base-event">
      <div>
        <span className="entity-label">Base Event</span>
        <h2>{event.title}</h2>
        <p>
          {event.eventTime} · {event.category}
        </p>
      </div>
      <ChevronRight size={22} />
    </section>
  );
}

function LabeledTextarea({
  label,
  value,
  maxLength,
  rows,
  onChange
}: {
  label: string;
  value: string;
  maxLength: number;
  rows: number;
  onChange: (value: string) => void;
}) {
  return (
    <label className="labeled-textarea">
      <span>{label}</span>
      <textarea value={value} maxLength={maxLength} rows={rows} onChange={(event) => onChange(event.target.value)} />
      <small>
        {value.length} / {maxLength}
      </small>
    </label>
  );
}

function BottomBar({ children }: { children: ReactNode }) {
  return <div className="bottom-bar">{children}</div>;
}

function Callout({ tone, title, message, action }: { tone: "warning" | "error" | "success" | "info"; title: string; message: string; action: string }) {
  return (
    <div className={`callout ${tone}`}>
      <AlertTriangle size={18} />
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
      <span>{action}</span>
    </div>
  );
}

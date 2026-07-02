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
  openRunEvents,
  refreshScenarioGroup,
  requestConfirmation,
  requestSignposts,
  requestValidation
} from "./api";
import { initialDesignModel, seedEvents } from "./lib/seed";
import { mergeDetailIntoModel, pickAgentStage, pickAgentStatus, pickRunId, pickScenarioGroupId } from "./lib/normalizer";
import type { EventItem, RunLifecycle, RunState, RuntimeConfig, ScenarioDesignModel, ScenarioRow, TimelineEvent } from "./types";

type Workspace = "events" | "design-step-1" | "design-step-2" | "detail";
type TopTab = "events" | "groups";
type DetailTab = "summary" | "assumptions" | "prices" | "scenario";

const DEFAULT_AGENT_BASE_URL = "http://localhost:8000";
const selectValues = ["전혀 없음", "낮음", "50%", "100%", "급차질-급회복", "급손상-장기재건", "1개월 이하", "6개월", "1년 초과", "종료 미정"];

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

export function App() {
  const [runtime, setRuntime] = useState<RuntimeConfig>(() =>
    readSaved("backoffice.runtime", {
          agentBaseUrl: DEFAULT_AGENT_BASE_URL,
          miEventId: "12",
          userId: "10603",
          runId: "",
          scenarioGroupId: ""
        })
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
  const [validation, setValidation] = useState<{ state: "idle" | "warning" | "success"; message: string; recommendation: string }>({
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
      if (event.type === "validation_result" || event.type === "callback") {
        const result = payload && typeof payload === "object" && "result" in payload ? String((payload as { result?: unknown }).result) : "";
        const message =
          payload && typeof payload === "object" && "message" in payload ? String((payload as { message?: unknown }).message) : "callback 결과를 확인하세요.";
        if (result.toLowerCase() === "failure") {
          setValidation({ state: "warning", message, recommendation: "Raw JSON에서 실패 상세를 확인하고 수정하세요." });
          setRunState((current) => ({ ...current, lifecycle: "failed" }));
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
    patchRuntime({ runId, scenarioGroupId });
    setRunState({
      lifecycle: "generation_waiting_callback",
      agentStatus: pickAgentStatus(record) || "creating",
      agentStage: pickAgentStage(record) || "ready"
    });
    addTimeline("accepted", "Create scenario draft accepted", payload);
    setWorkspace("design-step-1");
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
      () => refreshScenarioGroup(runtime.scenarioGroupId),
      (payload) => {
        setModel((current) => mergeDetailIntoModel(current, payload));
        addTimeline("detail_refreshed", "Scenario group detail refreshed", payload);
        setRunState((current) => ({ ...current, lifecycle: "scenario_created" }));
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
          state: "success",
          message: "변경사항 검토 요청이 접수되었습니다.",
          recommendation: "validation callback 또는 manual refresh 결과를 확인하세요."
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
    setValidation({ state: "idle", message: "", recommendation: "" });
    setRunState({ lifecycle: "idle", agentStatus: "-", agentStage: "-" });
    patchRuntime({ runId: "", scenarioGroupId: "" });
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

function EventWorkspace({
  topTab,
  runtime,
  onTopTab,
  onSelectEvent,
  onStartEvent
}: {
  topTab: TopTab;
  runtime: RuntimeConfig;
  onTopTab: (tab: TopTab) => void;
  onSelectEvent: (event: EventItem) => void;
  onStartEvent: (event: EventItem) => void;
}) {
  const [recommendedOnly, setRecommendedOnly] = useState(false);
  const [status, setStatus] = useState("전체");
  const [category, setCategory] = useState("all");
  const [keyword, setKeyword] = useState("");
  const filtered = seedEvents.filter(
    (event) =>
      (!recommendedOnly || event.recommended) &&
      (status === "전체" || event.status === status) &&
      (category === "all" || event.category === category) &&
      (!keyword.trim() || event.title.toLowerCase().includes(keyword.trim().toLowerCase()))
  );
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
            <select defaultValue="latest" aria-label="sort">
              <option value="latest">Latest first</option>
              <option value="impact">Impact priority</option>
            </select>
            <label className="toggle">
              <input type="checkbox" checked={recommendedOnly} onChange={(event) => setRecommendedOnly(event.target.checked)} />
              Recommended
            </label>
            <label className="search-box">
              <Search size={16} />
              <input placeholder="Search event name" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
            </label>
          </div>
          <div className="table-wrap">
            <table className="event-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Date/Time</th>
                  <th>Category</th>
                  <th>Event</th>
                  <th>JKM</th>
                  <th>TTF</th>
                  <th>HH</th>
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
                    <td>
                      <strong>{event.title}</strong>
                      {String(event.miEventId) === runtime.miEventId ? <span className="selected-note">selected</span> : null}
                    </td>
                    {(["JKM", "TTF", "HH"] as const).map((market) => (
                      <td key={market}>
                        <Impact value={event.impacts[market]} />
                      </td>
                    ))}
                    <td>
                      <button
                        className="icon-button"
                        aria-label="Start scenario design"
                        title="Start scenario design"
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation();
                          onStartEvent(event);
                        }}
                      >
                        <Sparkles size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
                {!filtered.length ? (
                  <tr>
                    <td colSpan={8}>
                      <div className="empty-table-message">조건에 맞는 이벤트가 없습니다. 필터를 조정하거나 runtime bar에서 miEventId를 직접 입력하세요.</div>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="empty-panel">
          <h2>Scenario Group List</h2>
          <p>Confirmed or refreshed scenario groups appear here when the backend run store is connected.</p>
        </div>
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
  validation: { state: "idle" | "warning" | "success"; message: string; recommendation: string };
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
            tone={validation.state === "warning" ? "warning" : "success"}
            title={validation.state === "warning" ? "값 조합 적합성" : "Validation requested"}
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
          <button className="button primary" disabled={validation.state === "warning" || !!pendingAction} onClick={onComplete}>
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

function Callout({ tone, title, message, action }: { tone: "warning" | "error" | "success"; title: string; message: string; action: string }) {
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

function Impact({ value }: { value: "up" | "down" | "neutral" }) {
  return (
    <span className={`impact ${value}`}>
      <b>S</b>
      <i />
      <i />
      <i />
    </span>
  );
}

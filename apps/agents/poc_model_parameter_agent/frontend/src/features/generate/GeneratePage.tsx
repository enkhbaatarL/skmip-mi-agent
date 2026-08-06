import { AlertCircle, Braces, CheckCircle2, CircleHelp, FileJson2, Play, RotateCcw, ShieldCheck, WandSparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ApiError } from "../../api/client";
import { useCreatePlan, useCreateRun, useExamples } from "../../api/queries";
import type { JsonObject, ParameterProposal, PlanResponse, RunDetail, RunMetadata, ValidationMessage } from "../../api/types";
import { useTargetMarket } from "../../app/TargetMarketContext";
import { useToast } from "../../app/Toast";
import { ErrorState, LoadingState } from "../../components/common/AsyncState";
import { StatusBadge } from "../../components/common/StatusBadge";
import { FinalFeedbackCard } from "../../components/feedback/FinalFeedbackCard";
import { EvaluationInvariants } from "../../components/results/EvaluationInvariants";
import { RevisionChain } from "../../components/results/RevisionChain";
import { ScenarioResults } from "../../components/results/ScenarioResults";

const MAX_BYTES = 1024 * 1024;
const initialMetadata: RunMetadata = { miEventIds: [], targetMarket: "JKM", comparisonRunId: "" };

type ContinueState = { continueRun?: RunDetail } | null;

function parseScenario(text: string): { value?: JsonObject; message: ValidationMessage } {
  if (new TextEncoder().encode(text).byteLength > MAX_BYTES) return { message: { level: "error", code: "PAYLOAD_TOO_LARGE", message: "Payload는 1 MiB를 초과할 수 없습니다." } };
  try {
    const value: unknown = JSON.parse(text);
    if (!value || typeof value !== "object" || Array.isArray(value)) return { message: { level: "error", code: "ROOT_TYPE", message: "Scenario JSON의 최상위 값은 Object여야 합니다." } };
    return { value: value as JsonObject, message: { level: "pass", code: "JSON_VALID", message: "JSON Syntax가 유효합니다. 계획 생성으로 Schema를 검증하세요." } };
  } catch (error) {
    return { message: { level: "error", code: "JSON_SYNTAX", message: error instanceof Error ? error.message : "JSON Syntax Error" } };
  }
}

export function GeneratePage() {
  const location = useLocation();
  const continueRun = (location.state as ContinueState)?.continueRun;
  const examples = useExamples();
  const planMutation = useCreatePlan();
  const runMutation = useCreateRun();
  const { setTargetMarket } = useTargetMarket();
  const { notify } = useToast();
  const [metadata, setMetadata] = useState<RunMetadata>(continueRun?.metadata ?? initialMetadata);
  const [eventIdsText, setEventIdsText] = useState((continueRun?.metadata.miEventIds ?? []).join(", "));
  const [jsonText, setJsonText] = useState(continueRun ? JSON.stringify(continueRun.sourceScenarioJson, null, 2) : "");
  const [syntaxMessage, setSyntaxMessage] = useState<ValidationMessage | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [freeModes, setFreeModes] = useState<Record<string, boolean>>({});
  const [run, setRun] = useState<RunDetail | null>(null);
  const [selection, setSelection] = useState<{ scenarioKey?: string; proposal?: ParameterProposal }>({});

  useEffect(() => setTargetMarket(metadata.targetMarket || "JKM"), [metadata.targetMarket, setTargetMarket]);
  const invalidateDerivedState = () => {
    setPlan(null);
    setRun(null);
    setSelection({});
    setAnswers({});
    setFreeModes({});
  };
  const updateMetadata = (patch: Partial<RunMetadata>) => {
    setMetadata((current) => ({ ...current, ...patch }));
    invalidateDerivedState();
  };
  const payloadBytes = useMemo(() => new TextEncoder().encode(jsonText).byteLength, [jsonText]);
  const requiredMissing = plan?.clarifications.some((question) => question.required && !answers[question.id]?.trim()) ?? false;
  const hasPlanErrors = plan?.validationMessages.some((message) => message.level === "error") ?? false;

  const loadExample = (index: number) => {
    const example = examples.data?.[index];
    if (!example) return;
    setMetadata(example.metadata); setEventIdsText(example.metadata.miEventIds.join(", ")); setJsonText(JSON.stringify(example.scenarioJson, null, 2)); invalidateDerivedState();
    setSyntaxMessage({ level: "info", message: `${example.label}을 불러왔습니다. JSON 검증 후 계획을 생성하세요.` });
    notify(`${example.label}을 API에서 불러왔습니다.`, "success");
  };

  const validateJson = () => {
    const parsed = parseScenario(jsonText);
    setSyntaxMessage(parsed.message);
    if (parsed.value) notify("JSON Syntax 검증을 통과했습니다.", "success");
  };

  const createPlan = async () => {
    const parsed = parseScenario(jsonText);
    setSyntaxMessage(parsed.message);
    if (!parsed.value) return;
    try {
      const response = await planMutation.mutateAsync({ metadata, scenarioJson: parsed.value });
      setRun(null); setSelection({}); setPlan(response); setAnswers(Object.fromEntries(response.clarifications.flatMap((question) => question.defaultValue ? [[question.id, question.defaultValue]] : [])));
      notify(response.validationMessages.some((message) => message.level === "error") ? "계획에 Validation Error가 있습니다." : "9단계 실행 계획을 생성했습니다.", response.validationMessages.some((message) => message.level === "error") ? "error" : "success");
    } catch (error) { notify(error instanceof Error ? error.message : "계획을 생성하지 못했습니다.", "error"); }
  };

  const createRun = async () => {
    const parsed = parseScenario(jsonText);
    if (!parsed.value || !plan) return;
    try {
      const response = await runMutation.mutateAsync({ metadata, scenarioJson: parsed.value, clarificationAnswers: answers });
      setRun(response); window.setTimeout(() => document.getElementById("run-results")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
      notify(`Parameter Run r${response.revision}을 생성했습니다.`, "success");
    } catch (error) {
      notify(error instanceof ApiError && error.status === 422 ? "Required Clarification 또는 입력 Validation을 확인하세요." : error instanceof Error ? error.message : "Run을 생성하지 못했습니다.", "error");
    }
  };

  const onSelection = useCallback((scenarioKey: string, proposal?: ParameterProposal) => setSelection({ scenarioKey, proposal }), []);
  const reset = () => { setMetadata(initialMetadata); setEventIdsText(""); setJsonText(""); setSyntaxMessage(null); invalidateDerivedState(); };

  return (
    <div className="page-stack generate-page">
      <header className="page-header"><div><span className="eyebrow">01 · MAIN PIPELINE</span><h1>Parameter 생성</h1><p>Scenario Group을 검증하고 결정적 월별 Parameter Proposal을 생성합니다.</p></div><button type="button" className="button button--ghost" onClick={reset}><RotateCcw size={14} />입력 초기화</button></header>
      {examples.isLoading && <LoadingState label="Example을 API에서 불러오는 중입니다." />}
      {examples.isError && <ErrorState error={examples.error} />}
      <section className="workspace-grid" aria-label="Parameter 생성 입력">
        <div className="card input-card">
          <div className="section-heading"><span className="eyebrow">RUN METADATA</span><h2>실행 Metadata</h2><p>Scenario의 Event 및 비교 기준을 지정합니다.</p></div>
          <div className="field-grid">
            <label className="field"><span>miEventIds <em>required</em></span><input value={eventIdsText} onChange={(event) => { const value = event.target.value; setEventIdsText(value); updateMetadata({ miEventIds: value.split(",").map((id) => Number(id.trim())).filter(Number.isFinite) }); }} placeholder="101, 202" /></label>
            <label className="field"><span>targetMarket <em>required</em></span><input value={metadata.targetMarket} onChange={(event) => updateMetadata({ targetMarket: event.target.value })} placeholder="JKM" /></label>
            <label className="field field--full"><span>comparisonRunId</span><input value={metadata.comparisonRunId} onChange={(event) => updateMetadata({ comparisonRunId: event.target.value })} placeholder="mp-v4-example-01" /></label>
          </div>
          <div className="example-actions"><span>Example Load</span>{[0, 1, 2].map((index) => <button className="button button--secondary" type="button" key={index} disabled={!examples.data?.[index]} onClick={() => loadExample(index)}>예시 {index + 1}{index === 2 ? " (질의 발생)" : ""} 불러오기</button>)}</div>
        </div>
        <div className="card json-card">
          <div className="section-heading section-heading--inline"><div><span className="eyebrow">SCENARIO JSON</span><h2>Scenario Payload</h2></div><span className={`payload-size${payloadBytes > MAX_BYTES ? " payload-size--error" : ""}`}>{(payloadBytes / 1024).toFixed(1)} / 1024 KiB</span></div>
          <label className="sr-only" htmlFor="scenario-json">Scenario JSON</label><textarea id="scenario-json" className="json-editor" spellCheck={false} value={jsonText} onChange={(event) => { setJsonText(event.target.value); setSyntaxMessage(null); invalidateDerivedState(); }} placeholder="Scenario Group JSON을 입력하거나 Example을 불러오세요." />
          {syntaxMessage && <div className={`message message--${syntaxMessage.level}`} role={syntaxMessage.level === "error" ? "alert" : "status"}>{syntaxMessage.level === "error" ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}<span><strong>{syntaxMessage.code}</strong>{syntaxMessage.message}</span></div>}
          <div className="card-actions"><button type="button" className="button button--secondary" onClick={validateJson} disabled={!jsonText}><Braces size={14} />JSON 검증</button><button type="button" className="button button--primary" onClick={createPlan} disabled={!jsonText || planMutation.isPending}><WandSparkles size={14} />{planMutation.isPending ? "계획 생성 중…" : "계획 생성"}</button></div>
        </div>
      </section>

      {plan && <section className="card plan-preview" aria-labelledby="plan-preview-title" data-testid="plan-preview">
        <div className="section-heading section-heading--inline"><div><span className="eyebrow">EXECUTION CONTRACT</span><h2 id="plan-preview-title">Plan Preview</h2></div><div className="badge-group"><StatusBadge tone={plan.validationMessages.some((m) => m.level === "error") ? "error" : "success"}>Error {plan.validationMessages.filter((m) => m.level === "error").length}</StatusBadge><StatusBadge tone={plan.validationMessages.some((m) => m.level === "warning") ? "warning" : "neutral"}>Warning {plan.validationMessages.filter((m) => m.level === "warning").length}</StatusBadge></div></div>
        <ol className="plan-steps">{plan.steps.map((step, index) => <li key={step.stepId}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{step.stepId}</strong><small>{step.label}</small></div><StatusBadge>{step.status ?? "pending"}</StatusBadge></li>)}</ol>
        <div className="plan-meta-grid">
          <div><h3>Assumptions</h3>{plan.assumptions.length ? <ul>{plan.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul> : <p className="muted">명시된 Assumption이 없습니다.</p>}</div>
          <div><h3>Active Asset Snapshot</h3><div className="context-chips">{plan.assetSnapshot.map((asset) => <code key={`${asset.assetType}-${asset.assetKey}`}>{asset.assetKey}@{asset.version}</code>)}</div></div>
        </div>
        {plan.validationMessages.length > 0 && <div className="validation-list" aria-label="Validation Messages">{plan.validationMessages.map((message, index) => <div className={`message message--${message.level}`} key={`${message.code}-${index}`}><ShieldCheck size={14} /><span><strong>{message.code}</strong>{message.path && <code>{message.path}</code>}{message.message}</span></div>)}</div>}
        {plan.clarifications.length > 0 && <div className="clarification-panel"><div className="section-heading"><span className="eyebrow">CLARIFICATION</span><h3>계산 전 확인</h3><p>결과에 큰 영향을 주는 모호성만 확인합니다. 모든 응답은 Interim Feedback으로 저장됩니다.</p></div>{plan.clarifications.map((question) => <fieldset className="clarification-question" key={question.id}><legend><CircleHelp size={15} />{question.question}<StatusBadge tone={question.required ? "error" : "neutral"}>{question.required ? "Required" : "Optional"}</StatusBadge></legend><div className="clarification-options">{question.options.map((option) => <label key={option.value}><input type="radio" name={question.id} checked={!freeModes[question.id] && answers[question.id] === option.value} onChange={() => { setFreeModes((current) => ({ ...current, [question.id]: false })); setAnswers((current) => ({ ...current, [question.id]: option.value })); }} /><span><strong>{option.label}</strong>{option.description && <small>{option.description}</small>}</span></label>)}{question.allowFreeText && <label><input type="radio" name={question.id} checked={Boolean(freeModes[question.id])} onChange={() => { setFreeModes((current) => ({ ...current, [question.id]: true })); setAnswers((current) => ({ ...current, [question.id]: "" })); }} /><span><strong>직접 입력</strong></span></label>}</div>{freeModes[question.id] && <label className="field field--full"><span>수기 응답</span><input aria-label={`${question.question} 수기 응답`} value={answers[question.id] ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))} placeholder="자연어로 입력하세요." /></label>}</fieldset>)}</div>}
        <div className="plan-footer"><p>{requiredMissing ? "Required Clarification 응답 후 실행할 수 있습니다." : hasPlanErrors ? "Validation Error를 수정한 뒤 계획을 다시 생성하세요." : "계획과 Asset Snapshot이 준비되었습니다."}</p><button type="button" className="button button--primary button--large" onClick={createRun} disabled={requiredMissing || hasPlanErrors || runMutation.isPending}><Play size={15} />{runMutation.isPending ? "Parameter 생성 중…" : "Parameter 생성"}</button></div>
      </section>}

      {run && <div className="run-results" id="run-results" data-testid="run-results"><div className="summary-grid"><RevisionChain chain={run.revisionChain} currentRunId={run.runId} /><EvaluationInvariants messages={run.evaluationInvariants ?? []} /></div><ScenarioResults run={run} onSelectionChange={onSelection} /><FinalFeedbackCard key={run.runId} run={run} scenarioKey={selection.scenarioKey} proposal={selection.proposal} onCreated={(child) => { setRun(child); setSelection({}); }} /></div>}
    </div>
  );
}

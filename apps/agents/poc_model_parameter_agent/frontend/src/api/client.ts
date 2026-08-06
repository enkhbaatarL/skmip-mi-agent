import type {
  AssetSnapshotEntry,
  AssetSummary,
  AssetVersion,
  Clarification,
  ExampleDefinition,
  FeedbackRecord,
  FinalFeedbackInput,
  FinalFeedbackResponse,
  HealthResponse,
  LearningBatch,
  LearningCandidate,
  ListParams,
  PagedResult,
  ParameterProposal,
  PlanInput,
  PlanResponse,
  RunDetail,
  RunInput,
  RunSummary,
  ScenarioResult,
  ValidationMessage,
} from "./types";

type UnknownRecord = Record<string, unknown>;

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;

  constructor(status: number, message: string, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const pick = <T>(record: UnknownRecord, ...keys: string[]): T | undefined => {
  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null) return record[key] as T;
  }
  return undefined;
};

const array = <T>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);
const number = (value: unknown, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};
const string = (value: unknown, fallback = "") => (typeof value === "string" ? value : fallback);
const bool = (value: unknown, fallback = false) => (typeof value === "boolean" ? value : fallback);

const query = (params?: ListParams) => {
  if (!params) return "";
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : "";
};

const feedbackQuery = (params?: ListParams) => {
  if (!params) return "";
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.pageSize !== undefined) search.set("pageSize", String(params.pageSize));
  if (params.tag) search.set("tag", params.tag);
  if (params.source) search.set("source", params.source);
  if (params.status) search.set("processingStatus", params.status);
  const text = search.toString();
  return text ? `?${text}` : "";
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const normalizedPath = API_BASE.endsWith("/api") && path.startsWith("/api/") ? path.slice(4) : path;
  const response = await fetch(`${API_BASE}${normalizedPath}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  const contentType = response.headers.get("content-type") ?? "";
  const body: unknown = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const error = isRecord(body) ? (isRecord(body.detail) ? body.detail : body) : {};
    throw new ApiError(
      response.status,
      string(pick(error, "message", "detail"), response.statusText || "요청을 처리하지 못했습니다."),
      string(pick(error, "code")) || undefined,
      pick(error, "details") ?? body,
    );
  }
  return body as T;
}

function normalizeMetadata(value: unknown) {
  const record = isRecord(value) ? value : {};
  return {
    miEventIds: array<number>(pick(record, "miEventIds", "mi_event_ids")).map(Number),
    targetMarket: string(pick(record, "targetMarket", "target_market"), "JKM"),
    comparisonRunId: string(pick(record, "comparisonRunId", "comparison_run_id")),
  };
}

function normalizeSnapshot(value: unknown): AssetSnapshotEntry[] {
  if (Array.isArray(value)) {
    return value.map((item) => {
      const r = isRecord(item) ? item : {};
      return {
        assetType: string(pick(r, "assetType", "asset_type")),
        assetKey: string(pick(r, "assetKey", "asset_key")),
        version: (pick(r, "version") as string | number | undefined) ?? "-",
      };
    });
  }
  if (isRecord(value)) {
    return Object.entries(value).map(([assetKey, version]) => ({
      assetType: isRecord(version) ? string(pick(version, "assetType", "asset_type"), assetKey.split(":")[0] ?? "asset") : assetKey.split(":")[0] ?? "asset",
      assetKey: isRecord(version) ? string(pick(version, "assetKey", "asset_key"), assetKey.split(":").slice(1).join(":") || assetKey) : assetKey,
      version: isRecord(version) ? ((pick(version, "version") as string | number | undefined) ?? "-") : String(version),
    }));
  }
  return [];
}

function normalizeMessages(value: unknown): ValidationMessage[] {
  return array<unknown>(value).map((item) => {
    const r = isRecord(item) ? item : {};
    const rawLevel = string(pick(r, "level", "severity"), "info").toLowerCase();
    const level = (["error", "warning", "info", "pass"].includes(rawLevel) ? rawLevel : "info") as ValidationMessage["level"];
    return {
      level,
      code: string(pick(r, "code")) || undefined,
      path: string(pick(r, "path", "field")) || undefined,
      message: string(pick(r, "message", "detail"), JSON.stringify(item)),
    };
  });
}

function normalizeClarifications(value: unknown): Clarification[] {
  return array<unknown>(value).map((item, index) => {
    const r = isRecord(item) ? item : {};
    const rawOptions = array<unknown>(pick(r, "options", "choices"));
    return {
      id: string(pick(r, "id", "questionId", "clarification_id", "question_id"), `clarification-${index + 1}`),
      question: string(pick(r, "question", "label", "prompt")),
      required: bool(pick(r, "required", "is_required")),
      type: string(pick(r, "type", "kind", "answer_type"), "single_choice") as Clarification["type"],
      options: rawOptions.map((option) => {
        const o = isRecord(option) ? option : {};
        return {
          value: isRecord(option) ? string(pick(o, "value", "id", "choiceId", "option_id")) : String(option),
          label: isRecord(option) ? string(pick(o, "label", "text"), string(pick(o, "value"))) : String(option),
          description: isRecord(option) ? string(pick(o, "description")) || undefined : undefined,
        };
      }),
      allowFreeText: bool(pick(r, "allowFreeText", "allowText", "allow_free_text"), true),
      defaultValue: string(pick(r, "defaultValue", "default_value")) || undefined,
    };
  });
}

export function normalizePlan(value: unknown): PlanResponse {
  const r = isRecord(value) ? value : {};
  const report = pick<UnknownRecord>(r, "validationReport", "validation_report");
  const rawMessages = pick(r, "validationMessages", "validation_messages") ?? (report ? pick(report, "messages") : []);
  return {
    steps: array<unknown>(pick(r, "steps", "planSteps", "plan_steps", "flow_steps")).map((step, index) => {
      const s = isRecord(step) ? step : {};
      return {
        stepId: string(pick(s, "stepId", "step_id", "id"), `step-${index + 1}`),
        label: string(pick(s, "label", "name")),
        status: string(pick(s, "status"), "pending") as "pending" | "completed" | "failed",
        description: string(pick(s, "description")) || undefined,
      };
    }),
    clarifications: normalizeClarifications(pick(r, "clarifications", "questions")),
    assumptions: array<unknown>(pick(r, "assumptions")).map(String),
    validationMessages: normalizeMessages(rawMessages),
    assetSnapshot: normalizeSnapshot(pick(r, "assetSnapshot", "asset_snapshot")),
    canRun: bool(pick(r, "canRun", "can_run"), !normalizeMessages(rawMessages).some((m) => m.level === "error")),
  };
}

function normalizeProposal(value: unknown): ParameterProposal {
  const r = isRecord(value) ? value : {};
  const rawEvidence = array<unknown>(pick(r, "evidence", "contributions"));
  const series = array<unknown>(pick(r, "series", "monthly_series", "time_series")).map((point) => {
    const p = isRecord(point) ? point : {};
    const pointContributions = array<unknown>(pick(p, "contributions"));
    const baseline = number(pick(p, "baseline", "baseline_value"));
    const proposed = number(pick(p, "proposed", "proposed_value"));
    return {
      month: string(pick(p, "month", "period")),
      baseline,
      proposed,
      delta: number(pick(p, "delta"), proposed - baseline),
      deltaPct: number(pick(p, "deltaPct", "deltaPercent", "delta_pct", "delta_percent"), baseline ? ((proposed - baseline) / baseline) * 100 : 0),
      phase: string(pick(p, "phase"), pointContributions.some((item) => string(pick(isRecord(item) ? item : {}, "phase")) === "event") ? "event" : pointContributions.some((item) => string(pick(isRecord(item) ? item : {}, "phase")) === "recovery") ? "recovery" : "baseline"),
    };
  });
  const baselinePeak = number(pick(r, "baselinePeak", "baseline_peak"), Math.max(0, ...series.map((p) => p.baseline)));
  const proposedPeak = number(pick(r, "proposedPeak", "proposed_peak"), Math.max(0, ...series.map((p) => p.proposed)));
  const delta = number(pick(r, "delta", "peak_delta"), proposedPeak - baselinePeak);
  return {
    proposalId: string(pick(r, "proposalId", "proposal_id")) || undefined,
    scenarioKey: string(pick(r, "scenarioKey", "scenario_key"), "scenario-1"),
    parameterCode: string(pick(r, "parameterCode", "parameter_code")),
    parameterName: string(pick(r, "parameterName", "parameter_name"), string(pick(r, "parameterCode", "parameter_code"))),
    domain: string(pick(r, "domain"), "price_only"),
    unit: string(pick(r, "unit")) || undefined,
    periodStart: (() => { const application = pick<unknown>(r, "applicationPeriod", "application_period"); return string(pick(r, "periodStart", "period_start") ?? (isRecord(application) ? pick(application, "start", "startMonth", "start_month") : undefined), series.at(0)?.month) || undefined; })(),
    periodEnd: (() => { const application = pick<unknown>(r, "applicationPeriod", "application_period"); return string(pick(r, "periodEnd", "period_end") ?? (isRecord(application) ? pick(application, "end", "endMonth", "end_month") : undefined), series.at(-1)?.month) || undefined; })(),
    baselinePeak,
    proposedPeak,
    delta,
    deltaPct: number(pick(r, "deltaPct", "deltaPercent", "delta_pct", "delta_percent"), baselinePeak ? (delta / baselinePeak) * 100 : 0),
    confidence: number(pick(r, "confidence")),
    warningCount: number(pick(r, "warningCount", "warning_count")),
    feedbackAdjusted: bool(pick(r, "feedbackAdjusted", "feedback_adjusted"), Boolean(pick(r, "feedbackAdjustment", "feedback_adjustment"))),
    series,
    trace: array<unknown>(pick(r, "trace", "rationale_trace", "trace_steps")).map((step) => {
      const s = isRecord(step) ? step : {};
      return {
        step: string(pick(s, "step", "step_id")),
        label: string(pick(s, "label", "step", "step_id")),
        summary: string(pick(s, "summary", "detail", "description"), "구조화 계산 결과"),
        details: pick(s, "details", "data", "evidence") as never,
        status: string(pick(s, "status"), "applied") as "applied" | "excluded" | "warning",
      };
    }),
    formula: string(pick(r, "formula")) || undefined,
    evidence: pick(r, "evidence") as never,
    contributions: pick(r, "contributions") as never,
    eventIds: array<number>(pick(r, "eventIds", "event_ids")).map(Number).length
      ? array<number>(pick(r, "eventIds", "event_ids")).map(Number)
      : [...new Set(rawEvidence.flatMap((evidence) => {
          const item = isRecord(evidence) ? evidence : {};
          const many = array<number>(pick(item, "eventIds", "event_ids")).map(Number);
          const single = number(pick(item, "eventId", "event_id"), Number.NaN);
          return many.length ? many : Number.isFinite(single) ? [single] : [];
        }))],
    leverCodes: array<string>(pick(r, "leverCodes", "lever_codes")).map(String).length
      ? array<string>(pick(r, "leverCodes", "lever_codes")).map(String)
      : [...new Set(rawEvidence.map((evidence) => string(pick(isRecord(evidence) ? evidence : {}, "leverCode", "lever_code"))).filter(Boolean))],
  };
}

function normalizeScenario(value: unknown, index: number): ScenarioResult {
  const r = isRecord(value) ? value : {};
  const pressure = pick<UnknownRecord>(r, "pressure") ?? {};
  const rawDimensionValues = pick<unknown>(r, "dimensionValues", "dimension_values") ?? {};
  const dimensionValues = isRecord(rawDimensionValues) ? rawDimensionValues : {};
  const providedDimensions = array<unknown>(pick(r, "dimensions", "dimension_rows")).length
    ? array<unknown>(pick(r, "dimensions", "dimension_rows"))
    : array<unknown>(rawDimensionValues);
  return {
    scenarioKey: string(pick(r, "scenarioKey", "scenario_key", "key"), `scenario-${index + 1}`),
    title: string(pick(r, "title", "name"), `Scenario ${index + 1}`),
    narrative: string(pick(r, "narrative", "description")) || undefined,
    probability: number(pick(r, "probability", "probabilityScore", "probability_score")),
    declaredPressureBand: string(pick(r, "declaredPressureBand", "declared_pressure_band", "targetMarketPressureBand", "target_market_pressure_band") ?? pick(pressure, "declaredBand", "declared_band")) || undefined,
    computedPressureBand: string(pick(r, "computedPressureBand", "computed_pressure_band", "calculated_pressure_band") ?? pick(pressure, "computedBand", "calculatedBand", "computed_band", "calculated_band", "netBand", "net_band")) || undefined,
    pressureScore: number(pick(r, "pressureScore", "pressure_score") ?? pick(pressure, "score", "netScore", "netPressureScore", "net_score", "net_pressure_score")),
    pressureConsistency: string(pick(r, "pressureConsistency", "pressure_consistency", "consistency_status") ?? pick(pressure, "consistency", "status"), "pass"),
    mixedFactors: array<unknown>(pick(r, "mixedFactors", "mixed_factors")).map(String),
    dimensions: providedDimensions.length
      ? providedDimensions.map((dimension) => {
          const d = isRecord(dimension) ? dimension : {};
          return {
            dimensionId: string(pick(d, "dimensionId", "dimension_id")),
            valueId: string(pick(d, "valueId", "value_id")),
            meaning: string(pick(d, "meaning", "label")) || undefined,
            leverCodes: array<string>(pick(d, "leverCodes", "lever_codes")).map(String),
            eventIds: array<number>(pick(d, "eventIds", "event_ids")).map(Number),
          };
        })
      : Object.entries(dimensionValues).map(([dimensionId, valueId]) => ({ dimensionId, valueId: String(valueId) })),
    validationMessages: normalizeMessages(pick(r, "validationMessages", "validation_messages")),
  };
}

function normalizeFeedback(value: unknown): FeedbackRecord {
  const r = isRecord(value) ? value : {};
  const context = (pick(r, "context", "context_json") ?? {}) as never;
  return {
    feedbackId: string(pick(r, "feedbackId", "feedback_id", "id")),
    runId: string(pick(r, "runId", "run_id")),
    resultRunId: string(pick(r, "resultRunId", "result_run_id")) || null,
    revision: number(pick(r, "revision") ?? (isRecord(context) ? pick(context, "revision") : undefined)) || undefined,
    tag: string(pick(r, "tag"), "interim") as FeedbackRecord["tag"],
    source: string(pick(r, "source"), "clarification") as FeedbackRecord["source"],
    scope: string(pick(r, "scope"), "run"),
    rawText: string(pick(r, "rawText", "raw_text", "text")),
    context,
    adjustment: pick(r, "adjustment", "adjustment_json") as never,
    interpretation: (pick(r, "interpretation", "interpretation_json") ?? null) as never,
    answer: pick(r, "answer", "answer_json") as never,
    recordJson: pick(r, "recordJson", "record_json") as never,
    processingStatus: string(pick(r, "processingStatus", "processing_status", "status"), "pending"),
    learningBatchId: string(pick(r, "learningBatchId", "learning_batch_id")) || null,
    candidateIds: array<string>(pick(r, "candidateIds", "candidate_ids")).map(String),
    createdAt: string(pick(r, "createdAt", "created_at")),
  };
}

export function normalizeRun(value: unknown): RunDetail {
  const r = isRecord(value) ? value : {};
  const result = isRecord(r.run) ? { ...r.run, ...r } : r;
  const rawScenarios = array<unknown>(pick(result, "scenarios", "scenario_results"));
  const nestedProposals = rawScenarios.flatMap((scenario, index) => {
    const scenarioRecord = isRecord(scenario) ? scenario : {};
    const key = string(pick(scenarioRecord, "scenarioKey", "scenario_key", "key"), `scenario-${index + 1}`);
    return array<unknown>(pick(scenarioRecord, "proposals", "parameterProposals", "parameter_proposals")).map((proposal) => {
      const proposalRecord = isRecord(proposal) ? proposal : {};
      return normalizeProposal({ ...proposalRecord, scenarioKey: pick(proposalRecord, "scenarioKey", "scenario_key") ?? key });
    });
  });
  const proposals = [...array<unknown>(pick(result, "proposals", "parameter_proposals")).map(normalizeProposal), ...nestedProposals];
  let scenarios = rawScenarios.map(normalizeScenario);
  if (!scenarios.length) {
    const normalized = pick<UnknownRecord>(result, "normalizedInput", "normalized_input");
    scenarios = array<unknown>(normalized ? pick(normalized, "scenarios") : undefined).map(normalizeScenario);
  }
  return {
    runId: string(pick(result, "runId", "run_id", "id")),
    rootRunId: string(pick(result, "rootRunId", "root_run_id")) || undefined,
    revision: number(pick(result, "revision"), 1),
    parentRunId: string(pick(result, "parentRunId", "parent_run_id")) || null,
    comparisonRunId: string(pick(result, "comparisonRunId", "comparison_run_id")) || undefined,
    targetMarket: string(pick(result, "targetMarket", "target_market"), "JKM"),
    eventIds: array<number>(pick(result, "eventIds", "event_ids", "mi_event_ids")).map(Number),
    createdAt: string(pick(result, "createdAt", "created_at")),
    status: string(pick(result, "status"), "completed"),
    scenarioCount: number(pick(result, "scenarioCount", "scenario_count"), scenarios.length),
    proposalCount: number(pick(result, "proposalCount", "proposal_count"), proposals.length),
    interimFeedbackCount: number(pick(result, "interimFeedbackCount", "interim_feedback_count")),
    finalFeedbackCount: number(pick(result, "finalFeedbackCount", "final_feedback_count")),
    adjustmentCount: number(pick(result, "adjustmentCount", "adjustment_count")),
    assetSnapshot: normalizeSnapshot(pick(result, "assetSnapshot", "assetVersions", "asset_snapshot", "asset_versions")),
    metadata: normalizeMetadata(pick(result, "metadata") ?? result),
    sourceScenarioJson: (pick(result, "sourceScenarioJson", "scenarioJson", "inputJson", "source_scenario_json", "scenario_json", "input_json", "source_json") ?? {}) as never,
    normalizedInput: pick(result, "normalizedInput", "normalized_input") as never,
    horizon: pick(result, "horizon") as never,
    clarificationAnswers: pick(result, "clarificationAnswers", "clarification_answers") as never,
    validationReport: pick(result, "validationReport", "validation_report") as never,
    planSteps: normalizePlan({ steps: pick(result, "planSteps", "plan_steps") }).steps,
    artifacts: array<unknown>(pick(result, "artifacts", "run_artifacts")).map((artifact) => {
      const a = isRecord(artifact) ? artifact : {};
      return {
        stepId: string(pick(a, "stepId", "step_id")),
        label: string(pick(a, "label")) || undefined,
        status: string(pick(a, "status")),
        output: pick(a, "output", "output_json") as never,
        validationMessages: normalizeMessages(pick(a, "validationMessages", "validation_messages")),
        exclusions: pick(a, "exclusions", "exclusionLog", "exclusion_log") as never,
      };
    }),
    proposals,
    scenarios,
    revisionChain: array<unknown>(pick(result, "revisionChain", "revision_chain")).map((link) => {
      const l = isRecord(link) ? link : {};
      return { runId: string(pick(l, "runId", "run_id")), revision: number(pick(l, "revision")), status: string(pick(l, "status")) || undefined };
    }),
    feedback: array<unknown>(pick(result, "feedback", "feedbacks", "feedback_history")).map(normalizeFeedback),
    evaluationInvariants: (() => {
      const raw = pick<unknown>(result, "evaluationInvariants", "evaluation_invariants");
      if (Array.isArray(raw)) return normalizeMessages(raw);
      if (isRecord(raw)) return Object.entries(raw).map(([code, passed]) => ({
        level: passed ? "pass" : "error",
        code,
        message: `${code}: ${passed ? "PASS" : "FAIL"}`,
      } as ValidationMessage));
      return [];
    })(),
    childRunId: string(pick(result, "childRunId", "child_run_id")) || (() => {
      const children = array<unknown>(pick(result, "childRuns", "child_runs"));
      const first = isRecord(children[0]) ? children[0] : {};
      return string(pick(first, "runId", "run_id")) || null;
    })(),
    hasFinalFeedback: bool(pick(result, "hasFinalFeedback", "has_final_feedback"), number(pick(result, "finalFeedbackCount", "final_feedback_count")) > 0),
  };
}

function normalizeRunSummary(value: unknown): RunSummary {
  return normalizeRun(value);
}

function normalizePaged<T>(value: unknown, normalize: (item: unknown) => T): PagedResult<T> {
  if (Array.isArray(value)) return { items: value.map(normalize), total: value.length };
  const r = isRecord(value) ? value : {};
  const items = array<unknown>(pick(r, "items", "results", "data", "runs", "feedback", "batches", "candidates", "assets"));
  const rawPending = pick<UnknownRecord>(r, "pendingCounts", "pending_counts");
  return {
    items: items.map(normalize),
    total: number(pick(r, "total", "total_count"), items.length),
    pendingCounts: rawPending ? {
      interim: number(pick(rawPending, "interim")),
      final: number(pick(rawPending, "final")),
      total: number(pick(rawPending, "total")),
    } : undefined,
  };
}

function normalizeCandidate(value: unknown): LearningCandidate {
  const r = isRecord(value) ? value : {};
  const sourceFeedback = pick<UnknownRecord>(r, "sourceFeedback", "source_feedback") ?? {};
  const evaluation = pick<UnknownRecord>(r, "evaluation") ?? {};
  return {
    candidateId: string(pick(r, "candidateId", "candidate_id", "id")),
    sourceFeedbackId: string(pick(r, "sourceFeedbackId", "source_feedback_id") ?? pick(sourceFeedback, "feedbackId", "feedback_id", "id")),
    sourceRunId: string(pick(r, "sourceRunId", "source_run_id") ?? pick(sourceFeedback, "runId", "run_id")) || undefined,
    sourceTag: string(pick(r, "sourceTag", "source_tag") ?? pick(sourceFeedback, "tag")) as LearningCandidate["sourceTag"],
    sourceContext: (pick(r, "sourceContext", "source_context") ?? pick(sourceFeedback, "context", "contextJson", "context_json")) as never,
    sourceFeedbackText: string(pick(r, "sourceFeedbackText", "source_feedback_text", "raw_text") ?? pick(sourceFeedback, "rawText", "raw_text", "text")) || undefined,
    targetType: string(pick(r, "targetType", "target_type")),
    targetAssetKey: string(pick(r, "targetAssetKey", "target_asset_key")),
    baseVersion: (pick(r, "baseVersion", "base_version") as string | number | undefined) ?? "-",
    proposedVersion: (pick(r, "proposedVersion", "proposed_version") as string | number | undefined) ?? "next",
    proposedContent: pick(r, "proposedContent", "proposed_content") as never,
    changeLine: string(pick(r, "changeLine", "change_line")),
    diff: string(pick(r, "diff", "diff_text")),
    classification: string(pick(r, "classification")) || undefined,
    matchedSignals: array<string>(pick(r, "matchedSignals", "matched_signals")).map(String),
    rationale: string(pick(r, "rationale")) || undefined,
    confidence: number(pick(r, "confidence")),
    evaluations: array<unknown>(pick(r, "evaluations", "evaluation_checks") ?? pick(evaluation, "checks")).map((check) => {
      const c = isRecord(check) ? check : {};
      return { name: string(pick(c, "name", "label", "checkId", "check_id", "check")), passed: bool(pick(c, "passed")), detail: string(pick(c, "detail", "message")) || undefined };
    }),
    risks: array<string>(pick(r, "risks")).map(String),
    expectedImpact: string(pick(r, "expectedImpact", "expected_impact")) || undefined,
    status: string(pick(r, "status"), "pending"),
    createdAt: string(pick(r, "createdAt", "created_at")) || undefined,
  };
}

function normalizeAssetVersion(value: unknown): AssetVersion {
  const r = isRecord(value) ? value : {};
  return {
    assetType: string(pick(r, "assetType", "asset_type")),
    assetKey: string(pick(r, "assetKey", "asset_key")),
    version: (pick(r, "version") as string | number | undefined) ?? "-",
    learnable: bool(pick(r, "learnable")),
    locked: bool(pick(r, "locked")),
    active: bool(pick(r, "active", "is_active")),
    createdAt: string(pick(r, "createdAt", "created_at")),
    sourceCandidateId: string(pick(r, "sourceCandidateId", "source_candidate_id")) || null,
    content: (pick(r, "content", "content_json", "content_text") ?? "") as never,
  };
}

function normalizeAsset(value: unknown): AssetSummary {
  const r = isRecord(value) ? value : {};
  const versions = array<unknown>(pick(r, "versions", "assetVersions", "version_history")).map(normalizeAssetVersion);
  return {
    assetType: string(pick(r, "assetType", "asset_type")),
    assetKey: string(pick(r, "assetKey", "asset_key")),
    learnable: bool(pick(r, "learnable"), versions[0]?.learnable),
    locked: bool(pick(r, "locked"), versions[0]?.locked),
    activeVersion: (pick(r, "activeVersion", "active_version") as string | number | undefined) ?? versions.find((v) => v.active)?.version ?? "-",
    versions,
  };
}

export const api = {
  health: async (): Promise<HealthResponse> => {
    const value = await request<unknown>("/health");
    const r = isRecord(value) ? value : {};
    const db = pick<unknown>(r, "database", "db");
    return {
      status: string(pick(r, "status"), "unknown"),
      databaseStatus: isRecord(db) ? string(pick(db, "status"), "unknown") : string(pick(r, "databaseStatus", "database_status", "db_status"), "unknown"),
      agentMode: string(pick(r, "agentMode", "agent_mode", "mode"), "mock"),
      activeAssets: normalizeSnapshot(pick(r, "activeAssets", "assets", "active_assets")),
    };
  },
  examples: async (): Promise<ExampleDefinition[]> => {
    const value = await request<unknown>("/api/examples");
    const r = isRecord(value) ? value : {};
    const source = Array.isArray(value) ? value : array<unknown>(pick(r, "items", "examples"));
    if (source.length) {
      return source.map((item, index) => {
        const e = isRecord(item) ? item : {};
        return {
          id: string(pick(e, "id", "exampleId", "example_id", "key"), `example${index + 1}`),
          label: string(pick(e, "label", "name", "title"), `예시 ${index + 1}`),
          description: string(pick(e, "description")) || undefined,
          metadata: normalizeMetadata(pick(e, "metadata", "meta")),
          scenarioJson: (pick(e, "scenarioJson", "scenario_json", "scenario", "payload") ?? {}) as never,
        };
      });
    }
    return Object.entries(r)
      .filter(([key]) => /^example\d+$/.test(key))
      .map(([key, item], index) => {
        const e = isRecord(item) ? item : {};
        return {
          id: key,
          label: `예시 ${index + 1}${index === 2 ? " (질의 발생)" : ""}`,
          metadata: normalizeMetadata(pick(e, "metadata", "meta") ?? pick(r, `${key}Meta`, `${key}_meta`)),
          scenarioJson: (pick(e, "scenarioJson", "scenario_json", "scenario") ?? item) as never,
        };
      });
  },
  createPlan: async (input: PlanInput) => normalizePlan(await request("/api/plans", { method: "POST", body: JSON.stringify(input) })),
  createRun: async (input: RunInput) => normalizeRun(await request("/api/runs", { method: "POST", body: JSON.stringify(input) })),
  runs: async (params?: ListParams) => normalizePaged(await request(`/api/runs${query(params)}`), normalizeRunSummary),
  run: async (id: string) => normalizeRun(await request(`/api/runs/${encodeURIComponent(id)}`)),
  submitFinalFeedback: async (runId: string, input: FinalFeedbackInput): Promise<FinalFeedbackResponse> => {
    const value = await request<unknown>(`/api/runs/${encodeURIComponent(runId)}/feedback`, { method: "POST", body: JSON.stringify(input) });
    const r = isRecord(value) ? value : {};
    return {
      feedback: normalizeFeedback(pick(r, "feedback") ?? value),
      resultRun: normalizeRun(pick(r, "resultRun", "result_run", "newRun", "new_run") ?? {}),
    };
  },
  feedback: async (params?: ListParams) => normalizePaged(await request(`/api/feedback${feedbackQuery(params)}`), normalizeFeedback),
  feedbackDetail: async (id: string) => normalizeFeedback(await request(`/api/feedback/${encodeURIComponent(id)}`)),
  batches: async (params?: ListParams) => normalizePaged(await request(`/api/learning/batches${query(params)}`), (item) => {
    const r = isRecord(item) ? item : {};
    return {
      batchId: string(pick(r, "batchId", "batch_id", "id")),
      createdAt: string(pick(r, "createdAt", "created_at")),
      feedbackIds: array<string>(pick(r, "feedbackIds", "feedback_ids")).map(String),
      interimCount: number(pick(r, "interimCount", "interim_count")),
      finalCount: number(pick(r, "finalCount", "final_count")),
      status: string(pick(r, "status")),
      reviewerMode: string(pick(r, "reviewerMode", "reviewer_mode"), "deterministic"),
      candidateCount: number(pick(r, "candidateCount", "candidate_count")),
      classificationSummary: pick(r, "classificationSummary", "classification_summary") as never,
      reviewSummary: pick(r, "reviewSummary", "review_summary") as never,
    } satisfies LearningBatch;
  }),
  batch: async (id: string) => request<LearningBatch>(`/api/learning/batches/${encodeURIComponent(id)}`),
  candidates: async (params?: ListParams) => normalizePaged(await request(`/api/learning/candidates${query(params)}`), normalizeCandidate),
  candidate: async (id: string) => normalizeCandidate(await request(`/api/learning/candidates/${encodeURIComponent(id)}`)),
  processPending: () => request<UnknownRecord>("/api/learning/process-pending", { method: "POST" }),
  approveCandidate: async (id: string, reviewerNote?: string) => request<AssetVersion>(`/api/learning/candidates/${encodeURIComponent(id)}/approve`, {
    method: "POST",
    body: JSON.stringify({ reviewerNote: reviewerNote || undefined }),
  }),
  rejectCandidate: async (id: string, reviewerNote: string) => request<LearningCandidate>(`/api/learning/candidates/${encodeURIComponent(id)}/reject`, {
    method: "POST",
    body: JSON.stringify({ reviewerNote }),
  }),
  assets: async () => normalizePaged(await request("/api/assets"), normalizeAsset),
  asset: async (type: string, key: string) => normalizeAsset(await request(`/api/assets/${encodeURIComponent(type)}/${encodeURIComponent(key)}`)),
  assetVersions: async (type: string, key: string) => normalizePaged(await request(`/api/assets/${encodeURIComponent(type)}/${encodeURIComponent(key)}/versions`), normalizeAssetVersion),
};

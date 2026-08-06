export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject { [key: string]: JsonValue }

export type FeedbackTag = "interim" | "final";
export type FeedbackSource = "clarification" | "result_review";
export type FeedbackScope = "parameter" | "scenario" | "run";
export type CandidateStatus = "pending" | "applied" | "rejected" | "conflict" | "failed";

export interface RunMetadata {
  miEventIds: number[];
  targetMarket: string;
  comparisonRunId: string;
}

export interface ExampleDefinition {
  id: string;
  label: string;
  description?: string;
  metadata: RunMetadata;
  scenarioJson: JsonObject;
}

export interface ValidationMessage {
  level: "error" | "warning" | "info" | "pass";
  code?: string;
  path?: string;
  message: string;
}

export interface ClarificationOption {
  value: string;
  label: string;
  description?: string;
}

export interface Clarification {
  id: string;
  question: string;
  required: boolean;
  type?: "single_choice" | "text";
  options: ClarificationOption[];
  allowFreeText?: boolean;
  defaultValue?: string;
}

export interface PlanStep {
  stepId: string;
  label: string;
  status?: "pending" | "completed" | "failed";
  description?: string;
}

export interface AssetSnapshotEntry {
  assetType: string;
  assetKey: string;
  version: number | string;
}

export interface PlanResponse {
  steps: PlanStep[];
  clarifications: Clarification[];
  assumptions: string[];
  validationMessages: ValidationMessage[];
  assetSnapshot: AssetSnapshotEntry[];
  canRun: boolean;
}

export interface SeriesPoint {
  month: string;
  baseline: number;
  proposed: number;
  delta?: number;
  deltaPct?: number;
  phase?: "event" | "recovery" | "baseline" | string;
}

export interface TraceStep {
  step: string;
  label: string;
  summary: string;
  details?: JsonValue;
  status?: "applied" | "excluded" | "warning";
}

export interface ParameterProposal {
  proposalId?: string;
  scenarioKey: string;
  parameterCode: string;
  parameterName: string;
  domain: "demand" | "supply" | "price_only" | string;
  unit?: string;
  periodStart?: string;
  periodEnd?: string;
  baselinePeak: number;
  proposedPeak: number;
  delta: number;
  deltaPct: number;
  confidence: number;
  warningCount: number;
  feedbackAdjusted?: boolean;
  series: SeriesPoint[];
  trace: TraceStep[];
  formula?: string;
  evidence?: JsonValue;
  contributions?: JsonValue;
  eventIds?: number[];
  leverCodes?: string[];
}

export interface DimensionValueRow {
  dimensionId: string;
  valueId: string;
  meaning?: string;
  leverCodes?: string[];
  eventIds?: number[];
}

export interface ScenarioResult {
  scenarioKey: string;
  title: string;
  narrative?: string;
  probability?: number;
  declaredPressureBand?: string;
  computedPressureBand?: string;
  pressureScore?: number;
  pressureConsistency?: "pass" | "warning" | "error" | string;
  mixedFactors?: string[];
  dimensions?: DimensionValueRow[];
  validationMessages?: ValidationMessage[];
}

export interface RevisionLink {
  runId: string;
  revision: number;
  status?: string;
}

export interface RunSummary {
  runId: string;
  rootRunId?: string;
  revision: number;
  parentRunId?: string | null;
  comparisonRunId?: string;
  targetMarket: string;
  eventIds: number[];
  createdAt: string;
  status: string;
  scenarioCount: number;
  proposalCount: number;
  interimFeedbackCount: number;
  finalFeedbackCount: number;
  adjustmentCount: number;
  assetSnapshot: AssetSnapshotEntry[];
}

export interface RunArtifact {
  stepId: string;
  label?: string;
  status: string;
  output?: JsonValue;
  validationMessages?: ValidationMessage[];
  exclusions?: JsonValue;
}

export interface RunDetail extends RunSummary {
  metadata: RunMetadata;
  sourceScenarioJson: JsonObject;
  normalizedInput?: JsonValue;
  horizon?: { start?: string; end?: string; includesRecovery?: boolean };
  clarificationAnswers?: JsonValue;
  validationReport?: JsonValue;
  planSteps?: PlanStep[];
  artifacts?: RunArtifact[];
  proposals: ParameterProposal[];
  scenarios: ScenarioResult[];
  revisionChain: RevisionLink[];
  feedback?: FeedbackRecord[];
  evaluationInvariants?: ValidationMessage[];
  childRunId?: string | null;
  hasFinalFeedback?: boolean;
}

export interface FeedbackRecord {
  feedbackId: string;
  runId: string;
  resultRunId?: string | null;
  revision?: number;
  tag: FeedbackTag;
  source: FeedbackSource;
  scope: FeedbackScope | string;
  rawText: string;
  context: JsonValue;
  adjustment?: JsonValue;
  interpretation?: JsonValue | null;
  answer?: JsonValue;
  recordJson?: JsonValue;
  processingStatus: string;
  learningBatchId?: string | null;
  candidateIds?: string[];
  createdAt: string;
}

export interface FinalFeedbackInput {
  scope: FeedbackScope;
  scenarioKey?: string;
  parameterCode?: string;
  text: string;
}

export interface FinalFeedbackResponse {
  feedback: FeedbackRecord;
  resultRun: RunDetail | RunSummary;
}

export interface LearningBatch {
  batchId: string;
  createdAt: string;
  feedbackIds: string[];
  interimCount: number;
  finalCount: number;
  status: string;
  reviewerMode: string;
  candidateCount: number;
  classificationSummary?: JsonValue;
  reviewSummary?: JsonValue;
}

export interface EvaluationCheck {
  name: string;
  passed: boolean;
  detail?: string;
}

export interface LearningCandidate {
  candidateId: string;
  sourceFeedbackId: string;
  sourceRunId?: string;
  sourceTag?: FeedbackTag;
  sourceContext?: JsonValue;
  sourceFeedbackText?: string;
  targetType: "memory" | "skill" | string;
  targetAssetKey: string;
  baseVersion: number | string;
  proposedVersion: number | string;
  proposedContent?: JsonValue | string;
  changeLine: string;
  diff: string;
  classification?: string;
  matchedSignals?: string[];
  rationale?: string;
  confidence: number;
  evaluations: EvaluationCheck[];
  risks?: string[];
  expectedImpact?: string;
  status: CandidateStatus | string;
  createdAt?: string;
}

export interface AssetVersion {
  assetType: string;
  assetKey: string;
  version: number | string;
  learnable: boolean;
  locked: boolean;
  active: boolean;
  createdAt: string;
  sourceCandidateId?: string | null;
  content: JsonValue | string;
}

export interface AssetSummary {
  assetType: string;
  assetKey: string;
  learnable: boolean;
  locked: boolean;
  activeVersion: number | string;
  versions: AssetVersion[];
}

export interface HealthResponse {
  status: string;
  databaseStatus: string;
  agentMode: string;
  activeAssets?: AssetSnapshotEntry[];
}

export interface PagedResult<T> {
  items: T[];
  total: number;
  pendingCounts?: { interim: number; final: number; total: number };
}

export interface ListParams {
  page?: number;
  pageSize?: number;
  status?: string;
  tag?: string;
  source?: string;
}

export interface PlanInput {
  metadata: RunMetadata;
  scenarioJson: JsonObject;
}

export interface RunInput extends PlanInput {
  clarificationAnswers: Record<string, string>;
}

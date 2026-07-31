export interface EventTypeRef {
  id: number;
  code: string;
  label: string;
}

export interface RelatedScenarioGroup {
  scenarioGroupId: number;
  status: string;
  stage: string;
  deleted: boolean;
  delYn: string;
  scenarioCount: number;
  signpostCount: number;
  title: string | null;
}

export type ScenarioActionType =
  | "create"
  | "continue_generation"
  | "open_detail"
  | "disabled";

export interface ScenarioActionState {
  type: ScenarioActionType;
  label: string;
  disabled: boolean;
  reason: string | null;
}

export interface EventListRow {
  miEventId: number;
  title: string;
  eventTitle: string;
  oneLineSummary: string;
  eventTime: string;
  occurredAt: string;
  category: string;
  eventTypeL1: EventTypeRef;
  eventTypeL2: EventTypeRef;
  newYn: string;
  signalYn: string;
  signalConfidence: number | null;
  signalReason: string | null;
  scenarioSuggestYn: string;
  scenarioSuggestReason: string | null;
  tags: string[];
  relatedScenarioGroup: RelatedScenarioGroup | null;
  scenarioActionState: ScenarioActionState;
}

export interface EventScenarioTemplate {
  eventTypeL2Id?: number;
  scenarioDimensionTemplateId?: number | null;
  eventTypeDefinition?: unknown;
  lngPriceImpactExamples?: unknown;
  templateChecksum?: string | null;
  [key: string]: unknown;
}

export interface EventDetail extends EventListRow {
  keyBullets: string[];
  detailAnalysis: string;
  sourceMiRecordIds: number[];
  createdAt: string;
  updatedAt: string;
  language: string;
  scenarioTemplate?: EventScenarioTemplate;
  source?: Record<string, unknown>;
}

export interface EventListResponse {
  rows: EventListRow[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    hasPrevious: boolean;
    hasNext: boolean;
  };
  source: Record<string, unknown>;
}

export interface EventDetailResponse {
  event: EventDetail;
  scenarioTemplate: EventScenarioTemplate;
  source: Record<string, unknown>;
}

export interface ScenarioTableHeader {
  key: string;
  label: string;
  displayOrder: number;
  [key: string]: unknown;
}

export interface SignpostPayload {
  signpostId: number | null;
  label: string;
  probabilityDirectionCode: string | null;
  probabilityImpactScore?: number | null;
  signpostReason: string | null;
  displayOrder: number | null;
  strength: string | null;
  useYn?: string;
  delYn?: string;
  [key: string]: unknown;
}

export interface ScenarioMetrics {
  probabilityScore?: number | null;
  probabilityDelta?: number | null;
  [key: string]: unknown;
}

export interface RelatedMarket {
  market: "JKM" | "TTF" | "HH";
  rationale: string;
}

export interface ScenarioTableRow {
  scenarioId: number | null;
  displayOrder: number;
  title: string;
  narrative?: string | null;
  cells: Record<string, string | number | boolean | null>;
  metrics?: ScenarioMetrics;
  baselineYn?: string | null;
  globalPressureBand?: string | null;
  scenarioRole?: string | null;
  probabilityScore?: number | null;
  globalPressureRationale?: string | null;
  relatedMarkets?: RelatedMarket[];
  signposts?: SignpostPayload[];
  delYn?: string;
  [key: string]: unknown;
}

export interface ScenarioTable {
  headers: ScenarioTableHeader[];
  rows: ScenarioTableRow[];
}

export interface ScenarioGroupPayload {
  scenarioGroupId: number;
  miEventId?: number | null;
  eventTypeL2Id?: number | null;
  requestUsrId?: number | null;
  title: string;
  summary?: string | null;
  description?: string | null;
  dimensionSelected?: string[];
  scenarioCount?: number;
  status: string;
  stage: string;
  apiVersion?: string;
  generationStrategy?: string;
  comparisonRunId?: string | null;
  impactCatalogVersion?: string | null;
  impactCatalogChecksum?: string | null;
  templateChecksum?: string | null;
  parameterMappingReady?: boolean;
  dimensionDefinitions?: Array<Record<string, unknown>>;
  generationDiagnostics?: Record<string, unknown>;
  delYn?: string;
  [key: string]: unknown;
}

export interface CallbackBody<
  TScenarioGroup extends ScenarioGroupPayload = ScenarioGroupPayload,
  TTable extends ScenarioTable = ScenarioTable
> {
  result: string;
  reason?: string | null;
  isValid?: boolean;
  scenarioGroup?: TScenarioGroup;
  table?: TTable;
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface WrapperBody<T> {
  status: string;
  message: string;
  data: T | null;
}

export interface ConfirmationData {
  scenarioGroupId: number;
  status: string;
  stage: string;
}

export interface ScenarioGroupDetailResponse {
  scenarioGroup: ScenarioGroupPayload;
  table: ScenarioTable;
  scenarioCount: number;
  signpostCount: number;
  deletedScenarioCount: number;
  deletedSignpostCount: number;
}

export interface SoftDeleteResponse {
  scenarioGroupDeleted: number;
  scenarioDeleted: number;
  signpostDeleted: number;
}

export interface CreateScenariosRequest {
  miEventId: number;
  userId: number;
}

export interface TableSyncRequest {
  userId: number;
  table: ScenarioTable;
}

export interface ConfirmationRequest {
  userId: number;
  scenarioGroup: {
    title: string;
    summary: string | null;
    description: string | null;
  };
  table: ScenarioTable;
}

export type ApiVersion = "v2" | "v3" | "v4";

export type GenerationStrategy =
  | "multi_event_source_dimensions"
  | "multi_event_composite_dimensions"
  | "multi_event_model_lever_dimensions";

export type GlobalPressureBand =
  | "strong_bullish"
  | "bullish"
  | "balanced"
  | "bearish"
  | "strong_bearish";

export type SourceType =
  | "event_fact"
  | "template_domain_knowledge"
  | "scenario_assumption"
  | "derived_interpretation";

export interface SourceLineage {
  eventId: number;
  eventTypeL2Id: number;
  dimKey: string;
  value: string | null;
  sourceType: SourceType;
  assumptionYn: "Y" | "N";
  rationale: string;
}

export interface DimensionValueDefinition {
  valueId: string;
  label: string;
  globalPressureContribution: string | null;
  sourceAssignments: SourceLineage[];
}

export interface DimensionDefinition {
  dimensionId: string;
  label: string;
  description: string;
  required: boolean;
  displayOrder: number;
  dimensionType:
    | "magnitude"
    | "scope"
    | "timing"
    | "recovery"
    | "mitigation"
    | "interaction"
    | null;
  valueKind: "categorical" | "numeric_range" | "temporal" | null;
  unit: string | null;
  sourceEventIds: number[];
  leverRefs: string[];
  modelSupportStatus: "full" | "partial" | "none" | "price_only" | null;
  sourceRefs: SourceLineage[];
  values: DimensionValueDefinition[];
}

export interface EventPayload {
  miEventId: number | string;
  eventTypeL2Id: number;
  eventTitleKo: string;
  oneLineSummary: string;
  detailAnalysis: string;
  keyBullets: string[];
  eventType: Record<string, unknown>;
  sourceMiRecordIds: number[];
  createdAt: string;
  updatedAt: string;
  language: string;
  occurredAt: string;
  tags: string[];
}

export interface ExcludedCandidate {
  globalPressureBand: GlobalPressureBand;
  reasonCode: string;
  reason: string;
}

export interface UnsupportedLeverDetail {
  leverCode: string;
  reasonCode:
    | "NO_PARAMETER_BINDING"
    | "INACTIVE_MODEL_PARAMETER"
    | "CATALOG_MARKED_UNSUPPORTED"
    | "PRICE_ONLY";
  parameterName: string | null;
}

export interface GenerationDiagnostics {
  targetPressureBands: string[];
  excludedCandidates: ExcludedCandidate[];
  excludedDimensions: Array<Record<string, unknown>>;
  impactCatalogVersion: string | null;
  coveredDimensions: string[];
  uncoveredDimensions: string[];
  unsupportedLevers: string[];
  unsupportedLeverDetails: UnsupportedLeverDetail[];
  coverageStatus: "full" | "partial" | "none" | null;
  eventImpactFacts: Array<Record<string, unknown>>;
  eventInteractions: Array<Record<string, unknown>>;
}

export interface LlmUsage {
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  [key: string]: unknown;
}

export interface VersionedCreateScenariosData {
  apiVersion: ApiVersion;
  generationStrategy: GenerationStrategy;
  comparisonRunId: string | null;
  impactCatalogVersion: string | null;
  scenarioGroup: ScenarioGroupPayload;
  events: EventPayload[];
  dimensionDefinitions: DimensionDefinition[];
  table: ScenarioTable;
  generationDiagnostics: GenerationDiagnostics;
  usage: LlmUsage | null;
}

export interface VersionedCreateScenariosOut {
  status: "success" | "error";
  message: string;
  data: VersionedCreateScenariosData | null;
  [key: string]: unknown;
}

export interface MultiEventCreateScenariosRequest {
  miEventIds: number[];
  userId: number;
  comparisonRunId: string;
}

export type V4MultiEventCreateScenariosRequest =
  MultiEventCreateScenariosRequest;

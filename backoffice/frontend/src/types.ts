export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type RunLifecycle =
  | "idle"
  | "creating"
  | "generation_waiting_callback"
  | "scenario_created"
  | "validating"
  | "validation_waiting_callback"
  | "scenario_validated"
  | "creating_signposts"
  | "signpost_waiting_callback"
  | "signpost_created"
  | "confirming"
  | "confirmed"
  | "failed";

export type TimelineEventType =
  | "accepted"
  | "callback"
  | "detail_refreshed"
  | "validation_result"
  | "normalized_model_updated"
  | "request_body"
  | "error"
  | "local";

export type TableHeader = {
  key: string;
  label: string;
  displayOrder: number;
};

export type Signpost = {
  id: string;
  label: string;
  direction: string;
  impact: string;
  evidence: string;
};

export type ScenarioRow = {
  localId: string;
  scenarioId?: number;
  displayOrder: number;
  title: string;
  narrative: string;
  cells: Record<string, string>;
  probability: string;
  baselineYn: "Y" | "N";
  signposts: Signpost[];
  status: string;
  edited?: boolean;
};

export type EventItem = {
  miEventId: number;
  title: string;
  summary?: string;
  eventTime: string;
  category: string;
  status: "신규" | "갱신";
  recommended: boolean;
  eventTypeL1?: { id?: number | null; code: string; label: string };
  eventTypeL2?: { id?: number | null; code: string; label: string };
  signalReason?: string | null;
  scenarioSuggestReason?: string | null;
  relatedScenarioGroup?: {
    scenarioGroupId?: number | null;
    status?: string | null;
    stage?: string | null;
    deleted?: boolean;
    scenarioCount?: number;
    signpostCount?: number;
    title?: string | null;
  } | null;
  scenarioActionState?: {
    type: "create" | "continue_generation" | "open_detail" | "disabled";
    label: string;
    disabled: boolean;
    reason?: string | null;
  };
};

export type EventListResponse = {
  rows: Array<{
    miEventId: number;
    title: string;
    oneLineSummary?: string;
    eventTime?: string;
    occurredAt?: string;
    category?: string;
    eventTypeL1?: { id?: number | null; code?: string; label?: string };
    eventTypeL2?: { id?: number | null; code?: string; label?: string };
    newYn?: string;
    signalReason?: string | null;
    scenarioSuggestYn?: string;
    scenarioSuggestReason?: string | null;
    relatedScenarioGroup?: EventItem["relatedScenarioGroup"];
    scenarioActionState?: EventItem["scenarioActionState"];
    raw?: unknown;
  }>;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    hasPrevious: boolean;
    hasNext: boolean;
  };
  meta: {
    source: string;
    fallbackReason?: string | null;
  };
  rawSource?: unknown;
};

export type ScenarioGroupListRow = {
  scenarioGroupId: number;
  title: string;
  baseEventTitle?: string | null;
  miEventId?: number | null;
  status?: string | null;
  stage?: string | null;
  scenarioCount: number;
  signpostCount: number;
  createdAt?: string | null;
  updatedAt?: string | null;
  deleted: boolean;
  delYn: "Y" | "N";
  latestRunId?: string | null;
  source: string;
  raw?: unknown;
};

export type ScenarioGroupListResponse = {
  rows: ScenarioGroupListRow[];
  meta: {
    source: string;
    total: number;
    returned: number;
    includeDeleted: boolean;
    fallbackReason?: string | null;
  };
  rawSource?: unknown;
};

export type ScenarioDesignModel = {
  groupName: string;
  description: string;
  baseEvent: EventItem;
  headers: TableHeader[];
  rows: ScenarioRow[];
};

export type RuntimeConfig = {
  agentBaseUrl: string;
  miEventId: string;
  userId: string;
  runId: string;
  scenarioGroupId: string;
};

export type RunState = {
  lifecycle: RunLifecycle;
  agentStatus: string;
  agentStage: string;
};

export type TimelineEvent = {
  id: string;
  at: string;
  type: TimelineEventType;
  title: string;
  payload: unknown;
};

export type ApiRunResponse = {
  runId?: string;
  run_id?: string;
  scenarioGroupId?: number | string;
  scenario_group_id?: number | string;
  status?: string;
  stage?: string;
  lifecycle?: RunLifecycle;
  data?: Record<string, unknown>;
  [key: string]: unknown;
};

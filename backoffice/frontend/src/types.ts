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
  eventTime: string;
  category: string;
  status: "신규" | "갱신";
  recommended: boolean;
  impacts: Record<"JKM" | "TTF" | "HH", "up" | "down" | "neutral">;
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

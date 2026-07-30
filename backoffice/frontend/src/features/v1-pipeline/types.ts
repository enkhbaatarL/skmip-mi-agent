import type { ApiCallRecord } from "../../domain/apiCall";
import type {
  EventDetail,
  ScenarioGroupDetailResponse,
  ScenarioGroupPayload,
  ScenarioTable
} from "../../domain/apiTypes";
import type { RunStatus } from "../../domain/judgments";
import type { RuntimeSnapshot } from "../../domain/runtime";

export type V1StepId =
  | "create"
  | "validation"
  | "signpost"
  | "confirmation";

export interface StepState {
  status: RunStatus;
  request?: unknown;
  response?: unknown;
  elapsedMs?: number;
  tokenUsage?: number;
  error?: string;
  warning?: string;
  warningAcknowledged?: boolean;
  summary?: string;
}

export interface V1RunState {
  runId: string;
  runtime?: RuntimeSnapshot;
  event?: EventDetail;
  scenarioGroupId?: number;
  currentStep: V1StepId;
  steps: Record<V1StepId, StepState>;
  editableTable?: ScenarioTable;
  lastServerTable?: ScenarioTable;
  scenarioGroup?: ScenarioGroupPayload;
  signposts?: unknown[];
  calls: ApiCallRecord[];
  finalScenarioGroupDetail?: ScenarioGroupDetailResponse;
  startedAt?: string;
  completedAt?: string;
  exported: boolean;
}

export function createEmptyV1Run(): V1RunState {
  return {
    runId:
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `v1-${Date.now()}`,
    currentStep: "create",
    steps: {
      create: { status: "idle" },
      validation: { status: "idle" },
      signpost: { status: "idle" },
      confirmation: { status: "idle" }
    },
    calls: [],
    exported: false
  };
}

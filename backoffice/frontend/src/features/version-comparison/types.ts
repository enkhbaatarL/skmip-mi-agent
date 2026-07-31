import type { ApiCallRecord } from "../../domain/apiCall";
import type {
  ApiVersion,
  EventDetail,
  GenerationStrategy,
  MultiEventCreateScenariosRequest,
  VersionedCreateScenariosOut
} from "../../domain/apiTypes";
import type {
  DeterministicCheckResult
} from "../../domain/deterministicChecks";
import type { RunStatus } from "../../domain/judgments";
import type { RuntimeSnapshot } from "../../domain/runtime";

export interface ManifestEventSnapshot {
  miEventId: number;
  detailStatus: "success" | "error";
  event?: EventDetail;
  error?: string;
}

export interface ComparisonManifest {
  runId: string;
  createdAt: string;
  agentBaseUrl: string;
  userId: number;
  timeoutMs: number;
  comparisonRunId: string;
  miEventIds: number[];
  selectedEvents: ManifestEventSnapshot[];
}

export type VersionRequest = MultiEventCreateScenariosRequest;

export interface VersionRunState {
  version: ApiVersion;
  generationStrategy: GenerationStrategy;
  status: RunStatus;
  request?: VersionRequest;
  response?: VersionedCreateScenariosOut;
  call?: ApiCallRecord;
  startedAt?: string;
  finishedAt?: string;
  elapsedMs?: number;
  integrityIssues: string[];
  error?: string;
}

export interface ComparisonRunState {
  runId: string;
  runtime: RuntimeSnapshot;
  manifest: ComparisonManifest;
  versions: Record<ApiVersion, VersionRunState>;
  checks: Record<ApiVersion, DeterministicCheckResult[]>;
  calls: ApiCallRecord[];
  startedAt: string;
  completedAt?: string;
}

export const VERSION_ORDER: ApiVersion[] = ["v2", "v3", "v4"];

export const VERSION_STRATEGIES: Record<ApiVersion, GenerationStrategy> = {
  v2: "multi_event_source_dimensions",
  v3: "multi_event_composite_dimensions",
  v4: "multi_event_model_lever_dimensions"
};

export function createVersionStates(): Record<ApiVersion, VersionRunState> {
  return {
    v2: {
      version: "v2",
      generationStrategy: VERSION_STRATEGIES.v2,
      status: "ready",
      integrityIssues: []
    },
    v3: {
      version: "v3",
      generationStrategy: VERSION_STRATEGIES.v3,
      status: "ready",
      integrityIssues: []
    },
    v4: {
      version: "v4",
      generationStrategy: VERSION_STRATEGIES.v4,
      status: "ready",
      integrityIssues: []
    }
  };
}

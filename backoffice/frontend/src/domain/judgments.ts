import type { ApiCallOutcome, ApiCallResult } from "./apiCall";
import type {
  ApiVersion,
  CallbackBody,
  ConfirmationData,
  VersionedCreateScenariosOut,
  WrapperBody
} from "./apiTypes";

export type RunStatus =
  | "idle"
  | "ready"
  | "running"
  | "success"
  | "warning"
  | "error"
  | "unknown";

export function transportStatusBeforeBody(
  outcome: ApiCallOutcome
): "body" | "error" | "unknown" {
  if (outcome === "success") return "body";
  if (["timeout", "abort", "network-error", "unknown"].includes(outcome)) {
    return "unknown";
  }
  return "error";
}

export function withTransportJudgment<T>(
  outcome: ApiCallOutcome,
  body: T | undefined,
  judgeBody: (value: T | undefined) => RunStatus
): RunStatus {
  const transport = transportStatusBeforeBody(outcome);
  return transport === "body" ? judgeBody(body) : transport;
}

export function judgeCreate(body: CallbackBody | undefined): RunStatus {
  return body?.result === "success" ? "success" : "error";
}

export function judgeValidation(
  body: CallbackBody | undefined,
  transportOk = true
): RunStatus {
  if (!transportOk || body?.result === "failure") return "error";
  if (body?.scenarioGroup?.stage === "scenario_validated") return "success";
  if (body?.result === "success") return "warning";
  return "error";
}

export function judgeSignpost(body: CallbackBody | undefined): RunStatus {
  return body?.result === "success" ? "success" : "error";
}

export function judgeConfirmation(
  body: WrapperBody<ConfirmationData> | undefined
): RunStatus {
  return body?.status === "success" && body.data?.stage === "completed"
    ? "success"
    : "error";
}

export interface ComparisonJudgmentManifest {
  miEventIds: readonly number[];
}

export interface ComparisonVersionJudgment {
  judgment: RunStatus;
  integrityIssues: string[];
}

function orderedEventIds(body: VersionedCreateScenariosOut): number[] {
  return (body.data?.events ?? []).map((event) => Number(event.miEventId));
}

export function judgeComparisonVersion(
  requestedVersion: ApiVersion,
  manifest: ComparisonJudgmentManifest,
  result: ApiCallResult<VersionedCreateScenariosOut>
): ComparisonVersionJudgment {
  const transport = transportStatusBeforeBody(result.record.transportStatus);
  if (transport !== "body") {
    return {
      judgment: transport,
      integrityIssues: []
    };
  }

  const httpStatus = result.record.httpStatus;
  if (
    httpStatus === undefined ||
    httpStatus < 200 ||
    httpStatus >= 300 ||
    !result.ok
  ) {
    return { judgment: "error", integrityIssues: [] };
  }

  const body = result.data;
  if (body?.status !== "success" || body.data == null) {
    return { judgment: "error", integrityIssues: [] };
  }

  const issues: string[] = [];
  if (body.data.apiVersion !== requestedVersion) {
    issues.push(
      `API_VERSION_MISMATCH: 요청 ${requestedVersion}, 응답 ${body.data.apiVersion}`
    );
  }
  const expectedIds = [...manifest.miEventIds];
  const actualIds = orderedEventIds(body);
  if (
    expectedIds.length !== actualIds.length ||
    expectedIds.some((eventId, index) => eventId !== actualIds[index])
  ) {
    issues.push(
      `EVENT_LINEAGE_MISMATCH: manifest [${expectedIds.join(", ")}], 응답 [${actualIds.join(", ")}]`
    );
  }

  return {
    judgment: issues.length === 0 ? "success" : "error",
    integrityIssues: issues
  };
}

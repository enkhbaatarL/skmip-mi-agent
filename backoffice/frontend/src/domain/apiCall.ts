export type ApiCallOutcome =
  | "success"
  | "http-error"
  | "network-error"
  | "timeout"
  | "abort"
  | "parse-error"
  | "unknown";

export type ApiCallJudgment = "success" | "error" | "unknown";

export interface ApiCallMetadata {
  workflow?: "runtime" | "v1" | "comparison";
  step?: string;
  version?: "v2" | "v3" | "v4";
}

export interface ApiCallRecord {
  id: string;
  url: string;
  method: string;
  request?: unknown;
  requestHeaders?: Record<string, string>;
  startedAt: string;
  finishedAt: string;
  elapsedMs: number;
  httpStatus?: number;
  transportStatus: ApiCallOutcome;
  judgment: ApiCallJudgment;
  metadata?: ApiCallMetadata;
  parsed?: unknown;
  rawText?: string;
  error?: string;
}

export interface ApiCallResult<T> {
  ok: boolean;
  data?: T;
  record: ApiCallRecord;
}

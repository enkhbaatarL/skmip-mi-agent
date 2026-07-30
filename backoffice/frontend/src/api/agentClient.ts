import type {
  ApiCallMetadata,
  ApiCallOutcome,
  ApiCallRecord,
  ApiCallResult
} from "../domain/apiCall";
import { normalizeBaseUrl, type RuntimeSnapshot } from "../domain/runtime";

const REDACTED = "[REDACTED]";
const SENSITIVE_KEY = /authorization|cookie|token|password|secret|api[-_]?key/i;
const TOKEN_COUNTER_KEY =
  /^(?:promptTokens|completionTokens|totalTokens|prompt_tokens|completion_tokens|total_tokens|tokenUsage|token_usage)$/;

export type ApiCallRecorder = (record: ApiCallRecord) => void;
export interface AgentRequestInit extends RequestInit {
  evidence?: ApiCallMetadata;
}

function createRecordId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `call-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isSensitiveKey(key: string): boolean {
  return SENSITIVE_KEY.test(key) && !TOKEN_COUNTER_KEY.test(key);
}

function containsSensitiveKey(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(containsSensitiveKey);
  return Object.entries(value).some(
    ([key, item]) => isSensitiveKey(key) || containsSensitiveKey(item)
  );
}

export function redactSecrets(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactSecrets);
  if (!value || typeof value !== "object") return value;

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      isSensitiveKey(key) ? REDACTED : redactSecrets(item)
    ])
  );
}

function redactHeaders(headers: Headers): Record<string, string> {
  return Object.fromEntries(
    Array.from(headers.entries(), ([key, value]) => [
      key,
      isSensitiveKey(key) ? REDACTED : value
    ])
  );
}

function redactPlainText(value: string): string {
  return value.replace(
    /"([^"]*(?:authorization|cookie|token|password|secret|api[-_]?key)[^"]*)"\s*:\s*"[^"]*"/gi,
    (match, key: string) =>
      isSensitiveKey(key) ? `"${key}":"${REDACTED}"` : match
  );
}

function serializableRequestBody(body: BodyInit | null | undefined): unknown {
  if (body == null) return undefined;
  if (typeof body === "string") {
    try {
      return redactSecrets(JSON.parse(body));
    } catch {
      return redactPlainText(body);
    }
  }
  if (body instanceof URLSearchParams) {
    return redactSecrets(Object.fromEntries(body.entries()));
  }
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    return redactSecrets(Object.fromEntries(body.entries()));
  }
  return `[${body.constructor?.name ?? "Body"}]`;
}

function redactUrl(value: string): string {
  try {
    const url = new URL(value);
    for (const key of Array.from(url.searchParams.keys())) {
      if (isSensitiveKey(key)) url.searchParams.set(key, REDACTED);
    }
    return url.toString();
  } catch {
    return value;
  }
}

export function joinAgentUrl(baseUrl: string, path: string): string {
  const normalizedBase = normalizeBaseUrl(baseUrl);
  return `${normalizedBase}/${path.trim().replace(/^\/+/, "")}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function judgeCall(method: string, outcome: ApiCallOutcome) {
  if (outcome === "success") return "success" as const;
  if (["timeout", "abort", "unknown"].includes(outcome)) {
    return "unknown" as const;
  }
  if (outcome === "network-error" && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    return "unknown" as const;
  }
  return "error" as const;
}

function judgeResponseBody(
  method: string,
  outcome: ApiCallOutcome,
  body: unknown
) {
  const transportJudgment = judgeCall(method, outcome);
  if (
    transportJudgment !== "success" ||
    !body ||
    typeof body !== "object"
  ) {
    return transportJudgment;
  }
  const response = body as Record<string, unknown>;
  if (
    ("result" in response && response.result !== "success") ||
    response.status === "error"
  ) {
    return "error" as const;
  }
  return transportJudgment;
}

export class AgentClient {
  readonly #runtime: RuntimeSnapshot;
  readonly #onRecord?: ApiCallRecorder;
  readonly #defaultMetadata?: ApiCallMetadata;

  constructor(
    runtime: RuntimeSnapshot,
    onRecord?: ApiCallRecorder,
    defaultMetadata?: ApiCallMetadata
  ) {
    this.#runtime = runtime;
    this.#onRecord = onRecord;
    this.#defaultMetadata = defaultMetadata;
  }

  async request<T>(
    path: string,
    init: AgentRequestInit = {}
  ): Promise<ApiCallResult<T>> {
    const { evidence, ...fetchInit } = init;
    const url = joinAgentUrl(this.#runtime.agentBaseUrl, path);
    const method = (fetchInit.method ?? "GET").toUpperCase();
    const headers = new Headers(fetchInit.headers);
    if (this.#runtime.authorization && !headers.has("Authorization")) {
      headers.set("Authorization", this.#runtime.authorization);
    }

    const startedAt = new Date();
    const startedMs = Date.now();
    const controller = new AbortController();
    let timedOut = false;
    let manuallyAborted = false;
    const externalSignal = fetchInit.signal;
    const handleExternalAbort = () => {
      manuallyAborted = true;
      controller.abort(externalSignal?.reason);
    };

    if (externalSignal?.aborted) {
      handleExternalAbort();
    } else {
      externalSignal?.addEventListener("abort", handleExternalAbort, {
        once: true
      });
    }

    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort(new DOMException("Request timed out", "TimeoutError"));
    }, this.#runtime.timeoutMs);

    const finishRecord = (
      transportStatus: ApiCallOutcome,
      details: Partial<ApiCallRecord> = {}
    ): ApiCallRecord => {
      const finishedAt = new Date();
      const record: ApiCallRecord = {
        id: createRecordId(),
        url: redactUrl(url),
        method,
        request: serializableRequestBody(fetchInit.body),
        requestHeaders: redactHeaders(headers),
        metadata:
          this.#defaultMetadata || evidence
            ? { ...this.#defaultMetadata, ...evidence }
            : undefined,
        startedAt: startedAt.toISOString(),
        finishedAt: finishedAt.toISOString(),
        elapsedMs: Math.max(0, Date.now() - startedMs),
        transportStatus,
        judgment: judgeCall(method, transportStatus),
        ...details
      };
      this.#onRecord?.(record);
      return record;
    };

    try {
      const response = await fetch(url, {
        ...fetchInit,
        headers,
        signal: controller.signal
      });
      const responseText = await response.text();
      let parsed: unknown;
      let parseError: Error | undefined;

      if (responseText) {
        try {
          parsed = JSON.parse(responseText);
        } catch (error) {
          parseError =
            error instanceof Error ? error : new Error("Response JSON parse failed");
        }
      }

      const safeParsed = redactSecrets(parsed);
      const safeRawText =
        parsed !== undefined && containsSensitiveKey(parsed)
          ? JSON.stringify(safeParsed)
          : redactPlainText(responseText);
      const transportStatus: ApiCallOutcome = !response.ok
        ? "http-error"
        : parseError
          ? "parse-error"
          : "success";
      const error = !response.ok
        ? `HTTP ${response.status}${response.statusText ? ` ${response.statusText}` : ""}`
        : parseError?.message;
      const record = finishRecord(transportStatus, {
        httpStatus: response.status,
        parsed: safeParsed,
        rawText: safeRawText,
        judgment: judgeResponseBody(method, transportStatus, safeParsed),
        ...(error ? { error } : {})
      });

      return {
        ok: transportStatus === "success",
        ...(safeParsed !== undefined ? { data: safeParsed as T } : {}),
        record
      };
    } catch (error) {
      const transportStatus: ApiCallOutcome = timedOut
        ? "timeout"
        : manuallyAborted ||
            (error instanceof DOMException && error.name === "AbortError")
          ? "abort"
          : error instanceof Error
            ? "network-error"
            : "unknown";
      const record = finishRecord(transportStatus, {
        error:
          transportStatus === "timeout"
            ? `Request timed out after ${this.#runtime.timeoutMs}ms`
            : errorMessage(error)
      });
      return { ok: false, record };
    } finally {
      window.clearTimeout(timeoutId);
      externalSignal?.removeEventListener("abort", handleExternalAbort);
    }
  }

  checkConnection(): Promise<ApiCallResult<unknown>> {
    return this.request("/events?page=1&pageSize=1", {
      method: "GET",
      evidence: { workflow: "runtime", step: "connection-check" }
    });
  }
}

export function createAgentClient(
  runtime: RuntimeSnapshot,
  onRecord?: ApiCallRecorder,
  defaultMetadata?: ApiCallMetadata
): AgentClient {
  return new AgentClient(runtime, onRecord, defaultMetadata);
}

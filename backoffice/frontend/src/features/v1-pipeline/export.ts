import { redactSecrets } from "../../api/agentClient";
import type { V1RunState } from "./types";

const REDACTED = "[REDACTED]";
const TOKEN_COUNTER_KEY =
  /^(?:promptTokens|completionTokens|totalTokens|prompt_tokens|completion_tokens|total_tokens|tokenUsage|token_usage)$/;
const SENSITIVE_PLAIN_TEXT =
  /"([^"]*(?:authorization|cookie|token|password|secret|api[-_]?key)[^"]*)"\s*:\s*"[^"]*"/gi;

function sanitize(value: unknown): unknown {
  if (typeof value === "string") {
    return value.replace(
      SENSITIVE_PLAIN_TEXT,
      (match, key: string) =>
        TOKEN_COUNTER_KEY.test(key) ? match : `"${key}":"${REDACTED}"`
    );
  }
  const redacted = redactSecrets(value);
  if (Array.isArray(redacted)) return redacted.map(sanitize);
  if (redacted && typeof redacted === "object") {
    return Object.fromEntries(
      Object.entries(redacted).map(([key, item]) => [key, sanitize(item)])
    );
  }
  return redacted;
}

export function buildV1ExportBundle(runState: V1RunState) {
  const runtime = runState.runtime
    ? {
        agentBaseUrl: runState.runtime.agentBaseUrl,
        userId: runState.runtime.userId,
        timeoutMs: runState.runtime.timeoutMs
      }
    : undefined;

  return sanitize({
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    runId: runState.runId,
    runtime,
    eventDetail: runState.event,
    scenarioGroupId: runState.scenarioGroupId,
    currentStep: runState.currentStep,
    steps: runState.steps,
    calls: runState.calls,
    finalScenarioGroupDetail: runState.finalScenarioGroupDetail
  });
}

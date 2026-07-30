import type { ComparisonRunState } from "../features/version-comparison/types";
import { totalTokens } from "./tokenUsage";

const REDACTED = "[REDACTED]";
const SENSITIVE_KEY =
  /authorization|cookie|password|secret|api[-_]?key|token/i;
const TOKEN_COUNTER_KEY =
  /^(?:promptTokens|completionTokens|totalTokens|prompt_tokens|completion_tokens|total_tokens|tokenUsage|token_usage)$/;
const SENSITIVE_PLAIN_TEXT =
  /("[^"]*(?:authorization|cookie|token|password|secret|api[-_]?key)[^"]*"\s*:\s*)"[^"]*"/gi;

function sanitize(value: unknown): unknown {
  if (typeof value === "string") {
    return value.replace(SENSITIVE_PLAIN_TEXT, `$1"${REDACTED}"`);
  }
  if (Array.isArray(value)) return value.map(sanitize);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      SENSITIVE_KEY.test(key) && !TOKEN_COUNTER_KEY.test(key)
        ? REDACTED
        : sanitize(item)
    ])
  );
}

export function buildComparisonExportBundle(
  comparisonRunState: ComparisonRunState
): unknown {
  const { runtime, manifest, versions, checks } = comparisonRunState;
  const versionEntries = Object.fromEntries(
    (["v2", "v3", "v4"] as const).map((version) => {
      const state = versions[version];
      return [
        version,
        {
          request: state.request,
          response: state.response,
          rawResponse: state.call?.rawText,
          transportStatus: state.call?.transportStatus,
          apiStatus: state.response?.status,
          judgment: state.status,
          integrityIssues: state.integrityIssues,
          httpStatus: state.call?.httpStatus,
          startedAt: state.startedAt,
          finishedAt: state.finishedAt,
          elapsedMs: state.elapsedMs,
          tokenUsage: {
            raw: state.response?.data?.usage,
            totalTokens: totalTokens(state.response?.data?.usage)
          },
          error: state.error,
          deterministicChecks: checks[version]
        }
      ];
    })
  );

  return sanitize({
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    runId: comparisonRunState.runId,
    runtime: {
      agentBaseUrl: runtime.agentBaseUrl,
      userId: runtime.userId,
      timeoutMs: runtime.timeoutMs
    },
    manifest,
    selectedEventSnapshots: manifest.selectedEvents,
    targetMarket: {
      value: manifest.targetMarket,
      selectionReason: manifest.targetMarketReason
    },
    versions: versionEntries,
    calls: comparisonRunState.calls,
    startedAt: comparisonRunState.startedAt,
    completedAt: comparisonRunState.completedAt
  });
}

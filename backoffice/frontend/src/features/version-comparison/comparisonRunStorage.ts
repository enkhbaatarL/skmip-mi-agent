import { redactSecrets } from "../../api/agentClient";
import type {
  ApiVersion,
  EventDetail
} from "../../domain/apiTypes";
import type { ComparisonRunState } from "./types";

export const COMPARISON_RUN_STORAGE_KEY =
  "scenario-comparison.latest-comparison-run";
const MAX_STORED_CHARACTERS = 4_500_000;
const TOKEN_COUNTER_KEY =
  /^(?:promptTokens|completionTokens|totalTokens|prompt_tokens|completion_tokens|total_tokens|tokenUsage|token_usage)$/;
const SENSITIVE_PLAIN_TEXT =
  /"([^"]*(?:authorization|cookie|token|password|secret|api[-_]?key)[^"]*)"\s*:\s*"[^"]*"/gi;

function sanitizeStrings(value: unknown): unknown {
  if (typeof value === "string") {
    return value.replace(
      SENSITIVE_PLAIN_TEXT,
      (match, key: string) =>
        TOKEN_COUNTER_KEY.test(key)
          ? match
          : `"${key}":"[REDACTED]"`
    );
  }
  if (Array.isArray(value)) return value.map(sanitizeStrings);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      sanitizeStrings(item)
    ])
  );
}

function browserStorage(): Storage | undefined {
  try {
    return window.sessionStorage;
  } catch {
    return undefined;
  }
}

export function saveComparisonRun(
  run: ComparisonRunState,
  storage: Storage | undefined = browserStorage()
): boolean {
  if (!storage) return false;
  const safeRun = sanitizeStrings(
    redactSecrets({
      ...run,
      runtime: {
        agentBaseUrl: run.runtime.agentBaseUrl,
        userId: run.runtime.userId,
        timeoutMs: run.runtime.timeoutMs
      }
    })
  );
  const serialized = JSON.stringify(safeRun);
  if (serialized.length > MAX_STORED_CHARACTERS) return false;
  try {
    storage.setItem(COMPARISON_RUN_STORAGE_KEY, serialized);
    return true;
  } catch {
    return false;
  }
}

export function clearComparisonRun(
  storage: Storage | undefined = browserStorage()
): void {
  storage?.removeItem(COMPARISON_RUN_STORAGE_KEY);
}

export function loadComparisonRun(
  storage: Storage | undefined = browserStorage()
): ComparisonRunState | undefined {
  if (!storage) return undefined;
  try {
    const parsed = JSON.parse(
      storage.getItem(COMPARISON_RUN_STORAGE_KEY) ?? "null"
    ) as ComparisonRunState | null;
    if (
      !parsed ||
      typeof parsed.runId !== "string" ||
      !parsed.manifest ||
      !parsed.versions
    ) {
      return undefined;
    }
    if (parsed.completedAt) return parsed;

    const recoveredAt = new Date().toISOString();
    for (const version of ["v2", "v3", "v4"] as ApiVersion[]) {
      if (["ready", "running"].includes(parsed.versions[version].status)) {
        parsed.versions[version] = {
          ...parsed.versions[version],
          status: "unknown",
          finishedAt: recoveredAt,
          error:
            "새로고침으로 실행 상태를 확인할 수 없습니다. 동일 POST를 자동 재개하지 않습니다."
        };
      }
    }
    parsed.completedAt = recoveredAt;
    return parsed;
  } catch {
    return undefined;
  }
}

export function restoredEvents(run: ComparisonRunState | undefined): EventDetail[] {
  return (run?.manifest.selectedEvents ?? []).flatMap((snapshot) =>
    snapshot.event ? [snapshot.event] : []
  );
}

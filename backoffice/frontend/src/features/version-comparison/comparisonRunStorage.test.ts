import { describe, expect, it } from "vitest";
import { makeManifest } from "../../test/comparisonFixtures";
import {
  createVersionStates,
  type ComparisonRunState
} from "./types";
import {
  COMPARISON_RUN_STORAGE_KEY,
  loadComparisonRun,
  saveComparisonRun
} from "./comparisonRunStorage";

function state(): ComparisonRunState {
  const manifest = makeManifest();
  const versions = createVersionStates();
  versions.v2.status = "running";
  return {
    runId: manifest.runId,
    runtime: {
      agentBaseUrl: manifest.agentBaseUrl,
      userId: manifest.userId,
      timeoutMs: manifest.timeoutMs,
      authorization: "Bearer memory-secret"
    },
    manifest,
    versions,
    checks: { v2: [], v3: [], v4: [] },
    calls: [],
    startedAt: manifest.createdAt
  };
}

describe("comparison refresh recovery", () => {
  it("stores no authorization and restores in-flight versions as unknown without retry", () => {
    const run = state();
    run.calls.push({
      id: "call",
      url: "https://agent.example.com",
      method: "POST",
      startedAt: "",
      finishedAt: "",
      elapsedMs: 1,
      transportStatus: "success",
      judgment: "success",
      rawText:
        '{"authorization":"raw-memory-secret","usage":{"total_tokens":30}}'
    });
    expect(saveComparisonRun(run, localStorage)).toBe(true);
    const stored = localStorage.getItem(COMPARISON_RUN_STORAGE_KEY);
    expect(stored).not.toContain("memory-secret");
    expect(stored).not.toContain("raw-memory-secret");
    expect(stored).toContain('\\"total_tokens\\":30');

    const restored = loadComparisonRun(localStorage);
    expect(restored?.versions.v2.status).toBe("unknown");
    expect(restored?.versions.v2.error).toContain("자동 재개하지 않습니다");
    expect(restored?.completedAt).toEqual(expect.any(String));
  });
});

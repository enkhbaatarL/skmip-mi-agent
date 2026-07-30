import { describe, expect, it } from "vitest";
import { buildComparisonExportBundle } from "./exportBundle";
import { runDeterministicChecks } from "./deterministicChecks";
import {
  makeApiResult,
  makeManifest,
  makeResponse
} from "../test/comparisonFixtures";
import {
  createVersionStates,
  type ComparisonRunState
} from "../features/version-comparison/types";

describe("comparison export bundle", () => {
  it("keeps evidence and token usage while redacting every secret value", () => {
    const manifest = makeManifest();
    const response = makeResponse("v2");
    response.authorizationToken = "response-secret";
    const result = makeApiResult(response, {
      requestHeaders: {
        Authorization: "Bearer request-secret",
        Cookie: "session=cookie-secret"
      },
      rawText:
        '{"authorizationToken":"raw-secret","usage":{"totalTokens":30}}'
    });
    const versions = createVersionStates();
    versions.v2 = {
      ...versions.v2,
      status: "success",
      request: {
        miEventIds: [101, 202],
        userId: 10001,
        comparisonRunId: "multi-event-test"
      },
      response,
      call: result.record,
      startedAt: result.record.startedAt,
      finishedAt: result.record.finishedAt,
      elapsedMs: result.record.elapsedMs
    };
    const state: ComparisonRunState = {
      runId: manifest.runId,
      runtime: {
        agentBaseUrl: manifest.agentBaseUrl,
        userId: manifest.userId,
        timeoutMs: manifest.timeoutMs,
        authorization: "Bearer runtime-secret"
      },
      manifest,
      versions,
      checks: {
        v2: runDeterministicChecks("v2", response.data ?? undefined, manifest),
        v3: [],
        v4: []
      },
      calls: [result.record],
      startedAt: manifest.createdAt,
      completedAt: "2026-07-30T00:00:01.000Z"
    };

    const json = JSON.stringify(buildComparisonExportBundle(state));
    expect(json).not.toContain("runtime-secret");
    expect(json).not.toContain("request-secret");
    expect(json).not.toContain("cookie-secret");
    expect(json).not.toContain("response-secret");
    expect(json).not.toContain("raw-secret");
    expect(json).toContain("[REDACTED]");
    expect(json).toContain('"totalTokens":30');
    expect(json).toContain('"deterministicChecks"');
  });
});

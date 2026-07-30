import { describe, expect, it } from "vitest";
import { buildV1ExportBundle } from "./export";
import { createEmptyV1Run } from "./types";

describe("buildV1ExportBundle", () => {
  it("removes authorization and secret-like values", () => {
    const run = createEmptyV1Run();
    run.runtime = {
      agentBaseUrl: "https://agent.example.com",
      userId: 10001,
      timeoutMs: 1_000,
      authorization: "Bearer runtime-secret"
    };
    run.steps.create = {
      status: "error",
      request: { token: "request-secret" },
      response: { nested: { password: "response-secret" } }
    };
    run.calls = [
      {
        id: "1",
        url: "https://agent.example.com",
        method: "POST",
        requestHeaders: { authorization: "Bearer header-secret" },
        rawText: '{"apiKey":"raw-secret"}',
        startedAt: "",
        finishedAt: "",
        elapsedMs: 1,
        transportStatus: "success",
        judgment: "success"
      }
    ];

    const serialized = JSON.stringify(buildV1ExportBundle(run));
    expect(serialized).not.toContain("runtime-secret");
    expect(serialized).not.toContain("request-secret");
    expect(serialized).not.toContain("response-secret");
    expect(serialized).not.toContain("header-secret");
    expect(serialized).not.toContain("raw-secret");
    expect(serialized).toContain("[REDACTED]");
  });
});

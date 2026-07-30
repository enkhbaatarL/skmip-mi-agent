import { afterEach, describe, expect, it, vi } from "vitest";
import type { RuntimeSnapshot } from "../domain/runtime";
import {
  AgentClient,
  joinAgentUrl
} from "./agentClient";

const runtime: RuntimeSnapshot = {
  agentBaseUrl: "https://agent.example.com/ingress",
  userId: 10603,
  timeoutMs: 5_000
};

function mockFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function abortingFetch() {
  const fetchMock = vi.fn((_url: RequestInfo | URL, init?: RequestInit) => {
    return new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener(
        "abort",
        () => reject(new DOMException("Aborted", "AbortError")),
        { once: true }
      );
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("AgentClient", () => {
  it("joins relative paths without discarding the Base URL path prefix", () => {
    expect(
      joinAgentUrl(" https://agent.example.com/ingress/ ", "/events?page=1")
    ).toBe("https://agent.example.com/ingress/events?page=1");
  });

  it("records a 2xx JSON response with parsed and raw forms", async () => {
    mockFetch(
      new Response(JSON.stringify({ status: "success", rows: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    const result = await new AgentClient(runtime).checkConnection();

    expect(result.ok).toBe(true);
    expect(result.record).toMatchObject({
      url: "https://agent.example.com/ingress/events?page=1&pageSize=1",
      method: "GET",
      httpStatus: 200,
      transportStatus: "success",
      parsed: { status: "success", rows: [] },
      rawText: '{"status":"success","rows":[]}'
    });
    expect(result.record.startedAt).toEqual(expect.any(String));
    expect(result.record.finishedAt).toEqual(expect.any(String));
    expect(result.record.elapsedMs).toEqual(expect.any(Number));
  });

  it("records non-2xx response details as an HTTP error", async () => {
    mockFetch(
      new Response(JSON.stringify({ detail: "not found" }), {
        status: 404,
        statusText: "Not Found"
      })
    );

    const result = await new AgentClient(runtime).request("/missing");

    expect(result.ok).toBe(false);
    expect(result.record).toMatchObject({
      httpStatus: 404,
      transportStatus: "http-error",
      parsed: { detail: "not found" },
      error: "HTTP 404 Not Found"
    });
  });

  it("preserves a non-JSON response as raw text and reports a parse error", async () => {
    mockFetch(new Response("plain upstream response", { status: 200 }));

    const result = await new AgentClient(runtime).request("/plain");

    expect(result.ok).toBe(false);
    expect(result.record.transportStatus).toBe("parse-error");
    expect(result.record.rawText).toBe("plain upstream response");
    expect(result.record.parsed).toBeUndefined();
  });

  it.each([
    [{ result: "failure", reason: "duplicate" }, "result=failure"],
    [{ status: "error", message: "generation failed", data: null }, "status=error"]
  ])("marks HTTP 200 API-body failures as Evidence errors (%s)", async (body, _label) => {
    mockFetch(
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    const result = await new AgentClient(runtime).request("/sync", {
      method: "POST"
    });

    expect(result.ok).toBe(true);
    expect(result.record.transportStatus).toBe("success");
    expect(result.record.judgment).toBe("error");
  });

  it("distinguishes timeout from a manual abort", async () => {
    vi.useFakeTimers();
    abortingFetch();
    const shortRuntime = { ...runtime, timeoutMs: 25 };

    const timeoutPromise = new AgentClient(shortRuntime).request("/slow");
    await vi.advanceTimersByTimeAsync(25);
    const timeoutResult = await timeoutPromise;
    expect(timeoutResult.record.transportStatus).toBe("timeout");
    expect(timeoutResult.record.judgment).toBe("unknown");

    const controller = new AbortController();
    const abortPromise = new AgentClient(runtime).request("/manual", {
      signal: controller.signal
    });
    controller.abort();
    const abortResult = await abortPromise;
    expect(abortResult.record.transportStatus).toBe("abort");
    expect(abortResult.record.judgment).toBe("unknown");
  });

  it("redacts Authorization and token fields from serializable records", async () => {
    mockFetch(
      new Response(
        JSON.stringify({ status: "success", refreshToken: "response-secret" }),
        { status: 200 }
      )
    );
    const client = new AgentClient({
      ...runtime,
      authorization: "Bearer header-secret"
    });

    const result = await client.request("/submit", {
      method: "POST",
      headers: {
        Authorization: "Bearer override-secret",
        "X-Trace-Token": "trace-secret",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        userId: 10603,
        token: "body-secret",
        nested: { password: "nested-secret" }
      })
    });
    const serialized = JSON.stringify(result.record);

    expect(result.record.requestHeaders).toMatchObject({
      authorization: "[REDACTED]",
      "x-trace-token": "[REDACTED]"
    });
    expect(result.record.request).toEqual({
      userId: 10603,
      token: "[REDACTED]",
      nested: { password: "[REDACTED]" }
    });
    expect(result.record.parsed).toEqual({
      status: "success",
      refreshToken: "[REDACTED]"
    });
    expect(serialized).not.toContain("secret");
  });

  it("preserves non-secret LLM token counters", async () => {
    mockFetch(
      new Response(
        JSON.stringify({
          usage: {
            prompt_tokens: 10,
            completion_tokens: 20,
            total_tokens: 30
          },
          token: "response-secret"
        }),
        { status: 200 }
      )
    );

    const result = await new AgentClient(runtime).request("/usage");

    expect(result.data).toEqual({
      usage: {
        prompt_tokens: 10,
        completion_tokens: 20,
        total_tokens: 30
      },
      token: "[REDACTED]"
    });
    expect(result.record.rawText).toContain('"total_tokens":30');
    expect(result.record.rawText).not.toContain("response-secret");
  });

  it("merges workflow defaults with request step/version metadata", async () => {
    mockFetch(new Response(JSON.stringify({ status: "success" }), { status: 200 }));
    const client = new AgentClient(runtime, undefined, {
      workflow: "comparison"
    });

    const result = await client.request("/v2/scenario-groups/sync", {
      method: "POST",
      evidence: { step: "version-create", version: "v2" }
    });

    expect(result.record.metadata).toEqual({
      workflow: "comparison",
      step: "version-create",
      version: "v2"
    });
  });

  it("never retries a failed request automatically", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const result = await new AgentClient(runtime).request("/fails");

    expect(result.record.transportStatus).toBe("network-error");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

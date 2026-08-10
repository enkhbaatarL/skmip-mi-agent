import { describe, expect, it, vi } from "vitest";
import type { AgentClient } from "./agentClient";
import type { ApiCallResult } from "../domain/apiCall";
import type { VersionedCreateScenariosOut } from "../domain/apiTypes";
import {
  makeApiResult,
  makeManifest,
  makeResponse
} from "../test/comparisonFixtures";
import {
  hasVersionRun,
  runComparison,
  runVersion
} from "./multiEventComparison";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("multi-event comparison orchestration", () => {
  it("runs v2, v3, and v4 sequentially with the same request", async () => {
    const pending = {
      v2: deferred<ApiCallResult<VersionedCreateScenariosOut>>(),
      v3: deferred<ApiCallResult<VersionedCreateScenariosOut>>(),
      v4: deferred<ApiCallResult<VersionedCreateScenariosOut>>()
    };
    const request = vi.fn((path: string, _init?: RequestInit) => {
      const version = path.slice(1, 3) as keyof typeof pending;
      return pending[version].promise;
    });
    const client = { request } as unknown as Pick<AgentClient, "request">;
    const manifest = makeManifest();

    const execution = runComparison(client, manifest);
    expect(request).toHaveBeenCalledTimes(1);
    expect(request.mock.calls[0][0]).toBe("/v2/scenario-groups/sync");

    pending.v2.resolve(makeApiResult(makeResponse("v2")));
    await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(2));
    expect(request.mock.calls[1][0]).toBe("/v3/scenario-groups/sync");

    pending.v3.resolve(makeApiResult(makeResponse("v3")));
    await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(3));
    expect(request.mock.calls[2][0]).toBe("/v4/scenario-groups/sync");

    const v2Body = JSON.parse(
      String((request.mock.calls[0][1] as RequestInit).body)
    );
    const v3Body = JSON.parse(
      String((request.mock.calls[1][1] as RequestInit).body)
    );
    const v4Body = JSON.parse(
      String((request.mock.calls[2][1] as RequestInit).body)
    );
    expect(v2Body).toEqual(v3Body);
    expect(v4Body).toEqual(v2Body);
    expect(v2Body).toEqual({
      miEventIds: [101, 202],
      userId: 10001
    });

    pending.v4.resolve(makeApiResult(makeResponse("v4")));
    const results = await execution;
    expect(results.v2.status).toBe("fulfilled");
    expect(results.v3.status).toBe("fulfilled");
    expect(results.v4.status).toBe("fulfilled");
  });

  it("continues with later versions after an earlier version rejects", async () => {
    const request = vi
      .fn()
      .mockRejectedValueOnce(new Error("v2 failed"))
      .mockResolvedValueOnce(makeApiResult(makeResponse("v3")))
      .mockResolvedValueOnce(makeApiResult(makeResponse("v4")));
    const client = { request } as unknown as Pick<AgentClient, "request">;

    const results = await runComparison(client, makeManifest());

    expect(request.mock.calls.map(([path]) => path)).toEqual([
      "/v2/scenario-groups/sync",
      "/v3/scenario-groups/sync",
      "/v4/scenario-groups/sync"
    ]);
    expect(results.v2.status).toBe("rejected");
    expect(results.v3.status).toBe("fulfilled");
    expect(results.v4.status).toBe("fulfilled");
  });

  it("claims each (runId, version) before POST and blocks all retries", async () => {
    const manifest = makeManifest();
    const request = vi.fn().mockResolvedValue(makeApiResult(makeResponse("v2")));
    const client = { request } as unknown as Pick<AgentClient, "request">;

    await runVersion(client, "v2", manifest);
    expect(hasVersionRun(manifest.runId, "v2")).toBe(true);
    await expect(runVersion(client, "v2", manifest)).rejects.toThrow(
      "이미 실행"
    );
    expect(request).toHaveBeenCalledTimes(1);
  });
});

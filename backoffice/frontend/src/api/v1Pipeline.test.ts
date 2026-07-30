import { describe, expect, it, vi } from "vitest";
import { AgentClient } from "./agentClient";
import {
  confirmGeneration,
  createScenarios,
  createSignposts,
  getEventDetail,
  getScenarioGroupDetail,
  softDeleteScenarioGroup,
  validateScenarios
} from "./v1Pipeline";

const runtime = {
  agentBaseUrl: "https://agent.example.com",
  userId: 10001,
  timeoutMs: 5_000
};

function response(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}

describe("v1 pipeline API", () => {
  it("uses exact paths/bodies and one request per helper", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => response({ event: { miEventId: 7 } }))
      .mockImplementationOnce(() =>
        response({
          result: "success",
          scenarioGroup: { scenarioGroupId: 9 },
          table: { headers: [], rows: [] }
        })
      )
      .mockImplementationOnce(() =>
        response({
          result: "success",
          isValid: false,
          reason: "invalid",
          scenarioGroup: { scenarioGroupId: 9, stage: "scenario_created" }
        })
      )
      .mockImplementationOnce(() => response({ result: "success" }))
      .mockImplementationOnce(() =>
        response({
          scenarioGroup: { scenarioGroupId: 9 },
          table: { headers: [], rows: [] }
        })
      )
      .mockImplementationOnce(() =>
        response({
          status: "success",
          message: "ok",
          data: { scenarioGroupId: 9, status: "created", stage: "completed" }
        })
      )
      .mockImplementationOnce(() =>
        response({
          scenarioGroupDeleted: 1,
          scenarioDeleted: 2,
          signpostDeleted: 3
        })
      );
    vi.stubGlobal("fetch", fetchMock);
    const client = new AgentClient(runtime);
    const table = { headers: [], rows: [] };

    await getEventDetail(client, 7);
    await createScenarios(client, { miEventId: 7, userId: 10001 });
    const validation = await validateScenarios(client, 9, {
      userId: 10001,
      table
    });
    await createSignposts(client, 9, { userId: 10001, table });
    await getScenarioGroupDetail(client, 9);
    await confirmGeneration(client, 9, {
      userId: 10001,
      scenarioGroup: { title: "g", summary: null, description: null },
      table
    });
    await softDeleteScenarioGroup(client, 9, { userId: 10001 }, "admin");

    expect(fetchMock).toHaveBeenCalledTimes(7);
    expect(validation.status).toBe("warning");
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      "https://agent.example.com/events/7",
      "https://agent.example.com/scenario-groups/sync",
      "https://agent.example.com/scenario-groups/9/validation/sync",
      "https://agent.example.com/scenario-groups/9/signposts/sync",
      "https://agent.example.com/scenario-groups/9",
      "https://agent.example.com/scenario-groups/9/confirmation",
      "https://agent.example.com/scenario-groups/9"
    ]);
    expect(fetchMock.mock.calls[6][1]?.headers).toBeInstanceOf(Headers);
    expect(
      (fetchMock.mock.calls[6][1]?.headers as Headers).get("Authorization")
    ).toBe("Bearer admin");
  });

  it("does not show HTTP 200 failure bodies as success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => response({ result: "failure", reason: "duplicate" }))
    );
    const result = await createScenarios(new AgentClient(runtime), {
      miEventId: 7,
      userId: 10001
    });
    expect(result.status).toBe("error");
  });
});

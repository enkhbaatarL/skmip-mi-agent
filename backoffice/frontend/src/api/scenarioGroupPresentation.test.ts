import { describe, expect, it, vi } from "vitest";
import type { AgentClient } from "./agentClient";
import { getScenarioGroupPresentation } from "./scenarioGroupPresentation";

describe("scenario group presentation API", () => {
  it("uses the dedicated endpoint and operationId query", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true });
    const client = { request } as unknown as Pick<AgentClient, "request">;

    await getScenarioGroupPresentation(client, 120, "01JABC+DEF");

    expect(request).toHaveBeenCalledWith(
      "/scenario-groups/120/presentation?operationId=01JABC%2BDEF",
      expect.objectContaining({
        method: "GET",
        evidence: { step: "scenario-group-presentation" }
      })
    );
  });
});

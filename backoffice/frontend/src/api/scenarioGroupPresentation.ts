import type { AgentClient } from "./agentClient";
import type { ApiCallResult } from "../domain/apiCall";
import type { ScenarioGroupPresentationResponse } from "../domain/apiTypes";

export function getScenarioGroupPresentation(
  client: Pick<AgentClient, "request">,
  scenarioGroupId: number,
  operationId?: string,
  signal?: AbortSignal
): Promise<ApiCallResult<ScenarioGroupPresentationResponse>> {
  const query = operationId
    ? `?operationId=${encodeURIComponent(operationId)}`
    : "";
  return client.request<ScenarioGroupPresentationResponse>(
    `/scenario-groups/${scenarioGroupId}/presentation${query}`,
    {
      method: "GET",
      signal,
      evidence: { step: "scenario-group-presentation" }
    }
  );
}

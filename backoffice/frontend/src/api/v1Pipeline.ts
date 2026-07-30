import type { AgentClient, AgentRequestInit } from "./agentClient";
import type { ApiCallResult } from "../domain/apiCall";
import type {
  CallbackBody,
  ConfirmationData,
  ConfirmationRequest,
  CreateScenariosRequest,
  EventDetailResponse,
  ScenarioGroupDetailResponse,
  SoftDeleteResponse,
  TableSyncRequest,
  WrapperBody
} from "../domain/apiTypes";
import {
  judgeConfirmation,
  judgeCreate,
  judgeSignpost,
  judgeValidation,
  withTransportJudgment,
  type RunStatus
} from "../domain/judgments";

export type JudgedApiCallResult<T> = ApiCallResult<T> & {
  status: RunStatus;
};

function jsonRequest(body: unknown, init: AgentRequestInit = {}): AgentRequestInit {
  return {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers
    },
    body: JSON.stringify(body)
  };
}

function attachStatus<T>(
  result: ApiCallResult<T>,
  judge: (body: T | undefined) => RunStatus
): JudgedApiCallResult<T> {
  return {
    ...result,
    status: withTransportJudgment(
      result.record.transportStatus,
      result.data,
      judge
    )
  };
}

export async function getEventDetail(
  client: AgentClient,
  miEventId: number
): Promise<JudgedApiCallResult<EventDetailResponse>> {
  const result = await client.request<EventDetailResponse>(
    `/events/${miEventId}`,
    { method: "GET", evidence: { step: "event-detail" } }
  );
  return attachStatus(result, (body) => body?.event ? "success" : "error");
}

export async function createScenarios(
  client: AgentClient,
  request: CreateScenariosRequest,
  signal?: AbortSignal
): Promise<JudgedApiCallResult<CallbackBody>> {
  const result = await client.request<CallbackBody>(
    "/scenario-groups/sync",
    jsonRequest(request, {
      method: "POST",
      signal,
      evidence: { step: "create" }
    })
  );
  return attachStatus(result, judgeCreate);
}

export async function validateScenarios(
  client: AgentClient,
  scenarioGroupId: number,
  request: TableSyncRequest,
  signal?: AbortSignal
): Promise<JudgedApiCallResult<CallbackBody>> {
  const result = await client.request<CallbackBody>(
    `/scenario-groups/${scenarioGroupId}/validation/sync`,
    jsonRequest(request, {
      method: "POST",
      signal,
      evidence: { step: "validation" }
    })
  );
  return attachStatus(result, (body) => judgeValidation(body, result.ok));
}

export async function createSignposts(
  client: AgentClient,
  scenarioGroupId: number,
  request: TableSyncRequest,
  signal?: AbortSignal
): Promise<JudgedApiCallResult<CallbackBody>> {
  const result = await client.request<CallbackBody>(
    `/scenario-groups/${scenarioGroupId}/signposts/sync`,
    jsonRequest(request, {
      method: "POST",
      signal,
      evidence: { step: "signpost" }
    })
  );
  return attachStatus(result, judgeSignpost);
}

export async function getScenarioGroupDetail(
  client: AgentClient,
  scenarioGroupId: number,
  signal?: AbortSignal
): Promise<JudgedApiCallResult<ScenarioGroupDetailResponse>> {
  const result = await client.request<ScenarioGroupDetailResponse>(
    `/scenario-groups/${scenarioGroupId}`,
    {
      method: "GET",
      signal,
      evidence: { step: "confirmation-detail" }
    }
  );
  return attachStatus(
    result,
    (body) => body?.scenarioGroup && body.table ? "success" : "error"
  );
}

export async function confirmGeneration(
  client: AgentClient,
  scenarioGroupId: number,
  request: ConfirmationRequest,
  signal?: AbortSignal
): Promise<JudgedApiCallResult<WrapperBody<ConfirmationData>>> {
  const result = await client.request<WrapperBody<ConfirmationData>>(
    `/scenario-groups/${scenarioGroupId}/confirmation`,
    jsonRequest(request, {
      method: "POST",
      signal,
      evidence: { step: "confirmation" }
    })
  );
  return attachStatus(result, judgeConfirmation);
}

export async function softDeleteScenarioGroup(
  client: AgentClient,
  scenarioGroupId: number,
  request: { userId: number },
  authorizationToken?: string
): Promise<JudgedApiCallResult<SoftDeleteResponse>> {
  const token = authorizationToken?.trim();
  const result = await client.request<SoftDeleteResponse>(
    `/scenario-groups/${scenarioGroupId}`,
    jsonRequest(request, {
      method: "DELETE",
      evidence: { step: "soft-delete" },
      ...(token
        ? {
            headers: {
              Authorization: token.toLowerCase().startsWith("bearer ")
                ? token
                : `Bearer ${token}`
            }
          }
        : {})
    })
  );
  return attachStatus(
    result,
    (body) =>
      body &&
      ["scenarioGroupDeleted", "scenarioDeleted", "signpostDeleted"].every(
        (key) => typeof body[key as keyof SoftDeleteResponse] === "number"
      )
        ? "success"
        : "error"
  );
}

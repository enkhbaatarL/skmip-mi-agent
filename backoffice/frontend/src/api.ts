import type { ApiRunResponse, EventListResponse, ScenarioDesignModel, ScenarioGroupListResponse, ScenarioRow, Signpost, TableHeader } from "./types";

const API_ROOT = "/backoffice/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw Object.assign(new Error(`HTTP ${response.status}`), {
      status: response.status,
      body: data
    });
  }
  return data as T;
}

export function createScenarioGroup(body: CreateScenarioGroupBody) {
  return requestJson<ApiRunResponse>("/runs/scenario-groups", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function refreshScenarioGroup(scenarioGroupId: string) {
  return requestJson<unknown>(`/scenario-groups/${encodeURIComponent(scenarioGroupId)}`);
}

export function listEvents(params: EventListParams) {
  const query = new URLSearchParams();
  if (params.agentBaseUrl) query.set("agentBaseUrl", params.agentBaseUrl);
  if (params.keyword) query.set("keyword", params.keyword);
  if (params.status) query.set("status", params.status);
  if (params.recommendedOnly) query.set("recommendedOnly", "true");
  if (params.sort) query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("pageSize", String(params.pageSize));
  return requestJson<EventListResponse>(`/events?${query.toString()}`);
}

export function fetchEventDetail(miEventId: number, agentBaseUrl: string) {
  const query = new URLSearchParams();
  if (agentBaseUrl) query.set("agentBaseUrl", agentBaseUrl);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<unknown>(`/events/${encodeURIComponent(miEventId)}${suffix}`);
}

export function listScenarioGroups(params: ScenarioGroupListParams) {
  const query = new URLSearchParams();
  if (params.agentBaseUrl) query.set("agentBaseUrl", params.agentBaseUrl);
  if (params.includeDeleted) query.set("includeDeleted", "true");
  if (params.keyword) query.set("keyword", params.keyword);
  if (params.status) query.set("status", params.status);
  if (params.stage) query.set("stage", params.stage);
  if (params.miEventId) query.set("miEventId", params.miEventId);
  if (params.sort) query.set("sort", params.sort);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<ScenarioGroupListResponse>(`/scenario-groups${suffix}`);
}

export function fetchScenarioGroupDetail(scenarioGroupId: string, agentBaseUrl: string, includeDeleted = false) {
  const query = new URLSearchParams();
  if (agentBaseUrl) query.set("agentBaseUrl", agentBaseUrl);
  if (includeDeleted) query.set("includeDeleted", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<ApiRunResponse>(`/scenario-groups/${encodeURIComponent(scenarioGroupId)}${suffix}`);
}

export function deleteScenarioGroup(scenarioGroupId: string, body: DeleteScenarioGroupBody) {
  return requestJson<unknown>(`/scenario-groups/${encodeURIComponent(scenarioGroupId)}`, {
    method: "DELETE",
    body: JSON.stringify(body)
  });
}

export function requestValidation(runId: string, body: ValidationRequestBody) {
  return requestJson<ApiRunResponse>(`/runs/${encodeURIComponent(runId)}/validation`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function requestSignposts(runId: string, body: SignpostRequestBody) {
  return requestJson<ApiRunResponse>(`/runs/${encodeURIComponent(runId)}/signposts`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function requestConfirmation(runId: string, body: ConfirmationRequestBody) {
  return requestJson<ApiRunResponse>(`/runs/${encodeURIComponent(runId)}/confirmation`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export type CreateScenarioGroupBody = {
  agentBaseUrl: string;
  miEventId: number;
  userId: number;
};

export type ScenarioGroupListParams = {
  agentBaseUrl: string;
  includeDeleted: boolean;
  keyword: string;
  status: string;
  stage: string;
  miEventId: string;
  sort: string;
};

export type EventListParams = {
  agentBaseUrl: string;
  keyword: string;
  status: string;
  recommendedOnly: boolean;
  sort: string;
  page: number;
  pageSize: number;
};

export type DeleteScenarioGroupBody = {
  agentBaseUrl: string;
  userId: number;
  deleteAuthorization: string;
};

export type ValidationRequestBody = {
  userId: number;
  table: {
    headers: TableHeader[];
      rows: Array<{
      scenarioId?: number;
      displayOrder: number;
      title: string;
      cells: Record<string, string>;
    }>;
  };
};

export type SignpostRequestBody = ValidationRequestBody & {
  scenarioGroup: {
    title: string;
    description: string;
  };
  scenarios: Array<{
    scenarioId?: number;
    displayOrder: number;
    title: string;
    narrative: string;
    probabilityScore: string;
    cells: Record<string, string>;
  }>;
};

export type ConfirmationRequestBody = {
  userId: number;
  scenarioGroup: {
    title: string;
    description: string;
  };
  table: {
    headers: TableHeader[];
    rows: Array<{
      scenarioId?: number;
      displayOrder: number;
      title: string;
      narrative: string;
      metrics: {
        probabilityScore: number;
      };
      baselineYn: "Y" | "N";
      cells: Record<string, string>;
      signposts: Array<Signpost & { signpostId?: number }>;
    }>;
  };
};

export function buildCreateBody(agentBaseUrl: string, miEventId: string, userId: string): CreateScenarioGroupBody {
  return {
    agentBaseUrl,
    miEventId: Number(miEventId),
    userId: Number(userId)
  };
}

export function buildValidationBody(userId: string, model: ScenarioDesignModel): ValidationRequestBody {
  return {
    userId: Number(userId),
    table: {
      headers: model.headers,
      rows: model.rows.map((row) => ({
        scenarioId: row.scenarioId,
        displayOrder: row.displayOrder,
        title: row.title,
        cells: row.cells
      }))
    }
  };
}

export function buildSignpostBody(userId: string, model: ScenarioDesignModel): SignpostRequestBody {
  return {
    ...buildValidationBody(userId, model),
    scenarioGroup: {
      title: model.groupName,
      description: model.description
    },
    scenarios: model.rows.map((row) => ({
      scenarioId: row.scenarioId,
      displayOrder: row.displayOrder,
      title: row.title,
      narrative: row.narrative,
      probabilityScore: row.probability,
      cells: row.cells
    }))
  };
}

export function buildConfirmationBody(userId: string, model: ScenarioDesignModel): ConfirmationRequestBody {
  return {
    userId: Number(userId),
    scenarioGroup: {
      title: model.groupName,
      description: model.description
    },
    table: {
      headers: model.headers,
      rows: model.rows.map((row) => ({
        scenarioId: row.scenarioId,
        displayOrder: row.displayOrder,
        title: row.title,
        narrative: row.narrative,
        metrics: {
          probabilityScore: Number(row.probability) || 0
        },
        baselineYn: row.baselineYn,
        cells: row.cells,
        signposts: row.signposts
          .map((signpost) => {
            const signpostId = Number(signpost.id);
            return Number.isFinite(signpostId) && signpostId > 0 ? { ...signpost, signpostId } : null;
          })
          .filter((signpost): signpost is Signpost & { signpostId: number } => signpost !== null)
      }))
    }
  };
}

export function openRunEvents(runId: string): EventSource {
  return new EventSource(`${API_ROOT}/runs/${encodeURIComponent(runId)}/events`);
}

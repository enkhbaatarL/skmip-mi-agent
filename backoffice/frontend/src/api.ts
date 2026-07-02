import type { ApiRunResponse, ScenarioDesignModel, ScenarioRow, Signpost, TableHeader } from "./types";

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
      signposts: Signpost[];
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
      }))
    }
  };
}

export function openRunEvents(runId: string): EventSource {
  return new EventSource(`${API_ROOT}/runs/${encodeURIComponent(runId)}/events`);
}

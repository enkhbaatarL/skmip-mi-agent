import type { ApiRunResponse, ScenarioDesignModel, ScenarioRow, TableHeader } from "../types";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
}

export function pickRunId(payload: ApiRunResponse): string {
  const run = asRecord(payload.run);
  return asString(payload.runId ?? payload.run_id ?? run.runId ?? run.run_id ?? asRecord(payload.data).runId ?? asRecord(payload.data).run_id);
}

export function pickScenarioGroupId(payload: ApiRunResponse): string {
  const run = asRecord(payload.run);
  return asString(
    payload.scenarioGroupId ??
      payload.scenario_group_id ??
      run.scenarioGroupId ??
      run.scenario_group_id ??
      asRecord(payload.data).scenarioGroupId ??
      asRecord(payload.data).scenario_group_id
  );
}

export function pickAgentStatus(payload: ApiRunResponse): string {
  const run = asRecord(payload.run);
  return asString(payload.status ?? run.agentStatus ?? run.agent_status ?? asRecord(payload.data).status);
}

export function pickAgentStage(payload: ApiRunResponse): string {
  const run = asRecord(payload.run);
  return asString(payload.stage ?? run.agentStage ?? run.agent_stage ?? asRecord(payload.data).stage);
}

export function mergeDetailIntoModel(current: ScenarioDesignModel, detail: unknown): ScenarioDesignModel {
  const root = asRecord(detail);
  const run = asRecord(root.run);
  const normalized = asRecord(root.normalized ?? run.normalized);
  const detailPayload = asRecord(root.detail ?? run.detail);
  const scenarioGroup = asRecord(
    normalized.scenarioGroup ??
      normalized.scenario_group ??
      detailPayload.scenarioGroup ??
      detailPayload.scenario_group ??
      root.scenarioGroup ??
      root.scenario_group ??
      root.data
  );
  const table = asRecord(normalized.table ?? detailPayload.table ?? root.table ?? scenarioGroup.table);
  const headers = Array.isArray(table.headers) ? (table.headers as TableHeader[]) : current.headers;
  const rows = Array.isArray(table.rows) ? table.rows : [];

  if (!rows.length) {
    return current;
  }

  const normalizedRows: ScenarioRow[] = rows.map((raw, index) => {
    const row = asRecord(raw);
    const cells = asRecord(row.cells);
    const metrics = asRecord(row.metrics);
    const signposts = Array.isArray(row.signposts) ? row.signposts : [];
    const generatedRow: ScenarioRow = {
      localId: `scenario-${asString(row.scenarioId, String(index + 1))}`,
      scenarioId: typeof row.scenarioId === "number" ? row.scenarioId : undefined,
      displayOrder: Number(row.displayOrder ?? index + 1),
      title: asString(row.title, `Scenario ${index + 1}`),
      narrative: asString(row.narrative),
      cells: Object.fromEntries(Object.entries(cells).map(([key, value]) => [key, asString(value)])),
      probability: asString(metrics.probabilityScore ?? row.probabilityScore ?? row.probability, "0"),
      baselineYn: row.baselineYn === "Y" ? "Y" : "N",
      status: asString(row.status, "Draft"),
      signposts: signposts.map((item, signpostIndex) => {
        const signpost = asRecord(item);
        return {
          id: asString(signpost.id ?? signpost.signpostId, `${row.scenarioId ?? index}-${signpostIndex}`),
          label: asString(signpost.label ?? signpost.title ?? signpost.signpostLabel),
          direction: asString(signpost.direction),
          impact: asString(signpost.impact),
          evidence: asString(signpost.evidence ?? signpost.coreBasis ?? signpost.reason)
        };
      })
    };
    const existing = current.rows.find(
      (currentRow) =>
        (generatedRow.scenarioId !== undefined && currentRow.scenarioId === generatedRow.scenarioId) ||
        currentRow.localId === generatedRow.localId ||
        currentRow.displayOrder === generatedRow.displayOrder
    );
    if (!existing?.edited) {
      return generatedRow;
    }
    return {
      ...generatedRow,
      localId: existing.localId,
      title: existing.title,
      narrative: existing.narrative,
      cells: { ...generatedRow.cells, ...existing.cells },
      probability: existing.probability,
      status: existing.status,
      edited: true,
      signposts: generatedRow.signposts.length ? generatedRow.signposts : existing.signposts
    };
  });

  return {
    ...current,
    groupName: asString(scenarioGroup.title ?? scenarioGroup.name, current.groupName),
    description: asString(scenarioGroup.description ?? scenarioGroup.summary, current.description),
    headers,
    rows: normalizedRows
  };
}

import { expect, type APIRequestContext } from "@playwright/test";

type RecordValue = Record<string, unknown>;

const apiURL = process.env.E2E_API_URL
  ?? process.env.E2E_BASE_URL
  ?? "http://127.0.0.1:8000";

export const itemArray = (payload: unknown): RecordValue[] => {
  if (Array.isArray(payload)) return payload.filter((item): item is RecordValue => typeof item === "object" && item !== null);
  if (payload && typeof payload === "object") {
    const items = (payload as RecordValue).items;
    if (Array.isArray(items)) return items.filter((item): item is RecordValue => typeof item === "object" && item !== null);
  }
  return [];
};

export const field = (record: RecordValue, ...names: string[]): unknown => {
  for (const name of names) if (record[name] !== undefined && record[name] !== null) return record[name];
  return undefined;
};

export const idField = (record: RecordValue, ...names: string[]): string => String(field(record, ...names) ?? "");

export async function expectHealthy(request: APIRequestContext): Promise<void> {
  const response = await request.get(`${apiURL}/health`);
  expect(response.ok(), await response.text()).toBeTruthy();
  const body = await response.json() as RecordValue;
  expect(field(body, "status")).toBe("ok");
}

export async function listRuns(request: APIRequestContext): Promise<RecordValue[]> {
  const response = await request.get(`${apiURL}/api/runs?page=1&pageSize=100`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return itemArray(await response.json());
}

export async function listCandidates(request: APIRequestContext): Promise<RecordValue[]> {
  const response = await request.get(`${apiURL}/api/learning/candidates?page=1&pageSize=100`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return itemArray(await response.json());
}

export async function listFeedback(request: APIRequestContext): Promise<RecordValue[]> {
  const response = await request.get(`${apiURL}/api/feedback?page=1&pageSize=100`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return itemArray(await response.json());
}

export async function listAssets(request: APIRequestContext): Promise<RecordValue[]> {
  const response = await request.get(`${apiURL}/api/assets`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return itemArray(await response.json());
}

export async function processPending(request: APIRequestContext): Promise<RecordValue> {
  const response = await request.post(`${apiURL}/api/learning/process-pending`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return await response.json() as RecordValue;
}

export async function createExampleRun(request: APIRequestContext, exampleIndex = 0): Promise<RecordValue> {
  const examplesResponse = await request.get(`${apiURL}/api/examples`);
  expect(examplesResponse.ok(), await examplesResponse.text()).toBeTruthy();
  const examples = itemArray(await examplesResponse.json());
  const example = examples[exampleIndex];
  expect(example, `Example index ${exampleIndex} should exist`).toBeTruthy();

  const response = await request.post(`${apiURL}/api/runs`, {
    data: {
      metadata: field(example, "metadata", "meta"),
      scenarioJson: field(example, "scenarioJson", "scenario_json", "scenario"),
      clarificationAnswers: {},
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return await response.json() as RecordValue;
}

export async function submitRunFeedback(
  request: APIRequestContext,
  runId: string,
  text: string,
): Promise<RecordValue> {
  const response = await request.post(`${apiURL}/api/runs/${encodeURIComponent(runId)}/feedback`, {
    data: { scope: "run", text },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return await response.json() as RecordValue;
}

export function resultRunId(response: RecordValue): string {
  const result = field(response, "resultRun", "result_run");
  return result && typeof result === "object"
    ? idField(result as RecordValue, "runId", "run_id")
    : idField(response, "resultRunId", "result_run_id");
}

export function activeAssetVersion(assets: RecordValue[], assetType: string, assetKey: string): string {
  const asset = assets.find((item) =>
    String(field(item, "assetType", "asset_type")) === assetType
    && String(field(item, "assetKey", "asset_key")) === assetKey);
  return String(asset ? field(asset, "activeVersion", "active_version", "version") ?? "" : "");
}

export function assetState(assets: RecordValue[], assetType: string, assetKey: string): RecordValue {
  const asset = assets.find((item) =>
    String(field(item, "assetType", "asset_type")) === assetType
    && String(field(item, "assetKey", "asset_key")) === assetKey);
  return {
    activeVersion: String(asset ? field(asset, "activeVersion", "active_version", "version") ?? "" : ""),
    versionCount: Number(asset ? field(asset, "versionCount", "version_count") ?? 0 : 0),
  };
}

export function assetRegistryState(assets: RecordValue[]): RecordValue[] {
  return assets
    .map((asset) => ({
      assetType: String(field(asset, "assetType", "asset_type") ?? ""),
      assetKey: String(field(asset, "assetKey", "asset_key") ?? ""),
      activeVersion: String(field(asset, "activeVersion", "active_version", "version") ?? ""),
      versionCount: Number(field(asset, "versionCount", "version_count") ?? 0),
    }))
    .sort((left, right) => `${left.assetType}:${left.assetKey}`.localeCompare(`${right.assetType}:${right.assetKey}`));
}

export function runAssetSnapshotVersion(run: RecordValue, assetType: string, assetKey: string): string {
  const snapshot = field(run, "assetSnapshot", "asset_snapshot", "assetVersions", "asset_versions");
  if (Array.isArray(snapshot)) {
    const item = snapshot.find((entry) => {
      if (!entry || typeof entry !== "object") return false;
      const record = entry as RecordValue;
      return String(field(record, "assetType", "asset_type")) === assetType
        && String(field(record, "assetKey", "asset_key")) === assetKey;
    });
    return item && typeof item === "object" ? String(field(item as RecordValue, "version") ?? "") : "";
  }
  if (snapshot && typeof snapshot === "object") {
    const entry = (snapshot as RecordValue)[`${assetType}:${assetKey}`];
    return entry && typeof entry === "object"
      ? String(field(entry as RecordValue, "version") ?? "")
      : String(entry ?? "");
  }
  return "";
}

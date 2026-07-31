import type { AgentClient } from "./agentClient";
import type { ApiCallResult } from "../domain/apiCall";
import type {
  ApiVersion,
  MultiEventCreateScenariosRequest,
  VersionedCreateScenariosOut
} from "../domain/apiTypes";
import {
  judgeComparisonVersion,
  type RunStatus
} from "../domain/judgments";
import type {
  ComparisonManifest,
  VersionRequest
} from "../features/version-comparison/types";

type ComparisonClient = Pick<AgentClient, "request">;

export interface JudgedVersionResult
  extends ApiCallResult<VersionedCreateScenariosOut> {
  status: RunStatus;
  integrityIssues: string[];
  request: VersionRequest;
}

export interface ComparisonRunCallbacks {
  onVersionStart?: (
    version: ApiVersion,
    request: VersionRequest,
    startedAt: string
  ) => void;
  onVersionSettled?: (
    version: ApiVersion,
    result: JudgedVersionResult
  ) => void;
  onVersionRejected?: (version: ApiVersion, error: unknown) => void;
}

export interface ComparisonSignals {
  v2?: AbortSignal;
  v3?: AbortSignal;
  v4?: AbortSignal;
}

const firedRunVersions = new Set<string>();

function guardKey(runId: string, version: ApiVersion): string {
  return `${runId}\u0000${version}`;
}

export function hasVersionRun(
  runId: string,
  version: ApiVersion
): boolean {
  return firedRunVersions.has(guardKey(runId, version));
}

function validateManifest(manifest: ComparisonManifest): void {
  const ids = manifest.miEventIds;
  if (
    ids.length < 2 ||
    ids.length > 5 ||
    new Set(ids).size !== ids.length ||
    ids.some((id) => !Number.isSafeInteger(id) || id <= 0)
  ) {
    throw new Error("miEventIds는 중복 없는 양의 정수 2~5개여야 합니다.");
  }
  const comparisonRunId = manifest.comparisonRunId.trim();
  if (!comparisonRunId || comparisonRunId.length > 255) {
    throw new Error("comparisonRunId는 공백이 아닌 255자 이하여야 합니다.");
  }
}

export function buildVersionRequest(
  _version: ApiVersion,
  manifest: ComparisonManifest
): MultiEventCreateScenariosRequest {
  const common: MultiEventCreateScenariosRequest = {
    miEventIds: [...manifest.miEventIds],
    userId: manifest.userId,
    comparisonRunId: manifest.comparisonRunId
  };
  return common;
}

export async function runVersion(
  client: ComparisonClient,
  version: ApiVersion,
  manifest: ComparisonManifest,
  signal?: AbortSignal
): Promise<JudgedVersionResult> {
  validateManifest(manifest);
  const key = guardKey(manifest.runId, version);
  if (firedRunVersions.has(key)) {
    throw new Error(
      `${version} POST는 comparison run ${manifest.runId}에서 이미 실행되었습니다.`
    );
  }
  firedRunVersions.add(key);

  const request = buildVersionRequest(version, manifest);
  const result = await client.request<VersionedCreateScenariosOut>(
    `/${version}/scenario-groups/sync`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
      evidence: {
        workflow: "comparison",
        step: "version-create",
        version
      }
    }
  );
  const judged = judgeComparisonVersion(version, manifest, result);
  return {
    ...result,
    status: judged.judgment,
    integrityIssues: judged.integrityIssues,
    request
  };
}

export async function runComparison(
  client: ComparisonClient,
  manifest: ComparisonManifest,
  callbacks: ComparisonRunCallbacks = {},
  signals: ComparisonSignals = {}
): Promise<Record<ApiVersion, PromiseSettledResult<JudgedVersionResult>>> {
  validateManifest(manifest);
  for (const version of ["v2", "v3", "v4"] as const) {
    if (hasVersionRun(manifest.runId, version)) {
      throw new Error(
        `${version} POST는 comparison run ${manifest.runId}에서 이미 실행되었습니다.`
      );
    }
  }

  const execute = async (
    version: ApiVersion
  ): Promise<JudgedVersionResult> => {
    callbacks.onVersionStart?.(
      version,
      buildVersionRequest(version, manifest),
      new Date().toISOString()
    );
    try {
      const result = await runVersion(
        client,
        version,
        manifest,
        signals[version]
      );
      callbacks.onVersionSettled?.(version, result);
      return result;
    } catch (error) {
      callbacks.onVersionRejected?.(version, error);
      throw error;
    }
  };

  const [v2, v3] = await Promise.allSettled([
    execute("v2"),
    execute("v3")
  ]);
  const v4 = await Promise.allSettled([execute("v4")]);

  return { v2, v3, v4: v4[0] };
}

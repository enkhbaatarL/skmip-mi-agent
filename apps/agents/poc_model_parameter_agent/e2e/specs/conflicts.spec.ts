import { expect, test, type Page } from "@playwright/test";
import {
  activeAssetVersion,
  assetRegistryState,
  assetState,
  createExampleRun,
  field,
  idField,
  listAssets,
  listCandidates,
  listRuns,
  processPending,
  resultRunId,
  runAssetSnapshotVersion,
  submitRunFeedback,
} from "../support/api";
import { fillReviewerNote, goTo } from "../support/ui";

type CandidateIdentity = {
  id: string;
  targetType: string;
  targetKey: string;
  baseVersion: string;
};

const asCandidate = (record: Record<string, unknown>): CandidateIdentity => ({
  id: idField(record, "candidateId", "candidate_id", "id"),
  targetType: String(field(record, "targetType", "target_type") ?? ""),
  targetKey: String(field(record, "targetAssetKey", "target_asset_key") ?? ""),
  baseVersion: String(field(record, "baseVersion", "base_version") ?? ""),
});

async function openCandidate(page: Page, id: string): Promise<void> {
  await goTo(page, `/learning/candidates/${encodeURIComponent(id)}`);
  await expect(page.getByTestId("candidate-detail")).toBeVisible();
  await expect(page.getByRole("heading", { name: id })).toBeVisible();
}

test("Reject is non-mutating and stale Base Version approval returns 409 with rollback", async ({ page, request }) => {
  const runs = await listRuns(request);
  expect(runs.length).toBeGreaterThan(0);
  let currentRunId = idField(runs[0], "runId", "run_id", "id");

  const preferenceFeedback = [
    "수요 영향이 과도합니다. 반복해서 조금 완화해 주세요.",
    "공급 영향이 너무 큽니다. 이후 Run에서도 줄여 주세요.",
    "위험 프리미엄을 보수적으로 낮추는 기본값을 기억해 주세요.",
    "현물 Cargo 영향은 과도하므로 항상 완화해 주세요.",
  ];
  for (const text of preferenceFeedback) {
    const response = await submitRunFeedback(request, currentRunId, text);
    const childId = resultRunId(response);
    expect(childId).not.toBe("");
    currentRunId = childId;
  }
  await processPending(request);

  let group: CandidateIdentity[] = [];
  await expect.poll(async () => {
    const candidates = (await listCandidates(request))
      .filter((item) => String(field(item, "status")) === "pending")
      .map(asCandidate);
    const groups = new Map<string, CandidateIdentity[]>();
    for (const candidate of candidates) {
      const key = `${candidate.targetType}/${candidate.targetKey}/v${candidate.baseVersion}`;
      groups.set(key, [...(groups.get(key) ?? []), candidate]);
    }
    group = [...groups.values()].sort((a, b) => b.length - a.length)[0] ?? [];
    return group.length;
  }, { timeout: 30_000 }).toBeGreaterThanOrEqual(3);

  const [rejected, approved, stale] = group;
  const beforeRejectAssets = await listAssets(request);
  const beforeReject = activeAssetVersion(beforeRejectAssets, rejected.targetType, rejected.targetKey);
  const stateBeforeReject = assetState(beforeRejectAssets, rejected.targetType, rejected.targetKey);
  const registryBeforeReject = assetRegistryState(beforeRejectAssets);

  await test.step("Candidate rejection changes only Candidate status", async () => {
    await openCandidate(page, rejected.id);
    await fillReviewerNote(page, "E2E rejection must not mutate the Asset.");
    await page.getByRole("button", { name: "Candidate 거절" }).click();
    await expect(page.getByText(/Candidate를 거절했습니다/)).toBeVisible();
    await expect.poll(async () => {
      const candidates = await listCandidates(request);
      return String(field(candidates.find((item) => idField(item, "candidateId", "candidate_id") === rejected.id) ?? {}, "status"));
    }).toBe("rejected");
    const afterRejectAssets = await listAssets(request);
    expect(activeAssetVersion(afterRejectAssets, rejected.targetType, rejected.targetKey)).toBe(beforeReject);
    expect(assetState(afterRejectAssets, rejected.targetType, rejected.targetKey)).toEqual(stateBeforeReject);
    expect(assetRegistryState(afterRejectAssets)).toEqual(registryBeforeReject);
  });

  let activeAfterApproval = "";
  await test.step("Candidate approval activates exactly one new version", async () => {
    await openCandidate(page, approved.id);
    await fillReviewerNote(page, "E2E approved after evaluation review.");
    await page.getByRole("button", { name: "Candidate 승인" }).click();
    await expect(page.getByText(/새 Asset Version을 활성화/)).toBeVisible();
    await expect.poll(async () => activeAssetVersion(await listAssets(request), approved.targetType, approved.targetKey)).not.toBe(beforeReject);
    activeAfterApproval = activeAssetVersion(await listAssets(request), approved.targetType, approved.targetKey);
  });

  await test.step("The next new Run snapshots the approved Asset Version", async () => {
    const nextRun = await createExampleRun(request);
    expect(runAssetSnapshotVersion(nextRun, approved.targetType, approved.targetKey)).toBe(activeAfterApproval);
  });

  await test.step("Stale candidate returns visible HTTP 409 and leaves Asset unchanged", async () => {
    const beforeConflictAssets = await listAssets(request);
    const stateBeforeConflict = assetState(beforeConflictAssets, stale.targetType, stale.targetKey);
    const registryBeforeConflict = assetRegistryState(beforeConflictAssets);
    await openCandidate(page, stale.id);
    await fillReviewerNote(page, "This candidate intentionally has a stale base version.");
    await page.getByRole("button", { name: "Candidate 승인" }).click();
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("Version Conflict · HTTP 409");
    await expect(alert).toContainText("어떤 Asset도 변경되지 않았습니다");
    const afterConflictAssets = await listAssets(request);
    expect(activeAssetVersion(afterConflictAssets, stale.targetType, stale.targetKey)).toBe(activeAfterApproval);
    expect(assetState(afterConflictAssets, stale.targetType, stale.targetKey)).toEqual(stateBeforeConflict);
    expect(assetRegistryState(afterConflictAssets)).toEqual(registryBeforeConflict);
  });

  await test.step("process-pending is idempotent", async () => {
    await processPending(request);
    const countAfterFirst = (await listCandidates(request)).length;
    await processPending(request);
    expect((await listCandidates(request)).length).toBe(countAfterFirst);
  });
});

import { expect, test } from "@playwright/test";
import { expectHealthy, field, idField, listFeedback } from "../support/api";
import {
  answerAdditionalInstruction,
  answerRequiredClarifications,
  captureReviewScreenshot,
  createParameterButton,
  createRun,
  goTo,
  loadExample,
  openLearningTab,
  validateAndPlan,
} from "../support/ui";

test.describe.serial("LNG Scenario-to-Parameter browser journey", () => {
  test("Example, Plan, Result, Feedback Revision, Ledger and Learning flow", async ({ page, request }) => {
    const interimInstruction = "수요 영향이 과도합니다. 완화해 주세요.";
    await test.step("Dockerized API and MySQL health", async () => {
      await expectHealthy(request);
      await goTo(page, "/generate", /Parameter 생성/);
      await expect(page.getByText(/MySQL · (connected|healthy)/i)).toBeVisible();
      await expect(page.getByText(/AGENT_MODE · MOCK/i)).toBeVisible();
    });

    let parentRunId = "";
    let childRunId = "";
    await test.step("Example 1 → JSON validation → nine-step Plan", async () => {
      await loadExample(page, 1);
      await validateAndPlan(page);
      await answerAdditionalInstruction(page, interimInstruction);
      await expect(createParameterButton(page)).toBeEnabled();
      await captureReviewScreenshot(page, "parameter-input-plan");
    });

    await test.step("Parameter generation, Scenario/Proposal selection, Plot/Trace/Formula", async () => {
      await createRun(page);
      const resultMeta = page.locator(".section-title-row__meta .mono").first();
      const resultText = await resultMeta.innerText();
      parentRunId = resultText.split(" · ")[0]?.trim() ?? "";
      expect(parentRunId).not.toBe("");

      const tabs = page.getByRole("tab", { name: /scenario-|강한|한파|공급/i });
      if (await tabs.count() > 1) {
        await tabs.nth(1).click();
        await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
      }

      const proposalButtons = page.getByRole("button", { name: /Parameter 선택$/ });
      expect(await proposalButtons.count()).toBeGreaterThan(0);
      const formulaBefore = await page.locator(".formula-block code").innerText();
      if (await proposalButtons.count() > 1) {
        await page.locator(".proposal-table tbody tr").nth(1).locator("td").nth(1).click();
        await expect(page.locator(".proposal-table tbody tr.is-selected")).toContainText(await proposalButtons.nth(1).innerText());
        await expect.poll(() => page.locator(".formula-block code").innerText()).not.toBe(formulaBefore);
      }
      await expect(page.getByRole("heading", { name: "Baseline vs Proposed" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Rationale Trace" })).toBeVisible();
      await expect(page.locator(".formula-block code")).not.toBeEmpty();
      await expect(page.getByText("Feedback Adjustment", { exact: true }).first()).toBeVisible();

      await expect.poll(async () => {
        const feedback = (await listFeedback(request)).find((item) =>
          idField(item, "runId", "run_id") === parentRunId
          && String(field(item, "tag")) === "interim"
          && String(field(item, "source")) === "clarification"
          && String(field(item, "rawText", "raw_text")) === interimInstruction);
        const adjustment = feedback ? field(feedback, "adjustment", "adjustment_json") : undefined;
        return Boolean(
          feedback
          && adjustment
          && typeof adjustment === "object"
          && field(adjustment as Record<string, unknown>, "interpreted") === true,
        );
      }).toBe(true);
      await captureReviewScreenshot(page, "parameter-result");
    });

    await test.step("Final Feedback immediately creates Child Revision", async () => {
      await page.getByLabel("Final Feedback").fill("현물 Cargo 가용성 영향이 너무 직접적입니다. 선택 Parameter를 완화해 주세요.");
      await page.getByRole("button", { name: /피드백 저장 \+ Parameter 재생성/ }).click();
      await expect(page.getByText(/Child Revision을 생성/)).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("run-results")).toContainText("r2");
      const childMeta = await page.locator(".section-title-row__meta .mono").first().innerText();
      childRunId = childMeta.split(" · ")[0]?.trim() ?? "";
      expect(childRunId).not.toBe("");

      const duplicate = await request.post(`/api/runs/${encodeURIComponent(parentRunId)}/feedback`, {
        data: { scope: "run", text: "동일 Revision 중복 제출 검증" },
      });
      expect(duplicate.status()).toBe(409);

      const stalePage = await page.context().newPage();
      await goTo(stalePage, `/runs/${encodeURIComponent(childRunId)}`, new RegExp(childRunId));
      const committed = await request.post(`/api/runs/${encodeURIComponent(childRunId)}/feedback`, {
        data: { scope: "run", text: "다른 검토자가 먼저 제출한 Final Feedback" },
      });
      expect(committed.status()).toBe(201);
      await stalePage.getByLabel("Final Feedback").fill("stale 화면에서 중복 제출");
      await stalePage.getByRole("button", { name: /피드백 저장 \+ Parameter 재생성/ }).click();
      await expect(stalePage.getByText(/이미 Final Feedback|이미 저장되었습니다/).first()).toBeVisible();
      await expect(stalePage.getByRole("button", { name: /피드백 저장 \+ Parameter 재생성/ })).toBeDisabled();
      await stalePage.close();
    });

    await test.step("Example 3 locks execution until Required Clarification", async () => {
      await loadExample(page, 3);
      await expect(page.getByTestId("run-results")).toHaveCount(0);
      await validateAndPlan(page);
      await expect(createParameterButton(page)).toBeDisabled();
      await expect(page.getByText(/Required Clarification 응답 후/)).toBeVisible();
      await answerRequiredClarifications(page);
      await expect(createParameterButton(page)).toBeEnabled();
      await createRun(page);
    });

    await test.step("Refresh persistence and Run History detail", async () => {
      await page.reload();
      await page.getByRole("link", { name: "Run History" }).click();
      await expect(page.getByRole("heading", { name: "Run History" })).toBeVisible();
      await expect(page.locator("tbody tr").first()).toBeVisible();
      await captureReviewScreenshot(page, "run-history");
      await page.locator("tbody tr").first().getByRole("link").first().click();
      await expect(page.locator(".run-detail-page")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Snapshot" })).toBeVisible();
      await expect(page.getByText(/Artifact/).first()).toBeVisible();
    });

    await test.step("Unified Feedback ledger keeps Interim/Final raw records", async () => {
      await page.getByRole("link", { name: "피드백 원장" }).click();
      await expect(page.getByRole("heading", { name: "피드백 원장" })).toBeVisible();
      const ledgerBody = page.locator(".feedback-table tbody");
      await expect(ledgerBody.getByText("interim", { exact: true }).first()).toBeVisible();
      await expect(ledgerBody.getByText("final", { exact: true }).first()).toBeVisible();
      await captureReviewScreenshot(page, "feedback-ledger");
      const rawToggle = page.locator(".feedback-records details").first().locator("summary");
      await rawToggle.click();
      await expect(page.locator("pre").last()).toContainText(/feedback/i);
    });

    await test.step("Learning batch and Candidate diff/evaluation", async () => {
      await page.getByRole("link", { name: "Learning Pipeline" }).click();
      await expect(page.getByRole("heading", { name: "Learning Pipeline" })).toBeVisible();
      const process = page.getByRole("button", { name: /Learning Worker 실행|미처리 Feedback 처리/ });
      await process.click();
      await expect(page.getByText(/Cycle|처리|Batch/).first()).toBeVisible();
      await openLearningTab(page, /Learning Batches|Batches/);
      await expect(page.locator("tbody tr").first()).toBeVisible();
      await captureReviewScreenshot(page, "learning-batches");
      await openLearningTab(page, /Candidates/);
      await expect(page.locator("tbody tr").first()).toBeVisible();
      await captureReviewScreenshot(page, "learning-candidates");
      await page.locator("tbody tr").first().getByRole("link").first().click();
      await expect(page.getByTestId("candidate-detail")).toBeVisible();
      await expect(page.locator(".candidate-detail .page-header h1")).not.toBeEmpty();
      await expect(page.getByText(/Line Diff|Diff/).first()).toBeVisible();
      await expect(page.getByText(/Evaluation/).first()).toBeVisible();
      await captureReviewScreenshot(page, "candidate-detail");
    });
  });
});

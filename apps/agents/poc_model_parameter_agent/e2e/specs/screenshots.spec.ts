import { existsSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { captureReviewScreenshot, goTo, openLearningTab, screenshotPath } from "../support/ui";

const requiredScreenshots = [
  "parameter-input-plan",
  "parameter-result",
  "run-history",
  "feedback-ledger",
  "learning-batches",
  "learning-candidates",
  "candidate-detail",
  "asset-versions",
] as const;

test("Capture Asset Versions and verify the complete 1440px review set", async ({ page }) => {
  await goTo(page, "/learning?tab=assets", /Learning Pipeline/);
  await openLearningTab(page, /Asset Versions/);
  await expect(page.getByTestId("learning-assets")).toBeVisible();
  await expect(page.locator(".asset-card").first()).toBeVisible();
  await expect(page.getByText(/Learnable/).first()).toBeVisible();
  await expect(page.getByText(/Locked/).first()).toBeVisible();
  await captureReviewScreenshot(page, "asset-versions");

  for (const name of requiredScreenshots) {
    expect(existsSync(screenshotPath(name)), `${name}.png was not generated`).toBeTruthy();
  }
});

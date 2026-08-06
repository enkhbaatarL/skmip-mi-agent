import { expect, type Locator, type Page } from "@playwright/test";

export const screenshotPath = (name: string): string => `artifacts/screenshots/${name}.png`;

export async function captureReviewScreenshot(page: Page, name: string): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(100);
  await page.screenshot({ path: screenshotPath(name), fullPage: true });
}

export async function goTo(page: Page, path: string, heading?: RegExp): Promise<void> {
  await page.goto(path);
  if (heading) await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
}

export async function loadExample(page: Page, example: 1 | 2 | 3): Promise<void> {
  await goTo(page, "/generate", /Parameter 생성/);
  const button = page.getByRole("button", { name: new RegExp(`예시 ${example}.*불러오기`) });
  await expect(button).toBeEnabled();
  await button.click();
  await expect(page.getByLabel("Scenario JSON")).not.toHaveValue("");
}

export async function validateAndPlan(page: Page): Promise<void> {
  await page.getByRole("button", { name: "JSON 검증" }).click();
  await expect(page.getByText(/JSON Syntax가 유효/)).toBeVisible();
  await page.getByRole("button", { name: /^계획 생성$/ }).click();
  await expect(page.getByTestId("plan-preview")).toBeVisible();
  await expect(page.getByTestId("plan-preview").locator(".plan-steps > li")).toHaveCount(9);
}

export function createParameterButton(page: Page): Locator {
  return page.getByRole("button", { name: /^Parameter 생성$/ });
}

export async function answerRequiredClarifications(page: Page): Promise<void> {
  const required = page.locator("fieldset.clarification-question").filter({ hasText: "Required" });
  const count = await required.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index += 1) {
    const question = required.nth(index);
    const choices = question.getByRole("radio");
    await expect(choices.first()).toBeVisible();
    await choices.first().check();
  }
}

export async function answerAdditionalInstruction(page: Page, text: string): Promise<void> {
  const question = page.locator("fieldset.clarification-question").filter({
    hasText: "Optional Additional Instruction",
  });
  await expect(question).toHaveCount(1);
  await question.getByRole("radio", { name: "직접 입력" }).check();
  await question.getByLabel(/Optional Additional Instruction 수기 응답/).fill(text);
}

export async function createRun(page: Page): Promise<void> {
  const button = createParameterButton(page);
  await expect(button).toBeEnabled();
  await button.click();
  await expect(page.getByTestId("run-results")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("scenario-results")).toBeVisible();
  await expect(page.getByText("Prototype synthetic baseline", { exact: false }).first()).toBeVisible();
}

export async function openLearningTab(page: Page, name: RegExp): Promise<void> {
  const tab = page.getByRole("tab", { name });
  await expect(tab).toBeVisible();
  await tab.click();
}

export async function fillReviewerNote(page: Page, text: string): Promise<void> {
  const input = page.getByLabel(/Reviewer Note|검토 의견|Review Note/i);
  if (await input.count()) await input.fill(text);
}

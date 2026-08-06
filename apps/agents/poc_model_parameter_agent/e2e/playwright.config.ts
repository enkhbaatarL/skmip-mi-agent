import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173";
const browserChannel = process.env.PLAYWRIGHT_CHANNEL;

export default defineConfig({
  testDir: "./specs",
  outputDir: "./artifacts/test-results",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [
    ["list"],
    ["html", { outputFolder: "./artifacts/report", open: "never" }],
  ],
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    locale: "ko-KR",
    timezoneId: "Asia/Seoul",
    ...(browserChannel ? { channel: browserChannel } : {}),
  },
  projects: [
    { name: "journey", testMatch: /full-flow\.spec\.ts/ },
    { name: "conflicts", testMatch: /conflicts\.spec\.ts/, dependencies: ["journey"] },
    { name: "screenshots", testMatch: /screenshots\.spec\.ts/, dependencies: ["conflicts"] },
  ],
});

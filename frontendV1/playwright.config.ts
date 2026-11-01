import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/stages",
  testMatch:
    process.env.E2E_STAGE === "provider-setup"
      ? "**/providers.spec.ts"
      : process.env.E2E_STAGE?.startsWith("model-")
        ? "**/models.spec.ts"
        : process.env.E2E_STAGE === "admissions-scan-ocr"
          ? "**/scan-ocr.spec.ts"
          : process.env.E2E_STAGE?.startsWith("admissions-")
            ? "**/admissions.spec.ts"
            : "**/workflow.spec.ts",
  timeout: 300 * 1000,
  expect: {
    timeout: 15 * 1000,
  },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    [
      "html",
      {
        outputFolder: `${process.env.E2E_OUTPUT || "test-results/v1-e2e"}/html`,
        open: "never",
      },
    ],
    [
      "json",
      {
        outputFile: `${process.env.E2E_OUTPUT || "test-results/v1-e2e"}/results.json`,
      },
    ],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:3091",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  outputDir: `${process.env.E2E_OUTPUT || "test-results/v1-e2e"}/artifacts`,
  projects: [
    {
      name: "desktop-chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: "mobile-chromium",
      use: {
        ...devices["Pixel 5"],
        viewport: { width: 375, height: 667 },
      },
      testMatch: /.*responsive\.spec\.ts/,
    },
  ],
});

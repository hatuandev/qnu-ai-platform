import { test } from "@playwright/test";

// Legacy scaffolding is excluded by playwright.config.ts. Never treat key presence as inference.
test("Legacy live placeholder must not report success", () => {
  throw new Error(
    "Dùng test-v1-e2e.ps1 init --mode live và các chặng thật trong e2e/stages.",
  );
});

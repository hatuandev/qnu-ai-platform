import { test } from "@playwright/test";
import { runRetest9 } from "./retest9-runner";

test.skip(
  process.env.E2E_RETEST9 !== "true",
  "Retest cần runner/cohort riêng.",
);

test("Retest chín câu lỗi: một cohort, một lượt mỗi câu", async ({ page }) => {
  await runRetest9(page, (ms) => test.setTimeout(ms));
});

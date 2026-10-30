import { expect, test } from "@playwright/test";
import { questionAdmissionDraft } from "./admissions-chat";
import { benchmark, checkSource, modelTimeout } from "./admissions-context";
import { compileAdmissionSource, publishAdmissionDraft } from "./admissions-publication";
import { extractAdmissionSource, uploadAdmissionSource } from "./admissions-source";
import { authenticate, checkpoint } from "./session";

const stage = process.env.E2E_STAGE;
const steps = {
  "admissions-upload": uploadAdmissionSource,
  "admissions-extraction": extractAdmissionSource,
  "admissions-compilation": compileAdmissionSource,
  "admissions-publication": publishAdmissionDraft,
  "admissions-chat": questionAdmissionDraft,
};
if (!stage || !(stage in steps)) throw new Error("Chặng điểm sàn không hợp lệ.");
test.use({ trace: "off", video: "off", screenshot: "only-on-failure" });

test(`PDF thật điểm sàn 2026: ${stage}`, async ({ page }) => {
  const api = await authenticate(page);
  const state = checkpoint();
  if (state.mode !== "live" || !state.runtimeDefaults || !state.workspace)
    throw new Error("BLOCKED: cần phiên live, đủ kiểm tra model và navigation.");
  checkSource();
  const timeout = await modelTimeout(api, state);
  const perPart = stage === "admissions-chat" ? benchmark.cases.length + 2 : benchmark.source.pages * 6 + 6;
  test.setTimeout(Math.max(900_000, timeout * perPart));
  await steps[stage as keyof typeof steps](api, state);
  if (stage === "admissions-upload") {
    await page.goto(`/workspaces/${state.workspace}/knowledge/${state.admissions?.collection}`);
    await expect(page.getByText("TB điểm sàn 26.pdf", { exact: true }).first()).toBeVisible();
  }
});

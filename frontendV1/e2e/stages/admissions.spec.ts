import path from "node:path";
import { expect, test } from "@playwright/test";
import { questionAdmissionDraft } from "./admissions-chat";
import {
  benchmark,
  checkAllSources,
  docPaths,
  modelTimeout,
} from "./admissions-context";
import {
  compileAdmissionSource,
  publishAdmissionDraft,
} from "./admissions-publication";
import {
  extractAdmissionSource,
  uploadAdmissionSource,
} from "./admissions-source";
import { authenticate, checkpoint } from "./session";

const stage = process.env.E2E_STAGE;
const steps = {
  "admissions-upload": uploadAdmissionSource,
  "admissions-extraction": extractAdmissionSource,
  "admissions-compilation": compileAdmissionSource,
  "admissions-publication": publishAdmissionDraft,
  "admissions-chat": questionAdmissionDraft,
};
if (!stage || !(stage in steps))
  throw new Error("Chặng tuyển sinh không hợp lệ.");
test.use({ trace: "off", video: "off", screenshot: "only-on-failure" });

test(`Tuyển sinh QNU (3 tài liệu, 53 cases): ${stage}`, async ({ page }) => {
  const api = await authenticate(page);
  const state = checkpoint();
  if (state.mode !== "live" || !state.runtimeDefaults || !state.workspace)
    throw new Error(
      "BLOCKED: cần phiên live, đủ kiểm tra model và navigation.",
    );
  checkAllSources();
  const timeout = await modelTimeout(api, state);
  const totalPages = Object.values(benchmark.documents).reduce(
    (sum, d) => sum + d.pages,
    0,
  );
  const perPart =
    stage === "admissions-chat"
      ? benchmark.cases.length + 2
      : totalPages * 8 + 10;
  test.setTimeout(Math.max(1_200_000, timeout * perPart));
  await steps[stage as keyof typeof steps](api, state);

  if (stage === "admissions-upload") {
    await page.goto(
      `/workspaces/${state.workspace}/knowledge/${state.admissions?.collection}`,
    );
    for (const key of Object.keys(benchmark.documents)) {
      const fileName = path.basename(docPaths[key]);
      await expect(
        page.getByText(fileName, { exact: false }).first(),
      ).toBeVisible();
    }
  }
});

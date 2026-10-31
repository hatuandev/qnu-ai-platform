import { expect, it } from "vitest";
import { progressWaitMs } from "../e2e/stages/progress-budget";

it("grants a full request budget even when parts are fewer than slots", () => {
  expect(progressWaitMs(1, 4, 330_000)).toBe(390_000);
});

it("rounds up scheduling waves and accounts for shared-provider queuing", () => {
  expect(progressWaitMs(3, 2, 330_000)).toBe(720_000);
  expect(progressWaitMs(3, 2, 330_000, 300_000)).toBe(1_320_000);
  expect(progressWaitMs(0, 0, 10)).toBe(240_000);
});

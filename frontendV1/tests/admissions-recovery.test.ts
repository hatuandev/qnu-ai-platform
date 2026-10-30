import { describe, expect, it } from "vitest";
import { canRecoverAdmissionCompilation } from "../e2e/stages/admissions-recovery";

const failed = {
  status: "failed", error_code: "chat_output_truncated", provider_id: "provider",
};

describe("admissions compilation recovery", () => {
  it("allows a known truncation once using configured output capacity", () => {
    expect(canRecoverAdmissionCompilation(failed, {}, "provider", 16384)).toBe(true);
  });
  it("keeps uncertain, other failures and other providers untouched", () => {
    expect(canRecoverAdmissionCompilation({ ...failed, status: "uncertain" }, {}, "provider", 16384)).toBe(false);
    expect(canRecoverAdmissionCompilation({ ...failed, error_code: "quota_exceeded" }, {}, "provider", 16384)).toBe(false);
    expect(canRecoverAdmissionCompilation(failed, {}, "another", 16384)).toBe(false);
  });
  it("does not loop a recovery or replace reviewed/published work", () => {
    for (const publication of [{ compilationRecoveryOf: "old" }, { review: "review" }, { version: "version" }]) {
      expect(canRecoverAdmissionCompilation(failed, publication, "provider", 16384)).toBe(false);
    }
  });
  it("requires a usable, explicit provider budget", () => {
    for (const limit of [undefined, null, 4096, 8192.5, Number.NaN, Infinity]) {
      expect(canRecoverAdmissionCompilation(failed, {}, "provider", limit)).toBe(false);
    }
  });
});

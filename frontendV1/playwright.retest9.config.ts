import base from "./playwright.config";

export default {
  ...base,
  testDir: "./e2e/stages",
  testMatch: "retest9.spec.ts",
  retries: 0,
  workers: 1,
  use: { ...base.use, trace: "off", video: "off" },
};

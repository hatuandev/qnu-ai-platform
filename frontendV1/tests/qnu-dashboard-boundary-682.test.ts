import { expect, test } from "vitest";
import { isV1Route } from "@/app/api/v1/endpoints";

test("QNU dashboard must use the backendV1 session gate", () => {
  expect(isV1Route("/dashboard")).toBe(true);
});
test.each([
  "/reference-dashboard",
  "/dashboard-other",
  "/student",
  "/applications",
])("template route %s must stay outside the v1 boundary", (path) => {
  expect(isV1Route(path)).toBe(false);
});

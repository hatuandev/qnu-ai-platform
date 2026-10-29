import { expect, test } from "vitest";
import { isV1Route } from "@/app/api/v1/endpoints";
import { getBreadcrumbs, isItemActive } from "@/navigation/utils";
import {
  isFeatureActive,
  workspaceFeatureKeys,
} from "@/navigation/workspace-features";
import {
  internalWorkspacePath,
  parseWorkspaceLink,
  publicWorkspacePath,
} from "@/navigation/workspace-links";

test.each([
  "knowledge",
  "assistants",
  "conversations",
  "members",
  "models",
  "quota",
  "operations",
  "resources",
  "audit",
])("%s links round trip without a workspace prefix", (feature) => {
  const internal = `/workspaces/ws/${feature}`;
  const path = publicWorkspacePath(internal, "ctsv");
  expect(path).toBe(`/ctsv/${feature}`);
  expect(isV1Route(path ?? "")).toBe(true);
  expect(
    internalWorkspacePath(requireLink(path ?? ""), {
      workspace_id: "ws",
      collection_id: null,
    }),
  ).toBe(internal);
});

test("document link resolves its collection and preserves dedicated OCR route", () => {
  for (const suffix of ["", "/ocr"]) {
    const path = `/workspaces/ws/collections/col/sources/src${suffix}`;
    const short = publicWorkspacePath(path, "ctsv") ?? "";
    expect(short).toBe(`/ctsv/files/src${suffix}`);
    expect(
      internalWorkspacePath(requireLink(short), {
        workspace_id: "ws",
        collection_id: "col",
      }),
    ).toBe(path);
  }
});

test("source details belong only to knowledge and breadcrumbs agree", () => {
  const path = "/workspaces/ws/collections/col/sources/src";
  expect(
    workspaceFeatureKeys.filter((key) =>
      isFeatureActive(key, path, { runId: "run" }),
    ),
  ).toEqual(["collections"]);
  expect(
    isItemActive(
      { id: "workspaces", title: "Workspaces", to: "/workspaces" },
      path,
    ),
  ).toBe(false);
  expect(getBreadcrumbs(path).at(-1)?.label).toBe("Kho tri thức");
});

test("system routes and malformed document paths are not workspace links", () => {
  for (const path of [
    "/settings/security",
    "/workspaces/knowledge",
    "/providers/files/s",
    "/ctsv/files",
    "/ctsv/files/s/unknown",
  ])
    expect(parseWorkspaceLink(path)).toBeUndefined();
  expect(
    publicWorkspacePath("/workspaces/choose/compiler", "ctsv"),
  ).toBeUndefined();
  expect(
    publicWorkspacePath("/workspaces/ws/knowledge", "providers"),
  ).toBeUndefined();
});

function requireLink(path: string) {
  const link = parseWorkspaceLink(path);
  if (!link) throw new Error("Invalid workspace link");
  return link;
}

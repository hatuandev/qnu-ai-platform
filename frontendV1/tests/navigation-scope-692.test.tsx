// @vitest-environment jsdom
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, test, vi } from "vitest";
import {
  FeatureScopeProvider,
  useFeatureScope,
} from "@/navigation/use-feature-scope";
import { getBreadcrumbs } from "@/navigation/utils";
import {
  featureTarget,
  isFeatureActive,
  routeFeatureScope,
  workspaceFeatureKeys,
  workspaceFeatures,
} from "@/navigation/workspace-features";

const auth = vi.hoisted(() => ({ isAuthenticated: true, sessionId: 1 }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => auth }));
window.scrollTo = vi.fn();
afterEach(() => {
  cleanup();
  auth.sessionId = 1;
  auth.isAuthenticated = true;
});

test.each(workspaceFeatureKeys)(
  "%s has a selection destination and a scoped destination",
  (key) => {
    expect(featureTarget(key, {})).toMatchObject({
      to: "/workspaces/choose/$feature",
      params: { feature: key },
    });
    const target = featureTarget(key, {
      workspaceId: "ws",
      collectionId: "col",
    });
    expect(target.params).toMatchObject({ workspaceId: "ws" });
    if (workspaceFeatures[key].kind === "collection")
      expect(target.params).toMatchObject({ collectionId: "col" });
    expect(target.to).not.toBe("/workspaces/choose/$feature");
  },
);

test("each collection tab and operation view selects exactly one feature", () => {
  for (const [path, search, expected] of [
    ["/workspaces/ws/collections/col", { tab: "sources" }, "ocr"],
    ["/workspaces/ws/collections/col", { tab: "compilations" }, "compiler"],
    ["/workspaces/ws/collections/col", { tab: "documents" }, "documents"],
    ["/workspaces/ws/collections/col", { tab: "index" }, "search"],
    ["/workspaces/ws/operations", { view: "jobs" }, "jobs"],
    ["/workspaces/ws/operations", { view: "backups" }, "backups"],
    ["/workspaces/ws/operations", { view: "storage" }, "storage"],
  ] as const)
    expect(
      workspaceFeatureKeys.filter((key) => isFeatureActive(key, path, search)),
    ).toEqual([expected]);
});

test("selector scope and breadcrumbs come from selected workspace and feature", () => {
  expect(
    routeFeatureScope("/workspaces/choose/compiler", { workspaceId: "ws" }),
  ).toEqual({ workspaceId: "ws" });
  expect(routeFeatureScope("/workspaces/choose/compiler", {})).toEqual({
    workspaceId: undefined,
  });
  expect(
    getBreadcrumbs("/workspaces/choose/compiler").map((x) => x.label),
  ).toEqual(["QNU AI", "Tri thức", "Biên soạn"]);
  expect(
    getBreadcrumbs("/workspaces/ws/operations", { view: "backups" }).at(-1)
      ?.label,
  ).toBe("Sao lưu");
});

test("OCR destination keeps the OCR action while ordinary source links remain default", () => {
  expect(
    featureTarget("ocr", { workspaceId: "ws", collectionId: "col" }),
  ).toMatchObject({ search: { tab: "sources", sourceAction: "ocr" } });
  expect(
    featureTarget("compiler", { workspaceId: "ws", collectionId: "col" }),
  ).toMatchObject({ search: { tab: "compilations", sourceAction: undefined } });
});

function ScopeProbe() {
  return (
    <output data-testid="scope">{JSON.stringify(useFeatureScope())}</output>
  );
}
test("scope follows chooser URL, keeps collection within workspace, clears across sessions and workspace changes", async () => {
  const history = createMemoryHistory({
    initialEntries: ["/workspaces/choose/compiler?workspaceId=ws1"],
  });
  const root = createRootRoute({
    component: () => (
      <FeatureScopeProvider>
        <Outlet />
      </FeatureScopeProvider>
    ),
  });
  const page = createRoute({
    getParentRoute: () => root,
    path: "$",
    component: ScopeProbe,
  });
  const router = createRouter({ routeTree: root.addChildren([page]), history });
  const result = render(<RouterProvider router={router} />);
  const value = () =>
    JSON.parse(screen.getByTestId("scope").textContent ?? "{}");
  await waitFor(() => expect(value()).toEqual({ workspaceId: "ws1" }));
  async function go(url: string) {
    await act(async () => {
      history.push(url);
      await router.load();
    });
  }
  await go("/workspaces/ws1/collections/col1/answers");
  await waitFor(() =>
    expect(value()).toEqual({ workspaceId: "ws1", collectionId: "col1" }),
  );
  await go("/workspaces/ws1/members");
  expect(value()).toEqual({ workspaceId: "ws1", collectionId: "col1" });
  await go("/modelops/providers");
  expect(value()).toEqual({ workspaceId: "ws1", collectionId: "col1" });
  auth.sessionId = 2;
  result.rerender(<RouterProvider router={router} />);
  await go("/modelops/defaults");
  expect(value()).toEqual({});
  await go("/workspaces/ws2/assistants");
  expect(value()).toEqual({ workspaceId: "ws2" });
  await go("/workspaces/choose/compiler");
  expect(value()).toEqual({});
});

test("closing and reopening mobile navigation preserves the shell selection", async () => {
  function Shell() {
    const [open, setOpen] = useState(true);
    return (
      <FeatureScopeProvider>
        <button type="button" onClick={() => setOpen(!open)}>
          Menu
        </button>
        {open && <ScopeProbe />}
        <Outlet />
      </FeatureScopeProvider>
    );
  }
  const history = createMemoryHistory({
    initialEntries: ["/workspaces/ws/collections/col"],
  });
  const root = createRootRoute({ component: Shell });
  const page = createRoute({
    getParentRoute: () => root,
    path: "$",
    component: () => null,
  });
  const router = createRouter({ routeTree: root.addChildren([page]), history });
  render(<RouterProvider router={router} />);
  await waitFor(() =>
    expect(screen.getByTestId("scope").textContent).toBe(
      '{"workspaceId":"ws","collectionId":"col"}',
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Menu" }));
  expect(screen.queryByTestId("scope")).toBeNull();
  await act(async () => {
    history.push("/modelops/providers");
    await router.load();
  });
  fireEvent.click(screen.getByRole("button", { name: "Menu" }));
  expect(screen.getByTestId("scope").textContent).toBe(
    '{"workspaceId":"ws","collectionId":"col"}',
  );
});

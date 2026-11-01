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
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { WorkspaceSidebar } from "@/layouts/workspace-sidebar";
import { FeatureScopeProvider } from "@/navigation/use-feature-scope";

vi.mock("@/features/workspaces/queries", () => ({
  useWorkspaceQuery: () => ({
    isPending: false,
    isError: false,
    data: { name: "Workspace thử" },
  }),
  useCallerWorkspaceRole: () => ({
    isPending: false,
    role: { kind: "platform-admin" },
  }),
  useWorkspacesQuery: () => ({
    isPending: false,
    isError: false,
    data: {
      items: [{ id: "ws-test", name: "Workspace thử" }],
      meta: { total: 1 },
    },
  }),
}));
vi.mock("@/features/knowledge/queries", () => ({
  useCollectionQuery: () => ({ data: { name: "Kho thử" } }),
  useCollectionsQuery: () => ({
    isPending: false,
    isError: false,
    data: { items: [{ id: "col-test", name: "Kho thử" }], meta: { total: 1 } },
  }),
}));
vi.mock("@/app/auth/v1", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/auth/v1")>();
  return {
    ...actual,
    useV1Auth: () => ({
      isAuthenticated: true,
      sessionId: 1,
      actor: { roles: ["AI.Admin"] },
    }),
    isPlatformWorkspaceAdmin: () => true,
  };
});
vi.mock("@/components/ui/sidebar", () => ({
  SidebarGroup: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  SidebarGroupLabel: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  SidebarMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SidebarMenuItem: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  SidebarMenuButton: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
window.scrollTo = vi.fn();
afterEach(cleanup);

test("clicking the sidebar opens the chosen feature selection page", async () => {
  const { Route: selector } = await import(
    "@/routes/workspaces.choose.$feature"
  );
  const root = createRootRoute({
    component: () => (
      <FeatureScopeProvider>
        <WorkspaceSidebar />
        <Outlet />
      </FeatureScopeProvider>
    ),
  });
  const home = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <p>Trang chủ</p>,
  });
  const workspaces = createRoute({
    getParentRoute: () => root,
    path: "/workspaces",
    component: Outlet,
  });
  const choose = selector.update({
    id: "/choose/$feature",
    path: "/choose/$feature",
    getParentRoute: () => workspaces,
  } as never);
  const knowledge = createRoute({
    getParentRoute: () => workspaces,
    path: "/$workspaceId/knowledge",
    component: () => <p>Trang kho tri thức</p>,
  });
  const router = createRouter({
    routeTree: root.addChildren([
      home,
      workspaces.addChildren([choose, knowledge]),
    ]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("link", { name: "Kho tri thức" }));
  await waitFor(() =>
    expect(router.state.location.pathname).toBe(
      "/workspaces/ws-test/knowledge",
    ),
  );
  expect(await screen.findByText("Trang kho tri thức")).toBeTruthy();
});

test.each([
  ["ocr", "sources"],
  ["compiler", "compilations"],
  ["search", "index"],
])(
  "real router preserves %s through workspace and collection selection",
  async (feature, tab) => {
    const { Route: selector } = await import(
      "@/routes/workspaces.choose.$feature"
    );
    const root = createRootRoute({ component: Outlet });
    const workspaces = createRoute({
      getParentRoute: () => root,
      path: "/workspaces",
      component: Outlet,
    });
    const choose = selector.update({
      id: "/choose/$feature",
      path: "/choose/$feature",
      getParentRoute: () => workspaces,
    } as never);
    const collection = createRoute({
      getParentRoute: () => root,
      path: "/workspaces/$workspaceId/collections/$collectionId",
      component: () => <p>Kho đã chọn</p>,
    });
    const router = createRouter({
      routeTree: root.addChildren([
        workspaces.addChildren([choose]),
        collection,
      ]),
      history: createMemoryHistory({
        initialEntries: [`/workspaces/choose/${feature}`],
      }),
    });
    render(<RouterProvider router={router} />);
    fireEvent.click(
      await screen.findByRole("link", { name: "Chọn Workspace thử" }),
    );
    fireEvent.click(await screen.findByRole("link", { name: "Mở Kho thử" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        "/workspaces/ws-test/collections/col-test",
      ),
    );
    expect(router.state.location.search.tab).toBe(tab);
  },
);

test.each([
  ["answers", "answers"],
  ["evaluation", "evaluations"],
])(
  "real router opens the %s page after selecting a collection",
  async (feature, suffix) => {
    const { Route: selector } = await import(
      "@/routes/workspaces.choose.$feature"
    );
    const root = createRootRoute({ component: Outlet });
    const workspaces = createRoute({
      getParentRoute: () => root,
      path: "/workspaces",
      component: Outlet,
    });
    const choose = selector.update({
      id: "/choose/$feature",
      path: "/choose/$feature",
      getParentRoute: () => workspaces,
    } as never);
    const target = createRoute({
      getParentRoute: () => root,
      path: `/workspaces/$workspaceId/collections/$collectionId/${suffix}`,
      component: () => <p>Đích</p>,
    });
    const router = createRouter({
      routeTree: root.addChildren([workspaces.addChildren([choose]), target]),
      history: createMemoryHistory({
        initialEntries: [`/workspaces/choose/${feature}?workspaceId=ws-test`],
      }),
    });
    render(<RouterProvider router={router} />);
    fireEvent.click(await screen.findByRole("link", { name: "Mở Kho thử" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        `/workspaces/ws-test/collections/col-test/${suffix}`,
      ),
    );
  },
);

test("real router carries the chosen workspace to assistants", async () => {
  const { Route: selector } = await import(
    "@/routes/workspaces.choose.$feature"
  );
  const root = createRootRoute({ component: Outlet });
  const workspaces = createRoute({
    getParentRoute: () => root,
    path: "/workspaces",
    component: Outlet,
  });
  const choose = selector.update({
    id: "/choose/$feature",
    path: "/choose/$feature",
    getParentRoute: () => workspaces,
  } as never);
  const target = createRoute({
    getParentRoute: () => root,
    path: "/workspaces/$workspaceId/assistants",
    component: () => <p>Trợ lý</p>,
  });
  const router = createRouter({
    routeTree: root.addChildren([workspaces.addChildren([choose]), target]),
    history: createMemoryHistory({
      initialEntries: ["/workspaces/choose/assistants"],
    }),
  });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("link", { name: "Mở Trợ lý AI" }));
  await waitFor(() =>
    expect(router.state.location.pathname).toBe(
      "/workspaces/ws-test/assistants",
    ),
  );
});

// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
  useLocation,
  useNavigate,
} from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import {
  WorkspaceCanonicalLink,
  WorkspaceLinkBridge,
} from "@/features/workspaces/workspace-link-bridge";
import { preserveWorkspaceMask } from "@/navigation/workspace-links";

vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 1 }) }));
vi.mock("@/features/workspaces/queries", () => ({
  useWorkspaceQuery: (id: string) => ({
    data: id ? { id, code: "ctsv" } : undefined,
  }),
}));
vi.mock("@/app/api/v1", () => ({
  v1Client: {
    get: vi.fn(async () => ({
      workspace_id: "ws",
      code: "ctsv",
      collection_id: "col",
    })),
  },
}));
window.scrollTo = vi.fn();
afterEach(cleanup);

test.each([
  "/workspaces/ws/collections/col/sources/src?runId=run&page=2",
  "/ctsv/files/src?runId=run&page=2",
])(
  "legacy and fresh short link open the same revision view: %s",
  async (entry) => {
    const root = createRootRoute({
      component: () => (
        <>
          <WorkspaceCanonicalLink />
          <Outlet />
        </>
      ),
    });
    const source = createRoute({
      getParentRoute: () => root,
      path: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
      validateSearch: (search: Record<string, unknown>) => search,
      component: () => {
        const location = useLocation();
        const navigate = useNavigate();
        return (
          <button
            type="button"
            onClick={() => {
              const search = { ...location.search, page: 3 };
              void navigate({
                search,
                replace: true,
                mask: preserveWorkspaceMask(
                  location.maskedLocation?.pathname,
                  search,
                ),
              });
            }}
          >
            Tài liệu đã mở
          </button>
        );
      },
    });
    const short = createRoute({
      getParentRoute: () => root,
      path: "/$workspaceCode/$",
      validateSearch: (search: Record<string, unknown>) => search,
      component: WorkspaceLinkBridge,
    });
    const history = createMemoryHistory({ initialEntries: [entry] });
    const router = createRouter({
      routeTree: root.addChildren([source, short]),
      history,
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Tài liệu đã mở")).toBeTruthy();
    await waitFor(() =>
      expect(history.location.pathname).toBe("/ctsv/files/src"),
    );
    expect(router.state.location.pathname).toBe(
      "/workspaces/ws/collections/col/sources/src",
    );
    expect(router.state.location.search).toEqual({ runId: "run", page: 2 });
    expect(history.location.search).toContain("runId=run");
    const paths: string[] = [];
    const unsubscribe = history.subscribe(({ location }) => {
      paths.push(location.pathname);
    });
    fireEvent.click(screen.getByRole("button", { name: "Tài liệu đã mở" }));
    await waitFor(() => expect(history.location.search).toContain("page=3"));
    unsubscribe();
    expect(paths).toEqual(["/ctsv/files/src"]);
  },
);

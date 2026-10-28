// @vitest-environment jsdom
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FeatureEntryPage } from "@/features/workspaces/feature-entry-page";
import type { WorkspaceFeature } from "@/navigation/workspace-features";

const state = vi.hoisted(() => ({
  canCreate: true,
  role: { kind: "platform-admin" } as
    | { kind: "platform-admin" }
    | { kind: "member"; role: "member" },
  workspaceStatus: "active",
  collectionError: false,
  retry: vi.fn(),
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ actor: {} }),
  isPlatformWorkspaceAdmin: () => state.canCreate,
}));
vi.mock("@/features/workspaces/queries", () => ({
  useWorkspacesQuery: () => ({
    data: {
      items: [
        { id: "ws-test", name: "Đơn vị thử", status: state.workspaceStatus },
      ],
      meta: { total: 1 },
    },
  }),
  useWorkspaceQuery: () => ({
    data: { name: "Đơn vị thử" },
    refetch: vi.fn(),
  }),
  useCallerWorkspaceRole: () => ({ role: state.role }),
}));
vi.mock("@/features/knowledge/queries", () => ({
  useCollectionsQuery: () => ({
    isError: state.collectionError,
    error: state.collectionError ? new Error("Không tải được kho") : null,
    refetch: state.retry,
    data: { items: [], meta: { total: 0 } },
  }),
}));
vi.mock("@/features/knowledge/collection-form-dialog", () => ({
  CollectionFormDialog: ({ workspaceId }: { workspaceId: string }) => (
    <div role="dialog" aria-label="Tạo kho">
      {workspaceId}
    </div>
  ),
}));
window.scrollTo = vi.fn();
beforeEach(() => {
  state.canCreate = true;
  state.role = { kind: "platform-admin" };
  state.workspaceStatus = "active";
  state.collectionError = false;
  state.retry.mockClear();
});
afterEach(cleanup);

function mount(feature: WorkspaceFeature, workspaceId?: string) {
  const root = createRootRoute({
    component: () => (
      <FeatureEntryPage
        feature={feature}
        workspaceId={workspaceId}
        page={1}
        onPageChange={vi.fn()}
      />
    ),
  });
  const router = createRouter({
    routeTree: root,
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  render(<RouterProvider router={router} />);
}

test("empty collection chooser lets an admin create in the selected workspace", async () => {
  mount("compiler", "ws-test");
  fireEvent.click(
    await screen.findByRole("button", { name: "Tạo kho đầu tiên" }),
  );
  expect((await screen.findByRole("dialog")).textContent).toBe("ws-test");
  expect(screen.getByRole("heading", { name: "Biên soạn" })).toBeTruthy();
});

test("read-only members see guidance without a mutation action", async () => {
  state.role = { kind: "member", role: "member" };
  mount("ocr", "ws-test");
  expect(await screen.findByText("Chưa có kho tri thức")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Tạo kho/ })).toBeNull();
  expect(screen.getByText(/Liên hệ quản trị viên/)).toBeTruthy();
});

test("collection request failure is an error with retry, never an empty state", async () => {
  state.collectionError = true;
  mount("compiler", "ws-test");
  fireEvent.click(await screen.findByRole("button", { name: /Thử lại/ }));
  expect(state.retry).toHaveBeenCalledOnce();
  expect(screen.queryByText("Chưa có kho tri thức")).toBeNull();
});

test("suspended workspace exposes management instead of opening runtime features", async () => {
  state.workspaceStatus = "suspended";
  mount("assistants");
  expect(await screen.findByText("Tạm dừng")).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: "Quản lý trạng thái" })
      .getAttribute("href"),
  ).toBe("/workspaces/ws-test");
  expect(screen.queryByRole("link", { name: "Mở Trợ lý AI" })).toBeNull();
});

test("changing workspace keeps the requested feature and clears the old selection", async () => {
  mount("evaluation", "ws-test");
  const link = await screen.findByRole("link", { name: "Đổi workspace" });
  expect(link.getAttribute("href")).toBe(
    "/workspaces/choose/evaluation?page=1",
  );
});

// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { WorkspaceSidebar } from "@/layouts/workspace-sidebar";

const session = vi.hoisted(() => ({
  authenticated: true,
  scope: {} as { workspaceId?: string; collectionId?: string },
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ isAuthenticated: session.authenticated }),
}));
vi.mock("@/navigation/use-feature-scope", () => ({
  useFeatureScope: () => session.scope,
}));
vi.mock("@/features/workspaces/queries", () => ({
  useWorkspaceQuery: () => ({ data: { name: "Workspace thử" } }),
}));
vi.mock("@/features/knowledge/queries", () => ({
  useCollectionQuery: () => ({ data: { name: "Kho thử" } }),
}));
vi.mock("@tanstack/react-router", () => ({
  useRouterState: () => ({ pathname: "/workspaces", search: {} }),
  Link: ({
    children,
    to,
    params,
    search,
  }: {
    children: ReactNode;
    to: string;
    params?: unknown;
    search?: unknown;
  }) => (
    <a
      href="/fixture"
      data-route={to}
      data-params={JSON.stringify(params)}
      data-search={JSON.stringify(search)}
    >
      {children}
    </a>
  ),
}));
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
afterEach(() => {
  cleanup();
  session.authenticated = true;
  session.scope = {};
});

test("without workspace the available actions guide the user to workspace selection", () => {
  render(<WorkspaceSidebar />);
  expect(screen.getByText("Chưa chọn workspace")).toBeTruthy();
  for (const group of ["Tri thức", "Trợ lý", "Quản trị", "Vận hành"]) {
    expect(screen.getByText(group)).toBeTruthy();
  }
  for (const label of [
    "Kho tri thức",
    "OCR & chính tả",
    "Biên soạn",
    "Tìm kiếm",
    "Hỏi đáp",
    "Đánh giá RAG",
    "Trợ lý AI",
    "Hội thoại",
    "Thành viên",
    "Sao lưu",
  ]) {
    expect(
      screen.getByRole("link", { name: label }).getAttribute("data-route"),
    ).toBe("/workspaces/choose/$feature");
  }
});

test("workspace shortcuts use the selected workspace and operations view", () => {
  session.scope = { workspaceId: "ws-example" };
  render(<WorkspaceSidebar />);
  const collections = screen.getByRole("link", {
    name: "Kho tri thức",
  });
  expect(collections.getAttribute("data-route")).toBe(
    "/workspaces/$workspaceId/collections",
  );
  expect(JSON.parse(collections.getAttribute("data-params") ?? "null")).toEqual(
    {
      workspaceId: "ws-example",
    },
  );
  const backups = screen.getByRole("link", { name: "Sao lưu" });
  expect(JSON.parse(backups.getAttribute("data-search") ?? "null").view).toBe(
    "backups",
  );
  expect(
    JSON.parse(backups.getAttribute("data-params") ?? "null").workspaceId,
  ).toBe("ws-example");
});

test("workspace actions are hidden without a V1 session", () => {
  session.authenticated = false;
  session.scope = { workspaceId: "ws-example" };
  render(<WorkspaceSidebar />);
  expect(screen.queryByRole("link", { name: "Trợ lý AI" })).toBeNull();
});

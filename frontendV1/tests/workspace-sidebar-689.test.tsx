// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { WorkspaceSidebar } from "@/layouts/workspace-sidebar";

const session = vi.hoisted(() => ({
  authenticated: true,
  scope: {} as { workspaceId?: string; collectionId?: string },
  role: { kind: "platform-admin" } as
    | { kind: "platform-admin" }
    | { kind: "member"; role: "admin" | "editor" | "reviewer" | "member" },
}));
vi.mock("@/app/auth/v1", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/auth/v1")>();
  return {
    ...actual,
    useV1Auth: () => ({
      isAuthenticated: session.authenticated,
      actor: session.authenticated ? { roles: ["AI.Admin"] } : null,
    }),
  };
});
vi.mock("@/navigation/use-feature-scope", () => ({
  useFeatureScope: () => session.scope,
}));
vi.mock("@/features/workspaces/queries", () => ({
  useWorkspaceQuery: () => ({ data: { name: "Workspace thử" } }),
  useCallerWorkspaceRole: () => ({ isPending: false, role: session.role }),
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
  session.role = { kind: "platform-admin" };
});

test("without workspace the available actions guide the user to workspace selection", () => {
  render(<WorkspaceSidebar />);
  expect(screen.getByText("Điều hướng")).toBeTruthy();
  for (const label of ["Kho tri thức", "Trợ lý AI", "Hội thoại", "Tác vụ"]) {
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
    "/workspaces/$workspaceId/knowledge",
  );
  expect(JSON.parse(collections.getAttribute("data-params") ?? "null")).toEqual(
    {
      workspaceId: "ws-example",
    },
  );
  const jobs = screen.getByRole("link", { name: "Tác vụ" });
  expect(JSON.parse(jobs.getAttribute("data-search") ?? "null").view).toBe(
    "jobs",
  );
  expect(
    JSON.parse(jobs.getAttribute("data-params") ?? "null").workspaceId,
  ).toBe("ws-example");
});

test("workspace actions are hidden without a V1 session", () => {
  session.authenticated = false;
  session.scope = { workspaceId: "ws-example" };
  render(<WorkspaceSidebar />);
  expect(screen.queryByRole("link", { name: "Trợ lý AI" })).toBeNull();
});

test("a member keeps only lookup entries", () => {
  session.role = { kind: "member", role: "member" };
  session.scope = { workspaceId: "ws-example" };
  render(<WorkspaceSidebar />);
  for (const label of ["Trợ lý AI", "Hội thoại", "Kho tri thức"]) {
    expect(screen.getByRole("link", { name: label })).toBeTruthy();
  }
  for (const label of ["Chuẩn bị nội dung", "Xuất bản", "Tác vụ"]) {
    expect(screen.queryByRole("link", { name: label })).toBeNull();
  }
});

test("an editor gets preparation and publication entries scoped to the collection", () => {
  session.role = { kind: "member", role: "editor" };
  session.scope = { workspaceId: "ws-example", collectionId: "col-1" };
  render(<WorkspaceSidebar />);
  const compiler = screen.getByRole("link", { name: "Chuẩn bị nội dung" });
  expect(compiler.getAttribute("data-route")).toBe(
    "/workspaces/$workspaceId/collections/$collectionId",
  );
  expect(JSON.parse(compiler.getAttribute("data-search") ?? "null").tab).toBe(
    "compilations",
  );
  const documents = screen.getByRole("link", { name: "Xuất bản" });
  expect(JSON.parse(documents.getAttribute("data-search") ?? "null").tab).toBe(
    "documents",
  );
  expect(screen.getByRole("link", { name: "Tác vụ" })).toBeTruthy();
});

test("a reviewer sees publication before the knowledge folder", () => {
  session.role = { kind: "member", role: "reviewer" };
  session.scope = { workspaceId: "ws-example" };
  render(<WorkspaceSidebar />);
  const labels = screen
    .getAllByRole("link")
    .map((link) => link.textContent?.trim())
    .filter((label): label is string => Boolean(label));
  expect(labels.indexOf("Xuất bản")).toBeLessThan(
    labels.indexOf("Kho tri thức"),
  );
  expect(screen.queryByRole("link", { name: "Tác vụ" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Chuẩn bị nội dung" })).toBeNull();
});

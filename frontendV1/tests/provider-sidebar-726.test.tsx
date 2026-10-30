// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { WorkspaceSidebar } from "@/layouts/workspace-sidebar";
import { getBreadcrumbs } from "@/navigation/utils";

const session = vi.hoisted(() => ({ pathname: "/providers", manage: true }));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ isAuthenticated: true, actor: {} }),
  hasV1Permission: () => session.manage,
}));
vi.mock("@/navigation/use-feature-scope.tsx", () => ({
  useFeatureScope: () => ({}),
}));
vi.mock("@tanstack/react-router", () => ({
  useRouterState: () => ({ pathname: session.pathname, search: {} }),
  Link: ({
    children,
    to,
    "aria-current": current,
  }: {
    children: ReactNode;
    to: string;
    "aria-current"?: "page";
  }) => (
    <a href={to} aria-current={current}>
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
  session.manage = true;
  session.pathname = "/providers";
});

test.each([
  "/providers",
  "/providers/conn_test",
  "/modelops/providers/conn_test",
])("provider route %s highlights its direct sidebar item", (pathname) => {
  session.pathname = pathname;
  render(<WorkspaceSidebar />);
  expect(
    screen.getByRole("link", { name: "Nhà cung cấp" }).getAttribute("href"),
  ).toBe("/providers");
  expect(
    screen
      .getByRole("link", { name: "Nhà cung cấp" })
      .getAttribute("aria-current"),
  ).toBe("page");
  expect(
    screen.getByRole("link", { name: "Cấu hình" }).getAttribute("aria-current"),
  ).toBeNull();
  expect(getBreadcrumbs(pathname).map((item) => item.label)).toEqual([
    "QNU AI",
    "Nhà cung cấp",
  ]);
});
test("model management permission is required for the provider menu", () => {
  session.manage = false;
  render(<WorkspaceSidebar />);
  expect(screen.queryByRole("link", { name: "Nhà cung cấp" })).toBeNull();
});
test("system model defaults remain under settings", () => {
  session.pathname = "/modelops/defaults";
  render(<WorkspaceSidebar />);
  expect(
    screen.getByRole("link", { name: "Cấu hình" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(
    screen
      .getByRole("link", { name: "Nhà cung cấp" })
      .getAttribute("aria-current"),
  ).toBeNull();
});

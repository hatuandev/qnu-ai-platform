// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { Building2, FolderOpen, Library, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PageBreadcrumbs } from "@/components/admin/page-breadcrumbs";
import {
  Breadcrumb,
  BreadcrumbEllipsis,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    className,
  }: {
    children: ReactNode;
    to: string;
    className?: string;
  }) => (
    <a href={to} className={className} data-testid="router-link">
      {children}
    </a>
  ),
  useRouterState: () => ({
    location: { pathname: "/workspaces/ws-1", search: {} },
  }),
}));

afterEach(() => {
  cleanup();
});

describe("Breadcrumb UI Primitives", () => {
  it("renders standard WAI-ARIA semantic elements for accessibility", () => {
    render(
      <Breadcrumb aria-label="Đường dẫn thử nghiệm">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/home">Trang chủ</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbEllipsis />
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Tài liệu hiện tại</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>,
    );

    const nav = screen.getByRole("navigation", { name: "Đường dẫn thử nghiệm" });
    expect(nav).toBeDefined();

    const list = screen.getByRole("list");
    expect(list).toBeDefined();

    const link = screen.getByText("Trang chủ");
    expect(link.getAttribute("href")).toBe("/home");

    const currentPage = screen.getByText("Tài liệu hiện tại");
    expect(currentPage.getAttribute("aria-current")).toBe("page");
  });
});

describe("PageBreadcrumbs Component", () => {
  it("renders full hierarchy with icons, links, and current page", () => {
    render(
      <PageBreadcrumbs
        items={[
          {
            label: "Workspace",
            to: "/workspaces/$workspaceId",
            params: { workspaceId: "ws_demo" },
            icon: Building2,
          },
          {
            label: "Kho tri thức",
            to: "/workspaces/$workspaceId/collections",
            params: { workspaceId: "ws_demo" },
            icon: Library,
          },
          {
            label: "Demo1",
            to: "/workspaces/$workspaceId/collections/$collectionId",
            params: { workspaceId: "ws_demo", collectionId: "col_demo" },
            icon: FolderOpen,
          },
          {
            label: "Biên soạn Gen #1",
            icon: Sparkles,
            current: true,
          },
        ]}
      />,
    );

    // Links rendered with TanStack Router
    const routerLinks = screen.getAllByTestId("router-link");
    expect(routerLinks).toHaveLength(3);
    expect(routerLinks[0].textContent).toContain("Workspace");
    expect(routerLinks[1].textContent).toContain("Kho tri thức");
    expect(routerLinks[2].textContent).toContain("Demo1");

    // Current page is not a link and has aria-current="page"
    const current = screen.getByText("Biên soạn Gen #1");
    expect(current).toBeDefined();
    const pageSpan = current.closest('[aria-current="page"]');
    expect(pageSpan).not.toBeNull();
  });

  it("handles long labels by applying truncation and tooltip accessibility", () => {
    const longTitle = "Quy chế tuyển sinh đại học chính quy năm học 2026-2027 trường Đại học Quy Nhơn";
    render(
      <PageBreadcrumbs
        items={[
          {
            label: "Kho tri thức",
            to: "/knowledge",
            icon: Library,
          },
          {
            label: longTitle,
            current: true,
            maxChars: 20,
          },
        ]}
      />,
    );

    const titleSpan = screen.getByText(longTitle);
    expect(titleSpan.className).toContain("max-w-");
  });
});


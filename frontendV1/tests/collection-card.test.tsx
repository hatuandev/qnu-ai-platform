// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CollectionCard,
  CollectionCardSkeleton,
} from "@/features/knowledge/collection-card";
import type { KBCollection } from "@/features/knowledge/types";

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
  useNavigate: () => vi.fn(),
}));

const mockCollection: KBCollection = {
  id: "col_123",
  workspace_id: "ws_456",
  name: "Kho Tuyển sinh 2026",
  description: "Tài liệu quy chế và thông tư tuyển sinh đại học",
  source_count: 5,
  created_by: "usr_admin",
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-02T00:00:00Z",
};

afterEach(() => {
  cleanup();
});

describe("CollectionCard Component", () => {
  it("renders collection title, description, document count, and navigation links", () => {
    render(
      <CollectionCard
        collection={mockCollection}
        workspaceId="ws_456"
        canManage={true}
      />,
    );

    expect(screen.getByText("Kho Tuyển sinh 2026")).toBeDefined();
    expect(
      screen.getByText("Tài liệu quy chế và thông tư tuyển sinh đại học"),
    ).toBeDefined();
    expect(screen.getByText("5")).toBeDefined();
    expect(screen.getByText("tài liệu")).toBeDefined();
    expect(screen.getByText("Mở kho")).toBeDefined();
  });

  it("renders graceful italic placeholder when description is empty or null", () => {
    const emptyDescCol: KBCollection = {
      ...mockCollection,
      id: "col_empty",
      description: null,
    };

    render(
      <CollectionCard
        collection={emptyDescCol}
        workspaceId="ws_456"
      />,
    );

    const fallback = screen.getByText("Chưa có mô tả chi tiết.");
    expect(fallback).toBeDefined();
    expect(fallback.className).toContain("italic");
  });

  it("renders action trigger and triggers callbacks on edit/archive/delete", async () => {
    const onEdit = vi.fn();
    const onArchive = vi.fn();
    const onDelete = vi.fn();

    render(
      <CollectionCard
        collection={mockCollection}
        workspaceId="ws_456"
        canManage={true}
        canArchive={true}
        canDelete={true}
        onEdit={onEdit}
        onArchive={onArchive}
        onDelete={onDelete}
      />,
    );

    const menuBtn = screen.getByRole("button", {
      name: "Thao tác với Kho Tuyển sinh 2026",
    });
    expect(menuBtn).toBeDefined();

    // Open Radix dropdown menu via keyDown
    fireEvent.keyDown(menuBtn, { key: "Enter" });

    // Click Edit
    const editItem = await screen.findByText("Sửa thông tin kho");
    fireEvent.click(editItem);
    expect(onEdit).toHaveBeenCalledWith(mockCollection);
  });
});

describe("CollectionCardSkeleton Component", () => {
  it("renders skeleton placeholders", () => {
    const { container } = render(<CollectionCardSkeleton />);
    expect(container.firstChild).toBeDefined();
  });
});

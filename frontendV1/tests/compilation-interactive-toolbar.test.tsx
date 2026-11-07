// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompilationDraftSections } from "@/features/knowledge/compilation-draft-sections";

afterEach(cleanup);

const mockSections = [
  {
    heading: "QNU-TS2026-001 Mã trường Đại học Quy Nhơn là gì?",
    paragraphs: [
      {
        text: "Mã tuyển sinh của trường là DQN.",
        citations: ["cit-1"],
      },
    ],
  },
  {
    heading: "QNU-TS2026-002 Địa chỉ trường Đại học Quy Nhơn ở đâu?",
    paragraphs: [
      {
        text: "Trường nằm tại số 170 An Dương Vương, TP. Quy Nhơn.",
        citations: ["cit-2"],
      },
    ],
  },
  {
    heading: "QNU-TS2026-003 Học phí năm học 2026 như thế nào?",
    paragraphs: [
      {
        text: "Mức học phí trung bình khoảng 18 triệu đồng mỗi năm học.",
        citations: ["cit-3"],
      },
    ],
  },
];

describe("QNU Knowledge Studio Master-Detail & Multi-View Features", () => {
  it("defaults to Master-Detail Studio mode and allows selecting items", () => {
    const onSelectCitation = vi.fn();
    render(
      <CompilationDraftSections
        sections={mockSections}
        onSelectCitation={onSelectCitation}
      />,
    );

    // Initial state: Master list has all 3 items, item 0 is active
    expect(screen.getByText("Danh mục câu hỏi")).toBeTruthy();
    expect(screen.getByText(/Mã tuyển sinh của trường là DQN/)).toBeTruthy();
    expect(screen.queryByText(/số 170 An Dương Vương/)).toBeNull();

    // Click on item 2 in the master list
    const item2Button = screen.getByRole("button", {
      name: "QNU-TS2026-002 Địa chỉ trường Đại học Quy Nhơn ở đâu?",
    });
    fireEvent.click(item2Button);

    // Now item 2's answer is visible in the right workspace
    expect(screen.getByText(/số 170 An Dương Vương/)).toBeTruthy();
    expect(screen.queryByText(/Mã tuyển sinh của trường là DQN/)).toBeNull();

    // Click on citation button
    const citationBtn = screen.getByRole("button", {
      name: "Xem dẫn chứng 1 của đoạn 2.1",
    });
    fireEvent.click(citationBtn);
    expect(onSelectCitation).toHaveBeenCalledWith("cit-2");
  });

  it("supports next and previous navigation in Studio view", () => {
    render(
      <CompilationDraftSections
        sections={mockSections}
        onSelectCitation={vi.fn()}
      />,
    );

    // Initially at item 1
    expect(screen.getByText(/Mã tuyển sinh của trường là DQN/)).toBeTruthy();

    // Click "Tiếp" button
    const nextBtn = screen.getByTitle(/Câu tiếp theo/);
    fireEvent.click(nextBtn);

    // Advances to item 2
    expect(screen.getByText(/số 170 An Dương Vương/)).toBeTruthy();

    // Click "Trước" button
    const prevBtn = screen.getByTitle(/Câu trước/);
    fireEvent.click(prevBtn);

    // Back to item 1
    expect(screen.getByText(/Mã tuyển sinh của trường là DQN/)).toBeTruthy();
  });

  it("filters items via instant search in both Master list and detail pane", () => {
    render(
      <CompilationDraftSections
        sections={mockSections}
        onSelectCitation={vi.fn()}
      />,
    );

    const searchInput = screen.getByPlaceholderText(/Tìm câu hỏi, mã số/);
    fireEvent.change(searchInput, { target: { value: "Học phí" } });

    // Should match and auto-select item 3
    expect(
      screen.getByText(/Mức học phí trung bình khoảng 18 triệu/),
    ).toBeTruthy();

    // Clear search
    const clearBtn = screen.getByLabelText("Xóa từ khóa tìm kiếm");
    fireEvent.click(clearBtn);

    // Back to 3 items
    expect(screen.getByText(/Mã tuyển sinh của trường là DQN/)).toBeTruthy();
  });

  it("switches to Table Grid view and Document view seamlessly", () => {
    render(
      <CompilationDraftSections
        sections={mockSections}
        onSelectCitation={vi.fn()}
      />,
    );

    // Switch to Table view
    const tableBtn = screen.getByTitle(
      "Chế độ bảng dữ liệu phân trang kiểu FastGPT",
    );
    fireEvent.click(tableBtn);

    // Table headers should appear
    expect(screen.getByText("Mã hiệu")).toBeTruthy();
    expect(screen.getByText("Câu hỏi")).toBeTruthy();
    expect(screen.getByText("Câu trả lời tóm tắt")).toBeTruthy();

    // Switch to Document view
    const docBtn = screen.getByTitle("Chế độ đọc văn bản toàn trang liên tục");
    fireEvent.click(docBtn);

    // All 3 items are rendered in full continuous document
    expect(screen.getByText(/Mã tuyển sinh của trường là DQN/)).toBeTruthy();
    expect(screen.getByText(/số 170 An Dương Vương/)).toBeTruthy();
    expect(screen.getByText(/18 triệu đồng/)).toBeTruthy();
  });
});

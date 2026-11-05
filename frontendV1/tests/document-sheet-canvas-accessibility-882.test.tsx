// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  DocumentSheetCanvas,
  type DocumentSheetCanvasProps,
} from "@/features/knowledge/document-sheet-canvas";
import type { TextUnit } from "@/features/knowledge/ocr-types";

const unit: TextUnit = {
  evidence_id: "ev-1",
  page: 1,
  kind: "paragraph",
  text: "Nội dung đã lưu.",
  original_text: "Nội dung đã lưu.",
  bbox: {},
  row: null,
  column: null,
};

function renderCanvas(overrides: Partial<DocumentSheetCanvasProps> = {}) {
  const props: DocumentSheetCanvasProps = {
    sequentialBlocks: [
      {
        type: "prose",
        unit,
        blockId: "block-1",
        currentText: "Nội dung đang chỉnh.",
        hasUnsavedDraft: false,
        wasSavedPreviously: false,
      },
    ],
    canManage: true,
    canCompareOcr: false,
    onStartEdit: vi.fn(),
    onToggleUnitSelection: vi.fn(),
    workspaceId: "ws-1",
    collectionId: "col-1",
    sourceId: "src-1",
    revisionId: "rev-1",
    ...overrides,
  };
  render(<DocumentSheetCanvas {...props} />);
  return props;
}

afterEach(cleanup);

describe("Document canvas accessible actions", () => {
  it("allows editing and selecting an unfocused paragraph without hovering", () => {
    const props = renderCanvas();
    const edit = screen.getByRole("button", { name: /^Sửa / });
    const checkbox = screen.getByRole("checkbox", {
      name: /kiểm tra chính tả/,
    });
    edit.focus();
    expect(document.activeElement).toBe(edit);
    fireEvent.click(edit);
    expect(props.onStartEdit).toHaveBeenCalledWith(
      unit,
      "Nội dung đang chỉnh.",
    );
    checkbox.focus();
    expect(document.activeElement).toBe(checkbox);
    fireEvent.click(checkbox);
    expect(props.onToggleUnitSelection).toHaveBeenCalledWith("ev-1");
  });

  it("does not expose editing or spellcheck selection to read-only users", () => {
    renderCanvas({ canManage: false });
    expect(screen.queryByRole("button", { name: /^Sửa / })).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.getByText("Nội dung đang chỉnh.")).toBeDefined();
  });
});

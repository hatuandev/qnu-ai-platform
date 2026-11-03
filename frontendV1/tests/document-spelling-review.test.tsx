// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, test, vi } from "vitest";
import { DocumentSpellingReview } from "@/features/knowledge/document-spelling-review";
import type {
  ReviewDocument,
  Suggestion,
} from "@/features/knowledge/ocr-types";

test("reviews suggestions across pages and saves the shared draft once", () => {
  const locate = vi.fn();
  const save = vi.fn();
  const doc = {
    units: [
      { evidence_id: "a", text: "bán cũ" },
      { evidence_id: "b", text: "tuyền sinh" },
      { evidence_id: "c", text: "bãn sao" },
    ],
  } as ReviewDocument;
  const items = [
    {
      id: "a",
      page: 1,
      suggestion: {
        evidence_id: "a",
        start: 0,
        end: 3,
        original: "bán",
        replacement: "bản",
      } as Suggestion,
    },
    {
      id: "b",
      page: 5,
      suggestion: {
        evidence_id: "b",
        start: 0,
        end: 5,
        original: "tuyền",
        replacement: "tuyển",
      } as Suggestion,
    },
    {
      id: "c",
      page: 8,
      suggestion: {
        evidence_id: "c",
        start: 0,
        end: 3,
        original: "bãn",
        replacement: "bản",
      } as Suggestion,
    },
  ];
  function Harness() {
    const [draft, setDraft] = useState(new Map<string, string>());
    const write = (id: string, text: string) => {
      setDraft((previous) => new Map(previous).set(id, text));
      return true;
    };
    return (
      <DocumentSpellingReview
        items={items}
        doc={doc}
        draftChanges={draft}
        canManage
        onLocateUnit={locate}
        onApply={(suggestion) => write(suggestion.evidence_id, "bản cũ")}
        onEdit={write}
        onSave={() => save(Object.fromEntries(draft))}
      />
    );
  }
  render(<Harness />);
  expect(locate).toHaveBeenLastCalledWith({ evidenceId: "a", page: 1 });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
  expect(locate).toHaveBeenLastCalledWith({ evidenceId: "b", page: 5 });
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh tay" }));
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "tuyển sinh" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Lưu vào nháp" }));
  expect(locate).toHaveBeenLastCalledWith({ evidenceId: "c", page: 8 });
  fireEvent.click(screen.getByRole("button", { name: "Bỏ qua" }));
  expect(save).not.toHaveBeenCalled();
  expect(screen.getByRole("status").textContent).toContain("3/3");
  fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
  expect(save).toHaveBeenCalledExactlyOnceWith({
    a: "bản cũ",
    b: "tuyển sinh",
  });
});

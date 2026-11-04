// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { CitationDrawer } from "@/features/knowledge/citation-drawer";
import { CompilationDraftSections } from "@/features/knowledge/compilation-draft-sections";
import type {
  CitationDetail,
  LiteralTableEntry,
} from "@/features/knowledge/compilation-types";
import { SourceTablesView } from "@/features/knowledge/source-tables-view";

afterEach(cleanup);

test("sections render on expansion and pass the original citation identifier", () => {
  const select = vi.fn();
  render(
    <CompilationDraftSections
      sections={[
        {
          heading: "First",
          paragraphs: [{ text: "First text", citations: ["original-1"] }],
        },
        {
          heading: "Second",
          paragraphs: [{ text: "Second text", citations: ["original-2"] }],
        },
      ]}
      onSelectCitation={select}
    />,
  );
  expect(screen.getByText("First text")).toBeTruthy();
  expect(screen.queryByText("Second text")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Second", exact: true }));
  expect(screen.getByText("Second text")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Xem dẫn chứng 1 của đoạn 2.1" }),
  );
  expect(select).toHaveBeenCalledExactlyOnceWith("original-2");
});

test("the source outline presents stored paragraphs without changing their citations", () => {
  const select = vi.fn();
  render(
    <CompilationDraftSections
      sections={[
        {
          heading: "Nguồn 1 · Phần 1",
          paragraphs: [
            { text: "Nội dung trang 1", citations: ["original-1"] },
            { text: "Giá trị gốc", citations: ["original-2"] },
          ],
        },
      ]}
      readingGroups={[
        { heading: "Trang 1", paragraphs: [[0, 0]] },
        { heading: "Phụ lục", paragraphs: [[0, 1]] },
      ]}
      onSelectCitation={select}
    />,
  );
  expect(screen.queryByText("Nguồn 1 · Phần 1")).toBeNull();
  expect(screen.queryByText("Giá trị gốc")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Phụ lục" }));
  expect(screen.getByText("Giá trị gốc")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Xem dẫn chứng 1 của đoạn 2.1" }),
  );
  expect(select).toHaveBeenCalledExactlyOnceWith("original-2");
});

const tables = [
  {
    citation: "original-table",
    page_number: 4,
    table: {
      rows: [
        [{ text: "Merged header", header: true, row_span: 2, col_span: 2 }],
        [{ text: "Cell value", header: false, row_span: 1, col_span: 1 }],
      ],
    },
  },
] as LiteralTableEntry[];

test("deferred source tables keep merged cells and text when explicitly opened", () => {
  render(<SourceTablesView tables={tables} deferContent />);
  expect(screen.queryByRole("table")).toBeNull();
  fireEvent.click(
    screen.getByRole("button", { name: "Bảng nguồn 1", exact: true }),
  );
  expect(
    screen
      .getByRole("columnheader", { name: "Merged header" })
      .getAttribute("rowspan"),
  ).toBe("2");
  expect(
    screen
      .getByRole("columnheader", { name: "Merged header" })
      .getAttribute("colspan"),
  ).toBe("2");
  expect(screen.getByRole("cell", { name: "Cell value" })).toBeTruthy();
});

test("other table consumers retain their expanded view by default", () => {
  render(<SourceTablesView tables={tables} />);
  expect(screen.getByRole("table")).toBeTruthy();
});

test("a canonical citation page is used for source navigation", () => {
  const navigate = vi.fn();
  const detail: CitationDetail = {
    workspace_id: "w",
    collection_id: "c",
    source_id: "s",
    revision_id: "rev",
    filename: "Source.pdf",
    content_type: "application/pdf",
    evidence_id: "evidence",
    canonical_sha256: "canonical",
    manifest_sha256: "manifest",
    page: 7,
  };
  render(
    <CitationDrawer
      citationId="run:evidence"
      detail={detail}
      isOpen
      onClose={() => {}}
      onNavigateToOcr={navigate}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Mở đối chiếu OCR & Văn bản" }),
  );
  expect(navigate).toHaveBeenCalledExactlyOnceWith({
    sourceId: "s",
    revisionId: "rev",
    runId: "run",
    page: 7,
  });
});

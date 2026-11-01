import { describe, expect, test } from "vitest";
import {
  assessScan,
  compactScanText,
  type ScanDocument,
  type ScanReference,
} from "../e2e/stages/scan-ocr-assessment";

const hash = "a".repeat(64);
function fixture(): { document: ScanDocument; reference: ScanReference } {
  return {
    reference: {
      version: "test",
      label_status: "visual_samples",
      model_reference: "https://example.test/model",
      source: {
        path: "test.pdf",
        sha256: hash,
        pages: 1,
        native_text_pages: 0,
      },
      checks: [{ id: "s1", page: 1, text: "Năm 2026", minimum: 1 }],
      table_checks: [
        {
          page: 1,
          expected_columns: 2,
          minimum_empty_cells: 1,
          headers: ["Mã"],
        },
      ],
    },
    document: {
      identity: { source_sha256: hash, run_id: "run", revision_id: "rev" },
      processing: {},
      evidence: { block1: {}, table1: {} },
      pages: [
        {
          page_number: 1,
          status: "completed",
          image: { sha256: hash, width: 1200, height: 1600 },
          warnings: [],
          blocks: [
            {
              evidence_id: "block1",
              type: "text",
              text: "Năm\n2026",
              bbox: { x0: 0.1, y0: 0.1, x1: 0.8, y1: 0.2 },
            },
            {
              evidence_id: "table1",
              type: "table",
              text: "Mã\tGhi chú",
              bbox: { x0: 0.1, y0: 0.3, x1: 0.8, y1: 0.9 },
              table: {
                status: "parsed",
                column_count: 2,
                rows: [
                  [
                    { text: "Mã", row_span: 1, col_span: 1 },
                    { text: "", row_span: 1, col_span: 1 },
                  ],
                ],
              },
            },
          ],
        },
      ],
    },
  };
}

describe("scan OCR assessment follows the canonical contract", () => {
  test("canonical parsed tables, blank cells and pre-labelled text pass", () => {
    const { document, reference } = fixture();
    const result = assessScan(document, reference);
    expect(result.technical_pass).toBe(true);
    expect(result.sample_quality_pass).toBe(true);
  });
  test("normalization preserves diacritics, punctuation and numbers", () => {
    expect(compactScanText("ĐIỀU\n 1.")).toBe(compactScanText("Điều 1."));
    expect(compactScanText("điều")).not.toBe(compactScanText("dieu"));
    expect(compactScanText("1/3")).not.toBe(compactScanText("13"));
  });
  test("a wrong year or a snippet on another page is not accepted", () => {
    const { document, reference } = fixture();
    document.pages[0].blocks[0].text = "Năm 2025";
    expect(assessScan(document, reference).sample_quality_pass).toBe(false);
    reference.checks[0].page = 2;
    expect(assessScan(document, reference).anchors[0].passed).toBe(false);
  });
  test("unsupported table remains a failed sample even when its raw text matches", () => {
    const { document, reference } = fixture();
    const table = document.pages[0].blocks[1].table;
    if (!table) throw new Error("Missing fixture table");
    table.status = "unsupported";
    expect(assessScan(document, reference).tables[0].passed).toBe(false);
  });
  test("filling a required empty cell does not satisfy blank-cell preservation", () => {
    const { document, reference } = fixture();
    const table = document.pages[0].blocks[1].table;
    if (!table) throw new Error("Missing fixture table");
    table.rows[0][1].text = "Invented value";
    expect(assessScan(document, reference).tables[0].passed).toBe(false);
  });
  test("invented extra columns fail even when all extra cells are blank", () => {
    const { document, reference } = fixture();
    const table = document.pages[0].blocks[1].table;
    if (!table) throw new Error("Missing fixture table");
    table.column_count = 3;
    table.rows[0].push({ text: "", row_span: 1, col_span: 1 });
    expect(assessScan(document, reference).tables[0].passed).toBe(false);
  });
  test("missing evidence and duplicate pages fail the technical gate", () => {
    const { document, reference } = fixture();
    delete document.evidence.block1;
    expect(assessScan(document, reference).technical_pass).toBe(false);
    document.evidence.block1 = {};
    document.pages.push(document.pages[0]);
    expect(assessScan(document, reference).technical_pass).toBe(false);
  });
  test("reversed bounding box cannot pass the technical gate", () => {
    const { document, reference } = fixture();
    document.pages[0].blocks[0].bbox.x0 = 0.9;
    expect(assessScan(document, reference).technical_pass).toBe(false);
  });
});

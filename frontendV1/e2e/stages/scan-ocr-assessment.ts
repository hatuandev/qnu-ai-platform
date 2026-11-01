/** Visual reference samples, not a full transcription or an OCR confidence score. */
export interface ScanReference {
  version: string;
  label_status: string;
  source: {
    path: string;
    sha256: string;
    pages: number;
    native_text_pages: number;
  };
  model_reference: string;
  checks: { id: string; page: number; text: string; minimum: number }[];
  table_checks: {
    page: number;
    expected_columns: number;
    headers?: string[];
    minimum_empty_cells?: number;
  }[];
}

interface ScanTable {
  status: string;
  column_count: number;
  rows: { text: string; row_span: number; col_span: number }[][];
}
export interface ScanDocument {
  identity: { source_sha256: string; run_id: string; revision_id: string };
  processing: Record<string, unknown>;
  evidence: Record<string, unknown>;
  pages: {
    page_number: number;
    status: string;
    extraction_method?: string;
    image: { sha256: string; width: number; height: number };
    warnings: string[];
    blocks: {
      evidence_id: string;
      type: string;
      text: string;
      bbox: { x0: number; y0: number; x1: number; y1: number };
      table?: ScanTable;
    }[];
  }[];
}

// Only layout whitespace and case are ignored. Diacritics and numbers remain exact.
export const compactScanText = (text: string) =>
  text.normalize("NFC").toLocaleLowerCase("vi").replace(/\s+/gu, "");

export function assessScan(document: ScanDocument, reference: ScanReference) {
  const anchorChecks = reference.checks.map((check) => {
    const page = document.pages.find((item) => item.page_number === check.page);
    const text = compactScanText(
      (page?.blocks ?? []).map((block) => block.text).join("\n"),
    );
    const needle = compactScanText(check.text);
    const observed = needle ? text.split(needle).length - 1 : 0;
    return {
      id: check.id,
      page: check.page,
      observed,
      minimum: check.minimum,
      passed: observed >= check.minimum,
    };
  });
  const tableChecks = reference.table_checks.map((check) => {
    const page = document.pages.find((item) => item.page_number === check.page);
    const tables = (page?.blocks ?? []).flatMap((block) =>
      block.table ? [block.table] : [],
    );
    const observed = tables.map((table) => ({
      status: table.status,
      columns: table.column_count,
      empty_cells: table.rows.flat().filter((cell) => cell.text.trim() === "")
        .length,
      missing_headers: (check.headers ?? []).filter(
        (header) =>
          !table.rows
            .flat()
            .some((cell) =>
              compactScanText(cell.text).includes(compactScanText(header)),
            ),
      ),
    }));
    return {
      page: check.page,
      observed,
      passed: observed.some(
        (table) =>
          table.status === "parsed" &&
          table.columns === check.expected_columns &&
          table.empty_cells >= (check.minimum_empty_cells ?? 0) &&
          table.missing_headers.length === 0,
      ),
    };
  });
  const pageChecks = Array.from({ length: reference.source.pages }, (_, i) => {
    const matches = document.pages.filter((page) => page.page_number === i + 1);
    const page = matches[0];
    return {
      page: i + 1,
      blocks: page?.blocks.length ?? 0,
      warnings: page?.warnings ?? [],
      passed:
        matches.length === 1 &&
        page.status === "completed" &&
        page.blocks.length > 0 &&
        page.blocks.every(
          (block) =>
            Boolean(document.evidence[block.evidence_id]) &&
            [block.bbox.x0, block.bbox.y0, block.bbox.x1, block.bbox.y1].every(
              (value) => Number.isFinite(value) && value >= 0 && value <= 1,
            ) &&
            block.bbox.x0 < block.bbox.x1 &&
            block.bbox.y0 < block.bbox.y1,
        ),
    };
  });
  return {
    label_status: reference.label_status,
    pages: pageChecks,
    anchors: anchorChecks,
    tables: tableChecks,
    technical_pass:
      document.identity.source_sha256 === reference.source.sha256 &&
      document.pages.length === reference.source.pages &&
      pageChecks.every((page) => page.passed),
    sample_quality_pass:
      anchorChecks.every((check) => check.passed) &&
      tableChecks.every((check) => check.passed),
    limitation:
      "Visual samples on seven pages; no full-document CER/WER or handwriting/signature accuracy claim.",
  };
}

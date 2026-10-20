export interface ReaderReference {
  id: string;
  target_id: string;
  block_id: string;
  block_anchor: string;
  label: string;
  table?: { row: number; column: number } | null;
}

export interface ReaderTable {
  headers: string[];
  column_ids: string[];
  rows: string[][];
  row_ids: string[];
  references: ReaderReference[];
  layout: {
    rows: number;
    columns: number;
    header_rows: number;
    cells: {
      text: string;
      row_start: number;
      row_end: number;
      col_start: number;
      col_end: number;
    }[];
  } | null;
}

export interface QnuReaderDocument {
  version: "qnu-reader/v1";
  title: string;
  revision_id: string;
  binding_id: string;
  markdown: string;
  limitations?: { block_id: string; code: string; detail: string }[];
  blocks: {
    id: string;
    anchor: string;
    type: string;
    markdown: string;
    references: ReaderReference[];
    embedded_references?: ReaderReference[];
    table?: ReaderTable;
  }[];
  notes: {
    id: string;
    anchor: string;
    label: string;
    markdown: string;
    anchors: ReaderReference[];
    unresolved: boolean;
  }[];
}

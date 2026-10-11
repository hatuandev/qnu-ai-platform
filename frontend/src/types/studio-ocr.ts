/** Types for Studio OCR & Document Sandbox */

export interface StudioOCRRegion {
  id?: string;
  readingOrder?: number;
  layoutConfidence?: number | null;
  textConfidence?: number | null;
  type: string;
  label: string;
  text: string;
  top: number;
  left: number;
  width: number;
  height: number;
  confidence?: number;
}

export interface StudioOCRPage {
  pageNumber: number;
  title: string;
  isSigned: boolean;
  hasTable: boolean;
  imageUrl: string;
  markdown: string;
  rawText: string;
  regions: StudioOCRRegion[];
  dimensions: { width: number; height: number };
  wordCount: number;
  lineCount: number;
  sheetData?: {
    name: string;
    rows: string[][];
    total_rows?: number;
    total_cols?: number;
  };
}

export interface StudioOCRDocument {
  revisionId?: string;
  filename: string;
  totalPages: number;
  size: string;
  provider: string;
  model: string;
  latencyMs: number;
  status?: string;
  indexStatus?: string;
  pdfUrl?: string;
  pages: StudioOCRPage[];
  sheetsData?: {
    name: string;
    rows: string[][];
    total_rows?: number;
    total_cols?: number;
  }[];
}

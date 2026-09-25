/** Types, Constants & Enums for OCR Studio & Document Verification */

import type { StudioOCRPage, StudioOCRRegion } from "@/services/api-client";

export type OcrViewMode = "rendered" | "raw" | "edit";
export type OcrRightTab =
  | "entities"
  | "text"
  | "markdown"
  | "excel"
  | "regions"
  | "json";
export type OcrRegionFilter = "all" | "table" | "signature" | "text";
export type OcrViewLayoutMode = "continuous" | "single";

export interface OcrRegionStyle {
  bg: string;
  border: string;
  text: string;
  badge: string;
}

export const REGION_COLORS: Record<string, OcrRegionStyle> = {
  header: {
    bg: "rgba(100, 116, 139, 0.08)",
    border: "#64748b",
    text: "#334155",
    badge: "#475569",
  },
  title: {
    bg: "rgba(13, 148, 136, 0.08)",
    border: "#0d9488",
    text: "#0f766e",
    badge: "#0d9488",
  },
  text: {
    bg: "rgba(100, 116, 139, 0.06)",
    border: "#94a3b8",
    text: "#475569",
    badge: "#64748b",
  },
  list: {
    bg: "rgba(13, 148, 136, 0.06)",
    border: "#14b8a6",
    text: "#0f766e",
    badge: "#0d9488",
  },
  table: {
    bg: "rgba(13, 148, 136, 0.12)",
    border: "#0d9488",
    text: "#0f766e",
    badge: "#0d9488",
  },
  signature: {
    bg: "rgba(16, 185, 129, 0.08)",
    border: "#059669",
    text: "#047857",
    badge: "#059669",
  },
  stamp: {
    bg: "rgba(225, 29, 72, 0.08)",
    border: "#e11d48",
    text: "#be123c",
    badge: "#e11d48",
  },
};

export interface OcrEngineOption {
  value: string;
  label: string;
  description: string;
}

export const OCR_ENGINE_OPTIONS: OcrEngineOption[] = [
  {
    value: "auto",
    label: "Tự động phân giải (Auto Pipeline)",
    description: "Tự động chọn PyMuPDF hoặc OCR tùy thuộc vào mật độ text thô",
  },
  {
    value: "pymupdf_ocr",
    label: "PyMuPDF OCR (Tesseract Engine)",
    description: "Tối ưu hóa tài liệu scan tiếng Việt tiêu chuẩn và bảng biểu",
  },
  {
    value: "docling",
    label: "Docling Parser (Deep Document Analysis)",
    description: "Phân tích cấu trúc phân cấp, nhận diện layout học thuật sâu",
  },
  {
    value: "easyocr",
    label: "EasyOCR (Deep Learning Vision)",
    description: "Mô hình mạng nơ-ron nhận diện văn bản mờ, ảnh chụp nghiêng",
  },
];

export interface OcrCanvasProps {
  pageData: StudioOCRPage | null;
  allPages?: StudioOCRPage[];
  layoutMode?: OcrViewLayoutMode;
  zoomLevel: number;
  showBoxes: boolean;
  filteredRegions: StudioOCRRegion[];
  selectedRegion: StudioOCRRegion | null;
  onSelectRegion: (region: StudioOCRRegion | null) => void;
  documentTitle?: string;
  pdfUrl?: string;
  onPageChange?: (newPage: number) => void;
}

export interface OcrToolbarProps {
  currentPage: number;
  totalPages: number;
  pageInput: string;
  onPageInputChange: (value: string) => void;
  onPageChange: (newPage: number) => void;
  zoomLevel: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  onFitWidth?: () => void;
  showBoxes: boolean;
  onToggleBoxes: (show: boolean) => void;
  layoutMode?: OcrViewLayoutMode;
  onToggleLayoutMode?: (mode: OcrViewLayoutMode) => void;
  regionFilter?: OcrRegionFilter;
  onRegionFilterChange?: (filter: OcrRegionFilter) => void;
  selectedEngine?: string;
  onSelectEngine?: (engine: string) => void;
  disabled?: boolean;
}

export interface OcrInspectorProps {
  pageData: StudioOCRPage | null;
  allPages?: StudioOCRPage[];
  documentTitle?: string;
  documentFilename?: string;
  rightTab: OcrRightTab;
  onTabChange: (tab: OcrRightTab) => void;
  markdownViewMode: OcrViewMode;
  onMarkdownViewModeChange: (mode: OcrViewMode) => void;
  editableMarkdown: string;
  onMarkdownChange: (text: string) => void;
  selectedRegion: StudioOCRRegion | null;
  onSelectRegion: (region: StudioOCRRegion | null) => void;
  onCopyContent: (text: string) => void;
  isCopied: boolean;
  isEditable?: boolean;
  onJumpToPage?: (pageNumber: number) => void;
}

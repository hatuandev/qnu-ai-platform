/** Types, Constants & Enums for OCR Studio & Document Verification */

import type { StudioOCRPage, StudioOCRRegion } from "@/services/api-client";

export type OcrViewMode = "rendered" | "raw" | "edit";
export type OcrRightTab = "markdown" | "excel" | "regions" | "json";
export type OcrRegionFilter = "all" | "table" | "signature" | "text";

export interface OcrRegionStyle {
  bg: string;
  border: string;
  text: string;
  badge: string;
}

export const REGION_COLORS: Record<string, OcrRegionStyle> = {
  header: {
    bg: "rgba(59, 130, 246, 0.12)",
    border: "#3b82f6",
    text: "#1d4ed8",
    badge: "#2563eb",
  },
  title: {
    bg: "rgba(139, 92, 246, 0.14)",
    border: "#8b5cf6",
    text: "#6d28d9",
    badge: "#7c3aed",
  },
  text: {
    bg: "rgba(168, 85, 247, 0.10)",
    border: "#a855f7",
    text: "#7e22ce",
    badge: "#9333ea",
  },
  list: {
    bg: "rgba(16, 185, 129, 0.12)",
    border: "#10b981",
    text: "#047857",
    badge: "#059669",
  },
  table: {
    bg: "rgba(245, 158, 11, 0.16)",
    border: "#f59e0b",
    text: "#b45309",
    badge: "#d97706",
  },
  signature: {
    bg: "rgba(244, 63, 94, 0.18)",
    border: "#f43f5e",
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
  zoomLevel: number;
  showBoxes: boolean;
  filteredRegions: StudioOCRRegion[];
  selectedRegion: StudioOCRRegion | null;
  onSelectRegion: (region: StudioOCRRegion | null) => void;
  documentTitle?: string;
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
  showBoxes: boolean;
  onToggleBoxes: (show: boolean) => void;
  regionFilter: OcrRegionFilter;
  onRegionFilterChange: (filter: OcrRegionFilter) => void;
  selectedEngine: string;
  onSelectEngine: (engine: string) => void;
  disabled?: boolean;
}

export interface OcrInspectorProps {
  pageData: StudioOCRPage | null;
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
}

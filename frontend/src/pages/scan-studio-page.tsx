import {
  ExcelSpreadsheetViewer,
  parseMarkdownTablesToSheets,
} from "@/components/admin/excel-spreadsheet-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  type KnowledgeCollection,
  type StudioOCRDocument,
  type StudioOCRPage,
  type StudioOCRRegion,
  apiClient,
} from "@/services/api-client";
import {
  AlertCircle,
  BookOpen,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Code,
  Copy,
  FileCode,
  FileSpreadsheet,
  FileText,
  Layers,
  Loader2,
  RotateCcw,
  Scan,
  Sparkles,
  Upload,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const REGION_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  header: { bg: "rgba(59, 130, 246, 0.12)", border: "#3b82f6", text: "#1d4ed8", badge: "#2563eb" },
  title: { bg: "rgba(139, 92, 246, 0.14)", border: "#8b5cf6", text: "#6d28d9", badge: "#7c3aed" },
  text: { bg: "rgba(168, 85, 247, 0.10)", border: "#a855f7", text: "#7e22ce", badge: "#9333ea" },
  list: { bg: "rgba(16, 185, 129, 0.12)", border: "#10b981", text: "#047857", badge: "#059669" },
  table: { bg: "rgba(245, 158, 11, 0.16)", border: "#f59e0b", text: "#b45309", badge: "#d97706" },
  signature: {
    bg: "rgba(244, 63, 94, 0.18)",
    border: "#f43f5e",
    text: "#be123c",
    badge: "#e11d48",
  },
};

export const ScanStudioPage: React.FC = () => {
  const [doc, setDoc] = useState<StudioOCRDocument | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>("1");
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [regionFilter, setRegionFilter] = useState<"all" | "table" | "signature" | "text">("all");
  const [selectedRegion, setSelectedRegion] = useState<StudioOCRRegion | null>(null);
  const [rightTab, setRightTab] = useState<"markdown" | "excel" | "regions" | "json">("markdown");
  const [markdownViewMode, setMarkdownViewMode] = useState<"rendered" | "raw">("rendered");

  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [selectedEngine, setSelectedEngine] = useState<string>("pymupdf_ocr");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // Dialog states
  const [codeModalOpen, setCodeModalOpen] = useState<boolean>(false);
  const [saveModalOpen, setSaveModalOpen] = useState<boolean>(false);
  const [collections, setCollections] = useState<KnowledgeCollection[]>([]);
  const [targetCollectionId, setTargetCollectionId] = useState<string>("");
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load sample document on initial mount
  useEffect(() => {
    async function loadSample() {
      setIsProcessing(true);
      try {
        const sample = await apiClient.getStudioSampleDocument();
        setDoc(sample);
      } catch (_err) {
        setErrorMessage("Không thể tải tài liệu mẫu. Vui lòng chọn tệp thủ công.");
      } finally {
        setIsProcessing(false);
      }
    }
    loadSample();
  }, []);

  // Update page input when page changes
  useEffect(() => {
    setPageInput(String(currentPage));
    setSelectedRegion(null);
  }, [currentPage]);

  const currentPageData: StudioOCRPage | null = useMemo(() => {
    if (!doc?.pages || doc.pages.length === 0) return null;
    const found = doc.pages.find((p) => p.pageNumber === currentPage);
    return found || doc.pages[0];
  }, [doc, currentPage]);

  const filteredRegions = useMemo(() => {
    if (!currentPageData?.regions) return [];
    if (regionFilter === "all") return currentPageData.regions;
    return currentPageData.regions.filter((r) => {
      if (regionFilter === "table") return r.type === "table";
      if (regionFilter === "signature") return r.type === "signature";
      if (regionFilter === "text")
        return r.type === "text" || r.type === "header" || r.type === "title" || r.type === "list";
      return true;
    });
  }, [currentPageData, regionFilter]);

  const totalPages = doc?.totalPages || doc?.pages?.length || 1;

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const parsed = await apiClient.parseStudioOcr(file, selectedEngine);
      setDoc(parsed);
      setCurrentPage(1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã xảy ra lỗi khi phân tích văn bản.";
      setErrorMessage(msg);
    } finally {
      setIsProcessing(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleLoadSample = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const sample = await apiClient.getStudioSampleDocument();
      setDoc(sample);
      setCurrentPage(1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể tải tài liệu mẫu.";
      setErrorMessage(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOpenSaveDialog = async () => {
    setSaveModalOpen(true);
    setSaveSuccess(false);
    try {
      const colList = await apiClient.getCollections();
      setCollections(colList);
      if (colList.length > 0 && !targetCollectionId) {
        setTargetCollectionId(colList[0].id);
      }
    } catch (_err) {
      // ignore
    }
  };

  const handleConfirmSave = async () => {
    if (!targetCollectionId || !doc) return;
    setIsSaving(true);
    try {
      const blob = new Blob(
        [doc.pages.map((p) => `<!-- Page ${p.pageNumber} -->\n${p.markdown}`).join("\n\n---\n\n")],
        { type: "text/markdown" }
      );
      const fileToUpload = new File([blob], doc.filename.replace(/\.pdf$/i, ".md"), {
        type: "text/markdown",
      });
      await apiClient.uploadDocument(targetCollectionId, fileToUpload, "auto");
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveModalOpen(false);
        setSaveSuccess(false);
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi khi lưu tài liệu.";
      alert(msg);
    } finally {
      setIsSaving(false);
    }
  };

  // Spreadsheet data detection
  const isSpreadsheet = useMemo(() => {
    const fn = (doc?.filename || "").toLowerCase();
    return (
      fn.endsWith(".xlsx") ||
      fn.endsWith(".xls") ||
      Boolean(currentPageData?.sheetData) ||
      Boolean(doc?.sheetsData && doc.sheetsData.length > 0)
    );
  }, [doc, currentPageData]);

  const spreadsheetSheets = useMemo(() => {
    if (currentPageData?.sheetData) {
      return [currentPageData.sheetData];
    }
    if (doc?.sheetsData && doc.sheetsData.length > 0) {
      return doc.sheetsData;
    }
    if (isSpreadsheet && currentPageData?.markdown) {
      return parseMarkdownTablesToSheets(currentPageData.markdown, doc?.filename || "Sheet1");
    }
    return [];
  }, [currentPageData, doc, isSpreadsheet]);

  const markdownComponents = useMemo(
    () => ({
      table: ({ children }: { children?: React.ReactNode }) => (
        <div className="my-3 overflow-x-auto rounded-md border border-border shadow-xs">
          <table className="min-w-full text-left text-xs divide-y divide-border border-collapse">
            {children}
          </table>
        </div>
      ),
      thead: ({ children }: { children?: React.ReactNode }) => (
        <thead className="bg-muted/80 text-foreground font-semibold border-b border-border">
          {children}
        </thead>
      ),
      th: ({ children }: { children?: React.ReactNode }) => (
        <th className="px-3 py-2 text-xs font-semibold tracking-wider text-muted-foreground border border-border bg-muted/50 whitespace-nowrap">
          {children}
        </th>
      ),
      td: ({ children }: { children?: React.ReactNode }) => (
        <td className="px-3 py-2 text-xs text-foreground/90 border border-border align-top leading-relaxed">
          {children}
        </td>
      ),
      tr: ({ children }: { children?: React.ReactNode }) => (
        <tr className="hover:bg-muted/40 transition-colors even:bg-muted/10">{children}</tr>
      ),
      blockquote: ({ children }: { children?: React.ReactNode }) => (
        <blockquote className="border-l-4 border-primary bg-primary/5 px-3.5 py-2.5 rounded-r-md my-3 italic text-foreground/80 text-xs">
          {children}
        </blockquote>
      ),
      h1: ({ children }: { children?: React.ReactNode }) => (
        <h1 className="text-base font-bold text-foreground mt-4 mb-2 pb-1 border-b border-border/60">
          {children}
        </h1>
      ),
      h2: ({ children }: { children?: React.ReactNode }) => (
        <h2 className="text-sm font-bold text-foreground mt-3 mb-1.5">{children}</h2>
      ),
      h3: ({ children }: { children?: React.ReactNode }) => (
        <h3 className="text-xs font-semibold text-primary mt-2.5 mb-1 uppercase tracking-wider">
          {children}
        </h3>
      ),
      p: ({ children }: { children?: React.ReactNode }) => (
        <p className="my-1.5 leading-relaxed text-xs">{children}</p>
      ),
    }),
    []
  );

  return (
    <div className="flex flex-col h-[calc(100vh-4.5rem)] space-y-3">
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx,.xls"
        className="hidden"
      />

      {/* 1. TOP HEADER TOOLBAR */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card border border-border rounded-lg px-4 py-3 shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0 border border-primary/20">
            <Scan className="size-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold text-foreground">
                Document Intelligence & Scan Studio
              </h1>
              <Badge
                variant="default"
                className="text-[11px] h-5 bg-primary/15 text-primary hover:bg-primary/20"
              >
                Studio
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Bóc tách văn bản scan, nhận diện bảng biểu, con dấu và kiểm soát Bounding Boxes với độ
              chính xác cao.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Engine Selector */}
          <div className="w-52">
            <Select value={selectedEngine} onValueChange={setSelectedEngine}>
              <SelectTrigger sizeVariant="sm" className="w-full">
                <SelectValue placeholder="Chọn engine" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pymupdf_ocr">PyMuPDF (Nhanh, text)</SelectItem>
                <SelectItem value="docling">Docling TableFormer</SelectItem>
                <SelectItem value="easyocr">EasyOCR (Scan, dấu đỏ)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Load Sample Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleLoadSample}
            disabled={isProcessing}
            className="h-8 text-xs gap-1.5"
            title="Nạp nhanh 14 trang Đề án Tuyển sinh 2026 của ĐH Quy Nhơn"
          >
            <Sparkles className="size-3.5 text-amber-500" />
            <span>Tài liệu mẫu QNU</span>
          </Button>

          {/* Upload Button */}
          <Button
            variant="default"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            className="h-8 text-xs gap-1.5"
          >
            {isProcessing ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Upload className="size-3.5" />
            )}
            <span>{isProcessing ? "Đang xử lý..." : "Tải tệp lên"}</span>
          </Button>

          {/* Code API button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCodeModalOpen(true)}
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
            title="Xem mã nguồn tích hợp qua cURL / Python"
          >
            <Code className="size-3.5" />
            <span className="hidden md:inline">Code API</span>
          </Button>

          {/* Save to Knowledge button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenSaveDialog}
            disabled={!doc}
            className="h-8 text-xs gap-1.5 border-primary/30 text-primary hover:bg-primary/10"
          >
            <BookOpen className="size-3.5" />
            <span>Lưu vào Kho</span>
          </Button>
        </div>
      </div>

      {/* Error banner */}
      {errorMessage && (
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-xs">
          <AlertCircle className="size-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 2. MAIN SPLIT-PANE WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0">
        {/* LEFT COLUMN: VISUAL DOCUMENT VIEWER (7 COLS) */}
        <div className="lg:col-span-7 flex flex-col bg-card border border-border rounded-lg overflow-hidden shadow-xs">
          {/* Canvas Toolbar */}
          <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-b border-border gap-2 text-xs flex-wrap">
            {/* Pagination Controls */}
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1}
                className="size-7"
                title="Trang đầu"
              >
                <ChevronsLeft className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="size-7"
                title="Trang trước"
              >
                <ChevronLeft className="size-3.5" />
              </Button>
              <div className="flex items-center gap-1 font-mono font-semibold text-foreground whitespace-nowrap text-xs px-1">
                <span>Trang</span>
                <input
                  type="text"
                  value={pageInput}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setPageInput(e.target.value)
                  }
                  onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                    if (e.key === "Enter") {
                      const p = Number.parseInt(pageInput, 10);
                      if (!Number.isNaN(p) && p >= 1 && p <= totalPages) {
                        setCurrentPage(p);
                      } else {
                        setPageInput(String(currentPage));
                      }
                    }
                  }}
                  className="w-9 h-6 text-center font-mono font-semibold text-foreground bg-background border border-border rounded text-xs"
                />
                <span>/ {totalPages}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage >= totalPages}
                className="size-7"
                title="Trang sau"
              >
                <ChevronRight className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage >= totalPages}
                className="size-7"
                title="Trang cuối"
              >
                <ChevronsRight className="size-3.5" />
              </Button>
            </div>

            {/* Zoom & Bounding Box Controls */}
            <div className="flex items-center gap-1.5">
              <div className="flex items-center rounded-md border border-border bg-background">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setZoomLevel((prev) => Math.max(50, prev - 15))}
                  className="size-6 rounded-none text-muted-foreground"
                  title="Thu nhỏ"
                >
                  <ZoomOut className="size-3" />
                </Button>
                <span className="px-1.5 font-mono text-[11px] text-muted-foreground w-11 text-center">
                  {zoomLevel}%
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setZoomLevel((prev) => Math.min(200, prev + 15))}
                  className="size-6 rounded-none text-muted-foreground"
                  title="Phóng to"
                >
                  <ZoomIn className="size-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setZoomLevel(100)}
                  className="size-6 rounded-none border-l border-border text-muted-foreground"
                  title="Tỷ lệ chuẩn 100%"
                >
                  <RotateCcw className="size-3" />
                </Button>
              </div>

              {/* Toggle Boxes */}
              <Button
                variant={showBoxes ? "default" : "outline"}
                size="sm"
                onClick={() => setShowBoxes(!showBoxes)}
                className={`h-7 px-2 text-[11px] gap-1 ${showBoxes ? "bg-primary text-primary-foreground" : ""}`}
              >
                <Layers className="size-3" />
                <span>Khung</span>
              </Button>

              {/* Filter dropdown */}
              <div className="w-28">
                <Select
                  value={regionFilter}
                  onValueChange={(val) => setRegionFilter(val as typeof regionFilter)}
                >
                  <SelectTrigger sizeVariant="sm" className="h-7 text-[11px] px-2 w-full">
                    <SelectValue placeholder="Tất cả" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tất cả</SelectItem>
                    <SelectItem value="table">Bảng</SelectItem>
                    <SelectItem value="signature">Dấu / Ký</SelectItem>
                    <SelectItem value="text">Chữ</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Document Canvas Container */}
          <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/20 relative">
            {currentPageData ? (
              <div
                className="relative bg-white shadow-lg border border-border rounded-sm transition-transform duration-100 select-none origin-top"
                style={{
                  width: `${(800 * zoomLevel) / 100}px`,
                  height: `${(1131 * zoomLevel) / 100}px`,
                }}
              >
                {/* Page Image */}
                <img
                  src={
                    currentPageData.imageUrl.startsWith("/")
                      ? currentPageData.imageUrl
                      : `/api/v1/ocr/studio/page-image/${doc?.filename || "demo"}/page_${currentPage}.jpg`
                  }
                  alt={`Trang ${currentPage}`}
                  className="w-full h-full object-contain pointer-events-none"
                  onError={(e) => {
                    // Fallback to local cached sample if API image is unavailable
                    const target = e.currentTarget;
                    if (!target.src.includes("/ocr-cache/doc_ts_2026/")) {
                      target.src = `/ocr-cache/doc_ts_2026/page_${currentPage}.jpg`;
                    }
                  }}
                />

                {/* Bounding Boxes Layer */}
                {showBoxes &&
                  filteredRegions.map((region, idx) => {
                    const colorStyle = REGION_COLORS[region.type] || REGION_COLORS.text;
                    const isSelected = selectedRegion === region;
                    return (
                      <button
                        type="button"
                        key={`box-${region.type}-${idx}-${region.top}-${region.left}`}
                        onClick={() => setSelectedRegion(region)}
                        className={`absolute border-2 transition-all cursor-pointer group text-left p-0 ${
                          isSelected ? "ring-2 ring-primary ring-offset-1 z-20" : "z-10"
                        }`}
                        style={{
                          top: `${region.top}%`,
                          left: `${region.left}%`,
                          width: `${region.width}%`,
                          height: `${region.height}%`,
                          backgroundColor: colorStyle.bg,
                          borderColor: colorStyle.border,
                        }}
                        title={`${region.label}: ${region.text}`}
                      >
                        {/* Tag Label */}
                        <div
                          className="absolute -top-5 left-0 px-1 py-0.2 text-[9px] font-bold rounded-t text-white whitespace-nowrap opacity-90 group-hover:opacity-100"
                          style={{ backgroundColor: colorStyle.border }}
                        >
                          {region.label}
                        </div>
                      </button>
                    );
                  })}
              </div>
            ) : (
              <div className="text-center py-20 text-muted-foreground">
                <FileText className="size-12 mx-auto mb-2 opacity-30" />
                <p>Không có dữ liệu trang</p>
              </div>
            )}
          </div>

          {/* Canvas Footer Info */}
          <div className="flex items-center justify-between px-3 py-1.5 bg-muted/40 border-t border-border text-[11px] text-muted-foreground">
            <div>
              Tài liệu: <strong className="text-foreground">{doc?.filename || "Chưa có"}</strong> (
              {doc?.size})
            </div>
            <div className="flex items-center gap-3">
              <span>
                Độ trễ: <strong className="text-foreground">{doc?.latencyMs || 0} ms</strong>
              </span>
              <span>
                Vùng bóc tách:{" "}
                <strong className="text-primary">
                  {currentPageData?.regions.length || 0} blocks
                </strong>
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: INSPECTOR & MARKDOWN / EXCEL TABS (5 COLS) */}
        <div className="lg:col-span-5 flex flex-col bg-card border border-border rounded-lg overflow-hidden shadow-xs">
          <Tabs
            value={rightTab}
            onValueChange={(val) => setRightTab(val as typeof rightTab)}
            className="flex flex-col h-full"
          >
            {/* Tab Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/40">
              <TabsList className="h-7 bg-muted">
                <TabsTrigger value="markdown" className="text-xs px-2.5 h-6 gap-1">
                  <FileText className="size-3" />
                  <span>Markdown</span>
                </TabsTrigger>
                {isSpreadsheet && (
                  <TabsTrigger
                    value="excel"
                    className="text-xs px-2.5 h-6 gap-1 text-emerald-600 dark:text-emerald-400"
                  >
                    <FileSpreadsheet className="size-3" />
                    <span>Bảng tính</span>
                  </TabsTrigger>
                )}
                <TabsTrigger value="regions" className="text-xs px-2.5 h-6 gap-1">
                  <Layers className="size-3" />
                  <span>Vùng ({currentPageData?.regions.length || 0})</span>
                </TabsTrigger>
                <TabsTrigger value="json" className="text-xs px-2.5 h-6 gap-1">
                  <FileCode className="size-3" />
                  <span>JSON</span>
                </TabsTrigger>
              </TabsList>

              {/* View mode toggle for Markdown tab */}
              {rightTab === "markdown" && (
                <div className="flex items-center rounded-md border border-border bg-background p-0.5">
                  <button
                    type="button"
                    onClick={() => setMarkdownViewMode("rendered")}
                    className={`px-2 py-0.5 text-[10px] font-medium rounded ${
                      markdownViewMode === "rendered"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    Xem đẹp
                  </button>
                  <button
                    type="button"
                    onClick={() => setMarkdownViewMode("raw")}
                    className={`px-2 py-0.5 text-[10px] font-medium rounded ${
                      markdownViewMode === "raw"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    Mã nguồn
                  </button>
                </div>
              )}
            </div>

            {/* TAB 1: MARKDOWN */}
            {rightTab === "markdown" && (
              <div className="flex-1 overflow-auto p-4 text-xs">
                {markdownViewMode === "rendered" ? (
                  <div className="prose prose-xs dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {currentPageData?.markdown || "(Trang không có nội dung)"}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <pre className="font-mono text-[11px] p-3 bg-muted/40 rounded-md border border-border whitespace-pre-wrap select-text leading-relaxed">
                    {currentPageData?.markdown}
                  </pre>
                )}
              </div>
            )}

            {/* TAB 2: EXCEL SPREADSHEET */}
            {rightTab === "excel" && (
              <div className="flex-1 overflow-hidden p-2">
                <ExcelSpreadsheetViewer
                  sheets={spreadsheetSheets}
                  filename={doc?.filename}
                  className="h-full"
                />
              </div>
            )}

            {/* TAB 3: REGIONS INSPECTOR */}
            {rightTab === "regions" && (
              <div className="flex-1 overflow-auto p-3 space-y-2">
                {currentPageData?.regions && currentPageData.regions.length > 0 ? (
                  currentPageData.regions.map((reg, idx) => {
                    const colorStyle = REGION_COLORS[reg.type] || REGION_COLORS.text;
                    const isSelected = selectedRegion === reg;
                    return (
                      <Card
                        key={`reg-card-${reg.type}-${idx}-${reg.top}`}
                        onClick={() => setSelectedRegion(reg)}
                        className={`cursor-pointer transition-all border ${
                          isSelected
                            ? "border-primary ring-1 ring-primary bg-primary/5"
                            : "hover:border-border/80"
                        }`}
                      >
                        <CardContent className="p-2.5 space-y-1">
                          <div className="flex items-center justify-between">
                            <Badge
                              variant="outline"
                              className="text-[10px] font-semibold uppercase px-1.5 py-0"
                              style={{ borderColor: colorStyle.border, color: colorStyle.text }}
                            >
                              {reg.type}
                            </Badge>
                            <span className="text-[10px] font-mono text-muted-foreground">
                              {reg.top.toFixed(1)}% T • {reg.left.toFixed(1)}% L •{" "}
                              {reg.width.toFixed(1)}% W
                            </span>
                          </div>
                          <p className="text-xs text-foreground/90 font-medium line-clamp-2">
                            {reg.text || `(Vùng ${reg.label})`}
                          </p>
                        </CardContent>
                      </Card>
                    );
                  })
                ) : (
                  <div className="text-center py-10 text-muted-foreground">
                    <p>Không phát hiện vùng bố cục nào trên trang này.</p>
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: JSON AST */}
            {rightTab === "json" && (
              <div className="flex-1 overflow-auto p-3">
                <pre className="font-mono text-[10px] p-3 bg-muted/40 rounded-md border border-border whitespace-pre-wrap select-text leading-tight text-foreground/80">
                  {JSON.stringify(currentPageData, null, 2)}
                </pre>
              </div>
            )}

            {/* Right Pane Footer */}
            <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-t border-border text-xs">
              <span className="text-muted-foreground">
                Số từ:{" "}
                <strong className="text-foreground">{currentPageData?.wordCount || 0}</strong> • Số
                dòng: <strong className="text-foreground">{currentPageData?.lineCount || 0}</strong>
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (currentPageData?.markdown) {
                    navigator.clipboard.writeText(currentPageData.markdown);
                    setIsCopied(true);
                    setTimeout(() => setIsCopied(false), 1500);
                  }
                }}
                className="h-6 text-[11px] gap-1 px-2"
              >
                {isCopied ? (
                  <Check className="size-3 text-emerald-500" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>{isCopied ? "Đã chép" : "Sao chép"}</span>
              </Button>
            </div>
          </Tabs>
        </div>
      </div>

      {/* 3. MODAL: CODE API SNIPPET */}
      <Dialog open={codeModalOpen} onOpenChange={setCodeModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Code className="size-5 text-primary" />
              <span>Tích Hợp API Studio OCR Cho Hệ Thống Khác</span>
            </DialogTitle>
            <DialogDescription>
              Các phòng ban và ứng dụng con tại ĐH Quy Nhơn có thể gọi trực tiếp API này để bóc tách
              tài liệu scan.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <p className="font-semibold text-foreground">Gọi bằng cURL (Terminal / Bash):</p>
            <pre className="p-3 bg-muted rounded-md border border-border font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
              {`curl -X POST "http://localhost:8001/api/v1/ocr/studio/parse" \\
  -F "file=@/duong/dan/tai_lieu_scan.pdf" \\
  -F "engine_id=docling"`}
            </pre>
            <p className="font-semibold text-foreground mt-3">
              Gọi bằng Python (httpx / requests):
            </p>
            <pre className="p-3 bg-muted rounded-md border border-border font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
              {`import httpx

url = "http://localhost:8001/api/v1/ocr/studio/parse"
with open("tai_lieu_scan.pdf", "rb") as f:
    files = {"file": ("tai_lieu_scan.pdf", f, "application/pdf")}
    data = {"engine_id": "docling"}
    resp = httpx.post(url, files=files, data=data, timeout=60.0)
    result = resp.json()
    print(f"Tổng số trang: {result['totalPages']}")`}
            </pre>
          </div>
          <DialogFooter>
            <Button size="sm" onClick={() => setCodeModalOpen(false)}>
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 4. MODAL: SAVE TO KNOWLEDGE BASE */}
      <Dialog open={saveModalOpen} onOpenChange={setSaveModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="size-5 text-primary" />
              <span>Lưu Vào Bộ Sưu Tập Tri Thức</span>
            </DialogTitle>
            <DialogDescription>
              Chọn Kho Tri Thức để nạp toàn bộ các trang và dữ liệu bảng biểu vào chỉ mục RAG.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1.5">
              <label htmlFor="target-collection-select" className="font-semibold text-foreground">
                Chọn Bộ Sưu Tập Mục Tiêu:
              </label>
              <Select value={targetCollectionId} onValueChange={setTargetCollectionId}>
                <SelectTrigger id="target-collection-select" className="w-full text-xs">
                  <SelectValue placeholder="Chọn bộ sưu tập" />
                </SelectTrigger>
                <SelectContent>
                  {collections.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name} ({c.document_count} tài liệu)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="p-3 bg-muted/40 rounded-md border border-border space-y-1">
              <div className="font-semibold text-foreground">Tệp chuẩn bị nạp:</div>
              <div className="text-muted-foreground">{doc?.filename}</div>
              <div className="text-[11px] text-primary">
                Sẽ tự động chunking và nạp vào Qdrant + PostgreSQL Facts.
              </div>
            </div>
            {saveSuccess && (
              <div className="flex items-center gap-2 p-2 bg-emerald-500/10 text-emerald-600 rounded border border-emerald-500/20 font-medium">
                <Check className="size-4" />
                <span>Nạp tài liệu vào Kho Tri Thức thành công!</span>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setSaveModalOpen(false)}>
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmSave}
              disabled={isSaving || !targetCollectionId || saveSuccess}
            >
              {isSaving ? <Loader2 className="size-3.5 animate-spin mr-1" /> : null}
              <span>{isSaving ? "Đang lưu..." : "Xác nhận nạp"}</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

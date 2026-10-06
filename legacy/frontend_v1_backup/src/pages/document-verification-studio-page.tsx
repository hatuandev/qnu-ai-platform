import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Code,
  Copy,
  Download,
  Edit3,
  Eye,
  FileCode,
  FileText,
  Maximize2,
  Save,
  Sparkles,
  X,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { DocumentBoundingVisualizer } from "../components/admin/document-bounding-visualizer";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { apiClient } from "../services/api-client";

export interface DocumentVerificationStudioPageProps {
  collectionId: string;
  documentId: string;
  onBackToConfig: () => void;
  onCommitSuccess: () => void;
}

export const DocumentVerificationStudioPage: React.FC<DocumentVerificationStudioPageProps> = ({
  collectionId: _collectionId,
  documentId,
  onBackToConfig,
  onCommitSuccess,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedFilter, setSelectedFilter] = useState<"all" | "table" | "text" | "stamp">("all");
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [activeBoxId, setActiveBoxId] = useState<string | null>(null);
  const [markdownScope, setMarkdownScope] = useState<"page" | "all">("all");
  const [showRawMarkdownSource, setShowRawMarkdownSource] = useState<boolean>(false);

  // In-place manual edit state
  const [isEditingMarkdown, setIsEditingMarkdown] = useState<boolean>(false);
  const [isPreviewEdit, setIsPreviewEdit] = useState<boolean>(false);
  const [editableMarkdown, setEditableMarkdown] = useState<string>("");
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [isCommitting, setIsCommitting] = useState<boolean>(false);
  const [isRescanning, setIsRescanning] = useState<boolean>(false);
  const [commitSuccessBanner, setCommitSuccessBanner] = useState<boolean>(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const handleRescanLayout = async () => {
    try {
      setIsRescanning(true);
      await apiClient.getDocumentVerification(documentId, true);
      await queryClient.invalidateQueries({ queryKey: ["document-verification", documentId] });
    } catch {
      // Graceful fallback per AGENTS.md 8.7
    } finally {
      setIsRescanning(false);
    }
  };

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
      ul: ({ children }: { children?: React.ReactNode }) => (
        <ul className="list-disc list-outside pl-5 my-2 space-y-1 text-foreground/90">
          {children}
        </ul>
      ),
      ol: ({ children }: { children?: React.ReactNode }) => (
        <ol className="list-decimal list-outside pl-5 my-2 space-y-1 text-foreground/90">
          {children}
        </ol>
      ),
      li: ({ children }: { children?: React.ReactNode }) => (
        <li className="text-xs leading-relaxed">{children}</li>
      ),
      hr: () => <hr className="my-3 border-border" />,
    }),
    []
  );

  // Fetch document verification data
  const { data: verificationData, isLoading } = useQuery({
    queryKey: ["document-verification", documentId],
    queryFn: () => apiClient.getDocumentVerification(documentId),
  });

  const currentPageData = useMemo(() => {
    if (!verificationData?.pages) return null;
    return (
      verificationData.pages.find((p) => p.page_number === currentPage) || verificationData.pages[0]
    );
  }, [verificationData, currentPage]);

  // Sync markdown content when page changes
  useEffect(() => {
    if (currentPageData) {
      setEditableMarkdown(currentPageData.markdown_content);
      setIsEditingMarkdown(false);
    }
  }, [currentPageData]);

  // Auto-scroll to active page section when viewing full document
  useEffect(() => {
    if (markdownScope === "all") {
      const el = document.getElementById(`page-section-${currentPage}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [currentPage, markdownScope]);

  const allBoundingBoxes = useMemo(() => {
    if (!verificationData?.pages) return [];
    return verificationData.pages.flatMap((p) => p.bounding_boxes);
  }, [verificationData]);

  const fullDocumentMarkdown = useMemo(() => {
    if (!verificationData?.pages || verificationData.pages.length === 0) return "";
    return verificationData.pages
      .map((p) => {
        const content = p.page_number === currentPage ? editableMarkdown : p.markdown_content;
        return `<!-- Trang ${p.page_number} / ${verificationData.total_pages} -->\n\n${(content || "").trim()}`;
      })
      .filter((s) => s.trim().length > 0)
      .join("\n\n---\n\n");
  }, [verificationData, currentPage, editableMarkdown]);

  const handleCopyContent = () => {
    const textToCopy = markdownScope === "all" ? fullDocumentMarkdown : editableMarkdown;
    navigator.clipboard.writeText(textToCopy);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleDownloadContent = () => {
    if (markdownScope === "all") {
      const blob = new Blob([fullDocumentMarkdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${verificationData?.filename || "document"}_Toan_Bo.md`;
      link.click();
      URL.revokeObjectURL(url);
    } else {
      const blob = new Blob([editableMarkdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${verificationData?.filename || "document"}_Trang_${currentPage}.md`;
      link.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleSaveManualEdit = () => {
    if (currentPageData) {
      currentPageData.markdown_content = editableMarkdown;
      currentPageData.raw_text = editableMarkdown;
      // Re-estimate words
      currentPageData.word_count = editableMarkdown.trim().split(/\s+/).length;
      currentPageData.line_count = editableMarkdown.split("\n").length;
    }
    setIsEditingMarkdown(false);
  };

  const handleCommitToVectorDb = async () => {
    setIsCommitting(true);
    setCommitError(null);
    try {
      // Sync the open page edit, then commit every page so manual fixes persist.
      const allPages = (verificationData?.pages || []).map((p) => ({
        page_number: p.page_number,
        markdown_content: p.page_number === currentPage ? editableMarkdown : p.markdown_content,
      }));
      await apiClient.saveDocumentVerification(documentId, { pages: allPages });
      setCommitSuccessBanner(true);
      setTimeout(() => {
        onCommitSuccess();
      }, 1500);
    } catch (err) {
      setCommitError(
        err instanceof Error ? err.message : "Nạp Vector DB thất bại. Vui lòng thử lại."
      );
    } finally {
      setIsCommitting(false);
    }
  };

  if (isLoading || !verificationData) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center space-y-3">
          <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-medium text-foreground">
            Đang tải Studio bóc tách & đối soát toàn màn hình...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background overflow-hidden select-none">
      {/* Topbar: Desktop-grade controls */}
      <div className="flex items-center justify-between px-4 py-2 bg-card border-b border-border shadow-xs z-30">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBackToConfig}
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            <span>Cấu hình lại</span>
          </Button>

          <div className="h-4 w-px bg-border" />

          <div className="flex items-center gap-2">
            <FileText className="size-4 text-primary shrink-0" />
            <span className="text-xs sm:text-sm font-bold text-foreground truncate max-w-[280px] sm:max-w-md">
              {verificationData.title}
            </span>
            <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
              {verificationData.total_pages} Trang
            </Badge>
            <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
              {verificationData.file_size_mb} MB
            </Badge>
            <Badge
              variant="secondary"
              className="text-[10px] font-mono text-primary bg-primary/10 border-primary/20"
            >
              {verificationData.engine}
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground font-mono mr-2">
            <Sparkles className="size-3.5 text-amber-500" />
            <span>
              {verificationData.total_chars.toLocaleString("vi-VN")} ký tự • ~
              {verificationData.estimated_chunks} Chunks
            </span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={onBackToConfig}
            className="h-8 text-xs text-muted-foreground"
          >
            Hủy bỏ
          </Button>

          <Button
            size="sm"
            disabled={isCommitting || commitSuccessBanner}
            onClick={handleCommitToVectorDb}
            className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
          >
            {commitSuccessBanner ? (
              <>
                <CheckCircle2 className="size-3.5 text-white" />
                <span>Đã nạp Vector DB thành công!</span>
              </>
            ) : isCommitting ? (
              <>
                <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Đang tính vector...</span>
              </>
            ) : (
              <>
                <Check className="size-3.5" />
                <span>Xác nhận & Nạp vào Vector DB</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Commit Error Banner */}
      {commitError && (
        <div className="px-4 py-2 bg-destructive/10 border-b border-destructive/30 text-xs text-destructive">
          {commitError}
        </div>
      )}

      {/* Main Split-Pane Workspace: 50% Left / 50% Right */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 overflow-hidden">
        {/* LEFT PANE: Document Bounding Box Visualizer */}
        <div className="h-full overflow-hidden">
          <DocumentBoundingVisualizer
            currentPage={currentPage}
            totalPages={verificationData.total_pages}
            onPageChange={setCurrentPage}
            boundingBoxes={allBoundingBoxes}
            selectedFilter={selectedFilter}
            onFilterChange={setSelectedFilter}
            showBoxes={showBoxes}
            onToggleShowBoxes={setShowBoxes}
            activeBoxId={activeBoxId}
            onSelectBox={setActiveBoxId}
            imageUrl={currentPageData?.image_url}
            isRescanning={isRescanning}
            onRescanLayout={handleRescanLayout}
          />
        </div>

        {/* RIGHT PANE: Extracted Clean Markdown Workspace */}
        <div className="h-full flex flex-col bg-background border-l border-border overflow-hidden">
          {/* Right Toolbar */}
          <div className="flex items-center justify-between px-3 py-2 bg-card border-b border-border/70">
            {/* Scope Switcher: Trang hiện tại (page) vs Toàn bộ file (all) */}
            <Tabs
              value={markdownScope}
              onValueChange={(val) => setMarkdownScope(val as "page" | "all")}
              className="w-auto"
            >
              <TabsList className="h-7 bg-muted/60 p-0.5 rounded-sm">
                <TabsTrigger value="all" className="text-[11px] h-6 px-2.5 gap-1.5 font-medium">
                  <FileCode className="size-3 text-primary" />
                  <span>Toàn bộ file ({verificationData.total_pages} trang)</span>
                </TabsTrigger>
                <TabsTrigger value="page" className="text-[11px] h-6 px-2.5 gap-1.5 font-medium">
                  <FileText className="size-3 text-muted-foreground" />
                  <span>Trang {currentPage}</span>
                </TabsTrigger>
              </TabsList>
            </Tabs>

            {/* Action Tools: Sửa tay (theo trang), Toggle Mã nguồn .md / Xem render, Copy, Download */}
            <div className="flex items-center gap-1">
              {/* Button Sửa tay */}
              {isEditingMarkdown ? (
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsPreviewEdit((prev) => !prev)}
                    className="h-6 px-2 text-[11px] gap-1 border-primary/40 text-primary hover:bg-primary/10"
                  >
                    <Eye className="size-3" />
                    <span>{isPreviewEdit ? "Sửa tiếp" : "Xem trước"}</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={handleSaveManualEdit}
                    className="h-6 px-2 text-[11px] gap-1 bg-primary text-primary-foreground"
                  >
                    <Save className="size-3" />
                    <span>Lưu sửa</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setIsEditingMarkdown(false);
                      setIsPreviewEdit(false);
                    }}
                    className="h-6 px-1.5 text-[11px]"
                    title="Hủy sửa"
                  >
                    <X className="size-3" />
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setMarkdownScope("page");
                    setIsEditingMarkdown(true);
                    setIsPreviewEdit(false);
                  }}
                  className="h-6 px-2 text-[11px] gap-1 border-primary/40 text-primary hover:bg-primary/10"
                  title={`Sửa tay Markdown của Trang ${currentPage}`}
                >
                  <Edit3 className="size-3" />
                  <span>Sửa Trang {currentPage}</span>
                </Button>
              )}

              {/* Button Toggle: Mã nguồn .md vs Xem render (khi không sửa tay) */}
              {!isEditingMarkdown && (
                <Button
                  size="sm"
                  variant={showRawMarkdownSource ? "secondary" : "ghost"}
                  onClick={() => setShowRawMarkdownSource((prev) => !prev)}
                  className="h-6 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground"
                  title="Chuyển đổi giữa xem render và mã nguồn Markdown"
                >
                  {showRawMarkdownSource ? <Eye className="size-3" /> : <Code className="size-3" />}
                  <span>{showRawMarkdownSource ? "Xem render" : "Mã nguồn .md"}</span>
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                onClick={handleCopyContent}
                className="size-6 h-6 w-6 p-0"
                title={
                  markdownScope === "all"
                    ? `Sao chép toàn bộ Markdown (${verificationData.total_pages} trang)`
                    : `Sao chép Markdown Trang ${currentPage}`
                }
              >
                {isCopied ? (
                  <Check className="size-3.5 text-emerald-600" />
                ) : (
                  <Copy className="size-3.5 text-muted-foreground" />
                )}
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={handleDownloadContent}
                className="size-6 h-6 w-6 p-0"
                title={
                  markdownScope === "all"
                    ? "Tải tệp Markdown toàn bộ tài liệu (.md)"
                    : `Tải Markdown Trang ${currentPage} (.md)`
                }
              >
                <Download className="size-3.5 text-muted-foreground" />
              </Button>

              <Button variant="ghost" size="icon" className="size-6 h-6 w-6 p-0" title="Mở rộng">
                <Maximize2 className="size-3.5 text-muted-foreground" />
              </Button>
            </div>
          </div>

          {/* Right Content Body */}
          <div className="flex-1 overflow-auto p-4 select-text">
            {/* VIEW 1: TRANG HIỆN TẠI (Scope: page) */}
            {markdownScope === "page" &&
              (isEditingMarkdown ? (
                <div className="h-full flex flex-col space-y-2">
                  <div className="p-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 rounded text-amber-800 dark:text-amber-300 text-[11px] flex items-center justify-between">
                    <span>
                      ✏️ <strong>Chế độ Sửa tay (Trang {currentPage})</strong>: Bạn có thể sửa trực
                      tiếp nội dung Markdown của trang này trước khi nạp vào Vector DB.
                    </span>
                    <span className="text-[10px] opacity-75">
                      {isPreviewEdit ? "Đang xem kết quả render" : "Đang sửa text Markdown thô"}
                    </span>
                  </div>
                  {isPreviewEdit ? (
                    <div className="flex-1 overflow-auto p-3 border border-border rounded-md bg-muted/10">
                      <div className="prose prose-sm dark:prose-invert max-w-none text-xs leading-relaxed font-sans">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {editableMarkdown}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <textarea
                      value={editableMarkdown}
                      onChange={(e) => setEditableMarkdown(e.target.value)}
                      className="flex-1 w-full p-3 font-mono text-xs leading-relaxed bg-muted/20 border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                    />
                  )}
                </div>
              ) : showRawMarkdownSource ? (
                <div className="space-y-3 font-mono text-xs leading-relaxed select-text">
                  <div className="text-[11px] text-muted-foreground pb-2 border-b border-border flex items-center justify-between">
                    <span>
                      &lt;!-- Mã nguồn Markdown Trang {currentPage} / {verificationData.total_pages}{" "}
                      --&gt;
                    </span>
                    <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded">
                      Raw Markdown Source
                    </span>
                  </div>
                  <pre className="font-mono text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed bg-muted/20 p-3 rounded-md border border-border">
                    {editableMarkdown}
                  </pre>
                </div>
              ) : (
                <div className="space-y-3 font-sans text-xs leading-relaxed select-text">
                  <div className="font-mono text-[11px] text-muted-foreground pb-2 border-b border-border flex items-center justify-between">
                    <span>
                      &lt;!-- Trang {currentPage} / {verificationData.total_pages} --&gt;
                    </span>
                    <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded font-mono">
                      Markdown Trang {currentPage}
                    </span>
                  </div>
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {editableMarkdown}
                    </ReactMarkdown>
                  </div>
                </div>
              ))}

            {/* VIEW 2: TOÀN BỘ TÀI LIỆU (Scope: all) */}
            {markdownScope === "all" && (
              <div className="space-y-4 font-sans text-xs leading-relaxed select-text">
                <div className="font-mono text-[11px] text-muted-foreground pb-2 border-b border-border flex items-center justify-between">
                  <span>
                    &lt;!-- Toàn bộ tài liệu ({verificationData.total_pages} trang) --&gt;
                  </span>
                  <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded font-mono">
                    {showRawMarkdownSource
                      ? "Mã nguồn Markdown Toàn Bộ File"
                      : "GFM Markdown Render • Toàn bộ file"}
                  </span>
                </div>

                {showRawMarkdownSource ? (
                  <pre className="font-mono text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed bg-muted/20 p-3 rounded-md border border-border">
                    {fullDocumentMarkdown}
                  </pre>
                ) : (
                  <div className="space-y-6">
                    {verificationData.pages.map((p) => {
                      const pageContent =
                        p.page_number === currentPage ? editableMarkdown : p.markdown_content;
                      const isCurrentPage = p.page_number === currentPage;
                      return (
                        <div
                          key={p.page_number}
                          id={`page-section-${p.page_number}`}
                          className={`space-y-2 pb-5 border-b border-border/60 last:border-b-0 rounded-md transition-all ${
                            isCurrentPage
                              ? "bg-primary/[0.03] p-3 border border-primary/20 ring-1 ring-primary/20"
                              : ""
                          }`}
                        >
                          <div className="font-mono text-[10px] text-muted-foreground/80 py-1 px-2.5 bg-muted/40 rounded flex items-center justify-between">
                            <span className="font-semibold text-foreground/70 flex items-center gap-1.5">
                              Trang {p.page_number} / {verificationData.total_pages}
                              {isCurrentPage && (
                                <span className="text-[9px] bg-primary text-primary-foreground px-1.5 py-0.5 rounded font-sans font-normal">
                                  Đang xem ở trang gốc
                                </span>
                              )}
                            </span>
                            <span>
                              {p.word_count ||
                                (pageContent.trim()
                                  ? pageContent.trim().split(/\s+/).length
                                  : 0)}{" "}
                              từ
                            </span>
                          </div>
                          <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={markdownComponents}
                            >
                              {pageContent}
                            </ReactMarkdown>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Footer Stats */}
          <div className="flex items-center justify-between px-4 py-2 bg-card border-t border-border text-xs text-muted-foreground font-mono">
            <span className="text-[11px]">
              {markdownScope === "all"
                ? `${verificationData.total_chars.toLocaleString("vi-VN")} ký tự • ${verificationData.total_pages} trang`
                : `${currentPageData?.word_count || 0} từ • ${currentPageData?.line_count || 0} dòng`}
            </span>
            <span className="text-[11px] font-medium text-foreground">
              {markdownScope === "all"
                ? `Toàn bộ ${verificationData.total_pages} trang`
                : `Trang ${currentPage}/${verificationData.total_pages}`}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

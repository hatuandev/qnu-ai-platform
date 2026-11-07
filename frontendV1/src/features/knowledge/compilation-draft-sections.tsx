import {
  BookOpen,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Columns2,
  Copy,
  FolderOpen,
  HelpCircle,
  ListTree,
  Search,
  Sparkles,
  Table2,
  Tag,
  X,
} from "lucide-react";
import { memo, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { DraftReadingGroup, DraftSection } from "./compilation-types";

function parseHeading(heading: string): { code?: string; title: string } {
  const match = heading.match(/^([A-Z0-9_\-\.]+)(?:\s*[:\-–—]?\s+)(.+)$/i);
  if (
    match &&
    match[1] &&
    match[2] &&
    match[1].length <= 25 &&
    !match[1].includes(" ")
  ) {
    return { code: match[1], title: match[2] };
  }
  return { title: heading };
}

function normalizeLabel(text: string): string {
  return text
    .replace(/[*_#:`]/g, "")
    .trim()
    .toUpperCase();
}

function isEmbeddingLabel(norm: string): boolean {
  return (
    norm === "NỘI DUNG DÙNG ĐỂ EMBEDDING" ||
    norm === "NỘI DUNG EMBEDDING" ||
    norm.startsWith("NỘI DUNG DÙNG ĐỂ EMBEDDING") ||
    norm.startsWith("EMBEDDING")
  );
}

function isAnswerLabel(norm: string): boolean {
  return (
    norm === "CÂU TRẢ LỜI GỐC" ||
    norm === "CÂU TRẢ LỜI" ||
    norm.startsWith("CÂU TRẢ LỜI GỐC") ||
    norm.startsWith("CÂU TRẢ LỜI")
  );
}

function isChapterHeader(
  heading: string,
  parsedHead: { code?: string; title: string },
): boolean {
  const trimmed = heading.trim();
  // 1. Phân loại theo tiền tố trang / chương / phần
  if (
    /^(?:trang|page)\s+/i.test(trimmed) ||
    parsedHead.code?.toLowerCase() === "trang"
  ) {
    return true;
  }
  if (/^(?:chương|phần|chủ đề)\s+/i.test(trimmed)) {
    return true;
  }
  // 2. Phân loại theo mã số chương lớn (VD: "01 THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026")
  if (
    parsedHead.code &&
    /^\d{1,3}$/.test(parsedHead.code) &&
    !trimmed.includes("?") &&
    parsedHead.title === parsedHead.title.toUpperCase() &&
    parsedHead.title.length > 3
  ) {
    return true;
  }

  return false;
}

interface ParsedQnAParts {
  isSectionHeader: boolean;
  directAnswer?: { text: string; citations: string[] };
  embeddingContext?: { text: string; citations: string[] };
  otherParagraphs: { text: string; citations: string[] }[];
}

function parseQnAParagraphs(
  heading: string,
  paragraphs: { text: string; citations: string[] }[],
): ParsedQnAParts {
  const parsedHead = parseHeading(heading);
  const isSectionHeader = isChapterHeader(heading, parsedHead);

  let directAnswer: { text: string; citations: string[] } | undefined;
  let embeddingContext: { text: string; citations: string[] } | undefined;
  const otherParagraphs: { text: string; citations: string[] }[] = [];

  const hasLabels = paragraphs.some((p) => {
    const n = normalizeLabel(p.text);
    return isAnswerLabel(n) || isEmbeddingLabel(n);
  });

  if (hasLabels) {
    let mode: "none" | "embedding" | "answer" = "none";
    for (const p of paragraphs) {
      const trimmed = p.text.trim();
      const norm = normalizeLabel(trimmed);

      // Bỏ qua nếu đoạn văn lặp lại đúng tiêu đề câu hỏi
      const isHeadingDuplicate =
        trimmed.toLowerCase() === heading.trim().toLowerCase() ||
        trimmed.toLowerCase() === parsedHead.title.trim().toLowerCase() ||
        (parsedHead.code &&
          trimmed.toLowerCase() ===
            `${parsedHead.code} ${parsedHead.title}`.trim().toLowerCase());

      if (isHeadingDuplicate) {
        continue;
      }

      if (isEmbeddingLabel(norm)) {
        mode = "embedding";
        const colonIdx = trimmed.indexOf(":");
        if (colonIdx !== -1 && colonIdx < trimmed.length - 1) {
          const inlineText = trimmed.slice(colonIdx + 1).trim();
          if (inlineText.length > 0) {
            embeddingContext = {
              text: inlineText,
              citations: [...p.citations],
            };
          }
        }
        continue;
      }

      if (isAnswerLabel(norm)) {
        mode = "answer";
        const colonIdx = trimmed.indexOf(":");
        if (colonIdx !== -1 && colonIdx < trimmed.length - 1) {
          const inlineText = trimmed.slice(colonIdx + 1).trim();
          if (inlineText.length > 0) {
            directAnswer = {
              text: inlineText,
              citations: [...p.citations],
            };
          }
        }
        continue;
      }

      if (mode === "answer") {
        if (!directAnswer) {
          directAnswer = { ...p };
        } else {
          directAnswer.text += `\n${p.text}`;
          directAnswer.citations = Array.from(
            new Set([...directAnswer.citations, ...p.citations]),
          );
        }
      } else if (mode === "embedding") {
        if (!embeddingContext) {
          embeddingContext = { ...p };
        } else {
          embeddingContext.text += `\n${p.text}`;
          embeddingContext.citations = Array.from(
            new Set([...embeddingContext.citations, ...p.citations]),
          );
        }
      } else {
        otherParagraphs.push(p);
      }
    }
  } else {
    const nonHeading = paragraphs.filter(
      (p) => p.text.trim().toLowerCase() !== heading.trim().toLowerCase(),
    );
    if (nonHeading.length === 1) {
      directAnswer = nonHeading[0];
    } else if (nonHeading.length > 1) {
      directAnswer = nonHeading[nonHeading.length - 1];
      otherParagraphs.push(...nonHeading.slice(0, nonHeading.length - 1));
    } else if (paragraphs.length > 0) {
      directAnswer = paragraphs[0];
    }
  }

  return {
    isSectionHeader,
    directAnswer,
    embeddingContext,
    otherParagraphs,
  };
}

export interface CompilationDraftSectionsProps {
  sections: DraftSection[];
  readingGroups?: DraftReadingGroup[];
  onSelectCitation: (id: string) => void;
  defaultViewMode?: "studio" | "table" | "document";
}

export const CompilationDraftSections = memo(function CompilationDraftSections({
  sections,
  readingGroups,
  onSelectCitation,
  defaultViewMode = "studio",
}: CompilationDraftSectionsProps) {
  const groups = useMemo(() => {
    return (
      readingGroups?.map((group) => ({
        heading: group.heading,
        paragraphs: group.paragraphs.flatMap(([section, paragraph]) => {
          const entry = sections[section]?.paragraphs[paragraph];
          return entry ? [entry] : [];
        }),
      })) ?? sections
    );
  }, [readingGroups, sections]);

  const [viewMode, setViewMode] = useState<"studio" | "table" | "document">(
    defaultViewMode,
  );
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<
    "all" | "has_citations" | "no_citations"
  >("all");
  const [tablePage, setTablePage] = useState(1);
  const [hasCopied, setHasCopied] = useState(false);
  const TABLE_PAGE_SIZE = 15;

  const q = searchQuery.trim().toLowerCase();

  // Tiền xử lý cấu trúc phân loại chương và ngữ cảnh câu hỏi
  const enrichedGroups = useMemo(() => {
    let currentChapter = "";
    return groups.map((group, originalIndex) => {
      const parsed = parseHeading(group.heading);
      const qnaParts = parseQnAParagraphs(group.heading, group.paragraphs);
      const totalCitations = group.paragraphs.reduce(
        (sum, p) => sum + (p.citations?.length ?? 0),
        0,
      );

      if (qnaParts.isSectionHeader) {
        if (
          parsed.code?.toLowerCase() === "trang" ||
          group.heading.toLowerCase().startsWith("trang")
        ) {
          currentChapter = group.heading;
        } else {
          currentChapter = parsed.code
            ? `Chủ đề ${parsed.code}: ${parsed.title}`
            : group.heading;
        }
      }

      return {
        group,
        originalIndex,
        parsed,
        qnaParts,
        totalCitations,
        chapterTitle: qnaParts.isSectionHeader ? undefined : currentChapter,
      };
    });
  }, [groups]);

  const filteredItems = useMemo(() => {
    return enrichedGroups.filter(({ group, totalCitations, parsed }) => {
      if (filterStatus === "has_citations" && totalCitations === 0) {
        return false;
      }
      if (filterStatus === "no_citations" && totalCitations > 0) {
        return false;
      }

      if (!q) return true;
      if (group.heading.toLowerCase().includes(q)) return true;
      if (parsed.title.toLowerCase().includes(q)) return true;
      if (parsed.code?.toLowerCase().includes(q)) return true;
      return group.paragraphs.some((p) => p.text.toLowerCase().includes(q));
    });
  }, [enrichedGroups, q, filterStatus]);

  const safeSelectedIndex = Math.min(
    Math.max(0, selectedIndex),
    Math.max(0, filteredItems.length - 1),
  );
  const activeItem = filteredItems[safeSelectedIndex] ?? null;

  // Tính tổng số câu hỏi thực tế (loại bỏ tiêu đề chương / bìa)
  const totalQuestions = useMemo(() => {
    return filteredItems.filter((item) => !item.qnaParts.isSectionHeader)
      .length;
  }, [filteredItems]);

  const activeQuestionNumber = useMemo(() => {
    if (!activeItem || activeItem.qnaParts.isSectionHeader) return undefined;
    return filteredItems
      .slice(0, safeSelectedIndex + 1)
      .filter((item) => !item.qnaParts.isSectionHeader).length;
  }, [activeItem, filteredItems, safeSelectedIndex]);

  // Hỗ trợ phím tắt điều hướng mũi tên Lên / Xuống (hoặc J / K) trong chế độ Studio
  useEffect(() => {
    if (viewMode !== "studio") return;
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredItems.length - 1));
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [viewMode, filteredItems.length]);

  // Tự động cuộn thẻ được chọn trong Master panel vào tầm mắt
  useEffect(() => {
    if (viewMode === "studio" && activeItem) {
      const el = document.getElementById(
        `master-item-${activeItem.originalIndex}`,
      );
      if (typeof el?.scrollIntoView === "function") {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [activeItem, viewMode]);

  // Phân trang cho Table view
  const totalPages = Math.max(
    1,
    Math.ceil(filteredItems.length / TABLE_PAGE_SIZE),
  );
  const startIdx = (tablePage - 1) * TABLE_PAGE_SIZE;
  const pagedItems = filteredItems.slice(startIdx, startIdx + TABLE_PAGE_SIZE);

  // Sao chép nội dung câu hỏi & câu trả lời
  const handleCopyQnA = () => {
    if (!activeItem) return;
    const qTitle = activeItem.parsed.title;
    const ansText = activeItem.qnaParts.directAnswer?.text || "";
    const textToCopy = `Câu hỏi: ${qTitle}\n\nTrả lời:\n${ansText}`;
    if (typeof navigator?.clipboard?.writeText === "function") {
      navigator.clipboard.writeText(textToCopy);
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-3">
      {/* THANH ĐIỀU KHIỂN CHÍNH (STUDIO TOOLBAR) */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2.5 p-2.5 sm:p-3 rounded-xl border border-border/70 bg-card shadow-2xs">
        {/* Nhóm trái: Ô tìm kiếm + Chip lọc trạng thái */}
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-0">
          <div className="relative min-w-[220px] max-w-sm flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Tìm câu hỏi, mã số (VD: 001, học phí)…"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setTablePage(1);
                setSelectedIndex(0);
              }}
              className="h-8 pl-8 pr-7 text-xs bg-background"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setTablePage(1);
                  setSelectedIndex(0);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                aria-label="Xóa từ khóa tìm kiếm"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          {/* Bộ lọc theo dẫn chứng */}
          <div className="flex items-center gap-1 text-xs shrink-0">
            <Button
              type="button"
              variant={filterStatus === "all" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => {
                setFilterStatus("all");
                setTablePage(1);
                setSelectedIndex(0);
              }}
              className={cn(
                "h-7 text-xs px-2.5 rounded-lg",
                filterStatus === "all" && "font-semibold shadow-2xs",
              )}
            >
              Tất cả ({groups.length})
            </Button>
            <Button
              type="button"
              variant={filterStatus === "has_citations" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => {
                setFilterStatus("has_citations");
                setTablePage(1);
                setSelectedIndex(0);
              }}
              className={cn(
                "h-7 text-xs px-2.5 rounded-lg gap-1",
                filterStatus === "has_citations" &&
                  "font-semibold shadow-2xs text-primary",
              )}
            >
              <Tag className="size-3 text-primary" />
              <span>Có dẫn chứng</span>
            </Button>
          </div>
        </div>

        {/* Nhóm phải: Chuyển đổi chế độ xem Segmented Switcher */}
        <div className="flex items-center p-0.5 rounded-lg border border-border/80 bg-muted/30 shrink-0">
          <Button
            type="button"
            variant={viewMode === "studio" ? "secondary" : "ghost"}
            size="sm"
            className={cn(
              "h-7 text-xs px-2.5 gap-1.5 rounded-md transition-colors",
              viewMode === "studio" &&
                "bg-background font-semibold shadow-2xs text-foreground",
            )}
            onClick={() => setViewMode("studio")}
            title="Chế độ Studio chia 2 cột kiểu Dify / Coze"
          >
            <Columns2 className="size-3.5 text-primary" />
            <span className="hidden sm:inline">Studio 2 Cột</span>
          </Button>

          <Button
            type="button"
            variant={viewMode === "table" ? "secondary" : "ghost"}
            size="sm"
            className={cn(
              "h-7 text-xs px-2.5 gap-1.5 rounded-md transition-colors",
              viewMode === "table" &&
                "bg-background font-semibold shadow-2xs text-foreground",
            )}
            onClick={() => setViewMode("table")}
            title="Chế độ bảng dữ liệu phân trang kiểu FastGPT"
          >
            <Table2 className="size-3.5 text-primary" />
            <span className="hidden sm:inline">Bảng Tri Thức</span>
          </Button>

          <Button
            type="button"
            variant={viewMode === "document" ? "secondary" : "ghost"}
            size="sm"
            className={cn(
              "h-7 text-xs px-2.5 gap-1.5 rounded-md transition-colors",
              viewMode === "document" &&
                "bg-background font-semibold shadow-2xs text-foreground",
            )}
            onClick={() => setViewMode("document")}
            title="Chế độ đọc văn bản toàn trang liên tục"
          >
            <BookOpen className="size-3.5 text-primary" />
            <span className="hidden sm:inline">Toàn Văn</span>
          </Button>
        </div>
      </div>

      {/* Thông tin tìm kiếm nếu có */}
      {searchQuery && (
        <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
          <span>
            Tìm thấy{" "}
            <strong className="text-foreground">
              {filteredItems.length}
            </strong>{" "}
            / {groups.length} mục phù hợp
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearchQuery("");
              setTablePage(1);
              setSelectedIndex(0);
            }}
            className="h-6 px-1.5 text-xs text-primary hover:text-primary"
          >
            Xóa tìm kiếm
          </Button>
        </div>
      )}

      {/* KẾT QUẢ RỖNG KHI TÌM KIẾM */}
      {filteredItems.length === 0 ? (
        <div className="py-12 text-center text-xs text-muted-foreground space-y-2 border border-dashed rounded-xl bg-muted/10">
          <Search className="size-6 text-muted-foreground/40 mx-auto" />
          <p className="font-semibold text-foreground text-sm">
            Không tìm thấy mục nào khớp với &quot;{searchQuery}&quot;
          </p>
          <p>Hãy thử tìm bằng từ khóa khác hoặc kiểm tra lại bộ lọc.</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setSearchQuery("");
              setFilterStatus("all");
            }}
            className="h-7 text-xs mt-1"
          >
            Xóa bộ lọc tìm kiếm
          </Button>
        </div>
      ) : viewMode === "studio" ? (
        /* ========================================================================= */
        /* CHẾ ĐỘ 1: MASTER - DETAIL STUDIO (CHUẨN DIFY / COZE)                      */
        /* ========================================================================= */
        <div className="flex flex-col lg:flex-row items-stretch gap-0 rounded-xl border border-border/80 bg-card overflow-hidden shadow-2xs h-[calc(100vh-230px)] min-h-[580px]">
          {/* CỘT TRÁI: MASTER LIST (Danh mục câu hỏi cuộn độc lập) */}
          <div className="w-full lg:w-[360px] xl:w-[390px] shrink-0 border-b lg:border-b-0 lg:border-r border-border/70 flex flex-col bg-muted/10 h-[260px] lg:h-full">
            {/* Tiêu đề cột trái */}
            <div className="p-3 border-b border-border/60 bg-muted/20 flex items-center justify-between text-xs text-muted-foreground shrink-0">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <ListTree className="size-3.5 text-primary" />
                <span>Danh mục câu hỏi</span>
              </span>
              <span className="text-[11px] font-mono font-medium">
                {activeQuestionNumber
                  ? `Câu ${activeQuestionNumber} / ${totalQuestions}`
                  : `${safeSelectedIndex + 1} / ${filteredItems.length}`}
              </span>
            </div>

            {/* Danh sách thẻ cuộn độc lập */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {filteredItems.map(
                (
                  {
                    group,
                    originalIndex,
                    parsed,
                    qnaParts,
                    totalCitations,
                  },
                  idx,
                ) => {
                  const isSelected = activeItem?.originalIndex === originalIndex;

                  // Phân loại phân đoạn chương / tiêu đề nhóm
                  if (qnaParts.isSectionHeader) {
                    return (
                      <div
                        key={`master-sec-${originalIndex}`}
                        id={`master-item-${originalIndex}`}
                        onClick={() => setSelectedIndex(idx)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setSelectedIndex(idx);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                        aria-label={
                          parsed.code
                            ? `${parsed.code} ${parsed.title}`
                            : group.heading
                        }
                        className={cn(
                          "w-full text-left px-3 py-2 rounded-lg transition-colors text-xs flex items-center justify-between gap-2 cursor-pointer font-bold border my-1.5 select-none",
                          isSelected
                            ? "bg-primary text-primary-foreground border-primary shadow-2xs"
                            : "bg-muted/70 hover:bg-muted text-foreground border-border/60 hover:border-primary/40",
                        )}
                      >
                        <span className="flex items-center gap-2 min-w-0">
                          <FolderOpen
                            className={cn(
                              "size-3.5 shrink-0",
                              isSelected
                                ? "text-primary-foreground"
                                : "text-primary",
                            )}
                          />
                          <span className="truncate uppercase tracking-wide text-[11px]">
                            {parsed.code &&
                            parsed.code.toLowerCase() !== "trang"
                              ? `Chủ đề ${parsed.code}: ${parsed.title}`
                              : group.heading}
                          </span>
                        </span>
                        {totalCitations > 0 && (
                          <span
                            className={cn(
                              "text-[10px] font-mono px-1.5 py-0.2 rounded border shrink-0 font-normal",
                              isSelected
                                ? "bg-primary-foreground/20 text-primary-foreground border-primary-foreground/30"
                                : "bg-background text-muted-foreground border-border/40",
                            )}
                          >
                            {totalCitations} nguồn
                          </span>
                        )}
                      </div>
                    );
                  }

                  return (
                    <button
                      key={`master-${originalIndex}`}
                      id={`master-item-${originalIndex}`}
                      type="button"
                      onClick={() => setSelectedIndex(idx)}
                      aria-label={
                        parsed.code
                          ? `${parsed.code} ${parsed.title}`
                          : group.heading
                      }
                      aria-current={isSelected ? "true" : undefined}
                      className={cn(
                        "w-full text-left p-3 rounded-xl transition-all text-xs flex flex-col gap-1.5 cursor-pointer border group relative",
                        isSelected
                          ? "bg-primary/5 border-primary/50 shadow-2xs text-foreground ring-1 ring-primary/30 border-l-4 border-l-primary"
                          : "bg-background/80 hover:bg-muted/50 border-border/60 hover:border-border text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {/* Hàng 1: Mã hiệu + Nguồn dẫn chứng */}
                      <div className="flex items-center justify-between gap-2">
                        {parsed.code ? (
                          <span
                            className={cn(
                              "font-mono text-[10px] font-bold px-1.5 py-0.5 rounded border tracking-tight",
                              isSelected
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-muted text-foreground border-border/60 group-hover:bg-muted/80",
                            )}
                          >
                            {parsed.code}
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-muted-foreground font-semibold">
                            #{originalIndex + 1}
                          </span>
                        )}

                        {totalCitations > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded border border-primary/20 shrink-0 font-medium">
                            <Tag className="size-2.5 text-primary" />
                            <span>{totalCitations} nguồn</span>
                          </span>
                        )}
                      </div>

                      {/* Hàng 2: Câu hỏi */}
                      <p
                        className={cn(
                          "line-clamp-2 text-xs leading-snug",
                          isSelected
                            ? "font-bold text-foreground"
                            : "font-medium text-foreground/90 group-hover:text-foreground",
                        )}
                      >
                        {parsed.code ? parsed.title : group.heading}
                      </p>
                    </button>
                  );
                },
              )}
            </div>
          </div>

          {/* CỘT PHẢI: DETAIL WORKSPACE (Chi tiết câu hỏi & Đối chiếu dẫn chứng) */}
          <div className="flex-1 flex flex-col min-w-0 bg-background overflow-hidden h-full">
            {activeItem ? (
              <>
                {/* Header thanh điều hướng chi tiết */}
                <div className="p-3 sm:p-3.5 border-b border-border/60 bg-muted/15 flex items-center justify-between gap-3 shrink-0">
                  <div className="flex items-center gap-2 min-w-0">
                    {activeItem.parsed.code ? (
                      <Badge
                        variant="outline"
                        className="font-mono text-xs font-bold text-primary bg-primary/5 border-primary/30 px-2 py-0.5 shrink-0"
                      >
                        {activeItem.parsed.code}
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="font-mono text-xs shrink-0"
                      >
                        Mục #{activeItem.originalIndex + 1}
                      </Badge>
                    )}

                    {/* Huy hiệu Chủ đề liên quan */}
                    {activeItem.chapterTitle && (
                      <span
                        className="hidden md:inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-md border border-border/50 truncate max-w-[220px]"
                        title={activeItem.chapterTitle}
                      >
                        <FolderOpen className="size-3 text-primary shrink-0" />
                        <span className="truncate">
                          {activeItem.chapterTitle}
                        </span>
                      </span>
                    )}

                    <span className="text-xs text-muted-foreground font-mono hidden xl:inline">
                      {activeQuestionNumber
                        ? `(Câu hỏi ${activeQuestionNumber}/${totalQuestions})`
                        : `(Mục ${safeSelectedIndex + 1}/${filteredItems.length})`}
                    </span>
                  </div>

                  {/* Nhóm thao tác: Sao chép & Điều hướng trước / sau */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    {!activeItem.qnaParts.isSectionHeader && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={handleCopyQnA}
                        className="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
                        title="Sao chép câu hỏi và câu trả lời vào clipboard"
                      >
                        {hasCopied ? (
                          <Check className="size-3.5 text-primary" />
                        ) : (
                          <Copy className="size-3.5" />
                        )}
                        <span className="hidden sm:inline">
                          {hasCopied ? "Đã chép" : "Sao chép Q&A"}
                        </span>
                      </Button>
                    )}

                    <span className="text-[11px] font-mono text-muted-foreground hidden lg:inline mr-0.5">
                      Phím ↑ / ↓
                    </span>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={safeSelectedIndex === 0}
                      onClick={() =>
                        setSelectedIndex((prev) => Math.max(0, prev - 1))
                      }
                      className="h-7 px-2 text-xs gap-1"
                      title="Câu trước (hoặc phím mũi tên Lên)"
                    >
                      <ChevronLeft className="size-3.5" />
                      <span className="hidden sm:inline">Trước</span>
                    </Button>
                    <span className="text-xs font-mono text-muted-foreground px-1">
                      {safeSelectedIndex + 1} / {filteredItems.length}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={safeSelectedIndex >= filteredItems.length - 1}
                      onClick={() =>
                        setSelectedIndex((prev) =>
                          Math.min(filteredItems.length - 1, prev + 1),
                        )
                      }
                      className="h-7 px-2 text-xs gap-1"
                      title="Câu tiếp theo (hoặc phím mũi tên Xuống)"
                    >
                      <span className="hidden sm:inline">Tiếp</span>
                      <ChevronRight className="size-3.5" />
                    </Button>
                  </div>
                </div>

                {/* Nội dung chi tiết cuộn độc lập */}
                {activeItem.qnaParts.isSectionHeader ? (
                  /* =============================================================== */
                  /* TRƯỜNG HỢP 1: MỤC ĐANG CHỌN LÀ TIÊU ĐỀ CHƯƠNG / TỔNG QUAN        */
                  /* =============================================================== */
                  <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
                    <div className="p-6 rounded-2xl border border-border/80 bg-muted/15 space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="size-10 rounded-xl bg-primary/10 border border-primary/25 flex items-center justify-center text-primary shrink-0">
                          <FolderOpen className="size-5" />
                        </div>
                        <div>
                          <div className="text-[11px] font-bold uppercase tracking-wider text-primary">
                            Chương mục / Phân loại tri thức
                          </div>
                          <h2 className="text-lg sm:text-xl font-bold text-foreground">
                            {activeItem.parsed.title}
                          </h2>
                        </div>
                      </div>

                      {/* Các đoạn văn giới thiệu nếu có */}
                      {activeItem.group.paragraphs.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-border/50 text-sm leading-relaxed text-foreground/90">
                          {activeItem.group.paragraphs.map((p, pIdx) => (
                            <p key={pIdx}>{p.text}</p>
                          ))}
                        </div>
                      )}

                      {/* Nút xem câu hỏi tiếp theo */}
                      <div className="pt-2">
                        <Button
                          type="button"
                          variant="default"
                          size="sm"
                          onClick={() =>
                            setSelectedIndex((prev) =>
                              Math.min(filteredItems.length - 1, prev + 1),
                            )
                          }
                          className="gap-1.5 text-xs font-semibold"
                        >
                          <span>Xem các câu hỏi trong chủ đề này</span>
                          <ChevronRight className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* =============================================================== */
                  /* TRƯỜNG HỢP 2: CÂU HỎI & ĐỐI CHIẾU DẪN CHỨNG (HERO LAYOUT)       */
                  /* =============================================================== */
                  <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
                    {/* KHUNG 1: CÂU HỎI CHUẨN */}
                    <div className="p-4 sm:p-5 rounded-xl border border-primary/20 bg-primary/5 space-y-1.5 shadow-2xs">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-primary">
                          <HelpCircle className="size-3.5" />
                          <span>Câu hỏi chuẩn</span>
                        </div>
                        {activeItem.qnaParts.directAnswer?.citations &&
                          activeItem.qnaParts.directAnswer.citations.length >
                            0 && (
                            <span className="text-[11px] font-mono text-muted-foreground">
                              {
                                activeItem.qnaParts.directAnswer.citations
                                  .length
                              }{" "}
                              trích dẫn nguồn
                            </span>
                          )}
                      </div>
                      <h2 className="text-base sm:text-lg font-bold text-foreground leading-snug">
                        {activeItem.parsed.title}
                      </h2>
                    </div>

                    {/* KHUNG 2: CÂU TRẢ LỜI CHÍNH THỨC (HERO ANSWER) */}
                    <div className="p-5 rounded-xl border border-border/80 bg-card space-y-3.5 shadow-2xs">
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-border/50">
                        <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-foreground">
                          <CheckCircle2 className="size-4 text-primary" />
                          <span className="text-primary font-bold">
                            Câu trả lời chính thức
                          </span>
                          <span className="text-muted-foreground font-normal text-[11px] hidden sm:inline">
                            (Dùng cho Chatbot & Hỏi đáp)
                          </span>
                        </div>

                        {/* Thẻ dẫn chứng trích dẫn trực tiếp */}
                        {activeItem.qnaParts.directAnswer?.citations &&
                          activeItem.qnaParts.directAnswer.citations.length >
                            0 && (
                            <div className="flex flex-wrap items-center gap-1">
                              {Array.from(
                                new Set(
                                  activeItem.qnaParts.directAnswer.citations,
                                ),
                              ).map((id, citIdx) => (
                                <Button
                                  key={id}
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => onSelectCitation(id)}
                                  className="h-6 px-2 text-[11px] font-mono gap-1 text-primary border-primary/30 hover:bg-primary/10 shadow-2xs cursor-pointer font-medium"
                                  aria-label={`Xem dẫn chứng ${citIdx + 1} của đoạn ${activeItem.originalIndex + 1}.1`}
                                  title="Nhấp để đối soát vị trí văn bản gốc OCR"
                                >
                                  <Tag className="size-2.5 text-primary" />
                                  <span>Dẫn chứng {citIdx + 1}</span>
                                </Button>
                              ))}
                            </div>
                          )}
                      </div>

                      {/* Nội dung câu trả lời */}
                      <div className="text-sm sm:text-base leading-relaxed text-foreground font-sans font-medium whitespace-pre-wrap">
                        {activeItem.qnaParts.directAnswer?.text ||
                          "Chưa có nội dung câu trả lời."}
                      </div>

                      {/* Chân thẻ dẫn chứng hướng dẫn */}
                      {activeItem.qnaParts.directAnswer?.citations &&
                        activeItem.qnaParts.directAnswer.citations.length >
                          0 && (
                          <div className="pt-2 border-t border-border/40 text-[11px] text-muted-foreground flex items-center gap-1.5">
                            <Tag className="size-3 text-primary shrink-0" />
                            <span>
                              Dẫn chứng đã đối khớp với văn bản nguồn. Nhấp nút
                              dẫn chứng ở trên để xem tài liệu gốc.
                            </span>
                          </div>
                        )}
                    </div>

                    {/* KHUNG 3: NGỮ CẢNH TRÍCH XUẤT MỞ RỘNG (VECTOR DB & RAG) */}
                    {activeItem.qnaParts.embeddingContext ? (
                      <details className="rounded-xl border border-border/70 bg-muted/20 text-xs group overflow-hidden shadow-2xs">
                        <summary className="p-3.5 cursor-pointer font-semibold flex items-center justify-between text-muted-foreground hover:text-foreground select-none">
                          <span className="flex items-center gap-2">
                            <Sparkles className="size-3.5 text-primary" />
                            <span className="text-foreground/90 font-medium">
                              Ngữ cảnh trích xuất mở rộng (Dùng cho Vector DB &
                              RAG)
                            </span>
                          </span>
                          <span className="text-[11px] font-normal text-muted-foreground group-open:hidden">
                            Nhấp để xem chi tiết
                          </span>
                        </summary>
                        <div className="p-4 space-y-2.5 border-t border-border/50 text-sm leading-relaxed text-foreground/90 font-sans bg-background/50">
                          <p className="whitespace-pre-wrap">
                            {activeItem.qnaParts.embeddingContext.text}
                          </p>
                          {activeItem.qnaParts.embeddingContext.citations
                            .length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {Array.from(
                                new Set(
                                  activeItem.qnaParts.embeddingContext
                                    .citations,
                                ),
                              ).map((id, citIdx) => (
                                <Button
                                  key={id}
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => onSelectCitation(id)}
                                  className="h-5 px-1.5 text-[11px] font-mono gap-1 text-primary border-primary/30 hover:bg-primary/10"
                                  aria-label={`Xem dẫn chứng ${citIdx + 1} của đoạn ${activeItem.originalIndex + 1}.2`}
                                >
                                  <Tag className="size-2.5 text-primary" />
                                  <span>Dẫn chứng {citIdx + 1}</span>
                                </Button>
                              ))}
                            </div>
                          )}
                        </div>
                      </details>
                    ) : null}

                    {/* Các đoạn bổ sung khác (nếu có) */}
                    {activeItem.qnaParts.otherParagraphs.length > 0 && (
                      <div className="space-y-2 pt-2">
                        {activeItem.qnaParts.otherParagraphs.map((p, pIdx) => (
                          <div
                            key={`other-${pIdx}`}
                            className="p-3 rounded-lg border border-border/50 bg-background text-xs leading-relaxed text-muted-foreground"
                          >
                            <p>{p.text}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
                <p>Vui lòng chọn một câu hỏi ở danh mục bên trái.</p>
              </div>
            )}
          </div>
        </div>
      ) : viewMode === "table" ? (
        /* ========================================================================= */
        /* CHẾ ĐỘ 2: BẢNG DỮ LIỆU TRI THỨC PHÂN TRANG (CHUẨN FASTGPT)                */
        /* ========================================================================= */
        <div className="rounded-xl border border-border/80 bg-card overflow-hidden shadow-2xs">
          <Table>
            <TableHeader className="bg-muted/30">
              <TableRow>
                <TableHead className="w-40 min-w-[150px] text-xs font-semibold whitespace-nowrap">
                  Mã hiệu
                </TableHead>
                <TableHead className="min-w-[200px] text-xs font-semibold">
                  Câu hỏi
                </TableHead>
                <TableHead className="min-w-[280px] text-xs font-semibold hidden md:table-cell">
                  Câu trả lời tóm tắt
                </TableHead>
                <TableHead className="w-24 text-xs font-semibold text-center whitespace-nowrap">
                  Dẫn chứng
                </TableHead>
                <TableHead className="w-28 text-xs font-semibold text-right whitespace-nowrap">
                  Thao tác
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pagedItems.map(
                ({
                  group,
                  originalIndex,
                  parsed,
                  qnaParts,
                  totalCitations,
                }) => {
                  // Dòng phân loại chương
                  if (qnaParts.isSectionHeader) {
                    const isPage =
                      parsed.code?.toLowerCase() === "trang" ||
                      group.heading.toLowerCase().startsWith("trang");

                    return (
                      <TableRow
                        key={`table-row-${originalIndex}`}
                        className="bg-muted/40 hover:bg-muted/60 font-semibold cursor-pointer border-y border-border/80"
                        onClick={() => {
                          setSelectedIndex(
                            filteredItems.findIndex(
                              (item) => item.originalIndex === originalIndex,
                            ),
                          );
                          setViewMode("studio");
                        }}
                      >
                        <TableCell className="font-mono text-xs font-bold py-2.5 whitespace-nowrap">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-[10px] font-bold whitespace-nowrap inline-block",
                              isPage
                                ? "bg-muted text-muted-foreground border border-border/60"
                                : "bg-primary/10 text-primary border border-primary/20",
                            )}
                          >
                            {isPage ? "TRANG" : "CHỦ ĐỀ"}
                          </span>
                        </TableCell>
                        <TableCell
                          colSpan={3}
                          className="text-xs font-bold text-foreground py-2.5"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <FolderOpen className="size-3.5 text-primary shrink-0" />
                            <span className="truncate">
                              {isPage
                                ? group.heading
                                : parsed.code
                                  ? `Chủ đề ${parsed.code}: ${parsed.title}`
                                  : group.heading}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right py-2.5 whitespace-nowrap">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs text-primary"
                          >
                            Mở xem
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  }

                  // Trích xuất câu trả lời thực tế (không lặp lại câu hỏi)
                  const answerPreview =
                    qnaParts.directAnswer?.text ??
                    qnaParts.embeddingContext?.text ??
                    group.paragraphs[0]?.text ??
                    "Chưa có nội dung";

                  return (
                    <TableRow
                      key={`table-row-${originalIndex}`}
                      className="hover:bg-muted/30 cursor-pointer"
                      onClick={() => {
                        setSelectedIndex(
                          filteredItems.findIndex(
                            (item) => item.originalIndex === originalIndex,
                          ),
                        );
                        setViewMode("studio");
                      }}
                    >
                      <TableCell className="font-mono text-xs font-bold text-primary py-3 whitespace-nowrap">
                        {parsed.code ? (
                          <span className="bg-primary/10 px-2 py-0.5 rounded border border-primary/20 whitespace-nowrap inline-block tracking-tight">
                            {parsed.code}
                          </span>
                        ) : (
                          <span className="text-muted-foreground font-mono">
                            #{originalIndex + 1}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="font-medium text-foreground text-xs max-w-xs truncate">
                        {parsed.code ? parsed.title : group.heading}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs max-w-md truncate hidden md:table-cell">
                        {answerPreview}
                      </TableCell>
                      <TableCell className="text-center">
                        {totalCitations > 0 ? (
                          <Badge
                            variant="secondary"
                            className="font-mono text-[11px] gap-1"
                          >
                            <Tag className="size-2.5 text-primary" />
                            <span>{totalCitations}</span>
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground/60 text-xs">
                            —
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs text-primary hover:text-primary gap-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedIndex(
                              filteredItems.findIndex(
                                (item) => item.originalIndex === originalIndex,
                              ),
                            );
                            setViewMode("studio");
                          }}
                        >
                          <span>Chi tiết</span>
                          <ChevronRight className="size-3" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                },
              )}
            </TableBody>
          </Table>

          {/* Thanh phân trang Table */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-3 border-t border-border/60 bg-muted/15 text-xs text-muted-foreground">
              <span>
                Hiển thị {startIdx + 1} -{" "}
                {Math.min(startIdx + TABLE_PAGE_SIZE, filteredItems.length)} /{" "}
                {filteredItems.length} mục
              </span>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={tablePage === 1}
                  onClick={() => setTablePage((p) => Math.max(1, p - 1))}
                  className="h-7 px-2 text-xs"
                >
                  Trang trước
                </Button>
                <span className="px-2 font-mono text-xs">
                  {tablePage} / {totalPages}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={tablePage === totalPages}
                  onClick={() =>
                    setTablePage((p) => Math.min(totalPages, p + 1))
                  }
                  className="h-7 px-2 text-xs"
                >
                  Trang sau
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* ========================================================================= */
        /* CHẾ ĐỘ 3: TOÀN VĂN LIÊN TỤC (READER DOCUMENT MODE)                        */
        /* ========================================================================= */
        <div className="space-y-4">
          {filteredItems.map(
            ({ originalIndex, parsed, qnaParts }) => {
              return (
                <article
                  key={`doc-sec-${originalIndex}`}
                  id={`section-${originalIndex}`}
                  className="p-4 sm:p-5 rounded-xl border border-border/70 bg-card hover:border-border transition-colors space-y-3 shadow-2xs"
                >
                  <div className="flex items-start sm:items-center gap-2">
                    {parsed.code ? (
                      <Badge
                        variant="outline"
                        className="font-mono text-[11px] font-semibold text-primary bg-primary/5 border-primary/25 shrink-0 px-2 py-0.5 rounded"
                      >
                        {parsed.code}
                      </Badge>
                    ) : null}
                    <h3 className="font-bold text-foreground text-sm sm:text-base leading-snug">
                      {parsed.title}
                    </h3>
                  </div>

                  <div className="space-y-2.5 text-sm leading-relaxed pl-1 sm:pl-2 border-l-2 border-primary/30 ml-0.5">
                    {qnaParts.directAnswer && (
                      <p className="font-medium text-foreground">
                        {qnaParts.directAnswer.text}
                      </p>
                    )}
                    {qnaParts.embeddingContext && (
                      <p className="text-muted-foreground text-xs italic">
                        {qnaParts.embeddingContext.text}
                      </p>
                    )}
                    {qnaParts.otherParagraphs.map((p, idx) => (
                      <p key={idx} className="text-foreground/90">
                        {p.text}
                      </p>
                    ))}
                  </div>
                </article>
              );
            },
          )}
        </div>
      )}
    </div>
  );
});

import {
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Copy,
  Eye,
  FileSpreadsheet,
  Filter,
  Layers,
  RefreshCw,
  RotateCcw,
  Search,
  Table2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { FactItem } from "@/types";

export interface CollectionFactsTabProps {
  facts: FactItem[];
  totalCount: number;
  isLoading: boolean;
  isFetching: boolean;
  onRefresh: () => void;
  onOpenExcelImport: () => void;
}

type QuickCategory = "all" | "score" | "quota" | "tuition" | "combo" | "other";
type SortOption =
  | "default"
  | "entity_asc"
  | "entity_desc"
  | "attr_asc"
  | "confidence_desc";

export function CollectionFactsTab({
  facts,
  totalCount,
  isLoading,
  isFetching,
  onRefresh,
  onOpenExcelImport,
}: CollectionFactsTabProps) {
  // Local Filter & Search States
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedQuickCategory, setSelectedQuickCategory] =
    useState<QuickCategory>("all");
  const [entityTypeFilter, setEntityTypeFilter] = useState("all");
  const [attributeFilter, setAttributeFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [sortBy, setSortBy] = useState<SortOption>("default");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Inspector Dialog State
  const [inspectFact, setInspectFact] = useState<FactItem | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // 1. Compute Telemetry / Metrics
  const metrics = useMemo(() => {
    const entities = new Set<string>();
    const attributes = new Set<string>();
    let totalConf = 0;

    let scoreCount = 0;
    let quotaCount = 0;
    let tuitionCount = 0;
    let comboCount = 0;
    let otherCount = 0;

    for (const f of facts) {
      if (f.entity_name) entities.add(f.entity_name);
      if (f.attribute_name) attributes.add(f.attribute_name);
      totalConf += f.confidence || 0;

      const attrLower = (f.attribute_name || "").toLowerCase();
      if (attrLower.includes("điểm") || attrLower.includes("score")) {
        scoreCount++;
      } else if (
        attrLower.includes("chỉ tiêu") ||
        attrLower.includes("quota")
      ) {
        quotaCount++;
      } else if (
        attrLower.includes("học phí") ||
        attrLower.includes("tuition") ||
        attrLower.includes("phí")
      ) {
        tuitionCount++;
      } else if (
        attrLower.includes("tổ hợp") ||
        attrLower.includes("combo") ||
        attrLower.includes("môn")
      ) {
        comboCount++;
      } else {
        otherCount++;
      }
    }

    const avgConf =
      facts.length > 0 ? Math.round((totalConf / facts.length) * 100) : 100;

    return {
      entityCount: entities.size,
      attributeCount: attributes.size,
      avgConfidence: avgConf,
      scoreCount,
      quotaCount,
      tuitionCount,
      comboCount,
      otherCount,
    };
  }, [facts]);

  // Distinct Lists for Select Filters
  const distinctEntityTypes = useMemo(() => {
    const set = new Set<string>();
    for (const f of facts) {
      if (f.entity_type) set.add(f.entity_type);
    }
    return Array.from(set).sort();
  }, [facts]);

  const distinctAttributes = useMemo(() => {
    const set = new Set<string>();
    for (const f of facts) {
      if (f.attribute_name) set.add(f.attribute_name);
    }
    return Array.from(set).sort();
  }, [facts]);

  // 2. Filter & Sort Logic
  const filteredFacts = useMemo(() => {
    let result = [...facts];

    // Quick Category Filter
    if (selectedQuickCategory !== "all") {
      result = result.filter((f) => {
        const attr = (f.attribute_name || "").toLowerCase();
        if (selectedQuickCategory === "score") {
          return attr.includes("điểm") || attr.includes("score");
        }
        if (selectedQuickCategory === "quota") {
          return attr.includes("chỉ tiêu") || attr.includes("quota");
        }
        if (selectedQuickCategory === "tuition") {
          return (
            attr.includes("học phí") ||
            attr.includes("tuition") ||
            attr.includes("phí")
          );
        }
        if (selectedQuickCategory === "combo") {
          return (
            attr.includes("tổ hợp") ||
            attr.includes("combo") ||
            attr.includes("môn")
          );
        }
        if (selectedQuickCategory === "other") {
          return (
            !attr.includes("điểm") &&
            !attr.includes("chỉ tiêu") &&
            !attr.includes("học phí") &&
            !attr.includes("tổ hợp")
          );
        }
        return true;
      });
    }

    // Entity Type Filter
    if (entityTypeFilter !== "all") {
      result = result.filter((f) => f.entity_type === entityTypeFilter);
    }

    // Specific Attribute Filter
    if (attributeFilter !== "all") {
      result = result.filter((f) => f.attribute_name === attributeFilter);
    }

    // Confidence Filter
    if (confidenceFilter !== "all") {
      result = result.filter((f) => {
        const conf = f.confidence || 0;
        if (confidenceFilter === "high") return conf >= 0.9;
        if (confidenceFilter === "medium") return conf >= 0.8 && conf < 0.9;
        if (confidenceFilter === "low") return conf < 0.8;
        return true;
      });
    }

    // Search Query (Entity Name, Attribute Name, Value, or Raw Data)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((f) => {
        const matchEntity = (f.entity_name || "").toLowerCase().includes(q);
        const matchAttr = (f.attribute_name || "").toLowerCase().includes(q);
        const matchVal = (f.attribute_value || "").toLowerCase().includes(q);
        const matchRaw = JSON.stringify(f.raw_data || {})
          .toLowerCase()
          .includes(q);
        return matchEntity || matchAttr || matchVal || matchRaw;
      });
    }

    // Sắp xếp
    if (sortBy === "entity_asc") {
      result.sort((a, b) =>
        (a.entity_name || "").localeCompare(b.entity_name || "", "vi"),
      );
    } else if (sortBy === "entity_desc") {
      result.sort((a, b) =>
        (b.entity_name || "").localeCompare(a.entity_name || "", "vi"),
      );
    } else if (sortBy === "attr_asc") {
      result.sort((a, b) =>
        (a.attribute_name || "").localeCompare(b.attribute_name || "", "vi"),
      );
    } else if (sortBy === "confidence_desc") {
      result.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
    }

    return result;
  }, [
    facts,
    selectedQuickCategory,
    entityTypeFilter,
    attributeFilter,
    confidenceFilter,
    searchQuery,
    sortBy,
  ]);

  // 3. Pagination Slicing
  const totalFiltered = filteredFacts.length;
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize));

  // Auto-adjust page if out of bounds
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const paginatedFacts = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return filteredFacts.slice(start, start + pageSize);
  }, [filteredFacts, safeCurrentPage, pageSize]);

  // Check if any filter is active
  const hasActiveFilters =
    Boolean(searchQuery.trim()) ||
    selectedQuickCategory !== "all" ||
    entityTypeFilter !== "all" ||
    attributeFilter !== "all" ||
    confidenceFilter !== "all" ||
    sortBy !== "default";

  const resetAllFilters = () => {
    setSearchQuery("");
    setSelectedQuickCategory("all");
    setEntityTypeFilter("all");
    setAttributeFilter("all");
    setConfidenceFilter("all");
    setSortBy("default");
    setCurrentPage(1);
  };

  // Helper copy to clipboard
  const handleCopyValue = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast.success(`Đã sao chép: "${text}"`);
    setTimeout(() => setCopiedId(null), 1800);
  };

  return (
    <div className="space-y-4">
      {/* 1. Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-3.5 sm:p-4 rounded-lg border border-border">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Table2 className="size-4 text-primary" />
            <span>Bảng Biểu & Số Liệu Trích Xuất (Facts Layer)</span>
            <Badge variant="outline" className="font-mono text-xs">
              {totalCount} facts
            </Badge>
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            Các số liệu chính xác 100% dạng bảng (điểm chuẩn, chỉ tiêu, học phí)
            được nạp trực tiếp từ bảng tính Excel/CSV để Trợ lý AI tra cứu đối
            soát, chống bịa đặt (Zero Hallucination).
          </p>
        </div>
        <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full sm:w-auto shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isFetching}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw
              className={cn("size-3.5", isFetching && "animate-spin")}
            />
            <span>Làm mới</span>
          </Button>
          <Button
            size="sm"
            onClick={onOpenExcelImport}
            className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <FileSpreadsheet className="size-3.5" />
            <span>Nạp Excel</span>
          </Button>
        </div>
      </div>

      {/* 2. Telemetry KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3">
        <div className="bg-card p-3 rounded-lg border border-border flex items-center justify-between">
          <div>
            <div className="text-[11px] text-muted-foreground">
              Tổng số facts
            </div>
            <div className="text-lg font-bold text-foreground font-mono mt-0.5">
              {totalCount}
            </div>
          </div>
          <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Table2 className="size-4" />
          </div>
        </div>

        <div className="bg-card p-3 rounded-lg border border-border flex items-center justify-between">
          <div>
            <div className="text-[11px] text-muted-foreground">
              Thực thể ngành / khoa
            </div>
            <div className="text-lg font-bold text-foreground font-mono mt-0.5">
              {metrics.entityCount}
            </div>
          </div>
          <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Layers className="size-4" />
          </div>
        </div>

        <div className="bg-card p-3 rounded-lg border border-border flex items-center justify-between">
          <div>
            <div className="text-[11px] text-muted-foreground">
              Loại thuộc tính
            </div>
            <div className="text-lg font-bold text-foreground font-mono mt-0.5">
              {metrics.attributeCount}
            </div>
          </div>
          <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Filter className="size-4" />
          </div>
        </div>

        <div className="bg-card p-3 rounded-lg border border-border flex items-center justify-between">
          <div>
            <div className="text-[11px] text-muted-foreground">
              Độ tin cậy TB
            </div>
            <div className="text-lg font-bold text-success font-mono mt-0.5">
              {metrics.avgConfidence}%
            </div>
          </div>
          <div className="size-8 rounded-lg bg-success/10 text-success flex items-center justify-center">
            <Check className="size-4" />
          </div>
        </div>
      </div>

      {/* 3. Quick Filter Chips Bar */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        <span className="text-xs text-muted-foreground mr-1 flex items-center gap-1">
          <Filter className="size-3" />
          <span>Lọc nhanh:</span>
        </span>

        <button
          type="button"
          onClick={() => {
            setSelectedQuickCategory("all");
            setCurrentPage(1);
          }}
          className={cn(
            "h-7 px-2.5 rounded-full text-xs font-medium transition-colors border",
            selectedQuickCategory === "all"
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border-border/60",
          )}
        >
          Tất cả ({facts.length})
        </button>

        {metrics.scoreCount > 0 && (
          <button
            type="button"
            onClick={() => {
              setSelectedQuickCategory("score");
              setCurrentPage(1);
            }}
            className={cn(
              "h-7 px-2.5 rounded-full text-xs font-medium transition-colors border",
              selectedQuickCategory === "score"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border-border/60",
            )}
          >
            Điểm chuẩn ({metrics.scoreCount})
          </button>
        )}

        {metrics.quotaCount > 0 && (
          <button
            type="button"
            onClick={() => {
              setSelectedQuickCategory("quota");
              setCurrentPage(1);
            }}
            className={cn(
              "h-7 px-2.5 rounded-full text-xs font-medium transition-colors border",
              selectedQuickCategory === "quota"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border-border/60",
            )}
          >
            Chỉ tiêu ({metrics.quotaCount})
          </button>
        )}

        {metrics.tuitionCount > 0 && (
          <button
            type="button"
            onClick={() => {
              setSelectedQuickCategory("tuition");
              setCurrentPage(1);
            }}
            className={cn(
              "h-7 px-2.5 rounded-full text-xs font-medium transition-colors border",
              selectedQuickCategory === "tuition"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border-border/60",
            )}
          >
            Học phí ({metrics.tuitionCount})
          </button>
        )}

        {metrics.comboCount > 0 && (
          <button
            type="button"
            onClick={() => {
              setSelectedQuickCategory("combo");
              setCurrentPage(1);
            }}
            className={cn(
              "h-7 px-2.5 rounded-full text-xs font-medium transition-colors border",
              selectedQuickCategory === "combo"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border-border/60",
            )}
          >
            Tổ hợp môn ({metrics.comboCount})
          </button>
        )}

        {metrics.otherCount > 0 && (
          <button
            type="button"
            onClick={() => {
              setSelectedQuickCategory("other");
              setCurrentPage(1);
            }}
            className={cn(
              "h-7 px-2.5 rounded-full text-xs font-medium transition-colors border",
              selectedQuickCategory === "other"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border-border/60",
            )}
          >
            Khác ({metrics.otherCount})
          </button>
        )}
      </div>

      {/* 4. Unified Search & Multi-Filters Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5 bg-card p-3 rounded-lg border border-border">
        {/* Search Input with Integrated Clear Button */}
        <div className="relative w-full lg:w-72 xl:w-80 shrink-0">
          <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Tìm mã ngành, tên, giá trị..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="h-8 pl-8 pr-8 text-xs w-full"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
                setCurrentPage(1);
              }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              title="Xóa từ khóa tìm kiếm"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 w-full lg:w-auto justify-start sm:justify-end">
          {/* Phân loại thực thể */}
          {distinctEntityTypes.length > 1 && (
            <Select
              value={entityTypeFilter}
              onValueChange={(val) => {
                setEntityTypeFilter(val);
                setCurrentPage(1);
              }}
            >
              <SelectTrigger sizeVariant="sm" className="w-[130px] text-xs">
                <SelectValue placeholder="Thực thể" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Mọi thực thể</SelectItem>
                {distinctEntityTypes.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t.toUpperCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Thuộc tính */}
          {distinctAttributes.length > 1 && (
            <Select
              value={attributeFilter}
              onValueChange={(val) => {
                setAttributeFilter(val);
                setCurrentPage(1);
              }}
            >
              <SelectTrigger sizeVariant="sm" className="w-[140px] text-xs">
                <SelectValue placeholder="Thuộc tính" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Mọi thuộc tính</SelectItem>
                {distinctAttributes.map((a) => (
                  <SelectItem key={a} value={a}>
                    {a}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Độ tin cậy */}
          <Select
            value={confidenceFilter}
            onValueChange={(val) => {
              setConfidenceFilter(val);
              setCurrentPage(1);
            }}
          >
            <SelectTrigger sizeVariant="sm" className="w-[125px] text-xs">
              <SelectValue placeholder="Độ tin cậy" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi độ tin cậy</SelectItem>
              <SelectItem value="high">Cao (≥ 90%)</SelectItem>
              <SelectItem value="medium">Khá (80 - 89%)</SelectItem>
              <SelectItem value="low">Cần soát (&lt; 80%)</SelectItem>
            </SelectContent>
          </Select>

          {/* Sắp xếp */}
          <Select
            value={sortBy}
            onValueChange={(val) => setSortBy(val as SortOption)}
          >
            <SelectTrigger sizeVariant="sm" className="w-[135px] text-xs">
              <SelectValue placeholder="Sắp xếp" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Mới số hóa nhất</SelectItem>
              <SelectItem value="entity_asc">Thực thể (A-Z)</SelectItem>
              <SelectItem value="entity_desc">Thực thể (Z-A)</SelectItem>
              <SelectItem value="attr_asc">Thuộc tính (A-Z)</SelectItem>
              <SelectItem value="confidence_desc">
                Độ tin cậy cao nhất
              </SelectItem>
            </SelectContent>
          </Select>

          {/* Nút đặt lại */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetAllFilters}
              className="h-8 text-xs gap-1 text-muted-foreground hover:text-foreground shrink-0"
              title="Đặt lại toàn bộ bộ lọc"
            >
              <RotateCcw className="size-3.5" />
              <span className="hidden sm:inline">Đặt lại</span>
            </Button>
          )}
        </div>
      </div>

      {/* 5. Mobile Facts Card View (< 640px) */}
      <div className="sm:hidden space-y-2.5">
        {isLoading ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            Đang tải danh sách bảng biểu số liệu...
          </div>
        ) : paginatedFacts.length === 0 ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            <FileSpreadsheet className="size-8 mx-auto mb-2 opacity-30 text-primary" />
            <p className="text-sm font-medium text-foreground">
              {hasActiveFilters
                ? "Không tìm thấy số liệu phù hợp với bộ lọc"
                : "Chưa có bảng biểu số liệu nào trong kho này"}
            </p>
            {hasActiveFilters ? (
              <Button
                variant="outline"
                size="sm"
                onClick={resetAllFilters}
                className="h-8 text-xs gap-1.5 mt-3"
              >
                <RotateCcw className="size-3.5" />
                <span>Xóa bộ lọc</span>
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={onOpenExcelImport}
                className="h-8 text-xs gap-1.5 mt-3"
              >
                <FileSpreadsheet className="size-3.5" />
                <span>Nạp tệp Excel ngay</span>
              </Button>
            )}
          </div>
        ) : (
          paginatedFacts.map((fact) => (
            <div
              key={fact.id}
              className="p-3.5 rounded-lg border border-border bg-card space-y-2 shadow-2xs"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-xs text-foreground">
                  {fact.entity_name}
                </span>
                <Badge
                  variant="outline"
                  className="text-[10px] px-1.5 py-0 font-normal uppercase shrink-0"
                >
                  {fact.entity_type}
                </Badge>
              </div>

              <div className="flex items-center justify-between text-xs pt-1.5 border-t border-border/50">
                <span className="text-muted-foreground font-mono text-[11px]">
                  {fact.attribute_name}
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-primary font-mono text-xs">
                    {fact.attribute_value}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      handleCopyValue(fact.attribute_value, fact.id)
                    }
                    className="text-muted-foreground hover:text-foreground p-0.5"
                    title="Sao chép giá trị"
                  >
                    {copiedId === fact.id ? (
                      <Check className="size-3 text-success" />
                    ) : (
                      <Copy className="size-3" />
                    )}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1.5 border-t border-border/50">
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] px-1.5 py-0 font-mono",
                    fact.confidence >= 0.9
                      ? "bg-success/10 text-success border-success/30"
                      : fact.confidence >= 0.8
                        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                        : "bg-muted text-muted-foreground",
                  )}
                >
                  {Math.round(fact.confidence * 100)}% tin cậy
                </Badge>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono">
                    {fact.created_at
                      ? new Date(fact.created_at).toLocaleDateString("vi-VN")
                      : "N/A"}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                    onClick={() => setInspectFact(fact)}
                    title="Xem chi tiết"
                  >
                    <Eye className="size-3" />
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 6. Desktop & Tablet Facts Table (>= 640px) */}
      <div className="hidden sm:block bg-card rounded-lg border border-border overflow-hidden shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs font-semibold text-muted-foreground uppercase">
              <TableHead className="w-12 text-center">#</TableHead>
              <TableHead>Thực thể (Entity)</TableHead>
              <TableHead className="w-28">Phân loại</TableHead>
              <TableHead className="w-48">Thuộc tính (Attribute)</TableHead>
              <TableHead>Giá trị (Value)</TableHead>
              <TableHead className="w-28 text-center">Độ tin cậy</TableHead>
              <TableHead className="w-36">Thời điểm số hóa</TableHead>
              <TableHead className="w-16 text-right">Chi tiết</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center py-12 text-xs text-muted-foreground"
                >
                  Đang tải danh sách bảng biểu số liệu...
                </TableCell>
              </TableRow>
            ) : paginatedFacts.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center py-12 text-muted-foreground"
                >
                  <FileSpreadsheet className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                  <p className="text-sm font-medium text-foreground">
                    {hasActiveFilters
                      ? "Không tìm thấy số liệu phù hợp với bộ lọc"
                      : "Chưa có bảng biểu số liệu nào trong kho này"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                    Tải lên tệp Excel (.xlsx) hoặc CSV chứa các cột (Mã ngành,
                    Tên ngành, Điểm chuẩn, Chỉ tiêu, Học phí) để hệ thống tự
                    động bóc tách thành facts tra cứu.
                  </p>
                  {hasActiveFilters ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={resetAllFilters}
                      className="h-8 text-xs gap-1.5 mt-3"
                    >
                      <RotateCcw className="size-3.5" />
                      <span>Xóa bộ lọc</span>
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={onOpenExcelImport}
                      className="h-8 text-xs gap-1.5 mt-3"
                    >
                      <FileSpreadsheet className="size-3.5" />
                      <span>Tải tệp Excel ngay</span>
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ) : (
              paginatedFacts.map((fact, idx) => {
                const globalIdx = (safeCurrentPage - 1) * pageSize + idx + 1;
                return (
                  <TableRow
                    key={fact.id}
                    className="hover:bg-muted/30 text-xs transition-colors group"
                  >
                    <TableCell className="text-center font-mono text-[11px] text-muted-foreground">
                      {globalIdx}
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold text-foreground leading-snug">
                        {fact.entity_name}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="text-[11px] font-normal uppercase py-0"
                      >
                        {fact.entity_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {fact.attribute_name}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-primary font-mono select-all">
                          {fact.attribute_value}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            handleCopyValue(fact.attribute_value, fact.id)
                          }
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground p-0.5"
                          title="Sao chép giá trị"
                        >
                          {copiedId === fact.id ? (
                            <Check className="size-3 text-success" />
                          ) : (
                            <Copy className="size-3" />
                          )}
                        </button>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[11px] font-mono py-0",
                          fact.confidence >= 0.9
                            ? "bg-success/10 text-success border-success/30"
                            : fact.confidence >= 0.8
                              ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                              : "bg-muted text-muted-foreground",
                        )}
                      >
                        {Math.round(fact.confidence * 100)}%
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-[11px]">
                      {fact.created_at
                        ? new Date(fact.created_at).toLocaleString("vi-VN")
                        : "N/A"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                        onClick={() => setInspectFact(fact)}
                        title="Xem chi tiết số hóa"
                      >
                        <Eye className="size-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>

        {/* 7. Pagination Footer Toolbar */}
        {totalFiltered > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-2.5 bg-muted/20 border-t border-border text-xs text-muted-foreground">
            <div>
              Hiển thị{" "}
              <span className="font-semibold text-foreground">
                {(safeCurrentPage - 1) * pageSize + 1}
              </span>{" "}
              -{" "}
              <span className="font-semibold text-foreground">
                {Math.min(safeCurrentPage * pageSize, totalFiltered)}
              </span>{" "}
              trong số{" "}
              <span className="font-semibold text-foreground">
                {totalFiltered}
              </span>{" "}
              facts đã lọc
              {totalCount > totalFiltered && (
                <span> (Tổng số kho: {totalCount})</span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {/* Page Size Selector */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px]">Hàng/trang:</span>
                <Select
                  value={String(pageSize)}
                  onValueChange={(val) => {
                    setPageSize(Number(val));
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger sizeVariant="sm" className="h-7 w-16 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15</SelectItem>
                    <SelectItem value="25">25</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Page Navigation Buttons */}
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setCurrentPage(1)}
                  disabled={safeCurrentPage <= 1}
                  title="Trang đầu"
                >
                  <ChevronsLeft className="size-3.5" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() =>
                    setCurrentPage((prev) => Math.max(1, prev - 1))
                  }
                  disabled={safeCurrentPage <= 1}
                  title="Trang trước"
                >
                  <ChevronLeft className="size-3.5" />
                </Button>

                <span className="px-2 font-mono text-xs text-foreground font-medium">
                  {safeCurrentPage} / {totalPages}
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() =>
                    setCurrentPage((prev) => Math.min(totalPages, prev + 1))
                  }
                  disabled={safeCurrentPage >= totalPages}
                  title="Trang sau"
                >
                  <ChevronRight className="size-3.5" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={safeCurrentPage >= totalPages}
                  title="Trang cuối"
                >
                  <ChevronsRight className="size-3.5" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 8. Fact Details Inspector Dialog */}
      <Dialog
        open={Boolean(inspectFact)}
        onOpenChange={(open) => !open && setInspectFact(null)}
      >
        <DialogContent className="max-w-md sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <Table2 className="size-4 text-primary" />
              <span>Chi Tiết Số Liệu Fact Số Hóa</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Mã định danh hệ thống:{" "}
              <span className="font-mono text-foreground font-semibold">
                {inspectFact?.id}
              </span>
            </DialogDescription>
          </DialogHeader>

          {inspectFact && (
            <div className="space-y-3.5 py-1 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-muted/30 p-3 rounded-lg border border-border">
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    Thực thể (Entity)
                  </span>
                  <span className="font-semibold text-foreground text-xs">
                    {inspectFact.entity_name}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    Phân loại
                  </span>
                  <Badge
                    variant="outline"
                    className="text-[10px] uppercase mt-0.5"
                  >
                    {inspectFact.entity_type}
                  </Badge>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    Tên thuộc tính
                  </span>
                  <span className="font-mono text-foreground">
                    {inspectFact.attribute_name}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    Giá trị số hóa
                  </span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="font-bold text-primary font-mono text-sm">
                      {inspectFact.attribute_value}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        handleCopyValue(
                          inspectFact.attribute_value,
                          inspectFact.id,
                        )
                      }
                      className="text-muted-foreground hover:text-foreground"
                      title="Sao chép giá trị"
                    >
                      <Copy className="size-3" />
                    </button>
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    Độ tin cậy Grounded
                  </span>
                  <span className="font-mono text-success font-semibold">
                    {Math.round(inspectFact.confidence * 100)}%
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    Thời điểm tạo
                  </span>
                  <span className="text-muted-foreground font-mono">
                    {inspectFact.created_at
                      ? new Date(inspectFact.created_at).toLocaleString("vi-VN")
                      : "N/A"}
                  </span>
                </div>
              </div>

              {/* Raw Data JSON */}
              <div>
                <span className="text-muted-foreground block text-[11px] mb-1 font-medium">
                  Dữ liệu gốc trích xuất (Raw Metadata):
                </span>
                <pre className="p-3 rounded-lg bg-muted/50 border border-border font-mono text-[11px] overflow-x-auto max-h-48 text-foreground leading-relaxed">
                  {JSON.stringify(inspectFact.raw_data || {}, null, 2)}
                </pre>
              </div>

              <div className="flex justify-end pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setInspectFact(null)}
                  className="h-8 text-xs"
                >
                  Đóng
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

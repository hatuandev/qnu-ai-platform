import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  Check,
  CheckCircle2,
  Copy,
  FileCheck2,
  FileText,
  GraduationCap,
  LayoutGrid,
  List,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Scale,
  Search,
  Settings,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { CreateDocumentTypeDialog } from "@/components/document-types/dialogs/create-document-type-dialog";
import {
  DocumentTypeCard,
  formatCategoryLabel,
  getCategoryIcon,
} from "@/components/document-types/document-type-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  activateDocumentType,
  type DocumentTypeCategory,
  deactivateDocumentType,
  listDocumentTypes,
  syncDocumentTypes,
} from "@/services/document-types-api";

const CATEGORY_OPTIONS: Array<{
  value: DocumentTypeCategory | "all";
  label: string;
}> = [
  { value: "all", label: "Tất cả nhóm" },
  { value: "legal_internal", label: "Quy phạm & Nội bộ" },
  { value: "administrative", label: "Hành chính Điều hành" },
  { value: "academic", label: "Đào tạo & Học thuật" },
  { value: "forms", label: "Biểu mẫu & Tiếp nhận" },
];

export function DocumentTypesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<DocumentTypeCategory | "all">("all");
  const [statusFilter, setStatusFilter] = useState<
    "all" | "active" | "inactive"
  >("all");
  const [standardFilter, setStandardFilter] = useState<
    "all" | "nd30" | "custom"
  >("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // 1. Fetch document types
  const documentTypesQuery = useQuery({
    queryKey: ["document-types"],
    queryFn: () => listDocumentTypes(),
  });

  // 2. Sync Mutation
  const syncMutation = useMutation({
    mutationFn: () => syncDocumentTypes(),
    onSuccess: (res) => {
      toast.success(
        `Đã đồng bộ taxonomy thành công! (Thêm: ${res.added}, Cập nhật: ${res.updated}, Tổng: ${res.total})`,
      );
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
    onError: (err: Error) => {
      toast.error(`Đồng bộ thất bại: ${err.message}`);
    },
  });

  // 3. Toggle Active Mutation
  const toggleActiveMutation = useMutation({
    mutationFn: async ({ code, active }: { code: string; active: boolean }) => {
      return active ? activateDocumentType(code) : deactivateDocumentType(code);
    },
    onSuccess: (updated) => {
      toast.success(
        updated.is_active
          ? `Đã kích hoạt thể thức “${updated.name}”.`
          : `Đã tạm dừng thể thức “${updated.name}”.`,
      );
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật trạng thái thất bại: ${err.message}`);
    },
  });

  // 4. Filter Items
  const rawItems = documentTypesQuery.data ?? [];
  const items = useMemo(() => {
    return rawItems.filter((item) => {
      // Search
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchCode = item.code.toLowerCase().includes(q);
        const matchName = item.name.toLowerCase().includes(q);
        const matchDesc = item.description?.toLowerCase().includes(q) ?? false;
        if (!matchCode && !matchName && !matchDesc) return false;
      }

      // Category
      if (category !== "all" && item.category !== category) return false;

      // Status
      if (statusFilter === "active" && !item.is_active) return false;
      if (statusFilter === "inactive" && item.is_active) return false;

      // Standard
      if (standardFilter === "nd30" && !item.nd30) return false;
      if (standardFilter === "custom" && !item.is_custom) return false;

      return true;
    });
  }, [rawItems, search, category, statusFilter, standardFilter]);

  // Telemetry Metrics
  const totalCount = rawItems.length;
  const nd30Count = rawItems.filter((i) => i.nd30).length;
  const academicCount = rawItems.filter(
    (i) => i.category === "academic",
  ).length;
  const activeCount = rawItems.filter((i) => i.is_active).length;

  const handleCopyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success(`Đã sao chép mã “${code}”!`);
    } catch {
      toast.error("Không thể sao chép mã.");
    }
  };

  return (
    <div className="space-y-5">
      {/* 1. Header & Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-border/70">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <FileText className="size-5 text-primary" />
            <span>Loại Văn Bản</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Danh mục phân loại tài liệu chuẩn hóa theo Nghị định 30/2020/NĐ-CP
            và quy chế học thuật ĐH Quy Nhơn.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            title="Đồng bộ danh mục taxonomy mẫu từ core"
          >
            <RefreshCw
              className={`size-3.5 ${syncMutation.isPending ? "animate-spin text-primary" : ""}`}
            />
            <span>Đồng bộ</span>
          </Button>

          <Button
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => setIsCreateOpen(true)}
          >
            <Plus className="size-3.5" />
            <span>Thêm loại</span>
          </Button>
        </div>
      </div>

      {/* 2. KPI Telemetry Strip 4 ô gộp trong Card nguyên khối */}
      <Card className="overflow-hidden border border-border/80 shadow-2xs">
        <CardContent className="grid grid-cols-2 lg:grid-cols-4 p-0 divide-y sm:divide-y-0 sm:divide-x divide-border">
          <KpiMetric
            icon={FileText}
            label="Tổng loại văn bản"
            value={totalCount.toString()}
            helper="Thể thức CSDL chuẩn hóa"
          />
          <KpiMetric
            icon={Scale}
            label="Chuẩn NĐ 30/2020"
            value={`${nd30Count} loại`}
            helper="Văn bản hành chính nhà nước"
          />
          <KpiMetric
            icon={GraduationCap}
            label="Đào tạo & Học thuật"
            value={`${academicCount} loại`}
            helper="Đề án, chương trình, quy chế"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Đang hoạt động"
            value={`${activeCount} / ${totalCount}`}
            helper="Khả dụng nạp Kho tri thức"
          />
        </CardContent>
      </Card>

      {/* 3. Filter Bar & View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Ô tìm kiếm debounced */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm theo tên hoặc mã loại văn bản..."
              className="h-8 pl-8 text-xs"
            />
          </div>

          {/* Bộ lọc Nhóm phân loại (175px chống cắt chữ) */}
          <Select
            value={category}
            onValueChange={(val) =>
              setCategory(val as DocumentTypeCategory | "all")
            }
          >
            <SelectTrigger className="h-8 w-[175px] text-xs">
              <SelectValue placeholder="Nhóm văn bản" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORY_OPTIONS.map((opt) => (
                <SelectItem
                  key={opt.value}
                  value={opt.value}
                  className="text-xs"
                >
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Bộ lọc Trạng thái */}
          <Select
            value={statusFilter}
            onValueChange={(val) =>
              setStatusFilter(val as "all" | "active" | "inactive")
            }
          >
            <SelectTrigger className="h-8 w-[140px] text-xs">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="text-xs">
                Tất cả trạng thái
              </SelectItem>
              <SelectItem value="active" className="text-xs">
                Đang hoạt động
              </SelectItem>
              <SelectItem value="inactive" className="text-xs">
                Đã tạm dừng
              </SelectItem>
            </SelectContent>
          </Select>

          {/* Quick toggle chips */}
          <div className="flex items-center gap-1 bg-muted/40 p-0.5 rounded-md border text-xs">
            <button
              type="button"
              onClick={() => setStandardFilter("all")}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                standardFilter === "all"
                  ? "bg-background text-foreground shadow-2xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Tất cả
            </button>
            <button
              type="button"
              onClick={() => setStandardFilter("nd30")}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                standardFilter === "nd30"
                  ? "bg-background text-foreground shadow-2xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Chuẩn NĐ 30
            </button>
            <button
              type="button"
              onClick={() => setStandardFilter("custom")}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                standardFilter === "custom"
                  ? "bg-background text-foreground shadow-2xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Tùy chỉnh
            </button>
          </div>
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center gap-1 border rounded-md p-0.5 bg-muted/30 shrink-0 self-end sm:self-auto">
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setViewMode("grid")}
            title="Xem dạng thẻ lưới"
          >
            <LayoutGrid className="size-3.5" />
          </Button>
          <Button
            variant={viewMode === "table" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setViewMode("table")}
            title="Xem dạng danh sách bảng"
          >
            <List className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* 4. Main Document Types Content */}
      {documentTypesQuery.isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
          <Loader2 className="size-6 animate-spin text-primary" />
          <span className="text-xs">
            Đang tải danh sách loại văn bản từ CSDL...
          </span>
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={
            search ||
            category !== "all" ||
            statusFilter !== "all" ||
            standardFilter !== "all"
              ? "Không tìm thấy loại văn bản phù hợp"
              : "Chưa có danh mục loại văn bản nào"
          }
          description={
            search ||
            category !== "all" ||
            statusFilter !== "all" ||
            standardFilter !== "all"
              ? "Thử thay đổi từ khóa tìm kiếm hoặc đặt lại các bộ lọc nhóm / tiêu chuẩn."
              : "Khởi tạo loại văn bản mới hoặc nhấn 'Đồng bộ' để nạp 37+ loại văn bản chuẩn theo NĐ 30/2020."
          }
          action={{
            label: "Thêm loại văn bản",
            onClick: () => setIsCreateOpen(true),
          }}
          secondaryAction={{
            label: "Đồng bộ chuẩn",
            onClick: () => syncMutation.mutate(),
          }}
        />
      ) : viewMode === "grid" ? (
        /* Cards Grid View: 1 col on mobile, 2 on tablet, 4 on desktop */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {items.map((item) => (
            <DocumentTypeCard
              key={item.code}
              item={item}
              onOpen={() =>
                navigate({
                  to: "/document-types/$code",
                  params: { code: item.code },
                })
              }
              onEdit={() =>
                navigate({
                  to: "/document-types/$code",
                  params: { code: item.code },
                })
              }
              onToggleActive={(active) =>
                toggleActiveMutation.mutate({ code: item.code, active })
              }
              isToggling={toggleActiveMutation.isPending}
            />
          ))}
        </div>
      ) : (
        /* Table View */
        <Card className="overflow-hidden border border-border/80 shadow-2xs">
          <div className="w-full overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="h-10 hover:bg-transparent">
                  <TableHead className="w-[260px] text-xs">
                    Mã chuẩn & Thể thức
                  </TableHead>
                  <TableHead className="text-xs">Nhóm phân loại</TableHead>
                  <TableHead className="text-xs text-center w-[120px]">
                    Chuẩn NĐ 30
                  </TableHead>
                  <TableHead className="text-xs">Thời hạn lưu trữ</TableHead>
                  <TableHead className="text-xs text-center w-[110px]">
                    Ưu tiên RAG
                  </TableHead>
                  <TableHead className="text-xs text-center w-[100px]">
                    Tài liệu
                  </TableHead>
                  <TableHead className="text-xs text-center w-[90px]">
                    Hoạt động
                  </TableHead>
                  <TableHead className="text-xs text-right w-[110px]">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => {
                  const Icon = getCategoryIcon(item.category);
                  return (
                    <TableRow
                      key={item.code}
                      className="h-11 hover:bg-muted/40 transition-colors"
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2.5">
                          <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
                            <Icon className="size-3.5" />
                          </div>
                          <div className="min-w-0">
                            <button
                              type="button"
                              onClick={() =>
                                navigate({
                                  to: "/document-types/$code",
                                  params: { code: item.code },
                                })
                              }
                              className="font-semibold text-foreground hover:text-primary transition-colors text-xs text-left truncate block max-w-[200px]"
                            >
                              {item.name}
                            </button>
                            <span className="font-mono text-[10px] text-muted-foreground block truncate">
                              {item.code}
                            </span>
                          </div>
                        </div>
                      </TableCell>

                      <TableCell>
                        <Badge variant="outline" className="text-[10px] h-5">
                          {formatCategoryLabel(item.category)}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-center">
                        {item.nd30 ? (
                          <Badge
                            variant="secondary"
                            className="bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/20 text-[10px] gap-1 h-5 inline-flex"
                          >
                            <Check className="size-2.5" />
                            <span>NĐ 30</span>
                          </Badge>
                        ) : (
                          <span className="text-[11px] text-muted-foreground inline-flex items-center gap-1">
                            <X className="size-3" />
                            <span>Nội bộ</span>
                          </span>
                        )}
                      </TableCell>

                      <TableCell className="text-xs text-foreground">
                        {item.retention_period || "Theo quy định"}
                      </TableCell>

                      <TableCell className="text-center">
                        <span className="font-mono text-xs font-semibold text-primary">
                          {item.priority}/10
                        </span>
                      </TableCell>

                      <TableCell className="text-center font-mono text-xs text-muted-foreground">
                        {item.doc_count || 0}
                      </TableCell>

                      <TableCell className="text-center">
                        <Switch
                          checked={item.is_active}
                          disabled={toggleActiveMutation.isPending}
                          onCheckedChange={(checked) =>
                            toggleActiveMutation.mutate({
                              code: item.code,
                              active: checked,
                            })
                          }
                          aria-label={`Trạng thái ${item.name}`}
                        />
                      </TableCell>

                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            onClick={() =>
                              navigate({
                                to: "/document-types/$code",
                                params: { code: item.code },
                              })
                            }
                            title="Chi tiết"
                          >
                            <Settings className="size-3 text-primary" />
                            <span className="sr-only">Chi tiết</span>
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0"
                              >
                                <MoreHorizontal className="size-3" />
                                <span className="sr-only">Thao tác</span>
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                              align="end"
                              className="w-40 text-xs"
                            >
                              <DropdownMenuItem
                                onClick={() =>
                                  navigate({
                                    to: "/document-types/$code",
                                    params: { code: item.code },
                                  })
                                }
                              >
                                <FileCheck2 className="size-3.5 mr-2 text-primary" />
                                <span>Chỉnh sửa</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleCopyCode(item.code)}
                              >
                                <Copy className="size-3.5 mr-2 text-primary" />
                                <span>Sao chép mã</span>
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => navigate({ to: "/knowledge" })}
                              >
                                <GraduationCap className="size-3.5 mr-2 text-primary" />
                                <span>Kho tri thức</span>
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

      {/* Modal Thêm Loại Mới */}
      <CreateDocumentTypeDialog
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
      />
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  BookOpen,
  Database,
  FileText,
  Layers,
  MoreVertical,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { CollectionConfigDialog } from "@/components/knowledge/dialogs/collection-config-dialog";
import { CollectionReconcileDialog } from "@/components/knowledge/dialogs/collection-reconcile-dialog";
import { DocumentUploadDialog } from "@/components/knowledge/dialogs/document-upload-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { knowledgeApi } from "@/services/knowledge-api";
import type {
  KnowledgeCollection,
  KnowledgeReconciliationReport,
} from "@/types/knowledge";

export const KnowledgePage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [strategyFilter, setStrategyFilter] = useState("all");
  const [ocrFilter, setOcrFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // Dialog States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createCode, setCreateCode] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [createStrategy, setCreateStrategy] = useState("SemanticChunker");
  const [createOcr, setCreateOcr] = useState("PyMuPDF");

  // Edit Collection Dialog State
  const [editTarget, setEditTarget] = useState<KnowledgeCollection | null>(
    null,
  );
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");

  // Upload Dialog State
  const [uploadTarget, setUploadTarget] = useState<KnowledgeCollection | null>(
    null,
  );

  // Delete Dialog State
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeCollection | null>(
    null,
  );

  // Reconcile Dialog State
  const [reconcileTarget, setReconcileTarget] =
    useState<KnowledgeCollection | null>(null);
  const [reconcileReport, setReconcileReport] =
    useState<KnowledgeReconciliationReport | null>(null);
  const [isLoadingReconcile, setIsLoadingReconcile] = useState(false);
  const [isFixingReconcile, setIsFixingReconcile] = useState(false);

  // Fetch Collections
  const {
    data: collections = [],
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["collections"],
    queryFn: () => knowledgeApi.getCollections(),
  });

  // Calculate Metrics
  const metrics = useMemo(() => {
    const totalCols = collections.length;
    const totalDocs = collections.reduce(
      (acc, c) => acc + (c.document_count || 0),
      0,
    );
    const totalChunks = collections.reduce(
      (acc, c) => acc + (c.chunk_count || 0),
      0,
    );
    return { totalCols, totalDocs, totalChunks };
  }, [collections]);

  // Filtered Collections
  const filteredCollections = useMemo(() => {
    return collections.filter((col) => {
      const q = searchQuery.toLowerCase().trim();
      const matchSearch =
        !q ||
        col.name.toLowerCase().includes(q) ||
        col.code.toLowerCase().includes(q) ||
        col.description.toLowerCase().includes(q);

      const matchStrategy =
        strategyFilter === "all" || col.chunking_strategy === strategyFilter;

      const matchOcr = ocrFilter === "all" || col.ocr_profile === ocrFilter;

      return matchSearch && matchStrategy && matchOcr;
    });
  }, [collections, searchQuery, strategyFilter, ocrFilter]);

  // Create Collection Mutation
  const createMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.createCollection({
        name: createName.trim(),
        code: createCode.trim() || undefined,
        description: createDescription.trim() || undefined,
        chunking_strategy: createStrategy,
        ocr_profile: createOcr,
      }),
    onSuccess: (newCol) => {
      toast.success(`Đã tạo kho tri thức: ${newCol.name}`);
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      setIsCreateOpen(false);
      resetCreateForm();
    },
    onError: (err: Error) => {
      toast.error(`Tạo kho thất bại: ${err.message}`);
    },
  });

  // Edit Collection Mutation
  const editMutation = useMutation({
    mutationFn: () => {
      if (!editTarget) throw new Error("Chưa chọn kho cần sửa.");
      return knowledgeApi.updateCollection(editTarget.id, {
        name: editName.trim() || undefined,
        description: editDescription.trim() || undefined,
      });
    },
    onSuccess: () => {
      toast.success("Cập nhật thông tin kho thành công.");
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      setEditTarget(null);
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật thất bại: ${err.message}`);
    },
  });

  // Delete Collection Mutation
  const deleteMutation = useMutation({
    mutationFn: (collectionId: string) =>
      knowledgeApi.deleteCollection(collectionId),
    onSuccess: () => {
      toast.success("Đã xóa kho tri thức.");
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      setDeleteTarget(null);
    },
    onError: (err: Error) => {
      toast.error(`Xóa kho thất bại: ${err.message}`);
    },
  });

  const resetCreateForm = () => {
    setCreateName("");
    setCreateCode("");
    setCreateDescription("");
    setCreateStrategy("SemanticChunker");
    setCreateOcr("PyMuPDF");
  };

  const handleOpenEdit = (col: KnowledgeCollection) => {
    setEditTarget(col);
    setEditName(col.name);
    setEditDescription(col.description);
  };

  const handleOpenReconcile = async (col: KnowledgeCollection) => {
    setReconcileTarget(col);
    setIsLoadingReconcile(true);
    setReconcileReport(null);
    try {
      const rep = await knowledgeApi.getReconciliationReport(col.id);
      setReconcileReport(rep);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Đối soát dữ liệu thất bại.",
      );
    } finally {
      setIsLoadingReconcile(false);
    }
  };

  const handleFixReconcile = async () => {
    if (!reconcileTarget) return;
    setIsFixingReconcile(true);
    try {
      const res = await knowledgeApi.fixReconciliation(reconcileTarget.id);
      toast.success(
        res.message || "Đã đồng bộ và dọn dẹp vector mồ côi thành công.",
      );
      const rep = await knowledgeApi.getReconciliationReport(
        reconcileTarget.id,
      );
      setReconcileReport(rep);
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Đồng bộ thất bại.");
    } finally {
      setIsFixingReconcile(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Actions */}
      <PageHeader
        title="Kho Tri Thức"
        description="Quản lý các bộ sưu tập tài liệu, bóc tách OCR, vector hóa BGE-M3 và số liệu facts phục vụ RAG."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading || isRefetching}
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw
                className={`size-3.5 ${isRefetching ? "animate-spin text-primary" : ""}`}
              />
              <span>Làm mới</span>
            </Button>
            <Button
              size="sm"
              onClick={() => setIsCreateOpen(true)}
              className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs"
            >
              <Plus className="size-3.5" />
              <span>Thêm kho</span>
            </Button>
          </div>
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={BookOpen}
            label="Kho tri thức"
            value={metrics.totalCols.toLocaleString("vi-VN")}
            helper="Bộ sưu tập đang hoạt động"
          />
          <KpiMetric
            icon={FileText}
            label="Văn bản bóc tách"
            value={metrics.totalDocs.toLocaleString("vi-VN")}
            helper="Tài liệu PDF, DOCX, XLSX"
          />
          <KpiMetric
            icon={Layers}
            label="Vector Chunks"
            value={metrics.totalChunks.toLocaleString("vi-VN")}
            helper="Chỉ mục BGE-M3 (1024D)"
          />
          <KpiMetric
            icon={Database}
            label="Cơ sở dữ liệu"
            value="Qdrant + Postgres"
            helper="Hybrid Search RRF k=60"
          />
        </CardContent>
      </Card>

      {/* 3. Filter Bar & View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm theo tên hoặc mã kho..."
              className="h-8 pl-8 text-xs"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full lg:w-auto">
          {/* Strategy filter */}
          <Select value={strategyFilter} onValueChange={setStrategyFilter}>
            <SelectTrigger className="h-8 text-xs w-full sm:w-[155px]">
              <SelectValue placeholder="Chiến lược" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi chiến lược</SelectItem>
              <SelectItem value="ClauseBasedChunker">
                Theo Điều/Khoản
              </SelectItem>
              <SelectItem value="SemanticChunker">Theo Ngữ nghĩa</SelectItem>
            </SelectContent>
          </Select>

          {/* OCR Engine filter */}
          <Select value={ocrFilter} onValueChange={setOcrFilter}>
            <SelectTrigger className="h-8 text-xs w-full sm:w-[155px]">
              <SelectValue placeholder="Bộ máy OCR" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi bộ máy OCR</SelectItem>
              <SelectItem value="PyMuPDF">PyMuPDF</SelectItem>
              <SelectItem value="Docling">Docling</SelectItem>
              <SelectItem value="EasyOCR">EasyOCR</SelectItem>
            </SelectContent>
          </Select>

          {/* View Mode Toggle */}
          <div className="col-span-2 sm:col-span-1 flex items-center border border-border rounded-md p-0.5 bg-muted/30">
            <Button
              variant={viewMode === "grid" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("grid")}
              className="h-7 px-2.5 text-xs rounded-xs flex-1 sm:flex-initial"
              title="Xem dạng thẻ"
            >
              Thẻ
            </Button>
            <Button
              variant={viewMode === "table" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("table")}
              className="h-7 px-2.5 text-xs rounded-xs flex-1 sm:flex-initial"
              title="Xem dạng bảng"
            >
              Bảng
            </Button>
          </div>
        </div>
      </div>

      {/* 4. Collections Display */}
      {isLoading ? (
        <div className="py-16 text-center space-y-3">
          <RefreshCw className="size-6 animate-spin mx-auto text-primary" />
          <p className="text-xs text-muted-foreground">
            Đang tải danh sách kho tri thức...
          </p>
        </div>
      ) : filteredCollections.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="Không tìm thấy kho tri thức"
          description={
            searchQuery
              ? `Không có kết quả khớp với từ khóa "${searchQuery}".`
              : "Chưa có bộ sưu tập tri thức nào. Hãy nhấn 'Thêm kho' để bắt đầu."
          }
          action={{
            label: "Thêm kho mới",
            onClick: () => setIsCreateOpen(true),
          }}
        />
      ) : viewMode === "grid" ? (
        /* Cards Grid View: 1 col on mobile, 2 on tablet, 4 on desktop */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {filteredCollections.map((col) => (
            <Card
              key={col.id}
              className="flex flex-col justify-between border-border/80 hover:border-primary/40 hover:shadow-xs transition-all duration-200"
            >
              {/* Card Header */}
              <div className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                      <BookOpen className="size-4" />
                    </div>
                    <div>
                      <h3>
                        <button
                          type="button"
                          onClick={() =>
                            navigate({ to: `/knowledge/${col.id}` })
                          }
                          className="text-left font-bold text-foreground hover:text-primary cursor-pointer line-clamp-1 transition-colors text-sm"
                          title={col.name}
                        >
                          {col.name}
                        </button>
                      </h3>
                      <span className="font-mono text-[11px] text-muted-foreground bg-muted px-1.5 py-0.2 rounded">
                        {col.code}
                      </span>
                    </div>
                  </div>

                  {/* Actions Dropdown */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground hover:text-foreground"
                      >
                        <MoreVertical className="size-3.5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="text-xs">
                      <DropdownMenuItem
                        onClick={() => navigate({ to: `/knowledge/${col.id}` })}
                        className="gap-2"
                      >
                        <ArrowRight className="size-3.5 text-primary" />
                        <span>Xem chi tiết</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setUploadTarget(col)}
                        className="gap-2"
                      >
                        <Upload className="size-3.5 text-primary" />
                        <span>Nạp tài liệu</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleOpenReconcile(col)}
                        className="gap-2"
                      >
                        <ShieldCheck className="size-3.5 text-success" />
                        <span>Đối soát</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleOpenEdit(col)}
                        className="gap-2"
                      >
                        <Pencil className="size-3.5" />
                        <span>Sửa</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => setDeleteTarget(col)}
                        className="gap-2 text-destructive focus:text-destructive"
                      >
                        <Trash2 className="size-3.5" />
                        <span>Xóa kho</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed min-h-[32px]">
                  {col.description ||
                    "Kho lưu trữ tài liệu nghiệp vụ QNU AI Platform."}
                </p>

                {/* Badges / Specs */}
                <div className="pt-2 border-t border-border/60 flex flex-wrap gap-1.5">
                  <Badge
                    variant="outline"
                    className="text-[11px] font-mono gap-1"
                  >
                    <FileText className="size-3 text-muted-foreground" />
                    <span>{col.document_count || 0} tài liệu</span>
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-[11px] font-mono gap-1"
                  >
                    <Layers className="size-3 text-muted-foreground" />
                    <span>{col.chunk_count || 0} chunks</span>
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-[11px] text-primary border-primary/20 bg-primary/5"
                  >
                    {col.chunking_strategy === "ClauseBasedChunker"
                      ? "Điều/Khoản"
                      : "Ngữ nghĩa"}
                  </Badge>
                </div>
              </div>

              {/* Card Footer */}
              <div className="p-3 bg-muted/20 border-t border-border/60 flex items-center justify-between gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setUploadTarget(col)}
                  className="h-7 text-xs gap-1.5 flex-1"
                >
                  <Upload className="size-3" />
                  <span>Nạp tài liệu</span>
                </Button>

                <Button
                  size="sm"
                  onClick={() => navigate({ to: `/knowledge/${col.id}` })}
                  className="h-7 text-xs gap-1.5 flex-1 bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/20 transition-colors cursor-pointer"
                >
                  <span>Mở kho</span>
                  <ArrowRight className="size-3" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="w-full overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow className="h-10 text-xs">
                <TableHead>Tên kho & Mã</TableHead>
                <TableHead>Mô tả</TableHead>
                <TableHead className="text-center">Tài liệu</TableHead>
                <TableHead className="text-center">Chunks</TableHead>
                <TableHead>Chiến lược Chunk</TableHead>
                <TableHead>Bộ máy OCR</TableHead>
                <TableHead className="text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-xs">
              {filteredCollections.map((col) => (
                <TableRow key={col.id} className="h-11">
                  <TableCell className="font-medium">
                    <button
                      type="button"
                      onClick={() => navigate({ to: `/knowledge/${col.id}` })}
                      className="text-left font-bold text-foreground hover:text-primary transition-colors block"
                    >
                      {col.name}
                    </button>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {col.code}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-xs truncate">
                    {col.description}
                  </TableCell>
                  <TableCell className="text-center font-mono">
                    {col.document_count || 0}
                  </TableCell>
                  <TableCell className="text-center font-mono">
                    {col.chunk_count || 0}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[11px]">
                      {col.chunking_strategy}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[11px]">
                      {col.ocr_profile}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setUploadTarget(col)}
                        className="h-7 text-xs px-2"
                        title="Nạp tài liệu"
                      >
                        <Upload className="size-3 text-primary" />
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => navigate({ to: `/knowledge/${col.id}` })}
                        className="h-7 text-xs px-2.5 gap-1 bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        <span>Mở</span>
                        <ArrowRight className="size-3" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 5. Dialog: Tạo Kho Tri Thức Mới */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <Plus className="size-4 text-primary" />
              <span>Thêm kho tri thức mới</span>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <label
                htmlFor="create-col-name"
                className="text-xs font-semibold text-foreground block"
              >
                Tên kho tri thức <span className="text-destructive">*</span>
              </label>
              <Input
                id="create-col-name"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="VD: Kho Tri Thức Tuyển Sinh Đại Học 2026..."
                className="h-9 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="create-col-code"
                className="text-xs font-semibold text-foreground block"
              >
                Mã định danh (Code)
              </label>
              <Input
                id="create-col-code"
                value={createCode}
                onChange={(e) => setCreateCode(e.target.value)}
                placeholder="VD: col_admissions_2026 (để trống sẽ tự sinh)"
                className="h-9 text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="create-col-desc"
                className="text-xs font-semibold text-foreground block"
              >
                Mô tả nghiệp vụ
              </label>
              <Input
                id="create-col-desc"
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="Mô tả phạm vi văn bản lưu trữ trong kho..."
                className="h-9 text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label
                  htmlFor="create-col-strategy"
                  className="text-xs font-semibold text-foreground block"
                >
                  Chiến lược Chunking
                </label>
                <Select
                  value={createStrategy}
                  onValueChange={setCreateStrategy}
                >
                  <SelectTrigger
                    id="create-col-strategy"
                    className="h-9 text-xs"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SemanticChunker">
                      Theo Ngữ Nghĩa
                    </SelectItem>
                    <SelectItem value="ClauseBasedChunker">
                      Theo Điều/Khoản
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="create-col-ocr"
                  className="text-xs font-semibold text-foreground block"
                >
                  Bộ máy OCR Mặc Định
                </label>
                <Select value={createOcr} onValueChange={setCreateOcr}>
                  <SelectTrigger id="create-col-ocr" className="h-9 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PyMuPDF">PyMuPDF (Nhanh)</SelectItem>
                    <SelectItem value="Docling">Docling (Bảng)</SelectItem>
                    <SelectItem value="EasyOCR">EasyOCR (Đa ngữ)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCreateOpen(false)}
              disabled={createMutation.isPending}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={!createName.trim() || createMutation.isPending}
              className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="size-3.5" />
              <span>
                {createMutation.isPending ? "Đang tạo..." : "Tạo kho"}
              </span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 6. Dialog: Sửa Kho Tri Thức */}
      {editTarget && (
        <CollectionConfigDialog
          open={Boolean(editTarget)}
          onOpenChange={(v) => {
            if (!v) setEditTarget(null);
          }}
          configName={editName}
          setConfigName={setEditName}
          configDescription={editDescription}
          setConfigDescription={setEditDescription}
          isSaving={editMutation.isPending}
          onSave={() => editMutation.mutate()}
        />
      )}

      {/* 7. Dialog: Nạp Tài Liệu */}
      {uploadTarget && (
        <DocumentUploadDialog
          open={Boolean(uploadTarget)}
          onOpenChange={(v) => {
            if (!v) setUploadTarget(null);
          }}
          collectionId={uploadTarget.id}
          collectionName={uploadTarget.name}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ["collections"] });
          }}
        />
      )}

      {/* 8. Dialog: Đối Soát Kho */}
      {reconcileTarget && (
        <CollectionReconcileDialog
          open={Boolean(reconcileTarget)}
          onOpenChange={(v) => {
            if (!v) setReconcileTarget(null);
          }}
          collectionCode={reconcileTarget.code}
          reconcileReport={reconcileReport}
          isLoading={isLoadingReconcile}
          isFixing={isFixingReconcile}
          onRefresh={() => handleOpenReconcile(reconcileTarget)}
          onFix={handleFixReconcile}
        />
      )}

      {/* 9. Dialog: Xác Nhận Xóa Kho */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(v) => {
          if (!v) setDeleteTarget(null);
        }}
        title="Xóa kho tri thức"
        description={`Bạn có chắc chắn muốn xóa kho "${deleteTarget?.name}"? Toàn bộ tài liệu, vector chunks và facts liên kết sẽ bị xóa vĩnh viễn.`}
        confirmText="Xóa vĩnh viễn"
        cancelText="Hủy"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
};

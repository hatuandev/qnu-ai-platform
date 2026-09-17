import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Cpu,
  Download,
  Eye,
  FileText,
  RefreshCw,
  Scan,
  Search,
  Settings,
  Terminal,
  Trash2,
  Upload,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  type IngestionTask,
  type KnowledgeCollection,
  type KnowledgeDocument,
  apiClient,
} from "../services/api-client";
import { DocumentIngestPage } from "./document-ingest-page";
import { DocumentVerificationStudioPage } from "./document-verification-studio-page";

export interface CollectionDetailPageProps {
  collectionId: string;
  onBack: () => void;
  onNavigate?: (path: string) => void;
  initialSubView?: "list" | "ingest" | "verify";
  initialVerifyDocId?: string;
}

export const CollectionDetailPage: React.FC<CollectionDetailPageProps> = ({
  collectionId,
  onBack,
  onNavigate: _onNavigate,
  initialSubView = "list",
  initialVerifyDocId,
}) => {
  const queryClient = useQueryClient();

  // Subview navigation: "list" | "ingest" | "verify"
  const [subView, setSubView] = useState<"list" | "ingest" | "verify">(initialSubView);
  const [verifyDocId, setVerifyDocId] = useState<string>(initialVerifyDocId || "");

  // Tabs on List view: "documents" | "tasks" | "playground"
  const [detailTab, setDetailTab] = useState<string>("documents");

  // Filter & Search states
  const [docSearchQuery, setDocSearchQuery] = useState<string>("");
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("all");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("all");
  const [selectedPriorityFilter, setSelectedPriorityFilter] = useState<string>("all");

  const [taskSearchQuery, setTaskSearchQuery] = useState<string>("");
  const [taskStatusFilter, setTaskStatusFilter] = useState<string>("all");

  // Dialog preview doc state
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDocument | null>(null);
  const [selectedTaskLog, setSelectedTaskLog] = useState<IngestionTask | null>(null);

  // Reindex state
  const [isReindexing, setIsReindexing] = useState<boolean>(false);
  const [reindexSuccess, setReindexSuccess] = useState<boolean>(false);

  // Playground state
  const [sandboxQuery, setSandboxQuery] = useState<string>("");
  const [isSearchingSandbox, setIsSearchingSandbox] = useState<boolean>(false);
  const [sandboxResults, setSandboxResults] = useState<
    | { id: string; title: string; clause: string; text: string; score: number; method: string }[]
    | null
  >(null);

  // Fetch collections
  const { data: collections = [] } = useQuery({
    queryKey: ["collections"],
    queryFn: () => apiClient.getCollections(),
  });

  const currentCollection = useMemo<KnowledgeCollection>(() => {
    const found = collections.find((c) => c.id === collectionId || c.code === collectionId);
    if (found) return found;
    return {
      id: collectionId,
      code: "admissions",
      name: "Kho Tri thức Tuyển sinh Đại học",
      description:
        "Lưu trữ đề án tuyển sinh, điểm chuẩn, tổ hợp xét tuyển và chỉ tiêu hàng năm của Đại học Quy Nhơn.",
      document_count: 1,
      chunk_count: 10,
      chunking_strategy: "SemanticChunker",
      ocr_profile: "Docling",
      embedding_model: "BAAI/bge-m3 (1024-dim)",
      status: "ready",
      updated_at: "19:48 12/09/2026",
    };
  }, [collections, collectionId]);

  // Fetch documents for this collection
  const { data: allDocuments = [] } = useQuery({
    queryKey: ["documents", currentCollection.id],
    queryFn: () => apiClient.getDocuments(currentCollection.id),
  });

  // Fetch ingestion tasks
  const { data: allTasks = [] } = useQuery({
    queryKey: ["ingestion-tasks", currentCollection.id],
    queryFn: () => apiClient.getIngestionTasks(currentCollection.id),
  });

  // Filtered documents
  const filteredDocuments = useMemo(() => {
    return allDocuments.filter((d) => {
      const matchSearch =
        !docSearchQuery.trim() ||
        d.title.toLowerCase().includes(docSearchQuery.toLowerCase()) ||
        d.filename.toLowerCase().includes(docSearchQuery.toLowerCase());
      const matchType =
        selectedTypeFilter === "all" || (d.document_type || "Quy chế") === selectedTypeFilter;
      const matchStatus =
        selectedStatusFilter === "all" || (d.status || "completed") === selectedStatusFilter;
      const matchPriority =
        selectedPriorityFilter === "all" || (d.priority_level || "core") === selectedPriorityFilter;
      return matchSearch && matchType && matchStatus && matchPriority;
    });
  }, [
    allDocuments,
    docSearchQuery,
    selectedTypeFilter,
    selectedStatusFilter,
    selectedPriorityFilter,
  ]);

  // Filtered tasks
  const filteredTasks = useMemo(() => {
    return allTasks.filter((t) => {
      const matchSearch =
        !taskSearchQuery.trim() ||
        t.task_name.toLowerCase().includes(taskSearchQuery.toLowerCase()) ||
        t.source_file.toLowerCase().includes(taskSearchQuery.toLowerCase()) ||
        t.worker_name.toLowerCase().includes(taskSearchQuery.toLowerCase());
      const matchStatus = taskStatusFilter === "all" || t.status === taskStatusFilter;
      return matchSearch && matchStatus;
    });
  }, [allTasks, taskSearchQuery, taskStatusFilter]);

  const handleReindex = () => {
    setIsReindexing(true);
    setTimeout(() => {
      setIsReindexing(false);
      setReindexSuccess(true);
      setTimeout(() => setReindexSuccess(false), 3000);
    }, 1200);
  };

  const handleSandboxSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sandboxQuery.trim()) return;
    setIsSearchingSandbox(true);
    setTimeout(() => {
      setIsSearchingSandbox(false);
      setSandboxResults([
        {
          id: "chunk_01",
          title: currentCollection.name,
          clause: "Mục II, Khoản 2 (Phương thức tuyển sinh)",
          text: "Phương thức 1 (PT1 - mã 100): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026. Phương thức 2 (PT2 - mã 200): Xét kết quả học tập 3 năm THPT. Phương thức 3 & 4: Xét ĐGNL ĐHQG TP.HCM và ĐH Sư phạm Hà Nội.",
          score: 0.962,
          method: "Hybrid RRF (Dense BGE-M3 + Postgres FTS)",
        },
        {
          id: "chunk_02",
          title: currentCollection.name,
          clause: "Phụ lục 01, Bảng mã ngành",
          text: "Ngành Quản lý giáo dục (Mã ngành: 7140114): Chỉ tiêu 60 sinh viên. Tổ hợp xét tuyển: (Văn, Sử, Địa), (Văn, Sử, GD KT&PL), (Văn, Địa, GD KT&PL), (Văn, Toán, GD KT&PL).",
          score: 0.915,
          method: "TableFormer Structured Cell Search",
        },
      ]);
    }, 500);
  };

  const formatFileSize = (bytes: number) => {
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  // SUBVIEW 1: INGEST FORM
  if (subView === "ingest") {
    return (
      <DocumentIngestPage
        collection={currentCollection}
        onBack={() => setSubView("list")}
        onStartVerification={(docId) => {
          setVerifyDocId(docId);
          setSubView("verify");
        }}
      />
    );
  }

  // SUBVIEW 2: SPLIT-PANE VERIFICATION STUDIO
  if (subView === "verify") {
    return (
      <DocumentVerificationStudioPage
        collectionId={currentCollection.id}
        documentId={verifyDocId || allDocuments[0]?.id || "doc_ts_2026"}
        onBackToConfig={() => setSubView("ingest")}
        onCommitSuccess={() => {
          setSubView("list");
          queryClient.invalidateQueries({ queryKey: ["documents"] });
          queryClient.invalidateQueries({ queryKey: ["collections"] });
        }}
      />
    );
  }

  // SUBVIEW 3: MASTER DETAIL VIEW WITH 3 TABS
  return (
    <div className="space-y-6">
      {/* Top Header Card matching Screenshot 2 */}
      <div className="bg-card border border-border rounded-lg p-5 sm:p-6 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={onBack}
              className="size-9 rounded-md shrink-0 text-muted-foreground hover:text-foreground"
              title="Quay lại danh sách kho"
            >
              <ArrowLeft className="size-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-lg sm:text-xl font-bold text-foreground">
                  {currentCollection.name}
                </h1>
                <Badge
                  variant="outline"
                  className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 font-medium text-[11px]"
                >
                  Sẵn sàng
                </Badge>
                <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  {currentCollection.code}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {currentCollection.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReindex}
              disabled={isReindexing}
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw
                className={`size-3.5 ${isReindexing ? "animate-spin text-primary" : ""}`}
              />
              <span>{isReindexing ? "Đang Reindex..." : "Reindex Kho"}</span>
            </Button>

            <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5">
              <Settings className="size-3.5" />
              <span>Cấu hình</span>
            </Button>

            <Button
              size="sm"
              onClick={() => setSubView("ingest")}
              className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
            >
              <Upload className="size-3.5" />
              <span>+ Nạp tài liệu</span>
            </Button>
          </div>
        </div>

        {/* Sub Meta Info Line */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/60 flex-wrap">
          <span className="flex items-center gap-1 font-mono text-[11px] text-primary">
            <Cpu className="size-3.5" />
            {currentCollection.embedding_model || "BAAI/bge-m3 (1024-dim)"}
          </span>
          <span>•</span>
          <span className="text-[11px]">Cập nhật: {currentCollection.updated_at}</span>
          <span>•</span>
          <span className="text-[11px] font-medium text-foreground">
            {allDocuments.length} văn bản ({currentCollection.chunk_count} chunks)
          </span>
          {reindexSuccess && (
            <span className="text-[11px] text-emerald-600 font-semibold ml-auto flex items-center gap-1">
              <CheckCircle2 className="size-3.5" /> Đã đồng bộ Vector Qdrant thành công!
            </span>
          )}
        </div>
      </div>

      {/* 3 Main Sub-Tabs */}
      <Tabs value={detailTab} onValueChange={setDetailTab} className="space-y-4">
        <TabsList className="bg-muted/60 p-1 rounded-md border border-border">
          <TabsTrigger value="documents" className="text-xs px-3.5 py-1.5 gap-1.5">
            <FileText className="size-3.5" />
            <span>Danh mục Tài liệu ({allDocuments.length})</span>
          </TabsTrigger>
          <TabsTrigger value="tasks" className="text-xs px-3.5 py-1.5 gap-1.5">
            <Activity className="size-3.5" />
            <span>Tiến trình & Lịch sử Tác vụ ({allTasks.length})</span>
          </TabsTrigger>
          <TabsTrigger value="playground" className="text-xs px-3.5 py-1.5 gap-1.5">
            <Bot className="size-3.5" />
            <span>Hỏi Thử Nghiệm trong Kho (Playground)</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: DANH MỤC TÀI LIỆU */}
        <TabsContent value="documents" className="space-y-4 mt-0">
          {/* Search and Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-lg border border-border">
            <div className="flex items-center gap-2 w-full sm:w-80">
              <Search className="size-4 text-muted-foreground shrink-0" />
              <Input
                placeholder="Tìm tiêu đề, tên tệp..."
                value={docSearchQuery}
                onChange={(e) => setDocSearchQuery(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap justify-end">
              <select
                value={selectedTypeFilter}
                onChange={(e) => setSelectedTypeFilter(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">Tất cả loại văn bản</option>
                <option value="Quy chế">Quy chế</option>
                <option value="Đề án">Đề án</option>
                <option value="Nghị định">Nghị định</option>
              </select>

              <select
                value={selectedStatusFilter}
                onChange={(e) => setSelectedStatusFilter(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">Tất cả trạng thái</option>
                <option value="completed">Hiệu lực</option>
                <option value="processing">Đang xử lý</option>
              </select>

              <select
                value={selectedPriorityFilter}
                onChange={(e) => setSelectedPriorityFilter(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">Tất cả mức ưu tiên</option>
                <option value="core">Ưu tiên Cao (Cốt lõi)</option>
                <option value="high">Ưu tiên Trung bình</option>
              </select>

              <span className="text-xs text-muted-foreground ml-2">
                Hiển thị {filteredDocuments.length} / {allDocuments.length} tài liệu
              </span>
            </div>
          </div>

          {/* Documents Table */}
          <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase">
                  <TableHead className="w-10 text-center">
                    <input type="checkbox" className="rounded border-border size-3.5" />
                  </TableHead>
                  <TableHead>Tài liệu & Tên tệp gốc</TableHead>
                  <TableHead>Loại văn bản</TableHead>
                  <TableHead>Chunks Vector</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocuments.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="h-32 text-center text-xs text-muted-foreground"
                    >
                      Không tìm thấy tài liệu phù hợp trong kho này.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredDocuments.map((doc) => (
                    <TableRow key={doc.id} className="hover:bg-muted/30 transition-colors">
                      <TableCell className="text-center">
                        <input type="checkbox" className="rounded border-border size-3.5" />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-start gap-3">
                          <div className="flex size-8 items-center justify-center rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 shrink-0 mt-0.5">
                            <FileText className="size-4" />
                          </div>
                          <div>
                            <p className="font-semibold text-xs text-foreground hover:text-primary transition-colors cursor-pointer">
                              {doc.title}
                            </p>
                            <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
                              <span>{doc.filename}</span>
                              <span>•</span>
                              <span>{formatFileSize(doc.file_size)}</span>
                              <span>•</span>
                              <span className="text-primary font-medium">
                                {doc.version || "v1.0"}
                              </span>
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <span className="text-xs text-foreground font-medium block">
                            {doc.document_type || "Quy chế"}
                          </span>
                          <Badge
                            variant="outline"
                            className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                          >
                            Ưu tiên Cao (Cốt lõi)
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-xs text-emerald-600 font-mono">
                          {doc.chunk_count} chunks
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="text-[11px] bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-200"
                        >
                          Hiệu lực
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              setVerifyDocId(doc.id);
                              setSubView("verify");
                            }}
                            className="size-7 text-muted-foreground hover:text-primary"
                            title="Mở Studio Bóc Tách & Đối Soát (Split-Pane)"
                          >
                            <Scan className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setPreviewDoc(doc)}
                            className="size-7 text-muted-foreground hover:text-foreground"
                            title="Xem trước Chunks Inspector"
                          >
                            <Eye className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 text-muted-foreground hover:text-foreground"
                            title="Tải tệp gốc"
                          >
                            <Download className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 text-rose-500 hover:text-rose-600"
                            title="Xóa tài liệu"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* TAB 2: TIẾN TRÌNH & LỊCH SỬ TÁC VỤ NGẦM */}
        <TabsContent value="tasks" className="space-y-4 mt-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-lg border border-border">
            <div>
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                Hàng Đợi & Lịch Sử Tác Vụ Ngầm ({allTasks.length})
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Giám sát thời gian thực quá trình Bóc tách (Ingestion), OCR tài liệu và Tái lập chỉ
                mục (Reindex) của kho này.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-8 text-xs text-muted-foreground">
                Dọn dẹp đã xong
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] })}
                className="h-8 text-xs gap-1.5"
              >
                <RefreshCw className="size-3.5" />
                <span>Làm mới</span>
              </Button>
            </div>
          </div>

          {/* Filter Bar for Tasks */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-lg border border-border">
            <div className="flex items-center gap-2 w-full sm:w-80">
              <Search className="size-4 text-muted-foreground shrink-0" />
              <Input
                placeholder="Tìm tác vụ, tệp, worker..."
                value={taskSearchQuery}
                onChange={(e) => setTaskSearchQuery(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={taskStatusFilter}
                onChange={(e) => setTaskStatusFilter(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">Tất cả trạng thái</option>
                <option value="completed">Hoàn tất</option>
                <option value="processing">Đang xử lý</option>
              </select>
              <span className="text-xs text-muted-foreground ml-2">
                Hiển thị {filteredTasks.length} / {allTasks.length} tác vụ
              </span>
            </div>
          </div>

          {/* Tasks Table matching Screenshot 3 */}
          <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase">
                  <TableHead>Tác vụ & Tài nguyên mục tiêu</TableHead>
                  <TableHead>Phân loại</TableHead>
                  <TableHead>Tiến độ</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Thời điểm</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="h-32 text-center text-xs text-muted-foreground"
                    >
                      Không có tác vụ nền nào đang chờ hoặc đã xử lý.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTasks.map((t) => (
                    <TableRow key={t.id} className="hover:bg-muted/30 transition-colors">
                      <TableCell>
                        <div className="flex items-start gap-3">
                          <div className="flex size-8 items-center justify-center rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 shrink-0 mt-0.5">
                            <Upload className="size-4" />
                          </div>
                          <div>
                            <p className="font-semibold text-xs text-foreground">{t.task_name}</p>
                            <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
                              <span>{t.source_file}</span>
                              <span>•</span>
                              <span>Worker: {t.worker_name}</span>
                              <span>•</span>
                              <span>{t.duration_seconds}s</span>
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-foreground">
                          {t.category === "ingestion"
                            ? "Nạp tài liệu"
                            : t.category === "ocr"
                              ? "OCR & Bóc tách"
                              : "Tái lập chỉ mục"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="w-28 space-y-1">
                          <div className="flex justify-between text-[11px] font-mono">
                            <span className="text-emerald-600 font-bold">
                              {t.progress_percent}%
                            </span>
                            <span className="text-muted-foreground">Xong</span>
                          </div>
                          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-600 rounded-full"
                              style={{ width: `${t.progress_percent}%` }}
                            />
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-300 text-[11px] gap-1"
                        >
                          <CheckCircle2 className="size-3" />
                          <span>Hoàn tất</span>
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground font-mono">
                          {t.created_at}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setSelectedTaskLog(t)}
                            className="size-7 font-mono text-xs text-muted-foreground hover:text-foreground"
                            title="Xem nhật ký Terminal"
                          >
                            <Terminal className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 text-rose-500 hover:text-rose-600"
                            title="Xóa bản ghi"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* TAB 3: PLAYGROUND TRONG KHO */}
        <TabsContent value="playground" className="space-y-4 mt-0">
          <Card className="p-5 border-border">
            <form onSubmit={handleSandboxSearch} className="space-y-3">
              <label
                htmlFor="sandbox-query"
                className="text-xs font-semibold text-foreground block"
              >
                Truy vấn thử nghiệm (Hybrid RRF BGE-M3 + PostgreSQL FTS):
              </label>
              <div className="flex gap-2">
                <Input
                  id="sandbox-query"
                  value={sandboxQuery}
                  onChange={(e) => setSandboxQuery(e.target.value)}
                  placeholder="VD: Điểm chuẩn và phương thức xét tuyển ngành Quản lý giáo dục năm 2026..."
                  className="h-9 text-xs"
                />
                <Button
                  type="submit"
                  disabled={isSearchingSandbox}
                  className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground shrink-0"
                >
                  <Search className="size-3.5" />
                  <span>{isSearchingSandbox ? "Đang tìm..." : "Truy vấn"}</span>
                </Button>
              </div>
            </form>

            {sandboxResults && (
              <div className="mt-5 space-y-3 pt-4 border-t border-border">
                <p className="text-xs font-semibold text-foreground">
                  Kết quả truy xuất ({sandboxResults.length} Chunks phù hợp nhất):
                </p>
                {sandboxResults.map((res) => (
                  <div
                    key={res.id}
                    className="p-3 bg-muted/20 border border-border rounded-lg space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-primary">{res.clause}</span>
                      <Badge variant="secondary" className="font-mono text-[10px]">
                        Điểm phù hợp: {res.score}
                      </Badge>
                    </div>
                    <p className="text-xs text-foreground leading-relaxed">{res.text}</p>
                    <p className="text-[10px] text-muted-foreground font-mono">
                      Phương pháp: {res.method}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* Terminal Log Modal for Task */}
      <Dialog open={!!selectedTaskLog} onOpenChange={() => setSelectedTaskLog(null)}>
        <DialogContent className="max-w-2xl bg-slate-950 text-slate-100 font-mono text-xs">
          <DialogHeader>
            <DialogTitle className="text-sm font-mono text-emerald-400 flex items-center gap-2">
              <Terminal className="size-4" />
              <span>Worker Log: {selectedTaskLog?.worker_name}</span>
            </DialogTitle>
          </DialogHeader>
          <pre className="p-4 bg-slate-900 rounded border border-slate-800 text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap">
            {selectedTaskLog?.log_output ||
              "[INFO] Tác vụ đã thực thi thành công không có cảnh báo."}
          </pre>
        </DialogContent>
      </Dialog>

      {/* Document Quick Preview Modal */}
      <Dialog open={!!previewDoc} onOpenChange={() => setPreviewDoc(null)}>
        <DialogContent className="max-w-md text-xs">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <FileText className="size-4 text-primary" />
              <span>{previewDoc?.title}</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="flex justify-between text-muted-foreground font-mono text-[11px] pb-2 border-b border-border">
              <span>Tên tệp: {previewDoc?.filename}</span>
              <span>{previewDoc ? formatFileSize(previewDoc.file_size) : ""}</span>
            </div>
            <p className="text-muted-foreground text-xs leading-relaxed">
              Tài liệu đã được bóc tách và phân đoạn thành công qua engine{" "}
              <strong className="text-foreground">{previewDoc?.ocr_method}</strong> với{" "}
              <strong className="text-primary">{previewDoc?.chunk_count} vector chunks</strong>{" "}
              trong kho tri thức{" "}
              <strong className="text-foreground">{currentCollection.name}</strong>.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

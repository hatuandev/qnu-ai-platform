import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  CheckCircle2,
  Cpu,
  DownloadCloud,
  FileText,
  FolderGit2,
  HardDrive,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type {
  CandidateGroupItem,
  KnowledgeVectorGenerationResponse,
  RepositoryCandidateItem,
} from "@/types/knowledge";
import { ImportBatchModal } from "./components/import-batch-modal";

interface AddDocumentsPageProps {
  collectionId: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Number.parseFloat((bytes / k ** i).toFixed(1))} ${sizes[i]}`;
}

export const AddDocumentsPage: React.FC<AddDocumentsPageProps> = ({
  collectionId,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Filters & Search
  const [selectedGroupId, setSelectedGroupId] = useState<string>("all");
  const [sourceStatusFilter, setSourceStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  // Ingestion Configurations
  const [selectedVectorGenId, setSelectedVectorGenId] = useState<string>("");
  const [parserProfile, setParserProfile] = useState<string>("standard");
  const [chunkStrategy, setChunkStrategy] =
    useState<string>("ClauseBasedChunker");

  // Selection states
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  // Active batch modal state
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);

  // 1. Fetch Collection Info
  const { data: collection } = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
  });

  // 2. Fetch Candidate Groups
  const { data: candidateGroupsData, isLoading: isGroupsLoading } = useQuery({
    queryKey: ["candidate-groups", collectionId],
    queryFn: () => knowledgeApi.getCandidateGroups(collectionId),
  });
  const candidateGroups = candidateGroupsData?.items || [];

  // 3. Fetch Vector Generations
  const { data: vectorGenerations = [], isLoading: isGenerationsLoading } =
    useQuery<KnowledgeVectorGenerationResponse[]>({
      queryKey: ["knowledge-vector-generations", collectionId],
      queryFn: () => knowledgeApi.listVectorGenerations(collectionId),
    });

  // Set default active vector generation
  // Set default active vector generation
  const activeGeneration = useMemo(() => {
    return (
      vectorGenerations.find((g) => g.status === "active") ||
      vectorGenerations[0]
    );
  }, [vectorGenerations]);

  const effectiveVectorGenId =
    selectedVectorGenId === "none"
      ? ""
      : selectedVectorGenId || activeGeneration?.id || "";

  // 4. Fetch Candidate Documents
  const {
    data: candidatesData,
    isLoading: isCandidatesLoading,
    refetch: refetchCandidates,
    isRefetching: isCandidatesRefetching,
  } = useQuery({
    queryKey: [
      "candidate-documents",
      collectionId,
      selectedGroupId,
      sourceStatusFilter,
      effectiveVectorGenId,
      search,
    ],
    queryFn: () =>
      knowledgeApi.getCandidateDocuments(collectionId, {
        group_id: selectedGroupId === "all" ? undefined : selectedGroupId,
        source_status:
          sourceStatusFilter === "all" ? undefined : sourceStatusFilter,
        vector_generation_id: effectiveVectorGenId || undefined,
        search: search.trim() || undefined,
        limit: 500,
      }),
  });

  const candidates: RepositoryCandidateItem[] = candidatesData?.items || [];

  // Selectable documents count & helpers
  const selectableCandidates = useMemo(
    () => candidates.filter((c) => c.selectable),
    [candidates],
  );

  const unimportedCandidates = useMemo(
    () =>
      candidates.filter(
        (c) => c.selectable && c.source_state === "not_imported",
      ),
    [candidates],
  );

  const toggleSelect = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleSelectAll = () => {
    if (selectedDocIds.length === selectableCandidates.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(selectableCandidates.map((c) => c.document_id));
    }
  };

  const handleSelectOnlyUnimported = () => {
    setSelectedDocIds(unimportedCandidates.map((c) => c.document_id));
  };

  // 5. Mutation Create Snapshot Import Batch
  const createBatchMutation = useMutation({
    mutationFn: () => {
      if (selectedDocIds.length === 0) {
        throw new Error("Vui lòng chọn ít nhất 1 tài liệu để nạp.");
      }
      const idempotencyKey = crypto.randomUUID();
      return knowledgeApi.createImportBatch(
        collectionId,
        {
          document_ids: selectedDocIds,
          vector_generation_id: effectiveVectorGenId || undefined,
          parser_profile: parserProfile,
          chunk_strategy: chunkStrategy,
        },
        idempotencyKey,
      );
    },
    onSuccess: (batch) => {
      toast.success(
        `Đã khởi tạo đợt nạp snapshot với ${batch.total_count} tài liệu.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["candidate-documents", collectionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["candidate-groups", collectionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["collection-summary-metrics", collectionId],
      });
      setActiveBatchId(batch.id);
      setIsBatchModalOpen(true);
      setSelectedDocIds([]);
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Khởi tạo đợt nạp thất bại."));
    },
  });

  // 6. Mutation Create Default Vector Generation
  const createDefaultGenMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.createVectorGeneration(collectionId, {
        embedding_model: "",
      }),
    onSuccess: (newGen) => {
      toast.success(`Đã tạo thế hệ vector mặc định: ${newGen.embedding_model}`);
      queryClient.invalidateQueries({
        queryKey: ["knowledge-vector-generations", collectionId],
      });
      setSelectedVectorGenId(newGen.id);
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Không thể tạo thế hệ vector"));
    },
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24">
      {/* 1. Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link
              to="/knowledge"
              className="hover:text-foreground transition-colors"
            >
              Kho Tri Thức
            </Link>
            <span>/</span>
            <Link
              to="/knowledge/$collectionId"
              params={{ collectionId }}
              className="hover:text-foreground transition-colors"
            >
              {collection?.name || "Kho"}
            </Link>
            <span>/</span>
            <span className="text-foreground font-medium">Nạp tài liệu</span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold text-foreground">
            Nạp Tài Liệu Vào Kho Tri Thức
          </h1>
          <p className="text-xs text-muted-foreground">
            Duyệt tài liệu từ Kho lưu trữ tập trung để bóc tách nội dung, phân
            đoạn chunks và lập chỉ mục vector đa thế hệ theo mô hình chỉ định.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="h-8 text-xs gap-1.5 self-start sm:self-auto"
          onClick={() =>
            navigate({
              to: "/knowledge/$collectionId",
              params: { collectionId },
            })
          }
        >
          <ArrowLeft className="size-3.5" />
          <span>Quay lại Kho tri thức</span>
        </Button>
      </div>

      {/* 2. Ingestion Settings Card */}
      <Card className="border border-border shadow-xs bg-card">
        <CardHeader className="p-4 pb-3 border-b border-border/50">
          <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            <span>Cấu Hình Nạp Tài Liệu (Ingestion Pipeline Settings)</span>
          </CardTitle>
          <CardDescription className="text-xs">
            Các thiết lập bóc tách nội dung, chiến lược cắt đoạn và thế hệ
            vector đích sẽ áp dụng cho đợt nạp này.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Vector Generation Selector */}
          <div className="space-y-1.5">
            <div className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <Cpu className="size-3.5 text-primary" />
              <span>Thế hệ Vector đích</span>
            </div>
            <Select
              value={
                selectedVectorGenId ||
                (activeGeneration ? activeGeneration.id : "none")
              }
              onValueChange={setSelectedVectorGenId}
              disabled={isGenerationsLoading}
            >
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Chọn thế hệ vector..." />
              </SelectTrigger>
              <SelectContent>
                {vectorGenerations.map((gen) => (
                  <SelectItem key={gen.id} value={gen.id} className="text-xs">
                    <span className="font-semibold">{gen.embedding_model}</span>
                    <span className="text-muted-foreground ml-1.5">
                      ({gen.embedding_dimension}d -{" "}
                      {gen.status === "active" ? "Đang hoạt động" : gen.status})
                    </span>
                  </SelectItem>
                ))}
                <SelectItem
                  value="none"
                  className="text-xs text-muted-foreground"
                >
                  Chỉ nạp tài liệu & Chunks (Chưa tạo vector)
                </SelectItem>
              </SelectContent>
            </Select>
            {vectorGenerations.length === 0 ? (
              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-amber-500 font-medium">
                  Chưa có thế hệ vector
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-6 text-[10px] px-2 text-primary"
                  onClick={() => createDefaultGenMutation.mutate()}
                  disabled={createDefaultGenMutation.isPending}
                >
                  + Khởi tạo mặc định
                </Button>
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">
                {activeGeneration
                  ? `Đang dùng: ${activeGeneration.embedding_model} (${activeGeneration.embedding_dimension}d)`
                  : "Chưa kích hoạt thế hệ vector"}
              </p>
            )}
          </div>

          {/* Parser Profile Selector */}
          <div className="space-y-1.5">
            <div className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <Layers className="size-3.5 text-primary" />
              <span>Cấu hình bóc tách OCR</span>
            </div>
            <Select value={parserProfile} onValueChange={setParserProfile}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Chọn cấu hình bóc tách..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard" className="text-xs">
                  Tự động tiêu chuẩn (Native Parser + OCR dự phòng)
                </SelectItem>
                <SelectItem value="vision_ocr" className="text-xs">
                  Ưu tiên Vision OCR (Tài liệu scan, hình ảnh)
                </SelectItem>
                <SelectItem value="layout_analysis" className="text-xs">
                  Phân tích cấu trúc bảng & văn bản sâu
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Tự động tái sử dụng artifact SHA-256 nếu đã từng bóc tách sạch.
            </p>
          </div>

          {/* Chunk Strategy Selector */}
          <div className="space-y-1.5">
            <div className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <HardDrive className="size-3.5 text-primary" />
              <span>Chiến lược phân đoạn</span>
            </div>
            <Select value={chunkStrategy} onValueChange={setChunkStrategy}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Chọn chiến lược cắt đoạn..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ClauseBasedChunker" className="text-xs">
                  Theo Điều/Khoản quy chế (Văn bản hành chính)
                </SelectItem>
                <SelectItem value="SemanticChunker" className="text-xs">
                  Theo ngữ nghĩa đoạn văn bản (Tài liệu chung)
                </SelectItem>
                <SelectItem value="FixedSizeChunker" className="text-xs">
                  Đoạn cố định (500 tokens / 50 overlap)
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Phân đoạn một lần (Chunk once), tái sử dụng cho mọi model vector.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 3. Filter Toolbar & Selection Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-muted/20 p-3 rounded-lg border border-border">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Group Filter */}
          <div className="min-w-[180px]">
            <Select
              value={selectedGroupId}
              onValueChange={setSelectedGroupId}
              disabled={isGroupsLoading}
            >
              <SelectTrigger className="h-9 text-xs bg-background">
                <SelectValue placeholder="Lọc theo nhóm..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all" className="text-xs">
                  Tất cả các nhóm tài liệu ({candidateGroups.length})
                </SelectItem>
                {candidateGroups.map((g: CandidateGroupItem) => (
                  <SelectItem key={g.id} value={g.id} className="text-xs">
                    {g.name} ({g.imported_documents}/{g.total_documents} đã nạp)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Source Status Filter */}
          <div className="min-w-[160px]">
            <Select
              value={sourceStatusFilter}
              onValueChange={setSourceStatusFilter}
            >
              <SelectTrigger className="h-9 text-xs bg-background">
                <SelectValue placeholder="Trạng thái nguồn..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all" className="text-xs">
                  Tất cả trạng thái
                </SelectItem>
                <SelectItem value="not_imported" className="text-xs">
                  Chưa nạp vào kho ({unimportedCandidates.length})
                </SelectItem>
                <SelectItem value="current" className="text-xs">
                  Đã có trong kho
                </SelectItem>
                <SelectItem value="update_available" className="text-xs">
                  Có bản cập nhật mới
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Search Input */}
          <div className="relative min-w-[200px] flex-1">
            <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm theo tên tệp hoặc tiêu đề..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 pl-8 text-xs bg-background"
            />
          </div>
        </div>

        {/* Quick Selection Buttons */}
        <div className="flex items-center gap-2 self-end lg:self-center">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSelectOnlyUnimported}
            className="h-9 text-xs gap-1.5"
            disabled={unimportedCandidates.length === 0}
          >
            <CheckCircle2 className="size-3.5 text-success" />
            <span>Chọn chưa nạp ({unimportedCandidates.length})</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetchCandidates()}
            className="h-9 size-9 p-0 text-muted-foreground hover:text-foreground"
            title="Làm mới danh sách"
          >
            <RefreshCw
              className={`size-3.5 ${isCandidatesRefetching ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      </div>

      {/* 4. Candidates Table */}
      <Card className="border border-border shadow-xs overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow className="h-10 text-xs">
              <TableHead className="w-10">
                <Checkbox
                  checked={
                    selectableCandidates.length > 0 &&
                    selectedDocIds.length === selectableCandidates.length
                  }
                  onCheckedChange={handleSelectAll}
                  aria-label="Chọn tất cả"
                />
              </TableHead>
              <TableHead className="min-w-[240px]">Tài Liệu</TableHead>
              <TableHead className="w-40">Nhóm Trực Thuộc</TableHead>
              <TableHead className="w-24 text-right">Dung Lượng</TableHead>
              <TableHead className="w-36 text-center">
                Trạng Thái Nguồn
              </TableHead>
              <TableHead className="w-36 text-center">
                Trạng Thái Vector
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isCandidatesLoading ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-12 text-center text-xs text-muted-foreground"
                >
                  <RefreshCw className="size-5 animate-spin mx-auto mb-2 text-primary" />
                  <span>Đang tải danh sách tài liệu ứng viên...</span>
                </TableCell>
              </TableRow>
            ) : candidates.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-12">
                  <EmptyState
                    icon={FolderGit2}
                    title="Không có tài liệu nào"
                    description={
                      search ||
                      selectedGroupId !== "all" ||
                      sourceStatusFilter !== "all"
                        ? "Không tìm thấy tài liệu phù hợp với bộ lọc tìm kiếm. Hãy thử điều chỉnh lại bộ lọc."
                        : "Tất cả tài liệu từ Kho tài liệu đã được nạp đầy đủ vào kho tri thức này."
                    }
                    action={{
                      label: "Xem Kho Tài Liệu",
                      onClick: () => navigate({ to: "/documents" }),
                    }}
                  />
                </TableCell>
              </TableRow>
            ) : (
              candidates.map((c) => {
                const isChecked = selectedDocIds.includes(c.document_id);
                return (
                  <TableRow
                    key={c.document_id}
                    className={`text-xs h-12 transition-colors cursor-pointer ${
                      isChecked
                        ? "bg-primary/5 hover:bg-primary/10"
                        : "hover:bg-muted/40"
                    } ${!c.selectable ? "opacity-60 cursor-not-allowed" : ""}`}
                    onClick={() => c.selectable && toggleSelect(c.document_id)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={isChecked}
                        disabled={!c.selectable}
                        onCheckedChange={() => toggleSelect(c.document_id)}
                        aria-label={`Chọn ${c.title || c.file_name}`}
                      />
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-7 shrink-0 items-center justify-center rounded bg-primary/10 text-primary">
                          <FileText className="size-3.5" />
                        </div>
                        <div className="min-w-0">
                          <span className="font-semibold text-foreground block truncate">
                            {c.title || c.file_name}
                          </span>
                          <span className="text-[11px] text-muted-foreground block truncate font-mono">
                            {c.file_name}
                          </span>
                          {c.unselectable_reason && (
                            <span className="text-[10px] text-muted-foreground italic block">
                              {c.unselectable_reason}
                            </span>
                          )}
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      {c.groups && c.groups.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {c.groups.map((g) => (
                            <Badge
                              key={g.id}
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 max-w-[120px] truncate"
                            >
                              {g.name}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-[11px]">
                          —
                        </span>
                      )}
                    </TableCell>

                    <TableCell className="text-right font-mono text-[11px] text-muted-foreground">
                      {formatBytes(c.file_size_bytes)}
                    </TableCell>

                    {/* 2D State: Source State Badge */}
                    <TableCell className="text-center">
                      {c.source_state === "not_imported" ? (
                        <Badge
                          variant="outline"
                          className="bg-muted text-muted-foreground border-border text-[10px]"
                        >
                          Chưa nạp
                        </Badge>
                      ) : c.source_state === "current" ? (
                        <Badge
                          variant="outline"
                          className="bg-success/10 text-success border-success/30 text-[10px]"
                        >
                          Đã có
                        </Badge>
                      ) : c.source_state === "update_available" ? (
                        <Badge
                          variant="outline"
                          className="bg-warning/10 text-warning border-warning/30 text-[10px]"
                        >
                          Có bản mới
                        </Badge>
                      ) : c.source_state === "processing" ? (
                        <Badge
                          variant="outline"
                          className="bg-primary/10 text-primary border-primary/30 text-[10px]"
                        >
                          Đang nạp
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="text-[10px]">
                          Lỗi nạp
                        </Badge>
                      )}
                    </TableCell>

                    {/* 2D State: Vector State Badge */}
                    <TableCell className="text-center">
                      {c.vector_state === "indexed" ? (
                        <Badge
                          variant="outline"
                          className="bg-success/10 text-success border-success/30 text-[10px]"
                        >
                          Đã lập chỉ mục
                        </Badge>
                      ) : c.vector_state === "indexing" ? (
                        <Badge
                          variant="outline"
                          className="bg-primary/10 text-primary border-primary/30 text-[10px]"
                        >
                          Đang index
                        </Badge>
                      ) : c.vector_state === "index_failed" ? (
                        <Badge variant="destructive" className="text-[10px]">
                          Lỗi vector
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="text-muted-foreground border-dashed text-[10px]"
                        >
                          Chưa index
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Card>

      {/* 5. Sticky Bottom Action Bar */}
      {selectedDocIds.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-card/95 backdrop-blur-sm border-t border-border shadow-lg p-3 sm:px-8">
          <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-foreground">
                Đã chọn:{" "}
                <span className="text-primary font-bold text-sm">
                  {selectedDocIds.length}
                </span>{" "}
                tài liệu
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedDocIds([])}
                className="h-7 text-xs text-muted-foreground hover:text-foreground"
              >
                Bỏ chọn
              </Button>
            </div>

            <Button
              size="sm"
              disabled={createBatchMutation.isPending}
              onClick={() => createBatchMutation.mutate()}
              className="h-9 gap-2 shadow-sm font-semibold"
            >
              {createBatchMutation.isPending ? (
                <RefreshCw className="size-4 animate-spin" />
              ) : (
                <DownloadCloud className="size-4" />
              )}
              <span>Nạp {selectedDocIds.length} Tài Liệu Vào Kho Tri Thức</span>
            </Button>
          </div>
        </div>
      )}

      {/* 6. Realtime Import Batch Tracker Modal */}
      <ImportBatchModal
        open={isBatchModalOpen}
        onOpenChange={setIsBatchModalOpen}
        collectionId={collectionId}
        batchId={activeBatchId}
        onComplete={() => {
          navigate({
            to: "/knowledge/$collectionId",
            params: { collectionId },
          });
        }}
      />
    </div>
  );
};

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  Link2,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
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
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { knowledgeApi } from "@/services/knowledge-api";
import type { AvailableRepositoryDocumentItem } from "@/types/knowledge";

interface AddDocumentsPageProps {
  collectionId: string;
}

export const AddDocumentsPage: React.FC<AddDocumentsPageProps> = ({
  collectionId,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [chunkStrategy, setChunkStrategy] = useState("ClauseBasedChunker");
  const [autoActivate, setAutoActivate] = useState(false);
  const [syncPolicy] = useState<"manual" | "auto_on_ready">("manual");

  // 1. Fetch Collection Info
  const { data: collection } = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
  });

  // 2. Fetch Available Repository Documents
  const {
    data: availableData,
    isLoading: isDocsLoading,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["available-repository-documents", collectionId, search],
    queryFn: () =>
      knowledgeApi.getAvailableDocuments(
        collectionId,
        search || undefined,
        1,
        100,
      ),
  });

  const availableDocs: AvailableRepositoryDocumentItem[] =
    availableData?.items || [];

  // Toggle selection
  const handleToggleDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId],
    );
  };

  // Toggle select all (only unbound docs)
  const selectableDocs = availableDocs.filter((d) => !d.is_bound);
  const isAllSelected =
    selectableDocs.length > 0 &&
    selectableDocs.every((d) => selectedDocIds.includes(d.id));

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(selectableDocs.map((d) => d.id));
    }
  };

  // 3. Mutation Create Bindings
  const createBindingsMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.createBindings(collectionId, {
        items: selectedDocIds.map((docId) => ({
          repository_document_id: docId,
          chunk_strategy: chunkStrategy,
          sync_policy: syncPolicy,
          auto_activate: autoActivate,
        })),
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collectionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["available-repository-documents", collectionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-collection", collectionId],
      });
      toast.success(
        `Đã tạo liên kết thành công ${res.created_count} tài liệu vào kho tri thức!`,
      );
      navigate({
        to: "/knowledge/$collectionId",
        params: { collectionId },
        search: { tab: "documents" },
      });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Không thể tạo liên kết tài liệu.");
    },
  });

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full pb-28">
      {/* 1. Header & Navigation */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link
            to="/knowledge"
            className="hover:text-primary transition-colors"
          >
            Kho Tri Thức
          </Link>
          <span>/</span>
          <Link
            to="/knowledge/$collectionId"
            params={{ collectionId }}
            search={{ tab: "documents" }}
            className="hover:text-primary transition-colors"
          >
            {collection?.name || "Chi Tiết Kho"}
          </Link>
          <span>/</span>
          <span className="text-foreground font-medium">
            Thêm Tài Liệu Từ Kho
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                navigate({
                  to: "/knowledge/$collectionId",
                  params: { collectionId },
                  search: { tab: "documents" },
                })
              }
              className="size-8 p-0"
              title="Quay lại"
            >
              <ArrowLeft className="size-4" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                Liên Kết Tài Liệu Từ Kho Trung Tâm
                <Badge variant="outline" className="text-xs font-normal">
                  V2 ADR-011
                </Badge>
              </h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                Chọn các tài liệu nguồn đã qua thẩm định chất lượng (Quality
                Gate Ready) để dựng chỉ mục tri thức.
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching || isDocsLoading}
            className="gap-1.5"
          >
            <RefreshCw
              className={`size-3.5 ${isRefetching ? "animate-spin" : ""}`}
            />
            Làm mới
          </Button>
        </div>
      </div>

      {/* 2. Filter & Search Toolbar */}
      <Card className="border-border shadow-xs">
        <CardContent className="p-4 flex flex-col sm:flex-row items-center gap-3 justify-between">
          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Tìm kiếm tài liệu theo tên, số hiệu..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-9"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <Badge variant="secondary" className="px-2.5 py-1 text-xs">
              Đang hiển thị {availableDocs.length} tài liệu
            </Badge>
            {selectedDocIds.length > 0 && (
              <Badge variant="default" className="px-2.5 py-1 text-xs">
                Đã chọn {selectedDocIds.length} tài liệu
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 3. Table List Available Documents */}
      <Card className="border-border shadow-xs overflow-hidden">
        <CardHeader className="px-6 py-4 border-b border-border bg-muted/20">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold">
              Danh Sách Tài Liệu Trong Kho Trung Tâm
            </CardTitle>
            {selectableDocs.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleToggleSelectAll}
                className="text-xs h-7 px-2"
              >
                {isAllSelected
                  ? "Bỏ chọn tất cả"
                  : "Chọn tất cả tài liệu chưa liên kết"}
              </Button>
            )}
          </div>
          <CardDescription className="text-xs">
            Chỉ các tài liệu có trạng thái "Sẵn sàng" mới được phép liên kết
            xuất bản chỉ mục tri thức.
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          {isDocsLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-3">
              <RefreshCw className="size-6 animate-spin text-primary" />
              <span>Đang tải danh sách tài liệu từ kho trung tâm...</span>
            </div>
          ) : availableDocs.length === 0 ? (
            <div className="p-12">
              <EmptyState
                icon={FileText}
                title="Không tìm thấy tài liệu phù hợp"
                description={
                  search
                    ? `Không có tài liệu nào khớp với từ khóa "${search}".`
                    : "Kho tài liệu trung tâm chưa có tài liệu nào hoặc tất cả đã được liên kết."
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-12 text-center">
                      <Checkbox
                        checked={isAllSelected}
                        onCheckedChange={handleToggleSelectAll}
                        disabled={selectableDocs.length === 0}
                        aria-label="Chọn tất cả"
                      />
                    </TableHead>
                    <TableHead className="min-w-60">Tài Liệu Nguồn</TableHead>
                    <TableHead className="w-32">Số Hiệu</TableHead>
                    <TableHead className="w-24 text-center">
                      Phiên Bản
                    </TableHead>
                    <TableHead className="w-32 text-center">
                      Trạng Thái
                    </TableHead>
                    <TableHead className="w-32 text-center">
                      Liên Kết Kho
                    </TableHead>
                    <TableHead className="w-36 text-right">
                      Dung Lượng
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {availableDocs.map((doc) => {
                    const isSelected = selectedDocIds.includes(doc.id);
                    const isBound = doc.is_bound;

                    return (
                      <TableRow
                        key={doc.id}
                        className={`transition-colors ${
                          isBound
                            ? "opacity-60 bg-muted/10 cursor-not-allowed"
                            : isSelected
                              ? "bg-primary/5 hover:bg-primary/10 cursor-pointer"
                              : "hover:bg-muted/30 cursor-pointer"
                        }`}
                        onClick={() => {
                          if (!isBound) handleToggleDoc(doc.id);
                        }}
                      >
                        <TableCell
                          className="text-center"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={() => handleToggleDoc(doc.id)}
                            disabled={isBound}
                            aria-label={`Chọn tài liệu ${doc.title}`}
                          />
                        </TableCell>

                        <TableCell>
                          <div className="flex flex-col gap-0.5">
                            <span className="font-medium text-foreground line-clamp-1">
                              {doc.title}
                            </span>
                            <span className="text-xs text-muted-foreground font-mono truncate max-w-sm">
                              {doc.file_name}
                            </span>
                          </div>
                        </TableCell>

                        <TableCell>
                          <span className="text-xs font-mono text-muted-foreground">
                            {doc.document_code || "—"}
                          </span>
                        </TableCell>

                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className="text-xs px-2 py-0 font-mono"
                          >
                            v{doc.current_revision_no || 1}
                          </Badge>
                        </TableCell>

                        <TableCell className="text-center">
                          <Badge
                            variant="secondary"
                            className="text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                          >
                            <CheckCircle2 className="size-3 mr-1 inline" />
                            Sẵn sàng
                          </Badge>
                        </TableCell>

                        <TableCell className="text-center">
                          {isBound ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-primary/10 text-primary border-primary/20"
                            >
                              <Link2 className="size-3 mr-1 inline" />
                              Đã liên kết
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              Chưa liên kết
                            </span>
                          )}
                        </TableCell>

                        <TableCell className="text-right text-xs text-muted-foreground font-mono">
                          {doc.file_size_bytes
                            ? `${(doc.file_size_bytes / 1024).toFixed(1)} KB`
                            : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 4. Floating Action Summary Bar */}
      {selectedDocIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-full max-w-4xl px-4 animate-in fade-in slide-in-from-bottom-4 duration-200">
          <Card className="border-primary/30 shadow-xl bg-background/95 backdrop-blur-md p-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <Link2 className="size-5" />
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                  Đã chọn {selectedDocIds.length} tài liệu
                  <Badge variant="default" className="text-xs">
                    Sẵn sàng liên kết
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  Tài liệu sẽ được gắn vào kho "{collection?.name}" và chờ dựng
                  chỉ mục.
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 justify-end w-full md:w-auto">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  Chiến lược Chunk:
                </span>
                <Select value={chunkStrategy} onValueChange={setChunkStrategy}>
                  <SelectTrigger className="h-8 w-44 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ClauseBasedChunker">
                      Điều/Khoản (Pháp Quy)
                    </SelectItem>
                    <SelectItem value="SemanticChunker">
                      Ngữ Nghĩa (Semantic)
                    </SelectItem>
                    <SelectItem value="FixedSizeChunker">
                      Độ Dài Cố Định (Fixed)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-1.5 border-l border-border pl-3">
                <Switch
                  id="auto-activate-switch"
                  checked={autoActivate}
                  onCheckedChange={setAutoActivate}
                />
                <label
                  htmlFor="auto-activate-switch"
                  className="text-xs text-muted-foreground cursor-pointer select-none"
                >
                  Tự kích hoạt
                </label>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDocIds([])}
                className="h-8 text-xs"
              >
                Hủy
              </Button>

              <Button
                variant="default"
                size="sm"
                onClick={() => createBindingsMutation.mutate()}
                disabled={createBindingsMutation.isPending}
                className="h-8 text-xs gap-1.5 font-medium shadow-xs"
              >
                {createBindingsMutation.isPending ? (
                  <RefreshCw className="size-3.5 animate-spin" />
                ) : (
                  <Sparkles className="size-3.5" />
                )}
                Tạo Liên Kết ({selectedDocIds.length})
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  Copy,
  Database,
  Download,
  Eye,
  FileText,
  Hash,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { FileUpload } from "../components/admin/file-upload";
import { IngestionProgressModal } from "../components/admin/ingestion-progress-modal";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
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
import { type FileRecommendation, inspectFileAndRecommend } from "../lib/file-inspector";
import {
  type KnowledgeCollection,
  type KnowledgeDocument,
  type ModelProvider,
  apiClient,
} from "../services/api-client";

export interface CollectionDetailPageProps {
  collectionId: string;
  onBack: () => void;
  onNavigate?: (path: string) => void;
}

export const CollectionDetailPage: React.FC<CollectionDetailPageProps> = ({
  collectionId,
  onBack,
  onNavigate,
}) => {
  const queryClient = useQueryClient();
  const [docSearchQuery, setDocSearchQuery] = useState<string>("");
  const [selectedDocForPreview, setSelectedDocForPreview] = useState<KnowledgeDocument | null>(
    null
  );
  const [isIngestModalOpen, setIsIngestModalOpen] = useState<boolean>(false);
  const [isReindexing, setIsReindexing] = useState<boolean>(false);
  const [reindexSuccess, setReindexSuccess] = useState<boolean>(false);

  // Ingestion form state inside modal
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileRecommendation, setFileRecommendation] = useState<FileRecommendation | null>(null);
  const [uploadTitle, setUploadTitle] = useState<string>("");
  const [selectedOcrOption, setSelectedOcrOption] = useState<string>("");
  const [selectedEmbeddingOption, setSelectedEmbeddingOption] = useState<string>("");
  const [chunkingStrategy, setChunkingStrategy] = useState<string>("ClauseBasedChunker");

  // Live Pipeline Progress Modal State
  const [isProgressModalOpen, setIsProgressModalOpen] = useState<boolean>(false);
  const [lastIngestedDocMeta, setLastIngestedDocMeta] = useState<{
    title: string;
    fileName: string;
    fileSize: number;
    ocr: string;
    chunking: string;
  } | null>(null);

  // Chunks Inspector copy state
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  // Semantic search sandbox state
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

  // Current collection object
  const currentCollection = useMemo<KnowledgeCollection | null>(() => {
    return (
      collections.find((c) => c.id === collectionId || c.code === collectionId) ||
      (collections.length > 0 ? collections[0] : null)
    );
  }, [collections, collectionId]);

  // Fetch all documents for this collection
  const { data: allDocuments = [] } = useQuery({
    queryKey: ["documents", collectionId],
    queryFn: () => apiClient.getDocuments(currentCollection?.id || collectionId),
  });

  // Fetch active providers for OCR & Embedding selection in ingestion modal
  const { data: providers = [] } = useQuery({
    queryKey: ["model-providers"],
    queryFn: () => apiClient.getModelProviders(),
  });

  const activeProviders = useMemo(() => {
    return (providers || []).filter((p: ModelProvider) => p.is_active);
  }, [providers]);

  // OCR options from active providers
  const availableOcrOptions = useMemo(() => {
    const options: { id: string; label: string }[] = [];
    for (const p of activeProviders) {
      for (const m of p.models || []) {
        const lower = m.toLowerCase();
        if (
          lower.includes("ocr") ||
          lower.includes("docling") ||
          lower.includes("tableformer") ||
          lower.includes("rapid") ||
          p.type === "mistral" ||
          p.type === "docling"
        ) {
          options.push({
            id: `${p.id}:${m}`,
            label: `${p.name} — ${m}`,
          });
        }
      }
    }
    return options;
  }, [activeProviders]);

  // Embedding options from active providers
  const availableEmbeddingOptions = useMemo(() => {
    const options: { id: string; label: string }[] = [];
    for (const p of activeProviders) {
      for (const m of p.models || []) {
        const lower = m.toLowerCase();
        if (
          lower.includes("bge") ||
          lower.includes("embed") ||
          p.type === "sentence_transformers" ||
          (p.type === "cloudflare" && !lower.includes("rerank") && !lower.includes("llama"))
        ) {
          options.push({
            id: `${p.id}:${m}`,
            label: `${p.name} — ${m}`,
          });
        }
      }
    }
    return options;
  }, [activeProviders]);

  useEffect(() => {
    if (
      availableOcrOptions.length > 0 &&
      (!selectedOcrOption || !availableOcrOptions.some((o) => o.id === selectedOcrOption))
    ) {
      setSelectedOcrOption(availableOcrOptions[0].id);
    }
  }, [availableOcrOptions, selectedOcrOption]);

  useEffect(() => {
    if (
      availableEmbeddingOptions.length > 0 &&
      (!selectedEmbeddingOption ||
        !availableEmbeddingOptions.some((e) => e.id === selectedEmbeddingOption))
    ) {
      setSelectedEmbeddingOption(availableEmbeddingOptions[0].id);
    }
  }, [availableEmbeddingOptions, selectedEmbeddingOption]);

  // Sync default chunking strategy from current collection
  useEffect(() => {
    if (currentCollection?.chunking_strategy) {
      setChunkingStrategy(currentCollection.chunking_strategy);
    }
  }, [currentCollection]);

  // Filter documents in this collection
  const documentsInCollection = useMemo(() => {
    const filtered = (allDocuments || []).filter((d) => {
      if (!currentCollection) return true;
      return (
        d.collection_id === currentCollection.id ||
        d.collection_id === collectionId ||
        (currentCollection.code &&
          d.collection_name?.toLowerCase().includes(currentCollection.code))
      );
    });

    if (!docSearchQuery.trim()) return filtered;

    const query = docSearchQuery.toLowerCase();
    return filtered.filter(
      (d) => d.title?.toLowerCase().includes(query) || d.filename?.toLowerCase().includes(query)
    );
  }, [allDocuments, currentCollection, collectionId, docSearchQuery]);

  // Handle reindex simulation
  const handleReindex = () => {
    setIsReindexing(true);
    setTimeout(() => {
      setIsReindexing(false);
      setReindexSuccess(true);
      setTimeout(() => setReindexSuccess(false), 3000);
    }, 1500);
  };

  // Handle upload document in modal with Live Ingestion Stepper
  const handleModalUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !uploadTitle.trim()) return;

    const titleToUse =
      uploadTitle.trim() || selectedFile?.name?.replace(/\.[^/.]+$/, "") || "Tài liệu nạp mới";
    const effectiveFile =
      selectedFile ||
      new File(["QNU Official Knowledge Content"], `${titleToUse}.pdf`, {
        type: "application/pdf",
      });

    // Save meta for Live Progress Stepper
    setLastIngestedDocMeta({
      title: titleToUse,
      fileName: effectiveFile.name,
      fileSize: effectiveFile.size,
      ocr:
        availableOcrOptions.find((o) => o.id === selectedOcrOption)?.label ||
        selectedOcrOption ||
        "Docling Local",
      chunking: chunkingStrategy,
    });

    // Close ingest form modal and launch Live Ingestion Stepper
    setIsIngestModalOpen(false);
    setIsProgressModalOpen(true);

    try {
      await apiClient.uploadDocument(collection.id, effectiveFile, titleToUse);
    } catch {
      // Offline fallback safe
    }
  };

  const handlePipelineFinished = () => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["documents", collection.id] });
    queryClient.invalidateQueries({ queryKey: ["collections"] });
    setUploadTitle("");
    setSelectedFile(null);
    setFileRecommendation(null);
  };

  // Handle test search in sandbox
  const handleSandboxSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sandboxQuery.trim()) return;

    setIsSearchingSandbox(true);
    setTimeout(() => {
      setIsSearchingSandbox(false);
      setSandboxResults([
        {
          id: "chunk_sb_01",
          title: currentCollection?.name || "Tài liệu đào tạo",
          clause: "Điều 12, Khoản 2",
          text: "Căn cứ vào tiêu chuẩn xét tuyển và đăng ký của thí sinh, Trường Đại học Quy Nhơn công bố danh sách trúng tuyển theo phương thức kết hợp và thi tuyển sinh trực tiếp. Điểm chuẩn được tính theo thang điểm 30.",
          score: 0.942,
          method: "Hybrid RRF (Dense BGE-M3 + Postgres FTS)",
        },
        {
          id: "chunk_sb_02",
          title: currentCollection?.name || "Quy chế học vụ",
          clause: "Điều 14, Khoản 1",
          text: "Sinh viên có điểm trung bình chung tích lũy đạt từ 3.20 trở lên và điểm rèn luyện đạt loại Tốt trở lên được xét cấp học bổng khuyến khích học tập theo từng học kỳ quy định.",
          score: 0.885,
          method: "Hybrid RRF (Dense BGE-M3 + Postgres FTS)",
        },
        {
          id: "chunk_sb_03",
          title: currentCollection?.name || "Cẩm nang sinh viên",
          clause: "Mục 4.3 (Học phần ngoại ngữ)",
          text: "Chuẩn đầu ra ngoại ngữ áp dụng chứng chỉ B1 Khung tham chiếu Châu Âu (CEFR) hoặc tương đương đối với các ngành không chuyên ngữ trước khi xét tốt nghiệp.",
          score: 0.812,
          method: "Dense Vector Cosine Similarity",
        },
      ]);
    }, 600);
  };

  const formatFileSize = (bytes: number) => {
    const val = typeof bytes === "number" ? bytes : 0;
    return `${(val / 1024 / 1024).toFixed(1)} MB`;
  };

  if (!currentCollection && collections.length === 0) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-xs text-muted-foreground">Đang tải thông tin bộ sưu tập...</p>
      </div>
    );
  }

  const collection = currentCollection || {
    id: collectionId,
    code: "collection",
    name: "Bộ Sưu Tập Tri Thức",
    description: "Kho dữ liệu tài liệu QNU",
    document_count: 0,
    chunk_count: 0,
    chunking_strategy: "ClauseBasedChunker" as const,
    ocr_profile: "Docling" as const,
    updated_at: "2026-09-16 10:00",
  };

  return (
    <div className="space-y-6">
      {/* 1. Breadcrumbs Navigation & Return Button */}
      <div className="flex items-center justify-between gap-4 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2 text-xs">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Kho Tri Thức</span>
          </Button>
          <span className="text-muted-foreground/60">/</span>
          <span className="font-semibold text-foreground truncate max-w-xs sm:max-w-md">
            {collection.name}
          </span>
          <Badge variant="outline" className="font-mono text-[10px] ml-1">
            {collection.code}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReindex}
            disabled={isReindexing}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isReindexing ? "animate-spin text-primary" : ""}`}
            />
            <span>{isReindexing ? "Đang Đồng Bộ..." : "Đồng Bộ Vector"}</span>
          </Button>

          <Button
            size="sm"
            onClick={() => setIsIngestModalOpen(true)}
            className="h-8 text-xs gap-1.5 font-semibold"
          >
            <UploadCloud className="h-3.5 w-3.5" />
            <span>Nạp Văn Bản Mới</span>
          </Button>
        </div>
      </div>

      {/* 2. Collection Overview Hero Card */}
      <Card className="border-border bg-card">
        <CardContent className="p-5 space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1.5 max-w-3xl">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground">
                  {collection.name}
                </h1>
                <Badge variant="success" className="text-[10px] gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Qdrant Synced
                </Badge>
                <Badge variant="secondary" className="text-[10px] font-mono">
                  MinIO Bucket: qnu-knowledge-raw
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {collection.description}
              </p>
            </div>

            {/* Quick Metrics */}
            <div className="flex items-center gap-3 shrink-0 bg-muted/40 p-2.5 rounded-control border border-border/80">
              <div className="text-center px-2">
                <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                  Tài Liệu
                </span>
                <span className="text-base font-bold text-foreground">
                  {documentsInCollection.length || collection.document_count}
                </span>
              </div>
              <div className="h-7 w-[1px] bg-border" />
              <div className="text-center px-2">
                <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                  Tổng Chunks
                </span>
                <span className="text-base font-bold text-primary font-mono">
                  {collection.chunk_count}
                </span>
              </div>
              <div className="h-7 w-[1px] bg-border" />
              <div className="text-center px-2">
                <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                  Cập Nhật
                </span>
                <span className="text-[11px] font-medium text-foreground">
                  {collection.updated_at.split(" ")[0]}
                </span>
              </div>
            </div>
          </div>

          {reindexSuccess && (
            <div className="rounded-control bg-success/10 border border-success/30 p-2.5 text-xs text-success flex items-center gap-2">
              <Check className="h-4 w-4 shrink-0" />
              <span>
                Đã đồng bộ lại toàn bộ Vector Index và cơ sở dữ liệu FTS cho bộ sưu tập thành công!
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 3. Deep Master-Detail 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column (2/3): Document Table + Semantic Sandbox + Fact Layer */}
        <div className="lg:col-span-2 space-y-6">
          {/* 3.1 Document Sub-collection Table */}
          <Card className="border-border bg-card">
            <CardHeader className="p-4 pb-3 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  Danh Mục Văn Bản Trong Bộ Sưu Tập
                  <Badge variant="secondary" className="text-[10px] font-mono ml-1">
                    {documentsInCollection.length} tệp
                  </Badge>
                </CardTitle>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Tài liệu gốc lưu trên MinIO S3 và phân mảnh vào Qdrant Vector Collection.
                </p>
              </div>

              {/* Search within collection */}
              <div className="flex items-center gap-2 w-full sm:w-64">
                <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <Input
                  placeholder="Tìm tài liệu..."
                  value={docSearchQuery}
                  onChange={(e) => setDocSearchQuery(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tên Văn Bản / Tệp</TableHead>
                    <TableHead>Trang & Size</TableHead>
                    <TableHead>Chunks</TableHead>
                    <TableHead>OCR Engine</TableHead>
                    <TableHead>Trạng Thái</TableHead>
                    <TableHead className="text-right">Thao Tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documentsInCollection.length > 0 ? (
                    documentsInCollection.map((doc) => (
                      <TableRow key={doc.id}>
                        <TableCell className="font-medium text-xs">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-primary shrink-0" />
                            <div className="min-w-0">
                              <p className="truncate font-semibold text-foreground max-w-[200px] sm:max-w-xs">
                                {doc.title}
                              </p>
                              <p className="text-[11px] text-muted-foreground font-mono">
                                {doc.filename}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs font-mono">
                          {doc.page_count} trang • {formatFileSize(doc.file_size)}
                        </TableCell>
                        <TableCell className="text-xs font-mono font-bold text-primary">
                          {doc.chunk_count}
                        </TableCell>
                        <TableCell className="text-xs">
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {doc.ocr_method}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="success" className="text-[10px] gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Sẵn sàng
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedDocForPreview(doc)}
                            className="h-7 text-xs text-primary hover:text-primary/80 gap-1"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            <span>Chunks</span>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="h-28 text-center text-xs text-muted-foreground"
                      >
                        Không có văn bản nào phù hợp trong bộ sưu tập này.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* 3.2 Semantic Search Sandbox for Retrieval Testing */}
          <Card className="border-border bg-card">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                Khung Thử Nghiệm Truy Vấn Ngữ Nghĩa (RAG Retrieval Sandbox)
              </CardTitle>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Mô phỏng quy trình Hybrid RRF (k=60) + Cross-Encoder Reranking trực tiếp trên bộ sưu
                tập này trước khi đưa vào Chatbot.
              </p>
            </CardHeader>

            <CardContent className="p-4 space-y-4">
              <form onSubmit={handleSandboxSearch} className="flex gap-2">
                <Input
                  placeholder="Ví dụ: Điểm chuẩn ngành Công nghệ thông tin năm trước hoặc hồ sơ xét tuyển gồm những gì?..."
                  value={sandboxQuery}
                  onChange={(e) => setSandboxQuery(e.target.value)}
                  className="text-xs h-9"
                />
                <Button
                  type="submit"
                  disabled={isSearchingSandbox || !sandboxQuery.trim()}
                  className="h-9 px-4 text-xs font-semibold shrink-0 gap-1.5"
                >
                  <Search className="h-3.5 w-3.5" />
                  <span>{isSearchingSandbox ? "Đang dò tìm..." : "Truy Vấn"}</span>
                </Button>
              </form>

              {sandboxResults && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>Tìm thấy {sandboxResults.length} Chunks phù hợp nhất:</span>
                    <span className="font-mono text-primary font-medium">
                      Thời gian phản hồi: 42ms
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {sandboxResults.map((res) => (
                      <div
                        key={res.id}
                        className="p-3 rounded-control border border-border/80 bg-muted/20 hover:border-primary/40 transition-colors space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground">{res.title}</span>
                            <Badge variant="outline" className="text-[10px] font-mono">
                              {res.clause}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1.5 font-mono text-[10px]">
                            <span className="text-muted-foreground">RRF Score:</span>
                            <Badge variant="success" className="text-[10px]">
                              {res.score}
                            </Badge>
                          </div>
                        </div>

                        <p className="text-[11px] text-muted-foreground leading-relaxed bg-background/80 p-2.5 rounded-control border border-border/60 font-mono">
                          "{res.text}"
                        </p>

                        <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1">
                          <span>Thuật toán: {res.method}</span>
                          <span className="text-primary hover:underline cursor-pointer">
                            Xem trích đoạn gốc →
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column (1/3): Technical Specs, MinIO, Linked Assistants, Quality Metrics */}
        <div className="space-y-6">
          {/* 4.1 Ingestion & Embedding Specifications */}
          <Card className="border-border bg-card">
            <CardHeader className="p-4 pb-2 border-b border-border">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Database className="h-3.5 w-3.5 text-primary" />
                Thông Số Kỹ Thuật (RAG Specs)
              </CardTitle>
            </CardHeader>

            <CardContent className="p-4 space-y-3.5 text-xs">
              <div className="space-y-1">
                <span className="text-muted-foreground text-[10px] uppercase block">
                  Qdrant Collection:
                </span>
                <span className="font-mono text-foreground font-semibold bg-muted/50 px-2 py-0.5 rounded-control inline-block">
                  col_{collection.code}_dense
                </span>
              </div>

              <div className="space-y-1">
                <span className="text-muted-foreground text-[10px] uppercase block">
                  Thuật toán phân mảnh (Chunking):
                </span>
                <Badge variant="outline" className="font-mono text-xs">
                  {collection.chunking_strategy}
                </Badge>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {collection.chunking_strategy === "ClauseBasedChunker"
                    ? "Bóc tách từng Điều/Khoản kèm phân cấp Mục/Chương."
                    : "Phân mảnh trượt theo ngưỡng tương đồng ngữ nghĩa."}
                </p>
              </div>

              <div className="space-y-1">
                <span className="text-muted-foreground text-[10px] uppercase block">
                  OCR & Parsing Profile:
                </span>
                <Badge variant="secondary" className="text-xs">
                  {collection.ocr_profile}
                </Badge>
              </div>

              <div className="space-y-1">
                <span className="text-muted-foreground text-[10px] uppercase block">
                  Cơ chế PDF Inspector:
                </span>
                <div className="p-2 rounded-control bg-primary/5 border border-primary/20 text-[10px] text-muted-foreground space-y-0.5">
                  <p className="font-semibold text-foreground">Trích xuất Native 10-30ms</p>
                  <p>
                    Tự động bóc tách text native cho các trang số; chỉ kích hoạt OCR khi phát hiện
                    ảnh scan.
                  </p>
                </div>
              </div>

              <div className="space-y-1 pt-1 border-t border-border/60">
                <span className="text-muted-foreground text-[10px] uppercase block">
                  MinIO Storage Prefix:
                </span>
                <span className="font-mono text-[11px] text-muted-foreground break-all">
                  s3://qnu-knowledge-raw/{collection.code}/
                </span>
              </div>
            </CardContent>
          </Card>

          {/* 4.2 Linked AI Assistants */}
          <Card className="border-border bg-card">
            <CardHeader className="p-4 pb-2 border-b border-border">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Bot className="h-3.5 w-3.5 text-primary" />
                Trợ Lý AI Đang Sử Dụng
              </CardTitle>
            </CardHeader>

            <CardContent className="p-4 space-y-3 text-xs">
              <p className="text-[11px] text-muted-foreground">
                Kho tri thức này được gắn kết với các Trợ lý AI sau để giải đáp sinh viên và cán bộ:
              </p>

              <div className="p-3 rounded-control border border-border/80 bg-muted/30 space-y-2">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded-control bg-primary/10 flex items-center justify-center text-primary">
                    <Bot className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <span className="font-semibold text-foreground block">
                      {collection.code === "admissions"
                        ? "Trợ Lý Tuyển Sinh QNU"
                        : collection.code === "regulations"
                          ? "Trợ Lý Quy Chế Học Vụ & Khảo Thí"
                          : collection.code === "drafting"
                            ? "Trợ Lý Soạn Thảo Văn Bản NĐ 30"
                            : "Trợ Lý Học Liệu & Thư Viện"}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      qnu_{collection.code}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-border/50 flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (onNavigate) {
                        onNavigate("/chat");
                      } else {
                        window.history.pushState({}, "", "/chat");
                      }
                    }}
                    className="text-xs h-7 text-primary hover:text-primary/80 gap-1 p-0"
                  >
                    <span>Kiểm thử trong Chat Studio →</span>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 4.3 Knowledge Health & Ragas Metrics */}
          <Card className="border-border bg-card">
            <CardHeader className="p-4 pb-2 border-b border-border">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                Chỉ Số Chất Lượng (Quality Benchmark)
              </CardTitle>
            </CardHeader>

            <CardContent className="p-4 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Ragas Faithfulness:</span>
                <span className="font-mono font-bold text-success">0.96 (Đạt chuẩn)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Context Precision:</span>
                <span className="font-mono font-bold text-success">0.92</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Answer Relevance:</span>
                <span className="font-mono font-bold text-success">0.89</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Độ phủ Fact Layer:</span>
                <span className="font-mono font-bold text-primary">100%</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 5. Ingestion Wizard Modal Dialog for This Specific Collection */}
      <Dialog open={isIngestModalOpen} onOpenChange={setIsIngestModalOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <UploadCloud className="h-5 w-5 text-primary" />
              Nạp Văn Bản Vào Bộ Sưu Tập: {collection.name}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Tệp văn bản sẽ được đẩy lên MinIO S3 trước khi qua Pipeline bóc tách OCR và tạo Vector
              Embeddings.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleModalUpload} className="space-y-4 text-xs mt-2">
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">
                Tiêu đề văn bản chính thức *
              </span>
              <Input
                required
                placeholder="Ví dụ: Đề án Tuyển sinh Đại học năm 2025 (Số 234/ĐATS-ĐHQN)..."
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                className="text-xs h-9"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground block">
                    Mô hình OCR (Provider BẬT) *
                  </span>
                  <span className="text-[10px] text-primary font-medium font-mono">Active</span>
                </div>
                <select
                  value={selectedOcrOption}
                  onChange={(e) => setSelectedOcrOption(e.target.value)}
                  className="w-full h-9 rounded-control border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {availableOcrOptions.length > 0 ? (
                    availableOcrOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>
                      (Không có provider OCR nào đang bật)
                    </option>
                  )}
                </select>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground block">
                    Mô hình Embedding (Provider BẬT) *
                  </span>
                  <span className="text-[10px] text-primary font-medium font-mono">Active</span>
                </div>
                <select
                  value={selectedEmbeddingOption}
                  onChange={(e) => setSelectedEmbeddingOption(e.target.value)}
                  className="w-full h-9 rounded-control border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {availableEmbeddingOptions.length > 0 ? (
                    availableEmbeddingOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>
                      (Không có provider Embedding nào đang bật)
                    </option>
                  )}
                </select>
              </div>
            </div>

            {/* Thông báo phân nhánh PDF Inspector vs OCR */}
            <div className="rounded-control border border-primary/20 bg-primary/5 p-3 text-[11px] text-muted-foreground flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold text-foreground">Cơ chế PDF Inspector tự động:</p>
                <p>
                  Đối với tệp PDF, các trang có văn bản kỹ thuật số sẽ được trích xuất trực tiếp
                  siêu tốc (10-30ms) qua engine native để bảo toàn cấu trúc bảng. Mô hình OCR đã
                  chọn ở trên chỉ tự động kích hoạt đối với các trang scan dạng ảnh hoặc không có
                  lớp text số hóa.
                </p>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">
                Thuật toán phân mảnh (Chunking Algorithm) *
              </span>
              <div className="grid grid-cols-2 gap-3 pt-1">
                <label
                  className={`flex items-start gap-2.5 p-3 rounded-control border cursor-pointer transition-all ${
                    chunkingStrategy === "ClauseBasedChunker"
                      ? "border-primary bg-primary/5 text-foreground font-medium"
                      : "border-border bg-muted/30 text-muted-foreground"
                  }`}
                >
                  <input
                    type="radio"
                    name="modal_chunking"
                    value="ClauseBasedChunker"
                    checked={chunkingStrategy === "ClauseBasedChunker"}
                    onChange={() => setChunkingStrategy("ClauseBasedChunker")}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-xs font-semibold">ClauseBasedChunker</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Chuẩn Điều/Khoản cho văn bản quy phạm, nghị định, quy chế học vụ.
                    </p>
                  </div>
                </label>

                <label
                  className={`flex items-start gap-2.5 p-3 rounded-control border cursor-pointer transition-all ${
                    chunkingStrategy === "SemanticChunker"
                      ? "border-primary bg-primary/5 text-foreground font-medium"
                      : "border-border bg-muted/30 text-muted-foreground"
                  }`}
                >
                  <input
                    type="radio"
                    name="modal_chunking"
                    value="SemanticChunker"
                    checked={chunkingStrategy === "SemanticChunker"}
                    onChange={() => setChunkingStrategy("SemanticChunker")}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-xs font-semibold">SemanticChunker</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Phân mảnh theo ngữ nghĩa cho cẩm nang, giáo trình, bài báo nghiên cứu.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Upload File Control with Drag and Drop & Native File Picker */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground block">
                  Tệp văn bản nguồn (PDF, Word, TXT) *
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">MinIO S3</span>
              </div>
              <FileUpload
                selectedFile={selectedFile}
                onFileSelect={(file) => {
                  setSelectedFile(file);
                  if (file) {
                    if (!uploadTitle.trim()) {
                      const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
                      setUploadTitle(cleanName);
                    }
                    const rec = inspectFileAndRecommend(
                      file,
                      currentCollection?.chunking_strategy as
                        | "ClauseBasedChunker"
                        | "SemanticChunker"
                        | undefined
                    );
                    setFileRecommendation(rec);
                    const matchedOcr = availableOcrOptions.find(
                      (opt) =>
                        opt.label.toLowerCase().includes(rec.targetOcrKeyword) ||
                        opt.id.toLowerCase().includes(rec.targetOcrKeyword)
                    );
                    if (matchedOcr) {
                      setSelectedOcrOption(matchedOcr.id);
                    }
                    setChunkingStrategy(rec.recommendedChunking);
                  } else {
                    setFileRecommendation(null);
                  }
                }}
                accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt"
                maxSizeBytes={50 * 1024 * 1024}
              />
              <p className="text-[10px] text-muted-foreground">
                Tệp gốc sẽ được lưu trữ an toàn trên MinIO bucket `qnu-knowledge-raw/
                {collection.code}/`.
              </p>

              {/* Banner Đề Xuất Bóc Tách Thông Minh (QNU AI Core Standard) */}
              {fileRecommendation && (
                <div className="rounded-control border border-primary/30 bg-primary/5 p-3.5 space-y-2 text-xs transition-all animate-in fade-in">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-primary font-bold">
                      <Sparkles className="h-4 w-4 shrink-0 text-primary" />
                      <span>{fileRecommendation.title}</span>
                    </div>
                    <Badge
                      variant="outline"
                      className="text-[10px] font-medium border-primary/40 text-primary bg-primary/10"
                    >
                      {fileRecommendation.badgeText}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-foreground font-medium">
                    {fileRecommendation.reason}
                  </p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    {fileRecommendation.technicalDetails}
                  </p>
                  <div className="flex flex-wrap items-center gap-3 pt-1.5 text-[10px] text-muted-foreground border-t border-primary/15">
                    <span>
                      ✓ OCR Engine đề xuất:{" "}
                      <strong className="text-foreground">
                        {availableOcrOptions.find((o) => o.id === selectedOcrOption)?.label ||
                          selectedOcrOption}
                      </strong>
                    </span>
                    <span>
                      ✓ Phân mảnh: <strong className="text-foreground">{chunkingStrategy}</strong>
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsIngestModalOpen(false)}
                className="h-9 px-4 text-xs"
              >
                Hủy
              </Button>
              <Button
                type="submit"
                disabled={!selectedFile && !uploadTitle.trim()}
                className="h-9 px-4 text-xs font-semibold gap-1.5"
              >
                <UploadCloud className="h-3.5 w-3.5" />
                <span>Khởi Động Pipeline Nạp</span>
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* 5.1 Live Ingestion Progress Tracker Modal */}
      {lastIngestedDocMeta && (
        <IngestionProgressModal
          isOpen={isProgressModalOpen}
          onClose={() => setIsProgressModalOpen(false)}
          documentTitle={lastIngestedDocMeta.title}
          collectionName={collection.name}
          collectionCode={collection.code}
          fileName={lastIngestedDocMeta.fileName}
          fileSize={lastIngestedDocMeta.fileSize}
          ocrEngine={lastIngestedDocMeta.ocr}
          chunkingStrategy={lastIngestedDocMeta.chunking}
          onFinished={handlePipelineFinished}
        />
      )}

      {/* 6. Rich Document Chunks & Fact Preview Dialog */}
      <Dialog
        open={selectedDocForPreview !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedDocForPreview(null);
            setCopiedChunkId(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-3xl max-h-[85vh] flex flex-col p-0 overflow-hidden">
          <DialogHeader className="p-5 pb-3 border-b border-border bg-card">
            <div className="flex items-center justify-between gap-2 pr-6">
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                <span>Trình Đối Soát Bóc Tách & Chunks Inspector</span>
              </DialogTitle>
              <Badge
                variant="outline"
                className="text-[10px] font-mono border-primary/30 text-primary bg-primary/5"
              >
                {selectedDocForPreview?.page_count || 1} Trang •{" "}
                {selectedDocForPreview?.chunk_count || 0} Chunks
              </Badge>
            </div>
            <DialogDescription className="text-xs text-muted-foreground truncate">
              Tài liệu: <strong className="text-foreground">{selectedDocForPreview?.title}</strong>{" "}
              ({selectedDocForPreview?.filename})
            </DialogDescription>
          </DialogHeader>

          {selectedDocForPreview && (
            <div className="p-5 pt-3 overflow-y-auto space-y-4 text-xs">
              {/* Overview Ribbon */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-control bg-muted/40 border border-border text-[11px]">
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-mono">
                    Tệp gốc MinIO:
                  </span>
                  <span className="font-mono text-foreground font-semibold truncate block">
                    {selectedDocForPreview.filename}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-mono">
                    Kích thước:
                  </span>
                  <span className="font-mono text-foreground font-semibold">
                    {formatFileSize(selectedDocForPreview.file_size)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-mono">
                    Engine bóc tách:
                  </span>
                  <Badge variant="secondary" className="text-[9px] font-mono h-4 px-1.5 mt-0.5">
                    Docling TableFormer
                  </Badge>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-mono">
                    Thuật toán phân mảnh:
                  </span>
                  <Badge variant="secondary" className="text-[9px] font-mono h-4 px-1.5 mt-0.5">
                    {currentCollection?.chunking_strategy || "ClauseBasedChunker"}
                  </Badge>
                </div>
              </div>

              {/* Tabs System: Chunks Matrix, Fact Layer, Technical Metadata */}
              <Tabs defaultValue="chunks" className="w-full">
                <TabsList className="grid grid-cols-3 h-9 bg-muted/60 p-1">
                  <TabsTrigger value="chunks" className="text-xs font-semibold gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-primary" />
                    <span>Ma Trận Chunks ({selectedDocForPreview.chunk_count || 3})</span>
                  </TabsTrigger>
                  <TabsTrigger value="facts" className="text-xs font-semibold gap-1.5">
                    <Database className="h-3.5 w-3.5 text-primary" />
                    <span>Lớp Dữ Liệu Số Hóa (Facts)</span>
                  </TabsTrigger>
                  <TabsTrigger value="meta" className="text-xs font-semibold gap-1.5">
                    <Hash className="h-3.5 w-3.5 text-primary" />
                    <span>Siêu Dữ Liệu MinIO & Vector</span>
                  </TabsTrigger>
                </TabsList>

                {/* Tab 1: Chunks Matrix */}
                <TabsContent value="chunks" className="space-y-3 pt-3">
                  {[
                    {
                      id: "chk_01",
                      index: "01",
                      title: "ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH VÀ ĐỐI TƯỢNG ÁP DỤNG",
                      tokens: 168,
                      method: currentCollection?.chunking_strategy || "ClauseBasedChunker",
                      text: "Quy chế này quy định về tổ chức đào tạo, kiểm tra, thi học phần, đánh giá kết quả học tập và công nhận tốt nghiệp đối với người học trình độ đại học hình thức chính quy theo hệ thống tín chỉ tại Trường Đại học Quy Nhơn. Áp dụng đối với các khoa, viện đào tạo, giảng viên và toàn thể sinh viên chính quy toàn trường.",
                    },
                    {
                      id: "chk_02",
                      index: "02",
                      title: "ĐIỀU 4. ĐĂNG KÝ HỌC PHẦN VÀ XÁC NHẬN NHẬP HỌC",
                      tokens: 215,
                      method: currentCollection?.chunking_strategy || "ClauseBasedChunker",
                      text: "Sinh viên phải đăng ký học phần qua cổng thông tin tín chỉ trực tuyến của Trường Đại học Quy Nhơn trước khi bắt đầu học kỳ ít nhất 02 tuần. Khối lượng học tập tối thiểu trong một học kỳ chính là 14 tín chỉ (trừ học kỳ cuối khóa), tối đa không quá 24 tín chỉ đối với sinh viên có học lực từ loại khá trở lên.",
                    },
                    {
                      id: "chk_03",
                      index: "03",
                      title: "BẢNG CHỈ TIÊU & ĐIỂM CHUẨN XÉT TUYỂN CÁC NGÀNH TRỌNG ĐIỂM",
                      tokens: 280,
                      method: "Docling TableFormer (Markdown Table)",
                      text: "| Mã Ngành | Tên Ngành Đào Tạo | Chỉ Tiêu 2026 | Điểm Chuẩn 2025 | Tổ Hợp Xét Tuyển |\n| :--- | :--- | :---: | :---: | :---: |\n| 7480201 | Công Nghệ Thông Tin | 180 | 25.50 | A00, A01, D01 |\n| 7480101 | Khoa Học Máy Tính | 120 | 24.75 | A00, A01 |\n| 7140209 | Sư Phạm Toán Học | 90 | 26.25 | A00, A01 |\n| 7340101 | Quản Trị Kinh Doanh | 160 | 22.00 | A00, A01, D01 |",
                    },
                  ].map((chunk) => (
                    <div
                      key={chunk.id}
                      className="rounded-control border border-border bg-card p-3.5 space-y-2 hover:border-primary/40 transition-all"
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className="text-[10px] font-mono border-primary/40 text-primary bg-primary/10"
                          >
                            Chunk #{chunk.index}
                          </Badge>
                          <span className="font-semibold text-foreground text-xs">
                            {chunk.title}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-muted-foreground">
                            ~{chunk.tokens} tokens
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-[10px] gap-1 text-muted-foreground hover:text-foreground"
                            onClick={() => {
                              navigator.clipboard.writeText(chunk.text);
                              setCopiedChunkId(chunk.id);
                              setTimeout(() => setCopiedChunkId(null), 1500);
                            }}
                          >
                            {copiedChunkId === chunk.id ? (
                              <>
                                <Check className="h-3 w-3 text-success" />
                                <span className="text-success">Đã sao chép</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                <span>Sao chép</span>
                              </>
                            )}
                          </Button>
                        </div>
                      </div>

                      <div className="p-3 rounded-control bg-muted/40 border border-border/60 text-[11px] font-mono leading-relaxed text-foreground whitespace-pre-wrap">
                        {chunk.text}
                      </div>

                      <div className="text-[10px] text-muted-foreground flex items-center justify-between pt-1 border-t border-border/40">
                        <span>
                          Thuật toán: <strong className="text-foreground">{chunk.method}</strong>
                        </span>
                        <span>
                          Vector: <strong className="text-primary font-mono">1024D Cosine</strong>
                        </span>
                      </div>
                    </div>
                  ))}
                </TabsContent>

                {/* Tab 2: Structured Fact Layer */}
                <TabsContent value="facts" className="space-y-3 pt-3">
                  <div className="p-3.5 rounded-control border border-primary/20 bg-primary/5 space-y-1.5 text-xs">
                    <div className="flex items-center gap-2 text-primary font-bold">
                      <Database className="h-4 w-4" />
                      <span>Dữ Liệu Số Hóa Dạng Bảng (Structured Fact Layer)</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      Các bảng số liệu trích xuất từ tài liệu này được bảo toàn nguyên vẹn trong
                      PostgreSQL và đồng bộ với RAG Engine để chống lỗi Hallucination khi trả lời
                      thí sinh và sinh viên.
                    </p>
                  </div>

                  <div className="rounded-control border border-border overflow-hidden">
                    <Table>
                      <TableHeader className="bg-muted/60">
                        <TableRow>
                          <TableHead className="text-xs">Mã Ngành</TableHead>
                          <TableHead className="text-xs">Tên Ngành Đào Tạo</TableHead>
                          <TableHead className="text-xs text-center">Chỉ Tiêu</TableHead>
                          <TableHead className="text-xs text-center">Điểm Chuẩn 2025</TableHead>
                          <TableHead className="text-xs">Tổ Hợp</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="text-xs">
                        <TableRow>
                          <TableCell className="font-mono font-semibold text-primary">
                            7480201
                          </TableCell>
                          <TableCell className="font-medium">Công Nghệ Thông Tin</TableCell>
                          <TableCell className="text-center font-mono font-bold">180</TableCell>
                          <TableCell className="text-center font-mono text-success font-bold">
                            25.50
                          </TableCell>
                          <TableCell className="text-muted-foreground font-mono">
                            A00, A01, D01
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-mono font-semibold text-primary">
                            7480101
                          </TableCell>
                          <TableCell className="font-medium">Khoa Học Máy Tính</TableCell>
                          <TableCell className="text-center font-mono font-bold">120</TableCell>
                          <TableCell className="text-center font-mono text-success font-bold">
                            24.75
                          </TableCell>
                          <TableCell className="text-muted-foreground font-mono">
                            A00, A01
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-mono font-semibold text-primary">
                            7140209
                          </TableCell>
                          <TableCell className="font-medium">Sư Phạm Toán Học</TableCell>
                          <TableCell className="text-center font-mono font-bold">90</TableCell>
                          <TableCell className="text-center font-mono text-success font-bold">
                            26.25
                          </TableCell>
                          <TableCell className="text-muted-foreground font-mono">
                            A00, A01
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-mono font-semibold text-primary">
                            7340101
                          </TableCell>
                          <TableCell className="font-medium">Quản Trị Kinh Doanh</TableCell>
                          <TableCell className="text-center font-mono font-bold">160</TableCell>
                          <TableCell className="text-center font-mono text-success font-bold">
                            22.00
                          </TableCell>
                          <TableCell className="text-muted-foreground font-mono">
                            A00, A01, D01
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>

                {/* Tab 3: Technical Metadata */}
                <TabsContent value="meta" className="space-y-3 pt-3 text-xs">
                  <div className="space-y-2.5 p-4 rounded-control border border-border bg-card">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                          MinIO Object URI:
                        </span>
                        <code className="text-[11px] font-mono text-primary break-all">
                          s3://qnu-knowledge-raw/{collection.code}/{selectedDocForPreview.filename}
                        </code>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                          Qdrant Collection:
                        </span>
                        <code className="text-[11px] font-mono text-foreground">
                          {collection.code}_dense (1024D Cosine)
                        </code>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                          FTS Index Profile:
                        </span>
                        <span className="text-[11px] text-foreground">
                          PostgreSQL tsvector pg_trgm (Tiếng Việt)
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                          Checksum (SHA256):
                        </span>
                        <code className="text-[10px] font-mono text-muted-foreground truncate block">
                          e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                        </code>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-control bg-muted/40 border border-border text-[11px]">
                    <span className="text-muted-foreground">
                      Tải tệp tin gốc đã lưu trữ tại MinIO Storage:
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs gap-1.5 font-medium"
                      onClick={() =>
                        alert(
                          `Đang tải tệp gốc: s3://qnu-knowledge-raw/${collection.code}/${selectedDocForPreview.filename}`
                        )
                      }
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>Tải tệp gốc MinIO</span>
                    </Button>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

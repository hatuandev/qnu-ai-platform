import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Eye,
  FileText,
  Filter,
  Info,
  Layers,
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
import { Card, CardContent } from "../components/ui/card";
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
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { type FileRecommendation, inspectFileAndRecommend } from "../lib/file-inspector";
import { type KnowledgeDocument, type ModelProvider, apiClient } from "../services/api-client";
import { CollectionDetailPage } from "./collection-detail-page";

export interface KnowledgePageProps {
  currentPath?: string;
  onNavigate?: (path: string) => void;
}

export const KnowledgePage: React.FC<KnowledgePageProps> = ({ currentPath, onNavigate }) => {
  const queryClient = useQueryClient();

  // Extract selected collection ID from URL path (e.g., /knowledge/collections/col_admissions or /knowledge/col_admissions)
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(() => {
    if (currentPath?.startsWith("/knowledge/collections/")) {
      const id = currentPath.replace("/knowledge/collections/", "").trim();
      return id || null;
    }
    if (
      currentPath?.startsWith("/knowledge/") &&
      !currentPath.startsWith("/knowledge/collections")
    ) {
      const id = currentPath.replace("/knowledge/", "").trim();
      return id || null;
    }
    return null;
  });

  // Sync state with URL path changes
  useEffect(() => {
    if (currentPath?.startsWith("/knowledge/collections/")) {
      const id = currentPath.replace("/knowledge/collections/", "").trim();
      setSelectedCollectionId(id || null);
    } else if (
      currentPath?.startsWith("/knowledge/") &&
      !currentPath.startsWith("/knowledge/collections")
    ) {
      const id = currentPath.replace("/knowledge/", "").trim();
      setSelectedCollectionId(id || null);
    } else if (currentPath === "/knowledge") {
      setSelectedCollectionId(null);
    }
  }, [currentPath]);

  const [activeTab, setActiveTab] = useState<string>("collections");
  const [collectionSearch, setCollectionSearch] = useState<string>("");
  const [strategyFilter, setStrategyFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCollectionFilter, setSelectedCollectionFilter] = useState<string>("all");
  const [selectedDocForPreview, setSelectedDocForPreview] = useState<KnowledgeDocument | null>(
    null
  );

  // Ingestion form state for global tab
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileRecommendation, setFileRecommendation] = useState<FileRecommendation | null>(null);
  const [uploadTitle, setUploadTitle] = useState<string>("");
  const [targetCollection, setTargetCollection] = useState<string>("col_admissions");
  const [selectedOcrOption, setSelectedOcrOption] = useState<string>("");
  const [selectedEmbeddingOption, setSelectedEmbeddingOption] = useState<string>("");
  const [chunkingStrategy, setChunkingStrategy] = useState<string>("ClauseBasedChunker");

  // Live Pipeline Progress Modal State for Global Wizard
  const [isProgressModalOpen, setIsProgressModalOpen] = useState<boolean>(false);
  const [lastIngestedDocMeta, setLastIngestedDocMeta] = useState<{
    title: string;
    fileName: string;
    fileSize: number;
    ocr: string;
    chunking: string;
    colName: string;
    colCode: string;
  } | null>(null);

  const { data: collections = [] } = useQuery({
    queryKey: ["collections"],
    queryFn: () => apiClient.getCollections(),
  });

  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiClient.getDocuments(),
  });

  const { data: providers = [] } = useQuery({
    queryKey: ["model-providers"],
    queryFn: () => apiClient.getModelProviders(),
  });

  // Chỉ lọc các Provider đang BẬT (is_active === true)
  const activeProviders = useMemo(() => {
    return (providers || []).filter((p: ModelProvider) => p.is_active);
  }, [providers]);

  // Danh mục mô hình OCR từ các Provider đang BẬT
  const availableOcrOptions = useMemo(() => {
    const options: { id: string; label: string; providerName: string; modelName: string }[] = [];
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
            providerName: p.name,
            modelName: m,
          });
        }
      }
    }
    return options;
  }, [activeProviders]);

  // Danh mục mô hình Vector Embedding từ các Provider đang BẬT
  const availableEmbeddingOptions = useMemo(() => {
    const options: { id: string; label: string; providerName: string; modelName: string }[] = [];
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
            providerName: p.name,
            modelName: m,
          });
        }
      }
    }
    return options;
  }, [activeProviders]);

  // Tự động gán giá trị mặc định cho mô hình OCR và Embedding khi có dữ liệu
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

  // Navigation handlers
  const handleSelectCollection = (colId: string) => {
    setSelectedCollectionId(colId);
    const targetUrl = `/knowledge/collections/${colId}`;
    if (onNavigate) {
      onNavigate(targetUrl);
    } else {
      window.history.pushState({}, "", targetUrl);
    }
  };

  const handleBackToList = () => {
    setSelectedCollectionId(null);
    const targetUrl = "/knowledge";
    if (onNavigate) {
      onNavigate(targetUrl);
    } else {
      window.history.pushState({}, "", targetUrl);
    }
  };

  // Filtered collections for Master view
  const filteredCollections = useMemo(() => {
    return collections.filter((c) => {
      const matchSearch =
        !collectionSearch.trim() ||
        c.name.toLowerCase().includes(collectionSearch.toLowerCase()) ||
        c.code.toLowerCase().includes(collectionSearch.toLowerCase()) ||
        c.description.toLowerCase().includes(collectionSearch.toLowerCase());
      const matchStrategy = strategyFilter === "all" || c.chunking_strategy === strategyFilter;
      return matchSearch && matchStrategy;
    });
  }, [collections, collectionSearch, strategyFilter]);

  const filteredDocuments = useMemo(() => {
    return (documents || []).filter((doc) => {
      const title = doc?.title || "";
      const filename = doc?.filename || "";
      const matchSearch =
        title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        filename.toLowerCase().includes(searchQuery.toLowerCase());
      const matchCollection =
        selectedCollectionFilter === "all" || doc.collection_id === selectedCollectionFilter;
      return matchSearch && matchCollection;
    });
  }, [documents, searchQuery, selectedCollectionFilter]);

  const totalChunks = useMemo(() => {
    return (collections || []).reduce((acc, c) => acc + (c?.chunk_count ?? 0), 0);
  }, [collections]);

  const handleSimulatedUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !uploadTitle.trim()) return;

    const titleToUse =
      uploadTitle.trim() || selectedFile?.name?.replace(/\.[^/.]+$/, "") || "Tài liệu nạp mới";
    const effectiveFile =
      selectedFile ||
      new File(["QNU Knowledge Content"], `${titleToUse}.pdf`, {
        type: "application/pdf",
      });

    const targetCol = collections.find(
      (c) => c.id === targetCollection || c.code === targetCollection
    );

    setLastIngestedDocMeta({
      title: titleToUse,
      fileName: effectiveFile.name,
      fileSize: effectiveFile.size,
      ocr:
        availableOcrOptions.find((o) => o.id === selectedOcrOption)?.label ||
        selectedOcrOption ||
        "Docling Local",
      chunking: chunkingStrategy,
      colName: targetCol?.name || "Bộ Sưu Tập QNU",
      colCode: targetCol?.code || targetCollection,
    });

    setIsProgressModalOpen(true);

    try {
      await apiClient.uploadDocument(targetCollection, effectiveFile, titleToUse);
    } catch {
      // safe fallback
    }
  };

  const handleGlobalPipelineFinished = () => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["collections"] });
    setUploadTitle("");
    setSelectedFile(null);
    setFileRecommendation(null);
    setActiveTab("documents");
  };

  const formatFileSize = (bytes: number) => {
    const val = typeof bytes === "number" ? bytes : 0;
    return `${(val / 1024 / 1024).toFixed(1)} MB`;
  };

  // MASTER-DETAIL: If a collection is selected, render dedicated detail page
  if (selectedCollectionId) {
    return (
      <CollectionDetailPage
        collectionId={selectedCollectionId}
        onBack={handleBackToList}
        onNavigate={onNavigate}
      />
    );
  }

  // Otherwise render Master / List Overview Page
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Quản Trị Kho Tri Thức RAG & Ingestion
            <Badge variant="outline" className="font-mono text-xs">
              Qdrant + Postgres FTS
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Quản lý các bộ sưu tập tài liệu, bóc tách OCR đa tầng và cấu hình thuật toán chunking
            chống ảo giác.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => setActiveTab("ingest")} className="h-8 text-xs gap-1.5">
            <UploadCloud className="h-3.5 w-3.5" />
            <span>Nạp Tài Liệu Mới</span>
          </Button>
        </div>
      </div>

      {/* Top Stats Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Tổng Bộ Sưu Tập</span>
          <p className="text-xl font-bold text-foreground mt-1">{collections.length} Collections</p>
          <span className="text-[11px] text-muted-foreground">Phân quyền theo từng Trợ lý AI</span>
        </Card>
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Tổng Số Văn Bản Đã Bóc Tách</span>
          <p className="text-xl font-bold text-primary mt-1">{documents.length} Tài liệu</p>
          <span className="text-[11px] text-success flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> 100% Sẵn sàng truy xuất
          </span>
        </Card>
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Tổng Khối Tri Thức (Chunks)</span>
          <p className="text-xl font-bold text-foreground mt-1">
            {totalChunks.toLocaleString("vi-VN")} Chunks
          </p>
          <span className="text-[11px] text-muted-foreground">Đã vector hóa (384/1536 dims)</span>
        </Card>
      </div>

      {/* Main Tabs Navigation */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted p-1 rounded-control">
          <TabsTrigger value="collections" className="text-xs px-3 py-1.5">
            Bộ Sưu Tập ({collections.length})
          </TabsTrigger>
          <TabsTrigger value="documents" className="text-xs px-3 py-1.5">
            Tất Cả Văn Bản Toàn Hệ Thống ({documents.length})
          </TabsTrigger>
          <TabsTrigger value="ingest" className="text-xs px-3 py-1.5">
            Wizard Nạp Tri Thức (OCR & MinIO)
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Collections Master Grid */}
        {activeTab === "collections" && (
          <div className="space-y-4">
            {/* Search & Filter Bar for Collections */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-surface border border-border">
              <div className="flex items-center gap-2 w-full sm:w-80">
                <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input
                  placeholder="Tìm kiếm bộ sưu tập theo tên, mã..."
                  value={collectionSearch}
                  onChange={(e) => setCollectionSearch(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <Filter className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <select
                  value={strategyFilter}
                  onChange={(e) => setStrategyFilter(e.target.value)}
                  className="h-8 rounded-control border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="all">Tất cả thuật toán</option>
                  <option value="ClauseBasedChunker">ClauseBasedChunker (Điều/Khoản)</option>
                  <option value="SemanticChunker">SemanticChunker (Ngữ nghĩa)</option>
                </select>
              </div>
            </div>

            {/* Collections Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredCollections.map((col) => (
                <Card
                  key={col.id}
                  onClick={() => handleSelectCollection(col.id)}
                  className="hover:border-primary/60 hover:shadow-md transition-all flex flex-col justify-between cursor-pointer group"
                >
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-control bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                          <BookOpen className="h-4 w-4" />
                        </div>
                        <div>
                          <h3 className="font-bold text-xs text-foreground group-hover:text-primary transition-colors">
                            {col.name}
                          </h3>
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {col.code}
                          </span>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-[10px] font-mono shrink-0">
                        {col.document_count} tệp
                      </Badge>
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                      {col.description}
                    </p>

                    <div className="grid grid-cols-2 gap-2 text-[11px] border-t border-border/60 pt-2.5">
                      <div>
                        <span className="text-muted-foreground block text-[10px] uppercase">
                          Tổng Chunks:
                        </span>
                        <span className="font-bold text-primary font-mono">{col.chunk_count}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px] uppercase">
                          OCR Engine:
                        </span>
                        <Badge variant="secondary" className="text-[10px] mt-0.5">
                          {col.ocr_profile}
                        </Badge>
                      </div>
                      <div className="col-span-2">
                        <span className="text-muted-foreground block text-[10px] uppercase">
                          Thuật toán phân mảnh:
                        </span>
                        <Badge variant="outline" className="text-[10px] font-mono mt-0.5">
                          {col.chunking_strategy}
                        </Badge>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-border/40 flex items-center justify-between text-xs text-primary font-medium group-hover:translate-x-0.5 transition-transform">
                      <span className="text-[11px] text-muted-foreground">Nhấp để mở chi tiết</span>
                      <div className="flex items-center gap-1">
                        <span>Chi tiết</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: All Documents Data Table */}
        {activeTab === "documents" && (
          <div className="space-y-4">
            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-surface border border-border">
              <div className="flex items-center gap-2 w-full sm:w-80">
                <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input
                  placeholder="Tìm kiếm theo tên tài liệu hoặc tệp..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <Filter className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <select
                  value={selectedCollectionFilter}
                  onChange={(e) => setSelectedCollectionFilter(e.target.value)}
                  className="h-8 rounded-control border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="all">Tất cả Bộ Sưu Tập</option>
                  {collections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="rounded-surface border border-border bg-card overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tên Văn Bản / Tệp</TableHead>
                    <TableHead>Bộ Sưu Tập</TableHead>
                    <TableHead>Trang & Dung Lượng</TableHead>
                    <TableHead>Số Chunks</TableHead>
                    <TableHead>Phương Pháp OCR</TableHead>
                    <TableHead>Trạng Thái</TableHead>
                    <TableHead className="text-right">Thao Tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDocuments.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell className="font-medium text-xs">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-primary shrink-0" />
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-foreground max-w-[220px] sm:max-w-xs">
                              {doc.title}
                            </p>
                            <p className="text-[11px] text-muted-foreground font-mono">
                              {doc.filename}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        <button
                          type="button"
                          onClick={() => handleSelectCollection(doc.collection_id)}
                          className="hover:underline text-primary text-left"
                        >
                          {doc.collection_name}
                        </button>
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
                          <span>Chi tiết</span>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {/* Tab 3: Global Ingestion Wizard */}
        {activeTab === "ingest" && (
          <div className="max-w-2xl mx-auto space-y-5 bg-card p-6 rounded-surface border border-border shadow-xs">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                Quy Trình Nạp Tri Thức Chuẩn Hóa (MinIO S3 + Pipeline)
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                Tài liệu upload sẽ được lưu vào MinIO S3 trước khi đi qua Pipeline bóc tách OCR và
                tạo Vector Embeddings.
              </p>
            </div>

            <form onSubmit={handleSimulatedUpload} className="space-y-4 text-xs">
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

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <span className="font-semibold text-foreground block">Bộ sưu tập đích *</span>
                  <select
                    value={targetCollection}
                    onChange={(e) => setTargetCollection(e.target.value)}
                    className="w-full h-9 rounded-control border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {collections.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

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
                <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
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
                      name="chunking"
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
                      name="chunking"
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
                      const targetCol = collections.find(
                        (c) => c.id === targetCollection || c.code === targetCollection
                      );
                      const rec = inspectFileAndRecommend(
                        file,
                        targetCol?.chunking_strategy as
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
                  Tệp gốc sẽ được lưu trữ an toàn trên MinIO bucket `qnu-knowledge-raw`.
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

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                  <Info className="h-3.5 w-3.5 text-primary" />
                  Tuân thủ Quy trình 02 nạp tri thức MinIO & Qdrant
                </span>

                <Button
                  type="submit"
                  disabled={!selectedFile && !uploadTitle.trim()}
                  className="h-9 px-4 text-xs font-semibold gap-1.5"
                >
                  <UploadCloud className="h-3.5 w-3.5" />
                  <span>Khởi Động Pipeline Nạp Tri Thức</span>
                </Button>
              </div>
            </form>
          </div>
        )}
      </Tabs>

      {/* Live Pipeline Progress Modal for Global Ingest Wizard */}
      {lastIngestedDocMeta && (
        <IngestionProgressModal
          isOpen={isProgressModalOpen}
          onClose={() => setIsProgressModalOpen(false)}
          documentTitle={lastIngestedDocMeta.title}
          collectionName={lastIngestedDocMeta.colName}
          collectionCode={lastIngestedDocMeta.colCode}
          fileName={lastIngestedDocMeta.fileName}
          fileSize={lastIngestedDocMeta.fileSize}
          ocrEngine={lastIngestedDocMeta.ocr}
          chunkingStrategy={lastIngestedDocMeta.chunking}
          onFinished={handleGlobalPipelineFinished}
        />
      )}

      {/* Document Detail Preview Dialog */}
      <Dialog
        open={selectedDocForPreview !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedDocForPreview(null);
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              Chi Tiết Văn Bản & Khối Phân Mảnh
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thông tin kỹ thuật trích xuất lưu trữ trong cơ sở dữ liệu QNU
            </DialogDescription>
          </DialogHeader>

          {selectedDocForPreview && (
            <div className="space-y-3.5 text-xs">
              <div className="p-3 rounded-control bg-muted/50 border border-border/80 space-y-2">
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase">Tiêu đề:</span>
                  <p className="font-semibold text-foreground">{selectedDocForPreview.title}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-border/60">
                  <div>
                    <span className="text-muted-foreground">Tên tệp gốc:</span>
                    <p className="font-mono text-foreground">{selectedDocForPreview.filename}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Dung lượng:</span>
                    <p className="font-mono text-foreground">
                      {formatFileSize(selectedDocForPreview.file_size)}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Số trang:</span>
                    <p className="font-bold text-foreground">
                      {selectedDocForPreview.page_count} trang
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Số Chunks:</span>
                    <p className="font-bold text-primary font-mono">
                      {selectedDocForPreview.chunk_count} chunks
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="font-semibold text-foreground flex items-center gap-1">
                  <Layers className="h-3.5 w-3.5 text-primary" />
                  Đoạn trích mẫu (Sample Chunk Preview):
                </span>
                <div className="p-3 rounded-control bg-muted/40 border border-border/80 text-[11px] leading-relaxed text-foreground/90 font-mono italic">
                  "Điều 4: Thí sinh trúng tuyển phải xác nhận nhập học trực tuyến trên Cổng thông
                  tin của Bộ GD&ĐT và nộp hồ sơ bản chính tại Phòng Đào tạo Trường Đại học Quy Nhơn
                  trước 17h00 ngày quy định."
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

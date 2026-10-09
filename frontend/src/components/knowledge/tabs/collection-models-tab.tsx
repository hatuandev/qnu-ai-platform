import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  BookOpen,
  Check,
  Cpu,
  ExternalLink,
  Eye,
  FileText,
  Hash,
  Info,
  Loader2,
  Lock,
  RefreshCw,
  RotateCcw,
  Save,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/services/modelops-api";
import type {
  CollectionDataProcessingConfig,
  KnowledgeCollection,
} from "@/types/knowledge";
import type { ModelOption } from "@/types/modelops";

interface CollectionModelsTabProps {
  collection: KnowledgeCollection;
  configName: string;
  setConfigName: (name: string) => void;
  configDescription: string;
  setConfigDescription: (desc: string) => void;
  dataProcessingConfig: CollectionDataProcessingConfig;
  setDataProcessingConfig: React.Dispatch<
    React.SetStateAction<CollectionDataProcessingConfig>
  >;
  isSaving: boolean;
  onSave: () => void;
}

export function CollectionModelsTab({
  collection,
  configName,
  setConfigName,
  configDescription,
  setConfigDescription,
  dataProcessingConfig,
  setDataProcessingConfig,
  isSaving,
  onSave,
}: CollectionModelsTabProps) {
  const isVectorLocked = (collection.document_count || 0) > 0;

  // Dynamically resolve available models from ModelOps API
  const {
    data: modelDefaults,
    isLoading: isModelsLoading,
    isError: isModelsError,
    refetch: refetchModels,
  } = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    staleTime: 60000,
  });

  const availableEmbeddings: ModelOption[] =
    modelDefaults?.available_embeddings || [];
  const availableOcrs: ModelOption[] = modelDefaults?.available_ocrs || [];

  const currentEmbeddingModel = dataProcessingConfig.embedding_model || "";
  const currentEmbeddingProvider =
    dataProcessingConfig.embedding_provider_id || "";
  const currentPrimaryOcr = dataProcessingConfig.primary_ocr_model || "";
  const currentPrimaryOcrProvider =
    dataProcessingConfig.primary_ocr_provider_id || "";
  const currentFallbackOcr = dataProcessingConfig.fallback_ocr_model || "";
  const currentFallbackOcrProvider =
    dataProcessingConfig.fallback_ocr_provider_id || "";
  const isOcrRescueEnabled = dataProcessingConfig.enable_ocr_rescue !== false;
  const isEmbeddingIncomplete =
    !dataProcessingConfig.embedding_model ||
    !dataProcessingConfig.embedding_provider_id ||
    !dataProcessingConfig.embedding_dimension;

  const handleSelectEmbedding = (item: ModelOption) => {
    if (isVectorLocked) return;
    setDataProcessingConfig((prev) => ({
      ...prev,
      embedding_model: item.model_name,
      embedding_provider_id: item.provider_id,
      embedding_dimension: item.dimension || undefined,
    }));
  };

  const handleSelectPrimaryOcr = (item: ModelOption) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      primary_ocr_model: item.model_name,
      primary_ocr_provider_id: item.provider_id,
    }));
  };

  const handleSelectFallbackOcr = (item: ModelOption) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      fallback_ocr_model: item.model_name,
      fallback_ocr_provider_id: item.provider_id,
    }));
  };

  const handleToggleOcrRescue = (checked: boolean) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      enable_ocr_rescue: checked,
    }));
  };

  const handleReset = () => {
    setConfigName(collection.name);
    setConfigDescription(collection.description || "");
    setDataProcessingConfig(collection.data_processing || {});
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg border border-border bg-card/60 backdrop-blur-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <Cpu className="size-4" />
            </div>
            <h2 className="text-sm sm:text-base font-bold text-foreground">
              Cấu Hình Kho & Ràng Buộc Mô Hình AI
            </h2>
          </div>
          <p className="text-xs text-muted-foreground">
            Thiết lập mô hình Vector Embedding và Vision OCR chuyên trách cho
            kho tri thức &ldquo;{collection.name}&rdquo;.
          </p>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={isSaving}
            className="h-8 text-xs gap-1.5"
          >
            <RotateCcw className="size-3.5" />
            <span>Khôi phục</span>
          </Button>
          <Button
            size="sm"
            onClick={onSave}
            disabled={isSaving || isEmbeddingIncomplete}
            className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-xs"
          >
            <Save className="size-3.5" />
            <span>{isSaving ? "Đang lưu cấu hình..." : "Lưu thay đổi"}</span>
          </Button>
        </div>
      </div>

      {/* 2. Bento Grid 2 Columns: General Info & Vector Embedding */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5/12): General Collection Info */}
        <div className="lg:col-span-5 space-y-6">
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border/60">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <BookOpen className="size-3.5 text-primary" />
                <span>Định Danh & Phạm Vi Tri Thức</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Thông tin nhận diện kho tri thức trong toàn bộ hệ thống
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="models-tab-name"
                  className="text-xs font-semibold text-foreground flex items-center gap-1.5"
                >
                  <span>Tên kho tri thức</span>
                  <span className="text-destructive">*</span>
                </label>
                <Input
                  id="models-tab-name"
                  value={configName}
                  onChange={(e) => setConfigName(e.target.value)}
                  placeholder="VD: Kho Tuyển sinh & Hướng nghiệp 2026"
                  className="h-9 text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="models-tab-code"
                  className="text-xs font-semibold text-foreground flex items-center gap-1.5"
                >
                  <Hash className="size-3 text-muted-foreground" />
                  <span>Mã định danh hệ thống (Code)</span>
                </label>
                <div
                  id="models-tab-code"
                  className="p-2.5 rounded-md bg-muted/50 border border-border flex items-center justify-between"
                >
                  <code className="text-xs font-mono font-medium text-foreground">
                    {collection.code}
                  </code>
                  <Badge variant="outline" className="text-[10px] font-normal">
                    Không thay đổi
                  </Badge>
                </div>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="models-tab-desc"
                  className="text-xs font-semibold text-foreground block"
                >
                  Mô tả chi tiết & phạm vi tài liệu
                </label>
                <Textarea
                  id="models-tab-desc"
                  rows={4}
                  value={configDescription}
                  onChange={(e) => setConfigDescription(e.target.value)}
                  placeholder="Mô tả phạm vi văn bản, đề án, quyết định hoặc cẩm nang nằm trong kho tri thức này..."
                  className="text-xs resize-none"
                />
              </div>

              {/* Status Chips */}
              <div className="pt-2 border-t border-border/60 grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-md bg-muted/30 border border-border/60">
                  <div className="text-[11px] text-muted-foreground">
                    Tài liệu đã index
                  </div>
                  <div className="text-sm font-bold text-foreground mt-0.5 flex items-center gap-1.5">
                    <FileText className="size-3.5 text-primary" />
                    <span>{collection.document_count || 0} tệp</span>
                  </div>
                </div>
                <div className="p-2.5 rounded-md bg-muted/30 border border-border/60">
                  <div className="text-[11px] text-muted-foreground">
                    Đoạn văn (Chunks)
                  </div>
                  <div className="text-sm font-bold text-foreground mt-0.5 font-mono">
                    {collection.chunk_count || 0}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column (7/12): Vector Embedding Space */}
        <div className="lg:col-span-7 space-y-6">
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <Cpu className="size-3.5 text-primary" />
                    <span>Mô Hình Vector Embedding (Không Gian Toán Học)</span>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Mô hình chịu trách nhiệm chuyển văn bản thành vector ngữ
                    nghĩa trong Qdrant
                  </CardDescription>
                </div>
                {isVectorLocked && (
                  <Badge
                    variant="outline"
                    className="text-[10px] gap-1 border-destructive/30 text-destructive"
                  >
                    <Lock className="size-3" />
                    <span>Cố định không gian</span>
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {/* Vector Invariance Alert */}
              {isVectorLocked ? (
                <div className="p-3.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive flex items-start gap-3">
                  <ShieldAlert className="size-4 shrink-0 mt-0.5" />
                  <div className="space-y-1 text-xs leading-relaxed">
                    <p className="font-semibold">
                      Quy tắc Bất biến Không gian Vector (Vector Invariance
                      Rule)
                    </p>
                    <p className="text-[11px] opacity-90 text-foreground">
                      Kho này hiện có{" "}
                      <strong>{collection.document_count}</strong> tài liệu đã
                      được lập chỉ mục vector. Không thể hoán đổi mô hình
                      Embedding giữa chừng để tránh làm sai lệch không gian tìm
                      kiếm hình học. Để đổi mô hình, cần khởi tạo đợt tạo lập
                      chỉ mục mới hoặc di chuyển dữ liệu.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 text-xs text-muted-foreground flex items-center gap-2.5">
                  <Info className="size-4 text-primary shrink-0" />
                  <span>
                    Kho chưa có tài liệu. Bạn có thể tự do lựa chọn mô hình
                    Embedding tối ưu nhất trước khi nạp dữ liệu.
                  </span>
                </div>
              )}

              {/* Embedding Model State Handler */}
              {isModelsLoading ? (
                <div className="flex flex-col items-center justify-center p-8 space-y-2 border border-dashed border-border rounded-lg">
                  <Loader2 className="size-6 animate-spin text-primary" />
                  <span className="text-xs text-muted-foreground">
                    Đang nạp danh mục mô hình từ ModelOps...
                  </span>
                </div>
              ) : isModelsError ? (
                <div className="flex flex-col items-center justify-center p-6 space-y-3 border border-destructive/20 bg-destructive/5 rounded-lg text-center">
                  <AlertCircle className="size-6 text-destructive" />
                  <p className="text-xs text-destructive font-medium">
                    Không thể kết nối tới dịch vụ ModelOps để tải danh mục mô
                    hình
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchModels()}
                    className="h-7 text-xs gap-1.5"
                  >
                    <RefreshCw className="size-3" />
                    <span>Thử lại</span>
                  </Button>
                </div>
              ) : availableEmbeddings.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-6 space-y-3 border border-dashed border-border rounded-lg text-center">
                  <Info className="size-6 text-muted-foreground" />
                  <div className="space-y-1 text-xs">
                    <p className="font-semibold text-foreground">
                      Chưa có mô hình Embedding nào được kích hoạt
                    </p>
                    <p className="text-muted-foreground max-w-sm">
                      Vui lòng truy cập trang Quản lý Mô hình (ModelOps) để bật
                      ít nhất một nhà cung cấp và mô hình Embedding trước khi
                      cấu hình kho tri thức.
                    </p>
                  </div>
                  <Link
                    to="/models"
                    className="inline-flex items-center gap-1.5 text-xs text-primary font-medium hover:underline"
                  >
                    <span>Quản lý ModelOps</span>
                    <ExternalLink className="size-3" />
                  </Link>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {availableEmbeddings.map((item) => {
                    const isSelected =
                      currentEmbeddingModel === item.model_name &&
                      currentEmbeddingProvider === item.provider_id;
                    return (
                      <Button
                        type="button"
                        variant="outline"
                        key={`${item.provider_id}-${item.model_name}`}
                        disabled={isVectorLocked}
                        onClick={() => handleSelectEmbedding(item)}
                        className={`h-auto w-full justify-start whitespace-normal p-3.5 rounded-lg border text-left transition-all ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/40 shadow-xs"
                            : "border-border hover:border-muted-foreground/30 bg-card hover:bg-muted/10"
                        } ${isVectorLocked ? "cursor-not-allowed opacity-80" : "cursor-pointer"}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-xs text-foreground">
                                {item.label || item.model_name}
                              </span>
                              <Badge
                                variant="outline"
                                className="text-[10px] font-mono px-1.5 py-0 h-4"
                              >
                                {item.provider_name}
                              </Badge>
                            </div>
                            <div className="text-[10px] text-muted-foreground/80 flex items-center gap-2 font-mono pt-0.5">
                              <span>Mã: {item.model_name}</span>
                              {item.dimension && (
                                <>
                                  <span>•</span>
                                  <span>
                                    Kích thước: {item.dimension} chiều
                                  </span>
                                </>
                              )}
                            </div>
                          </div>

                          <div className="shrink-0 flex items-center gap-1.5">
                            {isSelected ? (
                              <Badge className="bg-primary text-primary-foreground text-[10px] px-2 py-0.5 gap-1">
                                <Check className="size-3" />
                                <span>Đang áp dụng</span>
                              </Badge>
                            ) : (
                              <span className="text-[10px] text-muted-foreground border border-border px-2 py-0.5 rounded">
                                Chọn
                              </span>
                            )}
                          </div>
                        </div>
                      </Button>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 3. Full-Width Row: Vision OCR & Document Scanning Rescue */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Eye className="size-3.5 text-primary" />
                <span>Mô Hình Thị Giác Vision OCR & Cứu Hộ Văn Bản Quét</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Tự động nhận diện chữ, bảng biểu phức tạp và văn bản scan khi
                tài liệu PDF không có lớp ký tự gốc (Text Layer)
              </CardDescription>
            </div>

            <div className="flex items-center gap-3 p-2 rounded-lg border border-border bg-muted/30 shrink-0">
              <div className="space-y-0.5 text-left">
                <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Sparkles className="size-3 text-primary" />
                  <span>Kích hoạt OCR Rescue</span>
                </div>
                <div className="text-[10px] text-muted-foreground">
                  {isOcrRescueEnabled
                    ? "Tự động kích hoạt khi PDF là scan"
                    : "Đã tắt (chỉ đọc text thô)"}
                </div>
              </div>
              <Switch
                checked={isOcrRescueEnabled}
                onCheckedChange={handleToggleOcrRescue}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6 pt-4">
          {isModelsLoading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="size-5 animate-spin text-primary" />
            </div>
          ) : availableOcrs.length === 0 ? (
            <div className="p-4 border border-dashed border-border rounded-lg text-center text-xs text-muted-foreground">
              Chưa có mô hình Vision OCR nào được cấu hình trong ModelOps.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Primary OCR Model */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-primary" />
                    <span>Mô hình OCR Chính (Primary Model)</span>
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Ưu tiên xử lý đầu tiên
                  </span>
                </div>

                <div className="space-y-2">
                  {availableOcrs.map((item) => {
                    const isSelected =
                      currentPrimaryOcr === item.model_name &&
                      currentPrimaryOcrProvider === item.provider_id;
                    return (
                      <Button
                        type="button"
                        variant="outline"
                        key={`primary-${item.provider_id}-${item.model_name}`}
                        onClick={() => handleSelectPrimaryOcr(item)}
                        className={`h-auto w-full justify-start whitespace-normal p-3 rounded-lg border text-left cursor-pointer transition-all ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/40 shadow-xs"
                            : "border-border hover:border-muted-foreground/30 bg-card hover:bg-muted/10"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-xs text-foreground">
                                {item.label || item.model_name}
                              </span>
                              <Badge
                                variant="outline"
                                className="text-[9px] font-mono px-1 py-0 h-3.5"
                              >
                                {item.provider_name}
                              </Badge>
                            </div>
                            <p className="text-[11px] text-muted-foreground line-clamp-1 font-mono">
                              Mã: {item.model_name}
                            </p>
                          </div>
                          {isSelected && (
                            <Badge className="bg-primary text-primary-foreground text-[10px] px-1.5 py-0 h-4">
                              Chính
                            </Badge>
                          )}
                        </div>
                      </Button>
                    );
                  })}
                </div>
              </div>

              {/* Fallback OCR Model */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-muted-foreground" />
                    <span>Mô hình OCR Dự Phòng (Fallback Model)</span>
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Chuyển mạch khi Primary lỗi/timeout
                  </span>
                </div>

                <div className="space-y-2">
                  {availableOcrs.map((item) => {
                    const isSelected =
                      currentFallbackOcr === item.model_name &&
                      currentFallbackOcrProvider === item.provider_id;
                    return (
                      <Button
                        type="button"
                        variant="outline"
                        key={`fallback-${item.provider_id}-${item.model_name}`}
                        onClick={() => handleSelectFallbackOcr(item)}
                        className={`h-auto w-full justify-start whitespace-normal p-3 rounded-lg border text-left cursor-pointer transition-all ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/40 shadow-xs"
                            : "border-border hover:border-muted-foreground/30 bg-card hover:bg-muted/10"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-xs text-foreground">
                                {item.label || item.model_name}
                              </span>
                              <Badge
                                variant="outline"
                                className="text-[9px] font-mono px-1 py-0 h-3.5"
                              >
                                {item.provider_name}
                              </Badge>
                            </div>
                            <p className="text-[11px] text-muted-foreground line-clamp-1 font-mono">
                              Mã: {item.model_name}
                            </p>
                          </div>
                          {isSelected && (
                            <Badge
                              variant="outline"
                              className="text-[10px] border-primary/40 text-primary px-1.5 py-0 h-4"
                            >
                              Dự phòng
                            </Badge>
                          )}
                        </div>
                      </Button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 4. Bottom Sticky Action Save Bar */}
      <div className="flex justify-end items-center gap-2 pt-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleReset}
          disabled={isSaving}
          className="h-9 text-xs"
        >
          Hủy bỏ thay đổi
        </Button>
        <Button
          size="sm"
          onClick={onSave}
          disabled={isSaving || isEmbeddingIncomplete}
          className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium px-4 shadow-sm"
        >
          <Save className="size-4" />
          <span>{isSaving ? "Đang lưu cấu hình..." : "Lưu Cấu Hình Kho"}</span>
        </Button>
      </div>
    </div>
  );
}

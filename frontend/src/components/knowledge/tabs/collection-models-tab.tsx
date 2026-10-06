import {
  BookOpen,
  Check,
  Cpu,
  Eye,
  FileText,
  Hash,
  Info,
  Lock,
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
import type {
  CollectionDataProcessingConfig,
  KnowledgeCollection,
} from "@/types/knowledge";

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

const AVAILABLE_EMBEDDINGS = [
  {
    model: "bge-m3:latest",
    provider: "prov_rtx5090_ollama",
    label: "BGE-M3 Multilingual (1024D)",
    subLabel: "Máy chủ AI RTX 5090 On-Premise (Nội bộ ĐH Quy Nhơn)",
    dim: 1024,
    recommended: true,
  },
  {
    model: "@cf/baai/bge-m3",
    provider: "prov_cloudflare",
    label: "Cloudflare Workers AI BGE-M3 (1024D)",
    subLabel: "Điện toán đám mây Cloudflare Edge Serverless",
    dim: 1024,
    recommended: false,
  },
  {
    model: "text-embedding-3-small",
    provider: "prov_openai",
    label: "OpenAI Text-Embedding-3 Small (1536D)",
    subLabel: "OpenAI Cloud API (Chất lượng cao, tính phí token)",
    dim: 1536,
    recommended: false,
  },
  {
    model: "text-embedding-3-large",
    provider: "prov_openai",
    label: "OpenAI Text-Embedding-3 Large (3072D)",
    subLabel: "OpenAI Cloud API (Độ phân giải vector ngữ nghĩa tối đa)",
    dim: 3072,
    recommended: false,
  },
];

const AVAILABLE_OCR_MODELS = [
  {
    model: "qwen3-vl:8b",
    provider: "prov_rtx5090_ollama",
    label: "Qwen3-VL 8B Instruct (RTX 5090 On-Premise)",
    subLabel: "Xử lý ảnh scan & cấu trúc bảng tiếng Việt xuất sắc, bảo mật nội bộ",
    recommended: true,
  },
  {
    model: "gemini-3.1-flash-lite",
    provider: "prov_gemini",
    label: "Google Gemini 3.1 Flash Lite",
    subLabel: "Google AI Cloud tốc độ siêu nhanh (<1.2s), chi phí tối ưu",
    recommended: false,
  },
  {
    model: "gemini-2.5-flash",
    provider: "prov_gemini",
    label: "Google Gemini 2.5 Flash",
    subLabel: "Google AI Cloud chất lượng nhận diện văn bản đa phương thức chuẩn mực",
    recommended: false,
  },
  {
    model: "gpt-4o-mini",
    provider: "prov_openai",
    label: "OpenAI GPT-4o-mini Vision",
    subLabel: "OpenAI Multimodal Vision Cloud",
    recommended: false,
  },
  {
    model: "mistral-ocr-2503",
    provider: "prov_mistral",
    label: "Mistral OCR 2503 Document Understanding",
    subLabel: "Chuyên bóc tách văn bản tài liệu và công thức học thuật",
    recommended: false,
  },
];

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

  const currentEmbeddingModel =
    dataProcessingConfig.embedding_model || "bge-m3:latest";
  const currentPrimaryOcr =
    dataProcessingConfig.primary_ocr_model || "qwen3-vl:8b";
  const currentFallbackOcr =
    dataProcessingConfig.fallback_ocr_model || "gemini-3.1-flash-lite";
  const isOcrRescueEnabled =
    dataProcessingConfig.enable_ocr_rescue !== false;

  const handleSelectEmbedding = (item: (typeof AVAILABLE_EMBEDDINGS)[0]) => {
    if (isVectorLocked) return;
    setDataProcessingConfig((prev) => ({
      ...prev,
      embedding_model: item.model,
      embedding_provider_id: item.provider,
      embedding_dimension: item.dim,
    }));
  };

  const handleSelectPrimaryOcr = (item: (typeof AVAILABLE_OCR_MODELS)[0]) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      primary_ocr_model: item.model,
      primary_ocr_provider_id: item.provider,
    }));
  };

  const handleSelectFallbackOcr = (
    item: (typeof AVAILABLE_OCR_MODELS)[0],
  ) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      fallback_ocr_model: item.model,
      fallback_ocr_provider_id: item.provider,
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
    setDataProcessingConfig(
      collection.data_processing || {
        embedding_model: "bge-m3:latest",
        embedding_provider_id: "prov_rtx5090_ollama",
        embedding_dimension: 1024,
        ocr_mode: "combo",
        primary_ocr_model: "qwen3-vl:8b",
        primary_ocr_provider_id: "prov_rtx5090_ollama",
        fallback_ocr_model: "gemini-3.1-flash-lite",
        fallback_ocr_provider_id: "prov_gemini",
        enable_ocr_rescue: true,
      },
    );
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
            Thiết lập mô hình Vector Embedding và Vision OCR chuyên trách cho kho tri thức &ldquo;{collection.name}&rdquo;.
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
            disabled={isSaving}
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
                <div className="p-2.5 rounded-md bg-muted/50 border border-border flex items-center justify-between">
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
                  <div className="text-[11px] text-muted-foreground">Tài liệu đã index</div>
                  <div className="text-sm font-bold text-foreground mt-0.5 flex items-center gap-1.5">
                    <FileText className="size-3.5 text-primary" />
                    <span>{collection.document_count || 0} tệp</span>
                  </div>
                </div>
                <div className="p-2.5 rounded-md bg-muted/30 border border-border/60">
                  <div className="text-[11px] text-muted-foreground">Đoạn văn (Chunks)</div>
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
                    Mô hình chịu trách nhiệm chuyển văn bản thành vector ngữ nghĩa trong Qdrant
                  </CardDescription>
                </div>
                {isVectorLocked && (
                  <Badge variant="outline" className="text-[10px] gap-1 border-amber-500/30 text-amber-600 dark:text-amber-400">
                    <Lock className="size-3" />
                    <span>Cố định không gian</span>
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {/* Vector Invariance Alert */}
              {isVectorLocked ? (
                <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-400 flex items-start gap-3">
                  <ShieldAlert className="size-4 shrink-0 mt-0.5 text-amber-600" />
                  <div className="space-y-1 text-xs leading-relaxed">
                    <p className="font-semibold text-amber-800 dark:text-amber-300">
                      Quy tắc Bất biến Không gian Vector (Vector Invariance Rule)
                    </p>
                    <p className="text-[11px] opacity-90">
                      Kho này hiện có <strong>{collection.document_count}</strong> tài liệu đã được lập chỉ mục vector.
                      Không thể hoán đổi mô hình Embedding giữa chừng để tránh làm sai lệch không gian tìm kiếm hình học. Để đổi mô hình, vui lòng xóa toàn bộ tài liệu trong kho trước.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 text-xs text-muted-foreground flex items-center gap-2.5">
                  <Info className="size-4 text-primary shrink-0" />
                  <span>
                    Kho chưa có tài liệu. Bạn có thể tự do lựa chọn mô hình Embedding tối ưu nhất trước khi nạp dữ liệu.
                  </span>
                </div>
              )}

              {/* Embedding Model List */}
              <div className="space-y-2.5">
                {AVAILABLE_EMBEDDINGS.map((item) => {
                  const isSelected = currentEmbeddingModel === item.model;
                  return (
                    <div
                      key={item.model}
                      onClick={() => handleSelectEmbedding(item)}
                      className={`p-3.5 rounded-lg border text-left transition-all ${
                        isSelected
                          ? "border-primary bg-primary/5 ring-1 ring-primary/40 shadow-xs"
                          : "border-border hover:border-muted-foreground/30 bg-card hover:bg-muted/10"
                      } ${isVectorLocked ? "cursor-not-allowed opacity-80" : "cursor-pointer"}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-foreground">
                              {item.label}
                            </span>
                            {item.recommended && (
                              <Badge className="bg-primary/20 text-primary border-primary/30 text-[10px] px-1.5 py-0 h-4">
                                Khuyến nghị
                              </Badge>
                            )}
                          </div>
                          <p className="text-[11px] text-muted-foreground">
                            {item.subLabel}
                          </p>
                          <div className="text-[10px] text-muted-foreground/80 flex items-center gap-2 font-mono pt-0.5">
                            <span>Mã: {item.model}</span>
                            <span>•</span>
                            <span>Kích thước: {item.dim} chiều</span>
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
                    </div>
                  );
                })}
              </div>
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
                Tự động nhận diện chữ, bảng biểu phức tạp và văn bản scan khi tài liệu PDF không có lớp ký tự gốc (Text Layer)
              </CardDescription>
            </div>

            <div className="flex items-center gap-3 p-2 rounded-lg border border-border bg-muted/30 shrink-0">
              <div className="space-y-0.5 text-left">
                <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Sparkles className="size-3 text-primary" />
                  <span>Kích hoạt OCR Rescue</span>
                </div>
                <div className="text-[10px] text-muted-foreground">
                  {isOcrRescueEnabled ? "Tự động kích hoạt khi PDF là scan" : "Đã tắt (chỉ đọc text thô)"}
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Primary OCR Model */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-primary" />
                  <span>Mô hình OCR Chính (Primary Model)</span>
                </label>
                <span className="text-[10px] text-muted-foreground">
                  Ưu tiên xử lý đầu tiên
                </span>
              </div>

              <div className="space-y-2">
                {AVAILABLE_OCR_MODELS.map((item) => {
                  const isSelected = currentPrimaryOcr === item.model;
                  return (
                    <div
                      key={`primary-${item.model}`}
                      onClick={() => handleSelectPrimaryOcr(item)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? "border-primary bg-primary/5 ring-1 ring-primary/40 shadow-xs"
                          : "border-border hover:border-muted-foreground/30 bg-card hover:bg-muted/10"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-xs text-foreground">
                              {item.label}
                            </span>
                            {item.recommended && (
                              <Badge className="bg-primary/20 text-primary border-primary/30 text-[9px] px-1 py-0 h-3.5">
                                Khuyên dùng
                              </Badge>
                            )}
                          </div>
                          <p className="text-[11px] text-muted-foreground line-clamp-1">
                            {item.subLabel}
                          </p>
                        </div>
                        {isSelected && (
                          <Badge className="bg-primary text-primary-foreground text-[10px] px-1.5 py-0 h-4">
                            Chính
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Fallback OCR Model */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-amber-500" />
                  <span>Mô hình OCR Dự Phòng (Fallback Model)</span>
                </label>
                <span className="text-[10px] text-muted-foreground">
                  Chuyển mạch khi Primary lỗi/timeout
                </span>
              </div>

              <div className="space-y-2">
                {AVAILABLE_OCR_MODELS.map((item) => {
                  const isSelected = currentFallbackOcr === item.model;
                  return (
                    <div
                      key={`fallback-${item.model}`}
                      onClick={() => handleSelectFallbackOcr(item)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? "border-amber-500 bg-amber-500/5 ring-1 ring-amber-500/40 shadow-xs"
                          : "border-border hover:border-muted-foreground/30 bg-card hover:bg-muted/10"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-xs text-foreground">
                              {item.label}
                            </span>
                          </div>
                          <p className="text-[11px] text-muted-foreground line-clamp-1">
                            {item.subLabel}
                          </p>
                        </div>
                        {isSelected && (
                          <Badge
                            variant="outline"
                            className="text-[10px] border-amber-500/40 text-amber-600 dark:text-amber-400 px-1.5 py-0 h-4"
                          >
                            Dự phòng
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
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
          disabled={isSaving}
          className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium px-4 shadow-sm"
        >
          <Save className="size-4" />
          <span>{isSaving ? "Đang lưu cấu hình..." : "Lưu Cấu Hình Kho"}</span>
        </Button>
      </div>
    </div>
  );
}

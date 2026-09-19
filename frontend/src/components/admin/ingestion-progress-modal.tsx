import { Check, CheckCircle2, Loader2, Sparkles, UploadCloud } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";

export interface IngestionProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentTitle: string;
  collectionName: string;
  collectionCode: string;
  fileName: string;
  fileSize: number;
  ocrEngine: string;
  chunkingStrategy: string;
  activeStage?: number;
  isComplete?: boolean;
  stageDurations?: Record<number, number>;
  onFinished?: () => void;
}

interface PipelineStage {
  id: number;
  title: string;
  subtitle: string;
  description: string;
  detail: string;
}

export const IngestionProgressModal: React.FC<IngestionProgressModalProps> = ({
  isOpen,
  onClose,
  documentTitle,
  collectionName,
  collectionCode,
  fileName,
  fileSize,
  ocrEngine,
  chunkingStrategy,
  activeStage = 1,
  isComplete = false,
  stageDurations = {},
  onFinished,
}) => {
  const [currentStage, setCurrentStage] = useState<number>(activeStage);
  const [isDone, setIsDone] = useState<boolean>(isComplete);

  useEffect(() => {
    setCurrentStage(activeStage);
  }, [activeStage]);

  useEffect(() => {
    setIsDone(isComplete);
    if (isComplete && onFinished) {
      onFinished();
    }
  }, [isComplete, onFinished]);

  const formatFileSize = (bytes: number) => {
    if (!bytes) return "0.0 MB";
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const stages: PipelineStage[] = [
    {
      id: 1,
      title: "Chặng 1: Lưu Trữ Tệp Gốc MinIO S3",
      subtitle: "MinIO Object Storage",
      description: "Đẩy tệp nhị phân gốc lên MinIO bucket lưu trữ phân tán an toàn",
      detail: `Bucket: qnu-knowledge-raw/${collectionCode || "default"}/${fileName || "document.pdf"} (${formatFileSize(fileSize)})`,
    },
    {
      id: 2,
      title: "Chặng 2: Phân Tích Cấu Trúc & Bóc Tách OCR",
      subtitle: ocrEngine || "Docling TableFormer",
      description: "Nhận diện cấu trúc đoạn văn bản, tái tạo bảng số liệu và tiêu đề",
      detail: `Engine: ${ocrEngine || "Docling Local"} — Bóc tách native text và phục hồi hình học bảng`,
    },
    {
      id: 3,
      title: "Chặng 3: Chuẩn Hóa & Phân Mảnh (Chunking)",
      subtitle: chunkingStrategy || "ClauseBasedChunker",
      description: "Phân mảnh văn bản theo ngữ nghĩa hoặc chuẩn Điều/Khoản quy phạm",
      detail: `Thuật toán: ${chunkingStrategy || "ClauseBasedChunker"} — Tối ưu hóa kích thước chunk & overlap`,
    },
    {
      id: 4,
      title: "Chặng 4: Vector Indexing & Cơ Sở Dữ Liệu FTS",
      subtitle: "Qdrant 1024D + PostgreSQL FTS",
      description: "Tạo vector embeddings nạp vào Qdrant và đánh chỉ mục tìm kiếm từ khóa",
      detail: `Collection: ${collectionCode || "knowledge"}_dense — Sẵn sàng cho Hybrid RRF (k=60)`,
    },
  ];

  const progressPercent = Math.min(100, Math.round(((currentStage - 1) / 4) * 100));

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && isDone && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-base font-bold flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-control bg-primary/10 flex items-center justify-center text-primary">
                <UploadCloud className="h-4 w-4" />
              </div>
              <span>Tiến Trình Pipeline Bóc Tách Tri Thức</span>
            </div>
            <Badge variant={isDone ? "success" : "outline"} className="text-[10px] font-mono gap-1">
              {isDone ? (
                <>
                  <Check className="h-3 w-3" /> HOÀN TẤT 100%
                </>
              ) : (
                <>
                  <Loader2 className="h-3 w-3 animate-spin text-primary" /> CHẶNG{" "}
                  {Math.min(4, currentStage)}/4
                </>
              )}
            </Badge>
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Tài liệu: <strong className="text-foreground">{documentTitle || fileName}</strong> • Bộ
            sưu tập: <span className="text-primary font-medium">{collectionName}</span>
          </DialogDescription>
        </DialogHeader>

        {/* Dynamic Progress Bar */}
        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              {isDone
                ? "Bóc tách & Index thành công vào cơ sở dữ liệu tri thức"
                : `Đang thực thi chặng ${Math.min(4, currentStage)}: ${stages[Math.min(3, currentStage - 1)]?.subtitle}`}
            </span>
            <span className="font-mono font-bold text-primary">{progressPercent}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* 4 Pipeline Stages List */}
        <div className="space-y-2.5 pt-2">
          {stages.map((st) => {
            const isCompleted = currentStage > st.id;
            const isRunning = currentStage === st.id;
            const isPending = currentStage < st.id;

            return (
              <div
                key={st.id}
                className={`p-3 rounded-control border transition-all ${
                  isRunning
                    ? "border-primary/50 bg-primary/5 ring-1 ring-primary/30"
                    : isCompleted
                      ? "border-border bg-card/80"
                      : "border-border/40 bg-muted/20 opacity-60"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5">
                    <div
                      className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-mono shrink-0 mt-0.5 ${
                        isCompleted
                          ? "bg-success/15 text-success font-bold"
                          : isRunning
                            ? "bg-primary text-primary-foreground font-bold"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {isCompleted ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : isRunning ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        st.id
                      )}
                    </div>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`text-xs font-bold ${
                            isRunning
                              ? "text-primary"
                              : isCompleted
                                ? "text-foreground"
                                : "text-muted-foreground"
                          }`}
                        >
                          {st.title}
                        </span>
                        <Badge variant="secondary" className="text-[9px] font-mono px-1.5 py-0 h-4">
                          {st.subtitle}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        {st.description}
                      </p>
                      <p className="text-[10px] font-mono text-muted-foreground/80 pt-0.5">
                        {st.detail}
                      </p>
                    </div>
                  </div>

                  <div className="shrink-0 text-right">
                    {isCompleted && (
                      <Badge variant="success" className="text-[9px] font-mono px-1.5 py-0 h-4">
                        ✓ {stageDurations[st.id] ? `${stageDurations[st.id]}ms` : "OK"}
                      </Badge>
                    )}
                    {isRunning && (
                      <Badge
                        variant="outline"
                        className="text-[9px] font-mono px-1.5 py-0 h-4 border-primary/40 text-primary bg-primary/10 animate-pulse"
                      >
                        Đang chạy...
                      </Badge>
                    )}
                    {isPending && (
                      <span className="text-[10px] text-muted-foreground font-mono">Chờ</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-border">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
            <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
            MinIO S3 • Qdrant Vector • RFC 7807 Safe
          </span>
          <Button
            type="button"
            disabled={!isDone}
            onClick={onClose}
            className="h-9 px-5 text-xs font-semibold gap-1.5"
          >
            {isDone ? (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>Xem Tài Liệu Trong Bảng</span>
              </>
            ) : (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Đang xử lý...</span>
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

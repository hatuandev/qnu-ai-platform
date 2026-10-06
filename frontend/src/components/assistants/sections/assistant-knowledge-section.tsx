import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { KnowledgeCollection } from "@/types";
import { ArrowUpDown, ExternalLink, Info, Library } from "lucide-react";

interface AssistantKnowledgeSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  collections: KnowledgeCollection[];
  onNavigate: (path: string) => void;
}

const AVAILABLE_RERANKER_MODELS = [
  {
    value: "bge-reranker-base",
    label: "BGE Reranker Base (BAAI On-Premise / Cloud) - Khuyến nghị",
    description: "Cân bằng hoàn hảo giữa độ chính xác tiếng Việt và tốc độ",
  },
  {
    value: "bge-reranker-large",
    label: "BGE Reranker Large (BAAI Cross-Encoder)",
    description: "Độ chính xác cao nhất cho văn bản học thuật / quy chế phức tạp",
  },
  {
    value: "ms-marco-MiniLM-L-6-v2",
    label: "MS-MARCO MiniLM L6 v2 (Tốc độ siêu nhanh)",
    description: "Tối ưu hóa độ trễ thấp, phù hợp hỏi đáp thông thường",
  },
  {
    value: "cohere-rerank-v3",
    label: "Cohere Rerank v3 (Cloud API)",
    description: "Mô hình thương mại điện toán đám mây của Cohere",
  },
];

export function AssistantKnowledgeSection({
  form,
  onChange,
  collections,
  onNavigate,
}: AssistantKnowledgeSectionProps) {
  const selectedCollection = collections.find((c) => c.id === form.collection_id);

  return (
    <div className="space-y-4">
      {/* CARD 1: Kho Tri Thức RAG */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <Library className="size-4 text-primary" />
            <span>Gắn Kết Kho Tri Thức RAG</span>
          </CardTitle>
          <CardDescription className="text-xs">
            Kho tri thức chuyên trách cung cấp căn cứ dữ liệu chính thức của ĐH Quy Nhơn cho Trợ lý.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field htmlFor="detail-assistant-collection" label="Kho Tri Thức (Collection)">
            <div className="space-y-2">
              <Select
                value={form.collection_id}
                onValueChange={(val) => onChange({ ...form, collection_id: val })}
              >
                <SelectTrigger id="detail-assistant-collection">
                  <SelectValue placeholder="Chọn kho tri thức" />
                </SelectTrigger>
                <SelectContent>
                  {collections.map((col) => (
                    <SelectItem key={col.id} value={col.id}>
                      {col.name} ({col.document_count} tài liệu)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {form.collection_id && (
                <Button
                  className="w-full h-8 text-xs gap-1.5"
                  type="button"
                  variant="outline"
                  onClick={() => onNavigate(`/knowledge/${encodeURIComponent(form.collection_id)}`)}
                >
                  <Library className="size-3.5 text-primary" />
                  Mở chi tiết kho: {selectedCollection?.name || form.collection_id}
                  <ExternalLink className="size-3 ml-auto opacity-50" />
                </Button>
              )}
            </div>
          </Field>
        </CardContent>
      </Card>

      {/* CARD 2: Cấu Hình Cross-Encoder Reranker */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <ArrowUpDown className="size-4 text-primary" />
                <span>Xếp Hạng Lại (Cross-Encoder Reranker)</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Đánh giá ngữ nghĩa chuyên sâu cặp câu hỏi - tài liệu trước khi đưa vào ngữ cảnh LLM.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">
                {form.reranker_enabled ? "Đang bật" : "Đã tắt"}
              </span>
              <Switch
                checked={form.reranker_enabled}
                onCheckedChange={(checked) => onChange({ ...form, reranker_enabled: checked })}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.reranker_enabled ? (
            <div className="space-y-4 pt-1">
              <Field htmlFor="detail-reranker-model" label="Mô hình Reranker">
                <Select
                  value={form.reranker_model || "bge-reranker-base"}
                  onValueChange={(val) => onChange({ ...form, reranker_model: val })}
                >
                  <SelectTrigger id="detail-reranker-model">
                    <SelectValue placeholder="Chọn mô hình Cross-Encoder" />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_RERANKER_MODELS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        <div className="flex flex-col text-left py-0.5">
                          <span className="font-medium text-xs text-foreground">{item.label}</span>
                          <span className="text-[10px] text-muted-foreground">{item.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field
                  htmlFor="detail-reranker-top-k"
                  label="Top K Chunks Sau Khi Rerank"
                  hint="Số lượng đoạn văn bản điểm cao nhất được giữ lại để trả lời"
                >
                  <Input
                    id="detail-reranker-top-k"
                    type="number"
                    min={1}
                    max={20}
                    value={form.reranker_top_k ?? 5}
                    onChange={(e) =>
                      onChange({
                        ...form,
                        reranker_top_k: Number.parseInt(e.target.value, 10) || 5,
                      })
                    }
                    className="h-9 text-xs font-mono"
                  />
                </Field>

                <Field
                  htmlFor="detail-reranker-threshold"
                  label="Ngưỡng Điểm Phù Hợp (Score Threshold)"
                  hint="Loại bỏ các đoạn trích có điểm tương đồng thấp hơn ngưỡng này"
                >
                  <Input
                    id="detail-reranker-threshold"
                    type="number"
                    step="0.05"
                    min={0.0}
                    max={1.0}
                    value={form.reranker_score_threshold ?? 0.4}
                    onChange={(e) =>
                      onChange({
                        ...form,
                        reranker_score_threshold: Number.parseFloat(e.target.value) || 0.4,
                      })
                    }
                    className="h-9 text-xs font-mono"
                  />
                </Field>
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-lg border border-border bg-muted/30 text-xs text-muted-foreground flex items-start gap-2.5">
              <Info className="size-4 text-primary shrink-0 mt-0.5" />
              <div className="space-y-1 leading-relaxed">
                <p className="font-medium text-foreground">
                  Chế độ truy xuất RAG không qua Cross-Encoder
                </p>
                <p>
                  Khi tắt Reranker, trợ lý sẽ lấy kết quả Top RRF trực tiếp từ Vector Search (Qdrant)
                  và Full-Text Search (PostgreSQL). Giúp phản hồi cực nhanh (0ms độ trễ Reranker),
                  phù hợp với các tác vụ hỏi đáp thông thường.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

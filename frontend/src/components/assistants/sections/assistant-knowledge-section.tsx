import { ArrowUpDown, ExternalLink, Info, Library } from "lucide-react";
import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  type AssistantModelOption,
  selectedModelValue,
} from "@/features/assistants/model-options";
import { RetrievalPolicyCard } from "@/features/assistants/retrieval-policy-card";
import type { KnowledgeCollection } from "@/types";

interface AssistantKnowledgeSectionProps {
  availableModels?: AssistantModelOption[];
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  collections: KnowledgeCollection[];
  onNavigate: (path: string) => void;
}

export function AssistantKnowledgeSection({
  availableModels = [],
  form,
  onChange,
  collections,
  onNavigate,
}: AssistantKnowledgeSectionProps) {
  const selectedCollection = collections.find(
    (c) => c.id === form.collection_id,
  );

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
            Kho tri thức chuyên trách cung cấp căn cứ dữ liệu chính thức của ĐH
            Quy Nhơn cho Trợ lý.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field
            htmlFor="detail-assistant-collection"
            label="Kho Tri Thức (Collection)"
          >
            <div className="space-y-2">
              <Select
                value={form.collection_id}
                onValueChange={(val) =>
                  onChange({ ...form, collection_id: val })
                }
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
                  onClick={() =>
                    onNavigate(
                      `/knowledge/${encodeURIComponent(form.collection_id)}`,
                    )
                  }
                >
                  <Library className="size-3.5 text-primary" />
                  Mở chi tiết kho:{" "}
                  {selectedCollection?.name || form.collection_id}
                  <ExternalLink className="size-3 ml-auto opacity-50" />
                </Button>
              )}
            </div>
          </Field>
        </CardContent>
      </Card>

      <RetrievalPolicyCard form={form} onChange={onChange} />
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
                Đánh giá ngữ nghĩa chuyên sâu cặp câu hỏi - tài liệu trước khi
                đưa vào ngữ cảnh LLM.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">
                {form.reranker_enabled ? "Đang bật" : "Đã tắt"}
              </span>
              <Switch
                checked={form.reranker_enabled ?? true}
                onCheckedChange={(checked) =>
                  onChange({ ...form, reranker_enabled: checked })
                }
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {(form.reranker_enabled ?? true) ? (
            <div className="space-y-4 pt-1">
              <Field htmlFor="detail-reranker-model" label="Mô hình Reranker">
                <Select
                  value={selectedModelValue(
                    availableModels,
                    form.reranker_model,
                    form.reranker_provider_id,
                  )}
                  onValueChange={(val) =>
                    onChange({
                      ...form,
                      reranker_model:
                        availableModels.find((m) => m.value === val)?.model ??
                        "",
                      reranker_provider_id:
                        availableModels.find((m) => m.value === val)
                          ?.providerId ?? "",
                    })
                  }
                >
                  <SelectTrigger id="detail-reranker-model">
                    <SelectValue placeholder="Chọn mô hình Cross-Encoder" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">Mặc định ModelOps</SelectItem>
                    {availableModels.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        <div className="flex flex-col text-left py-0.5">
                          <span className="font-medium text-xs text-foreground">
                            {item.label}
                          </span>
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
                  hint={
                    form.retrieval_policy?.profile === "configured"
                      ? "Chế độ Tùy chỉnh dùng Đoạn ngữ cảnh chính ở trên thay cho ô này."
                      : "Số lượng đoạn văn bản điểm cao nhất được giữ lại để trả lời"
                  }
                >
                  <Input
                    id="detail-reranker-top-k"
                    type="number"
                    disabled={form.retrieval_policy?.profile === "configured"}
                    min={1}
                    max={20}
                    value={form.reranker_top_k ?? 5}
                    onChange={(e) =>
                      onChange({
                        ...form,
                        reranker_top_k:
                          Number.parseInt(e.target.value, 10) || 5,
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
                        reranker_score_threshold: Number.isFinite(
                          Number(e.target.value),
                        )
                          ? Number(e.target.value)
                          : 0.4,
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
                  Khi tắt Reranker, trợ lý sẽ lấy kết quả Top RRF trực tiếp từ
                  Vector Search (Qdrant) và Full-Text Search (PostgreSQL). Giúp
                  phản hồi cực nhanh (0ms độ trễ Reranker), phù hợp với các tác
                  vụ hỏi đáp thông thường.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

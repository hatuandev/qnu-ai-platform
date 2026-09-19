import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { KnowledgeCollection } from "@/types";
import { ExternalLink, Library, Sparkles } from "lucide-react";

interface AssistantKnowledgeSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  collections: KnowledgeCollection[];
  onNavigate: (path: string) => void;
}

export function AssistantKnowledgeSection({
  form,
  onChange,
  collections,
  onNavigate,
}: AssistantKnowledgeSectionProps) {
  const selectedCollection = collections.find((c) => c.id === form.collection_id);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-bold">Gắn Kết Kho Tri Thức RAG</CardTitle>
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

        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-foreground">
            <Sparkles className="size-3.5 text-primary" />
            Khuyến nghị Chiến lược Chunking & RAG
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            - <strong>ClauseBasedChunker</strong>: Phù hợp cho văn bản quy phạm, quy chế đào tạo, đề
            án tuyển sinh (bảo toàn trọn vẹn Điều, Khoản, Mục).
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            - <strong>SemanticChunker</strong>: Phù hợp cho cẩm nang sinh viên, giới thiệu khoa
            viện, tài liệu văn xuôi mô tả tổng quan.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

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
import { ExternalLink, Library } from "lucide-react";

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
      </CardContent>
    </Card>
  );
}

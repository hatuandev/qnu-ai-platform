import { ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import type { KnowledgeBinding } from "@/types/knowledge";

export function BulkSourceReview({
  sources,
  isPending,
  onReview,
}: {
  sources: KnowledgeBinding[];
  isPending: boolean;
  onReview: (sources: KnowledgeBinding[]) => void;
}) {
  const sourceIds = useMemo(
    () => sources.map((source) => source.id),
    [sources],
  );
  const [selected, setSelected] = useState<string[]>(sourceIds);

  useEffect(() => setSelected(sourceIds), [sourceIds]);

  return (
    <div className="space-y-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-foreground">
            {sources.length} nguồn cần xác nhận dữ liệu cấu trúc
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Chọn các nguồn bạn đã đối soát trong Studio OCR trước khi duyệt.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={!selected.length || isPending}
          onClick={() =>
            onReview(sources.filter((source) => selected.includes(source.id)))
          }
        >
          <ShieldCheck className="size-3.5" />
          Duyệt đã chọn
        </Button>
      </div>
      <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
        {sources.map((source) => {
          const checkboxId = `review-${source.id}`;
          return (
            <div
              key={source.id}
              className="flex items-start gap-2 rounded-md px-2 py-1.5 hover:bg-background/70"
            >
              <Checkbox
                id={checkboxId}
                checked={selected.includes(source.id)}
                onCheckedChange={(checked) =>
                  setSelected((current) =>
                    checked
                      ? [...new Set([...current, source.id])]
                      : current.filter((id) => id !== source.id),
                  )
                }
                aria-label={`Chọn ${source.document_title || source.id}`}
              />
              <label
                htmlFor={checkboxId}
                className="min-w-0 cursor-pointer text-xs"
              >
                <span className="block break-words text-foreground">
                  {source.document_title || source.id}
                </span>
                <span className="text-muted-foreground">
                  {source.structured_issue_count || 0} điểm cần xác nhận
                </span>
              </label>
            </div>
          );
        })}
      </div>
    </div>
  );
}

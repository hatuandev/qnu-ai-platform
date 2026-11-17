import { useState } from "react";
import { toast } from "sonner";
import {
  type SpellingDefaults,
  useSpellingDefaults,
} from "@/api/ocr/spelling-defaults";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";

const fields = [
  { key: "ocr", label: "Chữ nhận dạng từ ảnh (OCR)" },
  { key: "pdf_text", label: "Chữ đọc trực tiếp từ PDF" },
  { key: "word_text", label: "Chữ đọc trực tiếp từ Word" },
] as const;

export function SpellingDefaultsPanel() {
  const { query, update } = useSpellingDefaults();
  const [edits, setEdits] = useState<Partial<SpellingDefaults>>({});
  const policy = query.data;

  if (query.isPending) return <Skeleton className="h-48 w-full" />;
  if (query.isError || !policy) {
    return (
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p role="alert">Không tải được cài đặt soát chính tả.</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void query.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  }

  const values = { ...policy, ...edits };
  const isDirty = fields.some(({ key }) => values[key] !== policy[key]);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold">Tự động soát chính tả</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Áp dụng toàn hệ thống sau khi bóc tách. Người dùng vẫn có thể tự soát
          toàn bộ văn bản trong màn hình tài liệu.
        </p>
      </div>
      <div className="divide-y divide-border border-y border-border">
        {fields.map(({ key, label }) => (
          <div
            key={key}
            className="flex items-center justify-between gap-4 py-3"
          >
            <Label htmlFor={`spelling-${key}`}>{label}</Label>
            <Switch
              id={`spelling-${key}`}
              checked={values[key]}
              disabled={update.isPending}
              onCheckedChange={(checked) =>
                setEdits((previous) => ({ ...previous, [key]: checked }))
              }
            />
          </div>
        ))}
      </div>
      <Button
        disabled={!isDirty || update.isPending}
        onClick={() =>
          update.mutate(values, {
            onSuccess: () => {
              setEdits({});
              toast.success("Đã lưu cài đặt soát chính tả.");
            },
            onError: () => toast.error("Chưa lưu được cài đặt soát chính tả."),
          })
        }
      >
        {update.isPending ? "Đang lưu…" : "Lưu thay đổi"}
      </Button>
    </section>
  );
}

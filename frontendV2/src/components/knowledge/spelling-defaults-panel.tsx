import { Info } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  type SpellingDefaults,
  useSpellingDefaults,
} from "@/api/ocr/spelling-defaults";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";

const fields = [
  { key: "ocr", label: "Chữ nhận dạng từ ảnh (OCR)" },
  { key: "pdf_text", label: "Chữ đọc trực tiếp từ PDF" },
  { key: "word_text", label: "Chữ đọc trực tiếp từ Word" },
] as const;

const PASS_OPTIONS = [
  {
    value: 1,
    title: "1 lượt",
    desc: "Chỉ rà soát lỗi nhận dạng ký tự & dấu OCR",
  },
  {
    value: 2,
    title: "2 lượt (Mặc định)",
    desc: "Lượt 1: Ký tự & dấu OCR; Lượt 2: Ngữ cảnh & thuật ngữ/bảng biểu",
  },
  {
    value: 3,
    title: "3 lượt",
    desc: "Bổ sung rà soát ngữ pháp câu và cấu trúc liên kết",
  },
  {
    value: 4,
    title: "4 lượt",
    desc: "Rà soát toàn diện tối đa nhiều tầng ngữ nghĩa",
  },
];

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
  const isDirty =
    fields.some(({ key }) => values[key] !== policy[key]) ||
    (values.total_passes ?? 2) !== (policy.total_passes ?? 2);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-base font-semibold">Tự động soát chính tả</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Áp dụng toàn hệ thống sau khi bóc tách. Người dùng vẫn có thể tự soát
          toàn bộ văn bản trong màn hình tài liệu.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-muted/40 p-3.5 flex items-start gap-3 text-xs text-muted-foreground">
        <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-foreground">Nhóm model thực thi:</strong>{" "}
          Luồng soát chính tả tự động sử dụng danh sách model và cơ chế điều
          phối (Ưu tiên / Song song work-stealing) được cấu hình tại mục{" "}
          <strong className="text-foreground">Xử lý văn bản</strong>, độc lập
          với model hội thoại của trợ lý AI.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="spelling-total-passes" className="text-sm font-medium">
          Số lượt soát chính tả tự động (Multi-Pass)
        </Label>
        <Select
          value={String(values.total_passes ?? 2)}
          disabled={update.isPending}
          onValueChange={(val) =>
            setEdits((prev) => ({ ...prev, total_passes: Number(val) }))
          }
        >
          <SelectTrigger
            id="spelling-total-passes"
            className="w-full sm:w-[380px]"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PASS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={String(opt.value)}>
                <div className="flex flex-col text-left py-0.5">
                  <span className="font-medium">{opt.title}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {opt.desc}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Các lượt chạy nối tiếp bất đồng bộ, kế thừa các quyết định bỏ qua và
          khử trùng lặp giữa các lượt.
        </p>
      </div>

      <div className="space-y-1">
        <Label className="text-sm font-medium">
          Phạm vi tài liệu tự động soát
        </Label>
        <div className="divide-y divide-border border-y border-border">
          {fields.map(({ key, label }) => (
            <div
              key={key}
              className="flex items-center justify-between gap-4 py-3"
            >
              <Label
                htmlFor={`spelling-${key}`}
                className="cursor-pointer font-normal text-sm"
              >
                {label}
              </Label>
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

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, Plus } from "lucide-react";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";
import { Field } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  createDocumentType,
  type DocumentTypeCategory,
  type DocumentTypeInput,
  type DocumentTypeItem,
} from "@/services/document-types-api";

interface CreateDocumentTypeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (created: DocumentTypeItem) => void;
}

const CATEGORY_OPTIONS: Array<{
  value: DocumentTypeCategory;
  label: string;
  desc: string;
}> = [
  {
    value: "legal_internal",
    label: "Quy phạm & Nội bộ",
    desc: "Nghị quyết, Quyết định, Quy chế, Quy định, Điều lệ",
  },
  {
    value: "administrative",
    label: "Hành chính Điều hành",
    desc: "Thông báo, Công văn, Tờ trình, Báo cáo, Kế hoạch, Biên bản",
  },
  {
    value: "academic",
    label: "Đào tạo & Học thuật",
    desc: "Đề án tuyển sinh, Chương trình đào tạo, Đề cương, Giáo trình",
  },
  {
    value: "forms",
    label: "Biểu mẫu & Tiếp nhận",
    desc: "Đơn từ, Phiếu đăng ký, Giấy xác nhận, Hợp đồng ký túc xá",
  },
];

const INITIAL_FORM: DocumentTypeInput = {
  code: "",
  name: "",
  category: "administrative",
  description: "",
  priority: 5,
  retention_period: "Theo quy định",
};

export function CreateDocumentTypeDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateDocumentTypeDialogProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<DocumentTypeInput>(INITIAL_FORM);
  const [codeError, setCodeError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (input: DocumentTypeInput) => createDocumentType(input),
    onSuccess: (created) => {
      toast.success(`Đã tạo thành công loại văn bản “${created.name}”!`);
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
      onSuccess?.(created);
      onOpenChange(false);
      setForm(INITIAL_FORM);
      setCodeError(null);
    },
    onError: (err: Error) => {
      toast.error(`Tạo loại văn bản thất bại: ${err.message}`);
    },
  });

  const handleCodeChange = (raw: string) => {
    const sanitized = raw.toLowerCase().replace(/\s+/g, "_");
    setForm((prev) => ({ ...prev, code: sanitized }));
    if (sanitized && !/^[a-z0-9_]+$/.test(sanitized)) {
      setCodeError(
        "Mã chỉ được chứa chữ thường (a-z), chữ số (0-9) và dấu gạch dưới (_)",
      );
    } else {
      setCodeError(null);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.code.trim()) {
      setCodeError("Vui lòng nhập mã chuẩn loại văn bản.");
      return;
    }
    if (!/^[a-z0-9_]+$/.test(form.code)) {
      setCodeError(
        "Mã không hợp lệ. Chỉ dùng ký tự a-z, 0-9 và dấu gạch dưới.",
      );
      return;
    }
    if (!form.name.trim()) {
      toast.error("Vui lòng nhập tên hiển thị loại văn bản.");
      return;
    }

    createMutation.mutate({
      ...form,
      code: form.code.trim(),
      name: form.name.trim(),
      priority: Number(form.priority) || 5,
      retention_period: form.retention_period.trim() || "Theo quy định",
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileText className="size-4" />
            </div>
            <DialogTitle className="text-base font-bold text-foreground">
              Thêm Loại Văn Bản Mới
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Khởi tạo thể thức loại văn bản bổ sung phục vụ lưu trữ và phân loại
            tài liệu Kho Tri Thức.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3.5 py-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field
              label="Mã chuẩn (Code)"
              htmlFor="doc-code"
              required
              hint="Ví dụ: quyet_dinh, ke_hoach, hop_dong"
              error={codeError || undefined}
            >
              <Input
                id="doc-code"
                value={form.code}
                onChange={(e) => handleCodeChange(e.target.value)}
                placeholder="quyet_dinh"
                className="h-8 font-mono text-xs"
                disabled={createMutation.isPending}
                required
              />
            </Field>

            <Field label="Tên hiển thị" htmlFor="doc-name" required>
              <Input
                id="doc-name"
                value={form.name}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="Quyết định cá biệt"
                className="h-8 text-xs"
                disabled={createMutation.isPending}
                required
              />
            </Field>
          </div>

          <Field label="Nhóm phân loại" htmlFor="doc-category" required>
            <Select
              value={form.category}
              onValueChange={(val) =>
                setForm((prev) => ({
                  ...prev,
                  category: val as DocumentTypeCategory,
                }))
              }
              disabled={createMutation.isPending}
            >
              <SelectTrigger id="doc-category" className="h-8 text-xs w-full">
                <SelectValue placeholder="Chọn nhóm văn bản" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORY_OPTIONS.map((opt) => (
                  <SelectItem
                    key={opt.value}
                    value={opt.value}
                    className="text-xs"
                  >
                    <div className="py-0.5">
                      <span className="font-semibold text-foreground">
                        {opt.label}
                      </span>
                      <p className="text-[11px] text-muted-foreground">
                        {opt.desc}
                      </p>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label="Mô tả thể thức & Hướng dẫn áp dụng"
            htmlFor="doc-desc"
            hint="Mô tả mục đích và trường hợp áp dụng của thể thức này"
          >
            <Textarea
              id="doc-desc"
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder="Văn bản hành chính do Hiệu trưởng hoặc đơn vị được ủy quyền ban hành..."
              className="text-xs min-h-[68px] resize-none"
              disabled={createMutation.isPending}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <Field
              label="Mức ưu tiên RAG (1 - 10)"
              htmlFor="doc-priority"
              hint="10: Cao nhất (Quy chuẩn tối cao) • 1: Thấp nhất"
            >
              <Input
                id="doc-priority"
                type="number"
                min={1}
                max={10}
                value={form.priority}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    priority: Number.parseInt(e.target.value, 10) || 1,
                  }))
                }
                className="h-8 font-mono text-xs"
                disabled={createMutation.isPending}
              />
            </Field>

            <Field
              label="Thời hạn bảo quản"
              htmlFor="doc-retention"
              hint="Ví dụ: Vĩnh viễn, 70 năm, 10 năm, 5 năm"
            >
              <Input
                id="doc-retention"
                value={form.retention_period}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    retention_period: e.target.value,
                  }))
                }
                placeholder="Vĩnh viễn"
                className="h-8 text-xs"
                disabled={createMutation.isPending}
              />
            </Field>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-8 text-xs gap-1.5"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang tạo...</span>
                </>
              ) : (
                <>
                  <Plus className="size-3.5" />
                  <span>Tạo loại văn bản</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

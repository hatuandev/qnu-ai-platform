import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Check,
  ExternalLink,
  FileCheck,
  Loader2,
  Power,
  Save,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";
import { Field } from "@/components/admin/field";
import {
  formatCategoryLabel,
  getCategoryIcon,
} from "@/components/document-types/document-type-card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  activateDocumentType,
  type DocumentTypeCategory,
  type DocumentTypeInput,
  deactivateDocumentType,
  getDocumentType,
  updateDocumentType,
} from "@/services/document-types-api";

interface DocumentTypeDetailPageProps {
  code: string;
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

export function DocumentTypeDetailPage({ code }: DocumentTypeDetailPageProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [form, setForm] = useState<DocumentTypeInput | null>(null);

  // 1. Fetch document type details
  const documentTypeQuery = useQuery({
    queryKey: ["document-types", code],
    queryFn: () => getDocumentType(code),
    enabled: Boolean(code),
  });

  // 2. Sync to form state
  useEffect(() => {
    if (documentTypeQuery.data) {
      const d = documentTypeQuery.data;
      setForm({
        code: d.code,
        name: d.name,
        category: d.category,
        description: d.description || "",
        priority: d.priority,
        retention_period: d.retention_period || "Theo quy định",
      });
    }
  }, [documentTypeQuery.data]);

  // 3. Update Mutation
  const updateMutation = useMutation({
    mutationFn: (input: DocumentTypeInput) =>
      updateDocumentType(code, {
        name: input.name,
        category: input.category,
        description: input.description,
        priority: input.priority,
        retention_period: input.retention_period,
        is_active: documentTypeQuery.data?.is_active,
      }),
    onSuccess: (updated) => {
      toast.success(`Đã lưu thay đổi loại văn bản “${updated.name}”!`);
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
      queryClient.setQueryData(["document-types", code], updated);
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật thất bại: ${err.message}`);
    },
  });

  // 4. Toggle Active Mutation
  const toggleActiveMutation = useMutation({
    mutationFn: (active: boolean) =>
      active ? activateDocumentType(code) : deactivateDocumentType(code),
    onSuccess: (updated) => {
      toast.success(
        updated.is_active
          ? `Đã kích hoạt thể thức “${updated.name}”.`
          : `Đã tạm dừng thể thức “${updated.name}”.`,
      );
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
      queryClient.setQueryData(["document-types", code], updated);
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật trạng thái thất bại: ${err.message}`);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    if (!form.name.trim()) {
      toast.error("Vui lòng nhập tên loại văn bản.");
      return;
    }
    updateMutation.mutate(form);
  };

  const item = documentTypeQuery.data;

  if (documentTypeQuery.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-3">
        <Loader2 className="size-6 animate-spin text-primary" />
        <span className="text-xs">
          Đang tải thông tin thể thức loại văn bản...
        </span>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="py-16 text-center space-y-4">
        <AlertTriangle className="size-10 text-destructive mx-auto" />
        <h2 className="text-base font-bold text-foreground">
          Không tìm thấy loại văn bản
        </h2>
        <p className="text-xs text-muted-foreground">
          Mã loại văn bản “{code}” không tồn tại hoặc đã bị xóa khỏi hệ thống.
        </p>
        <Button
          variant="outline"
          size="sm"
          className="text-xs gap-1.5"
          onClick={() => navigate({ to: "/document-types" })}
        >
          <ArrowLeft className="size-3.5" />
          <span>Quay lại danh mục</span>
        </Button>
      </div>
    );
  }

  const Icon = getCategoryIcon(item.category);

  return (
    <div className="space-y-5">
      {/* 1. Top Navigation & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
            onClick={() => navigate({ to: "/document-types" })}
          >
            <ArrowLeft className="size-3.5" />
            <span>Danh mục</span>
          </Button>

          <div className="h-4 w-px bg-border" />

          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-foreground">
                  {item.name}
                </h1>
                <span className="font-mono text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {item.code}
                </span>
                <Badge variant="outline" className="text-[10px] h-4.5 px-1.5">
                  {formatCategoryLabel(item.category)}
                </Badge>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-end sm:self-auto">
          {/* Switch hoạt động nhanh */}
          <div className="flex items-center gap-2 bg-muted/30 px-3 py-1 rounded-md border text-xs">
            <span className="text-muted-foreground text-[11px]">
              {item.is_active ? "Đang hoạt động" : "Đã tạm dừng"}
            </span>
            <Switch
              checked={item.is_active}
              disabled={toggleActiveMutation.isPending}
              onCheckedChange={(checked) =>
                toggleActiveMutation.mutate(checked)
              }
              aria-label={`Trạng thái ${item.name}`}
            />
          </div>

          <Button
            type="submit"
            form="doc-type-form"
            size="sm"
            className="h-8 text-xs gap-1.5"
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                <span>Đang lưu...</span>
              </>
            ) : (
              <>
                <Save className="size-3.5" />
                <span>Lưu</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 2. Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Cột Trái: Form Thông số cấu hình (2 spans) */}
        <div className="lg:col-span-2 space-y-5">
          <form
            id="doc-type-form"
            onSubmit={handleSubmit}
            className="space-y-5"
          >
            {/* Card 1: Thông số định danh & thể thức */}
            <Card className="border border-border/80 shadow-2xs">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <FileCheck className="size-4 text-primary" />
                  <span>Thông Số Thể Thức & Phân Loại</span>
                </CardTitle>
                <CardDescription className="text-xs">
                  Cấu hình mã chuẩn, tên tiếng Việt chính quy và nhóm chức năng
                  của văn bản.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field
                    label="Mã chuẩn hệ thống (Code)"
                    htmlFor="field-code"
                    hint={
                      item.is_system_default
                        ? "Mã chuẩn theo Nghị định 30/2020 (không chỉnh sửa)"
                        : "Định danh duy nhất dùng trong API và trích xuất"
                    }
                  >
                    <Input
                      id="field-code"
                      value={form?.code || ""}
                      disabled
                      className="h-8 font-mono text-xs bg-muted/40 cursor-not-allowed"
                    />
                  </Field>

                  <Field
                    label="Tên thể thức văn bản"
                    htmlFor="field-name"
                    required
                  >
                    <Input
                      id="field-name"
                      value={form?.name || ""}
                      onChange={(e) =>
                        setForm((prev) =>
                          prev ? { ...prev, name: e.target.value } : prev,
                        )
                      }
                      placeholder="Ví dụ: Quyết định, Thông báo"
                      className="h-8 text-xs"
                      disabled={updateMutation.isPending}
                      required
                    />
                  </Field>
                </div>

                <Field
                  label="Nhóm phân loại chức năng"
                  htmlFor="field-category"
                  required
                >
                  <Select
                    value={form?.category}
                    onValueChange={(val) =>
                      setForm((prev) =>
                        prev
                          ? { ...prev, category: val as DocumentTypeCategory }
                          : prev,
                      )
                    }
                    disabled={updateMutation.isPending}
                  >
                    <SelectTrigger
                      id="field-category"
                      className="h-8 text-xs w-full"
                    >
                      <SelectValue placeholder="Chọn nhóm phân loại" />
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
                  label="Mô tả thể thức & Hướng dẫn văn thư áp dụng"
                  htmlFor="field-desc"
                  hint="Căn cứ để cán bộ phân loại chính xác khi nạp tài liệu vào Kho Tri Thức"
                >
                  <Textarea
                    id="field-desc"
                    value={form?.description || ""}
                    onChange={(e) =>
                      setForm((prev) =>
                        prev ? { ...prev, description: e.target.value } : prev,
                      )
                    }
                    placeholder="Mô tả mục đích và thẩm quyền ban hành loại văn bản này..."
                    className="text-xs min-h-[90px] leading-relaxed resize-none"
                    disabled={updateMutation.isPending}
                  />
                </Field>
              </CardContent>
            </Card>

            {/* Card 2: Trọng số RAG & Lưu trữ */}
            <Card className="border border-border/80 shadow-2xs">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Scale className="size-4 text-primary" />
                  <span>Trọng Số Hybrid RAG & Thời Hạn Bảo Quản</span>
                </CardTitle>
                <CardDescription className="text-xs">
                  Thiết lập trọng số ưu tiên xếp hạng khi Trợ lý AI tra cứu và
                  quy định lưu trữ văn thư.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field
                    label="Mức độ ưu tiên trích xuất RAG (1 - 10)"
                    htmlFor="field-priority"
                    hint="Ưu tiên cao hơn (10: Quy chế, Quyết định) sẽ được RRF xếp hạng trước các văn bản thông thường"
                  >
                    <div className="flex items-center gap-3">
                      <Input
                        id="field-priority"
                        type="number"
                        min={1}
                        max={10}
                        value={form?.priority || 5}
                        onChange={(e) =>
                          setForm((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  priority:
                                    Number.parseInt(e.target.value, 10) || 1,
                                }
                              : prev,
                          )
                        }
                        className="h-8 font-mono text-xs w-24"
                        disabled={updateMutation.isPending}
                      />
                      <div className="flex-1">
                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all duration-300 rounded-full"
                            style={{
                              width: `${((form?.priority || 5) / 10) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </Field>

                  <Field
                    label="Thời hạn bảo quản văn thư"
                    htmlFor="field-retention"
                    hint="Theo Thông tư hướng dẫn lưu trữ (Vĩnh viễn, 70 năm, 10 năm, 5 năm)"
                  >
                    <Input
                      id="field-retention"
                      value={form?.retention_period || ""}
                      onChange={(e) =>
                        setForm((prev) =>
                          prev
                            ? { ...prev, retention_period: e.target.value }
                            : prev,
                        )
                      }
                      placeholder="Vĩnh viễn"
                      className="h-8 text-xs"
                      disabled={updateMutation.isPending}
                    />
                  </Field>
                </div>
              </CardContent>
            </Card>
          </form>
        </div>

        {/* Cột Phải: Metadata Pháp lý, Thống kê Kho Tri Thức & Danger Zone */}
        <div className="space-y-5">
          {/* Card 3: Pháp lý & Xuất xứ */}
          <Card className="border border-border/80 shadow-2xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                <span>Căn Cứ Pháp Lý & Xuất Xứ</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">
                  Tiêu chuẩn thể thức:
                </span>
                {item.nd30 ? (
                  <Badge
                    variant="secondary"
                    className="bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/20 text-[10px] gap-1"
                  >
                    <Check className="size-2.5" />
                    <span>Nghị định 30/2020/NĐ-CP</span>
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px]">
                    Nội bộ ĐH Quy Nhơn
                  </Badge>
                )}
              </div>

              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">
                  Tính chất phân loại:
                </span>
                <span className="font-medium text-foreground">
                  {item.is_system_default
                    ? "Mặc định hệ thống"
                    : item.is_custom
                      ? "Tùy chỉnh đơn vị"
                      : "Tiêu chuẩn"}
                </span>
              </div>

              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">Nguồn đồng bộ:</span>
                <span className="font-mono text-[11px] text-foreground">
                  {item.source_system}
                </span>
              </div>

              {item.source_hash && (
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-muted-foreground">Mã băm nguồn:</span>
                  <span
                    className="font-mono text-[10px] text-muted-foreground truncate max-w-[140px]"
                    title={item.source_hash}
                  >
                    {item.source_hash}
                  </span>
                </div>
              )}

              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">Đồng bộ gần nhất:</span>
                <span className="text-[11px] text-foreground">
                  {item.synced_at
                    ? new Date(item.synced_at).toLocaleDateString("vi-VN")
                    : "Chưa đồng bộ"}
                </span>
              </div>

              <div className="flex items-center justify-between pt-0.5">
                <span className="text-muted-foreground">
                  Cập nhật lần cuối:
                </span>
                <span className="text-[11px] text-foreground">
                  {item.updated_at
                    ? new Date(item.updated_at).toLocaleDateString("vi-VN")
                    : "—"}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Thống kê Kho Tri Thức */}
          <Card className="border border-border/80 shadow-2xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <BookOpen className="size-4 text-primary" />
                <span>Tài Liệu Đang Áp Dụng</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Tổng số văn bản thực tế trong Kho Tri Thức thuộc thể thức này.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border">
                <span className="text-xs text-muted-foreground">
                  Văn bản đã bóc tách:
                </span>
                <span className="text-lg font-bold font-mono text-primary">
                  {item.doc_count || 0}
                </span>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="w-full h-8 text-xs gap-1.5"
                onClick={() => navigate({ to: "/knowledge" })}
              >
                <ExternalLink className="size-3.5" />
                <span>Mở Kho Tri Thức</span>
              </Button>
            </CardContent>
          </Card>

          {/* Card 5: Vùng Nguy Hiểm */}
          <Card className="border border-destructive/30 shadow-2xs">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold text-destructive flex items-center gap-2">
                <Power className="size-4" />
                <span>Vùng Nguy Hiểm</span>
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground">
                Tạm dừng hoặc khôi phục hoạt động của thể thức văn bản này.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-foreground">
                    {item.is_active
                      ? "Tạm dừng thể thức"
                      : "Kích hoạt lại thể thức"}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {item.is_active
                      ? "Ngăn không cho nạp văn bản mới theo loại này nhưng bảo toàn các văn bản cũ."
                      : "Cho phép tiếp tục nạp và phân loại văn bản mới."}
                  </p>
                </div>

                <Button
                  variant={item.is_active ? "destructive" : "default"}
                  size="sm"
                  className="h-8 text-xs shrink-0"
                  onClick={() => toggleActiveMutation.mutate(!item.is_active)}
                  disabled={toggleActiveMutation.isPending}
                >
                  {toggleActiveMutation.isPending ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : item.is_active ? (
                    "Tạm dừng"
                  ) : (
                    "Kích hoạt"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

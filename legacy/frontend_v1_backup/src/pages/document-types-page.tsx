import { DocumentTypeForm } from "@/components/admin/document-type-form";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  type DocumentTypeCategory,
  type DocumentTypeInput,
  type DocumentTypeItem,
  createDocumentType,
  listDocumentTypes,
  syncDocumentTypes,
} from "@/services/document-types-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, FileText, Plus, RefreshCw, Search } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

interface DocumentTypesPageProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

const CATEGORY_FILTERS: Array<{ value: DocumentTypeCategory | "all"; label: string }> = [
  { value: "all", label: "Tất cả nhóm" },
  { value: "legal_internal", label: "Quy phạm & Nội bộ" },
  { value: "administrative", label: "Hành chính Điều hành" },
  { value: "academic", label: "Đào tạo & Học thuật" },
  { value: "forms", label: "Biểu mẫu & Tiếp nhận" },
];

const EMPTY_FORM: DocumentTypeInput = {
  code: "",
  name: "",
  category: "administrative",
  description: "",
  priority: 5,
  retention_period: "",
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Không thể hoàn thành thao tác taxonomy.";
}

function DocumentTypeStats({ items }: { items: DocumentTypeItem[] }) {
  const activeCount = items.filter((item) => item.is_active).length;
  const nd30Count = items.filter((item) => item.nd30).length;
  const customCount = items.filter((item) => item.is_custom).length;
  const stats = [
    { label: "Tổng loại văn bản", value: items.length, icon: FileText },
    { label: "Đang hoạt động", value: activeCount, icon: Database },
    { label: "Mã NĐ30/2020", value: nd30Count, icon: FileText },
    { label: "Loại tùy chỉnh", value: customCount, icon: Plus },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.label} className="border-border/80">
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">{stat.value}</p>
              </div>
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon className="size-4" />
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function DocumentTypeRow({ item, onOpen }: { item: DocumentTypeItem; onOpen: () => void }) {
  return (
    <tr className="h-11 border-b border-border transition-colors hover:bg-muted/30">
      <td className="p-3 align-middle">
        <Button className="font-mono text-xs" size="sm" variant="link" onClick={onOpen}>
          {item.code}
        </Button>
        <p className="mt-0.5 text-xs text-muted-foreground">{item.name}</p>
      </td>
      <td className="p-3 align-middle text-xs">{item.category_name}</td>
      <td className="p-3 align-middle">
        {item.nd30 ? (
          <Badge variant="info">NĐ30</Badge>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="p-3 align-middle text-center text-xs">{item.priority}</td>
      <td className="p-3 align-middle text-center text-xs">{item.doc_count}</td>
      <td className="p-3 align-middle">
        <Badge variant={item.is_active ? "success" : "secondary"}>
          {item.is_active ? "Hoạt động" : "Tắt"}
        </Badge>
      </td>
      <td className="p-3 align-middle text-right">
        <Button size="sm" variant="outline" onClick={onOpen}>
          Chi tiết
        </Button>
      </td>
    </tr>
  );
}

export function DocumentTypesPage({ onNavigate }: DocumentTypesPageProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<DocumentTypeCategory | "all">("all");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [formValue, setFormValue] = useState<DocumentTypeInput>(EMPTY_FORM);
  const [feedback, setFeedback] = useState<string | null>(null);

  const documentTypesQuery = useQuery({
    queryKey: ["document-types", search, category],
    queryFn: () => listDocumentTypes({ search, category }),
  });

  const createMutation = useMutation({
    mutationFn: createDocumentType,
    onSuccess: () => {
      setIsCreateOpen(false);
      setFormValue(EMPTY_FORM);
      setFeedback("Đã tạo loại văn bản tùy chỉnh.");
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: syncDocumentTypes,
    onSuccess: (result) => {
      setFeedback(
        `Đã đồng bộ ${result.total} loại: thêm ${result.added}, cập nhật ${result.updated}, bỏ qua ${result.skipped}.`
      );
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
  });

  const items = documentTypesQuery.data ?? [];
  const errorMessage = documentTypesQuery.error
    ? getErrorMessage(documentTypesQuery.error)
    : createMutation.error
      ? getErrorMessage(createMutation.error)
      : syncMutation.error
        ? getErrorMessage(syncMutation.error)
        : null;
  const hasItems = items.length > 0;
  const filteredDescription = useMemo(
    () =>
      search || category !== "all"
        ? "Kết quả theo bộ lọc hiện tại."
        : "Nguồn chuẩn được đồng bộ từ qnu-ai-core.",
    [category, search]
  );

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
    createMutation.mutate(formValue);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <FileText className="size-4 text-primary" />
            <span>Kho Tri thức / Quản trị taxonomy</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight">Loại văn bản</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Chuẩn hóa loại văn bản ở Core để ingestion, RAG và soạn thảo dùng chung một mã định
            danh.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={syncMutation.isPending}
            variant="outline"
            onClick={() => {
              setFeedback(null);
              syncMutation.mutate();
            }}
          >
            <RefreshCw className={syncMutation.isPending ? "size-4 animate-spin" : "size-4"} />
            Đồng bộ Core
          </Button>
          <Button
            onClick={() => {
              setFormValue(EMPTY_FORM);
              setFeedback(null);
              setIsCreateOpen(true);
            }}
          >
            <Plus className="size-4" />
            Thêm loại tùy chỉnh
          </Button>
        </div>
      </div>

      <DocumentTypeStats items={items} />

      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>Danh mục loại văn bản</CardTitle>
            <CardDescription>{filteredDescription}</CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative min-w-64">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                className="pl-8"
                placeholder="Tìm theo mã hoặc tên..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <Select
              value={category}
              onValueChange={(value) => setCategory(value as DocumentTypeCategory | "all")}
            >
              <SelectTrigger aria-label="Lọc theo nhóm loại văn bản" className="min-w-48">
                <SelectValue placeholder="Tất cả nhóm" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORY_FILTERS.map((filter) => (
                  <SelectItem key={filter.value} value={filter.value}>
                    {filter.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {documentTypesQuery.isLoading ? (
            <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
              Đang tải taxonomy từ Backend...
            </div>
          ) : errorMessage ? (
            <EmptyState
              icon={FileText}
              title="Không tải được taxonomy"
              description={errorMessage}
              action={<Button onClick={() => documentTypesQuery.refetch()}>Thử lại</Button>}
            />
          ) : !hasItems ? (
            <EmptyState
              icon={FileText}
              title="Chưa có loại văn bản phù hợp"
              description="Hãy đồng bộ từ Core hoặc thay đổi bộ lọc để tiếp tục."
            />
          ) : (
            <div className="relative w-full overflow-auto rounded-md border border-border">
              <table className="w-full caption-bottom text-xs">
                <thead className="bg-muted/40">
                  <tr className="border-b border-border">
                    <th className="h-10 px-3 text-left font-semibold text-muted-foreground">
                      Mã / Tên
                    </th>
                    <th className="h-10 px-3 text-left font-semibold text-muted-foreground">
                      Nhóm
                    </th>
                    <th className="h-10 px-3 text-left font-semibold text-muted-foreground">
                      Chuẩn
                    </th>
                    <th className="h-10 px-3 text-center font-semibold text-muted-foreground">
                      Ưu tiên
                    </th>
                    <th className="h-10 px-3 text-center font-semibold text-muted-foreground">
                      Tài liệu
                    </th>
                    <th className="h-10 px-3 text-left font-semibold text-muted-foreground">
                      Trạng thái
                    </th>
                    <th className="h-10 px-3 text-right font-semibold text-muted-foreground">
                      Thao tác
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <DocumentTypeRow
                      key={item.code}
                      item={item}
                      onOpen={() => onNavigate(`/document-types/${encodeURIComponent(item.code)}`)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {feedback ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-4 py-3 text-xs text-success">
          {feedback}
        </div>
      ) : null}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Thêm loại văn bản tùy chỉnh</DialogTitle>
            <DialogDescription>
              Loại tùy chỉnh được lưu trong Platform và không ghi đè 37 loại chuẩn từ Core.
            </DialogDescription>
          </DialogHeader>
          <DocumentTypeForm
            formId="create-document-type"
            isCodeEditable
            isSubmitting={createMutation.isPending}
            onChange={setFormValue}
            onSubmit={handleCreate}
            submitLabel="Tạo loại văn bản"
            value={formValue}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Hủy
            </Button>
            <Button disabled={createMutation.isPending} form="create-document-type" type="submit">
              {createMutation.isPending ? "Đang lưu..." : "Tạo loại văn bản"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

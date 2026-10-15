import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Check,
  Pencil,
  Plus,
  RefreshCw,
  Undo2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import { Field } from "@/components/admin/field";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useRbac } from "@/rbac/context";
import { knowledgeApi } from "@/services/knowledge-api";
import type { GlossaryTerm, GlossaryTermStatus } from "@/types/knowledge";

const STATUS_META: Record<
  GlossaryTermStatus,
  {
    label: string;
    variant: "secondary" | "success" | "warning" | "destructive";
  }
> = {
  pending: { label: "Chờ duyệt", variant: "secondary" },
  approved: { label: "Đã duyệt", variant: "success" },
  rejected: { label: "Từ chối", variant: "warning" },
  revoked: { label: "Thu hồi", variant: "destructive" },
};

const STATUS_OPTIONS = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "pending", label: "Chờ duyệt" },
  { value: "approved", label: "Đã duyệt" },
  { value: "rejected", label: "Từ chối" },
  { value: "revoked", label: "Thu hồi" },
];

interface TermFormState {
  user_phrase: string;
  target_term: string;
  note: string;
  years: string;
  methods: string;
  entities: string;
}

const EMPTY_FORM: TermFormState = {
  user_phrase: "",
  target_term: "",
  note: "",
  years: "",
  methods: "",
  entities: "",
};

function parseListField(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function parseYearsField(value: string): number[] | null {
  const raw = parseListField(value);
  if (raw.length === 0) return null;
  const years = raw
    .map((part) => Number(part))
    .filter((num) => Number.isInteger(num));
  return years.length === raw.length ? years : null;
}

function buildScope(form: TermFormState): Record<string, unknown> | null {
  const years = parseYearsField(form.years);
  if (form.years.trim() !== "" && years === null) return null;
  const scope: Record<string, unknown> = {};
  if (years && years.length > 0) scope.years = years;
  const methods = parseListField(form.methods);
  if (methods.length > 0) scope.methods = methods;
  const entities = parseListField(form.entities);
  if (entities.length > 0) scope.entities = entities;
  return scope;
}

function scopeToForm(
  scope: Record<string, unknown>,
): Pick<TermFormState, "years" | "methods" | "entities"> {
  const join = (value: unknown): string =>
    Array.isArray(value) ? value.map((item) => String(item)).join(", ") : "";
  return {
    years: join((scope as Record<string, unknown>).years),
    methods: join((scope as Record<string, unknown>).methods),
    entities: join((scope as Record<string, unknown>).entities),
  };
}

export interface CollectionGlossaryTabProps {
  collectionId: string;
}

export function CollectionGlossaryTab({
  collectionId,
}: CollectionGlossaryTabProps) {
  const queryClient = useQueryClient();
  const { can } = useRbac();
  const canEdit = can("ai.knowledge.update");
  const canReview = can("ai.knowledge.review");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<GlossaryTerm | null>(null);
  const [form, setForm] = useState<TermFormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  const [reviewTarget, setReviewTarget] = useState<{
    term: GlossaryTerm;
    action: "approve" | "reject" | "revoke";
  } | null>(null);
  const [reviewReason, setReviewReason] = useState("");

  const settingsQuery = useQuery({
    queryKey: ["collection-glossary-settings", collectionId],
    queryFn: () => knowledgeApi.getGlossarySettings(collectionId),
  });

  const termsQuery = useQuery({
    queryKey: [
      "collection-glossary",
      collectionId,
      search,
      statusFilter,
      page,
      pageSize,
    ],
    queryFn: () =>
      knowledgeApi.listGlossaryTerms(collectionId, {
        search: search.trim() || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
        page,
        page_size: pageSize,
      }),
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({
      queryKey: ["collection-glossary", collectionId],
    });
    queryClient.invalidateQueries({
      queryKey: ["collection-glossary-settings", collectionId],
    });
  };

  const handleApiError = (err: unknown, fallback: string) => {
    const message = err instanceof Error ? err.message : fallback;
    toast.error(message);
    invalidateAll();
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const scope = buildScope(form);
      if (scope === null)
        throw new Error(
          "Năm phạm vi phải là các số nguyên, cách nhau bằng dấu phẩy.",
        );
      if (!form.user_phrase.trim() || !form.target_term.trim()) {
        throw new Error("Cụm hỏi và thuật ngữ đích không được để trống.");
      }
      const payload = {
        user_phrase: form.user_phrase.trim(),
        target_term: form.target_term.trim(),
        note: form.note.trim(),
        scope,
      };
      if (editing) {
        return knowledgeApi.updateGlossaryTerm(collectionId, editing.id, {
          ...payload,
          expected_version: editing.version,
        });
      }
      return knowledgeApi.createGlossaryTerm(collectionId, payload);
    },
    onSuccess: (saved) => {
      toast.success(
        editing
          ? `Đã lưu thuật ngữ (bản ${saved.version}).`
          : "Đã thêm thuật ngữ, đang chờ duyệt.",
      );
      setFormOpen(false);
      setEditing(null);
      setForm(EMPTY_FORM);
      setFormError(null);
      invalidateAll();
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "Lưu thuật ngữ thất bại.";
      setFormError(message);
    },
  });

  const reviewMutation = useMutation({
    mutationFn: () => {
      if (!reviewTarget) throw new Error("Chưa chọn thuật ngữ để duyệt.");
      return knowledgeApi.reviewGlossaryTerm(
        collectionId,
        reviewTarget.term.id,
        {
          action: reviewTarget.action,
          reason: reviewReason.trim() || undefined,
          expected_version: reviewTarget.term.version,
        },
      );
    },
    onSuccess: () => {
      toast.success("Đã ghi nhận quyết định duyệt.");
      setReviewTarget(null);
      setReviewReason("");
      invalidateAll();
    },
    onError: (err: unknown) => handleApiError(err, "Duyệt thuật ngữ thất bại."),
  });

  const toggleMutation = useMutation({
    mutationFn: (next: { is_enabled: boolean; expected_version: number }) =>
      knowledgeApi.updateGlossarySettings(collectionId, next),
    onSuccess: (settings) => {
      toast.success(
        settings.is_enabled
          ? "Đã bật sử dụng thuật ngữ."
          : "Đã tắt sử dụng thuật ngữ.",
      );
      invalidateAll();
    },
    onError: (err: unknown) =>
      handleApiError(err, "Bật/tắt thuật ngữ thất bại."),
  });

  const openAdd = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setFormOpen(true);
  };

  const openEdit = (term: GlossaryTerm) => {
    setEditing(term);
    setForm({
      user_phrase: term.user_phrase,
      target_term: term.target_term,
      note: term.note || "",
      ...scopeToForm(term.scope || {}),
    });
    setFormError(null);
    setFormOpen(true);
  };

  const terms: GlossaryTerm[] = useMemo(
    () => termsQuery.data?.items || [],
    [termsQuery.data],
  );
  const total = termsQuery.data?.total || 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const settings = settingsQuery.data;

  const reviewLabels: Record<
    string,
    { title: string; confirm: string; destructive?: boolean }
  > = {
    approve: { title: "Duyệt thuật ngữ", confirm: "Duyệt" },
    reject: { title: "Từ chối thuật ngữ", confirm: "Từ chối" },
    revoke: {
      title: "Thu hồi thuật ngữ",
      confirm: "Thu hồi",
      destructive: true,
    },
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-4 space-y-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Sử dụng thuật ngữ khi tìm kiếm
              </p>
              <p className="text-xs text-muted-foreground">
                Thuật ngữ hỗ trợ tìm kiếm, không thay thế căn cứ trong tài liệu.
                {settings
                  ? ` Phiên bản glossary hiện tại: ${settings.version}.`
                  : ""}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {settings?.is_enabled ? "Đang bật" : "Đang tắt"}
              </span>
              <Switch
                checked={settings?.is_enabled ?? false}
                disabled={
                  !canReview ||
                  toggleMutation.isPending ||
                  settingsQuery.isLoading
                }
                onCheckedChange={(checked) => {
                  if (!settings) return;
                  toggleMutation.mutate({
                    is_enabled: checked,
                    expected_version: settings.version,
                  });
                }}
                aria-label="Bật hoặc tắt sử dụng thuật ngữ"
              />
            </div>
          </div>
          {!canReview && (
            <p className="text-xs text-muted-foreground">
              Bạn không có quyền duyệt hoặc bật/tắt thuật ngữ.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <DebouncedSearchInput
          value={search}
          onChange={(value) => {
            setSearch(value);
            setPage(1);
          }}
          placeholder="Tìm theo cụm hỏi, thuật ngữ đích..."
          className="w-full sm:w-72 lg:w-80"
        />
        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:w-auto sm:justify-end">
          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-full sm:w-40 h-8 text-xs">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {canEdit && (
            <Button size="sm" className="h-8 text-xs" onClick={openAdd}>
              <Plus className="size-3.5" />
              Thêm
            </Button>
          )}
        </div>
      </div>

      {termsQuery.isLoading ? (
        <Card>
          <CardContent className="pt-4 space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </CardContent>
        </Card>
      ) : termsQuery.isError ? (
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <EmptyState
              icon={BookOpen}
              title="Không tải được danh sách thuật ngữ"
              description={
                termsQuery.error instanceof Error
                  ? termsQuery.error.message
                  : "Đã xảy ra lỗi không xác định."
              }
              action={{ label: "Thử lại", onClick: () => termsQuery.refetch() }}
            />
          </CardContent>
        </Card>
      ) : terms.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <EmptyState
              icon={BookOpen}
              title="Chưa có thuật ngữ nào"
              description="Thêm cách gọi thông thường và thuật ngữ đích trong tài liệu, sau đó duyệt để chatbot dùng khi tìm kiếm."
              action={canEdit ? { label: "Thêm", onClick: openAdd } : undefined}
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-0 px-0 sm:px-0">
            <div className="w-full overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="h-11">
                    <TableHead className="text-xs">Cụm hỏi</TableHead>
                    <TableHead className="text-xs">Thuật ngữ đích</TableHead>
                    <TableHead className="text-xs">Trạng thái</TableHead>
                    <TableHead className="text-xs">Người duyệt</TableHead>
                    <TableHead className="text-xs text-right">
                      Thao tác
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {terms.map((term) => {
                    const meta = STATUS_META[term.status];
                    return (
                      <TableRow key={term.id} className="h-11">
                        <TableCell className="text-sm font-medium">
                          {term.user_phrase}
                        </TableCell>
                        <TableCell className="text-sm">
                          {term.target_term}
                        </TableCell>
                        <TableCell>
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {term.reviewed_by || "—"}
                          {term.review_reason ? ` · ${term.review_reason}` : ""}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            {canEdit && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 px-2 text-xs"
                                onClick={() => openEdit(term)}
                              >
                                <Pencil className="size-3.5" />
                                Sửa
                              </Button>
                            )}
                            {canReview && term.status === "pending" && (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 px-2 text-xs"
                                  onClick={() => {
                                    setReviewTarget({
                                      term,
                                      action: "approve",
                                    });
                                    setReviewReason("");
                                  }}
                                >
                                  <Check className="size-3.5" />
                                  Duyệt
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 px-2 text-xs"
                                  onClick={() => {
                                    setReviewTarget({ term, action: "reject" });
                                    setReviewReason("");
                                  }}
                                >
                                  <X className="size-3.5" />
                                  Từ chối
                                </Button>
                              </>
                            )}
                            {canReview && term.status === "approved" && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 px-2 text-xs text-destructive"
                                onClick={() => {
                                  setReviewTarget({ term, action: "revoke" });
                                  setReviewReason("");
                                }}
                              >
                                <Undo2 className="size-3.5" />
                                Thu hồi
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            <DataTablePagination
              page={page}
              pageSize={pageSize}
              pageCount={pageCount}
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
            />
          </CardContent>
        </Card>
      )}

      <ResponsiveDialog open={formOpen} onOpenChange={setFormOpen}>
        <ResponsiveDialogContent className="sm:max-w-lg max-h-[min(820px,calc(100vh-2rem))]">
          <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-3">
            <ResponsiveDialogTitle>
              {editing ? "Sửa thuật ngữ" : "Thêm thuật ngữ"}
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              {editing
                ? `Sửa cụm từ hoặc phạm vi của mục đã duyệt sẽ quay về chờ duyệt (bản ${editing.version}).`
                : "Mục mới luôn ở trạng thái chờ duyệt."}
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {formError && (
              <p className="text-xs text-destructive" role="alert">
                {formError}
              </p>
            )}
            <Field label="Cụm người dùng thường hỏi" required>
              <Input
                value={form.user_phrase}
                onChange={(event) =>
                  setForm({ ...form, user_phrase: event.target.value })
                }
                placeholder="VD: học bạ"
                maxLength={200}
              />
            </Field>
            <Field label="Thuật ngữ đích trong tài liệu" required>
              <Input
                value={form.target_term}
                onChange={(event) =>
                  setForm({ ...form, target_term: event.target.value })
                }
                placeholder="VD: kết quả học tập THPT"
                maxLength={200}
              />
            </Field>
            <Field
              label="Ghi chú quan hệ và phạm vi"
              hint="Ghi chú tự do, không dùng để lọc khi tìm kiếm."
            >
              <Textarea
                value={form.note}
                onChange={(event) =>
                  setForm({ ...form, note: event.target.value })
                }
                placeholder="VD: chỉ dùng khi hỏi về phương thức xét tuyển"
                rows={2}
                maxLength={1000}
              />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <Field label="Năm áp dụng" hint="Cách nhau bằng dấu phẩy.">
                <Input
                  value={form.years}
                  onChange={(event) =>
                    setForm({ ...form, years: event.target.value })
                  }
                  placeholder="VD: 2026"
                />
              </Field>
              <Field label="Phương thức" hint="Cách nhau bằng dấu phẩy.">
                <Input
                  value={form.methods}
                  onChange={(event) =>
                    setForm({ ...form, methods: event.target.value })
                  }
                  placeholder="VD: PT2"
                />
              </Field>
              <Field label="Thực thể" hint="Cách nhau bằng dấu phẩy.">
                <Input
                  value={form.entities}
                  onChange={(event) =>
                    setForm({ ...form, entities: event.target.value })
                  }
                  placeholder="VD: ngành sư phạm"
                />
              </Field>
            </div>
          </div>
          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <div className="grid grid-cols-2 gap-2 sm:flex sm:justify-end w-full">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFormOpen(false)}
              >
                Hủy
              </Button>
              <Button
                size="sm"
                disabled={saveMutation.isPending}
                onClick={() => saveMutation.mutate()}
              >
                {saveMutation.isPending ? (
                  <>
                    <RefreshCw className="size-3.5 animate-spin" />
                    Đang lưu...
                  </>
                ) : (
                  "Lưu"
                )}
              </Button>
            </div>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      <ResponsiveDialog
        open={reviewTarget !== null}
        onOpenChange={(open) => !open && setReviewTarget(null)}
      >
        <ResponsiveDialogContent className="sm:max-w-md max-h-[min(820px,calc(100vh-2rem))]">
          <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-3">
            <ResponsiveDialogTitle>
              {reviewTarget ? reviewLabels[reviewTarget.action].title : ""}
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              {reviewTarget
                ? `“${reviewTarget.term.user_phrase}” → “${reviewTarget.term.target_term}” (bản ${reviewTarget.term.version})`
                : ""}
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
            <Field label="Lý do" hint="Lưu vào dấu vết duyệt.">
              <Textarea
                value={reviewReason}
                onChange={(event) => setReviewReason(event.target.value)}
                placeholder="VD: đã đối chiếu với thông báo tuyển sinh"
                rows={2}
                maxLength={512}
              />
            </Field>
          </div>
          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <div className="grid grid-cols-2 gap-2 sm:flex sm:justify-end w-full">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReviewTarget(null)}
              >
                Hủy
              </Button>
              <Button
                size="sm"
                variant={
                  reviewTarget?.action === "revoke" ? "destructive" : "default"
                }
                disabled={reviewMutation.isPending}
                onClick={() => reviewMutation.mutate()}
              >
                {reviewTarget ? reviewLabels[reviewTarget.action].confirm : ""}
              </Button>
            </div>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>
    </div>
  );
}

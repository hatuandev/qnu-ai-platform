import { DocumentTypeForm } from "@/components/admin/document-type-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type DocumentTypeInput,
  type DocumentTypeItem,
  activateDocumentType,
  deactivateDocumentType,
  getDocumentType,
  updateDocumentType,
} from "@/services/document-types-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Database, FileText, Power, Save } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

interface DocumentTypeDetailPageProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

function getCodeFromPath(currentPath: string): string {
  const encodedCode = currentPath.split("/").filter(Boolean).at(-1) || "";
  return decodeURIComponent(encodedCode);
}

function toFormValue(item: DocumentTypeItem): DocumentTypeInput {
  return {
    code: item.code,
    name: item.name,
    category: item.category,
    description: item.description || "",
    priority: item.priority,
    retention_period: item.retention_period || "",
  };
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Không thể hoàn thành thao tác loại văn bản.";
}

export function DocumentTypeDetailPage({ currentPath, onNavigate }: DocumentTypeDetailPageProps) {
  const code = getCodeFromPath(currentPath);
  const queryClient = useQueryClient();
  const [formValue, setFormValue] = useState<DocumentTypeInput | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const documentTypeQuery = useQuery({
    queryKey: ["document-types", code],
    queryFn: () => getDocumentType(code),
    enabled: Boolean(code),
  });

  useEffect(() => {
    if (documentTypeQuery.data) {
      setFormValue(toFormValue(documentTypeQuery.data));
    }
  }, [documentTypeQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (input: DocumentTypeInput) =>
      updateDocumentType(code, { ...input, is_active: documentTypeQuery.data?.is_active }),
    onSuccess: (item) => {
      setFormValue(toFormValue(item));
      setFeedback("Đã cập nhật thông tin loại văn bản.");
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateDocumentType(code),
    onSuccess: (item) => {
      queryClient.setQueryData(["document-types", code], item);
      setFeedback("Đã vô hiệu hóa loại văn bản.");
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
  });

  const activateMutation = useMutation({
    mutationFn: () => activateDocumentType(code),
    onSuccess: (item) => {
      queryClient.setQueryData(["document-types", code], item);
      setFeedback("Đã kích hoạt lại loại văn bản.");
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
    },
  });

  const item = documentTypeQuery.data;
  const error =
    documentTypeQuery.error ||
    updateMutation.error ||
    deactivateMutation.error ||
    activateMutation.error;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formValue) return;
    setFeedback(null);
    updateMutation.mutate(formValue);
  };

  if (documentTypeQuery.isLoading) {
    return (
      <div className="py-16 text-center text-sm text-muted-foreground">
        Đang tải chi tiết taxonomy...
      </div>
    );
  }

  if (!item || !formValue) {
    return (
      <Card>
        <CardContent className="space-y-4 p-8">
          <p className="text-sm font-medium">Không tải được loại văn bản</p>
          <p className="text-xs text-muted-foreground">
            {error ? getErrorMessage(error) : "Mã loại văn bản không hợp lệ."}
          </p>
          <Button variant="outline" onClick={() => onNavigate("/document-types")}>
            <ArrowLeft className="size-4" />
            Quay lại danh mục
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Button
            className="mb-3 -ml-3"
            size="sm"
            variant="ghost"
            onClick={() => onNavigate("/document-types")}
          >
            <ArrowLeft className="size-4" />
            Loại văn bản
          </Button>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <FileText className="size-4 text-primary" />
            <span>Kho Tri thức / Loại văn bản / {item.code}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{item.name}</h1>
            <Badge variant={item.is_active ? "success" : "secondary"}>
              {item.is_active ? "Hoạt động" : "Đã tắt"}
            </Badge>
            {item.is_custom ? (
              <Badge variant="warning">Tùy chỉnh</Badge>
            ) : (
              <Badge variant="info">Core</Badge>
            )}
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{item.code}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {item.is_active ? (
            <Button
              disabled={deactivateMutation.isPending}
              variant="destructive"
              onClick={() => deactivateMutation.mutate()}
            >
              <Power className="size-4" />
              {deactivateMutation.isPending ? "Đang tắt..." : "Vô hiệu hóa"}
            </Button>
          ) : (
            <Button
              disabled={activateMutation.isPending}
              variant="outline"
              className="border-success/50 text-success hover:bg-success/10 hover:text-success"
              onClick={() => activateMutation.mutate()}
            >
              <Power className="size-4" />
              {activateMutation.isPending ? "Đang bật..." : "Kích hoạt lại"}
            </Button>
          )}
          <Button disabled={updateMutation.isPending} form="edit-document-type" type="submit">
            <Save className="size-4" />
            {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
          </Button>
        </div>
      </div>

      {feedback ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-4 py-3 text-xs text-success">
          {feedback}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {getErrorMessage(error)}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          <CardHeader>
            <CardTitle>Metadata loại văn bản</CardTitle>
            <CardDescription>
              Thông tin này được dùng để gắn nhãn ingestion và định tuyến nghiệp vụ.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DocumentTypeForm
              formId="edit-document-type"
              isCodeEditable={false}
              isSubmitting={updateMutation.isPending}
              onChange={setFormValue}
              onSubmit={handleSubmit}
              submitLabel="Lưu thay đổi"
              value={formValue}
            />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="size-4 text-primary" />
                Sử dụng
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Tài liệu đang gắn</span>
                <span className="font-semibold">{item.doc_count}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Chuẩn NĐ30</span>
                <span className="font-semibold">{item.nd30 ? "Có" : "Không"}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Lưu trữ</span>
                <span className="font-semibold">{item.retention_period || "Chưa cấu hình"}</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Nguồn đồng bộ</CardTitle>
              <CardDescription>Audit metadata của taxonomy.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>
                Source: <span className="text-foreground">{item.source_system}</span>
              </p>
              <p>
                Version:{" "}
                <span className="font-mono text-foreground">{item.source_version || "—"}</span>
              </p>
              <p className="break-all">
                Hash: <span className="font-mono text-foreground">{item.source_hash || "—"}</span>
              </p>
              <p>
                Đồng bộ:{" "}
                <span className="text-foreground">
                  {item.synced_at ? new Date(item.synced_at).toLocaleString("vi-VN") : "—"}
                </span>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

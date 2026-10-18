import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Calculator, Plus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { Field } from "@/components/admin/field";
import { FileUpload } from "@/components/admin/file-upload";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
import { scoreRulesApi } from "@/services/score-rules-api";
import type { ScoreRuleStatus } from "@/types/score-rules";
import { parseRuleImport } from "./score-rule-import";

export const SCORE_RULE_STATUS: Record<ScoreRuleStatus, string> = {
  draft: "Bản nháp",
  approved: "Đã duyệt · chưa dùng",
  active: "Đang dùng cho chatbot",
  revoked: "Đã thu hồi",
};

export function ScoreRuleList({ collectionId }: { collectionId: string }) {
  const { can } = useRbac();
  const client = useQueryClient();
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [importFiles, setImportFiles] = useState<File[]>([]);
  const query = useQuery({
    queryKey: ["score-rules", collectionId],
    queryFn: () => scoreRulesApi.list(collectionId),
  });
  const mutation = useMutation({
    mutationFn: async (raw: string) => {
      return scoreRulesApi.importDrafts(
        collectionId,
        parseRuleImport(raw),
        query.data?.version ?? 0,
        crypto.randomUUID(),
      );
    },
    onSuccess: () => {
      toast.success("Đã lưu bản nháp, chưa kích hoạt.");
      setIsImportOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
    onSettled: () =>
      client.invalidateQueries({ queryKey: ["score-rules", collectionId] }),
  });
  const form = useForm({
    defaultValues: { definition: "" },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync(value.definition).catch(() => undefined);
    },
  });
  if (query.isPending) return <Skeleton className="h-36" />;
  if (query.isError)
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {query.error.message}{" "}
          <Button variant="outline" size="sm" onClick={() => query.refetch()}>
            Thử lại
          </Button>
        </AlertDescription>
      </Alert>
    );
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">
            Quy đổi điểm có kiểm chứng
          </h2>
          <p className="text-sm text-muted-foreground">
            Bản nháp → Duyệt → Kích hoạt. Chỉ quy tắc đang hoạt động được
            chatbot sử dụng.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={query.isFetching}
            onClick={() => query.refetch()}
          >
            <RefreshCw className="size-3.5" />
            Làm mới
          </Button>
          {can("ai.knowledge.update") && (
            <Button size="sm" onClick={() => setIsImportOpen(!isImportOpen)}>
              <Plus className="size-3.5" />
              Nhập bản nháp
            </Button>
          )}
        </div>
      </div>
      {isImportOpen && (
        <form
          className="space-y-3 rounded-lg border border-border p-4"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit();
          }}
        >
          <p className="text-sm">
            Chọn tệp quy tắc đã chuẩn bị từ nguồn đã xuất bản, hoặc dán định
            nghĩa bên dưới. Dấu duyệt trong tệp không được tin cậy: mọi mục nhập
            vào đều là bản nháp. Muốn sửa quy tắc đã có, hãy tạo mã phiên bản
            mới.
          </p>
          <FileUpload
            accept=".json,application/json"
            maxFiles={1}
            maxSize={5 * 1024 * 1024}
            disabled={mutation.isPending}
            value={importFiles}
            onFilesChange={(files) => {
              setImportFiles(files);
              if (files[0])
                void files[0]
                  .text()
                  .then((value) => form.setFieldValue("definition", value))
                  .catch(() => toast.error("Không đọc được tệp quy tắc."));
            }}
          />
          <form.Field name="definition">
            {(field) => (
              <Field label="Định nghĩa quy tắc (JSON)" required>
                {(props) => (
                  <Textarea
                    {...props}
                    className="min-h-40 font-mono text-xs"
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                )}
              </Field>
            )}
          </form.Field>
          <Button type="submit" size="sm" disabled={mutation.isPending}>
            {mutation.isPending ? "Đang lưu..." : "Lưu bản nháp"}
          </Button>
        </form>
      )}
      {query.data.items.length === 0 ? (
        <EmptyState
          icon={Calculator}
          title="Chưa có quy tắc được quản lý"
          description="Nhập bản nháp có tham chiếu tới nguồn đã xuất bản, tính thử và đối chiếu trước khi duyệt. Không tự tạo bảng điểm từ model."
        />
      ) : (
        <div className="w-full overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quy tắc</TableHead>
                <TableHead>Năm</TableHead>
                <TableHead>Phương thức</TableHead>
                <TableHead>Trạng thái</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.items.map((item) => (
                <TableRow key={item.definition.id}>
                  <TableCell>
                    <Link
                      className="font-medium text-primary hover:underline"
                      to="/knowledge/$collectionId/score-rules/$ruleId"
                      params={{ collectionId, ruleId: item.definition.id }}
                    >
                      {item.definition.id}
                    </Link>
                  </TableCell>
                  <TableCell>{item.definition.year}</TableCell>
                  <TableCell>
                    {item.definition.source_method} →{" "}
                    {item.definition.target_method} ·{" "}
                    {item.definition.base_combination}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        item.status === "active" ? "success" : "secondary"
                      }
                    >
                      {SCORE_RULE_STATUS[item.status]}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

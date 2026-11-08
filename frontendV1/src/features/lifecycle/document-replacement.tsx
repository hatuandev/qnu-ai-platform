import { Link } from "@tanstack/react-router";
import { useState, useSyncExternalStore } from "react";
import { getTokenState, subscribeToken } from "@/app/api/v1/session-token";
import { ErrorState } from "@/components/admin/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCompiledVersionsQuery } from "@/features/knowledge/publication-queries";
import { LifecycleActionDialog } from "./action-dialog";

type Props = {
  workspaceId: string;
  collectionId: string;
  documentId: string;
  title: string;
};
export function DocumentReplacement(props: Props) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <ReplacementSession
      key={JSON.stringify([sessionId, props.workspaceId, props.documentId])}
      {...props}
    />
  );
}
function ReplacementSession({
  workspaceId,
  collectionId,
  documentId,
  title,
}: Props) {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState("");
  const [open, setOpen] = useState(false);
  const query = useCompiledVersionsQuery(
    workspaceId,
    collectionId,
    documentId,
    21,
    (page - 1) * 20,
  );
  const candidates = (query.data ?? [])
    .slice(0, 20)
    .filter((version) => version.status === "approved");
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardContent className="space-y-3 p-4">
        <h2 className="font-semibold text-sm">Thay bản phục vụ</h2>
        <p className="text-sm text-muted-foreground">
          Theo cơ chế thay thế, bản xuất bản hiện tại được giữ nguyên trong lúc
          chuẩn bị; chỉ chuyển khi chỉ mục mới sẵn sàng. Upload revision ở chế
          độ chuẩn bị → OCR → Compiler → đăng ký và duyệt phiên bản → chọn bản
          thay thế tại đây.
        </p>
        <p className="text-xs text-muted-foreground">
          Chỉ phiên bản đã duyệt mới có thể thay bản phục vụ. Bản xem trước sẽ
          báo nếu tài liệu chưa xuất bản hoặc nguồn dùng chung xung đột; hệ
          thống không tự thay thế hàng loạt.
        </p>
        <Button asChild variant="outline" size="sm">
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId"
            params={{ workspaceId, collectionId }}
            search={{ page: 1, pageSize: 20, tab: "sources" }}
          >
            Mở văn bản nguồn
          </Link>
        </Button>
        {query.isPending ? (
          <p role="status">Đang đọc phiên bản thay thế…</p>
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : (
          <>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Select
                value={selected || "none"}
                onValueChange={(value) =>
                  setSelected(value === "none" ? "" : value)
                }
              >
                <SelectTrigger
                  className="sm:max-w-sm"
                  aria-label="Phiên bản thay thế đã duyệt"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Chọn phiên bản đã duyệt</SelectItem>
                  {candidates.map((version) => (
                    <SelectItem key={version.id} value={version.id}>
                      Phiên bản {version.version_no} · Đã duyệt
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                disabled={
                  !candidates.some((version) => version.id === selected)
                }
                onClick={() => setOpen(true)}
              >
                Xem trước thay bản
              </Button>
            </div>
            {candidates.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Trang này chưa có phiên bản ở trạng thái đã duyệt để thay thế.
              </p>
            ) : null}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Button
                size="sm"
                variant="ghost"
                disabled={page === 1}
                onClick={() => {
                  setPage(page - 1);
                  setSelected("");
                }}
              >
                Trang trước
              </Button>
              <span>Trang {page}</span>
              <Button
                size="sm"
                variant="ghost"
                disabled={(query.data?.length ?? 0) <= 20}
                onClick={() => {
                  setPage(page + 1);
                  setSelected("");
                }}
              >
                Trang sau
              </Button>
            </div>
          </>
        )}
        {open && selected ? (
          <LifecycleActionDialog
            workspaceId={workspaceId}
            label={`${title} · bản thay thế đã duyệt`}
            target={{
              kind: "document",
              resource_id: documentId,
              action: "replace",
              replacement_version_id: selected,
            }}
            onClose={() => setOpen(false)}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

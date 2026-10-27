import { useState } from "react";
import { Combobox } from "@/components/admin/combobox";
import { ErrorState } from "@/components/admin/error-state";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { ListPagination } from "./list-pagination";
import { useCompiledDocumentsQuery } from "./publication-queries";
export type DocumentSelection = { id: string; title: string };
type Props = {
  workspaceId: string;
  collectionId: string;
  selected: DocumentSelection[];
  onChange: (documents: DocumentSelection[]) => void;
  allowedIds?: string[];
  disabled?: boolean;
};

export function DocumentScopePicker(props: Props) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <section aria-label="Phạm vi tài liệu" className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={props.disabled}
          onClick={() => setIsOpen(true)}
        >
          Chọn tài liệu
        </Button>
        <span className="text-xs text-muted-foreground">
          {props.selected.length
            ? `Chỉ tìm trong ${props.selected.length} tài liệu đã chọn`
            : "Toàn bộ tài liệu đủ điều kiện"}
        </span>
      </div>
      {props.selected.length ? (
        <ul className="flex flex-wrap gap-2" aria-label="Tài liệu đã chọn">
          {props.selected.map((document) => (
            <li
              key={document.id}
              className="flex items-center gap-2 min-w-0 max-w-full rounded-md border pl-2 text-sm"
            >
              <span className="min-w-0 break-words">{document.title}</span>
              <Button
                variant="ghost"
                type="button"
                size="sm"
                disabled={props.disabled}
                aria-label={`Bỏ tài liệu ${document.title}`}
                onClick={() =>
                  props.onChange(
                    props.selected.filter((item) => item.id !== document.id),
                  )
                }
              >
                Bỏ
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
      {isOpen ? (
        <DocumentScopeDialog {...props} onClose={() => setIsOpen(false)} />
      ) : null}
    </section>
  );
}
function DocumentScopeDialog({
  workspaceId,
  collectionId,
  selected,
  allowedIds,
  disabled,
  onChange,
  onClose,
}: Props & { onClose: () => void }) {
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const query = useCompiledDocumentsQuery(
    workspaceId,
    collectionId,
    pageSize,
    (page - 1) * pageSize,
    { lookahead: true },
  );
  const rows = (query.data ?? []).slice(0, pageSize);
  const available = rows.filter(
    (document) => !allowedIds || allowedIds.includes(document.id),
  );
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <ResponsiveDialogContent className="p-0 gap-0 flex flex-col max-h-[min(820px,calc(100vh-2rem))]">
        <ResponsiveDialogHeader className="p-4 border-b bg-muted/20">
          <ResponsiveDialogTitle>Chọn phạm vi tài liệu</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Tìm theo tiêu đề trong trang hiện tại, hoặc chuyển trang để xem các
            tài liệu khác. Server chỉ dùng bản đang xuất bản và còn đủ quyền.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="p-4 min-h-0 flex-1 overflow-y-auto space-y-4">
          <p className="text-sm">
            Đã chọn {selected.length}/100. Bỏ hết lựa chọn sẽ tìm trong toàn bộ
            tài liệu đủ điều kiện.
          </p>
          {query.isError ? (
            <ErrorState
              error={query.error}
              onRetry={() => void query.refetch()}
            />
          ) : (
            <Combobox
              options={available.map((document) => ({
                value: document.id,
                label: `${document.title} · ${document.document_key}`,
                disabled:
                  selected.some((d) => d.id === document.id) ||
                  selected.length >= 100,
              }))}
              value={undefined}
              loading={query.isPending}
              disabled={disabled || query.isFetching}
              placeholder="Thêm tài liệu theo tiêu đề…"
              searchPlaceholder="Lọc trong trang…"
              emptyMessage="Trang này không có tài liệu phù hợp."
              onValueChange={(id) => {
                const document = available.find((item) => item.id === id);
                if (
                  !document ||
                  disabled ||
                  selected.length >= 100 ||
                  selected.some((d) => d.id === id)
                )
                  return;
                onChange([
                  ...selected,
                  { id: document.id, title: document.title },
                ]);
              }}
            />
          )}
          {allowedIds ? (
            <p className="text-xs text-muted-foreground">
              Chỉ chọn tài liệu thuộc snapshot đang đánh giá. Trang này có{" "}
              {available.length} tài liệu phù hợp.
            </p>
          ) : null}
          <ul className="space-y-2 text-sm" aria-label="Phạm vi đang chọn">
            {selected.map((document) => (
              <li
                key={document.id}
                className="flex items-start justify-between gap-2"
              >
                <span className="break-words min-w-0">{document.title}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={disabled}
                  onClick={() =>
                    onChange(selected.filter((item) => item.id !== document.id))
                  }
                >
                  Bỏ
                </Button>
              </li>
            ))}
          </ul>
          <ListPagination
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            hasNext={!query.isError && (query.data?.length ?? 0) > pageSize}
            disabled={query.isFetching}
            label="bộ chọn tài liệu"
          />
        </div>
        <ResponsiveDialogFooter className="p-4 border-t bg-card">
          <Button variant="outline" type="button" onClick={onClose}>
            Xong
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

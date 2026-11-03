import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { CitationDetail } from "./compilation-types";
import { ListPagination } from "./list-pagination";

const PAGE_SIZE = 20;

/** Only the paragraph being edited mounts this shared, paginated index. */
export function CompilationCitationPicker({
  citations,
  selected,
  onToggle,
  onClose,
}: {
  citations: Record<string, CitationDetail>;
  selected: string[];
  onToggle: (id: string) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const choices = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase();
    return Object.entries(citations)
      .map(([id, detail], index) => ({ id, detail, number: index + 1 }))
      .filter(({ id, detail, number }) =>
        `${number} ${detail.filename ?? ""} ${detail.page_number ?? detail.page ?? ""} ${id}`
          .toLocaleLowerCase()
          .includes(needle),
      );
  }, [citations, search]);
  const visible = choices.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-xl max-h-[calc(100dvh-2rem)] flex flex-col">
        <DialogHeader>
          <DialogTitle>Dẫn chứng cho đoạn văn</DialogTitle>
          <DialogDescription>
            Chọn từ bằng chứng nguồn. Lựa chọn được cập nhật vào bản nháp; cần
            xem trước và xác nhận để lưu bản mới.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="citation-search">Tìm dẫn chứng</Label>
          <Input
            id="citation-search"
            value={search}
            placeholder="Tên tài liệu, trang hoặc số dẫn chứng…"
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
          <p className="text-xs text-muted-foreground" role="status">
            Đã chọn {selected.length} dẫn chứng.
          </p>
        </div>
        <div className="min-h-0 overflow-y-auto divide-y">
          {visible.map(({ id, detail, number }) => (
            <Label
              key={id}
              htmlFor={`citation-choice-${number}`}
              className="flex items-start gap-3 py-3 cursor-pointer text-sm"
            >
              <Checkbox
                id={`citation-choice-${number}`}
                checked={selected.includes(id)}
                onCheckedChange={() => onToggle(id)}
              />
              <span className="min-w-0">
                <span className="block font-medium">
                  Dẫn chứng {number} · Trang{" "}
                  {detail.page_number ?? detail.page ?? "chưa xác định"}
                </span>
                <span className="block break-words text-xs text-muted-foreground">
                  {detail.filename || "Tài liệu nguồn"}
                </span>
              </span>
            </Label>
          ))}
          {!visible.length && (
            <p className="py-6 text-sm text-muted-foreground">
              Không có dẫn chứng phù hợp.
            </p>
          )}
        </div>
        <ListPagination
          page={page}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
          hasNext={page * PAGE_SIZE < choices.length}
          label="dẫn chứng"
        />
        <DialogFooter>
          <Button onClick={onClose}>Xong</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

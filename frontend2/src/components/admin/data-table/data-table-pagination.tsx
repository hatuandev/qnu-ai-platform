import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

type PageItem = number | "ellipsis-left" | "ellipsis-right";

function pageItems(page: number, pageCount: number): PageItem[] {
  if (pageCount <= 7)
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  if (page <= 4) return [1, 2, 3, 4, 5, "ellipsis-right", pageCount];
  if (page >= pageCount - 3)
    return [
      1,
      "ellipsis-left",
      pageCount - 4,
      pageCount - 3,
      pageCount - 2,
      pageCount - 1,
      pageCount,
    ];
  return [
    1,
    "ellipsis-left",
    page - 1,
    page,
    page + 1,
    "ellipsis-right",
    pageCount,
  ];
}

export function DataTablePagination({
  page,
  pageSize,
  pageCount,
  onPageChange,
  onPageSizeChange,
  total,
  className,
  bordered = false,
}: {
  page: number;
  pageSize: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  total?: number;
  className?: string;
  bordered?: boolean;
}) {
  const items = pageItems(page, pageCount);
  return (
    <div
      className={cn(
        "flex flex-col gap-3 py-2 sm:flex-row sm:items-center sm:justify-between text-xs",
        bordered && "rounded-lg border bg-card px-3 py-3",
        className,
      )}
    >
      <div className="flex items-center justify-between sm:justify-start gap-3">
        <div className="flex items-center gap-2">
          <Select
            value={String(pageSize)}
            onValueChange={(value) => onPageSizeChange(Number(value))}
          >
            <SelectTrigger
              className="h-8 w-[68px] text-xs"
              aria-label="Số dòng mỗi trang"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="20">20</SelectItem>
              <SelectItem value="50">50</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-muted-foreground text-xs">dòng / trang</span>
        </div>

        {typeof total === "number" ? (
          <span className="text-muted-foreground text-xs">
            Tổng cộng:{" "}
            <strong className="text-foreground font-semibold">{total}</strong>
          </span>
        ) : null}
      </div>

      <div className="flex items-center justify-between sm:justify-end gap-2">
        <span className="text-muted-foreground text-xs">
          Trang <strong className="text-foreground font-medium">{page}</strong>{" "}
          / {pageCount}
        </span>

        {/* Desktop numeric pagination */}
        <div className="hidden items-center gap-1 sm:flex">
          <Button
            variant="outline"
            size="icon-sm"
            className="size-8"
            aria-label="Trang đầu"
            disabled={page <= 1}
            onClick={() => onPageChange(1)}
          >
            <ChevronsLeft className="size-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            className="size-8"
            aria-label="Trang trước"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft className="size-3.5" />
          </Button>
          {items.map((item, idx) =>
            typeof item === "string" ? (
              <span
                key={`${item}-${idx}`}
                className="px-1 text-xs text-muted-foreground"
              >
                …
              </span>
            ) : (
              <Button
                key={item}
                variant={item === page ? "secondary" : "outline"}
                size="icon-sm"
                className="size-8 text-xs font-medium"
                aria-label={`Trang ${item}`}
                aria-current={item === page ? "page" : undefined}
                onClick={() => onPageChange(item)}
              >
                {item}
              </Button>
            ),
          )}
          <Button
            variant="outline"
            size="icon-sm"
            className="size-8"
            aria-label="Trang sau"
            disabled={page >= pageCount}
            onClick={() => onPageChange(page + 1)}
          >
            <ChevronRight className="size-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            className="size-8"
            aria-label="Trang cuối"
            disabled={page >= pageCount}
            onClick={() => onPageChange(pageCount)}
          >
            <ChevronsRight className="size-3.5" />
          </Button>
        </div>

        {/* Mobile touch buttons */}
        <div className="flex items-center gap-1.5 sm:hidden">
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-2.5 text-xs"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft className="size-3.5 mr-0.5" />
            Trước
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-2.5 text-xs"
            disabled={page >= pageCount}
            onClick={() => onPageChange(page + 1)}
          >
            Sau
            <ChevronRight className="size-3.5 ml-0.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

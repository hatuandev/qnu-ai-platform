import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
export type ListPagingProps = {
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
};
/** Arrays have no total. A sentinel proves the next page, including size=100. */
export async function readArrayPage<T>(
  loadRows: (limit: number, offset: number) => Promise<T[]>,
  size: number,
  offset: number,
): Promise<T[]> {
  const rows = await loadRows(Math.min(100, size + 1), offset);
  if (size !== 100 || rows.length < 100) return rows;
  const extra = await loadRows(1, offset + size);
  return [...rows, ...extra.slice(0, 1)];
}
export function ListPagination({
  page = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
  hasNext,
  disabled = false,
  label = "Danh sách",
}: ListPagingProps & { hasNext: boolean; disabled?: boolean; label?: string }) {
  if (!onPageChange) return null;
  return (
    <nav
      aria-label={`Phân trang ${label}`}
      className="flex flex-wrap justify-between items-center gap-3 py-2 text-xs"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span>Trang {page}</span>
        {onPageSizeChange ? (
          <Select
            value={String(pageSize)}
            onValueChange={(v) => onPageSizeChange(Number(v))}
            disabled={disabled}
          >
            <SelectTrigger
              aria-label={`Số dòng ${label}`}
              className="w-32 text-xs h-8"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[10, 20, 50, 100].map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size} dòng/trang
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : null}
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Trang trước
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={disabled || !hasNext}
          onClick={() => onPageChange(page + 1)}
        >
          Trang sau
        </Button>
      </div>
    </nav>
  );
}

import { FileSpreadsheet, RefreshCw, Search, Table2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { FactItem } from "@/types";

interface CollectionFactsTabProps {
  facts: FactItem[];
  totalCount: number;
  isLoading: boolean;
  isFetching: boolean;
  searchQuery: string;
  onSearchChange: (val: string) => void;
  onRefresh: () => void;
  onOpenExcelImport: () => void;
}

export function CollectionFactsTab({
  facts,
  totalCount,
  isLoading,
  isFetching,
  searchQuery,
  onSearchChange,
  onRefresh,
  onOpenExcelImport,
}: CollectionFactsTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-3.5 sm:p-4 rounded-lg border border-border">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Table2 className="size-4 text-primary" />
            <span>Bảng Biểu & Số Liệu Trích Xuất (Facts Layer)</span>
            <Badge variant="outline" className="font-mono text-xs">
              {totalCount} facts
            </Badge>
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            Các số liệu chính xác 100% dạng bảng (điểm chuẩn, chỉ tiêu, học phí)
            được nạp trực tiếp từ bảng tính Excel/CSV để Trợ lý AI tra cứu đối
            soát, chống bịa đặt (Zero Hallucination).
          </p>
        </div>
        <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full sm:w-auto shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isFetching}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw
              className={cn("size-3.5", isFetching && "animate-spin")}
            />
            <span>Làm mới</span>
          </Button>
          <Button
            size="sm"
            onClick={onOpenExcelImport}
            className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <FileSpreadsheet className="size-3.5" />
            <span>Nạp Excel</span>
          </Button>
        </div>
      </div>

      {/* Search bar for facts */}
      <div className="flex items-center gap-2">
        <Search className="size-4 text-muted-foreground shrink-0" />
        <Input
          placeholder="Tìm theo thực thể (ngành, khoa), tên thuộc tính hoặc giá trị..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="h-8 text-xs w-full"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2 shrink-0"
            onClick={() => onSearchChange("")}
          >
            Xóa lọc
          </Button>
        )}
      </div>

      {/* 1. Mobile Facts Card View (< 640px) */}
      <div className="sm:hidden space-y-2.5">
        {isLoading ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            Đang tải danh sách bảng biểu số liệu...
          </div>
        ) : facts.length === 0 ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            <FileSpreadsheet className="size-8 mx-auto mb-2 opacity-30 text-primary" />
            <p className="text-sm font-medium text-foreground">
              {searchQuery
                ? "Không tìm thấy số liệu phù hợp với từ khóa"
                : "Chưa có bảng biểu số liệu nào trong kho này"}
            </p>
            {!searchQuery && (
              <Button
                size="sm"
                onClick={onOpenExcelImport}
                className="h-8 text-xs gap-1.5 mt-3"
              >
                <FileSpreadsheet className="size-3.5" />
                <span>Tải tệp Excel ngay</span>
              </Button>
            )}
          </div>
        ) : (
          facts.map((fact) => (
            <div
              key={fact.id}
              className="p-3.5 rounded-lg border border-border bg-card space-y-2 shadow-2xs"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-xs text-foreground">
                  {fact.entity_name}
                </span>
                <Badge
                  variant="outline"
                  className="text-[10px] px-1.5 py-0 font-normal uppercase shrink-0"
                >
                  {fact.entity_type}
                </Badge>
              </div>

              <div className="flex items-center justify-between text-xs pt-1.5 border-t border-border/50">
                <span className="text-muted-foreground font-mono text-[11px]">
                  {fact.attribute_name}
                </span>
                <span className="font-bold text-primary font-mono text-xs">
                  {fact.attribute_value}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1.5 border-t border-border/50">
                <Badge
                  variant="outline"
                  className="text-[10px] px-1.5 py-0 bg-success/10 text-success border-success/30 font-mono"
                >
                  {Math.round(fact.confidence * 100)}% tin cậy
                </Badge>
                <span className="text-[10px] font-mono">
                  {fact.created_at
                    ? new Date(fact.created_at).toLocaleDateString("vi-VN")
                    : "N/A"}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 2. Desktop & Tablet Facts Table (>= 640px) */}
      <div className="hidden sm:block bg-card rounded-lg border border-border overflow-hidden shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs font-semibold text-muted-foreground uppercase">
              <TableHead>Thực thể (Entity)</TableHead>
              <TableHead>Phân loại</TableHead>
              <TableHead>Thuộc tính (Attribute)</TableHead>
              <TableHead>Giá trị (Value)</TableHead>
              <TableHead>Độ tin cậy</TableHead>
              <TableHead>Thời điểm số hóa</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center py-12 text-xs text-muted-foreground"
                >
                  Đang tải danh sách bảng biểu số liệu...
                </TableCell>
              </TableRow>
            ) : facts.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center py-12 text-muted-foreground"
                >
                  <FileSpreadsheet className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                  <p className="text-sm font-medium text-foreground">
                    {searchQuery
                      ? "Không tìm thấy số liệu phù hợp với từ khóa"
                      : "Chưa có bảng biểu số liệu nào trong kho này"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                    Tải lên tệp Excel (.xlsx) hoặc CSV chứa các cột (Mã ngành,
                    Tên ngành, Điểm chuẩn, Chỉ tiêu, Học phí) để hệ thống tự
                    động bóc tách thành facts tra cứu.
                  </p>
                  {!searchQuery && (
                    <Button
                      size="sm"
                      onClick={onOpenExcelImport}
                      className="h-8 text-xs gap-1.5 mt-3"
                    >
                      <FileSpreadsheet className="size-3.5" />
                      <span>Tải tệp Excel ngay</span>
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ) : (
              facts.map((fact) => (
                <TableRow key={fact.id} className="hover:bg-muted/30 text-xs">
                  <TableCell className="font-semibold text-foreground">
                    {fact.entity_name}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className="text-xs font-normal uppercase"
                    >
                      {fact.entity_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {fact.attribute_name}
                  </TableCell>
                  <TableCell className="font-semibold text-primary font-mono">
                    {fact.attribute_value}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className="text-xs bg-success/10 text-success border-success/30"
                    >
                      {Math.round(fact.confidence * 100)}%
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">
                    {fact.created_at
                      ? new Date(fact.created_at).toLocaleString("vi-VN")
                      : "N/A"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

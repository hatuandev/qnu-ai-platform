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
import { FileSpreadsheet, RefreshCw, Search, Table2 } from "lucide-react";

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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-lg border border-border">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Table2 className="size-4 text-primary" />
            <span>Bảng Biểu & Số Liệu Trích Xuất (Facts Layer)</span>
            <Badge variant="outline" className="font-mono text-xs">
              {totalCount} facts
            </Badge>
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            Các số liệu chính xác 100% dạng bảng (điểm chuẩn, chỉ tiêu, học phí) được nạp trực tiếp
            từ bảng tính Excel/CSV để Trợ lý AI tra cứu đối soát, chống bịa đặt (Zero
            Hallucination).
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isFetching}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw className={cn("size-3.5", isFetching && "animate-spin")} />
            <span>Làm mới</span>
          </Button>
          <Button
            size="sm"
            onClick={onOpenExcelImport}
            className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <FileSpreadsheet className="size-3.5" />
            <span>+ Nạp Bảng Biểu Excel/CSV</span>
          </Button>
        </div>
      </div>

      {/* Search bar for facts */}
      <div className="flex items-center gap-2 bg-card p-3 rounded-lg border border-border">
        <Search className="size-4 text-muted-foreground shrink-0" />
        <Input
          placeholder="Tìm theo thực thể (ngành, khoa), tên thuộc tính (điểm chuẩn, chỉ tiêu) hoặc giá trị..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="h-8 text-xs"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2"
            onClick={() => onSearchChange("")}
          >
            Xóa lọc
          </Button>
        )}
      </div>

      {/* Facts Table */}
      <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
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
                <TableCell colSpan={6} className="text-center py-12 text-xs text-muted-foreground">
                  Đang tải danh sách bảng biểu số liệu...
                </TableCell>
              </TableRow>
            ) : facts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                  <FileSpreadsheet className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                  <p className="text-sm font-medium text-foreground">
                    {searchQuery
                      ? "Không tìm thấy số liệu phù hợp với từ khóa"
                      : "Chưa có bảng biểu số liệu nào trong kho này"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                    Tải lên tệp Excel (.xlsx) hoặc CSV chứa các cột (Mã ngành, Tên ngành, Điểm
                    chuẩn, Chỉ tiêu, Học phí) để hệ thống tự động bóc tách thành facts tra cứu.
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
                    <Badge variant="outline" className="text-xs font-normal uppercase">
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
                    {fact.created_at ? new Date(fact.created_at).toLocaleString("vi-VN") : "N/A"}
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

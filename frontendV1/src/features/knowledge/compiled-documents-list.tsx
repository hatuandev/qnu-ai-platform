import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  BookMarked,
  FileText,
  RefreshCw,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTimeValue } from "@/lib/date-utils";
import { ListPagination, type ListPagingProps } from "./list-pagination";
import { useCompiledDocumentsQuery } from "./publication-queries";

export function CompiledDocumentsList({
  workspaceId,
  collectionId,
  canRegister = false,
  onOpenCompilationTab,
  page = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
}: ListPagingProps & {
  workspaceId: string;
  collectionId: string;
  canRegister?: boolean;
  onOpenCompilationTab?: () => void;
}) {
  const [searchQuery, setSearchQuery] = useState("");

  const documentsQuery = useCompiledDocumentsQuery(
    workspaceId,
    collectionId,
    pageSize,
    (page - 1) * pageSize,
    { lookahead: true },
  );

  const rawDocs = (documentsQuery.data ?? []).slice(0, pageSize);

  const filteredDocs = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return rawDocs;
    return rawDocs.filter(
      (doc) =>
        doc.title.toLowerCase().includes(q) ||
        doc.document_key.toLowerCase().includes(q) ||
        doc.id.toLowerCase().includes(q),
    );
  }, [rawDocs, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            <BookMarked className="size-4 text-primary" />
            Tài liệu biên soạn trong kho
          </h2>
          <p className="text-xs text-muted-foreground">
            Danh sách các tài liệu đã được hình thành từ các kết quả biên soạn
            (Compiler runs).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-56">
            <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Lọc trong trang..."
              className="pl-8 text-xs h-8"
            />
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => void documentsQuery.refetch()}
            disabled={documentsQuery.isFetching}
            className="h-8 px-2.5 text-xs gap-1"
            title="Làm mới"
          >
            <RefreshCw
              className={`size-3.5 ${
                documentsQuery.isFetching ? "animate-spin" : ""
              }`}
            />
            <span className="hidden sm:inline">Làm mới</span>
          </Button>
        </div>
      </div>

      {/* Content state */}
      {documentsQuery.isLoading ? (
        <Card className="rounded-xl shadow-2xs p-4 space-y-3">
          <Skeleton className="h-6 w-36" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </Card>
      ) : documentsQuery.isError ? (
        <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs space-y-2">
          <div className="flex items-center gap-2 text-destructive font-semibold">
            <AlertCircle className="size-4 shrink-0" />
            <span>Không thể tải danh sách tài liệu biên soạn</span>
          </div>
          <p className="text-muted-foreground">
            {documentsQuery.error instanceof Error
              ? documentsQuery.error.message
              : "Đã xảy ra lỗi khi tải dữ liệu từ máy chủ."}
          </p>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            onClick={() => void documentsQuery.refetch()}
          >
            Thử lại
          </Button>
        </Card>
      ) : filteredDocs.length === 0 ? (
        <Card className="rounded-xl shadow-2xs">
          <CardContent className="py-12 text-center space-y-3">
            <div className="size-12 rounded-full bg-muted/60 flex items-center justify-center mx-auto text-muted-foreground">
              <BookMarked className="size-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">
                {searchQuery.trim()
                  ? "Không tìm thấy tài liệu phù hợp"
                  : "Chưa có tài liệu biên soạn nào"}
              </h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                {searchQuery.trim()
                  ? `Không tìm thấy tài liệu nào khớp với từ khóa "${searchQuery}".`
                  : "Tài liệu biên soạn được tạo từ các lượt Compiler run đã hoàn tất. Vào tab 'Biên soạn tri thức' để bắt đầu biên soạn và đăng ký."}
              </p>
            </div>
            {onOpenCompilationTab && !searchQuery.trim() && (
              <Button
                size="sm"
                variant={canRegister ? "default" : "outline"}
                onClick={onOpenCompilationTab}
                className="text-xs gap-1.5 mt-2"
              >
                <FileText className="size-3.5" />
                <span>
                  {canRegister
                    ? "Bắt đầu biên soạn trong kho"
                    : "Xem danh sách lượt biên soạn"}
                </span>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-xl shadow-2xs overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                <TableHead className="text-xs font-semibold">
                  Tài liệu & Key
                </TableHead>
                <TableHead className="text-xs font-semibold text-center w-28">
                  Thay đổi (#)
                </TableHead>
                <TableHead className="text-xs font-semibold text-right w-44">
                  Ngày tạo
                </TableHead>
                <TableHead className="w-20 text-right" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDocs.map((doc) => (
                <TableRow
                  key={doc.id}
                  className="hover:bg-muted/40 transition-colors"
                >
                  <TableCell className="py-3">
                    <div className="space-y-1 min-w-0">
                      <Link
                        to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId"
                        params={{
                          workspaceId,
                          collectionId,
                          documentId: doc.id,
                        }}
                        className="text-xs sm:text-sm font-semibold text-foreground hover:text-primary transition-colors line-clamp-1 block"
                      >
                        {doc.title}
                      </Link>
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge
                          variant="outline"
                          className="font-mono text-[11px] bg-muted/40 text-muted-foreground border-border"
                        >
                          key: {doc.document_key}
                        </Badge>
                        <span className="text-[11px] font-mono text-muted-foreground/70">
                          {doc.id}
                        </span>
                      </div>
                    </div>
                  </TableCell>

                  <TableCell className="py-3 text-center">
                    <Badge variant="secondary" className="font-mono text-xs">
                      seq #{doc.change_sequence}
                    </Badge>
                  </TableCell>

                  <TableCell className="py-3 text-right text-xs text-muted-foreground">
                    <div>{formatDateTimeValue(doc.created_at)}</div>
                    <div className="text-[11px] text-muted-foreground/70 truncate">
                      bởi {doc.created_by}
                    </div>
                  </TableCell>

                  <TableCell className="py-3 text-right">
                    <Button
                      asChild
                      size="sm"
                      variant="ghost"
                      className="h-8 px-2 text-xs"
                    >
                      <Link
                        to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId"
                        params={{
                          workspaceId,
                          collectionId,
                          documentId: doc.id,
                        }}
                        title="Xem chi tiết tài liệu"
                      >
                        <ArrowRight className="size-4" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      <ListPagination
        page={page}
        pageSize={pageSize}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        hasNext={(documentsQuery.data?.length ?? 0) > pageSize}
        disabled={documentsQuery.isFetching}
        label="tài liệu biên soạn"
      />
    </div>
  );
}

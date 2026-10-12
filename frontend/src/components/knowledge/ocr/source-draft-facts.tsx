import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SourceArtifact } from "@/types/knowledge";

export function SourceDraftFacts({ artifact }: { artifact?: SourceArtifact }) {
  if (!artifact)
    return (
      <p className="text-xs text-muted-foreground">
        Bản nguồn chưa có facts dự thảo.
      </p>
    );
  return (
    <section className="space-y-2 rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">
          Facts dự thảo ({artifact.facts.length})
        </h3>
        <Badge variant="outline">
          {artifact.review.status === "approved"
            ? "Đã duyệt"
            : artifact.issues.length
              ? "Cần duyệt"
              : "Chưa xuất bản"}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        Trích từ Markdown của bản nguồn này. Sửa Markdown rồi lưu để tạo lại
        facts. Duyệt bản nguồn đồng thời duyệt tập facts; chưa dùng cho chatbot
        đến khi nạp và xuất bản.
      </p>
      {artifact.issues.length > 0 && (
        <p className="text-xs text-warning">
          {artifact.issues.length} vấn đề cấu trúc cần đối chiếu:{" "}
          {[...new Set(artifact.issues.map((issue) => issue.code))].join(", ")}
        </p>
      )}
      <div className="max-h-80 w-full overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Thực thể</TableHead>
              <TableHead>Thuộc tính</TableHead>
              <TableHead>Giá trị</TableHead>
              <TableHead>Nguồn</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {artifact.facts.map((fact) => (
              <TableRow key={fact.id}>
                <TableCell>{fact.entity_name}</TableCell>
                <TableCell>{fact.attribute_name}</TableCell>
                <TableCell>{fact.attribute_value}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  Trang {String(fact.raw_data.page_number ?? "?")} ·{" "}
                  {String(fact.raw_data.table_id)} · hàng{" "}
                  {Number(fact.raw_data.row_index) + 1}, cột{" "}
                  {Number(fact.raw_data.column_index) + 1}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}

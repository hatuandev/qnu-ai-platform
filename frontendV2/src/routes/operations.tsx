import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/operations")({
  component: OperationsPage,
});

function OperationsPage() {
  const operations = [
    {
      id: "op_01",
      name: "Bóc tách OCR tài liệu D01",
      type: "OCR & Document Parsing",
      target: "Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx",
      status: "completed",
      startedAt: "2026-11-09 10:15",
      duration: "4.2s",
    },
    {
      id: "op_02",
      name: "Lập chỉ mục vector Qwen",
      type: "Vector Embedding & Indexing",
      target: "Kho tri thức tuyển sinh 2026",
      status: "completed",
      startedAt: "2026-11-09 10:20",
      duration: "12.8s",
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Hệ thống & Vận hành"
        title="Tác vụ & Tiến trình"
        description="Lịch sử các tiến trình chạy ngầm: bóc tách OCR, đối soát văn bản, trích xuất cấu trúc và lập chỉ mục RAG."
        actions={
          <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
            <RefreshCw className="size-3.5" />
            <span>Làm mới</span>
          </Button>
        }
      />

      <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="h-10 text-xs">
              <TableHead className="w-[280px]">Tên tác vụ</TableHead>
              <TableHead>Loại tác vụ</TableHead>
              <TableHead>Đối tượng</TableHead>
              <TableHead className="w-[120px]">Trạng thái</TableHead>
              <TableHead className="w-[140px]">Thời gian</TableHead>
              <TableHead className="w-[100px] text-right">Thời lượng</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {operations.map((op) => (
              <TableRow key={op.id} className="h-11 text-xs">
                <TableCell className="font-medium text-foreground">
                  {op.name}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {op.type}
                </TableCell>
                <TableCell className="text-muted-foreground truncate max-w-[200px]">
                  {op.target}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] gap-1"
                  >
                    <CheckCircle2 className="size-2.5" />
                    <span>Hoàn thành</span>
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {op.startedAt}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {op.duration}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, Plus, RefreshCw } from "lucide-react";
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

export const Route = createFileRoute("/modelops")({
  component: ModelOpsPage,
});

function ModelOpsPage() {
  const models = [
    {
      id: "qwen-2.5-coder",
      name: "Qwen 2.5 Coder 32B Instruct",
      provider: "vLLM Local Server",
      family: "Qwen",
      context: "32,768 tokens",
      status: "ready",
      preferredFor: "RAG & Trích xuất tài liệu",
    },
    {
      id: "gpt-4o",
      name: "GPT-4o",
      provider: "OpenAI Platform",
      family: "GPT",
      context: "128,000 tokens",
      status: "ready",
      preferredFor: "Biên tập & Đánh giá chất lượng",
    },
    {
      id: "gemini-2.0-flash",
      name: "Gemini 2.0 Flash",
      provider: "Google Vertex AI",
      family: "Gemini",
      context: "1,048,576 tokens",
      status: "ready",
      preferredFor: "Tốc độ cao & Hỏi đáp tổng quan",
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Quản trị trí tuệ nhân tạo"
        title="Mô hình AI & Nhà cung cấp"
        description="Quản lý danh sách các mô hình ngôn ngữ lớn (LLM), trạng thái kết nối, cấu hình định tuyến và hạn ngạch quota."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
              <RefreshCw className="size-3.5" />
              <span>Kiểm tra kết nối</span>
            </Button>
            <Button size="sm" className="h-8 gap-1.5 text-xs">
              <Plus className="size-3.5" />
              <span>Thêm mô hình</span>
            </Button>
          </div>
        }
      />

      <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="h-10 text-xs">
              <TableHead className="w-[260px]">Tên mô hình</TableHead>
              <TableHead>Nhà cung cấp</TableHead>
              <TableHead>Họ mô hình</TableHead>
              <TableHead>Ngữ cảnh tối đa</TableHead>
              <TableHead>Mục đích ưu tiên</TableHead>
              <TableHead className="w-[120px]">Trạng thái</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {models.map((m) => (
              <TableRow key={m.id} className="h-11 text-xs">
                <TableCell className="font-semibold text-foreground">
                  {m.name}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {m.provider}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                    {m.family}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground font-mono text-[11px]">
                  {m.context}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {m.preferredFor}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] gap-1"
                  >
                    <CheckCircle2 className="size-2.5" />
                    <span>Sẵn sàng</span>
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

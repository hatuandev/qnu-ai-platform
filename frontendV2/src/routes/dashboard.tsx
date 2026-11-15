import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  Cpu,
  FileText,
  MessagesSquare,
} from "lucide-react";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <PageHeader
        eyebrow="Hệ thống AI ĐH Quy Nhơn"
        title="Tổng quan nền tảng"
        description="Theo dõi tình trạng hoạt động của kho tri thức, các mô hình ngôn ngữ lớn và các phiên hỏi đáp trợ lý."
        actions={
          <div className="flex items-center gap-2">
            <Button asChild size="sm" className="gap-1.5 h-8">
              <Link to="/knowledge">
                <BookOpen className="size-3.5" />
                <span>Kho tri thức</span>
              </Link>
            </Button>
          </div>
        }
      />

      {/* KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <KpiMetric
          label="Tài liệu tri thức"
          value="8"
          icon={FileText}
          helper="Toàn bộ tệp đã hoàn tất bóc tách & đối soát"
        />
        <KpiMetric
          label="Mô hình hoạt động"
          value="4"
          icon={Cpu}
          helper="Qwen 2.5, GPT-4o, Gemini Flash"
        />
        <KpiMetric
          label="Trạng thái hệ thống"
          value="Sẵn sàng"
          icon={CheckCircle2}
          helper="Tất cả dịch vụ backend V1 ổn định"
        />
      </div>

      {/* Quick Launch Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:border-primary/50 transition-colors shadow-2xs">
          <CardHeader className="pb-3">
            <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-2">
              <BookOpen className="size-4" />
            </div>
            <CardTitle className="text-sm font-semibold">
              Kho tri thức
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Quản lý tài liệu Word, PDF, bảng biểu OCR và theo dõi quy trình
              biên tập tài liệu đào tạo.
            </p>
            <Link
              to="/knowledge"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <span>Truy cập kho tri thức</span>
              <ArrowRight className="size-3" />
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 transition-colors shadow-2xs">
          <CardHeader className="pb-3">
            <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-2">
              <Bot className="size-4" />
            </div>
            <CardTitle className="text-sm font-semibold">Trợ lý AI</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Cấu hình trợ lý ảo theo phòng ban, liên kết nguồn tài liệu và
              thiết lập tham số sinh văn bản.
            </p>
            <Link
              to="/assistants"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <span>Quản lý trợ lý</span>
              <ArrowRight className="size-3" />
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 transition-colors shadow-2xs">
          <CardHeader className="pb-3">
            <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-2">
              <MessagesSquare className="size-4" />
            </div>
            <CardTitle className="text-sm font-semibold">
              Hội thoại & RAG
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Tra cứu thông tin chính xác với trích dẫn minh chứng từ các văn
              bản chính thức của nhà trường.
            </p>
            <Link
              to="/chat"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <span>Bắt đầu trò chuyện</span>
              <ArrowRight className="size-3" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

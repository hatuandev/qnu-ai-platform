import { createFileRoute } from "@tanstack/react-router";
import { LifeBuoy } from "lucide-react";
import { PageHeader } from "@/components/admin/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/help")({ component: HelpPage });

function HelpPage() {
  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Phát triển"
        title="Trung tâm trợ giúp"
        description="Tìm hướng dẫn sử dụng không gian làm việc Admin Starter."
      />
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LifeBuoy className="size-4 text-primary" />
            Hướng dẫn bắt đầu
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Nội dung của trung tâm trợ giúp sẽ được bổ sung khi tài liệu sản
            phẩm sẵn sàng.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

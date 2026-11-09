import { createFileRoute } from "@tanstack/react-router";
import { Moon, Sun } from "lucide-react";
import { Field, FieldLabel } from "@/components/admin/field";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useUiStore } from "@/lib/ui-store";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const { theme, setTheme } = useUiStore();

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Tùy chỉnh hệ thống"
        title="Cài đặt cấu hình"
        description="Quản lý giao diện, khóa API nhà cung cấp và thông tin phiên làm việc hiện tại."
      />

      <div className="space-y-4">
        {/* Theme Settings */}
        <Card className="shadow-2xs">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Giao diện người dùng
            </CardTitle>
            <CardDescription className="text-xs">
              Chọn chủ đề sáng hoặc tối theo sở thích thị giác.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-3">
            <Button
              variant={theme === "light" ? "default" : "outline"}
              size="sm"
              onClick={() => setTheme("light")}
              className="gap-2 text-xs"
            >
              <Sun className="size-3.5" />
              <span>Chế độ Sáng</span>
            </Button>
            <Button
              variant={theme === "dark" ? "default" : "outline"}
              size="sm"
              onClick={() => setTheme("dark")}
              className="gap-2 text-xs"
            >
              <Moon className="size-3.5" />
              <span>Chế độ Tối</span>
            </Button>
          </CardContent>
        </Card>

        {/* Backend & Environment */}
        <Card className="shadow-2xs">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">
                Chế độ xem trước Giao diện (Standalone UI)
              </CardTitle>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 font-medium">
                Đã ngắt API
              </span>
            </div>
            <CardDescription className="text-xs">
              Toàn bộ dữ liệu hiển thị là dữ liệu mẫu mô phỏng (Mock Data),
              không gửi bất kỳ yêu cầu mạng nào đến máy chủ.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field className="gap-2">
              <FieldLabel
                htmlFor="api-endpoint"
                className="text-xs font-semibold text-foreground"
              >
                Trạng thái API
              </FieldLabel>
              <Input
                id="api-endpoint"
                readOnly
                value="Tắt kết nối API (Chỉ chạy giao diện với Mock Data nội bộ)"
                className="h-9 text-xs font-mono bg-muted/40 text-emerald-600 font-medium"
              />
            </Field>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

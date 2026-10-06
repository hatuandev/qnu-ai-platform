import { Power, RotateCcw } from "lucide-react";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AssistantItem } from "@/services/api-client";

interface AssistantDangerZoneProps {
  assistant: AssistantItem;
  isDeactivating: boolean;
  isActivating: boolean;
  onDeactivate: () => void;
  onActivate: () => void;
}

export function AssistantDangerZone({
  assistant,
  isDeactivating,
  isActivating,
  onDeactivate,
  onActivate,
}: AssistantDangerZoneProps) {
  return (
    <Card
      className={
        assistant.is_active ? "border-destructive/30" : "border-success/30"
      }
    >
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-bold">
          {assistant.is_active
            ? "Vùng Nguy Hiểm"
            : "Khôi Phục Trạng Thái Hoạt Động"}
        </CardTitle>
        <CardDescription className="text-xs">
          {assistant.is_active
            ? "Vô hiệu hóa trợ lý nhưng bảo lưu toàn bộ đồ thị workflow và lịch sử kiểm toán."
            : "Kích hoạt lại trợ lý để tiếp tục tiếp nhận các phiên hội thoại và phục vụ người dùng."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {assistant.is_active ? (
          <ConfirmDialog
            confirmText="Vô hiệu hóa"
            description={`Trợ lý “${assistant.name}” sẽ dừng nhận các phiên hội thoại mới cho đến khi được kích hoạt lại.`}
            isPending={isDeactivating}
            title="Vô hiệu hóa trợ lý?"
            trigger={
              <Button
                type="button"
                variant="destructive"
                size="sm"
                className="text-xs gap-1.5"
              >
                <Power className="size-3.5" />
                Vô hiệu hóa trợ lý
              </Button>
            }
            onConfirm={onDeactivate}
          />
        ) : (
          <ConfirmDialog
            confirmText="Kích hoạt lại"
            description={`Trợ lý “${assistant.name}” sẽ mở lại trạng thái hoạt động bình thường trên kênh Chat và Widget.`}
            isPending={isActivating}
            title="Kích hoạt lại trợ lý?"
            trigger={
              <Button
                type="button"
                variant="default"
                size="sm"
                className="text-xs gap-1.5 bg-success hover:bg-success/90 text-success-foreground"
              >
                <RotateCcw className="size-3.5" />
                Kích hoạt lại trợ lý
              </Button>
            }
            onConfirm={onActivate}
          />
        )}
      </CardContent>
    </Card>
  );
}

import { Info } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function TemplateNotice() {
  return (
    <Alert className="mb-6">
      <Info className="size-4" />
      <AlertDescription>
        Bản mẫu KTX · Chỉ tham khảo giao diện. Chưa kết nối đăng nhập hoặc API;
        dữ liệu mẫu và vai trò thử không có quyền trên hệ thống thật.
      </AlertDescription>
    </Alert>
  );
}

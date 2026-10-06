import { ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
export function AccessDenied() {
  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-destructive" />
          Không có quyền truy cập
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Tài khoản hiện tại không được cấp quyền truy cập khu vực này.
        </p>
      </CardContent>
    </Card>
  );
}

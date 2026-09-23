import { ShieldCheck } from "lucide-react";
import type React from "react";
import { Card } from "../../components/ui/card";

export interface ResiliencePolicyCardProps {
  activeProviderNames: string[];
}

export const ResiliencePolicyCard: React.FC<ResiliencePolicyCardProps> = ({
  activeProviderNames,
}) => {
  return (
    <div className="space-y-3.5">
      <h2 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-primary" />
        Chính Sách Chuyển Vùng Dự Phòng (Dynamic Fallback & Key Rotation)
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4 space-y-2">
          <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-primary" />
            Cơ Chế JIT Key Failover Trong Nhóm (Key Pool)
          </h4>
          <div className="p-3 rounded-md bg-muted/40 border border-border/80 text-xs space-y-1 font-mono">
            <p className="text-foreground">
              Tự động chuyển khóa:{" "}
              <span className="text-primary font-bold">
                Priority #1 → #2 → #3
              </span>
            </p>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Khi một khóa chạm Rate Limit HTTP 429 hoặc cạn Token Quota, hệ thống
            lập tức chuyển sang khóa dự phòng kế tiếp và đưa khóa cũ vào thời
            gian nghỉ (Cooldown 60s).
          </p>
        </Card>

        <Card className="p-4 space-y-2">
          <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-info" />
            Chuyển Vùng Nhà Cung Cấp Fallback (Circuit Breaker)
          </h4>
          <div className="p-3 rounded-md bg-muted/40 border border-border/80 text-xs space-y-1 font-mono">
            <p className="text-foreground">
              Thứ tự Provider:{" "}
              <span className="text-primary font-bold">
                {activeProviderNames.join(" → ") ||
                  "Chưa có provider kích hoạt"}
              </span>
            </p>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Nếu toàn bộ khóa trong nhóm của nhà cung cấp chính đều kiệt sức hoặc
            lỗi mạng quá 15 giây, Circuit Breaker sẽ nhảy sang Provider dự phòng
            kế tiếp.
          </p>
        </Card>
      </div>
    </div>
  );
};

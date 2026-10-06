import { Link } from "@tanstack/react-router";
import { ArrowRight, LifeBuoy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function SupportCard({ className }: { className?: string }) {
  return (
    <Card
      className={cn(
        "border-border/60 bg-gradient-to-r from-card via-card to-primary/5 shadow-xs transition-colors hover:border-primary/30",
        className,
      )}
    >
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3 sm:items-center sm:gap-3.5">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary sm:size-11">
              <LifeBuoy className="size-5" />
            </div>
            <div className="min-w-0 space-y-0.5">
              <h3 className="text-sm font-semibold tracking-tight text-foreground sm:text-base">
                Cần hỗ trợ hoặc báo cáo sự cố?
              </h3>
              <p className="text-xs text-muted-foreground sm:text-sm">
                Gửi yêu cầu tới Ban quản lý KTX khi bạn gặp sự cố về điện, nước,
                cơ sở vật chất hoặc chi phí.
              </p>
            </div>
          </div>
          <Button
            asChild
            size="sm"
            variant="outline"
            className="h-9 shrink-0 gap-1.5 self-start font-medium shadow-xs sm:self-center"
          >
            <Link to="/support" search={{ q: "", page: 1, pageSize: 10 }}>
              Gửi yêu cầu <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

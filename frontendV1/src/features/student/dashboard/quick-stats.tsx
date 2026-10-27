import { Link } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type QuickStatItem = {
  icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
  badge?: {
    text: string;
    variant: "default" | "success" | "warning" | "secondary";
  };
  to?: string;
  search?: Record<string, unknown>;
};

export function QuickStatsGrid({ items }: { items: QuickStatItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-4">
      {items.map((item) => {
        const content = (
          <Card className="h-full transition-colors hover:bg-muted/30">
            <CardContent className="flex items-start gap-2.5 p-3 sm:gap-3 sm:p-4">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary sm:size-9">
                <item.icon className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] text-muted-foreground sm:text-xs">
                  {item.label}
                </p>
                <p className="truncate text-sm font-semibold sm:text-base">
                  {item.value}
                </p>
                {item.sub ? (
                  <p className="truncate text-[11px] text-muted-foreground sm:text-xs">
                    {item.sub}
                  </p>
                ) : null}
                {item.badge ? (
                  <Badge
                    variant={item.badge.variant}
                    className="mt-1 px-1.5 py-0 text-[10px]"
                  >
                    {item.badge.text}
                  </Badge>
                ) : null}
              </div>
            </CardContent>
          </Card>
        );
        return (
          <div
            key={item.label}
            className={cn(item.to && "transition-opacity hover:opacity-80")}
          >
            {item.to ? (
              <Link to={item.to} search={item.search as never}>
                {content}
              </Link>
            ) : (
              content
            )}
          </div>
        );
      })}
    </div>
  );
}

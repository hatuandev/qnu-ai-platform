import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { resourceLabel } from "@/features/activity/activity-item";
import type { ActivityEvent } from "@/features/activity/types";
import { formatDateTimeValue } from "@/lib/date-utils";

export function ActivityDetailSheet({
  event,
  open,
  onOpenChange,
}: {
  event: ActivityEvent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!event) return null;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full max-w-none flex-col overflow-hidden sm:max-w-lg"
      >
        <SheetHeader className="border-b px-5 pb-4">
          <SheetTitle>Chi tiết hoạt động</SheetTitle>
          <SheetDescription>
            {event.actor} {event.action} {event.subject}.
          </SheetDescription>
        </SheetHeader>
        <dl className="grid min-h-0 flex-1 content-start grid-cols-[110px_minmax(0,1fr)] gap-x-4 gap-y-4 overflow-y-auto px-5 py-5 text-sm">
          <dt className="text-muted-foreground">Sự kiện</dt>
          <dd>
            <Badge variant="outline">{resourceLabel(event.resource)}</Badge>
            <div className="type-metadata mt-1 font-mono text-muted-foreground">
              {event.type}
            </div>
          </dd>
          <dt className="text-muted-foreground">Người thực hiện</dt>
          <dd className="font-medium">{event.actor}</dd>
          <dt className="text-muted-foreground">Hành động</dt>
          <dd>{event.action}</dd>
          <dt className="text-muted-foreground">Đối tượng</dt>
          <dd className="font-medium">{event.subject}</dd>
          <dt className="text-muted-foreground">Thời gian</dt>
          <dd>{formatDateTimeValue(event.createdAt)}</dd>
          {event.metadata ? (
            <>
              <dt className="text-muted-foreground">Metadata</dt>
              <dd className="space-y-2">
                {Object.entries(event.metadata).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-xs text-muted-foreground">{key}</span>
                    <div>{value}</div>
                  </div>
                ))}
              </dd>
            </>
          ) : null}
        </dl>
      </SheetContent>
    </Sheet>
  );
}

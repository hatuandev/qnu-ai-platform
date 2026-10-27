import { Link2, Settings2, ShieldCheck, Users } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { ActivityEvent } from "@/features/activity/types";

const resourceLabels = {
  users: "Người dùng",
  roles: "Vai trò",
  settings: "Cài đặt",
  security: "Bảo mật",
} as const;

const resourceIcons = {
  users: Users,
  roles: ShieldCheck,
  settings: Settings2,
  security: Link2,
} as const;

export function ActivityItem({
  event,
  onClick,
}: {
  event: ActivityEvent;
  onClick: () => void;
}) {
  const Icon = resourceIcons[event.resource];
  return (
    <button
      type="button"
      className="group flex w-full items-start gap-3 border-b px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-muted/40 sm:px-5"
      onClick={onClick}
    >
      <Avatar className="mt-0.5 size-8 shrink-0">
        <AvatarFallback className="type-metadata font-semibold">
          {event.actorInitials}
        </AvatarFallback>
      </Avatar>
      <span className="min-w-0 flex-1">
        <span className="block text-sm text-foreground">
          <strong className="font-semibold">{event.actor}</strong>{" "}
          {event.action}{" "}
          <strong className="font-semibold">{event.subject}</strong>
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Icon className="size-3.5" />
            {resourceLabels[event.resource]}
          </span>
          <span aria-hidden="true">·</span>
          <time dateTime={event.createdAt}>
            {formatRelative(event.createdAt)}
          </time>
        </span>
      </span>
    </button>
  );
}

export function resourceLabel(resource: ActivityEvent["resource"]) {
  return resourceLabels[resource];
}

function formatRelative(value: string) {
  const difference = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(difference / 60000));
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.round(hours / 24);
  return `${days} ngày trước`;
}

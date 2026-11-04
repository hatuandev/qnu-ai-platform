import {
  Archive,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  RotateCcw,
  Trash2,
  XCircle,
} from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import { getTokenState, subscribeToken } from "@/app/api/v1/session-token";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LifecycleActionDialog } from "./action-dialog";
import { canLifecycleAction } from "./permissions";
import {
  ACTION_LABEL,
  type CancellableJobKind,
  type LifecycleOperation,
  type ResourceKind,
} from "./types";

type Props = {
  workspaceId: string;
  kind: ResourceKind;
  resourceId: string;
  label: string;
  role?: CallerWorkspaceRole;
  ownedConversation?: boolean;
  status?: string;
  isActive?: boolean;
  jobKind?: CancellableJobKind;
  compact?: boolean;
  onRename?: () => void;
  onDeleted?: () => void;
};
export function LifecycleActions(props: Props) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <ActionMenu
      key={JSON.stringify([
        sessionId,
        props.workspaceId,
        props.kind,
        props.resourceId,
      ])}
      {...props}
    />
  );
}
function ActionMenu(props: Props) {
  const [selected, setSelected] = useState<LifecycleOperation | null>(null);
  const {
    workspaceId,
    kind,
    resourceId,
    label,
    role,
    ownedConversation,
    status,
    isActive,
    jobKind,
    compact,
    onRename,
    onDeleted,
  } = props;
  const choices: LifecycleOperation[] =
    status === "archived" || status === "deleted"
      ? ["restore", ...(status === "archived" ? ["delete" as const] : [])]
      : kind === "job"
        ? ["cancel"]
        : kind === "index"
          ? ["cleanup"]
          : kind === "assistant"
            ? [isActive === false ? "resume" : "pause", "archive", "delete"]
            : ["archive", "delete"];
  const allowed = choices.filter((action) =>
    canLifecycleAction(role, kind, action, {
      ownedConversation,
      deleted: status === "deleted",
      turn: jobKind === "turn",
    }),
  );
  if (!allowed.length && !onRename) return null;
  const icons = {
    archive: Archive,
    delete: Trash2,
    restore: RotateCcw,
    pause: Pause,
    resume: Play,
    cancel: XCircle,
    cleanup: Trash2,
    replace: RotateCcw,
  };
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            size={compact ? "icon" : "sm"}
            variant={compact ? "ghost" : "outline"}
            aria-label={`Thao tác vòng đời: ${label}`}
            className={compact ? "size-7 shrink-0" : "gap-1.5"}
          >
            <MoreHorizontal className="size-3.5" />
            {!compact && "Quản lý"}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {onRename && (
            <>
              <DropdownMenuItem onSelect={onRename}>
                <Pencil className="size-4" />
                Đổi tên
              </DropdownMenuItem>
              {allowed.length > 0 && <DropdownMenuSeparator />}
            </>
          )}
          {allowed.map((action) => {
            const Icon = icons[action];
            return (
              <DropdownMenuItem
                key={action}
                onSelect={() => setSelected(action)}
                className={action === "delete" ? "text-destructive" : undefined}
              >
                <Icon className="size-4" />
                {ACTION_LABEL[action]}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
      {selected ? (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          label={label}
          target={{
            kind,
            resource_id: resourceId,
            action: selected,
            ...(jobKind ? { job_kind: jobKind } : {}),
          }}
          onClose={() => setSelected(null)}
          onCompleted={(action) => {
            setSelected(null);
            if (action.action === "delete") onDeleted?.();
          }}
        />
      ) : null}
    </>
  );
}

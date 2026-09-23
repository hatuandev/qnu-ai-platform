import { useRouter } from "@tanstack/react-router";
import { ShieldCheck, UserPlus, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useRbac } from "@/rbac/context";

export function QuickCreateMenu() {
  const router = useRouter();
  const { can } = useRbac();
  const canInvite = can("users.create");
  const canCreateRole = can("roles.create");
  if (!canInvite && !canCreateRole) return null;

  const trigger = (
    <DropdownMenuTrigger asChild>
      <Button
        variant="ghost"
        size="icon"
        className="lg:h-[var(--control-height)] lg:w-auto lg:px-3"
        aria-label="Tạo nhanh"
      >
        <Zap />
        <span className="hidden lg:inline">Tạo nhanh</span>
      </Button>
    </DropdownMenuTrigger>
  );

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>{trigger}</TooltipTrigger>
        <TooltipContent>Tạo nhanh</TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-56">
        {canInvite ? (
          <DropdownMenuItem
            onSelect={() =>
              void router.navigate({
                to: "/users",
                search: {
                  q: "",
                  roles: "",
                  statuses: "",
                  create: true,
                  page: 1,
                  pageSize: 10,
                  sort: "createdAt.desc",
                },
              })
            }
          >
            <UserPlus />
            Mời người dùng
          </DropdownMenuItem>
        ) : null}
        {canCreateRole ? (
          <DropdownMenuItem
            onSelect={() =>
              void router.navigate({
                to: "/roles",
                search: {
                  q: "",
                  create: true,
                  type: "",
                  status: "",
                  page: 1,
                  pageSize: 10,
                  sort: "name.asc",
                },
              })
            }
          >
            <ShieldCheck />
            Tạo vai trò
          </DropdownMenuItem>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

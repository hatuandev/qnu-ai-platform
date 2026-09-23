import { useRouter } from "@tanstack/react-router";
import {
  Activity,
  Bell,
  Compass,
  HelpCircle,
  KeyRound,
  LineChart,
  LogOut,
  Moon,
  PenLine,
  Settings2,
  ShieldCheck,
  ShieldPlus,
  Sparkles,
  Sun,
  UserPlus,
  UserRound,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/app/auth";
import { useTheme } from "@/app/theme-provider";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { navigationGroups } from "@/navigation/config";
import type { NavGroup, NavItem } from "@/navigation/types";
import { filterNavigationGroups } from "@/navigation/utils";
import { useRbac } from "@/rbac/context";

type CommandNavItem = NavItem & {
  groupLabel: string;
  searchLabel: string;
};

function flattenGroup(group: NavGroup): CommandNavItem[] {
  return group.items.flatMap((item) => {
    const own: CommandNavItem[] = item.to
      ? [
          {
            ...item,
            groupLabel: group.label,
            searchLabel: `${group.label} ${item.title}`,
          },
        ]
      : [];
    const children: CommandNavItem[] =
      item.children?.flatMap((child) =>
        child.to
          ? [
              {
                ...child,
                groupLabel: group.label,
                searchLabel: `${group.label} ${item.title} ${child.title}`,
              },
            ]
          : [],
      ) ?? [];
    return [...own, ...children];
  });
}

function getIconContainerClass(category: string): string {
  switch (category) {
    case "quick-theme":
      return "bg-amber-500/10 text-amber-600 dark:text-amber-400 group-data-[selected=true]:bg-amber-500 group-data-[selected=true]:text-white";
    case "quick-user":
      return "bg-blue-500/10 text-blue-600 dark:text-blue-400 group-data-[selected=true]:bg-blue-600 group-data-[selected=true]:text-white";
    case "quick-role":
      return "bg-purple-500/10 text-purple-600 dark:text-purple-400 group-data-[selected=true]:bg-purple-600 group-data-[selected=true]:text-white";
    case "quick-reg":
      return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-data-[selected=true]:bg-emerald-600 group-data-[selected=true]:text-white";
    case "quick-noti":
      return "bg-rose-500/10 text-rose-600 dark:text-rose-400 group-data-[selected=true]:bg-rose-600 group-data-[selected=true]:text-white";
    case "overview":
      return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-data-[selected=true]:bg-emerald-600 group-data-[selected=true]:text-white";
    case "ai_builder":
      return "bg-purple-500/10 text-purple-600 dark:text-purple-400 group-data-[selected=true]:bg-purple-600 group-data-[selected=true]:text-white";
    case "operations":
      return "bg-blue-500/10 text-blue-600 dark:text-blue-400 group-data-[selected=true]:bg-blue-600 group-data-[selected=true]:text-white";
    case "advanced":
      return "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 group-data-[selected=true]:bg-indigo-600 group-data-[selected=true]:text-white";
    case "system":
      return "bg-slate-500/10 text-slate-600 dark:text-slate-400 group-data-[selected=true]:bg-slate-700 group-data-[selected=true]:text-white";
    default:
      return "bg-muted text-muted-foreground group-data-[selected=true]:bg-primary group-data-[selected=true]:text-primary-foreground";
  }
}

export function CommandMenu({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const { isDemoMode, signOut, user } = useAuth();
  const { can, isAccessVerified } = useRbac();

  const permissionChecker = isAccessVerified
    ? can
    : (permission?: string) => permission === undefined;

  const filteredGroups = filterNavigationGroups(
    navigationGroups,
    permissionChecker,
    user?.userType,
  ).map((group) => ({
    ...group,
    flattenedItems: flattenGroup(group),
  }));

  const canReadUsers = can("users.read");
  const canCreateUser = can("users.create");
  const canReadRoles = can("roles.read");
  const canCreateRole = can("roles.create");
  const canReadPermissions = can("permissions.read");
  const canReadProfile = true;
  const canReadSettings = can("settings.read");
  const canSubmitApp = can("ktx.applications.submit");
  const canViewNotifications = can("ktx.notifications.view");

  const hasManagement =
    canReadUsers || canCreateUser || canReadRoles || canReadPermissions;

  const navigateTo = (to: string, search?: Record<string, unknown>) => {
    onOpenChange(false);
    void router.navigate({
      to: to as never,
      search: search as never,
    });
  };

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Tìm kiếm trang và thao tác"
    >
      <CommandInput placeholder="Tìm kiếm trang, tính năng hoặc thao tác... (Ctrl + K)" />
      <CommandList>
        <CommandEmpty>
          <div className="flex flex-col items-center justify-center gap-2 py-6">
            <Compass className="size-9 text-muted-foreground/40" />
            <p className="font-medium text-foreground text-sm">
              Không tìm thấy kết quả phù hợp
            </p>
            <p className="text-xs text-muted-foreground">
              Thử tìm: phòng, tòa nhà, hóa đơn, sinh viên, người dùng...
            </p>
          </div>
        </CommandEmpty>

        {/* 1. Thao tác nhanh */}
        <CommandGroup heading="Thao tác nhanh">
          <CommandItem
            value="chuyển đổi giao diện sáng tối dark light mode theme"
            onSelect={() => {
              setTheme(resolvedTheme === "dark" ? "light" : "dark");
              onOpenChange(false);
              toast.success(
                resolvedTheme === "dark"
                  ? "Đã chuyển sang giao diện sáng"
                  : "Đã chuyển sang giao diện tối",
              );
            }}
          >
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                "quick-theme",
              )}`}
            >
              {resolvedTheme === "dark" ? (
                <Sun className="size-4.5" />
              ) : (
                <Moon className="size-4.5" />
              )}
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate font-medium text-sm text-foreground">
                {resolvedTheme === "dark"
                  ? "Chuyển sang giao diện Sáng"
                  : "Chuyển sang giao diện Tối"}
              </span>
              <span className="truncate text-xs text-muted-foreground/75">
                Giao diện hệ thống
              </span>
            </div>
            <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
              <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                ↵
              </kbd>
            </div>
          </CommandItem>

          {canCreateUser ? (
            <CommandItem
              value="mời người dùng mới invite create user tài khoản"
              onSelect={() =>
                navigateTo("/users", {
                  q: "",
                  roles: "",
                  statuses: "",
                  create: true,
                  page: 1,
                  pageSize: 10,
                  sort: "createdAt.desc",
                })
              }
            >
              <span
                className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                  "quick-user",
                )}`}
              >
                <UserPlus className="size-4.5" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate font-medium text-sm text-foreground">
                  Mời người dùng mới
                </span>
                <span className="truncate text-xs text-muted-foreground/75">
                  Thêm thành viên vào hệ thống
                </span>
              </div>
              <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                  ↵
                </kbd>
              </div>
            </CommandItem>
          ) : null}

          {canCreateRole ? (
            <CommandItem
              value="tạo vai trò mới create role phân quyền"
              onSelect={() =>
                navigateTo("/roles", {
                  q: "",
                  create: true,
                  type: "",
                  status: "",
                  page: 1,
                  pageSize: 10,
                  sort: "name.asc",
                })
              }
            >
              <span
                className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                  "quick-role",
                )}`}
              >
                <ShieldPlus className="size-4.5" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate font-medium text-sm text-foreground">
                  Tạo vai trò mới
                </span>
                <span className="truncate text-xs text-muted-foreground/75">
                  Thiết lập vai trò & phân quyền
                </span>
              </div>
              <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                  ↵
                </kbd>
              </div>
            </CommandItem>
          ) : null}

          {canSubmitApp ? (
            <CommandItem
              value="đăng ký phòng ký túc xá student register room ktx"
              onSelect={() => navigateTo("/student/register")}
            >
              <span
                className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                  "quick-reg",
                )}`}
              >
                <PenLine className="size-4.5" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate font-medium text-sm text-foreground">
                  Đăng ký phòng ký túc xá
                </span>
                <span className="truncate text-xs text-muted-foreground/75">
                  Gửi hồ sơ đăng ký phòng trực tuyến
                </span>
              </div>
              <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                  ↵
                </kbd>
              </div>
            </CommandItem>
          ) : null}

          {canViewNotifications ? (
            <CommandItem
              value="xem thông báo notifications tin tức tin nhắn"
              onSelect={() => navigateTo("/notifications")}
            >
              <span
                className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                  "quick-noti",
                )}`}
              >
                <Bell className="size-4.5" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate font-medium text-sm text-foreground">
                  Xem thông báo hệ thống
                </span>
                <span className="truncate text-xs text-muted-foreground/75">
                  Cập nhật tin tức & thông báo KTX
                </span>
              </div>
              <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                  ↵
                </kbd>
              </div>
            </CommandItem>
          ) : null}
        </CommandGroup>

        <CommandSeparator />

        {/* 2. Toàn bộ các phân hệ Nghiệp vụ KTX từ Thanh điều hướng */}
        {filteredGroups.map((group) => (
          <CommandGroup key={group.id} heading={group.label}>
            {group.flattenedItems.map((item) => {
              const Icon = item.icon ?? Compass;
              return (
                <CommandItem
                  key={item.id}
                  value={`${item.title} ${item.searchLabel} ${item.to ?? ""} ${group.label}`}
                  onSelect={() => {
                    if (item.to) navigateTo(item.to);
                  }}
                >
                  <span
                    className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                      group.id,
                    )}`}
                  >
                    <Icon className="size-4.5 shrink-0" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate font-medium text-sm text-foreground">
                      {item.title}
                    </span>
                    <span className="truncate text-xs text-muted-foreground/75">
                      Ký túc xá / {group.label}
                    </span>
                  </div>
                  <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                    <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                      ↵
                    </kbd>
                  </div>
                </CommandItem>
              );
            })}
          </CommandGroup>
        ))}

        {/* 3. Quản trị & Phân quyền (RBAC) */}
        {hasManagement ? (
          <>
            <CommandSeparator />
            <CommandGroup heading="Quản trị & Phân quyền">
              {canReadUsers ? (
                <CommandItem
                  value="quản lý người dùng danh sách users accounts tài khoản"
                  onSelect={() => navigateTo("/users")}
                >
                  <span
                    className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                      "management",
                    )}`}
                  >
                    <Users className="size-4.5" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate font-medium text-sm text-foreground">
                      Quản lý người dùng
                    </span>
                    <span className="truncate text-xs text-muted-foreground/75">
                      Quản trị / Danh sách tài khoản người dùng
                    </span>
                  </div>
                  <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                    <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                      ↵
                    </kbd>
                  </div>
                </CommandItem>
              ) : null}

              {canCreateUser ? (
                <CommandItem
                  value="lời mời người dùng invitations invite pending"
                  onSelect={() => navigateTo("/users/invitations")}
                >
                  <span
                    className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                      "management",
                    )}`}
                  >
                    <UserPlus className="size-4.5" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate font-medium text-sm text-foreground">
                      Lời mời người dùng
                    </span>
                    <span className="truncate text-xs text-muted-foreground/75">
                      Quản trị / Quản lý danh sách lời mời
                    </span>
                  </div>
                  <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                    <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                      ↵
                    </kbd>
                  </div>
                </CommandItem>
              ) : null}

              {canReadRoles ? (
                <CommandItem
                  value="quản lý vai trò roles quyền hạn permission"
                  onSelect={() => navigateTo("/roles")}
                >
                  <span
                    className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                      "management",
                    )}`}
                  >
                    <ShieldCheck className="size-4.5" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate font-medium text-sm text-foreground">
                      Quản lý vai trò
                    </span>
                    <span className="truncate text-xs text-muted-foreground/75">
                      Quản trị / Vai trò & nhóm quyền
                    </span>
                  </div>
                  <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                    <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                      ↵
                    </kbd>
                  </div>
                </CommandItem>
              ) : null}

              {canReadPermissions ? (
                <CommandItem
                  value="danh mục quyền hạn permissions rbac catalog"
                  onSelect={() => navigateTo("/permissions")}
                >
                  <span
                    className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                      "management",
                    )}`}
                  >
                    <KeyRound className="size-4.5" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate font-medium text-sm text-foreground">
                      Danh mục quyền hạn
                    </span>
                    <span className="truncate text-xs text-muted-foreground/75">
                      Quản trị / Bảng phân quyền RBAC
                    </span>
                  </div>
                  <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                    <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                      ↵
                    </kbd>
                  </div>
                </CommandItem>
              ) : null}
            </CommandGroup>
          </>
        ) : null}

        {/* 4. Cài đặt & Hệ thống */}
        <CommandSeparator />
        <CommandGroup heading="Cài đặt & Hệ thống">
          {canReadProfile ? (
            <CommandItem
              value="hồ sơ cá nhân profile account thông tin cá nhân"
              onSelect={() => navigateTo("/profile")}
            >
              <span
                className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                  "system",
                )}`}
              >
                <UserRound className="size-4.5" />
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate font-medium text-sm text-foreground">
                  Hồ sơ cá nhân
                </span>
                <span className="truncate text-xs text-muted-foreground/75">
                  Tài khoản / Thông tin cá nhân
                </span>
              </div>
              <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                  ↵
                </kbd>
              </div>
            </CommandItem>
          ) : null}

          {canReadSettings ? (
            <>
              <CommandItem
                value="cài đặt không gian làm việc settings cấu hình"
                onSelect={() => navigateTo("/settings")}
              >
                <span
                  className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                    "system",
                  )}`}
                >
                  <Settings2 className="size-4.5" />
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="truncate font-medium text-sm text-foreground">
                    Cài đặt không gian
                  </span>
                  <span className="truncate text-xs text-muted-foreground/75">
                    Cấu hình / Tùy chọn không gian làm việc
                  </span>
                </div>
                <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                  <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                    ↵
                  </kbd>
                </div>
              </CommandItem>

              <CommandItem
                value="cài đặt thông báo settings notifications chuông"
                onSelect={() => navigateTo("/settings/notifications")}
              >
                <span
                  className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                    "system",
                  )}`}
                >
                  <Bell className="size-4.5" />
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="truncate font-medium text-sm text-foreground">
                    Cài đặt thông báo
                  </span>
                  <span className="truncate text-xs text-muted-foreground/75">
                    Cấu hình / Kênh & tần suất thông báo
                  </span>
                </div>
                <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                  <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                    ↵
                  </kbd>
                </div>
              </CommandItem>

              <CommandItem
                value="cài đặt bảo mật security mật khẩu 2fa phiên đăng nhập"
                onSelect={() => navigateTo("/settings/security")}
              >
                <span
                  className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                    "system",
                  )}`}
                >
                  <ShieldCheck className="size-4.5" />
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="truncate font-medium text-sm text-foreground">
                    Cài đặt bảo mật
                  </span>
                  <span className="truncate text-xs text-muted-foreground/75">
                    Cấu hình / Bảo mật & phiên đăng nhập
                  </span>
                </div>
                <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
                  <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                    ↵
                  </kbd>
                </div>
              </CommandItem>
            </>
          ) : null}

          <CommandItem
            value="nhật ký hoạt động activity logs lịch sử thao tác"
            onSelect={() => navigateTo("/activity")}
          >
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                "system",
              )}`}
            >
              <Activity className="size-4.5" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate font-medium text-sm text-foreground">
                Nhật ký hoạt động
              </span>
              <span className="truncate text-xs text-muted-foreground/75">
                Hệ thống / Lịch sử sự kiện & thao tác
              </span>
            </div>
            <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
              <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                ↵
              </kbd>
            </div>
          </CommandItem>

          <CommandItem
            value="phân tích hệ thống analytics thống kê biểu đồ"
            onSelect={() => navigateTo("/analytics")}
          >
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                "system",
              )}`}
            >
              <LineChart className="size-4.5" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate font-medium text-sm text-foreground">
                Phân tích hệ thống
              </span>
              <span className="truncate text-xs text-muted-foreground/75">
                Hệ thống / Chỉ số & biểu đồ phân tích
              </span>
            </div>
            <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
              <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                ↵
              </kbd>
            </div>
          </CommandItem>

          <CommandItem
            value="hệ thống thiết kế design system components UI mẫu"
            onSelect={() => navigateTo("/design-system")}
          >
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                "system",
              )}`}
            >
              <Sparkles className="size-4.5" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate font-medium text-sm text-foreground">
                Hệ thống thiết kế
              </span>
              <span className="truncate text-xs text-muted-foreground/75">
                Tài liệu / Thư viện thành phần UI
              </span>
            </div>
            <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
              <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                ↵
              </kbd>
            </div>
          </CommandItem>

          <CommandItem
            value="trợ giúp hướng dẫn help docs tài liệu"
            onSelect={() => navigateTo("/help")}
          >
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-all duration-150 ${getIconContainerClass(
                "system",
              )}`}
            >
              <HelpCircle className="size-4.5" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate font-medium text-sm text-foreground">
                Trợ giúp & Tài liệu
              </span>
              <span className="truncate text-xs text-muted-foreground/75">
                Hỗ trợ / Hướng dẫn sử dụng hệ thống
              </span>
            </div>
            <div className="ml-auto hidden sm:flex items-center text-xs text-primary font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
              <kbd className="inline-flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/10 font-mono text-[11px] text-primary shadow-xs">
                ↵
              </kbd>
            </div>
          </CommandItem>
        </CommandGroup>

        {/* 5. Đăng xuất */}
        <CommandSeparator />
        <CommandGroup heading="Tài khoản">
          <CommandItem
            value="đăng xuất logout sign out thoát tài khoản"
            onSelect={() => {
              onOpenChange(false);
              if (isDemoMode) {
                toast.info("Đăng xuất sẽ được kết nối khi tích hợp xác thực.");
                return;
              }
              signOut();
            }}
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive transition-all duration-150 group-data-[selected=true]:bg-destructive group-data-[selected=true]:text-destructive-foreground">
              <LogOut className="size-4.5" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate font-medium text-sm text-destructive">
                Đăng xuất tài khoản
              </span>
              <span className="truncate text-xs text-muted-foreground/75">
                {user?.name
                  ? `Tài khoản: ${user.name}`
                  : "Thoát phiên làm việc"}
              </span>
            </div>
            <div className="ml-auto hidden sm:flex items-center text-xs text-destructive font-medium opacity-0 group-data-[selected=true]:opacity-100 transition-opacity">
              <kbd className="inline-flex size-5 items-center justify-center rounded border border-destructive/30 bg-destructive/10 font-mono text-[11px]">
                ↵
              </kbd>
            </div>
          </CommandItem>
        </CommandGroup>
      </CommandList>

      {/* Footer bar */}
      <div className="flex items-center justify-between border-t border-border/70 bg-muted/30 px-3.5 sm:px-4 py-2.5 text-xs text-muted-foreground shrink-0">
        <div className="flex items-center gap-3">
          <span className="hidden sm:flex items-center gap-1">
            <kbd className="inline-flex h-4.5 min-w-4.5 items-center justify-center rounded border border-border/70 bg-background px-1 font-mono text-[10px] text-foreground/80 shadow-xs">
              ↑
            </kbd>
            <kbd className="inline-flex h-4.5 min-w-4.5 items-center justify-center rounded border border-border/70 bg-background px-1 font-mono text-[10px] text-foreground/80 shadow-xs">
              ↓
            </kbd>
            <span className="ml-0.5">Di chuyển</span>
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <kbd className="inline-flex h-4.5 min-w-4.5 items-center justify-center rounded border border-border/70 bg-background px-1 font-mono text-[10px] text-foreground/80 shadow-xs">
              ↵
            </kbd>
            <span className="ml-0.5">Chọn</span>
          </span>
          <span className="flex items-center gap-1">
            <kbd className="inline-flex h-4.5 min-w-4.5 items-center justify-center rounded border border-border/70 bg-background px-1.5 font-mono text-[10px] text-foreground/80 shadow-xs">
              ESC
            </kbd>
            <span className="ml-0.5">Đóng</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5 font-medium text-xs text-muted-foreground/70">
          <Sparkles className="size-3.5 text-primary" />
          <span>QNU KTX</span>
        </div>
      </div>
    </CommandDialog>
  );
}

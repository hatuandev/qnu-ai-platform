import { useRouter, useRouterState } from "@tanstack/react-router";
import {
  Bell,
  HelpCircle,
  Keyboard,
  Laptop,
  LogOut,
  Moon,
  Sparkles,
  Sun,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { isV1Route } from "@/app/api/v1/endpoints";
import { useAuth } from "@/app/auth";
import { hasV1Permission, useV1Auth } from "@/app/auth/v1";
import { useTheme } from "@/app/theme-provider";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from "@/components/ui/dropdown-menu";
import { StudentUserGuide } from "@/features/student/student-user-guide";
import { usePlatformShortcut } from "@/hooks/use-platform-shortcut";
import { isStudentAccount } from "@/rbac/backend-role-map";
import { useRbac } from "@/rbac/context";

const roleDisplayMap: Record<string, string> = {
  admin: "Quản trị viên KTX",
  manager: "Quản lý ký túc xá",
  staff: "Cán bộ quản lý",
  student: "Sinh viên",
};

export function AccountMenuContent({
  side = "bottom",
  align = "end",
  onNavigate,
}: {
  side?: "top" | "right" | "bottom" | "left";
  align?: "start" | "center" | "end";
  onNavigate?: () => void;
}) {
  const router = useRouter();
  const { isDemoMode, signOut, user } = useAuth();
  const v1 = useV1Auth();
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const isQnuV1 = isV1Route(pathname);
  const { roleKey, roles, setRoleKey } = useRbac();
  const { theme, setTheme } = useTheme();
  const shortcut = usePlatformShortcut();

  const [confirmSignOutOpen, setConfirmSignOutOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const isStudent = roleKey === "student" || isStudentAccount(user?.userType);
  const ktxDisplayName = user?.name || (isStudent ? "Sinh viên" : "Cán bộ KTX");
  const ktxDisplayEmail =
    user?.email ||
    (isStudent ? "student@st.qnu.edu.vn" : "ktx.manager@qnu.edu.vn");
  const ktxRoleName =
    roleDisplayMap[roleKey] ??
    roles.find((r) => r.key === roleKey)?.name ??
    (isStudent ? "Sinh viên" : "Cán bộ KTX");

  // v1 identity comes from GET /auth/me; it is never inferred from the demo role.
  const v1RoleName = isQnuV1
    ? hasV1Permission(v1.actor, "ai.workspaces.manage")
      ? "Quản trị nền tảng"
      : hasV1Permission(v1.actor, "ai.models.manage")
        ? "Quản trị model"
        : (v1.actor?.roles?.[0] ?? "Người dùng v1")
    : "";

  const displayName = isQnuV1
    ? (v1.actor?.display_name ?? "Chưa đăng nhập v1")
    : ktxDisplayName;
  const displayEmail = isQnuV1
    ? (v1.actor?.email ?? v1.actor?.actor_id ?? "Phiên v1 chưa xác thực")
    : ktxDisplayEmail;
  const roleName = isQnuV1 ? v1RoleName : ktxRoleName;

  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <>
      <DropdownMenuContent
        side={side}
        align={align}
        className="w-72 p-1.5 shadow-lg rounded-xl"
      >
        {/* 1. User Header & Role Badge */}
        <DropdownMenuLabel className="p-2.5 pb-2">
          <div className="flex items-start gap-3">
            <Avatar className="size-10 shrink-0 border border-primary/20 bg-primary/10">
              <AvatarFallback className="font-semibold text-primary">
                {initials || (isStudent ? "SV" : "CB")}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1 space-y-1">
              <p className="truncate text-sm font-semibold text-foreground leading-none">
                {displayName}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {displayEmail}
              </p>
              <div className="flex items-center gap-1.5 pt-0.5">
                <Badge
                  variant="outline"
                  className="gap-1 px-2 py-0.5 text-[10px] font-semibold text-primary border-primary/30 bg-primary/5 rounded-full"
                >
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  {roleName}
                </Badge>
              </div>
            </div>
          </div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        {/* 2. Account Actions — KTX template routes only */}
        {isQnuV1 ? null : (
          <>
            <DropdownMenuItem
              className="gap-2 text-xs py-2 cursor-pointer"
              onSelect={() => {
                onNavigate?.();
                void router.navigate({ to: "/profile" });
              }}
            >
              <UserRound className="size-4 text-muted-foreground" />
              <span>Thông tin cá nhân & Tài khoản</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              className="gap-2 text-xs py-2 cursor-pointer"
              onSelect={() => {
                onNavigate?.();
                void router.navigate({
                  to: "/notifications",
                  search: { q: "", type: undefined, page: 1, pageSize: 10 },
                });
              }}
            >
              <Bell className="size-4 text-muted-foreground" />
              <span>
                {isStudent ? "Thông báo của tôi" : "Thông báo & Công việc"}
              </span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />
          </>
        )}

        {/* 3. Quick Theme Submenu */}
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="gap-2 text-xs py-2 cursor-pointer">
            {theme === "dark" ? (
              <Moon className="size-4 text-muted-foreground" />
            ) : theme === "light" ? (
              <Sun className="size-4 text-muted-foreground" />
            ) : (
              <Laptop className="size-4 text-muted-foreground" />
            )}
            <span>
              Giao diện:{" "}
              {theme === "dark"
                ? "Tối"
                : theme === "light"
                  ? "Sáng"
                  : "Hệ thống"}
            </span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent className="w-40 rounded-lg">
            <DropdownMenuRadioGroup
              value={theme}
              onValueChange={(val) =>
                setTheme(val as "light" | "dark" | "system")
              }
            >
              <DropdownMenuRadioItem value="light" className="gap-2 text-xs">
                <Sun className="size-3.5" />
                <span>Giao diện sáng</span>
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="dark" className="gap-2 text-xs">
                <Moon className="size-3.5" />
                <span>Giao diện tối</span>
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="system" className="gap-2 text-xs">
                <Laptop className="size-3.5" />
                <span>Theo hệ thống</span>
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>

        {/* 4. Help & Shortcuts */}
        <DropdownMenuItem
          className="gap-2 text-xs py-2 cursor-pointer"
          onSelect={() => {
            onNavigate?.();
            setShortcutsOpen(true);
          }}
        >
          <Keyboard className="size-4 text-muted-foreground" />
          <div className="flex flex-1 items-center justify-between">
            <span>Bảng phím tắt</span>
            <kbd className="font-mono text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded border">
              {shortcut}
            </kbd>
          </div>
        </DropdownMenuItem>

        <DropdownMenuItem
          className="gap-2 text-xs py-2 cursor-pointer"
          onSelect={() => {
            onNavigate?.();
            setHelpOpen(true);
          }}
        >
          <HelpCircle className="size-4 text-muted-foreground" />
          <span>Hướng dẫn sử dụng</span>
        </DropdownMenuItem>

        {/* 5. Demo Role Switcher (KTX template only — never a v1 permission) */}
        {isDemoMode && !isQnuV1 ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className="gap-2 text-xs py-2 cursor-pointer text-amber-600 dark:text-amber-400">
                <Sparkles className="size-4" />
                <span>Chuyển vai trò thử nghiệm</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className="w-52 rounded-lg">
                <DropdownMenuRadioGroup
                  value={roleKey}
                  onValueChange={setRoleKey}
                >
                  {roles.map((role) => (
                    <DropdownMenuRadioItem
                      key={role.key}
                      value={role.key}
                      className="text-xs"
                    >
                      {role.name}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuRadioGroup>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </>
        ) : null}

        <DropdownMenuSeparator />

        {/* 6. System Version Footer */}
        <div className="px-2.5 py-1 text-[10px] text-muted-foreground flex items-center justify-between">
          <span>{isQnuV1 ? "QNU AI Platform" : "QNU-KTX System"}</span>
          <span className="font-mono">{isQnuV1 ? "v1alpha1" : "v1.0.1"}</span>
        </div>

        <DropdownMenuSeparator />

        {/* 7. Sign Out Button */}
        <DropdownMenuItem
          variant="destructive"
          className="gap-2 text-xs py-2 cursor-pointer"
          onSelect={(event) => {
            event.preventDefault();
            setConfirmSignOutOpen(true);
          }}
        >
          <LogOut className="size-4" />
          <span>Đăng xuất</span>
        </DropdownMenuItem>
      </DropdownMenuContent>

      {/* Dialog xác nhận Đăng xuất */}
      <ConfirmDialog
        open={confirmSignOutOpen}
        onOpenChange={setConfirmSignOutOpen}
        title="Xác nhận đăng xuất?"
        description={
          isQnuV1
            ? "Token và actor v1 sẽ bị xóa khỏi bộ nhớ tab này, cùng toàn bộ cache dữ liệu v1. BackendV1 chưa có API thu hồi JWT, nên token vẫn hợp lệ tới khi hết hạn (8 giờ) ở phía server."
            : "Bạn có chắc chắn muốn đăng xuất khỏi hệ thống Quản lý Ký túc xá Đại học Quy Nhơn?"
        }
        confirmLabel="Đăng xuất"
        confirmVariant="destructive"
        onConfirm={() => {
          setConfirmSignOutOpen(false);
          if (isQnuV1) {
            void v1.signOut().then(() => {
              toast.success("Đã đăng xuất phiên v1 trên tab này.");
            });
            return;
          }
          if (isDemoMode) {
            toast.info("Đã đăng xuất khỏi chế độ thử nghiệm.");
            return;
          }
          signOut();
        }}
      />

      {/* Dialog Hướng dẫn phím tắt */}
      <ResponsiveDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen}>
        <ResponsiveDialogContent className="max-w-md">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle className="flex items-center gap-2">
              <Keyboard className="size-5 text-primary" />
              <span>Phím tắt hệ thống</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              Các tổ hợp phím giúp bạn thao tác nhanh chóng và hiệu quả hơn.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="grid gap-2.5 py-3 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/40 border">
              <span className="font-medium text-foreground">
                Mở tìm kiếm nhanh
              </span>
              <kbd className="font-mono text-xs bg-background px-2 py-1 rounded border shadow-xs">
                {shortcut}
              </kbd>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/40 border">
              <span className="font-medium text-foreground">
                Đóng hộp thoại / Popup
              </span>
              <kbd className="font-mono text-xs bg-background px-2 py-1 rounded border shadow-xs">
                Esc
              </kbd>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/40 border">
              <span className="font-medium text-foreground">
                Lưu form dữ liệu nhanh
              </span>
              <kbd className="font-mono text-xs bg-background px-2 py-1 rounded border shadow-xs">
                Ctrl + Enter
              </kbd>
            </div>
          </div>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Dialog Hướng dẫn sử dụng nhanh */}
      <ResponsiveDialog open={helpOpen} onOpenChange={setHelpOpen}>
        <ResponsiveDialogContent className="flex max-h-[min(760px,calc(100dvh-1rem))] max-w-xl flex-col overflow-hidden">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle className="flex items-center gap-2">
              <HelpCircle className="size-5 text-primary" />
              <span>Hướng dẫn sử dụng</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              {isStudent
                ? "Các bước sử dụng hệ thống dành cho tài khoản sinh viên."
                : "Hướng dẫn nhanh dành cho tài khoản quản trị."}
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-0.5 py-2">
            {isStudent ? (
              <StudentUserGuide />
            ) : (
              <div className="space-y-2 text-xs">
                <div className="p-3 rounded-lg border bg-muted/20 space-y-1">
                  <p className="font-semibold text-foreground">
                    1. Thiết lập hệ thống
                  </p>
                  <p className="text-muted-foreground">
                    Quản lý tài khoản, phân quyền, năm học, đợt đăng ký và danh
                    mục phòng.
                  </p>
                </div>
                <div className="p-3 rounded-lg border bg-muted/20 space-y-1">
                  <p className="font-semibold text-foreground">
                    2. Xử lý hồ sơ
                  </p>
                  <p className="text-muted-foreground">
                    Tiếp nhận, yêu cầu bổ sung hoặc duyệt hồ sơ, sau đó xếp
                    phòng cho sinh viên.
                  </p>
                </div>
                <div className="p-3 rounded-lg border bg-muted/20 space-y-1">
                  <p className="font-semibold text-foreground">3. Thu phí</p>
                  <p className="text-muted-foreground">
                    Tạo hóa đơn, theo dõi công nợ và đối soát biên lai thanh
                    toán.
                  </p>
                </div>
                <div className="p-3 rounded-lg border bg-muted/20 space-y-1">
                  <p className="font-semibold text-foreground">4. Điều hành</p>
                  <p className="text-muted-foreground">
                    Gửi thông báo, xử lý yêu cầu hỗ trợ và xem báo cáo tổng hợp.
                  </p>
                </div>
              </div>
            )}
          </div>
        </ResponsiveDialogContent>
      </ResponsiveDialog>
    </>
  );
}

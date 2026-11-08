import { useRouter } from "@tanstack/react-router";
import {
  KeyRound,
  LayoutDashboard,
  LogOut,
  Moon,
  Server,
  Settings2,
} from "lucide-react";
import { hasV1Permission, useV1Auth } from "@/app/auth/v1";
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
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import {
  workspaceFeatureGroups,
  workspaceFeatureKeys,
  workspaceFeatures,
  workspacePrimaryFeatures,
} from "@/navigation/config";
import { useFeatureScope } from "@/navigation/use-feature-scope.tsx";
import { featureTarget } from "@/navigation/workspace-features";

export function QnuCommandMenu({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const scope = useFeatureScope();
  const auth = useV1Auth();
  const { resolvedTheme, setTheme } = useTheme();
  const role = useCallerWorkspaceRole(
    auth.isAuthenticated ? (scope.workspaceId ?? "") : "",
  );
  const primaryFeatures = workspacePrimaryFeatures(
    role.isPending ? undefined : role.role,
  );
  const canManageModels =
    auth.isAuthenticated && hasV1Permission(auth.actor, "ai.models.manage");

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Chuyển đến chức năng QNU AI"
    >
      <CommandInput placeholder="Tìm tài liệu, trợ lý, tác vụ hoặc cấu hình…" />
      <CommandList>
        <CommandEmpty>Không tìm thấy chức năng phù hợp.</CommandEmpty>
        {auth.isAuthenticated && (
          <CommandGroup heading="Điều hướng chính">
            <CommandItem
              value="Tổng quan dashboard"
              onSelect={() => {
                onOpenChange(false);
                void router.navigate({
                  to: "/dashboard",
                  search: { workspaceId: scope.workspaceId },
                });
              }}
            >
              <LayoutDashboard className="size-4" />
              Tổng quan
            </CommandItem>
            {primaryFeatures.map((key) => {
              const item = workspaceFeatures[key];
              const Icon = item.icon;
              return (
                <CommandItem
                  key={`primary-${key}`}
                  value={`${item.title} ${item.group}`}
                  onSelect={() => {
                    onOpenChange(false);
                    void router.navigate(featureTarget(key, scope));
                  }}
                >
                  <Icon className="size-4" />
                  {item.title}
                </CommandItem>
              );
            })}
            <CommandItem
              value="Cấu hình settings"
              onSelect={() => {
                onOpenChange(false);
                void router.navigate({ to: "/settings" });
              }}
            >
              <Settings2 className="size-4" />
              Cấu hình
            </CommandItem>
          </CommandGroup>
        )}
        {auth.isAuthenticated &&
          workspaceFeatureGroups.map((group) => {
            const subKeys = workspaceFeatureKeys.filter(
              (key) =>
                workspaceFeatures[key].group === group &&
                !primaryFeatures.includes(key),
            );
            if (subKeys.length === 0) return null;
            return (
              <CommandGroup key={group} heading={group}>
                {subKeys.map((key) => {
                  const item = workspaceFeatures[key];
                  const Icon = item.icon;
                  return (
                    <CommandItem
                      key={key}
                      value={`${group} ${item.title}`}
                      onSelect={() => {
                        onOpenChange(false);
                        void router.navigate(featureTarget(key, scope));
                      }}
                    >
                      <Icon className="size-4" />
                      {item.title}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            );
          })}
        {canManageModels && (
          <CommandGroup heading="Cấu hình nền tảng">
            <CommandItem
              value="Kết nối AI Nhà cung cấp ModelOps"
              onSelect={() => {
                onOpenChange(false);
                void router.navigate({
                  to: "/providers",
                  search: { page: 1, pageSize: 20 },
                });
              }}
            >
              <Server className="size-4" />
              Kết nối AI (Nhà cung cấp & Model)
            </CommandItem>
            <CommandItem
              value="API tích hợp API key ứng dụng bên ngoài"
              onSelect={() => {
                onOpenChange(false);
                void router.navigate({
                  to: "/modelops/endpoints",
                  search: { workspaceId: scope.workspaceId },
                });
              }}
            >
              <KeyRound className="size-4" />
              API tích hợp
            </CommandItem>
          </CommandGroup>
        )}
        <CommandSeparator />
        <CommandGroup heading="Tài khoản & giao diện">
          <CommandItem
            onSelect={() => {
              setTheme(resolvedTheme === "dark" ? "light" : "dark");
              onOpenChange(false);
            }}
          >
            <Moon className="size-4" />
            Đổi giao diện sáng/tối
          </CommandItem>
          <CommandItem
            onSelect={() => {
              onOpenChange(false);
              void auth.signOut();
            }}
          >
            <LogOut className="size-4" />
            Đăng xuất
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

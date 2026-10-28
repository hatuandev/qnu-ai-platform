import { useRouter } from "@tanstack/react-router";
import { LogOut, Moon } from "lucide-react";
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
import {
  navigationGroups,
  workspaceFeatureGroups,
  workspaceFeatureKeys,
  workspaceFeatures,
} from "@/navigation/config";
import { useFeatureScope } from "@/navigation/use-feature-scope.tsx";
import { filterNavigationGroups, flattenNavigation } from "@/navigation/utils";
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
  const globals = flattenNavigation(
    filterNavigationGroups(
      navigationGroups.filter((group) => !group.template),
      () => false,
      undefined,
      (permission) =>
        auth.isAuthenticated && hasV1Permission(auth.actor, permission),
    ),
  );
  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Chuyển đến chức năng QNU AI"
    >
      <CommandInput placeholder="Tìm workspace, tài liệu, trợ lý hoặc tác vụ…" />
      <CommandList>
        <CommandEmpty>Không tìm thấy chức năng phù hợp.</CommandEmpty>
        <CommandGroup heading="QNU AI">
          {globals.map(
            (item) =>
              item.to && (
                <CommandItem
                  key={item.id}
                  value={item.title}
                  onSelect={() => {
                    if (!item.to) return;
                    onOpenChange(false);
                    void router.navigate({
                      to: item.to,
                      search: { page: 1, pageSize: 20 },
                    });
                  }}
                >
                  {item.title}
                </CommandItem>
              ),
          )}
        </CommandGroup>
        {auth.isAuthenticated &&
          workspaceFeatureGroups.map((group) => (
            <CommandGroup key={group} heading={group}>
              {workspaceFeatureKeys
                .filter((key) => workspaceFeatures[key].group === group)
                .map((key) => {
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
          ))}
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

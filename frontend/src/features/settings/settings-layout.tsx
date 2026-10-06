import { Link, useRouter, useRouterState } from "@tanstack/react-router";
import { Settings2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const settingsItems = [
  { to: "/settings", label: "Chung" },
  { to: "/settings/notifications", label: "Thông báo" },
  { to: "/settings/security", label: "Bảo mật" },
] as const;

export function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const router = useRouter();
  const current =
    settingsItems.find((item) => item.to === pathname)?.to ?? "/settings";
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 border-b pb-3 lg:hidden">
        <Settings2 className="size-4 text-muted-foreground" />
        <Select
          value={current}
          onValueChange={(value) =>
            void router.navigate({
              to: value as
                | "/settings"
                | "/settings/notifications"
                | "/settings/security",
            })
          }
        >
          <SelectTrigger aria-label="Chọn mục cài đặt">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {settingsItems.map((item) => (
              <SelectItem key={item.to} value={item.to}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-8 lg:grid-cols-[180px_minmax(0,1fr)] lg:gap-10">
        <aside className="hidden lg:block">
          <nav
            aria-label="Điều hướng cài đặt"
            className="sticky top-20 space-y-1"
          >
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Cài đặt
            </p>
            {settingsItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                activeOptions={{ exact: item.to === "/settings" }}
                className="block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                activeProps={{ className: "bg-muted text-foreground" }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}

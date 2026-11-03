import { Link } from "@tanstack/react-router";
import {
  Archive,
  ArrowUpRight,
  Building2,
  Database,
  FileClock,
  Gauge,
  KeyRound,
  Settings2,
  ShieldCheck,
  Sliders,
  UsersRound,
} from "lucide-react";
import {
  hasV1Permission,
  isPlatformWorkspaceAdmin,
  useV1Auth,
} from "@/app/auth/v1";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useWorkspaceQuery,
  useWorkspacesQuery,
} from "@/features/workspaces/queries";
import { useFeatureScope } from "@/navigation/use-feature-scope";
import { featureTarget } from "@/navigation/workspace-features";

export function QnuSettingsHub() {
  const { actor, isAuthenticated } = useV1Auth();
  const scope = useFeatureScope();
  const workspacesQuery = useWorkspacesQuery(
    { page: 1, pageSize: 50 },
    isAuthenticated,
  );
  const activeWorkspaceId =
    scope.workspaceId ?? workspacesQuery.data?.items?.[0]?.id ?? "";
  const workspaceQuery = useWorkspaceQuery(activeWorkspaceId);
  const activeWorkspace =
    workspacesQuery.data?.items?.find((w) => w.id === activeWorkspaceId) ??
    workspaceQuery.data;

  const canManageModels =
    isAuthenticated && hasV1Permission(actor, "ai.models.manage");
  const isPlatformAdmin = isPlatformWorkspaceAdmin(actor);
  const targetScope = { workspaceId: activeWorkspaceId || undefined };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Cấu hình & Quản trị"
        title="Cấu hình hệ thống"
        description="Chọn nhóm chức năng để mở trang thiết lập chuyên biệt. Cấu hình được tách bạch rõ giữa phạm vi Đơn vị đang chọn và phạm vi Toàn nền tảng."
      />

      {/* Khu vực 1: Cấu hình của Đơn vị đang chọn */}
      <section aria-labelledby="unit-settings-heading" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2
                id="unit-settings-heading"
                className="text-base font-semibold text-foreground"
              >
                Cấu hình Đơn vị đang chọn
              </h2>
              <Badge variant="outline" className="font-medium">
                {activeWorkspace?.name ?? "Chưa chọn đơn vị"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Áp dụng trong phạm vi quyền của đơn vị hiện tại trên thanh đầu
              trang.
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {/* Nhóm: Đơn vị (Thành viên, Model được phép dùng, Mức sử dụng) */}
          <Card className="rounded-xl border-border/70 shadow-2xs flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <UsersRound className="size-4.5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Đơn vị & Phân quyền
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Thành viên, model được phép dùng và mức sử dụng
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-1.5 pt-0">
              <Link
                {...featureTarget("members", targetScope)}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <UsersRound className="size-3.5 text-muted-foreground" />
                  Thành viên & vai trò
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
              <Link
                {...featureTarget("models", targetScope)}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <Settings2 className="size-3.5 text-muted-foreground" />
                  Model được phép dùng
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
              <Link
                {...featureTarget("quota", targetScope)}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <Gauge className="size-3.5 text-muted-foreground" />
                  Mức sử dụng
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
            </CardContent>
          </Card>

          {/* Nhóm: API tích hợp */}
          <Card className="rounded-xl border-border/70 shadow-2xs flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <KeyRound className="size-4.5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    API tích hợp
                  </CardTitle>
                  <CardDescription className="text-xs">
                    API key cho ứng dụng bên ngoài kết nối vào đơn vị
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 pt-0">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Cấp phát và thu hồi khóa truy cập API có kiểm soát phạm vi model
                và hạn mức cho các hệ thống tích hợp bên ngoài.
              </p>
              <Link
                to="/modelops/endpoints"
                search={{ workspaceId: activeWorkspaceId || undefined }}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <KeyRound className="size-3.5 text-muted-foreground" />
                  Quản lý API key tích hợp
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
            </CardContent>
          </Card>

          {/* Nhóm: Nhật ký, Sao lưu & Dọn dữ liệu */}
          <Card className="rounded-xl border-border/70 shadow-2xs flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Archive className="size-4.5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Nhật ký & Bảo trì dữ liệu
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Nhật ký kiểm toán, sao lưu bằng chứng và dọn dữ liệu
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-1.5 pt-0">
              <Link
                {...featureTarget("audit", targetScope)}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <FileClock className="size-3.5 text-muted-foreground" />
                  Nhật ký hoạt động
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
              <Link
                {...featureTarget("backups", targetScope)}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <Archive className="size-3.5 text-muted-foreground" />
                  Sao lưu bằng chứng
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
              <Link
                {...featureTarget("storage", targetScope)}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <Database className="size-3.5 text-muted-foreground" />
                  Dọn dữ liệu dẫn xuất
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Khu vực 2: Cấu hình Toàn nền tảng */}
      <section
        aria-labelledby="platform-settings-heading"
        className="space-y-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2
                id="platform-settings-heading"
                className="text-base font-semibold text-foreground"
              >
                Cấu hình Toàn nền tảng
              </h2>
              <Badge variant="secondary" className="font-medium">
                Quản trị hệ thống
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Thiết lập model toàn cục, danh mục đơn vị và tùy chọn tài khoản.
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {canManageModels ? (
            <Card className="rounded-xl border-border/70 shadow-2xs">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2.5 text-sm font-semibold">
                  <Sliders className="size-4 text-primary" />
                  Model mặc định
                </CardTitle>
                <CardDescription className="text-xs">
                  Thiết lập model dùng chung toàn nền tảng.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <Link
                  to="/modelops/defaults"
                  className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
                >
                  Model mặc định hệ thống
                  <ArrowUpRight className="size-3.5 text-muted-foreground" />
                </Link>
              </CardContent>
            </Card>
          ) : null}
          {/* Nhóm: Quản lý danh sách Đơn vị */}
          {isPlatformAdmin ? (
            <Card className="rounded-xl border-border/70 shadow-2xs flex flex-col justify-between">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Building2 className="size-4.5" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-semibold">
                      Danh mục Đơn vị
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Khởi tạo và quản lý trạng thái các đơn vị trên nền tảng
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 pt-0">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Tạo đơn vị mới, cập nhật mã đơn vị hoặc tạm dừng hoạt động của
                  một đơn vị.
                </p>
                <Link
                  to="/workspaces"
                  search={{ page: 1, pageSize: 20 }}
                  className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
                >
                  <span className="flex items-center gap-2">
                    <Building2 className="size-3.5 text-muted-foreground" />
                    Mở danh sách Đơn vị
                  </span>
                  <ArrowUpRight className="size-3.5 text-muted-foreground" />
                </Link>
              </CardContent>
            </Card>
          ) : null}

          {/* Nhóm: Tài khoản & Bảo mật cá nhân */}
          <Card className="rounded-xl border-border/70 shadow-2xs flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <ShieldCheck className="size-4.5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Tài khoản & Thông báo
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Tùy chọn thông báo và bảo mật phiên đăng nhập
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-1.5 pt-0">
              <Link
                to="/settings/notifications"
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <Settings2 className="size-3.5 text-muted-foreground" />
                  Tùy chọn thông báo
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
              <Link
                to="/settings/security"
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <span className="flex items-center gap-2">
                  <ShieldCheck className="size-3.5 text-muted-foreground" />
                  Bảo mật tài khoản
                </span>
                <ArrowUpRight className="size-3.5 text-muted-foreground" />
              </Link>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

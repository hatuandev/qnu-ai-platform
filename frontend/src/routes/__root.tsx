import { createRootRoute, Outlet, useLocation } from "@tanstack/react-router";
import { AuthGate } from "@/app/auth/auth-gate";
import { AdminShell } from "@/layouts/admin-shell";

export const Route = createRootRoute({
  component: RootLayout,
  notFoundComponent: () => (
    <div className="py-12 text-center">
      <h1 className="type-section-title">Không tìm thấy trang</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Trang bạn yêu cầu không tồn tại.
      </p>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="py-12">
      <h1 className="type-section-title">Đã xảy ra lỗi</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {error instanceof Error ? error.message : String(error)}
      </p>
    </div>
  ),
});

function RootLayout() {
  const pathname = useLocation({ select: (location) => location.pathname });
  const isPublicRoute =
    pathname === "/" ||
    pathname === "/sign-in" ||
    pathname === "/signin-oidc" ||
    pathname === "/access-denied" ||
    pathname === "/chat" ||
    pathname.startsWith("/chat/");

  if (isPublicRoute) return <Outlet />;

  return (
    <AuthGate>
      <AdminShell>
        <Outlet />
      </AdminShell>
    </AuthGate>
  );
}

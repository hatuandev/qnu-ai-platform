import {
  createRootRoute,
  Outlet,
  useLocation,
  useNavigate,
} from "@tanstack/react-router";
import { useEffect } from "react";
import { isV1Route } from "@/app/api/v1/endpoints";
import { useAuth } from "@/app/auth";
import { AuthGate } from "@/app/auth/auth-gate";
import { V1SessionGate } from "@/app/auth/v1";
import { TemplateNotice } from "@/components/admin/template-notice";
import { AdminShell } from "@/layouts/admin-shell";
import { backendHomeRoute } from "@/rbac/backend-role-map";

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
      <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
    </div>
  ),
});

function RootLayout() {
  const pathname = useLocation({ select: (location) => location.pathname });
  const navigate = useNavigate();
  const { user } = useAuth();
  const isPublicRoute =
    pathname === "/sign-in" || pathname === "/access-denied";
  const isQnuV1Route = isV1Route(pathname);
  const homeRoute = backendHomeRoute(user?.userType);
  const shouldRedirectToHome = user !== null && pathname === "/";

  useEffect(() => {
    if (shouldRedirectToHome) {
      void navigate({ to: homeRoute, replace: true });
    }
  }, [homeRoute, navigate, shouldRedirectToHome]);

  if (pathname === "/signin-oidc") {
    return <Outlet />;
  }

  if (isPublicRoute)
    return (
      <>
        <TemplateNotice />
        <Outlet />
      </>
    );
  if (shouldRedirectToHome) return null;

  // QNU AI v1 screens use the real backendV1 actor, never the KTX demo session.
  if (isQnuV1Route)
    return (
      <V1SessionGate>
        <AdminShell>
          <Outlet />
        </AdminShell>
      </V1SessionGate>
    );

  return (
    <AuthGate>
      <AdminShell>
        <Outlet />
      </AdminShell>
    </AuthGate>
  );
}

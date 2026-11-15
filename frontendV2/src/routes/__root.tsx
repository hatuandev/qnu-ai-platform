import { createRootRoute, Outlet, useLocation } from "@tanstack/react-router";
import { AdminSessionGate } from "@/components/auth/admin-session-gate";
import { AppShell } from "@/layouts/app-shell";

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  const location = useLocation();
  // The landing page is the public front door; it hands off to SSO and then
  // the session gate takes over for every authenticated route.
  const isPublicPortal =
    location.pathname === "/" ||
    location.pathname.startsWith("/chatbot/") ||
    location.pathname === "/chatbot";

  // SSO callback pages must render without the admin shell or session gate:
  // they run during a full-page redirect from the SSO server.
  const isSsoCallback =
    location.pathname === "/signin-oidc" ||
    location.pathname === "/signout-callback-oidc";

  if (isPublicPortal || isSsoCallback) {
    return <Outlet />;
  }

  return (
    <AdminSessionGate>
      <AppShell>
        <Outlet />
      </AppShell>
    </AdminSessionGate>
  );
}

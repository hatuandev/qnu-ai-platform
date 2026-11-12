import { createRootRoute, Outlet, useLocation } from "@tanstack/react-router";
import { AppShell } from "@/layouts/app-shell";

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  const location = useLocation();
  const isPublicPortal =
    location.pathname.startsWith("/p/") ||
    location.pathname.startsWith("/public") ||
    location.pathname === "/p";

  if (isPublicPortal) {
    return <Outlet />;
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

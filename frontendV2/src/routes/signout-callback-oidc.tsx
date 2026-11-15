import { createFileRoute } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";

export const Route = createFileRoute("/signout-callback-oidc")({
  component: SignOutCallbackPage,
});

function SignOutCallbackPage() {
  useEffect(() => {
    window.location.replace("/");
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-background px-4 text-foreground antialiased select-none">
      <div className="w-full max-w-md rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="py-8 flex flex-col items-center justify-center text-center space-y-4">
          <div className="relative flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Loader2 className="size-6 animate-spin" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-foreground">
              Đã đăng xuất QNU SSO
            </h3>
            <p className="text-xs text-muted-foreground">
              Đang quay về trang chủ của nền tảng.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

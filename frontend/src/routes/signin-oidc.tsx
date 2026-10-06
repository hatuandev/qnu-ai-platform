import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AlertCircle, Bot, Loader2, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  getUserManager,
  handleSsoCallback,
  parseOidcUser,
} from "@/app/auth/oidc";
import { currentUserQueryKey } from "@/app/auth/queries";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/signin-oidc")({
  component: SignInOidcCallback,
});

function SignInOidcCallback() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const executedRef = useRef(false);

  useEffect(() => {
    if (executedRef.current) return;
    executedRef.current = true;

    handleSsoCallback()
      .then(({ user, returnUrl }) => {
        const currentUser = parseOidcUser(user);
        if (currentUser) {
          queryClient.setQueryData(currentUserQueryKey, currentUser);
        }
        const target = returnUrl?.startsWith("/") ? returnUrl : "/dashboard";
        window.location.replace(target);
      })
      .catch(async (err) => {
        console.error("QNU SSO Callback Error:", err);
        try {
          const mgr = getUserManager();
          const user = await mgr.getUser();
          if (user && !user.expired) {
            const currentUser = parseOidcUser(user);
            if (currentUser) {
              queryClient.setQueryData(currentUserQueryKey, currentUser);
            }
            window.location.replace("/dashboard");
            return;
          }
        } catch {
          // ignore fallback error
        }
        setError(
          err?.message ||
            "Không thể hoàn tất phiên xác thực với hệ thống QNU Single Sign-On.",
        );
      });
  }, [queryClient]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4 bg-muted/20">
        <div className="w-full max-w-md rounded-2xl border border-destructive/30 bg-card p-7 text-center shadow-xl space-y-4">
          <div className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive mx-auto border border-destructive/20">
            <AlertCircle className="size-7" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-foreground">
              Đăng nhập QNU SSO Không Thành Công
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {error}
            </p>
          </div>
          <Button
            className="w-full h-10 text-xs font-semibold gap-2 mt-2"
            onClick={() => void navigate({ to: "/sign-in", replace: true })}
          >
            Quay lại trang Đăng nhập
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 bg-background select-none">
      <div className="relative flex items-center justify-center size-16 rounded-2xl bg-primary/10 border border-primary/20 text-primary shadow-xs">
        <Bot className="size-8" />
        <Loader2 className="absolute -top-1.5 -right-1.5 size-5 animate-spin text-primary" />
      </div>

      <div className="text-center space-y-1">
        <div className="flex items-center justify-center gap-1.5 text-sm font-bold text-foreground">
          <ShieldCheck className="size-4 text-emerald-600" />
          <span>Đang hoàn tất phiên xác thực QNU SSO...</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Đang đồng bộ danh tính và phân quyền tài nguyên, vui lòng chờ trong
          giây lát
        </p>
      </div>
    </div>
  );
}

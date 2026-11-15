import { createFileRoute, useRouter } from "@tanstack/react-router";
import {
  AlertTriangle,
  KeyRound,
  Loader2,
  LogIn,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getMe } from "@/api/auth";
import { primeSessionBootstrap } from "@/api/session-bootstrap";
import { beginSsoLogin, completeSsoLogin, SsoError } from "@/api/sso";
import { listWorkspaces } from "@/api/workspaces";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/signin-oidc")({
  component: SignInOidcPage,
});

type CallbackError = {
  message: string;
};

const PRIME_TIMEOUT_MS = 4 * 1000;

async function primeDashboardData(): Promise<void> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), PRIME_TIMEOUT_MS);
  try {
    const [me, workspaces] = await Promise.all([
      getMe({ signal: controller.signal }),
      listWorkspaces({ page: 1, pageSize: 50 }, { signal: controller.signal }),
    ]);
    if (me?.actor?.authenticated) {
      primeSessionBootstrap(me.actor, workspaces.items);
    }
  } catch {
    // Best effort: the session gate retries and reports real failures.
  } finally {
    window.clearTimeout(timer);
  }
}

function SignInOidcPage() {
  const router = useRouter();
  const [error, setError] = useState<CallbackError | null>(null);
  const hasStartedRef = useRef(false);

  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    completeSsoLogin()
      .then(async ({ returnTo }) => {
        // Prime identity/workspaces here so the session gate does not show a
        // second "đang kiểm tra" stop before the dashboard.
        await primeDashboardData();
        // SPA navigation keeps the in-memory token; a full reload would
        // discard it and bounce through SSO again.
        router.history.replace(returnTo);
      })
      .catch((err: unknown) => {
        setError({
          message:
            err instanceof SsoError
              ? err.message
              : err instanceof Error
                ? err.message
                : "Không thể hoàn tất đăng nhập QNU SSO.",
        });
      });
  }, [router]);

  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-background px-4 text-foreground antialiased select-none">
      <div className="w-full max-w-md rounded-xl border border-border/80 bg-card p-6 shadow-sm space-y-5">
        {error ? (
          <>
            <div className="flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
              <ShieldAlert className="size-6" />
            </div>

            <div className="space-y-1.5">
              <h2 className="text-sm font-semibold text-foreground">
                Đăng nhập QNU SSO không hoàn tất
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Phản hồi từ máy chủ SSO chưa đủ để mở phiên làm việc cho tài
                khoản của bạn.
              </p>
            </div>

            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive space-y-1">
              <div className="font-semibold flex items-center gap-1.5">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span>Chi tiết lỗi:</span>
              </div>
              <p className="font-mono text-[11px] leading-relaxed break-words">
                {error.message}
              </p>
            </div>

            <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground space-y-1">
              <div className="font-medium text-foreground flex items-center gap-1.5">
                <KeyRound className="size-3.5 text-primary" />
                <span>Hướng dẫn xử lý:</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                Bấm Đăng nhập lại để tạo yêu cầu mới. Nếu lỗi lặp lại, phiên
                đăng nhập SSO trên trình duyệt có thể đã hết hạn hoặc trình
                duyệt đang chặn sessionStorage.
              </p>
            </div>

            <Button
              size="sm"
              className="w-full h-9 text-xs font-medium gap-2"
              onClick={() => {
                void beginSsoLogin("/dashboard").catch((err: unknown) => {
                  setError({
                    message:
                      err instanceof Error
                        ? err.message
                        : "Không thể bắt đầu đăng nhập QNU SSO.",
                  });
                });
              }}
            >
              <LogIn className="size-3.5" />
              <span>Đăng nhập lại</span>
            </Button>
          </>
        ) : (
          <div className="py-8 flex flex-col items-center justify-center text-center space-y-4">
            <div className="relative flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Loader2 className="size-6 animate-spin" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">
                Đang hoàn tất đăng nhập QNU SSO…
              </h3>
              <p className="text-xs text-muted-foreground">
                Đổi mã phiên an toàn (PKCE) sang phiên làm việc của nền tảng.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

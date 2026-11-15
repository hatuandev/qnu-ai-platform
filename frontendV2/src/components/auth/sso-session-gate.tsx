import {
  AlertTriangle,
  Building2,
  Copy,
  KeyRound,
  Loader2,
  LogIn,
  LogOut,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { getMe } from "@/api/auth";
import { ApiProblemError } from "@/api/client";
import { peekSessionBootstrap } from "@/api/session-bootstrap";
import { getAccessToken, subscribeToken } from "@/api/session-token";
import {
  beginSsoLogin,
  ensureSsoSession,
  isSsoLoggingOut,
  logoutSso,
  SsoError,
} from "@/api/sso";
import { listWorkspaces, type Workspace } from "@/api/workspaces";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/lib/ui-store";

type SsoGateStatus =
  | "checking"
  | "redirecting"
  | "no_workspace"
  | "ready"
  | "error";

type SsoGateError = {
  code: string;
  message: string;
};

function currentReturnTo(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

/**
 * Apply the workspace list to the UI store.
 * Returns false when the account has no workspace yet.
 */
function selectWorkspace(
  items: Workspace[],
  setActiveWorkspace: (ws: Workspace | null) => void,
): boolean {
  if (items.length === 0) return false;
  const currentId = useUiStore.getState().activeWorkspaceId;
  const isCurrentValid =
    currentId !== null && items.some((w) => w.id === currentId);
  if (!isCurrentValid) {
    setActiveWorkspace(items[0]);
  }
  return true;
}

function describeError(err: unknown): SsoGateError {
  if (err instanceof SsoError) {
    return { code: err.code, message: err.message };
  }
  if (err instanceof ApiProblemError) {
    if (err.isUnauthorized) {
      return {
        code: "sso_backend_unauthorized",
        message:
          "BackendV1 từ chối token do QNU SSO cấp (HTTP 401). Cấu hình xác thực SSO ở backend chưa khớp với máy chủ SSO.",
      };
    }
    return { code: `api_${err.code}`, message: err.message };
  }
  if (err instanceof Error) {
    return { code: "sso_unknown", message: err.message };
  }
  return {
    code: "sso_unknown",
    message: "Lỗi không xác định khi kiểm tra phiên đăng nhập QNU SSO.",
  };
}

function errorHint(code: string): string | null {
  if (code === "sso_config") {
    return "Khai báo VITE_SSO_ENABLED, VITE_SSO_AUTHORITY và VITE_SSO_CLIENT_ID trong frontendV2/.env.local (xem .env.example của frontendV2).";
  }
  if (code === "sso_unreachable") {
    return "Máy chủ QNU SSO chưa phản hồi. Kiểm tra dịch vụ SSO đang chạy và trình duyệt truy cập được địa chỉ này, rồi bấm Thử lại.";
  }
  if (code === "sso_backend_unauthorized") {
    return "Đối chiếu SSO_AUTHORITY ở backendV1 với issuer thật của QNU SSO (giữ nguyên dấu / ở cuối) và SSO_AUDIENCE=ai_api.";
  }
  if (code === "sso_callback_invalid" || code === "sso_callback_expired") {
    return "Phiên đăng nhập tạm trên trình duyệt đã hết hiệu lực. Bấm Đăng nhập lại để tạo phiên mới.";
  }
  if (code === "sso_storage") {
    return "Trình duyệt (hoặc chế độ ẩn danh) đang chặn sessionStorage. Cho phép lưu trữ cho trang này rồi thử lại.";
  }
  return null;
}

function SsoSessionGateInner({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SsoGateStatus>("checking");
  const [error, setError] = useState<SsoGateError | null>(null);
  const devActor = useUiStore((s) => s.devActor);
  const setDevActor = useUiStore((s) => s.setDevActor);
  const setActiveWorkspace = useUiStore((s) => s.setActiveWorkspace);
  const setIsSingleUnitMode = useUiStore((s) => s.setIsSingleUnitMode);
  const isInitializingRef = useRef(false);
  const isReadyRef = useRef(false);

  const startLogin = useCallback((returnTo: string) => {
    setStatus("redirecting");
    void beginSsoLogin(returnTo).catch((err: unknown) => {
      setError(describeError(err));
      setStatus("error");
    });
  }, []);

  const handleCopyIdentifier = useCallback(async () => {
    const identifier = useUiStore.getState().devActor?.actor_id;
    if (!identifier) return;
    try {
      await navigator.clipboard.writeText(identifier);
      toast.success("Đã sao chép mã định danh QNU SSO.");
    } catch {
      toast.error("Trình duyệt không cho phép sao chép tự động.");
    }
  }, []);

  const init = useCallback(async () => {
    if (isInitializingRef.current) return;
    isInitializingRef.current = true;
    setStatus("checking");
    setError(null);

    try {
      const hasSession = await ensureSsoSession();
      if (!hasSession) {
        startLogin(currentReturnTo());
        return;
      }

      const bootstrap = peekSessionBootstrap();
      if (bootstrap) {
        setDevActor(bootstrap.actor);
        if (!selectWorkspace(bootstrap.workspaces, setActiveWorkspace)) {
          setStatus("no_workspace");
          return;
        }
        setIsSingleUnitMode(false);
        isReadyRef.current = true;
        setStatus("ready");
        return;
      }

      const meRes = await getMe();
      if (!meRes?.actor?.authenticated) {
        setError({
          code: "sso_identity_missing",
          message:
            "Backend chưa xác nhận được danh tính người dùng từ QNU SSO.",
        });
        setStatus("error");
        return;
      }

      setDevActor(meRes.actor);

      const workspacesPage = await listWorkspaces({ page: 1, pageSize: 50 });
      if (!selectWorkspace(workspacesPage.items, setActiveWorkspace)) {
        setStatus("no_workspace");
        return;
      }
      setIsSingleUnitMode(false);

      isReadyRef.current = true;
      setStatus("ready");
    } catch (err: unknown) {
      setError(describeError(err));
      setStatus("error");
    } finally {
      isInitializingRef.current = false;
    }
  }, [setActiveWorkspace, setDevActor, setIsSingleUnitMode, startLogin]);

  useEffect(() => {
    void init();
  }, [init]);

  useEffect(() => {
    let hadToken = getAccessToken() !== null;
    return subscribeToken(() => {
      const hasToken = getAccessToken() !== null;
      if (hadToken === hasToken) return;
      hadToken = hasToken;
      if (hasToken || !isReadyRef.current || isSsoLoggingOut()) return;
      void init();
    });
  }, [init]);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState !== "visible") return;
      if (!isReadyRef.current || isSsoLoggingOut()) return;
      if (getAccessToken()) return;
      void init();
    };
    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted || isSsoLoggingOut()) return;
      isReadyRef.current = false;
      void init();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pageshow", onPageShow);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("pageshow", onPageShow);
    };
  }, [init]);

  if (status === "ready") {
    return <>{children}</>;
  }

  if (status === "no_workspace") {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-background px-4 text-foreground antialiased select-none">
        <div className="w-full max-w-md rounded-xl border border-border/80 bg-card p-6 shadow-sm space-y-5">
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Building2 className="size-6" />
          </div>

          <div className="space-y-1.5">
            <h2 className="text-sm font-semibold text-foreground">
              Chưa được gán đơn vị làm việc
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              QNU SSO đã xác thực tài khoản của bạn, nhưng tài khoản chưa là
              thành viên của đơn vị làm việc nào đang hoạt động trên nền tảng
              AI.
            </p>
          </div>

          {devActor?.actor_id && (
            <div className="rounded-lg border border-border/60 bg-muted/30 p-3 space-y-1.5">
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Liên hệ quản trị viên đơn vị để được thêm vào. Gửi kèm mã định
                danh QNU SSO của bạn:
              </p>
              <div className="flex items-center gap-2">
                <span className="flex-1 truncate font-mono text-[11px] text-foreground">
                  {devActor.actor_id}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 px-2 text-[11px] gap-1 shrink-0"
                  onClick={() => void handleCopyIdentifier()}
                >
                  <Copy className="size-3" />
                  <span>Sao chép</span>
                </Button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <Button
              size="sm"
              className="w-full h-9 text-xs font-medium gap-2"
              onClick={() => init()}
            >
              <RefreshCw className="size-3.5" />
              <span>Thử lại</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="w-full h-9 text-xs font-medium gap-2"
              onClick={() => void logoutSso()}
            >
              <LogOut className="size-3.5" />
              <span>Đăng xuất</span>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const hint = error ? errorHint(error.code) : null;

  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-background px-4 text-foreground antialiased select-none">
      <div className="w-full max-w-md rounded-xl border border-border/80 bg-card p-6 shadow-sm space-y-5">
        {status === "error" && error ? (
          <>
            <div className="flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
              <ShieldAlert className="size-6" />
            </div>

            <div className="space-y-1.5">
              <h2 className="text-sm font-semibold text-foreground">
                Không thể đăng nhập bằng QNU SSO
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Hệ thống chưa xác lập được phiên làm việc an toàn với tài khoản
                QNU SSO của bạn.
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

            {hint && (
              <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground space-y-1">
                <div className="font-medium text-foreground flex items-center gap-1.5">
                  <KeyRound className="size-3.5 text-primary" />
                  <span>Hướng dẫn xử lý:</span>
                </div>
                <p className="text-[11px] leading-relaxed">{hint}</p>
              </div>
            )}

            <div className="pt-2 grid grid-cols-2 gap-2">
              <Button
                size="sm"
                className="w-full h-9 text-xs font-medium gap-2"
                onClick={() => init()}
              >
                <RefreshCw className="size-3.5" />
                <span>Thử lại</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full h-9 text-xs font-medium gap-2"
                onClick={() => startLogin(currentReturnTo())}
              >
                <LogIn className="size-3.5" />
                <span>Đăng nhập lại</span>
              </Button>
            </div>
          </>
        ) : (
          <div className="py-8 flex flex-col items-center justify-center text-center space-y-4">
            <div className="relative flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Loader2 className="size-6 animate-spin" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">
                {status === "redirecting"
                  ? "Đang chuyển tới QNU SSO…"
                  : "Đang kiểm tra phiên đăng nhập QNU SSO…"}
              </h3>
              <p className="text-xs text-muted-foreground">
                {status === "redirecting"
                  ? "Bạn sẽ được đưa tới trang đăng nhập dùng chung của Đại học Quy Nhơn."
                  : "Xác thực phiên làm việc với máy chủ QNU SSO."}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function SsoSessionGate({ children }: { children: React.ReactNode }) {
  return <SsoSessionGateInner>{children}</SsoSessionGateInner>;
}

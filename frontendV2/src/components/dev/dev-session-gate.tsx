import {
  AlertTriangle,
  Building2,
  KeyRound,
  Loader2,
  LogIn,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { type AuthActor, getMe } from "@/api/auth";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "@/api/session-token";
import {
  getWorkspace,
  listWorkspaces,
  resolveWorkspaceRoute,
  type Workspace,
} from "@/api/workspaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUiStore } from "@/lib/ui-store";

export type DevSessionStatus =
  | "checking"
  | "authenticating"
  | "resolving"
  | "ready"
  | "signed_out"
  | "error";

const SIGNED_OUT_KEY = "qnu.dev.signedOut";
const DEV_TOKEN_STORAGE_KEY = "qnu.dev.token";

function isSignedOut(): boolean {
  try {
    return window.sessionStorage.getItem(SIGNED_OUT_KEY) === "1";
  } catch {
    return false;
  }
}

function setSignedOut(value: boolean): void {
  try {
    if (value) {
      window.sessionStorage.setItem(SIGNED_OUT_KEY, "1");
    } else {
      window.sessionStorage.removeItem(SIGNED_OUT_KEY);
    }
  } catch {
    // Storage may be unavailable; the in-memory token is already cleared.
  }
}

export function logoutDevSession(): void {
  setSignedOut(true);
  clearAccessToken();
  try {
    window.sessionStorage.removeItem(DEV_TOKEN_STORAGE_KEY);
  } catch {
    // ignore
  }
  window.location.href = "/";
}

function DevSessionGateInner({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<DevSessionStatus>("checking");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorHint, setErrorHint] = useState<string | null>(null);

  const [accessKey, setAccessKey] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { setActiveWorkspace, setIsSingleUnitMode, setDevActor } = useUiStore();

  const isExecutingRef = useRef(false);

  const initDevSession = useCallback(async () => {
    if (isExecutingRef.current) return;
    if (!getAccessToken() && isSignedOut()) {
      setStatus("signed_out");
      return;
    }
    isExecutingRef.current = true;

    setStatus("authenticating");
    setErrorMessage(null);
    setErrorHint(null);

    try {
      // 1. Verify existing token or perform auto-login
      let currentActor: AuthActor | null = null;
      let existingToken = getAccessToken();

      if (!existingToken) {
        try {
          const stored = window.sessionStorage.getItem(DEV_TOKEN_STORAGE_KEY);
          if (stored) {
            setAccessToken(stored);
            existingToken = stored;
          }
        } catch {
          // ignore
        }
      }

      if (existingToken) {
        try {
          const meRes = await getMe();
          if (meRes?.actor?.authenticated) {
            currentActor = meRes.actor;
          }
        } catch {
          existingToken = null;
          clearAccessToken();
          try {
            window.sessionStorage.removeItem(DEV_TOKEN_STORAGE_KEY);
          } catch {
            // ignore
          }
        }
      }

      let configuredWorkspaceCode: string | null =
        (
          import.meta.env.VITE_DEV_WORKSPACE_CODE as string | undefined
        )?.trim() || null;

      if (!currentActor) {
        if (isSignedOut()) {
          setStatus("signed_out");
          return;
        }

        // Try Vite dev auto-login bridge if in dev mode
        let autoLoggedIn = false;
        if (import.meta.env.DEV) {
          try {
            const bridgeResponse = await fetch("/__qnu_dev/auto-login", {
              method: "POST",
              headers: { Accept: "application/json" },
            });
            if (bridgeResponse.ok) {
              const payload = (await bridgeResponse.json().catch(() => null)) as {
                access_token?: string;
                default_workspace_code?: string;
              } | null;
              if (payload?.access_token) {
                setAccessToken(payload.access_token);
                try {
                  window.sessionStorage.setItem(
                    DEV_TOKEN_STORAGE_KEY,
                    payload.access_token,
                  );
                } catch {
                  // ignore
                }
                if (payload.default_workspace_code) {
                  configuredWorkspaceCode = payload.default_workspace_code;
                }
                const meRes = await getMe();
                if (meRes?.actor?.authenticated) {
                  currentActor = meRes.actor;
                  autoLoggedIn = true;
                }
              }
            }
          } catch {
            // bridge not reachable
          }
        }

        if (!autoLoggedIn) {
          setStatus("signed_out");
          return;
        }
      }

      if (!currentActor) {
        setStatus("signed_out");
        return;
      }

      setDevActor(currentActor);
      setSignedOut(false);

      // 2. Resolve default workspace code if available from dev config
      if (!configuredWorkspaceCode && import.meta.env.DEV) {
        try {
          const cfgRes = await fetch("/__qnu_dev/config");
          if (cfgRes.ok) {
            const cfg = (await cfgRes.json()) as { workspace_code?: string };
            if (cfg?.workspace_code) {
              configuredWorkspaceCode = cfg.workspace_code;
            }
          }
        } catch {
          // ignore
        }
      }

      setStatus("resolving");

      // 3. Resolve workspace: configured code first, fallback to first available workspace
      let realWorkspace: Workspace | null = null;
      if (configuredWorkspaceCode) {
        try {
          const resolved = await resolveWorkspaceRoute(configuredWorkspaceCode);
          realWorkspace = await getWorkspace(resolved.workspace_id);
        } catch {
          // fallback to listWorkspaces
        }
      }

      if (!realWorkspace) {
        try {
          const wsList = await listWorkspaces();
          if (wsList.items.length > 0) {
            realWorkspace = wsList.items[0];
          }
        } catch {
          // ignore
        }
      }

      setActiveWorkspace(realWorkspace);
      setIsSingleUnitMode(false);
      setStatus("ready");
    } catch (err: unknown) {
      setStatus("error");
      const message =
        err instanceof Error
          ? err.message
          : "Lỗi không xác định khi khởi tạo phiên làm việc dev.";
      setErrorMessage(message);
    } finally {
      isExecutingRef.current = false;
    }
  }, [setActiveWorkspace, setIsSingleUnitMode, setDevActor]);

  useEffect(() => {
    initDevSession();
  }, [initDevSession]);

  const handleDevLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const key = accessKey.trim();
    if (!key) return;
    setIsSubmitting(true);
    setLoginError(null);
    try {
      const res = await fetch("/platform/v1alpha1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_key: key }),
      });
      const data = (await res.json().catch(() => null)) as {
        access_token?: string;
        detail?: string;
        message?: string;
      } | null;
      if (!res.ok) {
        throw new Error(
          data?.detail || data?.message || "Khóa truy cập không chính xác.",
        );
      }
      if (!data?.access_token) {
        throw new Error("Không nhận được token xác thực từ server.");
      }
      setAccessToken(data.access_token);
      try {
        window.sessionStorage.setItem(DEV_TOKEN_STORAGE_KEY, data.access_token);
      } catch {
        // ignore
      }
      setSignedOut(false);
      isExecutingRef.current = false;
      await initDevSession();
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (status === "ready") {
    return <>{children}</>;
  }

  if (status === "signed_out") {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-background px-4 text-foreground antialiased select-none">
        <div className="w-full max-w-sm rounded-xl border border-border/80 bg-card p-6 shadow-sm space-y-5">
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <KeyRound className="size-6" />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-base font-semibold text-foreground tracking-tight">
              Đăng nhập Quản trị
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Nhập khóa truy cập nội bộ (Access Key) để đăng nhập vào bảng điều khiển quản trị QNU AI.
            </p>
          </div>

          <form onSubmit={handleDevLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="dev-access-key"
                className="text-xs font-medium text-foreground"
              >
                Khóa truy cập
              </label>
              <Input
                id="dev-access-key"
                type="password"
                autoFocus
                disabled={isSubmitting}
                placeholder="Nhập khóa quản trị (ví dụ: QNU@2026)"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                className="text-xs"
              />
            </div>

            {loginError && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-2.5 text-xs text-destructive flex items-center gap-2">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span>{loginError}</span>
              </div>
            )}

            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting || !accessKey.trim()}
              className="w-full h-9 text-xs font-medium gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang xác thực...</span>
                </>
              ) : (
                <>
                  <LogIn className="size-3.5" />
                  <span>Đăng nhập</span>
                </>
              )}
            </Button>
          </form>

          <div className="pt-2 border-t border-border/40 text-center">
            <a
              href="/"
              className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              ← Quay lại Cổng tư vấn công khai
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-background px-4 text-foreground antialiased select-none">
      <div className="w-full max-w-md rounded-xl border border-border/80 bg-card p-6 shadow-sm space-y-5">
        {status === "error" ? (
          <>
            <div className="flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
              <ShieldAlert className="size-6" />
            </div>

            <div className="space-y-1.5">
              <h2 className="text-sm font-semibold text-foreground">
                Không thể khởi tạo phiên làm việc Dev
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Đã xảy ra lỗi trong quá trình tự đăng nhập hoặc định tuyến đơn
                vị thật từ backend.
              </p>
            </div>

            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive space-y-1">
              <div className="font-semibold flex items-center gap-1.5">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span>Chi tiết lỗi:</span>
              </div>
              <p className="font-mono text-[11px] leading-relaxed break-words">
                {errorMessage}
              </p>
            </div>

            {errorHint && (
              <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground space-y-1">
                <div className="font-medium text-foreground flex items-center gap-1.5">
                  <Building2 className="size-3.5 text-primary" />
                  <span>Hướng dẫn xử lý:</span>
                </div>
                <p className="text-[11px] leading-relaxed">{errorHint}</p>
              </div>
            )}

            <div className="pt-2">
              <Button
                size="sm"
                className="w-full h-9 text-xs font-medium gap-2"
                onClick={() => initDevSession()}
              >
                <RefreshCw className="size-3.5" />
                <span>Thử kết nối lại</span>
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
                {status === "authenticating"
                  ? "Đang xác thực phiên dev..."
                  : "Đang định tuyến đơn vị làm việc..."}
              </h3>
              <p className="text-xs text-muted-foreground">
                Kết nối tới Backend QNU AI
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function DevSessionGate({ children }: { children: React.ReactNode }) {
  return <DevSessionGateInner>{children}</DevSessionGateInner>;
}

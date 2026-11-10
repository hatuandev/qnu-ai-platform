import {
  AlertTriangle,
  Building2,
  Loader2,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { type AuthActor, getMe } from "@/api/auth";
import { getAccessToken, setAccessToken } from "@/api/session-token";
import {
  getWorkspace,
  resolveWorkspaceRoute,
  type Workspace,
} from "@/api/workspaces";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/lib/ui-store";

export type DevSessionStatus =
  | "checking"
  | "authenticating"
  | "resolving"
  | "ready"
  | "error";

function DevSessionGateInner({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<DevSessionStatus>("checking");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorHint, setErrorHint] = useState<string | null>(null);

  const { setActiveWorkspace, setIsSingleUnitMode, setDevActor } = useUiStore();

  const isExecutingRef = useRef(false);

  const initDevSession = useCallback(async () => {
    if (isExecutingRef.current) return;
    isExecutingRef.current = true;

    setStatus("authenticating");
    setErrorMessage(null);
    setErrorHint(null);

    try {
      // 1. Verify existing token or perform auto-login
      let currentActor: AuthActor | null = null;
      let existingToken = getAccessToken();

      if (existingToken) {
        try {
          const meRes = await getMe();
          if (meRes?.actor?.authenticated) {
            currentActor = meRes.actor;
          }
        } catch {
          // Token is invalid/expired; clear it and call dev bridge
          existingToken = null;
        }
      }

      let configuredWorkspaceCode: string | null =
        (
          import.meta.env.VITE_DEV_WORKSPACE_CODE as string | undefined
        )?.trim() || null;

      if (!currentActor) {
        // Call dev auto-login bridge served by Vite dev server
        let bridgeResponse: Response;
        try {
          bridgeResponse = await fetch("/__qnu_dev/auto-login", {
            method: "POST",
            headers: {
              Accept: "application/json",
            },
          });
        } catch {
          throw new Error(
            "Không thể kết nối đến cầu nối dev server tại /__qnu_dev/auto-login. Kiểm tra dev server Vite đang chạy.",
          );
        }

        const payload = (await bridgeResponse.json().catch(() => null)) as {
          access_token?: string;
          code?: string;
          message?: string;
          default_workspace_code?: string;
        } | null;

        if (!bridgeResponse.ok) {
          const detail =
            payload?.message ||
            `Lỗi HTTP ${bridgeResponse.status} từ cầu nối dev auto-login.`;
          const code = payload?.code;

          let hint = "Kiểm tra cấu hình dev trong frontendV2/.env.local.";
          if (code === "backend_unreachable") {
            hint =
              "BackendV1 chưa khởi chạy hoặc cổng 8002 không phản hồi. Hãy khởi động backendV1 (cd backendV1 && uv run ...).";
          } else if (code === "invalid_credentials") {
            hint =
              "Mật khẩu dev không đúng. Kiểm tra DEV_ACCESS_PASSWORD trong file .env và QNU_DEV_ACCESS_KEY trong frontendV2/.env.local.";
          } else if (code === "dev_gate_disabled") {
            hint =
              "Dev gate ở backend đang tắt. Đặt DEV_AUTH_ENABLED=true trong file .env của backendV1.";
          }

          setErrorHint(hint);
          throw new Error(detail);
        }

        const token = payload?.access_token;
        if (!token) {
          throw new Error(
            "Cầu nối đăng nhập thành công nhưng không trả access_token.",
          );
        }

        setAccessToken(token);

        if (payload?.default_workspace_code) {
          configuredWorkspaceCode = payload.default_workspace_code;
        }

        // Validate actor via GET /auth/me
        const meRes = await getMe();
        if (!meRes?.actor?.authenticated) {
          throw new Error("Không thể xác nhận danh tính actor từ /auth/me.");
        }
        currentActor = meRes.actor;
      }

      setDevActor(currentActor);

      // 2. Resolve default workspace code
      if (!configuredWorkspaceCode) {
        // Query dev server config if not provided yet
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

      if (!configuredWorkspaceCode) {
        setErrorHint(
          "Đặt QNU_DEV_WORKSPACE_CODE=shl hoặc VITE_DEV_WORKSPACE_CODE=shl trong frontendV2/.env.local.",
        );
        throw new Error(
          "Cấu hình thiếu mã đơn vị dev. Không tự chọn đơn vị mẫu.",
        );
      }

      setStatus("resolving");

      // 3. Resolve workspace ID via GET /workspaces/resolve-route?code=...
      let resolved: { workspace_id: string; code: string };
      try {
        resolved = await resolveWorkspaceRoute(configuredWorkspaceCode);
      } catch (err: unknown) {
        const errorText = err instanceof Error ? err.message : String(err);
        if (
          errorText.includes("workspace_not_found") ||
          errorText.includes("404") ||
          errorText.includes("Không tìm thấy")
        ) {
          setErrorHint(
            `Đơn vị "${configuredWorkspaceCode}" chưa tồn tại trong cơ sở dữ liệu. Hãy chạy seed backend: cd backendV1 && uv run --frozen python -m scripts.seed_shl_pilot`,
          );
          throw new Error(
            `Không tìm thấy đơn vị với mã "${configuredWorkspaceCode}".`,
          );
        }
        if (
          errorText.includes("permission_denied") ||
          errorText.includes("403")
        ) {
          setErrorHint(
            `Tài khoản dev "${currentActor.username}" chưa được gán quyền trong đơn vị "${configuredWorkspaceCode}".`,
          );
          throw new Error(
            `Tài khoản không có quyền truy cập đơn vị "${configuredWorkspaceCode}".`,
          );
        }
        throw err;
      }

      // 4. Fetch full workspace detail
      let realWorkspace: Workspace;
      try {
        realWorkspace = await getWorkspace(resolved.workspace_id);
      } catch {
        throw new Error(
          `Không thể tải thông tin chi tiết của đơn vị ID: ${resolved.workspace_id}.`,
        );
      }

      // 5. Commit to dev state
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

  if (status === "ready") {
    return <>{children}</>;
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
                  ? "Đang xác thực phiên dev qua loopback..."
                  : "Đang định tuyến đơn vị làm việc thật..."}
              </h3>
              <p className="text-xs text-muted-foreground">
                Kết nối tới BackendV1 tại 127.0.0.1:8002
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function DevSessionGate({ children }: { children: React.ReactNode }) {
  if (!import.meta.env.DEV) {
    return <>{children}</>;
  }
  return <DevSessionGateInner>{children}</DevSessionGateInner>;
}

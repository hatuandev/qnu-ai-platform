import {
  AlertCircle,
  KeyRound,
  Loader2,
  LogIn,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { ApiProblemError } from "@/app/api/v1";
import { describeDevAutoLoginError } from "@/app/auth/v1/auto-login-errors";
import { useV1Auth } from "@/app/auth/v1/provider";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * Turn a v1 failure into a message that names the real cause.
 *
 * The dev gate is a server switch: this screen never enables it, never stores the
 * access key and never reads a password from the bundle.
 */
export function describeV1AuthError(error: unknown): string {
  if (error instanceof ApiProblemError) {
    switch (error.code) {
      case "invalid_credentials":
        return "Access key không đúng. Kiểm tra DEV_ACCESS_PASSWORD ở backendV1.";
      case "dev_gate_disabled":
        return "BackendV1 đang tắt dev access gate. Vui lòng đăng nhập qua QNU Single Sign-On.";
      case "sso_unavailable":
        return "Không kết nối được dịch vụ SSO hoặc khóa ký chưa sẵn sàng. Thử lại sau.";
      case "sso_unconfigured":
        return "SSO chưa được cấu hình đầy đủ ở backendV1.";
      case "SIGNING_KEY_MISSING":
        return "BackendV1 thiếu SECRET_KEY tối thiểu 32 byte nên không ký được token.";
      case "network_unreachable":
        return "Không kết nối được backendV1. Kiểm tra dịch vụ đang chạy ở cổng 8002.";
      case "invalid_token":
        return "Phiên đăng nhập SSO không hợp lệ hoặc đã hết hạn. Đăng nhập lại.";
      default:
        return error.message;
    }
  }
  return error instanceof Error ? error.message : "Không đăng nhập được.";
}

function Shell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-10">
      <section className="w-full max-w-md rounded-lg border bg-background p-6 shadow-2xs sm:p-8">
        <div className="mb-6 space-y-3">
          <div className="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
            <ShieldCheck className="size-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              QNU AI Platform · v1alpha1
            </p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">
              {title}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        {children}
        {footer ? (
          <div className="mt-6 border-t pt-4 text-[11px] leading-relaxed text-muted-foreground">
            {footer}
          </div>
        ) : null}
      </section>
    </main>
  );
}

function LoginScreen({ onAutoLogin }: { onAutoLogin?: () => void }) {
  const { signIn, signInWithSso, expired, autoLoginAvailable } = useV1Auth();
  const [accessKey, setAccessKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [ssoPending, setSsoPending] = useState(false);
  const [showDevGate, setShowDevGate] = useState(false);

  const isDevGateAllowed =
    typeof import.meta !== "undefined" &&
    !import.meta.env?.PROD &&
    (import.meta.env?.DEV || import.meta.env?.VITE_DEV_AUTH_ENABLED === "true");

  const handleSsoLogin = async () => {
    if (ssoPending) return;
    setSsoPending(true);
    setError(null);
    try {
      await signInWithSso();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Không thể kết nối tới trang đăng nhập QNU SSO.",
      );
      setSsoPending(false);
    }
  };

  const submitDevKey = async (event: React.FormEvent) => {
    event.preventDefault();
    if (pending) return;
    const value = accessKey.trim();
    if (!value) {
      setError("Nhập access key của dev gate.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await signIn(value);
      setAccessKey("");
    } catch (cause) {
      setError(describeV1AuthError(cause));
    } finally {
      setPending(false);
    }
  };

  return (
    <Shell
      title="Đăng nhập QNU AI Platform"
      subtitle="Xác thực qua cổng QNU Single Sign-On để truy cập phân hệ Workspaces và ModelOps."
      footer={
        <>
          Hệ thống bảo vệ phiên bằng PKCE S256. Token truy cập chỉ lưu trữ trong
          bộ nhớ của phiên duyệt web này, không lưu vĩnh viễn vào localStorage.
        </>
      }
    >
      {expired && !error ? (
        <Alert className="mb-4" variant="destructive">
          <AlertCircle className="size-4" />
          <AlertTitle>Phiên đã hết hạn</AlertTitle>
          <AlertDescription>
            Phiên làm việc trước đó đã kết thúc. Vui lòng đăng nhập lại.
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4">
        {/* Primary action: QNU SSO */}
        <Button
          type="button"
          size="default"
          className="w-full gap-2 text-xs font-medium"
          disabled={ssoPending || pending}
          onClick={() => void handleSsoLogin()}
        >
          {ssoPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              <span>Đang chuyển hướng tới QNU SSO...</span>
            </>
          ) : (
            <>
              <LogIn className="size-4" />
              <span>Đăng nhập QNU SSO</span>
            </>
          )}
        </Button>

        {error ? (
          <p
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
          >
            {error}
          </p>
        ) : null}

        {/* Local dev bridge: only rendered inside the Vite dev server */}
        {autoLoginAvailable && onAutoLogin ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="w-full gap-2 text-xs"
            disabled={pending || ssoPending}
            onClick={onAutoLogin}
          >
            <Sparkles className="size-3.5" />
            <span>Tự đăng nhập bằng cấu hình local</span>
          </Button>
        ) : null}

        {/* Secondary: Local dev access key gate (only in development) */}
        {isDevGateAllowed ? (
          <div className="mt-2 border-t pt-3">
            <button
              type="button"
              className="flex w-full items-center justify-between text-[11px] text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setShowDevGate((prev) => !prev)}
            >
              <span>Sử dụng Dev Access Key (kiểm thử cục bộ)</span>
              <span className="text-[10px]">{showDevGate ? "▲" : "▼"}</span>
            </button>

            {showDevGate ? (
              <form
                className="mt-3 grid gap-3"
                onSubmit={submitDevKey}
                noValidate
              >
                <Field>
                  <FieldLabel htmlFor="v1-access-key">Access key</FieldLabel>
                  <Input
                    id="v1-access-key"
                    type="password"
                    autoComplete="off"
                    className="text-xs"
                    placeholder="Nhập access key dev gate"
                    value={accessKey}
                    disabled={pending || ssoPending}
                    onChange={(event) => setAccessKey(event.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  <FieldDescription className="text-xs">
                    Gửi tới <code>POST /platform/v1alpha1/auth/login</code>.
                  </FieldDescription>
                </Field>

                <Button
                  type="submit"
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-xs"
                  disabled={pending || ssoPending}
                >
                  {pending ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      <span>Đang xác thực...</span>
                    </>
                  ) : (
                    <>
                      <KeyRound className="size-3.5" />
                      <span>Đăng nhập bằng dev key</span>
                    </>
                  )}
                </Button>
              </form>
            ) : null}
          </div>
        ) : null}
      </div>
    </Shell>
  );
}

function AutoLoginScreen() {
  return (
    <Shell
      title="Đang tự đăng nhập"
      subtitle="Dev server đang dùng cấu hình local để lấy token từ backendV1."
    >
      <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin text-primary" />
        <span>Đang xác thực qua cầu nối dev server...</span>
      </div>
    </Shell>
  );
}

function AutoLoginErrorScreen({
  onManualLogin,
}: {
  onManualLogin: () => void;
}) {
  const { autoLoginError, retryAutoLogin, signInWithSso, autoLoginPhase } =
    useV1Auth();
  const pending = autoLoginPhase === "pending";

  return (
    <Shell
      title="Không tự đăng nhập được"
      subtitle="Cầu nối đăng nhập local không lấy được token hợp lệ."
    >
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="size-4" />
        <AlertTitle>Kiểm tra cấu hình local</AlertTitle>
        <AlertDescription>
          {describeDevAutoLoginError(autoLoginError)}
        </AlertDescription>
      </Alert>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          className="gap-1.5 text-xs"
          disabled={pending}
          onClick={retryAutoLogin}
        >
          {pending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <RefreshCw className="size-3.5" />
          )}
          <span>Thử lại</span>
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 text-xs"
          onClick={onManualLogin}
        >
          <KeyRound className="size-3.5" />
          <span>Đăng nhập thủ công</span>
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="gap-1.5 text-xs"
          onClick={() => void signInWithSso()}
        >
          <LogIn className="size-3.5" />
          <span>QNU SSO</span>
        </Button>
      </div>
      <p className="mt-4 text-[11px] leading-relaxed text-muted-foreground">
        Cần bật <code>QNU_DEV_AUTO_LOGIN=true</code> và{" "}
        <code>QNU_DEV_ACCESS_KEY</code> trong <code>frontendV1/.env.local</code>
        , đồng thời backendV1 phải chạy với <code>DEV_AUTH_ENABLED=true</code>.
        Xem README mục “Tự đăng nhập khi phát triển local”.
      </p>
    </Shell>
  );
}

function VerifyingScreen() {
  return (
    <Shell
      title="Đang xác thực"
      subtitle="Đang đọc actor và quyền từ GET /auth/me."
    >
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
        <Loader2 className="size-4 animate-spin text-primary" />
        <span>Đang tải danh tính người gọi...</span>
      </div>
    </Shell>
  );
}

function SessionErrorScreen() {
  const { error, refetch, signOut, signInWithSso } = useV1Auth();
  return (
    <Shell
      title="Không xác thực được phiên"
      subtitle="BackendV1 không trả được actor hiện tại."
    >
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="size-4" />
        <AlertTitle>Lỗi xác thực</AlertTitle>
        <AlertDescription>{describeV1AuthError(error)}</AlertDescription>
      </Alert>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          className="gap-1.5 text-xs"
          onClick={() => void signInWithSso()}
        >
          <LogIn className="size-3.5" />
          <span>Đăng nhập QNU SSO</span>
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 text-xs"
          onClick={refetch}
        >
          <RefreshCw className="size-3.5" />
          <span>Thử lại</span>
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="gap-1.5 text-xs"
          onClick={() => void signOut()}
        >
          <span>Đăng xuất</span>
        </Button>
      </div>
    </Shell>
  );
}

/**
 * Gate for `/workspaces` and `/modelops`.
 *
 * It never redirects to the KTX BFF and never falls back to demo data: without a
 * verified actor the only thing rendered is the login form.
 */
export function V1SessionGate({ children }: { children: React.ReactNode }) {
  const {
    status,
    autoLoginAvailable,
    autoLoginPhase,
    autoLoginError,
    retryAutoLogin,
  } = useV1Auth();
  const [manualLogin, setManualLogin] = useState(false);

  if (status === "authenticated") return <>{children}</>;
  if (status === "verifying") return <VerifyingScreen />;
  if (status === "error") return <SessionErrorScreen />;

  if (!manualLogin) {
    if (autoLoginPhase === "pending") return <AutoLoginScreen />;
    if (autoLoginPhase === "failed" && autoLoginError) {
      return (
        <AutoLoginErrorScreen onManualLogin={() => setManualLogin(true)} />
      );
    }
  }

  return (
    <LoginScreen
      onAutoLogin={
        autoLoginAvailable
          ? () => {
              setManualLogin(false);
              retryAutoLogin();
            }
          : undefined
      }
    />
  );
}

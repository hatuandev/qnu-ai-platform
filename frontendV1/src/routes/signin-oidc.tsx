import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  Loader2,
  LogIn,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { z } from "zod";
import { authPaths, clearAccessToken, v1Client } from "@/app/api/v1";
import {
  handleSsoCallback,
  isValidActor,
  loginWithSso,
  setSsoCallbackActive,
  type V1ActorResponse,
} from "@/app/auth/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

const searchSchema = z.object({
  code: z.string().optional(),
  state: z.string().optional(),
  error: z.string().optional(),
  error_description: z.string().optional(),
});

export const Route = createFileRoute("/signin-oidc")({
  validateSearch: (search) => searchSchema.parse(search),
  component: SigninOidcCallbackPage,
});

export function SigninOidcCallbackPage() {
  const search = Route.useSearch();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"processing" | "success" | "error">(
    "processing",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDenied, setIsDenied] = useState(false);
  const processedRef = useRef(false);

  // The dev auto-login bridge must never race the SSO code exchange. The flag
  // is cleared when this page unmounts, so the bridge resumes afterwards.
  useEffect(() => {
    setSsoCallbackActive(true);
    return () => setSsoCallbackActive(false);
  }, []);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    // 1. Check if SSO provider returned an explicit error
    if (search.error) {
      setStatus("error");
      if (search.error === "access_denied") {
        setIsDenied(true);
        setErrorMessage(
          search.error_description ||
            "Yêu cầu đăng nhập đã bị từ chối hoặc bị hủy trên cổng QNU SSO.",
        );
      } else {
        setErrorMessage(
          search.error_description ||
            `Lỗi từ QNU SSO: ${search.error}. Vui lòng thử lại.`,
        );
      }
      return;
    }

    // 2. Check for missing authorization code
    if (!search.code) {
      setStatus("error");
      setErrorMessage(
        "Không tìm thấy mã xác thực (authorization code) từ QNU SSO. Vui lòng đăng nhập lại.",
      );
      return;
    }

    // 3. Process OIDC callback, exchange code with PKCE, and verify with backend
    const processCallback = async () => {
      try {
        const { returnUrl } = await handleSsoCallback();

        // 4. Verify token and caller identity against backend GET /auth/me
        const meResponse = await v1Client.get<V1ActorResponse>(authPaths.me);
        if (!meResponse || !isValidActor(meResponse.actor)) {
          clearAccessToken();
          setStatus("error");
          setErrorMessage(
            "Backend không thể xác thực danh tính người dùng từ token SSO vừa cấp.",
          );
          return;
        }

        setStatus("success");
        // 5. Navigate to sanitized return URL
        if (returnUrl === "/workspaces") {
          void navigate({
            to: "/workspaces",
            search: { page: 1, pageSize: 10 },
            replace: true,
          });
        } else {
          void (
            navigate as (opts: {
              to: string;
              replace: boolean;
            }) => Promise<void>
          )({ to: returnUrl, replace: true });
        }
      } catch (err) {
        clearAccessToken();
        setStatus("error");
        const msg =
          err instanceof Error
            ? err.message
            : "Đã xảy ra lỗi không xác định khi xử lý phản hồi từ SSO.";
        setErrorMessage(msg);
      }
    };

    void processCallback();
  }, [navigate, search.code, search.error, search.error_description]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-10">
      <section className="w-full max-w-md rounded-lg border bg-background p-6 shadow-2xs sm:p-8">
        <div className="mb-6 space-y-3">
          <div className="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
            {status === "error" ? (
              <ShieldAlert className="size-5 text-destructive" />
            ) : (
              <ShieldCheck className="size-5" />
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              QNU AI Platform · SSO Callback
            </p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">
              {status === "processing"
                ? "Đang xác thực phiên"
                : status === "success"
                  ? "Đăng nhập thành công"
                  : isDenied
                    ? "Truy cập bị từ chối"
                    : "Lỗi đăng nhập SSO"}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {status === "processing"
                ? "Đang kiểm tra mã giao dịch PKCE và đổi token với QNU SSO..."
                : status === "success"
                  ? "Đang chuyển tiếp về khu vực làm việc..."
                  : "Không thể hoàn tất quy trình xác thực Single Sign-On."}
            </p>
          </div>
        </div>

        {status === "processing" || status === "success" ? (
          <div className="flex items-center gap-3 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-5 animate-spin text-primary" />
            <span>Đang hoàn tất kết nối danh tính người dùng...</span>
          </div>
        ) : (
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertTitle>
                {isDenied ? "Từ chối truy cập" : "Lỗi xác thực"}
              </AlertTitle>
              <AlertDescription className="text-xs leading-relaxed">
                {errorMessage}
              </AlertDescription>
            </Alert>

            <div className="flex flex-wrap gap-2 pt-2">
              <Button
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => void loginWithSso()}
              >
                <LogIn className="size-3.5" />
                <span>Thử đăng nhập lại</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 text-xs"
                onClick={() =>
                  void navigate({
                    to: "/workspaces",
                    search: { page: 1, pageSize: 10 },
                    replace: true,
                  })
                }
              >
                <ArrowLeft className="size-3.5" />
                <span>Về trang chủ</span>
              </Button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

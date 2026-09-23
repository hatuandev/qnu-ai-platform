import { useLocation } from "@tanstack/react-router";
import {
  AlertCircle,
  LogIn,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect } from "react";
import { useAuth } from "@/app/auth";
import logoUrl from "@/assets/logo.png";
import { Button } from "@/components/ui/button";

function AuthLoading() {
  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-background px-4 py-8 overflow-hidden select-none">
      {/* Ambient background glows */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 size-96 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 left-1/2 -translate-x-1/2 size-96 rounded-full bg-indigo-500/5 blur-3xl" />

      {/* Main Glassmorphic Branded Card */}
      <div className="relative z-10 w-full max-w-[380px] sm:max-w-[420px] rounded-2xl border border-border/80 bg-card/90 p-7 sm:p-8 text-center shadow-xl shadow-primary/5 backdrop-blur-xl transition-all">
        {/* Animated Brand Icon with Double Rings */}
        <div className="relative mx-auto mb-5 size-20 flex items-center justify-center">
          {/* Outer Smooth Spinning Ring */}
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary border-r-primary/40 animate-spin duration-1000" />

          {/* Inner Pulsing Ambient Ring */}
          <div className="absolute inset-1.5 rounded-full border border-primary/20 bg-gradient-to-tr from-primary/15 via-primary/5 to-indigo-500/10 animate-pulse" />

          {/* Center Logo Icon */}
          <div className="relative flex size-12 items-center justify-center rounded-full bg-background shadow-xs border border-border/60 overflow-hidden p-1.5">
            <img
              src={logoUrl}
              alt="Logo QNU"
              className="size-full object-contain"
            />
            <Sparkles className="absolute -top-0.5 -right-0.5 size-3.5 text-amber-500 animate-bounce" />
          </div>
        </div>

        {/* Institution & System Title */}
        <div className="space-y-1">
          <p className="text-[11px] font-bold uppercase tracking-wider text-primary">
            Trường Đại học Quy Nhơn
          </p>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-foreground">
            QNU AI Platform — Trợ Lý Số Thông Minh
          </h1>
        </div>

        {/* Status Message */}
        <div className="mt-4 space-y-1">
          <p className="text-sm font-medium text-foreground/90 flex items-center justify-center gap-1.5">
            <span>Đang kiểm tra phiên đăng nhập...</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Đang đồng bộ với hệ thống xác thực tập trung QNU SSO
          </p>
        </div>

        {/* Modern Indeterminate Progress Bar */}
        <div className="mt-6 h-1.5 w-full overflow-hidden rounded-full bg-muted/60 relative">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary/40 via-primary to-primary/40 animate-pulse"
            style={{ width: "100%" }}
          />
        </div>

        {/* Security / SSO Trust Badge Footer */}
        <div className="mt-6 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground/80 border-t border-border/50 pt-4">
          <ShieldCheck className="size-3.5 text-emerald-600 shrink-0" />
          <span>Kết nối an toàn · QNU Single Sign-On</span>
        </div>
      </div>
    </div>
  );
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { error, isAuthenticated, isLoading, refetch, signIn } = useAuth();
  const returnUrl = `${location.pathname}${location.searchStr}${location.hash}`;

  useEffect(() => {
    if (!isLoading && !error && !isAuthenticated) {
      signIn(returnUrl);
    }
  }, [error, isAuthenticated, isLoading, returnUrl, signIn]);

  if (isLoading) return <AuthLoading />;

  if (error) {
    return (
      <div className="relative flex min-h-screen w-full items-center justify-center bg-background px-4 py-8 overflow-hidden select-none">
        {/* Ambient background glows */}
        <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 size-96 rounded-full bg-destructive/10 blur-3xl" />

        <div className="relative z-10 w-full max-w-[380px] sm:max-w-[420px] rounded-2xl border border-destructive/30 bg-card/95 p-7 sm:p-8 text-center shadow-xl shadow-destructive/5 backdrop-blur-xl">
          {/* Error Icon */}
          <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive border border-destructive/20">
            <AlertCircle className="size-7" />
          </div>

          <div className="space-y-1.5">
            <h2 className="text-base font-bold text-foreground">
              Không thể kiểm tra phiên đăng nhập
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {error.message ||
                "Đã xảy ra sự cố khi kết nối tới dịch vụ xác thực QNU SSO."}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              className="w-full sm:w-auto text-xs gap-1.5 h-9"
              onClick={() => void refetch()}
            >
              <RefreshCw className="size-3.5" />
              <span>Thử lại</span>
            </Button>
            <Button
              size="sm"
              className="w-full sm:w-auto text-xs gap-1.5 h-9"
              onClick={() => signIn(returnUrl)}
            >
              <LogIn className="size-3.5" />
              <span>Đăng nhập lại</span>
            </Button>
          </div>

          <div className="mt-5 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground/80 border-t border-border/50 pt-3.5">
            <span>QNU AI Platform · Trường Đại học Quy Nhơn</span>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return <AuthLoading />;

  return children;
}

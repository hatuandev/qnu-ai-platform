import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  GraduationCap,
  KeyRound,
  Lock,
  School,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useAuth } from "@/app/auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const searchSchema = z.object({
  redirect: z.string().optional(),
});

export const Route = createFileRoute("/sign-in")({
  validateSearch: (search) => searchSchema.parse(search),
  component: SignInPage,
});

function SignInPage() {
  const search = Route.useSearch();
  const navigate = useNavigate();
  const { isAuthenticated, login, loginSso } = useAuth();
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSsoLoading, setIsSsoLoading] = useState(false);
  const [showDevGate, setShowDevGate] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      void navigate({
        to: search.redirect?.startsWith("/") ? search.redirect : "/dashboard",
        replace: true,
      });
    }
  }, [isAuthenticated, navigate, search.redirect]);

  const handleSsoLogin = async () => {
    try {
      setIsSsoLoading(true);
      setErrorMsg(null);
      await loginSso(search.redirect || "/dashboard");
    } catch (err) {
      setIsSsoLoading(false);
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Không thể kết nối đến máy chủ xác thực QNU SSO.",
      );
    }
  };

  const handleDevSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setErrorMsg("Vui lòng nhập mật khẩu truy cập.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await login(password);
      void navigate({
        to: search.redirect?.startsWith("/") ? search.redirect : "/dashboard",
        replace: true,
      });
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Mật khẩu không đúng, vui lòng thử lại.";
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFillDefault = () => {
    setPassword("QNU@2026");
    setErrorMsg(null);
  };

  if (isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden select-none">
      {/* Background ambient lighting */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 size-96 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 left-1/2 -translate-x-1/2 size-96 rounded-full bg-indigo-500/5 blur-3xl" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 border border-primary/20 text-primary shadow-xs mb-1">
            <Bot className="size-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            QNU AI Platform
          </h1>
          <p className="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed">
            Hệ thống Quản trị & Vận hành Trợ lý Số Thông minh
            <br />
            <span className="font-semibold text-foreground/90">
              Trường Đại học Quy Nhơn
            </span>
          </p>
        </div>

        {/* Main Card */}
        <Card className="p-6 border border-border/80 shadow-xl bg-card/90 backdrop-blur-md space-y-5">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2 animate-in fade-in duration-200">
              <AlertCircle className="size-4 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium">{errorMsg}</div>
            </div>
          )}

          {/* Section 1: QNU SSO (Primary Action) */}
          <div className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                <ShieldCheck className="size-4 text-emerald-600" />
                <span>Cổng Xác Thực Tập Trung QNU SSO</span>
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Sử dụng tài khoản Trường Đại học Quy Nhơn để đăng nhập an toàn
              </p>
            </div>

            <Button
              type="button"
              onClick={handleSsoLogin}
              disabled={isSsoLoading || isSubmitting}
              className="w-full h-11 text-sm font-semibold flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-primary/10"
            >
              {isSsoLoading ? (
                <>
                  <div className="size-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  <span>Đang kết nối QNU SSO...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="size-4.5" />
                  <span>Đăng Nhập Bằng QNU SSO</span>
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>

            {/* SSO Identity Badges */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="flex items-center gap-1.5 p-2 rounded-md bg-muted/40 border border-border/60 text-[11px] text-muted-foreground">
                <School className="size-3.5 text-primary shrink-0" />
                <span className="truncate">Cán bộ / Giảng viên</span>
              </div>
              <div className="flex items-center gap-1.5 p-2 rounded-md bg-muted/40 border border-border/60 text-[11px] text-muted-foreground">
                <GraduationCap className="size-3.5 text-primary shrink-0" />
                <span className="truncate">Sinh viên (UIS)</span>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-[11px] uppercase">
              <span className="bg-card px-2 text-muted-foreground font-medium">
                hoặc
              </span>
            </div>
          </div>

          {/* Section 2: Dev Access Gate Toggle */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setShowDevGate(!showDevGate)}
              className="w-full flex items-center justify-between text-xs font-medium text-muted-foreground hover:text-foreground transition-colors py-1 cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <KeyRound className="size-3.5 text-primary" />
                <span>Chế độ Nhà phát triển (Dev Access Gate)</span>
              </span>
              {showDevGate ? (
                <ChevronUp className="size-3.5" />
              ) : (
                <ChevronDown className="size-3.5" />
              )}
            </button>

            {showDevGate && (
              <form
                onSubmit={handleDevSubmit}
                className="space-y-3 pt-1 border-t border-border/60 animate-in fade-in slide-in-from-top-2 duration-200"
              >
                <div className="space-y-1.5">
                  <div className="text-xs font-medium text-foreground flex items-center justify-between">
                    <span>Mật khẩu truy cập Dev</span>
                    <button
                      type="button"
                      onClick={handleFillDefault}
                      className="text-[11px] text-primary hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <Sparkles className="size-3" />
                      Điền mặc định
                    </button>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground">
                      <Lock className="size-4" />
                    </div>
                    <Input
                      id="access-password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Nhập mật khẩu truy cập..."
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (errorMsg) setErrorMsg(null);
                      }}
                      className="pl-9 pr-10 h-9 text-xs font-mono tracking-wider focus-visible:ring-1"
                      disabled={isSubmitting || isSsoLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <EyeOff className="size-4" />
                      ) : (
                        <Eye className="size-4" />
                      )}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  variant="outline"
                  className="w-full h-9 text-xs font-medium cursor-pointer"
                  disabled={isSubmitting || isSsoLoading}
                >
                  {isSubmitting ? (
                    <>
                      <div className="size-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin mr-2" />
                      <span>Đang kiểm tra...</span>
                    </>
                  ) : (
                    <span>Xác thực Mật khẩu Dev</span>
                  )}
                </Button>
              </form>
            )}
          </div>
        </Card>

        {/* Security Footer */}
        <p className="text-center text-[11px] text-muted-foreground">
          Được bảo vệ bởi <strong>QNU Single Sign-On (OpenIddict)</strong>
          <br />
          Trường Đại học Quy Nhơn &copy; 2026. All rights reserved.
        </p>
      </div>
    </div>
  );
}

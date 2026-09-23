import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
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
  const { isAuthenticated, login } = useAuth();
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      void navigate({
        to: search.redirect?.startsWith("/") ? search.redirect : "/dashboard",
        replace: true,
      });
    }
  }, [isAuthenticated, navigate, search.redirect]);

  const handleSubmit = async (e: React.FormEvent) => {
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
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background decorative gradient circles */}
      <div className="absolute -top-40 -right-40 size-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 size-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 border border-primary/20 text-primary shadow-xs mb-1">
            <Bot className="size-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            QNU AI Platform
          </h1>
          <p className="text-xs text-muted-foreground max-w-xs mx-auto">
            Nền tảng Quản trị & Vận hành Trợ lý AI Chuyên trách
            <br />
            <span className="font-medium text-foreground/80">
              Trường Đại học Quy Nhơn
            </span>
          </p>
        </div>

        {/* Login Card */}
        <Card className="p-6 border border-border shadow-xl bg-card/90 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border">
              <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                <KeyRound className="size-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-foreground">
                  Xác Thực Truy Cập Nền Tảng
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  Nhập mật khẩu quản trị để bắt đầu phiên làm việc
                </p>
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2 animate-in fade-in duration-200">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <div className="flex-1 font-medium">{errorMsg}</div>
              </div>
            )}

            <div className="space-y-1.5">
              <div className="text-xs font-medium text-foreground flex items-center justify-between">
                <span>Mật khẩu quản trị</span>
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
                  className="pl-9 pr-10 h-10 text-sm font-mono tracking-wider focus-visible:ring-1"
                  autoFocus
                  disabled={isSubmitting}
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
              <p className="text-[11px] text-muted-foreground flex items-center gap-1.5 pt-1">
                <ShieldCheck className="size-3.5 text-emerald-500" />
                Phiên làm việc được bảo vệ bằng HttpOnly Cookie
              </p>
            </div>

            <Button
              type="submit"
              className="w-full h-10 text-sm font-semibold flex items-center justify-center gap-2 cursor-pointer"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <div className="size-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  Đang xác thực...
                </>
              ) : (
                <>
                  Truy Cập Nền Tảng
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </form>
        </Card>

        {/* Footer */}
        <p className="text-center text-[11px] text-muted-foreground">
          QNU AI Platform &copy; 2026 Trường Đại học Quy Nhơn. All rights
          reserved.
        </p>
      </div>
    </div>
  );
}

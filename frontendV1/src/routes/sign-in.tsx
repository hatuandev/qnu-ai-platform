import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { LogIn, ShieldCheck } from "lucide-react";
import { useEffect } from "react";
import { z } from "zod";
import { useAuth } from "@/app/auth";
import { Button } from "@/components/ui/button";

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
  const { error, isAuthenticated, isDemoMode, isLoading, signIn } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      void navigate({
        to: search.redirect?.startsWith("/") ? search.redirect : "/dashboard",
        replace: true,
      });
    }
  }, [isAuthenticated, navigate, search.redirect]);

  if (isAuthenticated) return null;

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-10">
      <section className="w-full max-w-md rounded-lg border bg-background p-6 sm:p-8">
        <div className="mb-8 space-y-3">
          <div className="flex size-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ShieldCheck className="size-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">QNU KTX</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              Đăng nhập
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Đăng nhập qua hệ thống SSO để tiếp tục vào khu vực quản trị.
            </p>
          </div>
        </div>
        {error ? (
          <p className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            {error.message}
          </p>
        ) : null}
        <Button
          className="w-full"
          disabled={isLoading || isDemoMode}
          onClick={() => signIn(search.redirect)}
        >
          <LogIn />
          {isLoading ? "Đang kiểm tra..." : "Đăng nhập bằng SSO"}
        </Button>
        {isDemoMode ? (
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Chế độ demo đang bật. Tắt <code>VITE_AUTH_MODE=demo</code> để dùng
            SSO thật.
          </p>
        ) : null}
      </section>
    </main>
  );
}

import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/access-denied")({
  component: AccessDeniedPage,
});

function AccessDeniedPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-10">
      <section className="w-full max-w-md rounded-lg border bg-background p-6 sm:p-8">
        <ShieldAlert className="size-6 text-destructive" />
        <h1 className="mt-4 text-xl font-semibold">Không có quyền truy cập</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Tài khoản hiện tại không được cấp quyền truy cập khu vực này.
        </p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/dashboard">
            <ArrowLeft />
            Về bảng điều khiển
          </Link>
        </Button>
      </section>
    </main>
  );
}

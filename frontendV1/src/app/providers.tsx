import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/app/auth";
import { V1AuthProvider } from "@/app/auth/v1";
import { queryClient } from "@/app/query-client";
import { ThemeProvider } from "@/app/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { CompilationActivityProvider } from "@/features/knowledge/compilation-activity";
import { RbacProvider } from "@/rbac/context";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          {/* KTX demo identity (template screens) and the real v1 actor are
              deliberately separate: neither can grant the other's permissions. */}
          <V1AuthProvider>
            <TooltipProvider delayDuration={250}>
              <RbacProvider>
                <CompilationActivityProvider>
                  {children}
                </CompilationActivityProvider>
                <Toaster richColors position="bottom-right" />
              </RbacProvider>
            </TooltipProvider>
          </V1AuthProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/app/auth";
import { queryClient } from "@/app/query-client";
import { ThemeProvider } from "@/app/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RbacProvider } from "@/rbac/context";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <TooltipProvider delayDuration={250}>
            <RbacProvider>
              {children}
              <Toaster richColors position="bottom-right" />
            </RbacProvider>
          </TooltipProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

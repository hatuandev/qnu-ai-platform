import { QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { AppNotifications } from "@/components/ui/app-notifications";
import { TooltipProvider } from "@/components/ui/tooltip";
import { queryClient } from "@/lib/query-client";
import { useUiStore } from "@/lib/ui-store";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const theme = useUiStore((s) => s.theme);

  useEffect(() => {
    const isDark =
      theme === "dark" ||
      (theme === "system" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.classList.toggle("dark", isDark);
  }, [theme]);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={250}>
        {children}
        <AppNotifications />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

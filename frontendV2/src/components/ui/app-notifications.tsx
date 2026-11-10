import { Toaster } from "sonner";
import { useUiStore } from "@/lib/ui-store";

export function AppNotifications() {
  const theme = useUiStore((s) => s.theme);
  return (
    <Toaster
      theme={theme}
      richColors
      position="top-right"
      offset={72}
      mobileOffset={72}
    />
  );
}

import { useLocation } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { isV1Route } from "@/app/api/v1/endpoints";
import { TemplateNotice } from "@/components/admin/template-notice";
import { V1LiveNotice } from "@/components/admin/v1-live-notice";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/layouts/app-sidebar";
import { CommandMenu } from "@/layouts/command-menu";
import { Topbar } from "@/layouts/topbar";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const [commandOpen, setCommandOpen] = useState(false);
  const pathname = useLocation({ select: (location) => location.pathname });
  const isQnuV1 = isV1Route(pathname);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen((current) => !current);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <Topbar onOpenCommand={() => setCommandOpen(true)} />
        <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 sm:py-7 lg:px-8">
          {/* Two different truths: v1 screens call backendV1, KTX screens are
              still the copied template and their API stays blocked. */}
          {isQnuV1 ? <V1LiveNotice /> : <TemplateNotice />}
          {children}
        </main>
      </SidebarInset>
      <CommandMenu open={commandOpen} onOpenChange={setCommandOpen} />
    </SidebarProvider>
  );
}

import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { AppSidebar } from "@/layouts/app-sidebar";
import { CommandMenu } from "@/layouts/command-menu";
import { Topbar } from "@/layouts/topbar";
import { cn } from "@/lib/utils";
import * as React from "react";

export type LayoutVariant = "standard" | "wide" | "full-bleed";

interface AdminShellProps {
  children: React.ReactNode;
  currentPath: string;
  onNavigate: (path: string) => void;
  backendOnline?: boolean;
  layoutVariant?: LayoutVariant;
}

export function getLayoutVariant(pathname: string): LayoutVariant {
  // Full-bleed: Canvas studio, Workflows builder, OCR lab split-screen & verification studio, Chat playground, Conversations desk
  if (
    pathname === "/canvas" ||
    pathname.startsWith("/canvas/") ||
    (pathname.startsWith("/workflows/") && pathname !== "/workflows") ||
    pathname.startsWith("/knowledge/ocr-lab") ||
    pathname.includes("/ocr") ||
    pathname.includes("/playground") ||
    pathname.includes("/workflow") ||
    pathname.startsWith("/conversations")
  ) {
    return "full-bleed";
  }

  // Wide: Dashboard KPI overview, Runs table
  if (pathname === "/" || pathname.startsWith("/operations/runs") || pathname.startsWith("/runs")) {
    return "wide";
  }

  // Standard: Forms, Knowledge collections list/detail, Assistants list, Models, Settings
  return "standard";
}

export function AdminShell({
  children,
  currentPath,
  onNavigate,
  backendOnline = true,
  layoutVariant,
}: AdminShellProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("qnu-sidebar-open");
      return saved !== null ? saved === "true" : true;
    }
    return true;
  });

  const [mobileDrawerOpen, setMobileDrawerOpen] = React.useState(false);
  const [commandOpen, setCommandOpen] = React.useState(false);

  const toggleSidebar = () => {
    setSidebarOpen((prev) => {
      const next = !prev;
      localStorage.setItem("qnu-sidebar-open", String(next));
      return next;
    });
  };

  const handleMobileNavigate = (path: string) => {
    setMobileDrawerOpen(false);
    onNavigate(path);
  };

  const activeVariant = layoutVariant ?? getLayoutVariant(currentPath);

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      {/* 1. Collapsible Desktop Sidebar (Hidden on mobile < lg) */}
      <AppSidebar
        open={sidebarOpen}
        currentPath={currentPath}
        onNavigate={onNavigate}
        backendOnline={backendOnline}
      />

      {/* 2. Mobile Drawer (Sheet) */}
      <Sheet open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
        <SheetContent side="left" className="w-72 p-0 border-r border-border">
          <SheetTitle className="sr-only">Menu điều hướng</SheetTitle>
          <SheetDescription className="sr-only">
            Điều hướng các phân hệ của QNU AI Platform
          </SheetDescription>
          <AppSidebar
            open={true}
            isMobile={true}
            currentPath={currentPath}
            onNavigate={handleMobileNavigate}
            onCloseMobile={() => setMobileDrawerOpen(false)}
            backendOnline={backendOnline}
          />
        </SheetContent>
      </Sheet>

      {/* 3. Main Wrapper (pl-0 on mobile, shifted right on lg screens) */}
      <div
        className={cn(
          "flex min-h-screen flex-col transition-all duration-300 ease-in-out pl-0",
          sidebarOpen ? "lg:pl-64" : "lg:pl-16"
        )}
      >
        {/* Top Header */}
        <Topbar
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          onOpenCommand={() => setCommandOpen(true)}
          currentPath={currentPath}
          onNavigate={onNavigate}
          onOpenMobileDrawer={() => setMobileDrawerOpen(true)}
        />

        {/* Page Content with Layout Variants */}
        {activeVariant === "full-bleed" ? (
          <main className="flex-1 h-[calc(100vh-3.5rem)] p-0 overflow-hidden flex flex-col">
            {children}
          </main>
        ) : activeVariant === "wide" ? (
          <main className="flex-1 p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-[1600px]">{children}</div>
          </main>
        ) : (
          <main className="flex-1 p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-7xl">{children}</div>
          </main>
        )}
      </div>

      {/* 4. Global Command Palette (Ctrl + K) */}
      <CommandMenu open={commandOpen} onOpenChange={setCommandOpen} onSelectRoute={onNavigate} />
    </div>
  );
}

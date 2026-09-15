import { AppSidebar } from "@/layouts/app-sidebar";
import { CommandMenu } from "@/layouts/command-menu";
import { Topbar } from "@/layouts/topbar";
import { cn } from "@/lib/utils";
import * as React from "react";

interface AdminShellProps {
  children: React.ReactNode;
  currentPath: string;
  onNavigate: (path: string) => void;
  backendOnline?: boolean;
}

export function AdminShell({
  children,
  currentPath,
  onNavigate,
  backendOnline = true,
}: AdminShellProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("qnu-sidebar-open");
      return saved !== null ? saved === "true" : true;
    }
    return true;
  });

  const [commandOpen, setCommandOpen] = React.useState(false);

  const toggleSidebar = () => {
    setSidebarOpen((prev) => {
      const next = !prev;
      localStorage.setItem("qnu-sidebar-open", String(next));
      return next;
    });
  };

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      {/* 1. Collapsible Sidebar */}
      <AppSidebar
        open={sidebarOpen}
        currentPath={currentPath}
        onNavigate={onNavigate}
        backendOnline={backendOnline}
      />

      {/* 2. Main Wrapper (Shifted right according to sidebar width) */}
      <div
        className={cn(
          "flex min-h-screen flex-col transition-all duration-300 ease-in-out",
          sidebarOpen ? "pl-64" : "pl-16"
        )}
      >
        {/* Top Header */}
        <Topbar
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          onOpenCommand={() => setCommandOpen(true)}
          currentPath={currentPath}
        />

        {/* Page Content */}
        <main className="flex-1 p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>

      {/* 3. Global Command Palette (Ctrl + K) */}
      <CommandMenu open={commandOpen} onOpenChange={setCommandOpen} onSelectRoute={onNavigate} />
    </div>
  );
}

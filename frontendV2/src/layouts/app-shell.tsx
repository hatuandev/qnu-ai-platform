import type React from "react";
import { BackgroundTasksBar } from "@/components/knowledge/background-tasks-bar";
import { AppSidebar } from "./app-sidebar";
import { AppTopbar } from "./app-topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground antialiased">
      {/* Sidebar */}
      <div className="hidden md:flex shrink-0">
        <AppSidebar />
      </div>

      {/* Main Container */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <AppTopbar />

        {/* Content Viewport */}
        <main className="flex-1 overflow-y-auto">{children}</main>

        {/* Global Background Tasks Bar */}
        <BackgroundTasksBar />
      </div>
    </div>
  );
}

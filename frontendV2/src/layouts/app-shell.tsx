import type React from "react";
import { AppSidebar } from "./app-sidebar";
import { AppTopbar } from "./app-topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground antialiased">
      {/* Sidebar */}
      <AppSidebar />

      {/* Main Container */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <AppTopbar />

        {/* Content Viewport */}
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

import { EmptyState } from "@/components/admin/empty-state";
import { ThemeProvider } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { AdminShell } from "@/layouts/admin-shell";
import { queryClient } from "@/lib/query-client";
import { DashboardPage } from "@/pages/dashboard-page";
import { LoginPage } from "@/pages/login-page";
import { QueryClientProvider } from "@tanstack/react-query";
import { Network } from "lucide-react";
import { Suspense, lazy, useCallback, useEffect, useState } from "react";

const AssistantsPage = lazy(() =>
  import("@/pages/assistants-page").then((m) => ({ default: m.AssistantsPage }))
);
const KnowledgePage = lazy(() =>
  import("@/pages/knowledge-page").then((m) => ({ default: m.KnowledgePage }))
);
const AssistantCreatePage = lazy(() =>
  import("@/pages/assistant-create-page").then((m) => ({ default: m.AssistantCreatePage }))
);
const AssistantDetailPage = lazy(() =>
  import("@/pages/assistant-detail-page").then((m) => ({ default: m.AssistantDetailPage }))
);
const ChannelsPage = lazy(() =>
  import("@/pages/channels-page").then((m) => ({ default: m.ChannelsPage }))
);
const ChatStudioPage = lazy(() =>
  import("@/pages/chat-studio-page").then((m) => ({ default: m.ChatStudioPage }))
);
const ConversationsPage = lazy(() =>
  import("@/pages/conversations-page").then((m) => ({ default: m.ConversationsPage }))
);
const DAGCanvasPage = lazy(() =>
  import("@/pages/dag-canvas-page").then((m) => ({ default: m.DAGCanvasPage }))
);
const DesignSystemPage = lazy(() =>
  import("@/pages/design-system-page").then((m) => ({ default: m.DesignSystemPage }))
);
const DeveloperPage = lazy(() =>
  import("@/pages/developer-page").then((m) => ({ default: m.DeveloperPage }))
);
const DocumentTypeDetailPage = lazy(() =>
  import("@/pages/document-type-detail-page").then((m) => ({ default: m.DocumentTypeDetailPage }))
);
const DocumentTypesPage = lazy(() =>
  import("@/pages/document-types-page").then((m) => ({ default: m.DocumentTypesPage }))
);
const EvaluationPage = lazy(() =>
  import("@/pages/evaluation-page").then((m) => ({ default: m.EvaluationPage }))
);
const ModelOpsPage = lazy(() =>
  import("@/pages/modelops-page").then((m) => ({ default: m.ModelOpsPage }))
);
const NodeCatalogPage = lazy(() =>
  import("@/pages/node-catalog-page").then((m) => ({ default: m.NodeCatalogPage }))
);
const RunsPage = lazy(() => import("@/pages/runs-page").then((m) => ({ default: m.RunsPage })));
const ScanStudioPage = lazy(() =>
  import("@/pages/scan-studio-page").then((m) => ({ default: m.ScanStudioPage }))
);
const ToolsPage = lazy(() => import("@/pages/tools-page").then((m) => ({ default: m.ToolsPage })));
const WorkflowsPage = lazy(() =>
  import("@/pages/workflows-page").then((m) => ({ default: m.WorkflowsPage }))
);

interface BackendStatus {
  status: "idle" | "loading" | "online" | "offline";
  service?: string;
  version?: string;
  timestamp?: string;
  error?: string;
}

function AppContent() {
  const [currentPath, setCurrentPath] = useState<string>(() => {
    if (typeof window !== "undefined" && window.location.pathname) {
      return window.location.pathname;
    }
    return "/";
  });
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ status: "idle" });
  const { isAuthenticated, isLoading } = useAuth();

  const handleNavigate = useCallback((path: string) => {
    const target = new URL(path, window.location.origin);
    setCurrentPath(target.pathname);
    if (
      `${window.location.pathname}${window.location.search}` !==
      `${target.pathname}${target.search}`
    ) {
      window.history.pushState(null, "", `${target.pathname}${target.search}`);
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || "/");
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const checkBackendHealth = useCallback(async () => {
    setBackendStatus({ status: "loading" });
    try {
      const res = await fetch("/health/live", { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        setBackendStatus({
          status: "online",
          service: data.service || "qnu-ai-platform",
          version: data.version || "0.1.0",
          timestamp: new Date().toLocaleTimeString(),
        });
      } else {
        setBackendStatus({
          status: "offline",
          error: `HTTP ${res.status}: Backend phản hồi mã lỗi`,
        });
      }
    } catch (_err) {
      setBackendStatus({
        status: "offline",
        error: "Không thể kết nối Backend (Port 8001 đang tắt hoặc chưa khởi chạy)",
      });
    }
  }, []);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  const renderContent = () => {
    // 1. Dashboard
    if (currentPath === "/") {
      return <DashboardPage onNavigate={handleNavigate} />;
    }

    // 2. Assistant administration
    if (currentPath === "/assistants") {
      return <AssistantsPage onNavigate={handleNavigate} />;
    }
    if (currentPath === "/assistants/new") {
      return <AssistantCreatePage onNavigate={handleNavigate} />;
    }
    if (currentPath.startsWith("/assistants/")) {
      return <AssistantDetailPage currentPath={currentPath} onNavigate={handleNavigate} />;
    }

    // 3. Studio Chat Toàn Năng (SSE)
    if (currentPath === "/chat") {
      return <ChatStudioPage />;
    }

    // 4. Hội Thoại & Handoff
    if (currentPath === "/conversations") {
      return <ConversationsPage />;
    }

    // 5. Kênh & Mã Nhúng Web Widget
    if (currentPath === "/channels") {
      return <ChannelsPage />;
    }

    // 6. Lịch Sử Thực Thi DAG Runs
    if (currentPath === "/runs" || currentPath.startsWith("/runs/")) {
      return (
        <RunsPage
          currentPath={currentPath}
          onNavigate={handleNavigate}
          onNavigateToCanvas={() => handleNavigate("/canvas")}
        />
      );
    }

    // 7. Quản Trị Loại Văn Bản theo taxonomy Core
    if (currentPath === "/document-types") {
      return <DocumentTypesPage currentPath={currentPath} onNavigate={handleNavigate} />;
    }
    if (currentPath.startsWith("/document-types/")) {
      return <DocumentTypeDetailPage currentPath={currentPath} onNavigate={handleNavigate} />;
    }

    // 7a. Quản Trị Tri Thức
    if (currentPath === "/knowledge" || currentPath.startsWith("/knowledge/")) {
      return <KnowledgePage currentPath={currentPath} onNavigate={handleNavigate} />;
    }

    // 7b. Scan & OCR Document Intelligence Studio
    if (currentPath === "/ocr" || currentPath.startsWith("/ocr/")) {
      return <ScanStudioPage />;
    }

    // 8. Node Catalog from Core manifests
    if (currentPath === "/nodes") {
      return <NodeCatalogPage />;
    }

    // 8a. Workflows Directory (Master List View)
    if (currentPath === "/workflows") {
      return <WorkflowsPage onNavigate={handleNavigate} />;
    }

    // 9. DAG Canvas Studio & Deep Linking
    if (
      currentPath === "/canvas" ||
      currentPath.startsWith("/canvas/") ||
      currentPath.startsWith("/workflows/")
    ) {
      return (
        <DAGCanvasPage
          currentPath={currentPath}
          onNavigate={handleNavigate}
          onNavigateToChat={(code) => handleNavigate(`/chat?assistant=${encodeURIComponent(code)}`)}
        />
      );
    }

    // 10. Cổng Công Cụ Tools (UIS, Word NĐ 30, Excel Bloom)
    if (currentPath === "/tools") {
      return <ToolsPage />;
    }

    // 10. Kiểm Định Ragas TM-08
    if (currentPath === "/evaluation") {
      return <EvaluationPage onNavigateToKnowledge={() => setCurrentPath("/knowledge")} />;
    }

    // 11. Quản Trị Mô Hình & Circuit Breaker
    if (currentPath === "/models" || currentPath.startsWith("/models/")) {
      return <ModelOpsPage currentPath={currentPath} onNavigate={handleNavigate} />;
    }

    // 12. Cổng Developer & API Key
    if (currentPath === "/developer") {
      return <DeveloperPage />;
    }

    // 13. Design System Showcase
    if (currentPath === "/design-system") {
      return <DesignSystemPage />;
    }

    // Fallback View
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Phân Hệ</h1>
            <p className="text-xs text-muted-foreground mt-1">Đường dẫn: {currentPath}</p>
          </div>
          <Button size="sm" variant="outline" onClick={() => handleNavigate("/")}>
            Về Trang Chủ
          </Button>
        </div>
        <Card className="p-8">
          <EmptyState
            icon={Network}
            title={`Đang tải phân hệ: ${currentPath}`}
            description="Phân hệ này đã sẵn sàng trên QNU AI Platform."
            action={
              <Button size="sm" onClick={() => handleNavigate("/")}>
                Quay lại Bảng Điều Khiển
              </Button>
            }
          />
        </Card>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-3">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-xs text-muted-foreground font-medium">
          Đang kiểm tra phiên làm việc...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        onSuccess={() => {
          handleNavigate(currentPath === "/login" ? "/" : currentPath);
        }}
      />
    );
  }

  return (
    <AdminShell
      currentPath={currentPath}
      onNavigate={handleNavigate}
      backendOnline={backendStatus.status === "online"}
    >
      <Suspense
        fallback={
          <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span>Đang tải phân hệ...</span>
          </div>
        }
      >
        {renderContent()}
      </Suspense>
    </AdminShell>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system">
        <TooltipProvider delayDuration={0}>
          <AuthProvider>
            <AppContent />
          </AuthProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

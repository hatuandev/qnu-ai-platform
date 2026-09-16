import { EmptyState } from "@/components/admin/empty-state";
import { StatusBadge } from "@/components/admin/status-badge";
import { ThemeProvider } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AdminShell } from "@/layouts/admin-shell";
import { queryClient } from "@/lib/query-client";
import { ChannelsPage } from "@/pages/channels-page";
import { ChatStudioPage } from "@/pages/chat-studio-page";
import { ConversationsPage } from "@/pages/conversations-page";
import { DAGCanvasPage } from "@/pages/dag-canvas-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { DesignSystemPage } from "@/pages/design-system-page";
import { DeveloperPage } from "@/pages/developer-page";
import { EvaluationPage } from "@/pages/evaluation-page";
import { KnowledgePage } from "@/pages/knowledge-page";
import { ModelOpsPage } from "@/pages/modelops-page";
import { RunsPage } from "@/pages/runs-page";
import { ToolsPage } from "@/pages/tools-page";
import { QueryClientProvider } from "@tanstack/react-query";
import {
  BookOpen,
  Cpu,
  FileText,
  GraduationCap,
  MessageSquare,
  Network,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface BackendStatus {
  status: "idle" | "loading" | "online" | "offline";
  service?: string;
  version?: string;
  timestamp?: string;
  error?: string;
}

const OFFICIAL_ASSISTANTS = [
  {
    code: "admissions",
    name: "Trợ lý Tuyển sinh",
    scope: "Chỉ tiêu, mã ngành, học phí, điểm chuẩn và đề án tuyển sinh ĐH Quy Nhơn",
    icon: GraduationCap,
    category: "admissions",
    model: "gpt-4o-mini / gemini-1.5-flash",
    chunks: "42 chunks",
  },
  {
    code: "regulations",
    name: "Trợ lý Quy chế Học vụ",
    scope: "Quy chế đào tạo tín chỉ, chuẩn đầu ra, học bổng và rèn luyện sinh viên",
    icon: ShieldCheck,
    category: "regulations",
    model: "gpt-4o-mini / qwen2.5-7b",
    chunks: "128 chunks",
  },
  {
    code: "library",
    name: "Trợ lý Thư viện QNU",
    scope: "Tra cứu tài nguyên giáo trình, luận văn tốt nghiệp, tạp chí khoa học",
    icon: BookOpen,
    category: "library",
    model: "gemini-1.5-flash",
    chunks: "85 chunks",
  },
  {
    code: "drafting",
    name: "Trợ lý Soạn thảo NĐ 30",
    scope: "Hỗ trợ soạn thảo tờ trình, quyết định, công văn chuẩn thể thức văn bản hành chính",
    icon: FileText,
    category: "drafting",
    model: "gpt-4o / gemini-1.5-pro",
    chunks: "64 chunks",
  },
  {
    code: "question_bank",
    name: "Trợ lý Ngân hàng Đề thi",
    scope: "Ma trận đề thi chuẩn Bloom, câu hỏi trắc nghiệm A-B-C-D và thang điểm",
    icon: Cpu,
    category: "question_bank",
    model: "gpt-4o-mini",
    chunks: "56 chunks",
  },
];

function AppContent() {
  const [currentPath, setCurrentPath] = useState<string>(() => {
    if (typeof window !== "undefined" && window.location.pathname) {
      return window.location.pathname;
    }
    return "/";
  });
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ status: "idle" });

  const handleNavigate = useCallback((path: string) => {
    setCurrentPath(path);
    if (typeof window !== "undefined" && window.location.pathname !== path) {
      window.history.pushState(null, "", path);
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

    // 2. 05 Assistants Catalog
    if (currentPath === "/assistants") {
      return (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                05 Trợ Lý AI Chuyên Trách Chuẩn QNU
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                Danh mục Trợ lý AI tích hợp sẵn tri thức chuyên môn và luồng điều phối DAG phân
                nhánh.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => handleNavigate("/nodes")}>
                <Network className="size-3.5 mr-1" />
                <span>Xem Sơ Đồ DAG</span>
              </Button>
              <Button size="sm" onClick={() => handleNavigate("/chat")}>
                <MessageSquare className="size-3.5 mr-1" />
                <span>Thử Nghiệm Chat</span>
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {OFFICIAL_ASSISTANTS.map((asst) => {
              const Icon = asst.icon;
              return (
                <Card
                  key={asst.code}
                  className="flex flex-col justify-between hover:border-primary/50 transition-all"
                >
                  <CardHeader className="p-5 pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="size-5" />
                      </div>
                      <StatusBadge status="ready" label="Hoạt Động" />
                    </div>
                    <CardTitle className="mt-3 text-base">{asst.name}</CardTitle>
                    <CardDescription className="leading-relaxed">{asst.scope}</CardDescription>
                  </CardHeader>
                  <CardContent className="p-5 pt-0 space-y-3">
                    <div className="space-y-1.5 text-xs text-muted-foreground border-t border-border/60 pt-3">
                      <div className="flex justify-between">
                        <span>Mô hình:</span>
                        <span className="font-mono text-foreground">{asst.model}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Kho tri thức:</span>
                        <span className="text-foreground">{asst.chunks}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        variant="default"
                        size="sm"
                        className="w-full text-xs"
                        onClick={() => setCurrentPath("/chat")}
                      >
                        <MessageSquare className="size-3 mr-1" />
                        <span>Trò chuyện</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full text-xs"
                        onClick={() => setCurrentPath("/nodes")}
                      >
                        <Network className="size-3 mr-1" />
                        <span>Sơ đồ DAG</span>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      );
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
    if (currentPath === "/runs") {
      return <RunsPage onNavigateToCanvas={() => setCurrentPath("/nodes")} />;
    }

    // 7. Quản Trị Tri Thức & Loại Văn Bản
    if (currentPath === "/knowledge" || currentPath === "/document-types") {
      return <KnowledgePage />;
    }

    // 8. DAG Canvas Studio & Thư Viện Nodes
    if (currentPath === "/nodes" || currentPath === "/canvas") {
      return <DAGCanvasPage onNavigateToChat={(_code) => setCurrentPath("/chat")} />;
    }

    // 9. Cổng Công Cụ Tools (UIS, Word NĐ 30, Excel Bloom)
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

  return (
    <AdminShell
      currentPath={currentPath}
      onNavigate={handleNavigate}
      backendOnline={backendStatus.status === "online"}
    >
      {renderContent()}
    </AdminShell>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system">
        <TooltipProvider delayDuration={0}>
          <AppContent />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

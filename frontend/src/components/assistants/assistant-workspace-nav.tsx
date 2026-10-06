import { Bot, Cpu, MessageSquare, Network, Wrench } from "lucide-react";
import type * as React from "react";
import { cn } from "@/lib/utils";

export type AssistantSubView =
  | "overview"
  | "models"
  | "tools"
  | "playground"
  | "workflow"
  | "channels"
  | "quality"
  | "runs";

interface AssistantWorkspaceNavProps {
  assistantId: string;
  activeSubView: AssistantSubView;
  onNavigate?: (path: string) => void;
  onSelectSubView?: (subView: AssistantSubView) => void;
  className?: string;
}

interface WorkspaceTab {
  id: AssistantSubView;
  label: string;
  subPath: string;
  icon: React.ElementType;
}

const WORKSPACE_TABS: WorkspaceTab[] = [
  {
    id: "overview",
    label: "Cấu hình",
    subPath: "",
    icon: Bot,
  },
  {
    id: "models",
    label: "Mô hình & An toàn",
    subPath: "/models",
    icon: Cpu,
  },
  {
    id: "tools",
    label: "Công cụ & Quản trị",
    subPath: "/tools",
    icon: Wrench,
  },
  {
    id: "workflow",
    label: "Sơ đồ DAG",
    subPath: "/workflow",
    icon: Network,
  },
  {
    id: "playground",
    label: "Thử nghiệm",
    subPath: "/playground",
    icon: MessageSquare,
  },
];

export function AssistantWorkspaceNav({
  assistantId,
  activeSubView,
  onNavigate,
  onSelectSubView,
  className,
}: AssistantWorkspaceNavProps) {
  const handleTabClick = (tab: WorkspaceTab) => {
    if (onSelectSubView) {
      onSelectSubView(tab.id);
    } else if (onNavigate) {
      const targetPath = `/assistants/${encodeURIComponent(assistantId)}${tab.subPath}`;
      onNavigate(targetPath);
    }
  };

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 overflow-x-auto border-b border-border pb-2.5 pt-1 text-xs select-none scrollbar-none",
        className,
      )}
    >
      {WORKSPACE_TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeSubView === tab.id;

        return (
          <button
            type="button"
            key={tab.id}
            onClick={() => handleTabClick(tab)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-md px-3 py-1.5 font-medium transition-all duration-150 cursor-pointer",
              isActive
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="size-3.5" />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

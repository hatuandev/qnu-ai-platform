import { cn } from "@/lib/utils";
import { Bot, Cpu, Network, Wrench } from "lucide-react";
import type * as React from "react";

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
  onNavigate: (path: string) => void;
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
    label: "Thông tin & Tri thức",
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
    label: "Quy trình & Công cụ",
    subPath: "/tools",
    icon: Wrench,
  },
  {
    id: "workflow",
    label: "Sơ đồ DAG Studio",
    subPath: "/workflow",
    icon: Network,
  },
];

export function AssistantWorkspaceNav({
  assistantId,
  activeSubView,
  onNavigate,
  className,
}: AssistantWorkspaceNavProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 overflow-x-auto border-b border-border pb-2.5 pt-1 text-xs select-none scrollbar-none",
        className
      )}
    >
      {WORKSPACE_TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeSubView === tab.id;
        const targetPath = `/assistants/${encodeURIComponent(assistantId)}${tab.subPath}`;

        return (
          <button
            type="button"
            key={tab.id}
            onClick={() => onNavigate(targetPath)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-md px-3 py-1.5 font-medium transition-all duration-150",
              isActive
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
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

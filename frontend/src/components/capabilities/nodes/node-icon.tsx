import {
  Database,
  FileOutput,
  GitBranch,
  HelpCircle,
  LogIn,
  Network,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";

interface NodeCategoryIconProps {
  category: string;
  className?: string;
}

export function NodeCategoryIcon({
  category,
  className = "size-4",
}: NodeCategoryIconProps) {
  switch (category.toLowerCase()) {
    case "input":
      return <LogIn className={className} aria-hidden="true" />;
    case "ai":
      return <Sparkles className={className} aria-hidden="true" />;
    case "knowledge":
      return <Database className={className} aria-hidden="true" />;
    case "routing":
      return <GitBranch className={className} aria-hidden="true" />;
    case "control":
      return <ShieldCheck className={className} aria-hidden="true" />;
    case "interaction":
      return <HelpCircle className={className} aria-hidden="true" />;
    case "tool":
      return <Wrench className={className} aria-hidden="true" />;
    case "output":
      return <FileOutput className={className} aria-hidden="true" />;
    default:
      return <Network className={className} aria-hidden="true" />;
  }
}

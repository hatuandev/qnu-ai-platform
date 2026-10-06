import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { IngestionTask } from "@/types";
import { Terminal } from "lucide-react";

interface TaskLogDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: IngestionTask | null;
}

export function TaskLogDialog({ open, onOpenChange, task }: TaskLogDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-slate-950 text-slate-100 font-mono text-xs">
        <DialogHeader>
          <DialogTitle className="text-sm font-mono text-emerald-400 flex items-center gap-2">
            <Terminal className="size-4" />
            <span>Worker Log: {task?.worker_name}</span>
          </DialogTitle>
        </DialogHeader>
        <pre className="p-4 bg-slate-900 rounded border border-slate-800 text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap">
          {task?.log_output || "[INFO] Tác vụ đã thực thi thành công không có cảnh báo."}
        </pre>
      </DialogContent>
    </Dialog>
  );
}

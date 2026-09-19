import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Settings } from "lucide-react";

interface CollectionConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  configName: string;
  setConfigName: (name: string) => void;
  configDescription: string;
  setConfigDescription: (desc: string) => void;
  isSaving: boolean;
  onSave: () => void;
}

export function CollectionConfigDialog({
  open,
  onOpenChange,
  configName,
  setConfigName,
  configDescription,
  setConfigDescription,
  isSaving,
  onSave,
}: CollectionConfigDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md text-xs">
        <DialogHeader>
          <DialogTitle className="text-sm font-bold flex items-center gap-2">
            <Settings className="size-4 text-primary" />
            <span>Cấu hình kho tri thức</span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="space-y-1.5">
            <label
              htmlFor="config-coll-name"
              className="text-xs font-semibold text-foreground block"
            >
              Tên kho
            </label>
            <Input
              id="config-coll-name"
              value={configName}
              onChange={(e) => setConfigName(e.target.value)}
              className="h-9 text-xs"
              placeholder="Tên bộ sưu tập tri thức"
            />
          </div>
          <div className="space-y-1.5">
            <label
              htmlFor="config-coll-desc"
              className="text-xs font-semibold text-foreground block"
            >
              Mô tả
            </label>
            <Input
              id="config-coll-desc"
              value={configDescription}
              onChange={(e) => setConfigDescription(e.target.value)}
              className="h-9 text-xs"
              placeholder="Mô tả ngắn về kho tri thức"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Hủy bỏ
            </Button>
            <Button size="sm" className="h-8 text-xs" onClick={onSave} disabled={isSaving}>
              {isSaving ? "Đang lưu..." : "Lưu cấu hình"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

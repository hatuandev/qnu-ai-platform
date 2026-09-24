import { Copy, Loader2 } from "lucide-react";
import * as React from "react";
import { Field } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface AssistantCloneDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  originalName: string;
  initialCode: string;
  initialName: string;
  initialDescription: string;
  initialCollectionId: string;
  onConfirm: (data: {
    code: string;
    name: string;
    description: string;
    collectionId: string;
    forkWorkflow?: boolean;
  }) => void;
  isPending: boolean;
}

export function AssistantCloneDialog({
  open,
  onOpenChange,
  originalName,
  initialCode,
  initialName,
  initialDescription,
  initialCollectionId,
  onConfirm,
  isPending,
}: AssistantCloneDialogProps) {
  const [code, setCode] = React.useState(initialCode);
  const [name, setName] = React.useState(initialName);
  const [description, setDescription] = React.useState(initialDescription);
  const [collectionId, setCollectionId] = React.useState(initialCollectionId);
  const [forkWorkflow, setForkWorkflow] = React.useState(true);

  React.useEffect(() => {
    if (open) {
      setCode(initialCode);
      setName(initialName);
      setDescription(initialDescription);
      setCollectionId(initialCollectionId);
      setForkWorkflow(true);
    }
  }, [open, initialCode, initialName, initialDescription, initialCollectionId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim() || !name.trim()) return;
    onConfirm({
      code: code.trim(),
      name: name.trim(),
      description: description.trim(),
      collectionId: collectionId.trim(),
      forkWorkflow,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md sm:max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <Copy className="size-4 text-primary" />
              Nhân Bản Trợ Lý AI
            </DialogTitle>
            <DialogDescription className="text-xs">
              Tạo một bản sao độc lập từ Trợ lý{" "}
              <strong className="text-foreground">{originalName}</strong> với
              đầy đủ 7 lớp cấu hình.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 text-xs">
            <Field
              label="Mã định danh mới (Unique Code)"
              required
              hint="Viết liền, không dấu, dùng dấu gạch dưới"
            >
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="vd: ast_tuyensinh_2026_copy"
                className="font-mono text-xs"
                required
              />
            </Field>

            <Field label="Tên Trợ lý mới" required>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="vd: Trợ lý Tuyển sinh 2026 (Bản sao)"
                required
              />
            </Field>

            <Field label="Mô tả nhiệm vụ">
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Mô tả phạm vi hỗ trợ của bản sao..."
              />
            </Field>

            <div className="rounded-lg border p-3 bg-muted/20 space-y-1.5">
              <label className="flex items-center gap-2 font-medium cursor-pointer text-foreground select-none">
                <Checkbox
                  checked={forkWorkflow}
                  onCheckedChange={(checked) =>
                    setForkWorkflow(checked === true)
                  }
                />
                <span>Tách quy trình xử lý riêng (Fork Private Workflow)</span>
              </label>
              <p className="text-[11px] text-muted-foreground pl-6 leading-relaxed">
                Khuyến nghị bật: Trợ lý bản sao sẽ sở hữu một bản sao Workflow
                độc lập, cho phép tùy biến luồng DAG mà không ảnh hưởng đến trợ
                lý gốc.
              </p>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Hủy bỏ
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-8 text-xs gap-1.5"
              disabled={isPending || !code.trim() || !name.trim()}
            >
              {isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Copy className="size-3.5" />
              )}
              {isPending ? "Đang nhân bản..." : "Xác nhận nhân bản"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

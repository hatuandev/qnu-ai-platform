import { Key, Plus } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateAppApiKeyMutation } from "@/features/modelops/queries";
import type { AppApiKeySecretResponse } from "@/features/modelops/types";

interface AssistantOption {
  id: string;
  name: string;
}

interface CreateKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  assistants: AssistantOption[];
  onSuccess: (data: AppApiKeySecretResponse) => void;
}

export function CreateKeyDialog({
  open,
  onOpenChange,
  workspaceId,
  assistants,
  onSuccess,
}: CreateKeyDialogProps) {
  const [appName, setAppName] = React.useState("");
  const [name, setName] = React.useState("");
  const [allowAllAssistants, setAllowAllAssistants] = React.useState(true);
  const [selectedAssistantIds, setSelectedAssistantIds] = React.useState<
    string[]
  >([]);
  const [rpm, setRpm] = React.useState("60");
  const [rpd, setRpd] = React.useState("10000");
  const [expiresInDays, setExpiresInDays] = React.useState<string>("60");

  const createMutation = useCreateAppApiKeyMutation(workspaceId, onSuccess);

  // Reset form when dialog opens
  React.useEffect(() => {
    if (open) {
      setAppName("");
      setName("");
      setAllowAllAssistants(true);
      setSelectedAssistantIds([]);
      setRpm("60");
      setRpd("10000");
      setExpiresInDays("60");
    }
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appName.trim()) {
      toast.error("Vui lòng nhập tên ứng dụng.");
      return;
    }
    if (!name.trim()) {
      toast.error("Vui lòng nhập tên khóa API.");
      return;
    }
    if (!allowAllAssistants && selectedAssistantIds.length === 0) {
      toast.error("Chọn ít nhất một trợ lý được phép gọi.");
      return;
    }

    const payload = {
      app_name: appName.trim(),
      name: name.trim(),
      allow_all_assistants: allowAllAssistants,
      idempotency_key: crypto.randomUUID(),
      allowed_assistant_ids: allowAllAssistants
        ? undefined
        : selectedAssistantIds,
      rate_limit_rpm: Number.parseInt(rpm, 10) || 60,
      rate_limit_rpd: Number.parseInt(rpd, 10) || 10000,
      expires_in_days:
        expiresInDays === "never" ? null : Number.parseInt(expiresInDays, 10),
    };

    try {
      await createMutation.mutateAsync(payload);
      toast.success("Tạo khóa API thành công!");
      onOpenChange(false);
    } catch (err: unknown) {
      toast.error((err as Error)?.message || "Không thể tạo khóa API.");
    }
  };

  const toggleAssistant = (id: string) => {
    setSelectedAssistantIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2 text-primary">
            <Key className="size-4" />
            <DialogTitle className="text-base">
              Tạo Khóa API Ứng Dụng
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Cấp quyền truy cập OpenAI Gateway cho hệ thống bên ngoài gọi trợ lý
            trong workspace này.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2 text-xs">
          {/* App Name */}
          <div className="space-y-1.5">
            <Label htmlFor="app_name" className="text-xs font-medium">
              Tên ứng dụng / Hệ thống gọi{" "}
              <span className="text-destructive">*</span>
            </Label>
            <Input
              id="app_name"
              placeholder="VD: Cổng Tuyển Sinh Web, LMS Trường, Chatbot Zalo..."
              value={appName}
              onChange={(e) => setAppName(e.target.value)}
              className="h-8 text-xs"
              required
            />
            <p className="text-[11px] text-muted-foreground">
              Mỗi ứng dụng có một danh tính máy riêng biệt trong đơn vị.
            </p>
          </div>

          {/* Key Name */}
          <div className="space-y-1.5">
            <Label htmlFor="key_name" className="text-xs font-medium">
              Tên khóa <span className="text-destructive">*</span>
            </Label>
            <Input
              id="key_name"
              placeholder="VD: Khóa Production 2026, Khóa Test Dev..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-8 text-xs"
              required
            />
          </div>

          {/* Assistant Scope */}
          <div className="space-y-2 rounded-lg border border-border bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold">
                Phạm vi trợ lý được phép gọi
              </Label>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="allow_all"
                  checked={allowAllAssistants}
                  onCheckedChange={(checked) =>
                    setAllowAllAssistants(Boolean(checked))
                  }
                />
                <label
                  htmlFor="allow_all"
                  className="text-[11px] cursor-pointer text-muted-foreground font-medium"
                >
                  Tất cả trợ lý trong workspace
                </label>
              </div>
            </div>

            {!allowAllAssistants && (
              <div className="mt-2 space-y-1.5 max-h-36 overflow-y-auto border-t pt-2">
                {assistants.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground italic">
                    Chưa có trợ lý nào trong workspace này.
                  </p>
                ) : (
                  assistants.map((ast) => (
                    <div
                      key={ast.id}
                      className="flex items-center gap-2 py-0.5"
                    >
                      <Checkbox
                        id={`ast_${ast.id}`}
                        checked={selectedAssistantIds.includes(ast.id)}
                        onCheckedChange={() => toggleAssistant(ast.id)}
                      />
                      <label
                        htmlFor={`ast_${ast.id}`}
                        className="text-xs cursor-pointer truncate"
                      >
                        {ast.name}{" "}
                        <span className="font-mono text-[10px] text-muted-foreground">
                          ({ast.id})
                        </span>
                      </label>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Rate Limits */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="rpm" className="text-xs font-medium">
                Giới hạn RPM (req/phút)
              </Label>
              <Input
                id="rpm"
                type="number"
                min="1"
                max="10000"
                value={rpm}
                onChange={(e) => setRpm(e.target.value)}
                className="h-8 text-xs font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rpd" className="text-xs font-medium">
                Giới hạn RPD (req/ngày)
              </Label>
              <Input
                id="rpd"
                type="number"
                min="1"
                max="1000000"
                value={rpd}
                onChange={(e) => setRpd(e.target.value)}
                className="h-8 text-xs font-mono"
              />
            </div>
          </div>

          {/* Expiration */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Thời hạn sử dụng</Label>
            <Select value={expiresInDays} onValueChange={setExpiresInDays}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Chọn thời hạn" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30 ngày</SelectItem>
                <SelectItem value="60">60 ngày (Khuyên dùng)</SelectItem>
                <SelectItem value="90">90 ngày</SelectItem>
                <SelectItem value="180">180 ngày (6 tháng)</SelectItem>
                <SelectItem value="365">365 ngày (1 năm)</SelectItem>
                <SelectItem value="never">Không thời hạn</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <DialogFooter className="gap-2 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={createMutation.isPending}
              className="gap-1.5"
            >
              <Plus className="size-3.5" />
              <span>
                {createMutation.isPending ? "Đang tạo..." : "Tạo khóa"}
              </span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

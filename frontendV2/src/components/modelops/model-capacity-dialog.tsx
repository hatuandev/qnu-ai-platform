import { Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useUpdateModelCapacityMutation } from "@/api/modelops/queries";
import type { ModelProvider, TokenLimits } from "@/api/modelops/types";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

function positive(value: string): number | null {
  const parsed = Number(value.trim());
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function ModelCapacityDialog({
  connectionId,
  model,
  open,
  onOpenChange,
}: {
  connectionId: string;
  model: ModelProvider | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!model) return null;
  return (
    <CapacityForm
      key={model.id}
      connectionId={connectionId}
      model={model}
      open={open}
      onOpenChange={onOpenChange}
    />
  );
}

function CapacityForm({
  connectionId,
  model,
  open,
  onOpenChange,
}: {
  connectionId: string;
  model: ModelProvider;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useUpdateModelCapacityMutation(connectionId);
  const [context, setContext] = useState("");
  const [maxInput, setMaxInput] = useState("");
  const [maxOutput, setMaxOutput] = useState("");

  useEffect(() => {
    setContext(
      model.token_limits?.context_window_tokens
        ? String(model.token_limits.context_window_tokens)
        : "",
    );
    setMaxInput(
      model.token_limits?.max_input_tokens
        ? String(model.token_limits.max_input_tokens)
        : "",
    );
    setMaxOutput(
      model.token_limits?.max_output_tokens
        ? String(model.token_limits.max_output_tokens)
        : "",
    );
  }, [model]);

  const contextTokens = positive(context);
  const inputTokens = positive(maxInput);
  const outputTokens = positive(maxOutput);
  const hasAnyValue = Boolean(contextTokens || inputTokens || outputTokens);
  const exceedsContext =
    contextTokens !== null &&
    ((inputTokens !== null && inputTokens > contextTokens) ||
      (outputTokens !== null && outputTokens > contextTokens));
  const isValid = hasAnyValue && !exceedsContext;

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!isValid) return;
    const tokenLimits: TokenLimits = {};
    if (contextTokens) tokenLimits.context_window_tokens = contextTokens;
    if (inputTokens) tokenLimits.max_input_tokens = inputTokens;
    if (outputTokens) tokenLimits.max_output_tokens = outputTokens;
    try {
      await mutation.mutateAsync({ providerId: model.id, tokenLimits });
      toast.success(`Đã lưu thông số cho "${model.model_name}"`);
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lưu thông số thất bại";
      toast.error(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Thông số model</DialogTitle>
          <DialogDescription>
            <span className="font-mono">{model.model_name}</span> · giới hạn đã
            khai báo làm trần cho QNU; bỏ trống trường chưa biết.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          <Field>
            <FieldLabel htmlFor="capacity-context">Ngữ cảnh (token)</FieldLabel>
            <Input
              id="capacity-context"
              inputMode="numeric"
              value={context}
              onChange={(event) => setContext(event.target.value)}
              placeholder="VD: 200000"
              className="h-8 text-xs font-mono"
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="capacity-input">
              Đầu vào tối đa (token, tùy chọn)
            </FieldLabel>
            <Input
              id="capacity-input"
              inputMode="numeric"
              value={maxInput}
              onChange={(event) => setMaxInput(event.target.value)}
              placeholder="Bỏ trống nếu endpoint dùng chung ngữ cảnh"
              className="h-8 text-xs font-mono"
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="capacity-output">
              Đầu ra tối đa (token)
            </FieldLabel>
            <Input
              id="capacity-output"
              inputMode="numeric"
              value={maxOutput}
              onChange={(event) => setMaxOutput(event.target.value)}
              placeholder="VD: 64000"
              className="h-8 text-xs font-mono"
            />
            <FieldDescription>
              Lưu tại đây được ghi nhận là Quản trị viên khai báo. Dùng "Đồng bộ
              từ nhà cung cấp" để lấy số do endpoint công bố.
            </FieldDescription>
          </Field>
          {exceedsContext && (
            <p className="text-[11px] text-destructive">
              Giới hạn đầu vào/đầu ra không được vượt ngữ cảnh dùng chung.
            </p>
          )}
          {!hasAnyValue && (
            <p className="text-[11px] text-muted-foreground">
              Cần khai báo ít nhất một giới hạn.
            </p>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              disabled={!isValid || mutation.isPending}
            >
              {mutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Save className="size-3.5" />
              )}
              <span>Lưu thông số</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

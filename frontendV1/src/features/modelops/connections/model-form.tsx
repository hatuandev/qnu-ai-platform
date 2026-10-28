import { useForm, useStore } from "@tanstack/react-form";
import { useEffect } from "react";
import { toast } from "sonner";
import { ErrorState } from "@/components/admin/error-state";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CAPABILITIES, CAPABILITY_LABELS, type Capability } from "../types";
import { useAddConnectionModel } from "./api";

export function ModelForm({
  connectionId,
  modelName,
  open,
  onOpenChange,
}: {
  connectionId: string;
  modelName?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const form = useForm({
    defaultValues: {
      name: modelName ?? "",
      caps: [] as Capability[],
      dimension: "",
    },
  });
  const name = useStore(form.store, (state) => state.values.name);
  const caps = useStore(form.store, (state) => state.values.caps);
  const dimension = useStore(form.store, (state) => state.values.dimension);
  const setName = (value: string) => form.setFieldValue("name", value);
  const setCaps = (value: Capability[]) => form.setFieldValue("caps", value);
  const setDimension = (value: string) =>
    form.setFieldValue("dimension", value);
  const mutation = useAddConnectionModel(connectionId);
  useEffect(() => {
    if (open) {
      form.reset({ name: modelName ?? "", caps: [], dimension: "" });
      mutation.reset();
    }
  }, [open, modelName, mutation.reset, form]);
  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle>Thêm model</ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Model dùng kết nối và API key của nhà cung cấp. Chọn chức năng theo
            model thực tế; việc có trong danh sách không đồng nghĩa đã chạy thử
            đạt.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!caps.length) {
              toast.error("Chọn ít nhất một chức năng.");
              return;
            }
            try {
              await mutation.mutateAsync({
                model_name: name.trim(),
                capabilities: caps,
                ...(dimension
                  ? { embedding_dimension: Number(dimension) }
                  : {}),
              });
              onOpenChange(false);
              toast.success("Đã thêm model.");
            } catch {
              /* Server errors are shown below. */
            }
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="connection-model-name">ID model trên server</Label>
            <Input
              id="connection-model-name"
              required
              maxLength={128}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ví dụ: qwen3.5-9b"
            />
          </div>
          <fieldset className="space-y-3">
            <legend className="mb-2 text-sm font-medium">
              Chức năng của model
            </legend>
            {CAPABILITIES.map((cap) => (
              <div key={cap} className="flex items-center gap-2">
                <Checkbox
                  id={`model-cap-${cap}`}
                  checked={caps.includes(cap)}
                  onCheckedChange={(checked) =>
                    setCaps(
                      checked ? [...caps, cap] : caps.filter((x) => x !== cap),
                    )
                  }
                />
                <Label htmlFor={`model-cap-${cap}`}>
                  {CAPABILITY_LABELS[cap]}
                </Label>
              </div>
            ))}
          </fieldset>
          {caps.includes("embedding") && (
            <div className="space-y-2">
              <Label htmlFor="model-dimension">
                Số chiều embedding (nếu đã biết)
              </Label>
              <Input
                id="model-dimension"
                type="number"
                min={1}
                max={65536}
                value={dimension}
                onChange={(e) => setDimension(e.target.value)}
              />
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Sau khi thêm, mở model để khai báo giới hạn và chạy thử trước khi
            cấp cho đơn vị.
          </p>
          {mutation.isError && <ErrorState error={mutation.error} />}
          <ResponsiveDialogFooter className="grid grid-cols-2 gap-2 border-t bg-card p-4 sm:flex sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button disabled={mutation.isPending} type="submit">
              {mutation.isPending ? "Đang thêm…" : "Thêm model"}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

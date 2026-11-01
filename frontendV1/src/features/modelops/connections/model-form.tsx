import { useForm, useStore } from "@tanstack/react-form";
import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type CapacityDraft,
  EMPTY_CAPACITY_DRAFT,
  embeddingDimensionFromDraft,
  hasManualCapacityDraft,
  tokenLimitsFromDraft,
  validateCapacityDraft,
} from "../capacity-patch";
import type { DiscoveredModel } from "../diagnostic-queries";
import { CAPABILITIES, CAPABILITY_LABELS, type Capability } from "../types";
import { buildConnectionModelPayload, useAddConnectionModel } from "./api";

export function ModelForm({
  connectionId,
  modelName,
  open,
  onOpenChange,
  discoveredModels = [],
  discoveryCheckId = null,
  discoveryError = null,
  onAdded,
}: {
  connectionId: string;
  modelName?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  discoveredModels?: DiscoveredModel[];
  discoveryCheckId?: string | null;
  discoveryError?: string | null;
  onAdded?: () => void;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: {
      name: modelName ?? "",
      caps: [] as Capability[],
      capacity: { ...EMPTY_CAPACITY_DRAFT } as CapacityDraft,
    },
  });

  const name = useStore(form.store, (state) => state.values.name);
  const caps = useStore(form.store, (state) => state.values.caps);
  const capacity = useStore(form.store, (state) => state.values.capacity);

  const setName = (value: string) => form.setFieldValue("name", value);
  const setCaps = (value: Capability[]) => form.setFieldValue("caps", value);
  const setCapacityField = <K extends keyof CapacityDraft>(
    key: K,
    value: CapacityDraft[K],
  ) => {
    setAdvancedOpen(true);
    setValidationError(null);
    form.setFieldValue("capacity", { ...capacity, [key]: value });
  };

  const mutation = useAddConnectionModel(connectionId);

  useEffect(() => {
    if (open) {
      setAdvancedOpen(false);
      setValidationError(null);
      form.reset({
        name: modelName ?? "",
        caps: [],
        capacity: { ...EMPTY_CAPACITY_DRAFT },
      });
    }
  }, [open, modelName, form.reset]);

  const matchedDiscovered = discoveredModels.find(
    (item) => item.id === name.trim(),
  );
  const hasServerMetadata = Boolean(
    matchedDiscovered &&
      (matchedDiscovered.context_window_tokens !== null ||
        matchedDiscovered.max_output_tokens !== null ||
        matchedDiscovered.embedding_dimension !== null),
  );

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle>Thêm model</ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Model dùng kết nối và API key của nhà cung cấp. Không bắt buộc nhập
            giới hạn token; nếu server chưa công bố, hệ thống sẽ dùng ngân sách
            vận hành tạm tính do backend quyết định.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5 text-sm"
          onSubmit={async (e) => {
            e.preventDefault();
            setValidationError(null);
            if (!caps.length) {
              toast.error("Chọn ít nhất một chức năng.");
              return;
            }
            const hasManual = hasManualCapacityDraft(capacity);
            if (hasManual) {
              const capacityProblem = validateCapacityDraft(capacity);
              if (capacityProblem) {
                setValidationError(capacityProblem);
                return;
              }
            }

            try {
              const manualLimits = hasManual
                ? tokenLimitsFromDraft(capacity)
                : undefined;
              const manualDim = hasManual
                ? embeddingDimensionFromDraft(capacity)
                : undefined;

              const payload = buildConnectionModelPayload({
                model_name: name.trim(),
                capabilities: caps,
                ...(hasManual
                  ? {
                      token_limits: manualLimits,
                      embedding_dimension: manualDim,
                    }
                  : hasServerMetadata && discoveryCheckId
                    ? { discovery_check_id: discoveryCheckId }
                    : {}),
              });

              await mutation.mutateAsync(payload);
              onOpenChange(false);
              onAdded?.();
              toast.success("Đã thêm model.");
            } catch (err) {
              if (err instanceof Error && !mutation.isError) {
                setValidationError(err.message);
              }
            }
          }}
        >
          {discoveryError ? (
            <Alert variant="warning" className="text-xs">
              <AlertDescription>
                Không lấy được danh sách model từ server ({discoveryError}). Bạn
                vẫn có thể nhập trực tiếp ID model tùy chỉnh bên dưới.
              </AlertDescription>
            </Alert>
          ) : null}

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
            {discoveredModels.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {discoveredModels.map((item) => (
                  <Button
                    key={item.id}
                    type="button"
                    size="sm"
                    variant={name.trim() === item.id ? "secondary" : "outline"}
                    className="h-6 px-2 text-xs font-mono"
                    onClick={() => setName(item.id)}
                  >
                    {item.id}
                  </Button>
                ))}
              </div>
            ) : null}
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

          {/* Vùng Nâng cao thu gọn mặc định */}
          <div className="rounded-lg border bg-muted/15 p-3">
            <button
              type="button"
              aria-expanded={advancedOpen}
              onClick={() => setAdvancedOpen((prev) => !prev)}
              className="flex w-full items-center justify-between gap-2 text-left text-xs font-semibold text-foreground"
            >
              <span>
                Nâng cao (Giới hạn token & thông số kỹ thuật tùy chọn)
              </span>
              <ChevronDown
                className={`size-4 text-muted-foreground transition-transform ${
                  advancedOpen ? "rotate-180" : ""
                }`}
              />
            </button>
            <p className="mt-1 text-xs text-muted-foreground">
              Không bắt buộc nhập trong chế độ thông thường. Chỉ điền khi bạn
              muốn khai báo thủ công thông số thật của model (đơn vị: token).
            </p>

            <div
              hidden={!advancedOpen}
              className={
                advancedOpen ? "mt-3 space-y-3 border-t pt-3" : "hidden"
              }
            >
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1">
                  <Label
                    htmlFor="model-context-window"
                    className="font-mono text-xs"
                  >
                    context_window_tokens
                  </Label>
                  <Input
                    id="model-context-window"
                    inputMode="numeric"
                    value={capacity.contextWindowTokens}
                    onChange={(e) =>
                      setCapacityField("contextWindowTokens", e.target.value)
                    }
                    placeholder="Chưa công bố"
                    className="h-8 font-mono text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label
                    htmlFor="model-max-input"
                    className="font-mono text-xs"
                  >
                    max_input_tokens
                  </Label>
                  <Input
                    id="model-max-input"
                    inputMode="numeric"
                    value={capacity.maxInputTokens}
                    onChange={(e) =>
                      setCapacityField("maxInputTokens", e.target.value)
                    }
                    placeholder="Chưa công bố"
                    className="h-8 font-mono text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label
                    htmlFor="model-max-output"
                    className="font-mono text-xs"
                  >
                    max_output_tokens
                  </Label>
                  <Input
                    id="model-max-output"
                    inputMode="numeric"
                    value={capacity.maxOutputTokens}
                    onChange={(e) =>
                      setCapacityField("maxOutputTokens", e.target.value)
                    }
                    placeholder="Chưa công bố"
                    className="h-8 font-mono text-xs"
                  />
                </div>
              </div>

              {caps.includes("embedding") && (
                <div className="space-y-1">
                  <Label htmlFor="model-dimension">
                    Số chiều embedding (nếu đã biết)
                  </Label>
                  <Input
                    id="model-dimension"
                    inputMode="numeric"
                    value={capacity.embeddingDimension}
                    onChange={(e) =>
                      setCapacityField("embeddingDimension", e.target.value)
                    }
                    placeholder="Chưa công bố"
                    className="h-8 font-mono text-xs"
                  />
                </div>
              )}

              {caps.includes("ocr") && (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-1">
                    <Label
                      htmlFor="model-ocr-width"
                      className="font-mono text-xs"
                    >
                      max_image_width
                    </Label>
                    <Input
                      id="model-ocr-width"
                      inputMode="numeric"
                      value={capacity.ocrMaxImageWidth}
                      onChange={(e) =>
                        setCapacityField("ocrMaxImageWidth", e.target.value)
                      }
                      className="h-8 font-mono text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label
                      htmlFor="model-ocr-height"
                      className="font-mono text-xs"
                    >
                      max_image_height
                    </Label>
                    <Input
                      id="model-ocr-height"
                      inputMode="numeric"
                      value={capacity.ocrMaxImageHeight}
                      onChange={(e) =>
                        setCapacityField("ocrMaxImageHeight", e.target.value)
                      }
                      className="h-8 font-mono text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label
                      htmlFor="model-ocr-tokens"
                      className="font-mono text-xs"
                    >
                      input_tokens_upper_bound
                    </Label>
                    <Input
                      id="model-ocr-tokens"
                      inputMode="numeric"
                      value={capacity.ocrInputTokensUpperBound}
                      onChange={(e) =>
                        setCapacityField(
                          "ocrInputTokensUpperBound",
                          e.target.value,
                        )
                      }
                      className="h-8 font-mono text-xs"
                    />
                  </div>
                  <div className="space-y-1 sm:col-span-3">
                    <Label
                      htmlFor="model-ocr-sha"
                      className="font-mono text-xs"
                    >
                      prompt_sha256
                    </Label>
                    <Input
                      id="model-ocr-sha"
                      value={capacity.ocrPromptSha256}
                      onChange={(e) =>
                        setCapacityField("ocrPromptSha256", e.target.value)
                      }
                      className="h-8 font-mono text-xs"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {validationError ? (
            <Alert variant="destructive" className="text-xs">
              <AlertDescription>{validationError}</AlertDescription>
            </Alert>
          ) : null}
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

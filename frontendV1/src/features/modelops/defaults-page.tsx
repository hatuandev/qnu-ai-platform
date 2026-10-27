import { Loader2, RefreshCw, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDefaultsQuery,
  useProvidersQuery,
  usePutDefaults,
} from "@/features/modelops/queries";
import {
  clearDefaultFor,
  defaultsPatchFor,
} from "@/features/modelops/requests";
import {
  CAPABILITIES,
  CAPABILITY_LABELS,
  type Capability,
  type ModelDefaults,
  type Provider,
} from "@/features/modelops/types";
import { cn } from "@/lib/utils";

const NONE = "__none__";

function currentProviderId(
  defaults: ModelDefaults,
  capability: Capability,
): string | null {
  switch (capability) {
    case "chat":
      return defaults.chat_provider_id;
    case "embedding":
      return defaults.embedding_provider_id;
    case "rerank":
      return defaults.rerank_provider_id;
    case "ocr":
      return defaults.ocr_provider_id;
  }
}

function currentModel(
  defaults: ModelDefaults,
  capability: Capability,
): string | null {
  switch (capability) {
    case "chat":
      return defaults.chat_model;
    case "embedding":
      return defaults.embedding_model;
    case "rerank":
      return defaults.rerank_model;
    case "ocr":
      return defaults.ocr_model;
  }
}

export function DefaultsPage() {
  const { actor } = useV1Auth();
  const defaultsQuery = useDefaultsQuery();
  const providersQuery = useProvidersQuery();
  const putDefaults = usePutDefaults();
  const [pendingCapability, setPendingCapability] = useState<Capability | null>(
    null,
  );

  const canManage = isModelAdmin(actor);
  const defaults = defaultsQuery.data;
  const providers = providersQuery.data ?? [];

  const isLoading = defaultsQuery.isLoading || providersQuery.isLoading;
  const error = defaultsQuery.error ?? providersQuery.error;

  const candidates = (capability: Capability): Provider[] =>
    providers.filter(
      (provider) =>
        provider.is_active && provider.capabilities.includes(capability),
    );

  const apply = (capability: Capability, providerId: string) => {
    setPendingCapability(capability);
    const provider = providers.find((item) => item.id === providerId);
    const payload =
      providerId === NONE || !provider
        ? clearDefaultFor(capability)
        : defaultsPatchFor(provider, capability);

    void putDefaults
      .mutateAsync(payload)
      .then(() => {
        toast.success(
          providerId === NONE
            ? `Đã bỏ mặc định ${CAPABILITY_LABELS[capability]}.`
            : `Đã đặt mặc định ${CAPABILITY_LABELS[capability]}.`,
        );
      })
      .catch((mutationError: unknown) =>
        toast.error(
          mutationError instanceof ApiProblemError
            ? mutationError.message
            : "Không lưu được model mặc định.",
        ),
      )
      .finally(() => setPendingCapability(null));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · MODELOPS"
        title="Model mặc định"
        description="Mỗi capability có đúng một provider mặc định. Model đi kèm luôn là model_name của provider đã chọn, không nhập tay. Chỉ provider đang bật và có capability đó mới chọn được."
        actions={
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            onClick={() => {
              void defaultsQuery.refetch();
              void providersQuery.refetch();
            }}
            disabled={defaultsQuery.isFetching || providersQuery.isFetching}
          >
            <RefreshCw
              className={cn(
                "size-3.5",
                (defaultsQuery.isFetching || providersQuery.isFetching) &&
                  "animate-spin",
              )}
            />
            <span>Làm mới</span>
          </Button>
        }
      />

      {error ? (
        <ErrorState
          error={error}
          onRetry={() => {
            void defaultsQuery.refetch();
            void providersQuery.refetch();
          }}
        />
      ) : isLoading || !defaults ? (
        <div className="grid gap-3">
          {[0, 1, 2, 3].map((row) => (
            <Skeleton key={row} className="h-20 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3">
          {CAPABILITIES.map((capability) => {
            const providerId = currentProviderId(defaults, capability);
            const model = currentModel(defaults, capability);
            const selected = providers.find((item) => item.id === providerId);
            const options = candidates(capability);
            const selectedUnavailable =
              providerId !== null && !selected?.is_active;
            const selectedLacksCapability =
              selected !== undefined &&
              !selected.capabilities.includes(capability);
            const busy = pendingCapability === capability;

            return (
              <Card key={capability} className="rounded-xl shadow-2xs">
                <CardContent className="grid gap-3 py-4 sm:grid-cols-[160px_1fr] sm:items-start">
                  <div>
                    <p className="text-sm font-semibold">
                      {CAPABILITY_LABELS[capability]}
                    </p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {capability}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                      <Select
                        value={providerId ?? NONE}
                        onValueChange={(value) => apply(capability, value)}
                        disabled={!canManage || busy}
                      >
                        <SelectTrigger
                          className="h-9 w-full text-xs sm:max-w-md"
                          aria-label={`Provider mặc định cho ${CAPABILITY_LABELS[capability]}`}
                        >
                          <SelectValue placeholder="Chưa đặt mặc định" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={NONE} className="text-xs">
                            Không đặt mặc định
                          </SelectItem>
                          {options.map((provider) => (
                            <SelectItem
                              key={provider.id}
                              value={provider.id}
                              className="text-xs"
                            >
                              {provider.name} · {provider.model_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {busy ? (
                        <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                      ) : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                      <span>
                        Model hiện tại:{" "}
                        {model ? (
                          <code className="font-mono text-foreground">
                            {model}
                          </code>
                        ) : (
                          "chưa đặt"
                        )}
                      </span>
                      {options.length === 0 ? (
                        <Badge variant="secondary" className="text-[10px]">
                          Không có provider đang bật cho capability này
                        </Badge>
                      ) : null}
                    </div>

                    {selectedUnavailable ? (
                      <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-[11px] leading-5">
                        <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
                        <span>
                          Mặc định đang trỏ tới provider{" "}
                          <code className="font-mono">{providerId}</code> nhưng
                          provider này không còn trong danh sách hoặc đã bị tắt.
                          Chọn provider khác hoặc bỏ mặc định.
                        </span>
                      </p>
                    ) : null}

                    {selectedLacksCapability ? (
                      <p className="text-[11px] text-destructive">
                        Provider đang đặt mặc định không khai báo capability
                        này. Backend sẽ từ chối khi ghi.
                      </p>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <p className="text-[11px] leading-5 text-muted-foreground">
        PUT chỉ gửi capability vừa đổi, các capability khác được giữ nguyên phía
        máy chủ. Thao tác ghi cần quyền ai.models.manage; trang không tự sửa gì
        khi mở.
      </p>
    </div>
  );
}

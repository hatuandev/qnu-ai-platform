import { useForm } from "@tanstack/react-form";
import { Loader2, Save, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { z } from "zod";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ExecutionHistory } from "./execution-history";
import { useProvidersQuery } from "./queries";
import {
  type PolicyResponse,
  TASKS,
  type Task,
  type Transport,
  taskCapability,
  useResilience,
  useSaveResilience,
  useTransportRegistry,
} from "./resilience-queries";
import type { Provider } from "./types";

const numeric = z.number().int().min(1).max(86400);

function PolicyForm({
  provider,
  saved,
  registry,
}: {
  provider: Provider;
  saved: PolicyResponse;
  registry: Transport[];
}) {
  const mutation = useSaveResilience(provider.id);
  const providers = useProvidersQuery();
  const [notice, setNotice] = useState("");
  const metadata = registry.find(
    (item) => item.provider_type === provider.provider_type,
  );
  const form = useForm({
    defaultValues: saved.policy,
    onSubmit: async ({ value }) => {
      setNotice("");
      try {
        await mutation.mutateAsync(value);
        setNotice("Đã lưu chính sách.");
      } catch {
        /* Query mutation renders the safe server error below. */
      }
    },
  });
  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      {saved.status === "stale" && (
        <p className="text-sm text-warning">
          Endpoint hoặc model đã đổi. Chính sách cũ đang ngừng áp dụng; kiểm tra
          và lưu lại.
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        Khi bật nhóm khóa, mỗi khóa đang gọi sẽ được giữ riêng đến khi hoàn tất.
        Chỉ lỗi 401 và 429 mới tạm nghỉ khóa và cho phép thử khóa khác trong
        cùng model.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <form.Field name="key_pool_enabled">
          {(field) => (
            <Field className="flex-row items-center justify-between rounded-md border p-3">
              <FieldLabel htmlFor="key-pool">Dùng nhóm khóa</FieldLabel>
              <Switch
                id="key-pool"
                checked={field.state.value}
                disabled={
                  mutation.isPending ||
                  !Object.keys(metadata?.protocols ?? {}).length
                }
                onCheckedChange={(checked) => {
                  field.handleChange(checked);
                  if (!checked) form.setFieldValue("max_key_attempts", 1);
                }}
              />
            </Field>
          )}
        </form.Field>
        <form.Field name="retry_owner">
          {(field) => (
            <Field>
              <FieldLabel htmlFor="retry-owner">Bên quản lý thử lại</FieldLabel>
              <Select
                value={field.state.value}
                disabled={mutation.isPending}
                onValueChange={(value) => {
                  field.handleChange(value as "qnu" | "gateway");
                  if (value === "gateway")
                    form.setFieldValue("max_key_attempts", 1);
                }}
              >
                <SelectTrigger id="retry-owner">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="qnu">QNU</SelectItem>
                  <SelectItem value="gateway">Gateway / 9router</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          )}
        </form.Field>
        <form.Subscribe
          selector={(state) =>
            [state.values.key_pool_enabled, state.values.retry_owner] as const
          }
        >
          {([pool, owner]) => (
            <form.Field
              name="max_key_attempts"
              validators={{ onChange: z.number().int().min(1).max(3) }}
            >
              {(field) => (
                <Field>
                  <FieldLabel htmlFor="key-attempts">
                    Tối đa lượt gọi
                  </FieldLabel>
                  <Input
                    id="key-attempts"
                    type="number"
                    min={1}
                    max={3}
                    value={field.state.value}
                    disabled={
                      mutation.isPending || !pool || owner === "gateway"
                    }
                    onChange={(e) => field.handleChange(Number(e.target.value))}
                    aria-invalid={field.state.meta.errors.length > 0}
                  />
                  {field.state.meta.errors.length > 0 && (
                    <FieldError>
                      Nhập số nguyên trong khoảng cho phép.
                    </FieldError>
                  )}
                </Field>
              )}
            </form.Field>
          )}
        </form.Subscribe>
        {(["auth_cooldown_seconds", "rate_cooldown_seconds"] as const).map(
          (name) => (
            <form.Field
              key={name}
              name={name}
              validators={{ onChange: numeric }}
            >
              {(field) => (
                <Field>
                  <FieldLabel htmlFor={name}>
                    {name === "auth_cooldown_seconds"
                      ? "Nghỉ khi sai khóa (giây)"
                      : "Nghỉ khi giới hạn (giây)"}
                  </FieldLabel>
                  <Input
                    id={name}
                    type="number"
                    min={1}
                    max={86400}
                    value={field.state.value}
                    disabled={mutation.isPending}
                    onChange={(e) => field.handleChange(Number(e.target.value))}
                    aria-invalid={field.state.meta.errors.length > 0}
                  />
                  {field.state.meta.errors.length > 0 && (
                    <FieldError>
                      Nhập số nguyên trong khoảng cho phép.
                    </FieldError>
                  )}
                </Field>
              )}
            </form.Field>
          ),
        )}
      </div>
      <div className="space-y-3 border-t pt-4">
        <h3 className="text-sm font-semibold">Model dự phòng</h3>
        <p className="text-sm text-muted-foreground">
          Chỉ chọn dự phòng khi model mặc định bị tắt hoặc không có khóa sẵn
          sàng, trước khi chốt tác vụ và ngân sách. Model được chọn cụ thể sẽ
          giữ nguyên. Mỗi workspace vẫn phải được cấp quyền dùng model dự phòng.
        </p>
        <p className="text-xs text-muted-foreground">
          Không đổi model embedding trong chỉ mục; không chuyển model sau khi
          OCR/Compiler đã bắt đầu. Timeout hoặc lỗi chưa rõ kết quả sẽ báo lỗi.
        </p>
        {providers.isError ? (
          <ErrorState
            error={providers.error}
            onRetry={() => void providers.refetch()}
          />
        ) : null}
        {(Object.keys(TASKS) as Task[])
          .filter(
            (task) =>
              provider.capabilities.includes(taskCapability(task)) &&
              metadata?.protocols[taskCapability(task)],
          )
          .map((task) => {
            const choices = (providers.data ?? []).filter(
              (item) =>
                item.id !== provider.id &&
                item.is_active &&
                item.capabilities.includes(taskCapability(task)) &&
                registry.find((r) => r.provider_type === item.provider_type)
                  ?.protocols[taskCapability(task)],
            );
            return (
              <form.Field key={task} name={`fallbacks.${task}`}>
                {(field) => {
                  const ids = field.state.value ?? [];
                  return (
                    <div className="space-y-2">
                      <p className="text-sm font-medium">{TASKS[task]}</p>
                      <div className="grid gap-2 lg:grid-cols-3">
                        {[0, 1, 2].map((slot) => (
                          <Select
                            key={`${task}-${slot}`}
                            value={ids[slot] ?? "__none"}
                            disabled={
                              mutation.isPending ||
                              providers.isPending ||
                              providers.isError ||
                              (slot > 0 && !ids[slot - 1])
                            }
                            onValueChange={(id) => {
                              const next = ids.slice();
                              if (id === "__none") next.splice(slot);
                              else next[slot] = id;
                              field.handleChange(next);
                              setNotice("");
                            }}
                          >
                            <SelectTrigger
                              className="w-full"
                              aria-label={`${TASKS[task]} dự phòng ${slot + 1}`}
                            >
                              <SelectValue placeholder="Không dùng" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none">Không dùng</SelectItem>
                              {ids[slot] &&
                                !choices.some((p) => p.id === ids[slot]) && (
                                  <SelectItem value={ids[slot]}>
                                    Model không còn sẵn sàng
                                  </SelectItem>
                                )}
                              {choices.map((item) => (
                                <SelectItem
                                  key={item.id}
                                  value={item.id}
                                  disabled={
                                    ids.includes(item.id) &&
                                    ids[slot] !== item.id
                                  }
                                >
                                  {item.name} · {item.model_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ))}
                      </div>
                    </div>
                  );
                }}
              </form.Field>
            );
          })}
      </div>
      {mutation.isError && <ErrorState error={mutation.error} />}
      {notice && (
        <p role="status" className="text-sm text-success">
          {notice}
        </p>
      )}
      <form.Subscribe selector={(state) => state.canSubmit}>
        {(canSubmit) => (
          <Button
            type="submit"
            size="sm"
            disabled={
              !canSubmit ||
              mutation.isPending ||
              providers.isPending ||
              providers.isError
            }
          >
            {mutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Save className="size-4" />
            )}{" "}
            Lưu chính sách
          </Button>
        )}
      </form.Subscribe>
    </form>
  );
}

export function ProviderResiliencePanel({ provider }: { provider: Provider }) {
  const { actor, sessionId } = useV1Auth();
  const query = useResilience(provider.id);
  const registry = useTransportRegistry();
  if (!isModelAdmin(actor)) return null;
  const metadata = registry.data?.find(
    (item) => item.provider_type === provider.provider_type,
  );
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ShieldCheck className="size-4" /> Khóa và dự phòng{" "}
          <Badge variant="outline">
            {query.data?.status === "configured"
              ? "Đã cấu hình"
              : query.data?.status === "stale"
                ? "Cần lưu lại"
                : "Mặc định"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : registry.isError ? (
          <ErrorState
            error={registry.error}
            onRetry={() => void registry.refetch()}
          />
        ) : !query.data || !registry.data ? (
          <Skeleton className="h-24" />
        ) : (
          <>
            <div className="space-y-1 rounded-md border bg-muted/20 p-3 text-xs text-muted-foreground">
              <p>
                Giao thức adapter:{" "}
                {Object.entries(metadata?.protocols ?? {})
                  .map(([cap, protocol]) => `${cap}: ${protocol}`)
                  .join(" · ") || "Chưa có adapter"}
              </p>
              <p>
                Responses API: {metadata?.responses_api ? "có" : "chưa hỗ trợ"}{" "}
                · Streaming: {metadata?.streaming ? "có" : "chưa hỗ trợ"}
              </p>
              <p>
                Schema đầu ra là khả năng gửi yêu cầu của adapter; cần kiểm tra
                model riêng.
              </p>
            </div>
            <PolicyForm
              key={`${provider.id}:${sessionId}:${provider.updated_at}`}
              provider={provider}
              saved={query.data}
              registry={registry.data}
            />
          </>
        )}
        <ExecutionHistory providerId={provider.id} />
      </CardContent>
    </Card>
  );
}

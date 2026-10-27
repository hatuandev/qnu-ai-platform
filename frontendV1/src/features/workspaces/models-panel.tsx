import { Cpu, Loader2, Save, ShieldAlert, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { canManageMembers, isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useProvidersQuery } from "@/features/modelops/queries";
import {
  type AllowlistDraft,
  draftFromAllowlist,
  orphanedDefaults,
  pruneOrphanedDefaults,
  sameAllowlist,
  setCapabilityDefault,
  toAllowlistInput,
  toggleProvider,
} from "@/features/workspaces/allowlist-patch";
import {
  useAllowlistQuery,
  useCallerWorkspaceRole,
  usePutAllowlist,
  usePutWorkspaceDefaults,
} from "@/features/workspaces/queries";
import { CAPABILITIES, type Capability } from "@/features/workspaces/types";

const NONE = "__none__";

export function WorkspaceModelsPanel({ workspaceId }: { workspaceId: string }) {
  const { actor } = useV1Auth();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const allowlistQuery = useAllowlistQuery(workspaceId);
  const modelAdmin = isModelAdmin(actor);
  const providersQuery = useProvidersQuery({ enabled: modelAdmin });
  const putAllowlist = usePutAllowlist(workspaceId);
  const putDefaults = usePutWorkspaceDefaults(workspaceId);

  const [prevWorkspaceId, setPrevWorkspaceId] = useState(workspaceId);
  const [draft, setDraft] = useState<AllowlistDraft | null>(null);
  const [confirmPrune, setConfirmPrune] = useState(false);

  if (prevWorkspaceId !== workspaceId) {
    setPrevWorkspaceId(workspaceId);
    setDraft(null);
    setConfirmPrune(false);
  }

  const allowlist = allowlistQuery.data;
  const baseline = allowlist ? draftFromAllowlist(allowlist) : null;
  const dirty = Boolean(draft && baseline && !sameAllowlist(draft, baseline));

  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;
  const draftRef = useRef(draft);
  draftRef.current = draft;

  useEffect(() => {
    if (!allowlist) return;
    if (!dirtyRef.current || !draftRef.current) {
      setDraft(draftFromAllowlist(allowlist));
    }
  }, [allowlist]);

  const providerMeta = useMemo(() => {
    const map = new Map<
      string,
      { name: string; capabilities: string[]; is_active: boolean }
    >();
    for (const item of allowlist?.providers ?? []) {
      map.set(item.provider_id, {
        name: item.name,
        capabilities: item.capabilities,
        is_active: item.is_active,
      });
    }
    for (const provider of providersQuery.data ?? []) {
      map.set(provider.id, {
        name: provider.name,
        capabilities: provider.capabilities,
        is_active: provider.is_active,
      });
    }
    return map;
  }, [allowlist, providersQuery.data]);

  const canEditDefaults = canManageMembers(role);
  const orphans = draft ? orphanedDefaults(draft) : [];
  const busy = putAllowlist.isPending || putDefaults.isPending;

  if (allowlistQuery.isLoading || rolePending) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (allowlistQuery.isError) {
    return (
      <ErrorState
        error={allowlistQuery.error}
        title="Không đọc được danh sách model được cấp"
        onRetry={() => void allowlistQuery.refetch()}
      />
    );
  }

  if (!draft || !allowlist) return null;

  const grantedIds = new Set(draft.providerIds);
  const availableProviders = (providersQuery.data ?? []).filter(
    (provider) => !grantedIds.has(provider.id),
  );

  const save = () => {
    if (!dirty) return;
    const next = orphans.length > 0 ? pruneOrphanedDefaults(draft) : draft;

    const mutation = modelAdmin
      ? putAllowlist.mutateAsync(toAllowlistInput(next))
      : putDefaults.mutateAsync(next.defaults);

    void mutation
      .then(() => {
        toast.success(
          modelAdmin
            ? "Đã lưu danh sách model được cấp."
            : "Đã lưu model mặc định của workspace.",
        );
        setConfirmPrune(false);
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof ApiProblemError
            ? error.message
            : "Không lưu được cấu hình model.",
        ),
      );
  };

  const requestSave = () => {
    if (orphans.length > 0) {
      setConfirmPrune(true);
      return;
    }
    save();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">
            Model được cấp cho workspace
          </h2>
          <p className="text-xs text-muted-foreground">
            Danh sách này do quản trị ModelOps cấp. Workspace admin chỉ chọn
            được model mặc định trong số provider đã được cấp.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            disabled={!dirty || busy}
            onClick={() => {
              setDraft(baseline);
            }}
          >
            Hoàn tác
          </Button>
          <Button
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            disabled={!dirty || busy || !canEditDefaults}
            title={
              canEditDefaults
                ? undefined
                : "Cần vai trò admin của workspace này để lưu cấu hình model"
            }
            onClick={requestSave}
          >
            {busy ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Save className="size-3.5" />
            )}
            <span>Lưu thay đổi</span>
          </Button>
        </div>
      </div>

      <p className="flex items-start gap-2 rounded-md border bg-muted/40 px-3 py-2 text-[11px] leading-5">
        <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
        <span>
          {modelAdmin
            ? "Bạn có ai.models.manage: lưu sẽ gọi PUT /allowed-providers và thay thế toàn bộ danh sách cấp kèm model mặc định liên quan."
            : "Bạn không có ai.models.manage: chỉ lưu được model mặc định qua PUT /model-defaults; thêm hoặc bỏ provider cần quản trị ModelOps."}
        </span>
      </p>

      <Card className="rounded-xl shadow-2xs">
        <CardContent className="space-y-3 py-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Provider được cấp ({draft.providerIds.length})
            </h3>
            {!modelAdmin ? (
              <Badge variant="outline" className="text-[10px]">
                Chỉ đọc
              </Badge>
            ) : null}
          </div>

          {draft.providerIds.length === 0 ? (
            <EmptyState
              icon={Cpu}
              title="Workspace chưa được cấp provider nào"
              description={
                modelAdmin
                  ? "Chọn provider bên dưới để cấp quyền dùng model cho workspace."
                  : "Liên hệ quản trị ModelOps để cấp provider cho workspace này."
              }
            />
          ) : (
            <ul className="divide-y rounded-lg border">
              {draft.providerIds.map((providerId) => {
                const meta = providerMeta.get(providerId);
                return (
                  <li
                    key={providerId}
                    className="flex flex-col gap-2 px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-start gap-2">
                      {modelAdmin ? (
                        <Checkbox
                          id={`granted-${providerId}`}
                          className="mt-0.5"
                          checked
                          disabled={busy}
                          onCheckedChange={() =>
                            setDraft(toggleProvider(draft, providerId, false))
                          }
                        />
                      ) : null}
                      <div>
                        {modelAdmin ? (
                          <label
                            htmlFor={`granted-${providerId}`}
                            className="text-xs font-medium"
                          >
                            {meta?.name ?? providerId}
                          </label>
                        ) : (
                          <p className="text-xs font-medium">
                            {meta?.name ?? providerId}
                          </p>
                        )}
                        <p className="font-mono text-[11px] text-muted-foreground">
                          {providerId}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-1">
                      {(meta?.capabilities ?? []).map((capability) => (
                        <Badge
                          key={capability}
                          variant="outline"
                          className="text-[10px]"
                        >
                          {capability}
                        </Badge>
                      ))}
                      {meta && !meta.is_active ? (
                        <Badge variant="warning" className="text-[10px]">
                          Provider đang tắt
                        </Badge>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {modelAdmin && availableProviders.length > 0 ? (
            <div className="space-y-2 rounded-lg border border-dashed p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                Cấp thêm provider
              </p>
              <ul className="grid gap-1.5 sm:grid-cols-2">
                {availableProviders.map((provider) => (
                  <li key={provider.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`available-${provider.id}`}
                      checked={false}
                      disabled={busy}
                      onCheckedChange={() =>
                        setDraft(toggleProvider(draft, provider.id, true))
                      }
                    />
                    <label
                      htmlFor={`available-${provider.id}`}
                      className="text-xs"
                    >
                      {provider.name}
                      <span className="ml-1 font-mono text-[11px] text-muted-foreground">
                        {provider.model_name}
                      </span>
                      {!provider.is_active ? (
                        <span className="ml-1 text-[11px] text-muted-foreground">
                          (đang tắt)
                        </span>
                      ) : null}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-xl shadow-2xs">
        <CardContent className="space-y-3 py-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Model mặc định theo capability
            </h3>
            <p className="mt-1 text-[11px] leading-5 text-muted-foreground">
              Chỉ chọn được trong số provider đã cấp và có capability tương ứng.
              Bỏ trống nghĩa là workspace không có mặc định cho capability đó.
            </p>
          </div>

          <div className="grid gap-3">
            {CAPABILITIES.map((capability) => {
              const options = draft.providerIds.filter((providerId) => {
                const meta = providerMeta.get(providerId);
                return (
                  Boolean(meta?.is_active) &&
                  (meta?.capabilities ?? []).includes(capability)
                );
              });
              const value = draft.defaults[capability] ?? NONE;
              return (
                <div
                  key={capability}
                  className="grid gap-2 sm:grid-cols-[140px_1fr] sm:items-center"
                >
                  <span className="text-xs font-medium">{capability}</span>
                  <Select
                    value={value}
                    onValueChange={(next) =>
                      setDraft(
                        setCapabilityDefault(
                          draft,
                          capability as Capability,
                          next === NONE ? null : next,
                        ),
                      )
                    }
                    disabled={!canEditDefaults || busy || options.length === 0}
                  >
                    <SelectTrigger
                      className="h-8 text-xs sm:max-w-sm"
                      aria-label={`Model mặc định cho ${capability}`}
                    >
                      <SelectValue placeholder="Chưa đặt mặc định" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE} className="text-xs">
                        Không đặt mặc định
                      </SelectItem>
                      {options.map((providerId) => (
                        <SelectItem
                          key={providerId}
                          value={providerId}
                          className="text-xs"
                        >
                          {providerMeta.get(providerId)?.name ?? providerId}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              );
            })}
          </div>

          {draft.providerIds.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">
              Chưa có provider nào được cấp nên không đặt được mặc định.
            </p>
          ) : null}
        </CardContent>
      </Card>

      {orphans.length > 0 ? (
        <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-[11px] leading-5">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          <span>
            {orphans.length} model mặc định đang trỏ tới provider không còn được
            cấp. Backend sẽ từ chối payload này, nên khi lưu các mặc định đó sẽ
            bị bỏ:{" "}
            {orphans
              .map((item) => `${item.capability} → ${item.providerId}`)
              .join(", ")}
            .
          </span>
        </p>
      ) : null}

      <ConfirmDialog
        open={confirmPrune}
        onOpenChange={(open) => {
          if (!putAllowlist.isPending) setConfirmPrune(open);
        }}
        title="Bỏ các model mặc định mồ côi?"
        description={
          <div className="space-y-2">
            <p>
              Các provider sau không còn được cấp nên model mặc định của chúng
              phải bị bỏ:
            </p>
            <ul className="list-disc pl-4 font-mono text-xs">
              {orphans.map((item) => (
                <li key={item.capability}>
                  {item.capability} → {item.providerId}
                </li>
              ))}
            </ul>
          </div>
        }
        confirmLabel="Lưu và bỏ mặc định"
        isLoading={busy}
        onConfirm={save}
      />
    </div>
  );
}

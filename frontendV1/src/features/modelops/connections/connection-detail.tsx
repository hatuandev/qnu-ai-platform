import { Link } from "@tanstack/react-router";
import { ArrowLeft, Pencil, PlugZap, Plus } from "lucide-react";
import { useState } from "react";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDiagnostics, useRunDiagnostic } from "../diagnostic-queries";
import { KeysPanel } from "../keys-panel";
import { CAPABILITY_LABELS, type Capability } from "../types";
import {
  type Connection,
  FAMILIES,
  useConnection,
  useConnectionModels,
  useSaveConnection,
} from "./api";
import { ConnectionForm } from "./connection-form";
import { ConnectionStatus } from "./connection-list";
import { ModelForm } from "./model-form";

export function ConnectionDetail({ connectionId }: { connectionId: string }) {
  const query = useConnection(connectionId);
  const modelsQuery = useConnectionModels(connectionId);
  const diagnostic = useDiagnostics(connectionId);
  const run = useRunDiagnostic(connectionId);
  const update = useSaveConnection(connectionId);
  const [edit, setEdit] = useState(false);
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState<string>();
  const connection =
    query.data && !Array.isArray(query.data) ? query.data : undefined;
  const models = modelsQuery.data ?? [];
  const latest = diagnostic.data?.checks.find((x) => x.kind === "discovery");
  const candidates =
    latest?.outcome === "ok" && latest.configuration_status !== "stale"
      ? latest.models
      : [];
  const registered = new Set(models.map((x) => x.model_name));
  if (query.isLoading) return <Skeleton className="h-64 w-full" />;
  if (query.isError || !connection)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  const toggle = () =>
    update.mutate({
      name: connection.name,
      family: connection.family,
      base_url: connection.base_url,
      timeout_seconds: connection.timeout_seconds,
      is_active: !connection.is_active,
    });
  return (
    <div className="space-y-6">
      <Button asChild size="sm" variant="ghost">
        <Link to="/modelops/providers">
          <ArrowLeft className="size-4" />
          Nhà cung cấp
        </Link>
      </Button>
      <PageHeader
        eyebrow={`MODELOPS · ${FAMILIES[connection.family]}`}
        title={connection.name}
        description="Kết nối → API key → thử kết nối → thêm model. Khóa dùng chung cho các model được phép trong nhà cung cấp này."
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={toggle}
              disabled={update.isPending}
            >
              {connection.is_active ? "Tắt nhà cung cấp" : "Bật nhà cung cấp"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEdit(true)}>
              <Pencil className="size-4" />
              Sửa
            </Button>
          </div>
        }
      />
      {update.isError && <ErrorState error={update.error} />}
      <Card className="rounded-xl shadow-2xs">
        <CardHeader>
          <CardTitle className="text-sm">Kết nối</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="break-all font-mono text-sm">{connection.base_url}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {connection.model_count} model · {connection.active_keys_count}{" "}
              khóa đang bật
            </p>
          </div>
          <div className="flex gap-2">
            <Badge variant={connection.is_active ? "success" : "secondary"}>
              {connection.is_active ? "Đang bật" : "Đang tắt"}
            </Badge>
            <ConnectionStatus status={connection.last_probe_status} />
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-5">
          <KeysPanel providerId={connectionId} />
        </CardContent>
      </Card>
      <Card className="rounded-xl shadow-2xs">
        <CardHeader className="flex flex-wrap flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm">
              Thử kết nối & lấy danh sách model
            </CardTitle>
            <p className="mt-2 text-xs text-muted-foreground">
              Gọi danh sách model để kiểm tra endpoint và khóa. Mỗi model sẽ
              được chạy thử riêng sau khi thêm.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={
              run.isPending ||
              !connection.is_active ||
              connection.active_keys_count === 0
            }
            onClick={() => run.mutate("discovery")}
          >
            <PlugZap className="size-4" />
            {run.isPending ? "Đang kiểm tra…" : "Thử kết nối"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {run.isError && <ErrorState error={run.error} />}
          {diagnostic.isError && <ErrorState error={diagnostic.error} />}
          {latest && (
            <div className="rounded-lg border p-3 text-sm">
              <ConnectionStatus
                status={
                  latest.configuration_status === "stale"
                    ? "stale"
                    : latest.outcome === "ok"
                      ? "success"
                      : latest.outcome
                }
              />
              <p className="mt-2 text-muted-foreground">{latest.detail}</p>
              {latest.http_status && (
                <p className="text-xs">
                  HTTP {latest.http_status} · {latest.latency_ms ?? "—"} ms
                </p>
              )}
            </div>
          )}
          {candidates.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {candidates.map((name) => (
                <div
                  key={name}
                  className="flex min-w-0 items-center justify-between gap-2 rounded-lg border p-3"
                >
                  <span className="break-all font-mono text-xs">{name}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={registered.has(name)}
                    onClick={() => {
                      setSelected(name);
                      setAdding(true);
                    }}
                  >
                    {registered.has(name) ? "Đã thêm" : "Thêm"}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <Card className="overflow-hidden rounded-xl shadow-2xs">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm">Model của nhà cung cấp</CardTitle>
            <p className="mt-2 text-xs text-muted-foreground">
              Khai báo chức năng, giới hạn và chạy thử model trước khi cấp cho
              đơn vị.
            </p>
          </div>
          <Button
            size="sm"
            disabled={
              !connection.is_active || connection.active_keys_count === 0
            }
            onClick={() => {
              setSelected(undefined);
              setAdding(true);
            }}
          >
            <Plus className="size-4" />
            Thêm model
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {modelsQuery.isLoading ? (
            <Skeleton className="h-24" />
          ) : modelsQuery.isError ? (
            <ErrorState error={modelsQuery.error} />
          ) : models.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">
              Chưa có model. Thử kết nối rồi chọn từ danh sách, hoặc thêm bằng
              ID model trên server.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Chức năng</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.id}>
                    <TableCell className="font-mono text-sm">
                      {model.model_name}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {model.capabilities.map((cap) => (
                          <Badge key={cap} variant="outline">
                            {CAPABILITY_LABELS[cap as Capability] ?? cap}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {model.is_active ? "Đang bật" : "Đang tắt"}
                    </TableCell>
                    <TableCell>
                      <Button asChild size="sm" variant="ghost">
                        <Link
                          to="/modelops/models/$modelId"
                          params={{ modelId: model.id }}
                        >
                          Cấu hình & chạy thử
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <ConnectionForm
        open={edit}
        onOpenChange={setEdit}
        connection={connection as Connection}
      />
      <ModelForm
        open={adding}
        onOpenChange={setAdding}
        connectionId={connectionId}
        modelName={selected}
      />
    </div>
  );
}

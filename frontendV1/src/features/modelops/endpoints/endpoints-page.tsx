import { Activity, Key, Plus, RefreshCw } from "lucide-react";
import * as React from "react";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAssistantsQuery } from "@/features/assistants/queries";
import { ApiKeysTable } from "@/features/modelops/endpoints/api-keys-table";
import { CreateKeyDialog } from "@/features/modelops/endpoints/create-key-dialog";
import { EndpointCard } from "@/features/modelops/endpoints/endpoint-card";
import { IntegrationGuide } from "@/features/modelops/endpoints/integration-guide";
import { KeySecretModal } from "@/features/modelops/endpoints/key-secret-modal";
import { RecentLogsTable } from "@/features/modelops/endpoints/recent-logs-table";
import { RevokeKeyDialog } from "@/features/modelops/endpoints/revoke-key-dialog";
import {
  useIntegrationConfigQuery,
  useIntegrationKeysQuery,
  useIntegrationLogsQuery,
} from "@/features/modelops/queries";
import type {
  AppApiKey,
  AppApiKeySecretResponse,
} from "@/features/modelops/types";
import { useWorkspacesQuery } from "@/features/workspaces/queries";
import { cn } from "@/lib/utils";

export function EndpointsPage() {
  const workspacesQuery = useWorkspacesQuery({ page: 1, pageSize: 100 });
  const workspaces = workspacesQuery.data?.items ?? [];

  const [selectedWorkspaceId, setSelectedWorkspaceId] =
    React.useState<string>("");

  // Auto-select first workspace when loaded
  React.useEffect(() => {
    if (!selectedWorkspaceId && workspaces.length > 0) {
      setSelectedWorkspaceId(workspaces[0].id);
    }
  }, [workspaces, selectedWorkspaceId]);

  // Queries scoped to selected workspace
  const configQuery = useIntegrationConfigQuery();
  const keysQuery = useIntegrationKeysQuery(selectedWorkspaceId, {
    enabled: Boolean(selectedWorkspaceId),
  });
  const assistantsQuery = useAssistantsQuery(selectedWorkspaceId);
  const logsQuery = useIntegrationLogsQuery(selectedWorkspaceId, 50, {
    enabled: Boolean(selectedWorkspaceId),
  });

  // Dialog states
  const [createOpen, setCreateOpen] = React.useState(false);
  const [revokeKey, setRevokeKey] = React.useState<AppApiKey | null>(null);
  const [secretModalData, setSecretModalData] =
    React.useState<AppApiKeySecretResponse | null>(null);

  const keys = keysQuery.data ?? [];
  const assistants = (assistantsQuery.data ?? []).map((a) => ({
    id: a.id,
    name: a.name,
  }));
  const logs = logsQuery.data ?? [];

  const handleRefreshAll = () => {
    void keysQuery.refetch();
    void logsQuery.refetch();
    void configQuery.refetch();
  };

  const activeWorkspace = workspaces.find((w) => w.id === selectedWorkspaceId);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · MODELOPS · INTEGRATION"
        title="API tích hợp"
        description="Cung cấp cổng OpenAI-compatible Gateway để các website trường, ứng dụng mobile và đối tác bên ngoài kết nối gọi trợ lý QNU."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {/* Workspace Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground hidden sm:inline">
                Đơn vị:
              </span>
              <Select
                value={selectedWorkspaceId}
                onValueChange={setSelectedWorkspaceId}
                disabled={workspacesQuery.isLoading}
              >
                <SelectTrigger className="h-8 w-[200px] text-xs">
                  <SelectValue placeholder="Chọn đơn vị..." />
                </SelectTrigger>
                <SelectContent>
                  {workspaces.map((ws) => (
                    <SelectItem key={ws.id} value={ws.id} className="text-xs">
                      {ws.name} ({ws.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={handleRefreshAll}
              disabled={keysQuery.isFetching}
            >
              <RefreshCw
                className={cn(
                  "size-3.5",
                  keysQuery.isFetching && "animate-spin",
                )}
              />
              <span>Làm mới</span>
            </Button>
          </div>
        }
      />

      {/* Block 1: Endpoint & Base URL */}
      {workspacesQuery.isError && (
        <ErrorState
          error={workspacesQuery.error}
          onRetry={() => void workspacesQuery.refetch()}
        />
      )}
      {configQuery.isError ? (
        <ErrorState
          error={configQuery.error}
          onRetry={() => void configQuery.refetch()}
        />
      ) : (
        <EndpointCard config={configQuery.data} />
      )}

      {/* Block 2: API Keys Management Table */}
      <Card className="rounded-xl border border-border bg-card shadow-2xs overflow-hidden">
        <CardHeader className="border-b bg-muted/20 pb-3 flex flex-row items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Key className="size-4 text-primary" />
              <CardTitle className="text-sm font-semibold">
                Danh Sách Khóa API Ứng Dụng
              </CardTitle>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {activeWorkspace
                ? `Quản lý khóa tích hợp thuộc đơn vị: ${activeWorkspace.name}`
                : "Vui lòng chọn đơn vị để quản lý khóa"}
            </p>
          </div>

          <Button
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            disabled={!selectedWorkspaceId}
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="size-3.5" />
            <span>Tạo khóa mới</span>
          </Button>
        </CardHeader>

        <CardContent className="p-0">
          {keysQuery.isError ? (
            <ErrorState
              error={keysQuery.error}
              onRetry={() => void keysQuery.refetch()}
            />
          ) : keysQuery.isLoading ? (
            <p className="p-4 text-sm text-muted-foreground">
              Đang tải khóa API…
            </p>
          ) : (
            <ApiKeysTable
              keys={keys}
              workspaceId={selectedWorkspaceId}
              onOpenCreate={() => setCreateOpen(true)}
              onOpenRevoke={(item) => setRevokeKey(item)}
              onRotateSuccess={(data) => setSecretModalData(data)}
            />
          )}
        </CardContent>
      </Card>

      {/* Block 3: Code Samples & Integration Guide */}
      {configQuery.data && (
        <IntegrationGuide
          config={configQuery.data}
          defaultModel={assistants.length > 0 ? assistants[0].id : "tro-ly-qnu"}
        />
      )}

      {/* Block 4: Recent Logs */}
      <Card className="rounded-xl border border-border bg-card shadow-2xs overflow-hidden">
        <CardHeader className="border-b bg-muted/20 pb-3 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="size-4 text-primary" />
            <CardTitle className="text-sm font-semibold">
              Nhật Ký Gọi API Gần Đây (Request Logs)
            </CardTitle>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono">
            {logs.length} bản ghi gần nhất
          </span>
        </CardHeader>

        <CardContent className="p-0">
          {logsQuery.isError ? (
            <ErrorState
              error={logsQuery.error}
              onRetry={() => void logsQuery.refetch()}
            />
          ) : (
            <RecentLogsTable logs={logs} isLoading={logsQuery.isLoading} />
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <CreateKeyDialog
        key={selectedWorkspaceId}
        open={createOpen}
        onOpenChange={setCreateOpen}
        workspaceId={selectedWorkspaceId}
        assistants={assistants}
        onSuccess={(data) => setSecretModalData(data)}
      />

      <RevokeKeyDialog
        keyItem={revokeKey}
        workspaceId={selectedWorkspaceId}
        onClose={() => setRevokeKey(null)}
      />

      <KeySecretModal
        data={secretModalData}
        onClose={() => setSecretModalData(null)}
      />
    </div>
  );
}

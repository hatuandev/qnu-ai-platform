import { createFileRoute } from "@tanstack/react-router";
import { Building2, Plus, RefreshCw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { useBuildingsQuery } from "@/features/buildings/api";
import { useDeleteFloor, useFloorsQuery } from "@/features/floors/api";
import { FloorFormDialog } from "@/features/floors/floor-form-dialog";
import { FloorsTable } from "@/features/floors/floors-table";
import type { Floor } from "@/features/floors/types";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  buildingId: z.string().optional().catch(undefined),
  q: z.union([z.string(), z.number()]).catch(""),
  status: z.enum(["active", "inactive"]).optional().catch(undefined),
});

export const Route = createFileRoute("/floors/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: FloorsPage,
});

function FloorsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const [formState, setFormState] = useState<
    Floor | null | "create" | undefined
  >(undefined);
  const [pendingDeactivate, setPendingDeactivate] = useState<Floor | null>(
    null,
  );
  const deleteFloor = useDeleteFloor();
  const buildingsQuery = useBuildingsQuery({ page: 1, pageSize: 50 });

  const floorsQuery = useFloorsQuery(search.buildingId);
  const selectedBuilding = buildingsQuery.data?.items.find(
    (building) => building.id === search.buildingId,
  );

  const buildingOptions = useMemo(
    () =>
      (buildingsQuery.data?.items ?? []).map((b) => ({
        value: b.id,
        label: `${b.code} — ${b.name}`,
      })),
    [buildingsQuery.data?.items],
  );

  const filteredFloors = useMemo(() => {
    const query = String(search.q).trim().toLowerCase();
    return (floorsQuery.data ?? []).filter(
      (floor) =>
        (!search.status || floor.status === search.status) &&
        (!query ||
          floor.name.toLowerCase().includes(query) ||
          String(floor.floorNumber).includes(query)),
    );
  }, [floorsQuery.data, search.q, search.status]);

  const updateSearch = useCallback(
    (changes: Partial<typeof search>) =>
      void navigate({ search: (previous) => ({ ...previous, ...changes }) }),
    [navigate],
  );

  const isFetching = buildingsQuery.isFetching || floorsQuery.isFetching;

  if (!can("ktx.floors.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / DANH MỤC"
        title="Quản lý tầng"
        description="Quản lý danh mục tầng theo từng tòa nhà và theo dõi số phòng thuộc từng tầng."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={() => {
                void buildingsQuery.refetch();
                void floorsQuery.refetch();
              }}
              disabled={isFetching}
            >
              <RefreshCw
                className={cn("size-3.5", isFetching && "animate-spin")}
              />
              <span>Làm mới</span>
            </Button>
            {search.buildingId && can("ktx.floors.create") ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setFormState("create")}
              >
                <Plus className="size-3.5" />
                <span>Thêm tầng</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* 2. Bộ chọn Tòa nhà */}
      <div className="rounded-xl border border-border/80 bg-card p-4 sm:p-5 shadow-xs">
        <div className="flex flex-col gap-2 sm:max-w-md">
          <label
            htmlFor="floor-building"
            className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider"
          >
            <Building2 className="size-3.5 text-primary" />
            Tòa nhà quản lý
          </label>
          <Combobox
            className="w-full text-xs"
            options={buildingOptions}
            value={search.buildingId ?? ""}
            searchPlaceholder="Tìm mã hoặc tên tòa nhà..."
            onValueChange={(buildingId) =>
              updateSearch({
                buildingId: buildingId || undefined,
                q: "",
                status: undefined,
              })
            }
          />
          {buildingsQuery.isError ? (
            <p className="text-xs text-destructive">
              Không thể tải danh sách tòa nhà để chọn tầng.
            </p>
          ) : selectedBuilding ? (
            <p className="text-xs text-muted-foreground">
              Đang xem tầng thuộc khối nhà:{" "}
              <span className="font-semibold text-foreground">
                {selectedBuilding.name}
              </span>{" "}
              ({selectedBuilding.code})
            </p>
          ) : null}
        </div>
      </div>

      {/* 3. Bảng danh sách Tầng */}
      {search.buildingId ? (
        <FloorsTable
          data={filteredFloors}
          allFloors={floorsQuery.data ?? []}
          isLoading={floorsQuery.isLoading}
          isError={floorsQuery.isError}
          errorMessage={
            floorsQuery.error instanceof Error
              ? floorsQuery.error.message
              : undefined
          }
          query={String(search.q)}
          status={search.status}
          hasActiveFilters={Boolean(search.q || search.status)}
          canUpdate={can("ktx.floors.update")}
          canDeactivate={can("ktx.floors.deactivate")}
          canDelete={can("ktx.floors.deactivate")}
          onRetry={() => void floorsQuery.refetch()}
          onQueryChange={(q) => updateSearch({ q })}
          onStatusChange={(status) => updateSearch({ status })}
          onResetFilters={() => updateSearch({ q: "", status: undefined })}
          onView={(floor) =>
            void navigate({
              to: "/floors/$buildingId/$floorId",
              params: { buildingId: floor.buildingId, floorId: floor.id },
            })
          }
          onEdit={setFormState}
          onDeactivate={setPendingDeactivate}
          onDelete={setPendingDeactivate}
        />
      ) : (
        <div className="flex min-h-56 items-center justify-center rounded-xl border border-dashed border-border/80 bg-card/60 p-8 text-center shadow-xs">
          <div className="flex flex-col items-center gap-2">
            <div className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Building2 className="size-6" />
            </div>
            <p className="font-semibold text-foreground text-base">
              Vui lòng chọn tòa nhà
            </p>
            <p className="text-xs text-muted-foreground max-w-sm">
              Chọn tòa nhà từ danh sách phía trên để xem và quản lý danh mục
              tầng, phòng ở.
            </p>
          </div>
        </div>
      )}

      {selectedBuilding && typeof formState !== "undefined" ? (
        <FloorFormDialog
          key={`${formState === "create" ? "create" : (formState?.id ?? "closed")}`}
          open={Boolean(formState)}
          onOpenChange={(open) => {
            if (!open) setFormState(undefined);
          }}
          buildingId={selectedBuilding.id}
          floor={formState === "create" ? null : formState}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !deleteFloor.isPending) setPendingDeactivate(null);
        }}
        title="Xác nhận xóa tầng?"
        description={
          pendingDeactivate
            ? `Bạn có chắc chắn muốn xóa tầng “${pendingDeactivate.name}” (${pendingDeactivate.floorNumber ? `Tầng ${pendingDeactivate.floorNumber}` : ""}) không? Hệ thống sẽ từ chối nếu tầng còn phòng đang hoạt động.`
            : ""
        }
        confirmLabel="Xóa tầng"
        confirmVariant="destructive"
        isLoading={deleteFloor.isPending}
        onConfirm={() => {
          if (!pendingDeactivate) return;
          void deleteFloor
            .mutateAsync({
              buildingId: pendingDeactivate.buildingId,
              id: pendingDeactivate.id,
            })
            .then(() => {
              setPendingDeactivate(null);
              toast.success("Đã xóa tầng thành công.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error ? error.message : "Không thể xóa tầng.",
              ),
            );
        }}
      />
    </div>
  );
}

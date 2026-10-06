import {
  BellRing,
  Layers3,
  Save,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  useNotifyRoomSelection,
  useRegistrationPeriodRoomRulesQuery,
  useUpdateRegistrationPeriodRoomRules,
} from "@/features/registration-periods/api";
import type {
  RegistrationPeriod,
  RegistrationPeriodRoomGenderPolicy,
  RegistrationPeriodRoomRule,
  RegistrationPeriodRoomRules,
} from "@/features/registration-periods/types";
import { cn } from "@/lib/utils";

type DraftRoomRule = Pick<
  RegistrationPeriodRoomRule,
  "roomId" | "isEnabled" | "genderPolicy"
>;

type AllocationFilter = "all" | "allocated" | "unallocated" | "unavailable";

const selectableGenderPolicies: {
  value: RegistrationPeriodRoomGenderPolicy;
  label: string;
}[] = [
  { value: "male", label: "Phòng Nam" },
  { value: "female", label: "Phòng Nữ" },
];

const roomStatusLabels: Record<string, string> = {
  available: "Đang dùng",
  full: "Đã đủ chỗ",
  maintenance: "Bảo trì",
  inactive: "Ngừng sử dụng",
};

const allocationStatusLabels: Record<
  RegistrationPeriodRoomRules["allocationStatus"],
  string
> = {
  not_allocated: "Chưa phân bổ",
  allocated: "Đã lưu cấu hình",
  selection_open: "Đang cho chọn phòng",
  selection_ended: "Đã kết thúc chọn phòng",
  finalized: "Đã chốt",
};

const allocationFilterLabels: Record<AllocationFilter, string> = {
  all: "Tất cả phòng",
  allocated: "Đã phân bổ",
  unallocated: "Chưa phân bổ",
  unavailable: "Không thể mở",
};

function allocationStatusVariant(
  status: RegistrationPeriodRoomRules["allocationStatus"],
) {
  if (status === "finalized") return "success" as const;
  if (status === "selection_open") return "info" as const;
  if (status === "not_allocated") return "warning" as const;
  return "secondary" as const;
}

function roomStatusVariant(status: string) {
  if (status === "available") return "success" as const;
  if (status === "maintenance") return "warning" as const;
  if (status === "inactive") return "destructive" as const;
  return "secondary" as const;
}

function sameDrafts(
  rooms: RegistrationPeriodRoomRule[],
  drafts: Record<string, DraftRoomRule>,
) {
  return rooms.every((room) => {
    const draft = drafts[room.roomId];
    return (
      draft?.isEnabled === room.isEnabled &&
      draft?.genderPolicy === room.genderPolicy
    );
  });
}

export function RegistrationPeriodRoomRulesDialog({
  layout = "dialog",
  open = true,
  onOpenChange,
  onClose,
  period,
  canEdit,
}: {
  layout?: "dialog" | "page";
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onClose?: () => void;
  period: RegistrationPeriod | null;
  canEdit: boolean;
}) {
  const isPage = layout === "page";
  const isActive = isPage || open;
  const close = () => {
    if (isPage) onClose?.();
    else onOpenChange?.(false);
  };
  const [search, setSearch] = useState("");
  const [buildingFilter, setBuildingFilter] = useState("all");
  const [floorFilter, setFloorFilter] = useState("all");
  const [roomFilter, setRoomFilter] = useState("all");
  const [allocationFilter, setAllocationFilter] =
    useState<AllocationFilter>("all");
  const [drafts, setDrafts] = useState<Record<string, DraftRoomRule>>({});
  const [selectedRoomIds, setSelectedRoomIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [confirmSaveOpen, setConfirmSaveOpen] = useState(false);
  const [confirmNotifyOpen, setConfirmNotifyOpen] = useState(false);

  const queryParams = useMemo(
    () => ({
      buildingCode: buildingFilter !== "all" ? buildingFilter : undefined,
      floorNumber: floorFilter !== "all" ? Number(floorFilter) : undefined,
    }),
    [buildingFilter, floorFilter],
  );

  const roomRulesQuery = useRegistrationPeriodRoomRulesQuery(
    period?.id,
    queryParams,
    isActive,
  );
  const updateRoomRules = useUpdateRegistrationPeriodRoomRules();
  const notifyRoomSelection = useNotifyRoomSelection();
  const data = roomRulesQuery.data;

  useEffect(() => {
    if (data?.rooms) {
      setDrafts((prev) => {
        const next = { ...prev };
        for (const room of data.rooms) {
          if (!next[room.roomId]) {
            next[room.roomId] = {
              roomId: room.roomId,
              isEnabled: room.isEnabled,
              genderPolicy: room.genderPolicy,
            };
          }
        }
        return next;
      });
      setSelectedRoomIds(new Set());
    }
  }, [data?.rooms]);

  useEffect(() => {
    if (
      data?.buildings &&
      data.buildings.length > 0 &&
      buildingFilter === "all"
    ) {
      setBuildingFilter(data.buildings[0].buildingCode);
    }
  }, [data?.buildings]);

  useEffect(() => {
    if (!isPage && !open) {
      setSearch("");
      setBuildingFilter("all");
      setFloorFilter("all");
      setRoomFilter("all");
      setAllocationFilter("all");
      setSelectedRoomIds(new Set());
    }
  }, [isPage, open]);

  const buildingOptions = useMemo(() => {
    if (data?.buildings && data.buildings.length > 0) {
      return [
        { value: "all", label: "Tất cả tòa nhà" },
        ...data.buildings.map((b) => ({
          value: b.buildingCode,
          label: `${b.buildingCode} · ${b.buildingName}${b.enabledRooms > 0 ? ` (${b.enabledRooms}/${b.totalRooms} phòng mở)` : ` (${b.totalRooms} phòng)`}`,
        })),
      ];
    }
    if (!data) return [];
    const options = Array.from(
      new Map(
        data.rooms.map((room) => [
          room.buildingCode,
          `${room.buildingCode} · ${room.buildingName}`,
        ]),
      ).entries(),
    );
    return [
      { value: "all", label: "Tất cả tòa nhà" },
      ...options.map(([value, label]) => ({ value, label })),
    ];
  }, [data]);

  const floorOptions = useMemo(() => {
    if (!data) return [];
    const floors = Array.from(
      new Set(
        data.rooms
          .filter(
            (room) =>
              buildingFilter === "all" || room.buildingCode === buildingFilter,
          )
          .map((room) => room.floorNumber),
      ),
    ).sort((left, right) => left - right);
    return [
      { value: "all", label: "Tất cả tầng" },
      ...floors.map((floor) => ({
        value: String(floor),
        label: `Tầng ${floor}`,
      })),
    ];
  }, [buildingFilter, data]);

  const roomOptions = useMemo(() => {
    if (!data) return [];
    const rooms = data.rooms
      .filter(
        (room) =>
          (buildingFilter === "all" || room.buildingCode === buildingFilter) &&
          (floorFilter === "all" || String(room.floorNumber) === floorFilter),
      )
      .sort((left, right) => left.roomCode.localeCompare(right.roomCode));
    return [
      { value: "all", label: "Tất cả phòng" },
      ...rooms.map((room) => ({
        value: room.roomId,
        label: `${room.roomCode} · ${room.roomName}`,
      })),
    ];
  }, [buildingFilter, data, floorFilter]);

  const savedSummary = useMemo(() => {
    if (!data) {
      return {
        enabledRooms: 0,
        enabledPlaces: 0,
        unallocatedRooms: 0,
        unavailableRooms: 0,
        maleRooms: 0,
        femaleRooms: 0,
        mixedRooms: 0,
        unspecifiedRooms: 0,
      };
    }
    return data.rooms.reduce(
      (result, room) => {
        const roomUnavailable =
          room.roomStatus !== "available" || room.availablePlaceCount <= 0;
        if (roomUnavailable) result.unavailableRooms += 1;
        else if (!room.isEnabled) result.unallocatedRooms += 1;
        if (!room.isEnabled) return result;
        result.enabledRooms += 1;
        result.enabledPlaces += room.operationalCapacity;
        if (room.genderPolicy === "male") result.maleRooms += 1;
        if (room.genderPolicy === "female") result.femaleRooms += 1;
        if (room.genderPolicy === "mixed") result.mixedRooms += 1;
        if (room.genderPolicy === "unspecified") result.unspecifiedRooms += 1;
        return result;
      },
      {
        enabledRooms: 0,
        enabledPlaces: 0,
        unallocatedRooms: 0,
        unavailableRooms: 0,
        maleRooms: 0,
        femaleRooms: 0,
        mixedRooms: 0,
        unspecifiedRooms: 0,
      },
    );
  }, [data]);

  const visibleRooms = useMemo(() => {
    if (!data) return [];
    const normalizedSearch = search.trim().toLocaleLowerCase("vi-VN");
    return data.rooms.filter((room) => {
      const matchesBuilding =
        buildingFilter === "all" || room.buildingCode === buildingFilter;
      const matchesFloor =
        floorFilter === "all" || String(room.floorNumber) === floorFilter;
      const matchesRoom = roomFilter === "all" || room.roomId === roomFilter;
      const roomUnavailable =
        room.roomStatus !== "available" || room.availablePlaceCount <= 0;
      const matchesAllocation =
        allocationFilter === "all" ||
        (allocationFilter === "allocated" &&
          !roomUnavailable &&
          room.isEnabled) ||
        (allocationFilter === "unallocated" &&
          !roomUnavailable &&
          !room.isEnabled) ||
        (allocationFilter === "unavailable" && roomUnavailable);
      const searchable =
        `${room.roomCode} ${room.roomName} ${room.buildingName} ${room.roomTypeName}`.toLocaleLowerCase(
          "vi-VN",
        );
      return (
        matchesBuilding &&
        matchesFloor &&
        matchesRoom &&
        matchesAllocation &&
        (!normalizedSearch || searchable.includes(normalizedSearch))
      );
    });
  }, [allocationFilter, buildingFilter, data, floorFilter, roomFilter, search]);

  const groups = useMemo(() => {
    const result = new Map<
      string,
      {
        buildingCode: string;
        buildingName: string;
        floorNumber: number;
        rooms: RegistrationPeriodRoomRule[];
      }
    >();
    for (const room of visibleRooms) {
      const key = `${room.buildingCode}:${room.floorNumber}`;
      const current = result.get(key);
      if (current) current.rooms.push(room);
      else {
        result.set(key, {
          buildingCode: room.buildingCode,
          buildingName: room.buildingName,
          floorNumber: room.floorNumber,
          rooms: [room],
        });
      }
    }
    return Array.from(result.values());
  }, [visibleRooms]);

  const summary = useMemo(() => {
    if (!data)
      return {
        enabledRooms: 0,
        availablePlaces: 0,
        occupiedPlaces: 0,
        totalPlaces: 0,
      };
    return data.rooms.reduce(
      (result, room) => {
        const draft = drafts[room.roomId] ?? room;
        result.enabledRooms += draft.isEnabled ? 1 : 0;
        result.availablePlaces += room.availablePlaceCount;
        result.occupiedPlaces += room.occupiedPlaceCount;
        result.totalPlaces += room.operationalCapacity;
        return result;
      },
      {
        enabledRooms: 0,
        availablePlaces: 0,
        occupiedPlaces: 0,
        totalPlaces: 0,
      },
    );
  }, [data, drafts]);

  const draftSummary = useMemo(() => {
    if (!data) {
      return {
        enabledRooms: 0,
        enabledPlaces: 0,
        maleRooms: 0,
        femaleRooms: 0,
        mixedRooms: 0,
      };
    }
    return data.rooms.reduce(
      (acc, room) => {
        const draft = drafts[room.roomId] ?? room;
        if (draft.isEnabled) {
          acc.enabledRooms += 1;
          acc.enabledPlaces += room.operationalCapacity;
          if (draft.genderPolicy === "male") acc.maleRooms += 1;
          else if (draft.genderPolicy === "female") acc.femaleRooms += 1;
          else if (draft.genderPolicy === "mixed") acc.mixedRooms += 1;
        }
        return acc;
      },
      {
        enabledRooms: 0,
        enabledPlaces: 0,
        maleRooms: 0,
        femaleRooms: 0,
        mixedRooms: 0,
      },
    );
  }, [data, drafts]);

  const hasChanges = Boolean(data && !sameDrafts(data.rooms, drafts));
  const isReadOnly = !canEdit || !data?.canEdit;

  const updateDraft = (roomId: string, changes: Partial<DraftRoomRule>) => {
    setDrafts((current) => ({
      ...current,
      [roomId]: { ...current[roomId], roomId, ...changes },
    }));
  };

  const isRoomEditable = (room: RegistrationPeriodRoomRule) =>
    room.roomStatus === "available" && room.occupiedPlaceCount === 0;

  const isRoomSelectable = (room: RegistrationPeriodRoomRule) =>
    room.roomStatus === "available" && room.occupiedPlaceCount === 0;

  const updateRoomSelection = (roomIds: string[], checked: boolean) => {
    setSelectedRoomIds((current) => {
      const next = new Set(current);
      for (const roomId of roomIds) {
        if (checked) next.add(roomId);
        else next.delete(roomId);
      }
      return next;
    });
  };

  const applyToRooms = (
    roomIds: string[],
    changes: Partial<Omit<DraftRoomRule, "roomId">>,
  ) => {
    const nextChanges =
      changes.genderPolicy !== undefined
        ? { ...changes, isEnabled: true }
        : changes;
    setDrafts((current) => {
      const next = { ...current };
      for (const roomId of roomIds) {
        const room = data?.rooms.find((r) => r.roomId === roomId);
        // Chỉ cho phép can thiệp/áp dụng đối với phòng còn trống
        if (room && isRoomEditable(room)) {
          next[roomId] = { ...next[roomId], roomId, ...nextChanges };
        }
      }
      return next;
    });
  };

  const toggleGroup = (group: (typeof groups)[number], enabled: boolean) => {
    const roomIds = group.rooms
      .filter(isRoomEditable)
      .map((room) => room.roomId);
    applyToRooms(roomIds, { isEnabled: enabled });
  };

  const selectedRooms =
    data?.rooms.filter((room) => selectedRoomIds.has(room.roomId)) ?? [];

  const save = async () => {
    if (!period || !data || isReadOnly) return;
    try {
      await updateRoomRules.mutateAsync({
        id: period.id,
        input: {
          rooms: data.rooms.map(
            (room) =>
              drafts[room.roomId] ?? {
                roomId: room.roomId,
                isEnabled: room.isEnabled,
                genderPolicy: room.genderPolicy,
              },
          ),
        },
      });
      toast.success("Đã lưu phân bổ phòng thành công.");
      if (!isPage) close();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Không thể lưu cấu hình phòng.",
      );
    }
  };

  const notifyStudents = async () => {
    if (!period || !data || !canEdit || !data.canNotify) return;
    try {
      const recipientCount = await notifyRoomSelection.mutateAsync(period.id);
      toast.success(
        recipientCount > 0
          ? `Đã phát thông báo hệ thống và xếp hàng gửi email cho ${recipientCount} sinh viên.`
          : "Thông báo chọn phòng đã được gửi trước đó.",
      );
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Không thể gửi thông báo chọn phòng.",
      );
    }
  };

  const enabledPercent =
    data?.rooms.length && data.rooms.length > 0
      ? (summary.enabledRooms / data.rooms.length) * 100
      : 0;

  const content = (
    <div className="space-y-6">
      {/* 1. Master Card Summary Header */}
      {data ? (
        <Card className="rounded-xl border bg-card shadow-2xs overflow-hidden">
          <CardContent className="p-0">
            <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x">
              {/* Left Panel (7 cols): Period Context, Capacity Progress Bar, Actions */}
              <div className="lg:col-span-7 p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h2 className="text-base sm:text-lg font-bold text-foreground">
                        {period?.name ?? "Đợt đăng ký"}
                      </h2>
                      {period?.code ? (
                        <span className="font-mono text-xs px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-semibold">
                          {period.code}
                        </span>
                      ) : null}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Cấu hình danh mục phòng mở và chính sách giới tính cho
                      sinh viên đăng ký.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant={allocationStatusVariant(data.allocationStatus)}
                      className="gap-1 text-[11px] font-medium"
                    >
                      <span className="size-1.5 rounded-full bg-current" />
                      {allocationStatusLabels[data.allocationStatus]}
                    </Badge>
                    {data.roomSelectionNotificationSentAt ? (
                      <Badge variant="success" className="text-[11px]">
                        Đã thông báo
                      </Badge>
                    ) : null}
                  </div>
                </div>

                {/* Fill Rate Progress Bar */}
                <div className="space-y-2 rounded-lg border bg-muted/15 p-3.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-foreground">
                      Tỷ lệ mở phòng trong đợt:
                    </span>
                    <span className="font-semibold text-foreground font-mono">
                      {summary.enabledRooms}/{data.rooms.length} phòng (
                      {Math.round(enabledPercent)}%)
                    </span>
                  </div>
                  <Progress
                    value={enabledPercent}
                    className="h-2 rounded-full"
                  />
                  <div className="grid grid-cols-2 gap-y-1.5 gap-x-2 pt-1 text-[11px] text-muted-foreground sm:flex sm:flex-wrap sm:items-center sm:justify-between">
                    <span>
                      Chỗ mở:{" "}
                      <strong className="text-foreground font-mono">
                        {savedSummary.enabledPlaces}
                      </strong>
                    </span>
                    <span>
                      Còn trống:{" "}
                      <strong className="text-foreground font-mono">
                        {summary.availablePlaces}
                      </strong>
                    </span>
                    <span>
                      Đang ở:{" "}
                      <strong className="text-foreground font-mono">
                        {summary.occupiedPlaces}
                      </strong>
                    </span>
                    <span>
                      Sức chứa:{" "}
                      <strong className="text-foreground font-mono">
                        {summary.totalPlaces}
                      </strong>
                    </span>
                  </div>
                </div>

                {/* Status Messages & Workflow Actions */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  {!data.hasExplicitRules ? (
                    <p className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                      ⚠️ Chưa phân bổ phòng. Hãy mở các phòng trống trước khi gửi
                      thông báo cho sinh viên.
                    </p>
                  ) : (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                      ✓ Đã phân bổ {savedSummary.enabledRooms} phòng (
                      {savedSummary.enabledPlaces} chỗ) cho đợt này.
                    </p>
                  )}

                  {data.canNotify && canEdit ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="gap-1.5 text-xs font-medium"
                      disabled={notifyRoomSelection.isPending}
                      onClick={() => setConfirmNotifyOpen(true)}
                    >
                      <BellRing className="size-3.5" />
                      <span>
                        {notifyRoomSelection.isPending
                          ? "Đang gửi..."
                          : "Thông báo sinh viên"}
                      </span>
                    </Button>
                  ) : null}
                </div>
              </div>

              {/* Right Panel (5 cols): Gender Breakdown & Sync State */}
              <div className="lg:col-span-5 p-5 flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
                      Phân bổ giới tính đã lưu
                    </span>
                    <Badge
                      variant={hasChanges ? "warning" : "success"}
                      className="text-[10px] font-medium"
                    >
                      {hasChanges ? "Chưa lưu thay đổi" : "Đã đồng bộ"}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="rounded-lg border bg-card p-3">
                      <span className="text-xs text-muted-foreground block font-medium">
                        Phòng Nam
                      </span>
                      <span className="text-2xl font-bold font-mono text-foreground mt-0.5 block">
                        {savedSummary.maleRooms}{" "}
                        <span className="text-xs font-normal text-muted-foreground">
                          phòng
                        </span>
                      </span>
                    </div>
                    <div className="rounded-lg border bg-card p-3">
                      <span className="text-xs text-muted-foreground block font-medium">
                        Phòng Nữ
                      </span>
                      <span className="text-2xl font-bold font-mono text-foreground mt-0.5 block">
                        {savedSummary.femaleRooms}{" "}
                        <span className="text-xs font-normal text-muted-foreground">
                          phòng
                        </span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t pt-2.5">
                  <span>
                    Chưa phân bổ:{" "}
                    <strong className="font-mono text-foreground">
                      {savedSummary.unallocatedRooms}
                    </strong>
                  </span>
                  <span>
                    Không thể mở:{" "}
                    <strong className="font-mono text-foreground">
                      {savedSummary.unavailableRooms}
                    </strong>
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* 2. Filter Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-xs">
          <DebouncedSearchInput
            className="text-xs h-9"
            value={search}
            placeholder="Tìm theo mã phòng, tên phòng..."
            onChange={setSearch}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:w-auto sm:items-center">
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-60 text-xs"
            options={buildingOptions}
            value={buildingFilter}
            searchPlaceholder="Tìm tòa nhà..."
            onValueChange={(value) => {
              setBuildingFilter(value ?? "all");
              setFloorFilter("all");
              setRoomFilter("all");
            }}
          />

          <Combobox
            className="w-full sm:w-36 text-xs"
            options={floorOptions}
            value={floorFilter}
            searchPlaceholder="Tìm tầng..."
            onValueChange={(value) => {
              setFloorFilter(value ?? "all");
              setRoomFilter("all");
            }}
          />

          <Combobox
            className="w-full sm:w-40 text-xs"
            options={roomOptions}
            value={roomFilter}
            searchPlaceholder="Tìm phòng..."
            onValueChange={(value) => setRoomFilter(value ?? "all")}
          />

          <Select
            value={allocationFilter}
            onValueChange={(value) =>
              setAllocationFilter(value as AllocationFilter)
            }
          >
            <SelectTrigger className="w-full col-span-2 sm:col-span-1 sm:w-52 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                {allocationFilterLabels.all} ({data?.rooms.length ?? 0})
              </SelectItem>
              <SelectItem value="allocated">
                {allocationFilterLabels.allocated} ({savedSummary.enabledRooms})
              </SelectItem>
              <SelectItem value="unallocated">
                {allocationFilterLabels.unallocated} (
                {savedSummary.unallocatedRooms})
              </SelectItem>
              <SelectItem value="unavailable">
                {allocationFilterLabels.unavailable} (
                {savedSummary.unavailableRooms})
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 3. Floating Bottom-Center Batch Action Modal */}
      {!isReadOnly && selectedRooms.length > 0 ? (
        <div className="fixed bottom-5 inset-x-0 mx-auto z-50 w-[calc(100%-1.5rem)] sm:w-fit max-w-2xl px-2 sm:px-0 animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="flex items-center justify-between gap-2 sm:gap-3 rounded-full border border-border bg-card/95 backdrop-blur-md px-3.5 py-1.5 shadow-xl ring-1 ring-black/5 dark:ring-white/10">
            {/* Left: Counter */}
            <div className="flex items-center gap-2 border-r border-border pr-3">
              <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-primary text-[11px] font-bold font-mono">
                {selectedRooms.length}
              </span>
              <span className="text-xs font-semibold text-foreground whitespace-nowrap">
                Đã chọn {selectedRooms.length} phòng
              </span>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-1.5">
              <Select
                onValueChange={(value) =>
                  applyToRooms(
                    selectedRooms.map((room) => room.roomId),
                    {
                      genderPolicy: value as RegistrationPeriodRoomGenderPolicy,
                    },
                  )
                }
              >
                <SelectTrigger className="w-32 sm:w-36 h-8 text-xs font-medium">
                  <SelectValue placeholder="Gán giới tính" />
                </SelectTrigger>
                <SelectContent>
                  {selectableGenderPolicies.map(({ value, label }) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                type="button"
                size="sm"
                className="h-8 px-3 text-xs font-medium shrink-0"
                onClick={() =>
                  applyToRooms(
                    selectedRooms.map((room) => room.roomId),
                    { isEnabled: true },
                  )
                }
              >
                Mở phòng
              </Button>

              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-8 px-3 text-xs font-medium shrink-0"
                onClick={() =>
                  applyToRooms(
                    selectedRooms.map((room) => room.roomId),
                    { isEnabled: false },
                  )
                }
              >
                Tắt phòng
              </Button>

              {/* Icon-only Unselect button */}
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-8 text-muted-foreground hover:text-foreground hover:bg-muted shrink-0 rounded-full"
                onClick={() => setSelectedRoomIds(new Set())}
                title="Bỏ chọn tất cả"
                aria-label="Bỏ chọn tất cả"
              >
                <X className="size-4" />
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* 4. Floor Cards & Rooms Grid */}
      {roomRulesQuery.isLoading ? (
        <div className="rounded-xl border bg-card p-10 text-center text-xs text-muted-foreground shadow-2xs">
          Đang tải danh mục phòng...
        </div>
      ) : roomRulesQuery.isError ? (
        <div className="rounded-xl border border-dashed bg-card p-10 text-center text-xs text-destructive shadow-2xs">
          Không thể tải cấu hình phòng đợt đăng ký.
        </div>
      ) : groups.length === 0 ? (
        <div className="rounded-xl border border-dashed bg-card p-10 text-center text-xs text-muted-foreground shadow-2xs">
          Không tìm thấy phòng nào phù hợp với bộ lọc.
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => {
            const enabledCount = group.rooms.filter(
              (room) => (drafts[room.roomId] ?? room).isEnabled,
            ).length;
            const selectableGroupRooms = group.rooms.filter(isRoomSelectable);
            const selectedGroupCount = selectableGroupRooms.filter((room) =>
              selectedRoomIds.has(room.roomId),
            ).length;
            const allGroupSelected =
              selectableGroupRooms.length > 0 &&
              selectedGroupCount === selectableGroupRooms.length;
            const someGroupSelected =
              selectedGroupCount > 0 && !allGroupSelected;
            const allEnabled =
              selectableGroupRooms.length > 0 &&
              selectableGroupRooms.every(
                (room) => (drafts[room.roomId] ?? room).isEnabled,
              );

            return (
              <Card
                key={`${group.buildingCode}-${group.floorNumber}`}
                className="rounded-xl border bg-card shadow-2xs overflow-hidden"
              >
                {/* Floor Header */}
                <div className="flex flex-col gap-3 border-b bg-muted/15 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <Checkbox
                      checked={
                        allGroupSelected
                          ? true
                          : someGroupSelected
                            ? "indeterminate"
                            : false
                      }
                      disabled={isReadOnly || selectableGroupRooms.length === 0}
                      onCheckedChange={(checked) =>
                        updateRoomSelection(
                          selectableGroupRooms.map((room) => room.roomId),
                          checked === true,
                        )
                      }
                      aria-label={`Chọn phòng tầng ${group.floorNumber}`}
                    />
                    <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground border shrink-0">
                      <Layers3 className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-bold text-foreground text-sm">
                        {group.buildingCode} · {group.buildingName} — Tầng{" "}
                        {group.floorNumber}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {group.rooms.length} phòng ·{" "}
                        <strong className="text-foreground font-mono">
                          {enabledCount}
                        </strong>{" "}
                        phòng được mở
                        {selectableGroupRooms.length < group.rooms.length
                          ? ` · ${group.rooms.length - selectableGroupRooms.length} phòng không còn chỗ`
                          : ""}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:w-auto sm:items-center sm:justify-end">
                    <Select
                      onValueChange={(value) =>
                        applyToRooms(
                          selectableGroupRooms.map((room) => room.roomId),
                          {
                            genderPolicy:
                              value as RegistrationPeriodRoomGenderPolicy,
                          },
                        )
                      }
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="w-full sm:w-44 h-8 text-xs">
                        <SelectValue placeholder="Gán giới tính tầng" />
                      </SelectTrigger>
                      <SelectContent>
                        {selectableGenderPolicies.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-full sm:w-auto h-8 text-xs font-medium"
                      disabled={isReadOnly || selectableGroupRooms.length === 0}
                      onClick={() => toggleGroup(group, !allEnabled)}
                    >
                      {allEnabled ? "Tắt cả tầng" : "Mở cả tầng"}
                    </Button>
                  </div>
                </div>

                {/* Rooms Grid */}
                <CardContent className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {group.rooms.map((room) => {
                    const draft = drafts[room.roomId] ?? {
                      roomId: room.roomId,
                      isEnabled: room.isEnabled,
                      genderPolicy: room.genderPolicy,
                    };
                    const isGenderSet =
                      draft.genderPolicy === "male" ||
                      draft.genderPolicy === "female";

                    const hasOccupants = room.occupiedPlaceCount > 0;
                    const editable = isRoomEditable(room);
                    const isSelected = selectedRoomIds.has(room.roomId);

                    return (
                      <div
                        key={room.roomId}
                        className={cn(
                          "rounded-xl border p-3.5 space-y-2.5 transition-all relative",
                          isSelected
                            ? "ring-2 ring-primary border-primary shadow-sm bg-primary/[0.03]"
                            : draft.isEnabled
                              ? draft.genderPolicy === "male"
                                ? "bg-blue-500/[0.04] dark:bg-blue-500/[0.08] border-blue-500/50 shadow-xs hover:border-blue-500/70"
                                : draft.genderPolicy === "female"
                                  ? "bg-rose-500/[0.04] dark:bg-rose-500/[0.08] border-rose-500/50 shadow-xs hover:border-rose-500/70"
                                  : "bg-card border-primary/50 shadow-xs hover:border-primary/70"
                              : "bg-card border-border hover:border-muted-foreground/40 shadow-xs",
                        )}
                      >
                        {/* Header: Checkbox + Code + Status Badge */}
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <Checkbox
                              checked={isSelected}
                              disabled={isReadOnly || !editable}
                              onCheckedChange={(checked) =>
                                updateRoomSelection(
                                  [room.roomId],
                                  checked === true,
                                )
                              }
                              aria-label={`Chọn phòng ${room.roomCode}`}
                            />
                            <span className="font-mono font-bold text-foreground text-sm tracking-tight">
                              {room.roomCode}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {hasOccupants ? (
                              <Badge
                                variant="outline"
                                className="text-[10px] px-1.5 py-0 border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 font-medium"
                              >
                                Đã có {room.occupiedPlaceCount} SV
                              </Badge>
                            ) : null}
                            <Badge
                              variant={roomStatusVariant(room.roomStatus)}
                              className="text-[10px] px-2 py-0.5 font-medium shrink-0"
                            >
                              {roomStatusLabels[room.roomStatus] ??
                                room.roomStatus}
                            </Badge>
                          </div>
                        </div>

                        {/* Middle: Name, Room Type Badge & Occupancy */}
                        <div className="space-y-1 text-xs">
                          <div className="flex items-center justify-between gap-1.5">
                            <p className="text-muted-foreground truncate font-medium">
                              {room.roomName}
                            </p>
                            <Badge
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 shrink-0 border-border/80 bg-muted/30"
                            >
                              {room.roomTypeName}
                            </Badge>
                          </div>
                          <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
                            <Users className="size-3 shrink-0" />
                            <span>
                              <strong className="text-foreground">
                                {room.availablePlaceCount}
                              </strong>{" "}
                              trống · {room.occupiedPlaceCount} ở /{" "}
                              {room.operationalCapacity}
                            </span>
                          </p>
                        </div>

                        {/* Bottom: Switch & Gender Policy */}
                        <div className="space-y-2 pt-2.5 border-t border-border/80 text-xs">
                          <div className="flex items-center justify-between">
                            <label
                              htmlFor={`room-enabled-${room.roomId}`}
                              className={cn(
                                "text-xs transition-colors",
                                hasOccupants
                                  ? "font-medium text-muted-foreground cursor-not-allowed"
                                  : draft.isEnabled
                                    ? "font-semibold text-foreground cursor-pointer"
                                    : "font-medium text-muted-foreground hover:text-foreground cursor-pointer",
                              )}
                            >
                              {hasOccupants
                                ? "Đang có SV"
                                : draft.isEnabled
                                  ? "Mở phòng"
                                  : "Không mở"}
                            </label>
                            <Switch
                              id={`room-enabled-${room.roomId}`}
                              checked={draft.isEnabled}
                              disabled={isReadOnly || !editable}
                              onCheckedChange={(checked) => {
                                if (checked && !editable) return;
                                updateDraft(room.roomId, {
                                  isEnabled: checked,
                                  genderPolicy:
                                    checked && !isGenderSet
                                      ? "male"
                                      : draft.genderPolicy,
                                });
                              }}
                            />
                          </div>

                          <Select
                            value={isGenderSet ? draft.genderPolicy : undefined}
                            disabled={isReadOnly || !editable}
                            onValueChange={(value) =>
                              updateDraft(room.roomId, {
                                genderPolicy:
                                  value as RegistrationPeriodRoomGenderPolicy,
                              })
                            }
                          >
                            <SelectTrigger className="w-full h-8 text-xs font-medium border-border">
                              <SelectValue placeholder="Chọn giới tính..." />
                            </SelectTrigger>
                            <SelectContent>
                              {selectableGenderPolicies.map(
                                ({ value, label }) => (
                                  <SelectItem key={value} value={value}>
                                    {label}
                                  </SelectItem>
                                ),
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* 5. Footer Actions Bar (Borderless) */}
      <div className="flex items-center justify-end pt-2">
        <div className="flex items-center justify-end gap-2.5 w-full sm:w-auto">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full sm:w-auto h-9 text-xs"
            onClick={close}
          >
            {isPage ? "Quay lại" : "Đóng"}
          </Button>

          {!isReadOnly ? (
            <Button
              type="button"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs font-semibold gap-1.5"
              disabled={!hasChanges || updateRoomRules.isPending}
              onClick={() => setConfirmSaveOpen(true)}
            >
              <Save className="size-3.5" />
              <span>
                {updateRoomRules.isPending
                  ? "Đang lưu..."
                  : "Lưu phân bổ phòng"}
              </span>
            </Button>
          ) : null}
        </div>
      </div>

      <ConfirmDialog
        open={confirmSaveOpen}
        onOpenChange={setConfirmSaveOpen}
        title="Xác nhận lưu phân bổ phòng"
        description={
          <div className="space-y-3 text-xs">
            <p>
              Bạn có chắc chắn muốn lưu cấu hình phân bổ phòng cho đợt{" "}
              <strong className="text-foreground">{period?.name}</strong>?
            </p>
            <div className="rounded-lg border bg-muted/40 p-3 space-y-1.5 font-normal">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tổng số phòng mở:</span>
                <span className="font-semibold text-foreground">
                  {draftSummary.enabledRooms} phòng (
                  {draftSummary.enabledPlaces} chỗ)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Phòng Nam:</span>
                <span className="font-medium text-blue-600 dark:text-blue-400">
                  {draftSummary.maleRooms} phòng
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Phòng Nữ:</span>
                <span className="font-medium text-rose-600 dark:text-rose-400">
                  {draftSummary.femaleRooms} phòng
                </span>
              </div>
              {draftSummary.mixedRooms > 0 ? (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Phòng Nam/Nữ:</span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">
                    {draftSummary.mixedRooms} phòng
                  </span>
                </div>
              ) : null}
            </div>
            <p className="text-muted-foreground text-[11px]">
              Lưu ý: Cấu hình phân bổ này sẽ áp dụng trực tiếp cho sinh viên khi
              tham gia chọn phòng trong đợt này.
            </p>
          </div>
        }
        confirmLabel="Lưu cấu hình"
        confirmVariant="default"
        isLoading={updateRoomRules.isPending}
        onConfirm={async () => {
          await save();
          setConfirmSaveOpen(false);
        }}
      />

      <ConfirmDialog
        open={confirmNotifyOpen}
        onOpenChange={setConfirmNotifyOpen}
        title="Xác nhận gửi thông báo cho sinh viên"
        description={
          <div className="space-y-3 text-xs">
            <p>
              Bạn có chắc chắn muốn phát thông báo hệ thống và gửi email thông
              báo chọn phòng cho các sinh viên có hồ sơ đã duyệt trong đợt{" "}
              <strong className="text-foreground">{period?.name}</strong>?
            </p>
            <div className="rounded-lg border bg-muted/40 p-3 space-y-1.5 font-normal">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Phòng mở đã lưu:</span>
                <span className="font-semibold text-foreground">
                  {savedSummary.enabledRooms} phòng (
                  {savedSummary.enabledPlaces} chỗ)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Phòng Nam:</span>
                <span className="font-medium text-blue-600 dark:text-blue-400">
                  {savedSummary.maleRooms} phòng
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Phòng Nữ:</span>
                <span className="font-medium text-rose-600 dark:text-rose-400">
                  {savedSummary.femaleRooms} phòng
                </span>
              </div>
              {savedSummary.mixedRooms > 0 ? (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Phòng Nam/Nữ:</span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">
                    {savedSummary.mixedRooms} phòng
                  </span>
                </div>
              ) : null}
            </div>
            {hasChanges ? (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-amber-700 dark:text-amber-300 text-[11px] font-medium">
                ⚠️ Bạn đang có thay đổi phân bổ phòng chưa lưu. Hãy nhấn{" "}
                <strong>"Lưu phân bổ phòng"</strong> trước khi gửi thông báo để
                sinh viên thấy đúng danh sách phòng mới nhất.
              </div>
            ) : null}
            <p className="text-muted-foreground text-[11px]">
              Lưu ý: Hệ thống sẽ gửi chuông thông báo trực tiếp và xếp hàng gửi
              email đồng loạt cho sinh viên đủ điều kiện.
            </p>
          </div>
        }
        confirmLabel="Gửi thông báo"
        confirmVariant="default"
        isLoading={notifyRoomSelection.isPending}
        onConfirm={async () => {
          await notifyStudents();
          setConfirmNotifyOpen(false);
        }}
      />
    </div>
  );

  if (isPage) {
    return content;
  }

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(900px,calc(100dvh-1rem))] w-full max-w-6xl flex-col overflow-hidden p-6">
        <ResponsiveDialogHeader className="border-b pb-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
              <SlidersHorizontal className="size-4" />
            </div>
            <span>Phân bổ phòng cho đợt đăng ký</span>
          </ResponsiveDialogTitle>
        </ResponsiveDialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto pt-4">{content}</div>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

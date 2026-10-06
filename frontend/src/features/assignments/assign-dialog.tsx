import {
  Building2,
  DoorOpen,
  GraduationCap,
  Search,
  Sparkles,
  User,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  useAssignStudent,
  useEligibleApplicationsQuery,
} from "@/features/assignments/api";
import type { EligibleApplication } from "@/features/assignments/types";
import { useRegistrationPeriodRoomRulesQuery } from "@/features/registration-periods/api";
import type { RegistrationPeriodRoomRule } from "@/features/registration-periods/types";

const assignmentSchema = z.object({
  applicationId: z.string().min(1),
  roomId: z.string().min(1),
  note: z.string().max(2000),
});

function isGenderCompatible(studentGender?: string, roomPolicy?: string) {
  return (
    !studentGender ||
    roomPolicy === "mixed" ||
    roomPolicy === "unspecified" ||
    studentGender === roomPolicy
  );
}

export function AssignDialog({
  open,
  onOpenChange,
  registrationPeriodId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  registrationPeriodId?: string;
}) {
  const [applicationSearch, setApplicationSearch] = useState("");
  const [selectedApplication, setSelectedApplication] =
    useState<EligibleApplication | null>(null);
  const [roomId, setRoomId] = useState("");
  const [note, setNote] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  const isSearching = applicationSearch.trim().length > 0;

  const eligible = useEligibleApplicationsQuery(
    applicationSearch.trim(),
    registrationPeriodId,
    open && isSearching,
  );
  const rooms = useRegistrationPeriodRoomRulesQuery(registrationPeriodId, open);
  const assign = useAssignStudent();

  const compatibleRooms = useMemo(() => {
    const list = (rooms.data?.rooms ?? []).filter(
      (room) =>
        Boolean(rooms.data?.hasExplicitRules) &&
        room.isEnabled &&
        room.roomStatus === "available" &&
        room.availablePlaceCount > 0 &&
        isGenderCompatible(selectedApplication?.gender, room.genderPolicy),
    );

    // Sort: rooms matching requested room type first
    return list.sort((left, right) => {
      const isLeftMatch =
        selectedApplication?.requestedRoomTypeName === left.roomTypeName;
      const isRightMatch =
        selectedApplication?.requestedRoomTypeName === right.roomTypeName;
      if (isLeftMatch && !isRightMatch) return -1;
      if (!isLeftMatch && isRightMatch) return 1;
      return left.roomCode.localeCompare(right.roomCode, "vi", {
        numeric: true,
      });
    });
  }, [rooms.data, selectedApplication]);

  const selectedRoom = useMemo<RegistrationPeriodRoomRule | undefined>(
    () => compatibleRooms.find((r) => r.roomId === roomId),
    [compatibleRooms, roomId],
  );

  const reset = () => {
    setApplicationSearch("");
    setSelectedApplication(null);
    setRoomId("");
    setNote("");
    setConfirmOpen(false);
  };

  const handleSelectStudent = (app: EligibleApplication) => {
    setSelectedApplication(app);
    setRoomId("");
  };

  const handleClearStudent = () => {
    setSelectedApplication(null);
    setRoomId("");
  };

  const handleOpenConfirm = () => {
    if (!selectedApplication || !roomId) {
      toast.error("Vui lòng chọn hồ sơ sinh viên và phòng còn chỗ phù hợp.");
      return;
    }
    const parsed = assignmentSchema.safeParse({
      applicationId: selectedApplication.id,
      roomId,
      note,
    });
    if (!parsed.success) {
      toast.error("Thông tin phân phòng chưa hợp lệ.");
      return;
    }
    setConfirmOpen(true);
  };

  const handleConfirmAssign = () => {
    if (!selectedApplication || !roomId) return;
    void assign
      .mutateAsync({
        applicationId: selectedApplication.id,
        roomId,
        note: note.trim() || undefined,
      })
      .then(() => {
        setConfirmOpen(false);
        onOpenChange(false);
        reset();
        toast.success(
          `Đã xếp sinh viên ${selectedApplication.studentName} vào Phòng ${selectedRoom?.roomCode ?? ""}.`,
        );
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error ? error.message : "Không thể xếp phòng.",
        ),
      );
  };

  return (
    <>
      <ResponsiveDialog
        open={open}
        onOpenChange={(value) => {
          onOpenChange(value);
          if (!value && !assign.isPending) reset();
        }}
      >
        <ResponsiveDialogContent className="flex max-h-[min(860px,calc(100vh-2rem))] w-full max-w-2xl flex-col overflow-hidden p-0 gap-0 shadow-xl">
          {/* Header */}
          <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
            <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                <UserPlus className="size-4" />
              </div>
              <span>Xếp sinh viên vào phòng</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-0.5">
              Tìm kiếm sinh viên đủ điều kiện và chỉ định phòng còn chỗ phù hợp.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>

          {/* Body */}
          <div className="min-h-0 flex-1 overflow-y-auto space-y-4 px-6 py-4">
            {/* BƯỚC 1: TÌM KIẾM & CHỌN SINH VIÊN */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <User className="size-3.5 text-primary" />
                  1. Sinh viên cần xếp phòng{" "}
                  <span className="text-destructive">*</span>
                </label>
                {selectedApplication && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                    onClick={handleClearStudent}
                  >
                    <X className="size-3 mr-1" />
                    Đổi sinh viên khác
                  </Button>
                )}
              </div>

              {!selectedApplication ? (
                <div className="space-y-2">
                  <DebouncedSearchInput
                    value={applicationSearch}
                    onChange={setApplicationSearch}
                    placeholder="Tìm theo mã sinh viên hoặc họ và tên..."
                    className="h-9 text-xs"
                  />

                  {!isSearching ? (
                    <div className="rounded-lg border border-dashed bg-muted/15 p-6 text-center text-xs text-muted-foreground space-y-1.5">
                      <Search className="size-5 mx-auto text-muted-foreground/60 mb-1" />
                      <p className="font-semibold text-foreground">
                        Nhập mã sinh viên hoặc họ và tên để tra cứu
                      </p>
                      <p className="text-[11px] text-muted-foreground max-w-sm mx-auto">
                        Hệ thống sẽ tra cứu các hồ sơ đã duyệt nhưng chưa được
                        xếp phòng trong đợt này.
                      </p>
                    </div>
                  ) : (
                    /* Danh sách kết quả tìm kiếm sinh viên */
                    <div className="rounded-lg border bg-card overflow-hidden">
                      {eligible.isLoading ? (
                        <div className="py-8 text-center text-xs text-muted-foreground">
                          Đang tìm kiếm hồ sơ đủ điều kiện...
                        </div>
                      ) : eligible.isError ? (
                        <div className="py-6 text-center text-xs text-destructive">
                          Không thể tải danh sách hồ sơ sinh viên.
                        </div>
                      ) : eligible.data?.items.length === 0 ? (
                        <div className="py-8 text-center text-xs text-muted-foreground">
                          Không tìm thấy sinh viên nào khớp với từ khóa “
                          {applicationSearch}”.
                        </div>
                      ) : (
                        <div className="max-h-52 overflow-y-auto divide-y divide-border/60">
                          {eligible.data?.items.map((item) => (
                            <div
                              key={item.id}
                              onClick={() => handleSelectStudent(item)}
                              className="flex items-center justify-between p-3 hover:bg-muted/50 cursor-pointer transition-colors text-xs gap-3 group"
                            >
                              <div className="space-y-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
                                    {item.studentName}
                                  </span>
                                  <span className="font-mono text-[11px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                                    {item.studentCode}
                                  </span>
                                  <Badge
                                    variant={
                                      item.gender === "male"
                                        ? "default"
                                        : "secondary"
                                    }
                                    className="text-[10px] px-1.5 py-0 font-normal"
                                  >
                                    {item.gender === "male"
                                      ? "Nam"
                                      : item.gender === "female"
                                        ? "Nữ"
                                        : item.gender}
                                  </Badge>
                                </div>
                                <div className="text-muted-foreground text-[11px] flex items-center gap-2 flex-wrap">
                                  <span>
                                    {[item.faculty, item.className]
                                      .filter(Boolean)
                                      .join(" · ") || "Chưa có lớp/khoa"}
                                  </span>
                                  {item.requestedRoomTypeName && (
                                    <>
                                      <span>•</span>
                                      <span className="text-primary font-medium">
                                        Nguyện vọng:{" "}
                                        {item.requestedRoomTypeName}
                                      </span>
                                    </>
                                  )}
                                  {item.priorityScore > 0 && (
                                    <>
                                      <span>•</span>
                                      <span>
                                        Điểm ưu tiên: {item.priorityScore}
                                      </span>
                                    </>
                                  )}
                                </div>
                              </div>

                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="shrink-0 h-7 text-xs px-2.5 group-hover:bg-primary group-hover:text-primary-foreground transition-colors"
                              >
                                Chọn
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                /* Card thông tin sinh viên đã chọn */
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-3.5 text-xs space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="size-7 rounded-full bg-primary/20 flex items-center justify-center text-primary shrink-0">
                        <UserCheck className="size-4" />
                      </div>
                      <div>
                        <p className="font-bold text-foreground text-sm">
                          {selectedApplication.studentName}
                        </p>
                        <p className="font-mono text-muted-foreground text-[11px]">
                          {selectedApplication.studentCode} · Hồ sơ:{" "}
                          {selectedApplication.applicationCode}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={
                        selectedApplication.gender === "male"
                          ? "default"
                          : "secondary"
                      }
                      className="text-xs px-2 py-0.5"
                    >
                      {selectedApplication.gender === "male"
                        ? "Nam"
                        : selectedApplication.gender === "female"
                          ? "Nữ"
                          : selectedApplication.gender}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 border-t border-primary/15 text-[11px]">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <GraduationCap className="size-3.5 text-primary/70 shrink-0" />
                      <span>
                        {[
                          selectedApplication.faculty,
                          selectedApplication.className,
                        ]
                          .filter(Boolean)
                          .join(" · ") || "Chưa có khoa/lớp"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <DoorOpen className="size-3.5 text-primary/70 shrink-0" />
                      <span>Nguyện vọng: </span>
                      <strong className="text-foreground">
                        {selectedApplication.requestedRoomTypeName || "Bất kỳ"}
                      </strong>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* BƯỚC 2: CHỌN PHÒNG CHO SINH VIÊN */}
            {selectedApplication && (
              <div className="space-y-2 pt-2 border-t">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <Building2 className="size-3.5 text-primary" />
                    2. Chọn phòng còn chỗ phù hợp{" "}
                    <span className="text-destructive">*</span>
                  </label>
                  <span className="text-[11px] text-muted-foreground">
                    {compatibleRooms.length} phòng khả dụng
                  </span>
                </div>

                <Select value={roomId} onValueChange={setRoomId}>
                  <SelectTrigger className="text-xs h-10">
                    <SelectValue
                      placeholder={
                        rooms.isLoading
                          ? "Đang tải danh sách phòng..."
                          : "Chọn phòng cho sinh viên..."
                      }
                    />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {compatibleRooms.map((room) => {
                      const isMatch =
                        selectedApplication.requestedRoomTypeName ===
                        room.roomTypeName;
                      return (
                        <SelectItem key={room.roomId} value={room.roomId}>
                          <div className="flex items-center gap-2 text-xs py-0.5">
                            <span className="font-semibold text-foreground">
                              {room.buildingCode} - P.{room.roomCode}
                            </span>
                            <span className="text-muted-foreground">
                              (Tầng {room.floorNumber} · {room.roomTypeName})
                            </span>
                            <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                              · Còn {room.availablePlaceCount} chỗ
                            </span>
                            {isMatch && (
                              <Badge
                                variant="success"
                                className="text-[10px] px-1.5 py-0 gap-1 ml-1"
                              >
                                <Sparkles className="size-2.5" />
                                Đúng nguyện vọng
                              </Badge>
                            )}
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>

                {compatibleRooms.length === 0 && !rooms.isLoading && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-md p-2.5">
                    ⚠️ Không tìm thấy phòng nào còn chỗ phù hợp với giới tính (
                    {selectedApplication.gender === "male" ? "Nam" : "Nữ"}) hoặc
                    chính sách phòng của đợt này.
                  </p>
                )}

                {/* Tóm tắt phòng đã chọn */}
                {selectedRoom && (
                  <div className="rounded-lg border bg-muted/40 p-3 text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">
                          Phòng {selectedRoom.roomCode} ·{" "}
                          {selectedRoom.buildingName}
                        </span>
                        <Badge variant="outline" className="text-[10px]">
                          Tầng {selectedRoom.floorNumber}
                        </Badge>
                        {selectedApplication.requestedRoomTypeName ===
                          selectedRoom.roomTypeName && (
                          <Badge
                            variant="success"
                            className="text-[10px] gap-1"
                          >
                            <Sparkles className="size-2.5" /> Khớp nguyện vọng
                          </Badge>
                        )}
                      </div>
                      <span className="text-muted-foreground text-[11px] flex items-center gap-1">
                        <Users className="size-3" />
                        Còn {selectedRoom.availablePlaceCount}/
                        {selectedRoom.operationalCapacity ||
                          selectedRoom.capacity}{" "}
                        chỗ
                      </span>
                    </div>
                    <p className="text-muted-foreground text-[11px]">
                      Loại phòng:{" "}
                      <strong className="text-foreground">
                        {selectedRoom.roomTypeName}
                      </strong>{" "}
                      · Quy định:{" "}
                      {selectedRoom.genderPolicy === "male"
                        ? "Phòng Nam"
                        : selectedRoom.genderPolicy === "female"
                          ? "Phòng Nữ"
                          : "Dùng chung"}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* BƯỚC 3: GHI CHÚ */}
            {selectedApplication && (
              <div className="space-y-1.5 pt-2 border-t">
                <label className="text-xs font-medium text-foreground">
                  Ghi chú phân phòng
                </label>
                <Textarea
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Ghi chú phân phòng (ví dụ: Xếp theo diện ưu tiên chính sách, xếp hộ tại văn phòng...)"
                  rows={2}
                  className="text-xs"
                />
              </div>
            )}
          </div>

          {/* Footer */}
          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6 sm:py-3.5">
            <div className="grid grid-cols-2 gap-3 w-full sm:flex sm:w-auto sm:items-center sm:justify-end sm:gap-2.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full sm:w-auto h-9 text-xs"
                disabled={assign.isPending}
                onClick={() => onOpenChange(false)}
              >
                Hủy
              </Button>
              <Button
                type="button"
                size="sm"
                className="w-full sm:w-auto h-9 text-xs font-semibold bg-primary hover:bg-primary/90"
                disabled={assign.isPending || !selectedApplication || !roomId}
                onClick={handleOpenConfirm}
              >
                {assign.isPending ? "Đang lưu..." : "Xếp phòng"}
              </Button>
            </div>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* MODAL XÁC NHẬN AN TOÀN */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Xác nhận xếp phòng cho sinh viên?"
        description={
          selectedApplication && selectedRoom ? (
            <div className="space-y-2.5 text-xs text-foreground">
              <p>
                Bạn có chắc chắn muốn phân phòng cho sinh viên dưới đây không?
              </p>
              <div className="rounded-lg border bg-muted/40 p-3 space-y-1.5 text-muted-foreground font-normal">
                <div>
                  <span>Sinh viên: </span>
                  <strong className="text-foreground">
                    {selectedApplication.studentName}
                  </strong>{" "}
                  ({selectedApplication.studentCode} -{" "}
                  {selectedApplication.className || "Chưa có lớp"})
                </div>
                <div>
                  <span>Phòng gán: </span>
                  <strong className="text-foreground">
                    Phòng {selectedRoom.roomCode} · {selectedRoom.buildingName}
                  </strong>{" "}
                  (Tầng {selectedRoom.floorNumber} · {selectedRoom.roomTypeName}
                  )
                </div>
              </div>
              <p className="text-muted-foreground text-[11px]">
                Lưu ý: Sau khi xác nhận, hồ sơ sinh viên sẽ chuyển sang trạng
                thái{" "}
                <strong className="text-foreground">
                  Đã xếp phòng chính thức
                </strong>{" "}
                và hệ thống sẽ tự động phát thông báo đến sinh viên.
              </p>
            </div>
          ) : (
            ""
          )
        }
        confirmLabel="Xác nhận xếp phòng"
        confirmVariant="default"
        isLoading={assign.isPending}
        onConfirm={handleConfirmAssign}
      />
    </>
  );
}

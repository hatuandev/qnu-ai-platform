import { useForm } from "@tanstack/react-form";
import { Loader2, Plus, Save } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { Combobox } from "@/components/admin/combobox";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useBuildingsQuery } from "@/features/buildings/api";
import { useFloorsQuery } from "@/features/floors/api";
import { useRoomTypesQuery } from "@/features/room-types/api";
import { useCreateRoom, useUpdateRoom } from "@/features/rooms/api";
import type { RoomDetail, RoomFormValues } from "@/features/rooms/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const roomFormSchema = z
  .object({
    buildingId: z.string().min(1, "Tòa nhà là bắt buộc."),
    floorId: z.string().min(1, "Tầng là bắt buộc."),
    roomTypeId: z.string().min(1, "Loại phòng là bắt buộc."),
    code: z
      .string()
      .trim()
      .min(1, "Mã phòng là bắt buộc.")
      .max(50, "Mã phòng tối đa 50 ký tự."),
    name: z
      .string()
      .trim()
      .min(1, "Tên phòng là bắt buộc.")
      .max(100, "Tên phòng tối đa 100 ký tự."),
    capacity: z.number().int().min(1, "Sức chứa phải lớn hơn 0."),
    operationalCapacity: z
      .number()
      .int()
      .min(1, "Sức chứa vận hành phải lớn hơn 0."),
    note: z.string().trim().max(2000, "Ghi chú tối đa 2000 ký tự."),
  })
  .refine((value) => value.operationalCapacity <= value.capacity, {
    path: ["operationalCapacity"],
    message: "Sức chứa vận hành không được vượt quá sức chứa thiết kế.",
  });

function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

function getServerFieldErrors(error: ApiError) {
  return Object.fromEntries(
    Object.entries(error.fieldErrors ?? {}).map(([key, messages]) => [
      key.toLowerCase(),
      messages.join(" "),
    ]),
  );
}

export function RoomFormDialog({
  open,
  onOpenChange,
  room,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  room?: RoomDetail | null;
}) {
  const isEdit = Boolean(room);
  const createMutation = useCreateRoom();
  const updateMutation = useUpdateRoom();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFieldErrors, setServerFieldErrors] = useState<
    Record<string, string>
  >({});
  const [selectedBuildingId, setSelectedBuildingId] = useState(
    room?.buildingId ?? "",
  );
  const buildingsQuery = useBuildingsQuery({
    page: 1,
    pageSize: 100,
    status: "active",
  });
  const floorsQuery = useFloorsQuery(selectedBuildingId);
  const roomTypesQuery = useRoomTypesQuery({
    page: 1,
    pageSize: 100,
    isActive: true,
  });

  const buildings = buildingsQuery.data?.items ?? [];
  const floors = floorsQuery.data ?? [];
  const roomTypes = roomTypesQuery.data?.items ?? [];

  const buildingOptions = useMemo(
    () =>
      buildings.map((b) => ({
        value: b.id,
        label: `${b.code} · ${b.name}`,
      })),
    [buildings],
  );

  const floorOptions = useMemo(
    () =>
      floors.map((f) => ({
        value: f.id,
        label: `Tầng ${f.floorNumber} · ${f.name}`,
      })),
    [floors],
  );

  const roomTypeOptions = useMemo(
    () =>
      roomTypes.map((rt) => ({
        value: rt.id,
        label: `${rt.code} · ${rt.name} (${rt.capacity} người)`,
      })),
    [roomTypes],
  );

  const form = useForm({
    defaultValues: {
      buildingId: room?.buildingId ?? "",
      floorId: room?.floorId ?? "",
      roomTypeId: room?.roomTypeId ?? "",
      code: room?.code ?? "",
      name: room?.name ?? "",
      capacity: room?.capacity ?? 1,
      operationalCapacity: room?.operationalCapacity ?? room?.capacity ?? 1,
      note: room?.note ?? "",
    } satisfies RoomFormValues,
    validators: { onSubmit: roomFormSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFieldErrors({});
      try {
        if (room) {
          await updateMutation.mutateAsync({
            id: room.id,
            input: {
              name: value.name.trim(),
              capacity: value.capacity,
              operationalCapacity: value.operationalCapacity,
              note: value.note.trim() || undefined,
            },
          });
        } else {
          await createMutation.mutateAsync({
            buildingId: value.buildingId,
            floorId: value.floorId,
            roomTypeId: value.roomTypeId,
            code: value.code.trim(),
            name: value.name.trim(),
            capacity: value.capacity,
            operationalCapacity: value.operationalCapacity,
            note: value.note.trim() || undefined,
          });
        }
        toast.success(
          room
            ? "Đã cập nhật phòng thành công."
            : "Đã tạo phòng mới thành công.",
        );
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFieldErrors(getServerFieldErrors(error));
        } else {
          setServerError("Không thể lưu phòng. Vui lòng thử lại.");
        }
      }
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(840px,calc(100vh-2rem))] w-full max-w-2xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa phòng" : "Thêm phòng mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Cập nhật thông tin vận hành của phòng. Tòa nhà, tầng, loại và mã phòng không thay đổi sau khi tạo."
              : "Tạo phòng thuộc một tầng và loại phòng cụ thể trong ký túc xá."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="grid gap-5 px-4 py-4 lg:px-1">
            {serverError ? (
              <div
                role="alert"
                className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              >
                {serverError}
              </div>
            ) : null}

            {/* Tòa nhà & Tầng */}
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="buildingId">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.buildingid;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-building">
                        Tòa nhà{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Combobox
                        className="w-full text-xs"
                        options={buildingOptions}
                        value={field.state.value}
                        searchPlaceholder="Tìm tòa nhà..."
                        disabled={isEdit || isSubmitting}
                        onValueChange={(value) => {
                          const v = value ?? "";
                          setSelectedBuildingId(v);
                          field.handleChange(v);
                          form.setFieldValue("floorId", "");
                        }}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              <form.Field name="floorId">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.floorid;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-floor">
                        Tầng{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Combobox
                        className="w-full text-xs"
                        options={floorOptions}
                        value={field.state.value}
                        searchPlaceholder={
                          !selectedBuildingId
                            ? "Vui lòng chọn tòa nhà trước"
                            : "Tìm tầng..."
                        }
                        disabled={isEdit || !selectedBuildingId || isSubmitting}
                        onValueChange={(value) =>
                          field.handleChange(value ?? "")
                        }
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Loại phòng */}
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="roomTypeId">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.roomtypeid;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-type">
                        Loại phòng{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Combobox
                        className="w-full text-xs"
                        options={roomTypeOptions}
                        value={field.state.value}
                        searchPlaceholder="Tìm loại phòng..."
                        disabled={isEdit || isSubmitting}
                        onValueChange={(value) => {
                          const v = value ?? "";
                          field.handleChange(v);
                          const selectedType = roomTypes.find(
                            (rt) => rt.id === v,
                          );
                          if (selectedType && !isEdit) {
                            form.setFieldValue(
                              "capacity",
                              selectedType.capacity,
                            );
                            form.setFieldValue(
                              "operationalCapacity",
                              selectedType.capacity,
                            );
                          }
                        }}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Mã phòng & Tên phòng */}
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="code">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.code;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-code">
                        Mã phòng{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="room-code"
                        className="text-xs font-mono"
                        placeholder="Ví dụ: P.101"
                        value={field.state.value}
                        disabled={isEdit || isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              <form.Field name="name">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.name;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-name">
                        Tên phòng{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="room-name"
                        className="text-xs"
                        placeholder="Ví dụ: Phòng 101"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Sức chứa thiết kế & Sức chứa vận hành */}
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="capacity">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.capacity;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-capacity">
                        Sức chứa thiết kế{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="room-capacity"
                        type="number"
                        min={1}
                        className="text-xs font-mono"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(Number(event.target.value))
                        }
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              <form.Field name="operationalCapacity">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.operationalcapacity;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-operational-capacity">
                        Sức chứa vận hành{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="room-operational-capacity"
                        type="number"
                        min={1}
                        className="text-xs font-mono"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(Number(event.target.value))
                        }
                        aria-invalid={Boolean(error)}
                      />
                      <p className="type-caption text-muted-foreground text-xs mt-0.5">
                        Giới hạn chỗ ở thực tế đang được phép sử dụng.
                      </p>
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Ghi chú */}
            <form.Field name="note">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ?? serverFieldErrors.note;
                return (
                  <Field>
                    <FieldLabel htmlFor="room-note">Ghi chú</FieldLabel>
                    <Textarea
                      id="room-note"
                      rows={3}
                      className="text-xs"
                      placeholder="Nhập ghi chú thêm cho phòng (tùy chọn)..."
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
          </div>

          {/* Footer */}
          <ResponsiveDialogFooter className="border-t px-4 pt-4 lg:px-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={isSubmitting}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, formSubmitting]) => (
                <Button
                  type="submit"
                  size="sm"
                  className="gap-1.5 text-xs font-semibold"
                  disabled={!canSubmit || formSubmitting || isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : isEdit ? (
                    <>
                      <Save className="size-3.5" />
                      <span>Lưu thay đổi</span>
                    </>
                  ) : (
                    <>
                      <Plus className="size-3.5" />
                      <span>Tạo phòng</span>
                    </>
                  )}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

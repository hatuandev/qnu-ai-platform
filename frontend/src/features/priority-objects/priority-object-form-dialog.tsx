import { useForm } from "@tanstack/react-form";
import { toast } from "sonner";
import { z } from "zod";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { EligibleAreasDialog } from "@/features/priority-objects/eligible-areas-dialog";
import {
  type CreatePriorityObjectInput,
  PRIORITY_OBJECT_VERIFICATION_TYPE,
  PRIORITY_OBJECT_VERIFICATION_TYPE_LABELS,
  type PriorityObject,
  type PriorityObjectVerificationType,
  type UpdatePriorityObjectInput,
} from "@/features/priority-objects/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const VERIFICATION_TYPE_VALUES = [
  PRIORITY_OBJECT_VERIFICATION_TYPE.None,
  PRIORITY_OBJECT_VERIFICATION_TYPE.ImageEvidence,
  PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea,
  PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea,
] as const;

const EVIDENCE_DEFAULTS = {
  maxFiles: 4,
  maxFileSizeMb: 10,
} as const;

const verificationRequiresEvidence = (
  type: PriorityObjectVerificationType,
): boolean =>
  type === PRIORITY_OBJECT_VERIFICATION_TYPE.ImageEvidence ||
  type === PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea;

const verificationRequiresArea = (
  type: PriorityObjectVerificationType,
): boolean =>
  type === PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea ||
  type === PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea;

const schema = z.object({
  code: z.string().trim().min(1, "Mã là bắt buộc.").max(50),
  name: z.string().trim().min(1, "Tên là bắt buộc.").max(255),
  score: z.number().int().min(0, "Điểm phải lớn hơn hoặc bằng 0."),
  description: z.string().trim().max(1000),
  isActive: z.boolean(),
  verificationType: z.enum([
    PRIORITY_OBJECT_VERIFICATION_TYPE.None,
    PRIORITY_OBJECT_VERIFICATION_TYPE.ImageEvidence,
    PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea,
    PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea,
  ]),
  evidenceInstructions: z.string().trim().max(1000),
  maxEvidenceFiles: z.number().int().min(0).max(10),
  maxEvidenceFileSizeBytes: z.number().int().min(1),
});

type Values = z.infer<typeof schema>;

function defaultValuesFrom(priorityObject: PriorityObject | null): Values {
  return {
    code: priorityObject?.code ?? "",
    name: priorityObject?.name ?? "",
    score: priorityObject?.score ?? 0,
    description: priorityObject?.description ?? "",
    isActive: priorityObject?.isActive ?? true,
    verificationType:
      priorityObject?.verificationType ??
      PRIORITY_OBJECT_VERIFICATION_TYPE.None,
    evidenceInstructions: priorityObject?.evidenceInstructions ?? "",
    maxEvidenceFiles:
      priorityObject?.maxEvidenceFiles ?? EVIDENCE_DEFAULTS.maxFiles,
    maxEvidenceFileSizeBytes:
      priorityObject?.maxEvidenceFileSizeBytes ??
      EVIDENCE_DEFAULTS.maxFileSizeMb * 1024 * 1024,
  };
}

export function PriorityObjectFormDialog({
  open,
  priorityObject,
  isSubmitting,
  onOpenChange,
  onCreate,
  onUpdate,
}: {
  open: boolean;
  priorityObject: PriorityObject | null;
  isSubmitting: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (input: CreatePriorityObjectInput) => Promise<void>;
  onUpdate: (id: string, input: UpdatePriorityObjectInput) => Promise<void>;
}) {
  const isEdit = Boolean(priorityObject);
  const form = useForm({
    defaultValues: defaultValuesFrom(priorityObject),
    validators: { onSubmit: schema },
    onSubmit: async ({ value }) => {
      const verificationType = value.verificationType;
      const evidenceInstructions = value.evidenceInstructions.trim();
      const wantsEvidence = verificationRequiresEvidence(verificationType);
      const payload = {
        name: value.name.trim(),
        score: value.score,
        description: value.description.trim() || undefined,
        isActive: value.isActive,
        verificationType,
        evidenceInstructions: wantsEvidence
          ? evidenceInstructions || undefined
          : undefined,
        maxEvidenceFiles: wantsEvidence ? value.maxEvidenceFiles : 0,
        maxEvidenceFileSizeBytes: wantsEvidence
          ? value.maxEvidenceFileSizeBytes
          : 0,
      };

      if (priorityObject) {
        await onUpdate(priorityObject.id, payload);
      } else {
        await onCreate({
          code: value.code.trim(),
          ...payload,
        });
      }
    },
  });

  const firstError = (errors: unknown[]) => getFormErrorMessage(errors[0]);

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(760px,calc(100vh-2rem))] w-full max-w-xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa đối tượng ưu tiên" : "Thêm đối tượng ưu tiên"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Khai báo nhóm đối tượng, điểm cộng và hình thức xác minh hồ sơ.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form
              .handleSubmit()
              .catch((error: unknown) =>
                toast.error(
                  error instanceof Error
                    ? error.message
                    : "Không thể lưu đối tượng ưu tiên.",
                ),
              );
          }}
        >
          <form.Subscribe selector={(state) => state.values.verificationType}>
            {(verificationType) => {
              const showEvidence =
                verificationRequiresEvidence(verificationType);
              const showArea = verificationRequiresArea(verificationType);
              return (
                <div className="grid gap-5 px-1 py-4">
                  <div className="grid gap-5 sm:grid-cols-2">
                    <form.Field name="code">
                      {(field) => (
                        <Field>
                          <FieldLabel htmlFor="priority-code">
                            Mã đối tượng
                          </FieldLabel>
                          <Input
                            id="priority-code"
                            value={field.state.value}
                            disabled={isEdit || isSubmitting}
                            onBlur={field.handleBlur}
                            onChange={(event) =>
                              field.handleChange(event.target.value)
                            }
                          />
                          {firstError(field.state.meta.errors) ? (
                            <FieldError>
                              {firstError(field.state.meta.errors)}
                            </FieldError>
                          ) : null}
                        </Field>
                      )}
                    </form.Field>
                    <form.Field name="score">
                      {(field) => (
                        <Field>
                          <FieldLabel htmlFor="priority-score">
                            Điểm ưu tiên
                          </FieldLabel>
                          <Input
                            id="priority-score"
                            type="number"
                            min={0}
                            step={1}
                            value={field.state.value}
                            disabled={isSubmitting}
                            onBlur={field.handleBlur}
                            onChange={(event) =>
                              field.handleChange(Number(event.target.value))
                            }
                          />
                          {firstError(field.state.meta.errors) ? (
                            <FieldError>
                              {firstError(field.state.meta.errors)}
                            </FieldError>
                          ) : null}
                        </Field>
                      )}
                    </form.Field>
                  </div>
                  <form.Field name="name">
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor="priority-name">
                          Tên hiển thị
                        </FieldLabel>
                        <Input
                          id="priority-name"
                          value={field.state.value}
                          disabled={isSubmitting}
                          onBlur={field.handleBlur}
                          onChange={(event) =>
                            field.handleChange(event.target.value)
                          }
                        />
                        {firstError(field.state.meta.errors) ? (
                          <FieldError>
                            {firstError(field.state.meta.errors)}
                          </FieldError>
                        ) : null}
                      </Field>
                    )}
                  </form.Field>
                  <form.Field name="description">
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor="priority-description">
                          Mô tả
                        </FieldLabel>
                        <Textarea
                          id="priority-description"
                          value={field.state.value}
                          disabled={isSubmitting}
                          onBlur={field.handleBlur}
                          onChange={(event) =>
                            field.handleChange(event.target.value)
                          }
                        />
                        {firstError(field.state.meta.errors) ? (
                          <FieldError>
                            {firstError(field.state.meta.errors)}
                          </FieldError>
                        ) : null}
                      </Field>
                    )}
                  </form.Field>

                  <div className="rounded-md border bg-muted/20 px-4 py-4">
                    <div className="mb-3">
                      <FieldLabel>Hình thức xác minh</FieldLabel>
                      <p className="text-sm text-muted-foreground">
                        Quyết định hồ sơ sinh viên cần đính kèm ảnh minh chứng
                        và/hoặc thuộc địa bàn được phép.
                      </p>
                    </div>
                    <form.Field name="verificationType">
                      {(field) => (
                        <Field>
                          <Select
                            value={field.state.value}
                            disabled={isSubmitting}
                            onValueChange={(val) => {
                              if (
                                VERIFICATION_TYPE_VALUES.includes(
                                  val as PriorityObjectVerificationType,
                                )
                              ) {
                                field.handleChange(
                                  val as PriorityObjectVerificationType,
                                );
                              }
                            }}
                          >
                            <SelectTrigger id="priority-verification-type">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {VERIFICATION_TYPE_VALUES.map((value) => (
                                <SelectItem key={value} value={value}>
                                  {
                                    PRIORITY_OBJECT_VERIFICATION_TYPE_LABELS[
                                      value
                                    ]
                                  }
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {firstError(field.state.meta.errors) ? (
                            <FieldError>
                              {firstError(field.state.meta.errors)}
                            </FieldError>
                          ) : null}
                        </Field>
                      )}
                    </form.Field>

                    {showEvidence ? (
                      <div className="mt-4 grid gap-4 sm:grid-cols-2">
                        <form.Field name="maxEvidenceFiles">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor="priority-max-files">
                                Số file tối đa
                              </FieldLabel>
                              <Input
                                id="priority-max-files"
                                type="number"
                                min={1}
                                max={10}
                                step={1}
                                value={field.state.value}
                                disabled={isSubmitting}
                                onBlur={field.handleBlur}
                                onChange={(event) =>
                                  field.handleChange(Number(event.target.value))
                                }
                              />
                              {firstError(field.state.meta.errors) ? (
                                <FieldError>
                                  {firstError(field.state.meta.errors)}
                                </FieldError>
                              ) : null}
                            </Field>
                          )}
                        </form.Field>
                        <form.Field name="maxEvidenceFileSizeBytes">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor="priority-max-size">
                                Dung lượng tối đa (MB)
                              </FieldLabel>
                              <Input
                                id="priority-max-size"
                                type="number"
                                min={1}
                                step={1}
                                value={Math.max(
                                  1,
                                  Math.round(field.state.value / (1024 * 1024)),
                                )}
                                disabled={isSubmitting}
                                onBlur={field.handleBlur}
                                onChange={(event) =>
                                  field.handleChange(
                                    Math.max(1, Number(event.target.value)) *
                                      1024 *
                                      1024,
                                  )
                                }
                              />
                              {firstError(field.state.meta.errors) ? (
                                <FieldError>
                                  {firstError(field.state.meta.errors)}
                                </FieldError>
                              ) : null}
                            </Field>
                          )}
                        </form.Field>
                        <form.Field name="evidenceInstructions">
                          {(field) => (
                            <Field className="sm:col-span-2">
                              <FieldLabel htmlFor="priority-instructions">
                                Hướng dẫn nộp minh chứng
                              </FieldLabel>
                              <Textarea
                                id="priority-instructions"
                                placeholder="Ví dụ: Chụp rõ sổ hộ khẩu trang đầu tiên có tên sinh viên."
                                value={field.state.value}
                                disabled={isSubmitting}
                                onBlur={field.handleBlur}
                                onChange={(event) =>
                                  field.handleChange(event.target.value)
                                }
                              />
                              {firstError(field.state.meta.errors) ? (
                                <FieldError>
                                  {firstError(field.state.meta.errors)}
                                </FieldError>
                              ) : null}
                            </Field>
                          )}
                        </form.Field>
                      </div>
                    ) : null}

                    {showArea ? (
                      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-dashed bg-background px-3 py-3">
                        <div>
                          <p className="text-sm font-medium">
                            Địa bàn được chấp nhận
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Sinh viên phải thuộc một trong các địa bàn dưới đây
                            mới được áp dụng đối tượng.
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">
                            {priorityObject?.eligibleAreaCount ?? 0} địa bàn
                          </Badge>
                          {priorityObject ? (
                            <EligibleAreasDialog
                              priorityObjectId={priorityObject.id}
                              priorityObjectName={priorityObject.name}
                              priorityObjectCode={priorityObject.code}
                              triggerLabel="Quản lý địa bàn"
                              triggerVariant="outline"
                              triggerSize="sm"
                              disabled={!isEdit}
                            />
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <form.Field name="isActive">
                    {(field) => (
                      <div className="flex items-center justify-between rounded-md border px-3 py-3">
                        <div>
                          <FieldLabel htmlFor="priority-active">
                            Đang áp dụng
                          </FieldLabel>
                          <p className="text-sm text-muted-foreground">
                            Cho phép chọn đối tượng này trong hồ sơ đăng ký mới.
                          </p>
                        </div>
                        <Switch
                          id="priority-active"
                          checked={field.state.value}
                          disabled={isSubmitting}
                          onCheckedChange={field.handleChange}
                        />
                      </div>
                    )}
                  </form.Field>
                </div>
              );
            }}
          </form.Subscribe>
          <ResponsiveDialogFooter className="border-t px-1 py-4">
            <Button
              type="button"
              variant="outline"
              disabled={isSubmitting}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Đang lưu..." : "Lưu đối tượng"}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

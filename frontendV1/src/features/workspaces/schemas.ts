/** Client-side validation mirroring `qnu/domains/workspaces/schemas.py`. */

import { z } from "zod";

export const workspaceCodeSchema = z
  .string()
  .trim()
  .min(2, "Mã workspace tối thiểu 2 ký tự.")
  .max(64, "Mã workspace tối đa 64 ký tự.")
  .regex(
    /^[a-z0-9]+(?:[-_][a-z0-9]+)*$/,
    "Chỉ dùng chữ thường, số, '-' hoặc '_' và không bắt đầu/kết thúc bằng dấu phân cách.",
  );

export const workspaceNameSchema = z
  .string()
  .trim()
  .min(2, "Tên workspace tối thiểu 2 ký tự.")
  .max(255, "Tên workspace tối đa 255 ký tự.");

export const workspaceDescriptionSchema = z
  .string()
  .trim()
  .max(2000, "Mô tả tối đa 2000 ký tự.");

export const workspaceCreateSchema = z.object({
  code: workspaceCodeSchema,
  name: workspaceNameSchema,
  description: workspaceDescriptionSchema,
});

export const workspaceUpdateSchema = z.object({
  /**
   * Present only so the edit form can reuse one value shape. `code` is never
   * sent: `WorkspaceUpdateRequest` does not accept it.
   */
  code: z.string(),
  name: workspaceNameSchema,
  description: workspaceDescriptionSchema,
});

export const workspaceRoleSchema = z.enum([
  "admin",
  "editor",
  "reviewer",
  "member",
]);

export const memberCreateSchema = z.object({
  actor_ref: z
    .string()
    .trim()
    .min(2, "actor_ref tối thiểu 2 ký tự.")
    .max(200, "actor_ref tối đa 200 ký tự."),
  display_name: z.string().trim().max(255, "Tên hiển thị tối đa 255 ký tự."),
  role: workspaceRoleSchema,
});

export const quotaSchema = z.object({
  /** Empty string means "chưa đặt giới hạn"; it is not zero. */
  monthly_token_limit: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || /^\d+$/.test(value),
      "Giới hạn token phải là số nguyên không âm.",
    )
    .refine(
      (value) => value === "" || Number(value) <= 1_000_000_000_000_000,
      "Giới hạn token quá lớn.",
    ),
  is_blocked: z.boolean(),
});

export type WorkspaceCreateValues = z.infer<typeof workspaceCreateSchema>;
export type WorkspaceUpdateValues = z.infer<typeof workspaceUpdateSchema>;
export type MemberCreateValues = z.infer<typeof memberCreateSchema>;
export type QuotaValues = z.infer<typeof quotaSchema>;

export const WORKSPACE_ROLE_LABELS: Record<
  z.infer<typeof workspaceRoleSchema>,
  string
> = {
  admin: "Quản trị workspace",
  editor: "Biên tập",
  reviewer: "Duyệt nội dung",
  member: "Thành viên",
};

export const MEMBER_STATUS_LABELS: Record<
  "active" | "pending" | "revoked",
  string
> = {
  active: "Đang hoạt động",
  pending: "Đang chờ",
  revoked: "Đã thu hồi",
};

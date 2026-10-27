import { z } from "zod";
import { pageSearchSchema } from "@/features/workspaces/search";
export const jobKindSchema = z.enum([
  "ocr",
  "compiler",
  "index",
  "auto_review",
  "review",
  "spelling",
  "turn",
  "backup",
]);
export const operationsSearchSchema = pageSearchSchema.extend({
  view: z.enum(["jobs", "backups", "storage"]).optional(),
  backupId: z.string().min(1).max(64).optional(),
  cleanupActionId: z.string().min(1).max(64).optional(),
  kind: jobKindSchema.optional(),
  status: z.string().min(1).max(16).optional(),
  collectionId: z.string().min(1).max(64).optional(),
  jobId: z.string().min(1).max(64).optional(),
  jobKind: jobKindSchema.optional(),
  lifecycleActionId: z.string().min(1).max(64).optional(),
  operationActionId: z.string().min(1).max(64).optional(),
});
export type OperationsSearch = z.infer<typeof operationsSearchSchema>;

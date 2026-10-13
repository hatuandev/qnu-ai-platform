import { createFileRoute } from "@tanstack/react-router";
import { BackupPolicyPage } from "@/features/backups/backup-policy-page";
export const Route = createFileRoute("/settings/backups/policy")({
  component: BackupPolicyPage,
});

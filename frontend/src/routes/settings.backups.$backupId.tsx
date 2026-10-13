import { createFileRoute } from "@tanstack/react-router";
import { BackupDetailPage } from "@/features/backups/backup-detail-page";

export const Route = createFileRoute("/settings/backups/$backupId")({
  component: Page,
});
function Page() {
  const { backupId } = Route.useParams();
  return <BackupDetailPage backupId={backupId} />;
}

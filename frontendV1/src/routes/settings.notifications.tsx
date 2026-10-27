import { createFileRoute } from "@tanstack/react-router";
import { AccessDenied } from "@/components/admin/access-denied";
import { SettingsSection } from "@/features/settings/settings-section";
import { useRbac } from "@/rbac/context";
export const Route = createFileRoute("/settings/notifications")({
  component: Page,
});
function Page() {
  const { can } = useRbac();
  return can("settings.read") ? (
    <SettingsSection section="Notifications" />
  ) : (
    <AccessDenied />
  );
}

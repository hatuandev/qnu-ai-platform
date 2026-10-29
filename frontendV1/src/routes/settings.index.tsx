import { createFileRoute } from "@tanstack/react-router";
import { QnuSettingsHub } from "@/features/settings/qnu-settings-hub";

export const Route = createFileRoute("/settings/")({ component: Page });
function Page() {
  return <QnuSettingsHub />;
}

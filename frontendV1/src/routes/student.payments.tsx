import { createFileRoute } from "@tanstack/react-router";
import { AccessDenied } from "@/components/admin/access-denied";
import { StudentPaymentPage } from "@/features/payments/student-payment-page";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/student/payments")({
  component: StudentPaymentsRoute,
});

function StudentPaymentsRoute() {
  const { can } = useRbac();

  if (!can("ktx.payments.view")) return <AccessDenied />;

  return <StudentPaymentPage canSubmit={can("ktx.payments.submit")} />;
}

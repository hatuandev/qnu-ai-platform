import { createFileRoute } from "@tanstack/react-router";
import { AccessDenied } from "@/components/admin/access-denied";
import { InvoiceDetailPage } from "@/features/invoices/invoice-detail";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/invoices/$invoiceId")({
  component: InvoiceDetailRoute,
});

function InvoiceDetailRoute() {
  const { invoiceId } = Route.useParams();
  const { can } = useRbac();
  if (!can("ktx.invoices.view")) return <AccessDenied />;
  return (
    <div className="space-y-6">
      <InvoiceDetailPage
        invoiceId={invoiceId}
        canPay={can("ktx.invoices.pay")}
        canVoid={can("ktx.invoices.void")}
        canViewSubmissions={can("ktx.payments.view")}
        canVerifySubmission={can("ktx.payments.verify")}
      />
    </div>
  );
}

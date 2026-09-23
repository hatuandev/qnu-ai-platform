import { createFileRoute } from "@tanstack/react-router";
import { PaymentConfigurationsPage } from "@/features/payment-configurations/payment-configurations-page";

export const Route = createFileRoute("/payment-configurations/")({
  component: PaymentConfigurationsPage,
});

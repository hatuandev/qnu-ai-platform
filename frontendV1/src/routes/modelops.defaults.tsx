import { createFileRoute } from "@tanstack/react-router";
import { DefaultsPage } from "@/features/modelops/defaults-page";

export const Route = createFileRoute("/modelops/defaults")({
  component: DefaultsPage,
});

import { createFileRoute } from "@tanstack/react-router";
import { EndpointsPage } from "@/features/modelops/endpoints/endpoints-page";

export const Route = createFileRoute("/modelops/endpoints")({
  component: EndpointsPage,
});

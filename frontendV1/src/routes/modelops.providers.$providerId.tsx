import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/modelops/providers/$providerId")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/providers/$providerId", params });
  },
});

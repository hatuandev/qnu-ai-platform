import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/modelops/providers/")({
  beforeLoad: () => {
    throw redirect({ to: "/providers" });
  },
});

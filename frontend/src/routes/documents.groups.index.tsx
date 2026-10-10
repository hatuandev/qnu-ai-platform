import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/documents/groups/")({
  beforeLoad: () => {
    throw redirect({ to: "/documents" });
  },
});

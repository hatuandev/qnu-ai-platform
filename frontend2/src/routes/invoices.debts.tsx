import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/invoices/debts")({
  beforeLoad: () => {
    throw redirect({
      to: "/debts",
      search: { q: "", academicYearId: undefined },
    });
  },
});

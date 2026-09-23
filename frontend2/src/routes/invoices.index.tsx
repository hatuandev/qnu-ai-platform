import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { InvoicesPage } from "@/features/invoices/invoices-page";
import type { InvoiceStatus } from "@/features/invoices/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  status: z
    .enum(["unpaid", "partial", "paid", "cancelled"])
    .optional()
    .catch(undefined),
  academicYearId: z.string().optional().catch(undefined),
  registrationPeriodId: z.string().optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/invoices/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: InvoicesIndex,
});

function InvoicesIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  if (!can("ktx.invoices.view")) return <AccessDenied />;
  return (
    <InvoicesPage
      search={{
        q: String(search.q),
        status: search.status as InvoiceStatus | undefined,
        academicYearId: search.academicYearId,
        registrationPeriodId: search.registrationPeriodId,
        page: search.page,
        pageSize: search.pageSize,
      }}
      onSearch={(changes) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
      canGenerate={can("ktx.invoices.generate")}
    />
  );
}

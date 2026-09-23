import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { PaymentSubmissionsPage } from "@/features/payments/payment-submissions-page";
import type { PaymentSubmissionStatus } from "@/features/payments/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  status: z
    .enum(["submitted", "verified", "rejected", "cancelled"])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/payment-submissions/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: PaymentSubmissionsIndex,
});

function PaymentSubmissionsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();

  if (!can("ktx.payments.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ký túc xá / Tài chính"
        title="Đối soát thanh toán"
        description="Kiểm tra biên lai sinh viên đã nộp và cập nhật trạng thái thanh toán."
      />
      <PaymentSubmissionsPage
        search={{
          q: String(search.q),
          status: search.status as PaymentSubmissionStatus | undefined,
          page: search.page,
          pageSize: search.pageSize,
        }}
        onSearch={(changes) =>
          void navigate({ search: (previous) => ({ ...previous, ...changes }) })
        }
        canVerify={can("ktx.payments.verify")}
      />
    </div>
  );
}

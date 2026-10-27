import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import {
  NotificationsPage,
  type NotificationsSearch,
  notificationTypes,
} from "@/features/notifications/notifications-page";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  type: z.enum(notificationTypes).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/notifications/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: NotificationsRoute,
});

function NotificationsRoute() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/notifications/" });
  return (
    <NotificationsPage
      search={search}
      onSearchChange={(changes: Partial<NotificationsSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}

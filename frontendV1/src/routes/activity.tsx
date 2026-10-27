import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Activity } from "lucide-react";
import { useMemo, useState } from "react";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { DataTableFacetedFilter } from "@/components/admin/data-table/data-table-faceted-filter";
import { EmptyState } from "@/components/admin/empty-state";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ActivityDetailSheet } from "@/features/activity/activity-detail-sheet";
import { ActivityItem } from "@/features/activity/activity-item";
import { activityEvents } from "@/features/activity/data";
import type { ActivityEvent } from "@/features/activity/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.string().catch(""),
  type: z
    .union([z.literal(""), z.enum(["users", "roles", "settings", "security"])])
    .catch(""),
  actor: z.string().catch(""),
});

export const Route = createFileRoute("/activity")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ActivityPage,
});

const typeOptions = [
  { value: "users", label: "Người dùng" },
  { value: "roles", label: "Vai trò" },
  { value: "settings", label: "Cài đặt" },
  { value: "security", label: "Bảo mật" },
];

function eventGroup(event: ActivityEvent) {
  const days = Math.floor(
    (Date.now() - new Date(event.createdAt).getTime()) / 86_400_000,
  );
  return days < 1 ? "Hôm nay" : days < 2 ? "Hôm qua" : "Trước đó";
}

function ActivityPage() {
  const { can } = useRbac();
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/activity" });
  const [selectedEvent, setSelectedEvent] = useState<ActivityEvent | null>(
    null,
  );
  const [isLoading] = useState(false);
  const [isError] = useState(false);
  const queryText = search.q.trim().toLowerCase();
  const actors = useMemo(
    () =>
      [...new Set(activityEvents.map((event) => event.actor))].map((actor) => ({
        value: actor,
        label: actor,
        count: activityEvents.filter((event) => event.actor === actor).length,
      })),
    [],
  );
  const filteredEvents = useMemo(
    () =>
      activityEvents.filter((event) => {
        const matchesQuery = [event.actor, event.action, event.subject]
          .join(" ")
          .toLowerCase()
          .includes(queryText);
        const matchesType = !search.type || event.resource === search.type;
        const matchesActor = !search.actor || event.actor === search.actor;
        return matchesQuery && matchesType && matchesActor;
      }),
    [queryText, search.actor, search.type],
  );
  const groups = ["Hôm nay", "Hôm qua", "Trước đó"]
    .map((label) => ({
      label,
      events: filteredEvents.filter((event) => eventGroup(event) === label),
    }))
    .filter((group) => group.events.length);
  const updateSearch = (changes: Partial<typeof search>) =>
    void navigate({ search: (previous) => ({ ...previous, ...changes }) });
  const resetFilters = () => updateSearch({ q: "", type: "", actor: "" });
  if (!can("activity.read")) return <AccessDenied />;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Giám sát"
        title="Hoạt động"
        description="Xem lại các sự kiện quản trị gần đây trong không gian làm việc."
      />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Input
          value={search.q}
          onChange={(event) => updateSearch({ q: event.target.value })}
          placeholder="Tìm kiếm hoạt động..."
          aria-label="Tìm kiếm hoạt động"
          className="sm:max-w-sm"
        />
        <DataTableFacetedFilter
          title="Loại"
          options={typeOptions}
          selectedValues={search.type ? [search.type] : []}
          onChange={(values) =>
            updateSearch({ type: (values[0] ?? "") as typeof search.type })
          }
        />
        <DataTableFacetedFilter
          title="Người thực hiện"
          options={actors}
          selectedValues={search.actor ? [search.actor] : []}
          onChange={(values) => updateSearch({ actor: values[0] ?? "" })}
        />
        {search.q || search.type || search.actor ? (
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            Đặt lại bộ lọc
          </Button>
        ) : null}
      </div>
      {isLoading ? (
        <div className="overflow-hidden rounded-lg border bg-card">
          {["one", "two", "three", "four"].map((row) => (
            <div
              key={row}
              className="flex gap-3 border-b px-4 py-4 last:border-0"
            >
              <Skeleton className="size-8 rounded-full" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-64" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="flex min-h-48 flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-card px-5 text-center">
          <p className="font-medium">Không thể tải hoạt động</p>
          <p className="text-sm text-muted-foreground">
            Hãy thử tải lại danh sách sự kiện.
          </p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Thử lại
          </Button>
        </div>
      ) : groups.length ? (
        <div className="space-y-6">
          {groups.map((group) => (
            <section
              key={group.label}
              aria-labelledby={`activity-${group.label}`}
            >
              <h2
                id={`activity-${group.label}`}
                className="mb-2 text-sm font-semibold text-muted-foreground"
              >
                {group.label}
              </h2>
              <div className="overflow-hidden rounded-lg border bg-card">
                {group.events.map((event) => (
                  <ActivityItem
                    key={event.id}
                    event={event}
                    onClick={() => setSelectedEvent(event)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Activity}
          title={
            search.q || search.type || search.actor
              ? "Không có hoạt động phù hợp"
              : "Chưa có hoạt động nào"
          }
          description={
            search.q || search.type || search.actor
              ? "Hãy thử từ khóa hoặc bộ lọc khác."
              : "Các sự kiện quản trị sẽ xuất hiện tại đây."
          }
          action={
            search.q || search.type || search.actor
              ? { label: "Đặt lại bộ lọc", onClick: resetFilters }
              : undefined
          }
        />
      )}
      <ActivityDetailSheet
        event={selectedEvent}
        open={Boolean(selectedEvent)}
        onOpenChange={(open) => {
          if (!open) setSelectedEvent(null);
        }}
      />
    </div>
  );
}

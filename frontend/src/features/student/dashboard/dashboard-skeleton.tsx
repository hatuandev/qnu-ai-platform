import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function StudentDashboardSkeleton() {
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header skeleton (Profile banner) */}
      <div className="flex flex-col gap-3.5 rounded-xl border bg-card p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex items-center gap-3.5">
          <Skeleton className="size-10 shrink-0 rounded-full sm:size-11" />
          <div className="min-w-0 space-y-1.5">
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-44 sm:w-56" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
            <div className="flex items-center gap-3">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="hidden h-3.5 w-36 sm:inline-block" />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-center">
          <Skeleton className="hidden h-4 w-20 sm:inline-block" />
          <Skeleton className="h-8 w-24 rounded-md" />
        </div>
      </div>

      {/* Hero / Status section skeleton */}
      <Card>
        <CardContent className="space-y-5 p-4 sm:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-5 w-28 rounded-full" />
              </div>
              <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-20 rounded-full" />
                <Skeleton className="h-5 w-40" />
              </div>
              <Skeleton className="h-4 w-56" />
            </div>
            <Skeleton className="h-9 w-36 rounded-md" />
          </div>

          {/* Stepper skeleton */}
          <div className="grid gap-2 border-t pt-4 sm:flex sm:items-center sm:gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-2">
                {i > 1 ? (
                  <Skeleton className="hidden h-px w-6 sm:block sm:w-9" />
                ) : null}
                <Skeleton className="size-6 shrink-0 rounded-full" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick stats grid skeleton (2 cols on mobile, 4 on desktop) */}
      <div className="grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="flex items-start gap-2.5 p-3 sm:gap-3 sm:p-4">
              <Skeleton className="size-8 shrink-0 rounded-lg sm:size-9" />
              <div className="min-w-0 flex-1 space-y-1.5">
                <Skeleton className="h-3 w-12" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-3 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Room & Invoice grid skeleton (2 cols) */}
      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        {/* Room card */}
        <Card>
          <CardHeader className="space-y-1 pb-3">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-20 rounded-full" />
            </div>
            <Skeleton className="h-3.5 w-40" />
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <Skeleton className="size-10 shrink-0 rounded-lg" />
              <div className="min-w-0 flex-1 space-y-1.5">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-28" />
              </div>
            </div>
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-8 w-28 rounded-md" />
          </CardContent>
        </Card>

        {/* Invoice card */}
        <Card>
          <CardHeader className="space-y-1 pb-3">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-20 rounded-full" />
            </div>
            <Skeleton className="h-3.5 w-44" />
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16 rounded-full" />
              </div>
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-28" />
            </div>
            <Skeleton className="h-8 w-full rounded-md" />
          </CardContent>
        </Card>
      </div>

      {/* Support banner skeleton */}
      <Card>
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3.5">
              <Skeleton className="size-10 shrink-0 rounded-xl sm:size-11" />
              <div className="min-w-0 space-y-1.5">
                <Skeleton className="h-4 w-48 sm:w-60" />
                <Skeleton className="h-3.5 w-64 sm:w-80" />
              </div>
            </div>
            <Skeleton className="h-9 w-32 rounded-md" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

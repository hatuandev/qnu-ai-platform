import { Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DeadlineCountdownBadge } from "@/features/student/dashboard/status-hero";
import {
  applicationStatusLabels,
  applicationStatusVariants,
  type MyApplication,
  type OpenRegistrationPeriod,
} from "@/features/student/types";
import { formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

export function ApplicationRow({
  application,
  onWithdraw,
  isWithdrawing,
  canWithdrawApplications,
}: {
  application: MyApplication;
  onWithdraw: (application: MyApplication) => void;
  isWithdrawing: boolean;
  canWithdrawApplications: boolean;
}) {
  const canWithdraw =
    application.status === "draft" || application.status === "submitted";
  return (
    <div className="flex flex-col gap-4 rounded-lg border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold">{application.registrationPeriodName}</p>
          <Badge variant={applicationStatusVariants[application.status]}>
            {applicationStatusLabels[application.status]}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Mã hồ sơ:{" "}
          <span className="font-medium text-foreground">
            {application.applicationCode}
          </span>
        </p>
        <p className="text-xs text-muted-foreground">
          Nộp ngày{" "}
          {application.submittedAt
            ? formatDateValue(application.submittedAt)
            : formatDateValue(application.created)}
          {application.requestedRoomTypeName
            ? ` · ${application.requestedRoomTypeName}`
            : ""}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {application.status === "approved" ||
        application.status === "assigned" ? (
          <Button asChild variant="outline" size="sm">
            <Link
              to="/student/room-selection"
              search={{
                registrationPeriodId: application.registrationPeriodId,
              }}
            >
              Chọn phòng <ArrowRight />
            </Link>
          </Button>
        ) : null}
        {canWithdraw && canWithdrawApplications ? (
          <Button
            variant="outline"
            size="sm"
            disabled={isWithdrawing}
            onClick={() => onWithdraw(application)}
          >
            Rút hồ sơ
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function PeriodCard({
  period,
  application,
  onWithdraw,
  isWithdrawing,
  canWithdrawApplications,
}: {
  period: OpenRegistrationPeriod;
  application?: MyApplication;
  onWithdraw: (application: MyApplication) => void;
  isWithdrawing: (application: MyApplication) => boolean;
  canWithdrawApplications: boolean;
}) {
  return (
    <Card className="border-primary/25 bg-gradient-to-r from-card via-card to-primary/5 transition-all hover:border-primary/50 hover:shadow-sm">
      <CardHeader className="gap-2 pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base font-bold sm:text-lg">
                {period.name}
              </CardTitle>
              <Badge variant="success">Đang nhận hồ sơ</Badge>
              <DeadlineCountdownBadge
                targetDate={period.endAt}
                prefix="Đóng sau"
              />
            </div>
            <CardDescription className="text-xs sm:text-sm">
              {period.academicYearCode} · Mở từ{" "}
              {formatDateValue(period.startAt)} · Hạn nộp{" "}
              {formatDateValue(period.endAt)} · Đã nhận{" "}
              {period.applicationCount} hồ sơ
            </CardDescription>
          </div>
          {!application ? (
            <Button
              asChild
              size="default"
              className="shrink-0 font-semibold shadow-sm"
            >
              <Link to="/student/register">
                <Sparkles className="size-4" />
                Đăng ký ngay <ArrowRight className="size-4" />
              </Link>
            </Button>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {period.note ? (
          <p className="rounded-lg bg-muted/60 px-3 py-2 text-xs text-muted-foreground sm:text-sm">
            {period.note}
          </p>
        ) : null}
        {application ? (
          <ApplicationRow
            application={application}
            onWithdraw={onWithdraw}
            isWithdrawing={isWithdrawing(application)}
            canWithdrawApplications={canWithdrawApplications}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

/** Section hiển thị các đợt mở để đặt ở VỊ TRÍ ĐẦU TRANG */
export function OpenPeriodsSection({
  periods,
  applications,
  onWithdraw,
  isWithdrawing,
  canWithdrawApplications,
  className,
}: {
  periods: OpenRegistrationPeriod[];
  applications: MyApplication[];
  onWithdraw: (application: MyApplication) => void;
  isWithdrawing: (application: MyApplication) => boolean;
  canWithdrawApplications: boolean;
  className?: string;
}) {
  const registeredPeriodIds = new Set(
    applications.map((application) => application.registrationPeriodId),
  );
  const periodsToApply = periods.filter(
    (period) => !registeredPeriodIds.has(period.id),
  );

  if (!periodsToApply.length) return null;

  return (
    <section className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-base font-bold tracking-tight text-foreground sm:text-lg">
          <span>Đợt đăng ký đang mở</span>
          <Badge variant="default" className="text-xs">
            {periodsToApply.length} đợt khả dụng
          </Badge>
        </h2>
      </div>
      <div className="grid gap-3 sm:gap-4">
        {periodsToApply.map((period) => (
          <PeriodCard
            key={period.id}
            period={period}
            onWithdraw={onWithdraw}
            isWithdrawing={isWithdrawing}
            canWithdrawApplications={canWithdrawApplications}
          />
        ))}
      </div>
    </section>
  );
}

/** Section hiển thị hồ sơ các đợt khác (đặt ở cuối trang) */
export function OtherApplicationsSection({
  applications,
  focusApplicationId,
  onWithdraw,
  isWithdrawing,
  canWithdrawApplications,
  className,
}: {
  applications: MyApplication[];
  focusApplicationId?: string;
  onWithdraw: (application: MyApplication) => void;
  isWithdrawing: (application: MyApplication) => boolean;
  canWithdrawApplications: boolean;
  className?: string;
}) {
  const otherApplications = applications.filter(
    (application) => application.id !== focusApplicationId,
  );

  if (!otherApplications.length) return null;

  return (
    <section className={cn("space-y-3", className)}>
      <h2 className="text-base font-semibold tracking-tight sm:text-lg">
        Hồ sơ các đợt khác
      </h2>
      <div className="grid gap-3 sm:gap-4">
        {otherApplications.map((application) => (
          <ApplicationRow
            key={application.id}
            application={application}
            onWithdraw={onWithdraw}
            isWithdrawing={isWithdrawing(application)}
            canWithdrawApplications={canWithdrawApplications}
          />
        ))}
      </div>
    </section>
  );
}

export function ApplicationsSection({
  periods,
  applications,
  focusApplicationId,
  onWithdraw,
  isWithdrawing,
  canWithdrawApplications,
  className,
}: {
  periods: OpenRegistrationPeriod[];
  applications: MyApplication[];
  focusApplicationId?: string;
  onWithdraw: (application: MyApplication) => void;
  isWithdrawing: (application: MyApplication) => boolean;
  canWithdrawApplications: boolean;
  className?: string;
}) {
  const registeredPeriodIds = new Set(
    applications.map((application) => application.registrationPeriodId),
  );
  const periodsToApply = periods.filter(
    (period) => !registeredPeriodIds.has(period.id),
  );
  const otherApplications = applications.filter(
    (application) => application.id !== focusApplicationId,
  );

  if (!periodsToApply.length && !otherApplications.length) return null;

  return (
    <section className={cn("space-y-4", className)}>
      {periodsToApply.length ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">
            Đợt đăng ký đang mở
          </h2>
          <div className="grid gap-4">
            {periodsToApply.map((period) => (
              <PeriodCard
                key={period.id}
                period={period}
                onWithdraw={onWithdraw}
                isWithdrawing={isWithdrawing}
                canWithdrawApplications={canWithdrawApplications}
              />
            ))}
          </div>
        </div>
      ) : null}
      {otherApplications.length ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">
            Hồ sơ các đợt khác
          </h2>
          <div className="grid gap-4">
            {otherApplications.map((application) => (
              <ApplicationRow
                key={application.id}
                application={application}
                onWithdraw={onWithdraw}
                isWithdrawing={isWithdrawing(application)}
                canWithdrawApplications={canWithdrawApplications}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

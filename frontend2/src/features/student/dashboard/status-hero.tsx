import { Link } from "@tanstack/react-router";
import { AlertCircle, ArrowRight, Check, Clock } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  journeyStep,
  journeySteps,
  statusDescriptions,
  useLiveCountdown,
} from "@/features/student/dashboard/helpers";
import {
  applicationStatusLabels,
  applicationStatusVariants,
  type MyApplication,
  type OpenRegistrationPeriod,
  type StudentApplicationStatus,
  type StudentRoomSelection,
} from "@/features/student/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

export function DeadlineCountdownBadge({
  targetDate,
  prefix = "Hạn chót",
}: {
  targetDate?: string | null;
  prefix?: string;
}) {
  const info = useLiveCountdown(targetDate);
  if (!info) return null;

  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <Clock className="size-3.5 shrink-0 text-muted-foreground" />
      <span className="text-muted-foreground">{prefix}:</span>
      <Badge variant={info.badgeVariant} className="px-1.5 py-0 text-[11px]">
        {info.detailedLabel}
      </Badge>
    </span>
  );
}

export function NextActionButton({
  application,
  selection,
}: {
  application: MyApplication;
  selection?: StudentRoomSelection | null;
}) {
  if (application.status === "draft") {
    return (
      <Button asChild>
        <Link to="/student/register">
          Hoàn tất và nộp hồ sơ <ArrowRight />
        </Link>
      </Button>
    );
  }
  if (application.status === "need_supplement") {
    return (
      <Button asChild variant="outline">
        <Link to="/student/registration-history">Xem hồ sơ</Link>
      </Button>
    );
  }
  if (selection?.currentSelection?.status === "checked_in") {
    return (
      <Button asChild variant="outline">
        <Link
          to="/student/room-selection"
          search={{ registrationPeriodId: application.registrationPeriodId }}
        >
          Xem chỗ ở <ArrowRight />
        </Link>
      </Button>
    );
  }
  if (selection?.currentSelection?.status === "assigned") {
    return (
      <Button asChild>
        <Link
          to="/student/room-selection"
          search={{ registrationPeriodId: application.registrationPeriodId }}
        >
          Xem chỗ ở <ArrowRight />
        </Link>
      </Button>
    );
  }
  if (selection?.currentSelection?.status === "selected") {
    return (
      <Button asChild variant="outline">
        <Link
          to="/student/room-selection"
          search={{ registrationPeriodId: application.registrationPeriodId }}
        >
          Xem lựa chọn <ArrowRight />
        </Link>
      </Button>
    );
  }
  if (
    application.status === "approved" &&
    selection &&
    selection.selectionStatus !== "open"
  ) {
    return (
      <Button asChild variant="outline">
        <Link
          to="/student/room-selection"
          search={{ registrationPeriodId: application.registrationPeriodId }}
        >
          Xem lịch chọn phòng <ArrowRight />
        </Link>
      </Button>
    );
  }
  if (application.status === "approved" || application.status === "assigned") {
    return (
      <Button asChild>
        <Link
          to="/student/room-selection"
          search={{ registrationPeriodId: application.registrationPeriodId }}
        >
          {application.status === "approved"
            ? "Chọn phòng ngay"
            : "Xem phòng đã xếp"}{" "}
          <ArrowRight />
        </Link>
      </Button>
    );
  }
  return null;
}

export function JourneyStepper({
  status,
  selection,
}: {
  status: StudentApplicationStatus;
  selection?: StudentRoomSelection | null;
}) {
  const current = journeyStep(status, selection);
  if (current < 0) return null;
  return (
    <ol className="grid gap-2 border-t pt-4 sm:flex sm:items-center sm:gap-2">
      {journeySteps.map((step, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li key={step} className="flex items-center gap-2">
            {index > 0 ? (
              <span
                className={cn(
                  "hidden h-px w-5 shrink-0 sm:block sm:w-9",
                  done || active ? "bg-primary" : "bg-border",
                )}
              />
            ) : null}
            <span
              className={cn(
                "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                done || active
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              {done ? <Check className="size-3.5" /> : index + 1}
            </span>
            <span
              className={cn(
                "text-sm whitespace-nowrap",
                active ? "font-semibold" : "text-muted-foreground",
              )}
            >
              {step}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function StatusHero({
  application,
  period,
  selection,
}: {
  application: MyApplication;
  period: OpenRegistrationPeriod | null | undefined;
  selection?: StudentRoomSelection | null;
}) {
  const isRoomSelectionPhase =
    application.status === "approved" && selection?.selectionStatus === "open";

  const deadline = isRoomSelectionPhase
    ? (period?.roomSelectionEndAt ?? selection?.selectionEndAt)
    : application.status === "approved"
      ? period?.roomSelectionEndAt
      : period?.endAt;

  const deadlinePrefix = isRoomSelectionPhase
    ? "Đợt chọn phòng đóng sau"
    : application.status === "approved"
      ? "Hạn chọn phòng"
      : "Hạn nộp";

  return (
    <Card>
      <CardContent className="space-y-5 p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-primary">
                Trạng thái hiện tại
              </p>
              {deadline ? (
                <DeadlineCountdownBadge
                  targetDate={deadline}
                  prefix={deadlinePrefix}
                />
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={applicationStatusVariants[application.status]}>
                {applicationStatusLabels[application.status]}
              </Badge>
              <span className="font-semibold">
                {application.registrationPeriodName}
              </span>
              <span className="text-sm text-muted-foreground">
                · {application.applicationCode}
              </span>
            </div>
            {deadline ? (
              <p className="text-sm text-muted-foreground">
                {deadlinePrefix}: {formatDateTimeValue(deadline)}
              </p>
            ) : null}
            <p className="text-sm text-muted-foreground">
              {statusDescriptions[application.status]}
            </p>
          </div>
          <div className="shrink-0">
            <NextActionButton application={application} selection={selection} />
          </div>
        </div>
        <JourneyStepper status={application.status} selection={selection} />
      </CardContent>
    </Card>
  );
}

function StatusAlerts({ application }: { application: MyApplication }) {
  if (application.status === "need_supplement") {
    return (
      <Alert variant="warning">
        <AlertCircle />
        <div>
          <AlertTitle>Hồ sơ cần bổ sung</AlertTitle>
          <AlertDescription>
            {application.reviewNote ||
              "Hãy theo dõi hướng dẫn từ cán bộ phụ trách để hoàn thiện hồ sơ."}
          </AlertDescription>
        </div>
      </Alert>
    );
  }
  if (application.status === "rejected") {
    return (
      <Alert variant="destructive">
        <AlertCircle />
        <div>
          <AlertTitle>Hồ sơ không được duyệt</AlertTitle>
          <AlertDescription>
            {application.reviewNote ||
              "Liên hệ phòng Công tác sinh viên nếu bạn cần hỗ trợ."}
          </AlertDescription>
        </div>
      </Alert>
    );
  }
  return null;
}

export function StatusHeroSection({
  application,
  period,
  selection,
}: {
  application: MyApplication;
  period: OpenRegistrationPeriod | null | undefined;
  selection?: StudentRoomSelection | null;
}) {
  return (
    <section className="space-y-3">
      <StatusHero
        application={application}
        period={period}
        selection={selection}
      />
      <StatusAlerts application={application} />
    </section>
  );
}

/** Banner CTA khi có đợt mở nhưng SV chưa có hồ sơ. */
export function OpenPeriodBanner({
  period,
}: {
  period: OpenRegistrationPeriod;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-primary">
              Cơ hội đăng ký
            </p>
            <DeadlineCountdownBadge
              targetDate={period.endAt}
              prefix="Đóng đơn sau"
            />
          </div>
          <p className="font-semibold">
            Đợt “{period.name}” đang mở nhận hồ sơ
          </p>
          <p className="text-sm text-muted-foreground">
            Hạn nộp: {formatDateTimeValue(period.endAt)}. Bạn chưa có hồ sơ đăng
            ký trong đợt này.
          </p>
        </div>
        <div className="shrink-0">
          <Button asChild>
            <Link to="/student/register">
              Đăng ký ngay <ArrowRight />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

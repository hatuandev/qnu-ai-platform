import { useEffect, useState } from "react";
import {
  applicationStatusLabels,
  type StudentApplicationStatus,
  type StudentRoomSelection,
} from "@/features/student/types";

export { applicationStatusLabels };

export const statusDescriptions: Record<StudentApplicationStatus, string> = {
  draft: "Hồ sơ đã lưu nhưng chưa nộp. Hoàn tất và nộp trước hạn đăng ký.",
  submitted: "Hồ sơ đã nộp và đang chờ hội đồng KTX xét duyệt.",
  need_supplement: "Hồ sơ cần bổ sung giấy tờ theo hướng dẫn của cán bộ.",
  approved: "Hồ sơ đã được duyệt. Bạn đủ điều kiện chọn phòng trong đợt.",
  assigned: "Bạn đã được xếp phòng. Kiểm tra thông tin phòng và nhận phòng.",
  rejected: "Hồ sơ không được duyệt trong đợt này.",
  cancelled: "Hồ sơ đã được rút và không còn hiệu lực.",
};

export const journeySteps = [
  "Nộp hồ sơ",
  "Chờ duyệt",
  "Đã duyệt",
  "Chọn phòng",
  "Nhận phòng",
];

export function journeyStep(
  status: StudentApplicationStatus,
  selection?: StudentRoomSelection | null,
): number {
  if (selection?.currentSelection?.status === "checked_in") return 4;
  if (selection?.currentSelection?.status === "assigned") return 4;
  if (selection?.currentSelection?.status === "selected") return 3;

  switch (status) {
    case "draft":
      return 0;
    case "submitted":
    case "need_supplement":
      return 1;
    case "approved":
      return 3;
    case "assigned":
      return 4;
    default:
      return -1;
  }
}

export function money(value: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

export type DeadlineUrgency = "expired" | "urgent" | "warning" | "normal";

export type DeadlineInfo = {
  diffMs: number;
  days: number;
  hours: number;
  minutes: number;
  isExpired: boolean;
  urgency: DeadlineUrgency;
  label: string;
  detailedLabel: string;
  badgeVariant: "destructive" | "warning" | "default" | "info" | "secondary";
};

export function getDeadlineStatus(value?: string | null): DeadlineInfo | null {
  if (!value) return null;
  const targetTime = new Date(value).getTime();
  if (Number.isNaN(targetTime)) return null;

  const now = Date.now();
  const diffMs = targetTime - now;

  if (diffMs <= 0) {
    const pastDays = Math.abs(Math.floor(diffMs / (1000 * 60 * 60 * 24)));
    return {
      diffMs,
      days: -pastDays,
      hours: 0,
      minutes: 0,
      isExpired: true,
      urgency: "expired",
      label: "Đã hết hạn",
      detailedLabel:
        pastDays > 0 ? `Đã quá hạn ${pastDays} ngày` : "Đã hết hạn",
      badgeVariant: "destructive",
    };
  }

  const totalMinutes = Math.floor(diffMs / (1000 * 60));
  const totalHours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const hours = totalHours % 24;
  const minutes = totalMinutes % 60;

  if (totalHours < 24) {
    const label =
      totalHours > 0
        ? `Còn ${totalHours} giờ ${minutes > 0 ? `${minutes}p` : ""}`
        : `Còn ${minutes} phút`;
    return {
      diffMs,
      days: 0,
      hours: totalHours,
      minutes,
      isExpired: false,
      urgency: "urgent",
      label,
      detailedLabel: label,
      badgeVariant: totalHours < 6 ? "destructive" : "warning",
    };
  }

  if (days <= 2) {
    const label = `Còn ${days} ngày ${hours > 0 ? `${hours}h` : ""}`;
    return {
      diffMs,
      days,
      hours,
      minutes,
      isExpired: false,
      urgency: "warning",
      label: `Còn ${days} ngày`,
      detailedLabel: label,
      badgeVariant: "warning",
    };
  }

  return {
    diffMs,
    days,
    hours,
    minutes,
    isExpired: false,
    urgency: "normal",
    label: `Còn ${days} ngày`,
    detailedLabel: `Còn ${days} ngày ${hours > 0 ? `${hours}h` : ""}`,
    badgeVariant: "info",
  };
}

/** React hook cập nhật đếm ngược theo thời gian thực (chu kỳ 30s) */
export function useLiveCountdown(
  targetDateStr?: string | null,
): DeadlineInfo | null {
  const [info, setInfo] = useState<DeadlineInfo | null>(() =>
    getDeadlineStatus(targetDateStr),
  );

  useEffect(() => {
    setInfo(getDeadlineStatus(targetDateStr));
    if (!targetDateStr) return;

    const timer = setInterval(() => {
      setInfo(getDeadlineStatus(targetDateStr));
    }, 30_000);

    return () => clearInterval(timer);
  }, [targetDateStr]);

  return info;
}

/** Days remaining until an ISO date string (negative if past). Null when no date. */
export function daysRemaining(value?: string | null): number | null {
  const status = getDeadlineStatus(value);
  if (!status) return null;
  return status.days;
}

/** "còn 5 ngày" | "đã hết hạn" — null when no date. */
export function countdownLabel(value?: string | null): string | null {
  const status = getDeadlineStatus(value);
  if (!status) return null;
  return status.label;
}

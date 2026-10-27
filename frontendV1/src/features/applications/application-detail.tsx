import { useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  BookOpen,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  Copy,
  Download,
  Eye,
  FileCheck2,
  FileText,
  GraduationCap,
  History,
  Home,
  Mail,
  MapPin,
  Pencil,
  Phone,
  ShieldCheck,
  Sparkles,
  Trash2,
  User,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  attachmentDownloadUrl,
  useApplicationHistoryQuery,
  useApplicationQuery,
  useApproveApplication,
  useDeleteApplication,
  useRejectApplication,
  useRequestApplicationSupplement,
  useReviewPriorityVerification,
} from "@/features/applications/api";
import { EditApplicationDialog } from "@/features/applications/edit-application-dialog";
import {
  type ApplicationAttachment,
  type ApplicationDetail as ApplicationDetailType,
  type ApplicationStatus,
  applicationStatusVariants,
  applicationStatusLabels as labels,
  type PriorityEvidenceReviewStatus,
  type PriorityResidenceReviewStatus,
  priorityEvidenceReviewStatusLabels,
  priorityResidenceReviewStatusLabels,
  type ReviewPriorityVerificationInput,
} from "@/features/applications/types";
import { formatDateTime, formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export function ApplicationDetail({
  applicationId,
}: {
  applicationId: string;
}) {
  const { can } = useRbac();
  const navigate = useNavigate();
  const query = useApplicationQuery(applicationId);
  const history = useApplicationHistoryQuery(applicationId);

  const [review, setReview] = useState<
    "approve" | "reject" | "request-supplement" | null
  >(null);
  const [priorityReviewOpen, setPriorityReviewOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [previewAttachment, setPreviewAttachment] =
    useState<ApplicationAttachment | null>(null);

  const deleteApplication = useDeleteApplication();

  if (query.isLoading) {
    return <ApplicationDetailSkeleton />;
  }

  if (query.isError || !query.data) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center bg-card">
        <div className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-4">
          <AlertCircle className="size-7" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">
          Không thể tải thông tin hồ sơ
        </h3>
        <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
          Đã xảy ra lỗi khi tải hồ sơ đăng ký hoặc hồ sơ không tồn tại.
        </p>
        <div className="mt-6 flex items-center gap-3">
          <Button variant="outline" onClick={() => window.history.back()}>
            <ArrowLeft className="mr-2 size-4" /> Quay lại
          </Button>
          <Button onClick={() => void query.refetch()}>Thử lại</Button>
        </div>
      </div>
    );
  }

  const item = query.data;
  const isPendingReview =
    item.status === "submitted" || item.status === "need_supplement";
  const canReview = can("ktx.applications.review");
  const canReject =
    canReview && (isPendingReview || item.status === "approved");
  const canDelete =
    (can("ktx.applications.delete") || canReview) && item.status !== "assigned";
  const hasEditPermission =
    can("ktx.applications.update") ||
    can("ktx.applications.create") ||
    can("ktx.applications.review");
  const canEdit =
    hasEditPermission &&
    (item.status === "draft" ||
      item.status === "submitted" ||
      item.status === "need_supplement" ||
      item.status === "approved");
  const evidenceAttachments = item.attachments.filter(
    (attachment) => attachment.attachmentType === "priority_evidence",
  );
  const requiresPriorityVerification =
    item.priorityVerificationType === "image_evidence" ||
    item.priorityVerificationType === "residence_area" ||
    item.priorityVerificationType === "image_and_residence_area";
  const reviewPriorityVerificationAllowed = can(
    "ktx.applications.review.priority_verification",
  );

  const initials = (item.studentName ?? "SV")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const handleCopyCode = () => {
    if (!item.applicationCode) return;
    void navigator.clipboard.writeText(item.applicationCode);
    setCopiedCode(true);
    toast.success("Đã sao chép mã hồ sơ.");
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="w-full space-y-5 pb-20 sm:pb-10">
      {/* 1. Header Navigation & Actions Bar (Clean, Flat, Full Width) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1.5">
            <button
              type="button"
              onClick={() => window.history.back()}
              className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
            >
              <ArrowLeft className="size-3.5" />
              <span>Hồ sơ đăng ký</span>
            </button>
            <span>/</span>
            <span className="truncate font-medium text-foreground">
              {item.registrationPeriodName}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
              <FileCheck2 className="size-5" />
            </div>
            <h1 className="font-mono text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {item.applicationCode}
            </h1>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={handleCopyCode}
                    className="inline-flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                    aria-label="Sao chép mã hồ sơ"
                  >
                    {copiedCode ? (
                      <Check className="size-4 text-emerald-600" />
                    ) : (
                      <Copy className="size-4" />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent>Sao chép mã</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <StatusBadgeLarge status={item.status} />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="hidden sm:flex flex-wrap items-center gap-2 shrink-0">
          {canEdit && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 h-9 text-xs font-medium border-primary/30 text-primary hover:bg-primary/5"
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="size-4" />
              <span>Chỉnh sửa hồ sơ</span>
            </Button>
          )}

          {requiresPriorityVerification && reviewPriorityVerificationAllowed ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-primary/30 text-primary hover:bg-primary/5 h-9 text-xs font-medium"
              onClick={() => setPriorityReviewOpen(true)}
            >
              <ShieldCheck className="size-4" />
              <span>Duyệt minh chứng</span>
            </Button>
          ) : null}

          {canReview && isPendingReview ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-amber-500/40 text-amber-600 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-950/40 h-9 text-xs font-medium"
              onClick={() => setReview("request-supplement")}
            >
              <AlertCircle className="size-4" />
              <span>Yêu cầu bổ sung</span>
            </Button>
          ) : null}

          {canReject ? (
            <Button
              size="sm"
              variant="destructive"
              className="gap-1.5 h-9 text-xs font-medium"
              onClick={() => setReview("reject")}
            >
              <XCircle className="size-4" />
              <span>Từ chối</span>
            </Button>
          ) : null}

          {canReview && isPendingReview ? (
            <Button
              size="sm"
              className="gap-1.5 bg-emerald-600 text-white hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 h-9 text-xs font-medium"
              onClick={() => setReview("approve")}
            >
              <CheckCircle2 className="size-4" />
              <span>Phê duyệt</span>
            </Button>
          ) : null}

          {canDelete ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 h-9 text-xs font-medium border-destructive/40 text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="size-4" />
              <span>Xóa hồ sơ</span>
            </Button>
          ) : null}
        </div>
      </div>

      {/* 2. Unified 2-Card Layout (Only 2 Cards across Full Width) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
        {/* CARD 1 (LEFT): All Application & Student Information (Col Span 8) */}
        <div className="lg:col-span-8">
          <Card className="shadow-2xs overflow-hidden">
            {/* Student Profile Header Banner */}
            <div className="flex items-center gap-4 bg-muted/20 border-b p-5">
              <Avatar className="size-13 border-2 border-primary/20 bg-primary/10 text-primary shrink-0">
                <AvatarFallback className="font-semibold text-base">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h2 className="text-lg font-bold text-foreground truncate">
                    {item.studentName}
                  </h2>
                  <span className="font-mono font-medium text-xs bg-muted px-2 py-0.5 rounded text-foreground">
                    MSSV: {item.studentCode}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                  {[item.className, item.faculty].filter(Boolean).join(" · ") ||
                    "Chưa cập nhật lớp/khoa"}
                </p>
              </div>
            </div>

            <CardContent className="p-5 sm:p-6 space-y-5">
              {/* Section 1: Academic & Contact Information */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                  <GraduationCap className="size-3.5 text-primary" />
                  <span>Thông tin sinh viên & Liên hệ</span>
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 text-xs sm:text-sm">
                  <InfoItem
                    icon={
                      <Building2 className="size-4 text-muted-foreground" />
                    }
                    label="Khoa / Đơn vị"
                    value={item.faculty}
                  />
                  <InfoItem
                    icon={<BookOpen className="size-4 text-muted-foreground" />}
                    label="Lớp sinh hoạt"
                    value={item.className}
                  />
                  <InfoItem
                    icon={<Sparkles className="size-4 text-muted-foreground" />}
                    label="Ngành đào tạo"
                    value={item.major}
                  />
                  <InfoItem
                    icon={<User className="size-4 text-muted-foreground" />}
                    label="Dân tộc"
                    value={item.ethnicity || "Kinh"}
                  />
                  <InfoItem
                    icon={<Phone className="size-4 text-muted-foreground" />}
                    label="Số điện thoại"
                    value={
                      item.phoneNumber ? (
                        <a
                          href={`tel:${item.phoneNumber}`}
                          className="text-primary hover:underline font-medium inline-block"
                        >
                          {item.phoneNumber}
                        </a>
                      ) : null
                    }
                  />
                  <InfoItem
                    icon={<Mail className="size-4 text-muted-foreground" />}
                    label="Email trường (QNU)"
                    value={(() => {
                      const emailToDisplay =
                        item.schoolEmail ||
                        (item.studentCode
                          ? `${item.studentCode.toLowerCase()}@st.qnu.edu.vn`
                          : item.email);
                      return emailToDisplay ? (
                        <a
                          href={`mailto:${emailToDisplay}`}
                          className="text-primary hover:underline font-medium break-all"
                          title={emailToDisplay}
                        >
                          {emailToDisplay}
                        </a>
                      ) : null;
                    })()}
                  />
                  <InfoItem
                    icon={<MapPin className="size-4 text-muted-foreground" />}
                    label="Hộ khẩu thường trú"
                    value={item.permanentAddress}
                  />
                </div>
              </div>

              <Separator />

              {/* Section 2: Dormitory Room Preference */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                  <Home className="size-3.5 text-primary" />
                  <span>Nguyện vọng nội trú</span>
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 text-xs sm:text-sm">
                  <InfoItem
                    icon={<Calendar className="size-4 text-muted-foreground" />}
                    label="Đợt đăng ký"
                    value={`${item.registrationPeriodName} (${item.periodCode})`}
                  />
                  <InfoItem
                    icon={<Home className="size-4 text-muted-foreground" />}
                    label="Loại phòng mong muốn"
                    value={
                      item.requestedRoomTypeName ? (
                        <Badge
                          variant="secondary"
                          className="font-medium text-xs px-2.5 py-0.5"
                        >
                          {item.requestedRoomTypeName}
                        </Badge>
                      ) : (
                        "Không chọn cụ thể"
                      )
                    }
                  />
                </div>

                {item.reason ? (
                  <div className="mt-3">
                    <p className="text-xs text-muted-foreground font-medium mb-1">
                      Lý do / Hoàn cảnh đăng ký:
                    </p>
                    <div className="rounded-lg bg-muted/30 border p-3.5 text-xs sm:text-sm leading-relaxed italic text-foreground">
                      "{item.reason}"
                    </div>
                  </div>
                ) : null}
              </div>

              <Separator />

              {/* Section 3: Priority Objects & Verification */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Award className="size-3.5 text-primary" />
                    <span>Chính sách ưu tiên</span>
                  </h3>
                  {item.priorityScore > 0 ? (
                    <Badge className="bg-emerald-600 hover:bg-emerald-600 text-white font-medium text-xs px-2.5 py-0.5">
                      +{item.priorityScore} điểm ưu tiên
                    </Badge>
                  ) : null}
                </div>

                {item.priorityObjectId ? (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/20 border p-3.5 text-xs sm:text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">
                          Diện đối tượng
                        </p>
                        <p className="font-semibold text-foreground mt-0.5">
                          {item.priorityObjectName}
                        </p>
                      </div>
                      {item.priorityObjectCode ? (
                        <Badge variant="outline" className="font-mono text-xs">
                          {item.priorityObjectCode}
                        </Badge>
                      ) : null}
                    </div>

                    {requiresPriorityVerification ? (
                      <div className="grid gap-3 sm:grid-cols-2 text-xs">
                        {/* Area verification */}
                        {item.priorityVerificationType === "residence_area" ||
                        item.priorityVerificationType ===
                          "image_and_residence_area" ? (
                          <div className="rounded-lg border p-3.5 space-y-1.5 bg-card">
                            <div className="flex items-center justify-between gap-1">
                              <span className="flex items-center gap-1 font-medium text-muted-foreground">
                                <MapPin className="size-3.5" />
                                Địa bàn thường trú
                              </span>
                              <PriorityReviewBadge
                                status={item.priorityResidenceReviewStatus}
                              />
                            </div>
                            <p className="font-medium text-foreground text-xs sm:text-sm">
                              {item.priorityResidenceAreaNameSnapshot ??
                                "Chưa chọn địa bàn"}
                            </p>
                            {item.priorityResidenceProvinceSnapshot ? (
                              <p className="text-muted-foreground text-[11px]">
                                Tỉnh/TP:{" "}
                                {item.priorityResidenceProvinceSnapshot}
                              </p>
                            ) : null}
                            {item.priorityResidenceVillageSnapshot ? (
                              <p className="text-foreground font-medium text-[11px] bg-muted/50 px-2 py-1 rounded">
                                Thôn/Xóm/Ấp:{" "}
                                {item.priorityResidenceVillageSnapshot}
                              </p>
                            ) : null}
                            {item.priorityResidenceReviewNote ? (
                              <p className="text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 p-2 rounded border border-amber-200 dark:border-amber-900 text-xs mt-1">
                                Nhận xét: {item.priorityResidenceReviewNote}
                              </p>
                            ) : null}
                          </div>
                        ) : null}

                        {/* Evidence image verification */}
                        {item.priorityVerificationType === "image_evidence" ||
                        item.priorityVerificationType ===
                          "image_and_residence_area" ? (
                          <div className="rounded-lg border p-3.5 space-y-1.5 bg-card">
                            <div className="flex items-center justify-between gap-1">
                              <span className="flex items-center gap-1 font-medium text-muted-foreground">
                                <ShieldCheck className="size-3.5" />
                                Ảnh minh chứng ({evidenceAttachments.length}{" "}
                                tệp)
                              </span>
                              <PriorityReviewBadge
                                status={item.priorityEvidenceReviewStatus}
                              />
                            </div>
                            <p className="text-muted-foreground text-xs">
                              Xem và duyệt tại danh sách tệp đính kèm.
                            </p>
                            {item.priorityEvidenceReviewNote ? (
                              <p className="text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 p-2 rounded border border-amber-200 dark:border-amber-900 text-xs mt-1">
                                Nhận xét: {item.priorityEvidenceReviewNote}
                              </p>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="flex items-center gap-3 rounded-lg border border-dashed p-3.5 text-xs sm:text-sm text-muted-foreground">
                    <User className="size-4.5 text-muted-foreground/60 shrink-0" />
                    <span>
                      Sinh viên đăng ký theo diện thông thường (không áp dụng
                      đối tượng ưu tiên).
                    </span>
                  </div>
                )}
              </div>

              {/* Section 4: Staff Review Conclusion (If available) */}
              {item.reviewedAt || item.reviewNote ? (
                <>
                  <Separator />
                  <div
                    className={cn(
                      "rounded-lg border p-4 text-xs sm:text-sm space-y-2",
                      item.status === "approved"
                        ? "border-emerald-500/30 bg-emerald-50/25 dark:bg-emerald-950/15"
                        : item.status === "rejected"
                          ? "border-destructive/30 bg-destructive/5"
                          : "border-amber-500/30 bg-amber-50/25 dark:bg-amber-950/15",
                    )}
                  >
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-2">
                        {item.status === "approved" ? (
                          <CheckCircle2 className="size-4.5 text-emerald-600" />
                        ) : item.status === "rejected" ? (
                          <XCircle className="size-4.5 text-destructive" />
                        ) : (
                          <AlertCircle className="size-4.5 text-amber-600" />
                        )}
                        <span>Ý kiến xét duyệt của cán bộ</span>
                      </span>
                      {item.reviewedAt ? (
                        <span className="text-xs font-normal text-muted-foreground">
                          {formatDateTimeValue(item.reviewedAt)}
                        </span>
                      ) : null}
                    </div>
                    {item.reviewNote ? (
                      <p className="text-foreground leading-relaxed pt-1 bg-background/80 p-3 rounded border">
                        {item.reviewNote}
                      </p>
                    ) : (
                      <p className="text-muted-foreground italic">
                        Không có nhận xét chi tiết.
                      </p>
                    )}
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        </div>

        {/* CARD 2 (RIGHT): Attachments + Timeline + System Info (Col Span 4) */}
        <div className="lg:col-span-4">
          <Card className="shadow-2xs overflow-hidden">
            {/* Section A: Attachments */}
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <FileText className="size-3.5 text-primary" />
                  <span>Tệp đính kèm ({item.attachments?.length ?? 0})</span>
                </h3>
                {requiresPriorityVerification &&
                reviewPriorityVerificationAllowed ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-xs text-primary px-1.5 -mr-1.5"
                    onClick={() => setPriorityReviewOpen(true)}
                  >
                    Duyệt minh chứng
                  </Button>
                ) : null}
              </div>

              {item.attachments?.length ? (
                <div className="space-y-2">
                  {item.attachments.map((attachment) => {
                    const isImage =
                      attachment.contentType?.startsWith("image/") ||
                      /\.(jpg|jpeg|png|webp|gif)$/i.test(attachment.fileName);

                    return (
                      <div
                        key={attachment.id}
                        className="group flex items-center justify-between gap-2.5 rounded-lg border bg-card p-2.5 hover:border-primary/40 hover:bg-muted/30 transition-all text-xs"
                      >
                        <div className="flex items-center gap-2.5 min-w-0 flex-1">
                          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                            <FileText className="size-4" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p
                              className="truncate font-medium text-foreground"
                              title={attachment.fileName}
                            >
                              {attachment.fileName}
                            </p>
                            <p className="text-[11px] text-muted-foreground truncate">
                              {attachment.sizeBytes
                                ? `${(attachment.sizeBytes / 1024).toFixed(1)} KB · `
                                : ""}
                              {formatDateTime(new Date(attachment.uploadedAt))}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          {isImage ? (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-7.5 text-muted-foreground hover:text-foreground"
                              onClick={() => setPreviewAttachment(attachment)}
                              title="Xem ảnh"
                            >
                              <Eye className="size-4" />
                            </Button>
                          ) : null}
                          <Button
                            variant="ghost"
                            size="icon"
                            asChild
                            className="size-7.5 text-muted-foreground hover:text-foreground"
                            title="Tải về"
                          >
                            <a
                              href={attachmentDownloadUrl(
                                applicationId,
                                attachment.id,
                              )}
                              target="_blank"
                              rel="noreferrer"
                              download={attachment.fileName}
                            >
                              <Download className="size-4" />
                            </a>
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-5 text-center text-muted-foreground bg-muted/20 rounded-lg border border-dashed">
                  <FileText className="size-6 text-muted-foreground/40 mb-1" />
                  <p className="text-xs font-medium">Không có tệp đính kèm</p>
                </div>
              )}
            </div>

            <Separator />

            {/* Section B: Lifecycle Timeline */}
            <div className="p-5 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <History className="size-3.5 text-primary" />
                <span>Tiến trình hồ sơ</span>
              </h3>

              {history.isLoading ? (
                <div className="space-y-2.5">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : history.data?.length ? (
                <div className="relative pl-4 space-y-4 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border text-xs">
                  {history.data.map((entry, index) => {
                    const isLatest = index === 0;
                    return (
                      <div key={entry.id} className="relative">
                        <span
                          className={cn(
                            "absolute -left-4 top-1 size-2.5 rounded-full border-2 border-background",
                            isLatest
                              ? "bg-primary ring-2 ring-primary/20"
                              : "bg-muted-foreground/40",
                          )}
                        />
                        <div>
                          <p className="font-medium text-foreground">
                            {entry.fromStatus
                              ? `${labels[entry.fromStatus]} → `
                              : ""}
                            {labels[entry.toStatus]}
                          </p>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {formatDateTime(new Date(entry.changedAt))}
                            {entry.changedBy ? ` · ${entry.changedBy}` : ""}
                          </p>
                          {entry.note ? (
                            <p className="mt-1.5 rounded bg-muted/50 p-2 text-xs text-foreground/90 border leading-relaxed">
                              {entry.note}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-3 italic">
                  Chưa ghi nhận lịch sử thay đổi.
                </p>
              )}
            </div>

            <Separator />

            {/* Section C: Compact System Timestamps (No empty space) */}
            <div className="bg-muted/15 p-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-0.5">
                  <p className="text-[11px] font-medium text-muted-foreground">
                    Ngày nộp hồ sơ
                  </p>
                  <p className="text-xs font-semibold text-foreground">
                    {item.submittedAt
                      ? formatDateTimeValue(item.submittedAt)
                      : "—"}
                  </p>
                </div>
                <div className="space-y-0.5">
                  <p className="text-[11px] font-medium text-muted-foreground">
                    Cập nhật lần cuối
                  </p>
                  <p className="text-xs font-semibold text-foreground">
                    {item.lastModified
                      ? formatDateTimeValue(item.lastModified)
                      : "—"}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Mobile Floating Bottom Action Bar */}
      {canReject || canDelete ? (
        <div className="fixed bottom-0 left-0 right-0 z-30 border-t bg-background/95 p-3 backdrop-blur-md shadow-lg sm:hidden flex items-center gap-2">
          {canReject ? (
            <Button
              size="sm"
              variant="destructive"
              className="flex-1 h-10 text-xs font-semibold gap-1"
              onClick={() => setReview("reject")}
            >
              <XCircle className="size-4" />
              <span>Từ chối</span>
            </Button>
          ) : null}
          {canReview && isPendingReview ? (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-10 text-xs font-semibold gap-1 border-amber-500/40 text-amber-600"
              onClick={() => setReview("request-supplement")}
            >
              <AlertCircle className="size-4" />
              <span>Bổ sung</span>
            </Button>
          ) : null}
          {canReview && isPendingReview ? (
            <Button
              size="sm"
              className="flex-1 h-10 text-xs font-semibold gap-1 bg-emerald-600 text-white hover:bg-emerald-700"
              onClick={() => setReview("approve")}
            >
              <CheckCircle2 className="size-4" />
              <span>Phê duyệt</span>
            </Button>
          ) : null}
          {canDelete ? (
            <Button
              size="sm"
              variant="outline"
              className="h-10 text-xs font-semibold gap-1 border-destructive/40 text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="size-4" />
              <span>Xóa</span>
            </Button>
          ) : null}
        </div>
      ) : null}

      {/* Review Dialog */}
      <ReviewDialog
        action={review}
        applicationId={applicationId}
        onClose={() => setReview(null)}
      />

      {/* Delete Application Dialog */}
      <ResponsiveDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <ResponsiveDialogContent className="max-w-md">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="size-5" />
              <span>Xác nhận xóa hồ sơ đăng ký</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              Bạn có chắc chắn muốn xóa vĩnh viễn hồ sơ đăng ký{" "}
              <strong className="font-mono text-foreground">
                {item.applicationCode}
              </strong>{" "}
              của sinh viên <strong>{item.studentName}</strong> không?
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="my-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-destructive">Cảnh báo:</p>
            <p>
              Thao tác này sẽ xóa sạch hồ sơ đăng ký, các file minh chứng và
              lịch sử trạng thái kèm theo. Dữ liệu sau khi xóa sẽ không thể phục
              hồi.
            </p>
          </div>
          <ResponsiveDialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={deleteApplication.isPending}
            >
              Hủy bỏ
            </Button>
            <Button
              variant="destructive"
              disabled={deleteApplication.isPending}
              onClick={() => {
                deleteApplication.mutate(item.id, {
                  onSuccess: () => {
                    toast.success("Đã xóa hồ sơ đăng ký thành công.");
                    setDeleteOpen(false);
                    void navigate({
                      to: "/applications",
                      search: { page: 1, pageSize: 10, q: "" },
                    });
                  },
                  onError: (err) => {
                    toast.error(
                      err instanceof Error
                        ? err.message
                        : "Xóa hồ sơ thất bại.",
                    );
                  },
                });
              }}
            >
              {deleteApplication.isPending ? "Đang xóa..." : "Xác nhận xóa"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Edit Application Dialog */}
      <EditApplicationDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        application={item}
      />

      {/* Priority Verification Dialog */}
      {requiresPriorityVerification && reviewPriorityVerificationAllowed ? (
        <PriorityVerificationDialog
          applicationId={applicationId}
          open={priorityReviewOpen}
          item={item}
          onClose={() => setPriorityReviewOpen(false)}
        />
      ) : null}

      {/* Image Preview Modal */}
      {previewAttachment ? (
        <Dialog
          open={Boolean(previewAttachment)}
          onOpenChange={(open) => {
            if (!open) setPreviewAttachment(null);
          }}
        >
          <DialogContent className="max-w-3xl overflow-hidden p-0 max-h-[90dvh] flex flex-col">
            <DialogHeader className="border-b p-4 shrink-0">
              <DialogTitle className="text-sm font-medium truncate">
                {previewAttachment.fileName}
              </DialogTitle>
            </DialogHeader>
            <div className="flex-1 flex items-center justify-center bg-black/5 p-4 overflow-auto min-h-0">
              <img
                src={attachmentDownloadUrl(applicationId, previewAttachment.id)}
                alt={previewAttachment.fileName}
                className="max-h-[65vh] w-auto max-w-full rounded-md object-contain shadow-md"
              />
            </div>
            <div className="flex justify-end gap-2 border-t p-3 bg-muted/20 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPreviewAttachment(null)}
              >
                Đóng
              </Button>
              <Button size="sm" asChild>
                <a
                  href={attachmentDownloadUrl(
                    applicationId,
                    previewAttachment.id,
                  )}
                  download={previewAttachment.fileName}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Download className="mr-1.5 size-4" /> Tải về
                </a>
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}

// Clean Information Item with Icon
function InfoItem({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5">
      {icon ? <div className="mt-0.5 shrink-0">{icon}</div> : null}
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground font-medium">{label}</p>
        <div className="text-xs sm:text-sm font-medium text-foreground mt-0.5 break-words">
          {value || (
            <span className="text-muted-foreground/60 font-normal">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

// Status Badge Large
function StatusBadgeLarge({ status }: { status: ApplicationStatus }) {
  const variant = applicationStatusVariants[status] || "secondary";
  const label = labels[status] || status;

  return (
    <Badge
      variant={variant}
      className={cn(
        "gap-1.5 px-3 py-1 text-xs font-semibold uppercase tracking-wide shrink-0",
        status === "approved" &&
          "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
        status === "submitted" &&
          "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
        status === "need_supplement" &&
          "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
        status === "rejected" &&
          "bg-destructive/15 text-destructive border-destructive/30",
      )}
    >
      <span
        className={cn(
          "size-2 rounded-full",
          status === "approved" && "bg-emerald-500",
          status === "submitted" && "bg-blue-500 animate-pulse",
          status === "need_supplement" && "bg-amber-500",
          status === "rejected" && "bg-destructive",
          status === "draft" && "bg-muted-foreground/60",
          status === "cancelled" && "bg-muted-foreground/60",
        )}
      />
      {label}
    </Badge>
  );
}

// Priority Review Badge
function PriorityReviewBadge({
  status,
}: {
  status: PriorityEvidenceReviewStatus | PriorityResidenceReviewStatus;
}) {
  const tone =
    status === "approved" || status === "valid"
      ? "success"
      : status === "need_supplement" || status === "need_correction"
        ? "warning"
        : status === "rejected" || status === "invalid"
          ? "destructive"
          : "secondary";

  const label =
    status in priorityEvidenceReviewStatusLabels
      ? priorityEvidenceReviewStatusLabels[
          status as PriorityEvidenceReviewStatus
        ]
      : priorityResidenceReviewStatusLabels[
          status as PriorityResidenceReviewStatus
        ];

  return (
    <Badge
      variant={tone}
      className="font-medium text-[11px] px-2 py-0.5 shrink-0"
    >
      {label}
    </Badge>
  );
}

// Review Dialog Component
function ReviewDialog({
  action,
  applicationId,
  onClose,
}: {
  action: "approve" | "reject" | "request-supplement" | null;
  applicationId: string;
  onClose: () => void;
}) {
  const approve = useApproveApplication();
  const reject = useRejectApplication();
  const supplement = useRequestApplicationSupplement();
  const [note, setNote] = useState("");

  if (!action) return null;

  const mutation =
    action === "approve" ? approve : action === "reject" ? reject : supplement;
  const title =
    action === "approve"
      ? "Phê duyệt hồ sơ"
      : action === "reject"
        ? "Từ chối hồ sơ đăng ký"
        : "Yêu cầu sinh viên bổ sung hồ sơ";

  const description =
    action === "approve"
      ? "Hồ sơ hợp lệ sẽ được chuyển sang trạng thái Đã duyệt và sẵn sàng cho bước xếp phòng."
      : action === "reject"
        ? "Sinh viên sẽ nhận được thông báo hồ sơ bị từ chối kèm lý do cụ thể."
        : "Hồ sơ sẽ được chuyển về trạng thái Cần bổ sung để sinh viên có thể chỉnh sửa và nộp lại.";

  const required = action !== "approve";

  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open && !mutation.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="max-w-lg">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle className="flex items-center gap-2 text-base sm:text-lg">
            {action === "approve" ? (
              <CheckCircle2 className="size-5 text-emerald-600" />
            ) : action === "reject" ? (
              <XCircle className="size-5 text-destructive" />
            ) : (
              <AlertCircle className="size-5 text-amber-600" />
            )}
            <span>{title}</span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs sm:text-sm">
            {description}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="my-3 space-y-2">
          <Label htmlFor="review-note" className="text-xs font-medium">
            {required ? (
              <span>
                Nhận xét / Lý do <span className="text-destructive">*</span>
              </span>
            ) : (
              "Nhận xét (không bắt buộc)"
            )}
          </Label>
          <Textarea
            id="review-note"
            className="min-h-24 text-sm"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              required
                ? "Nhập lý do hoặc hướng dẫn sinh viên bổ sung..."
                : "Ghi chú thêm cho hồ sơ này..."
            }
          />
        </div>
        <ResponsiveDialogFooter className="flex-col-reverse sm:flex-row gap-2">
          <Button
            variant="outline"
            disabled={mutation.isPending}
            onClick={onClose}
            className="w-full sm:w-auto"
          >
            Hủy
          </Button>
          <Button
            variant={
              action === "reject"
                ? "destructive"
                : action === "approve"
                  ? "default"
                  : "secondary"
            }
            className={cn(
              "w-full sm:w-auto",
              action === "approve" &&
                "bg-emerald-600 text-white hover:bg-emerald-700",
            )}
            disabled={mutation.isPending || (required && !note.trim())}
            onClick={() =>
              void mutation
                .mutateAsync({
                  id: applicationId,
                  reviewNote: note.trim() || undefined,
                })
                .then(() => {
                  onClose();
                  toast.success("Đã cập nhật trạng thái hồ sơ thành công.");
                })
                .catch((error: unknown) =>
                  toast.error(
                    error instanceof ApiError
                      ? error.message
                      : "Không thể cập nhật hồ sơ.",
                  ),
                )
            }
          >
            {mutation.isPending ? "Đang lưu..." : "Xác nhận"}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

const RESIDENCE_REVIEW_OPTIONS: PriorityResidenceReviewStatus[] = [
  "pending_review",
  "valid",
  "invalid",
  "need_correction",
];

const EVIDENCE_REVIEW_OPTIONS: PriorityEvidenceReviewStatus[] = [
  "pending_review",
  "approved",
  "need_supplement",
  "rejected",
];

// Priority Verification Dialog
function PriorityVerificationDialog({
  applicationId,
  item,
  open,
  onClose,
}: {
  applicationId: string;
  item: ApplicationDetailType;
  open: boolean;
  onClose: () => void;
}) {
  const review = useReviewPriorityVerification();
  const requiresEvidence =
    item.priorityVerificationType === "image_evidence" ||
    item.priorityVerificationType === "image_and_residence_area";
  const requiresArea =
    item.priorityVerificationType === "residence_area" ||
    item.priorityVerificationType === "image_and_residence_area";

  const [residenceStatus, setResidenceStatus] = useState<
    PriorityResidenceReviewStatus | ""
  >(
    item.priorityResidenceReviewStatus === "not_required"
      ? ""
      : item.priorityResidenceReviewStatus,
  );
  const [residenceNote, setResidenceNote] = useState(
    item.priorityResidenceReviewNote ?? "",
  );
  const [evidenceStatus, setEvidenceStatus] = useState<
    PriorityEvidenceReviewStatus | ""
  >(
    item.priorityEvidenceReviewStatus === "not_required"
      ? ""
      : item.priorityEvidenceReviewStatus,
  );
  const [evidenceNote, setEvidenceNote] = useState(
    item.priorityEvidenceReviewNote ?? "",
  );
  const [propagate, setPropagate] = useState(true);

  if (!open) return null;

  const buildPayload = (): ReviewPriorityVerificationInput | null => {
    const payload: ReviewPriorityVerificationInput = {
      propagateToApplicationStatus: propagate,
    };
    let hasAny = false;
    if (requiresArea && residenceStatus) {
      payload.residenceReviewStatus = residenceStatus;
      payload.residenceReviewNote = residenceNote.trim() || undefined;
      hasAny = true;
    }
    if (requiresEvidence && evidenceStatus) {
      payload.evidenceReviewStatus = evidenceStatus;
      payload.evidenceReviewNote = evidenceNote.trim() || undefined;
      hasAny = true;
    }
    return hasAny ? payload : null;
  };

  const isDirty =
    (requiresArea &&
      (residenceStatus !== item.priorityResidenceReviewStatus ||
        (residenceNote ?? "") !== (item.priorityResidenceReviewNote ?? ""))) ||
    (requiresEvidence &&
      (evidenceStatus !== item.priorityEvidenceReviewStatus ||
        (evidenceNote ?? "") !== (item.priorityEvidenceReviewNote ?? "")));

  const payload = buildPayload();
  const canSubmit = Boolean(payload) && isDirty && !review.isPending;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !review.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="max-w-2xl">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle className="flex items-center gap-2 text-base sm:text-lg">
            <ShieldCheck className="size-5 text-primary" />
            <span>Thẩm định diện ưu tiên</span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs sm:text-sm">
            Cập nhật kết quả thẩm định địa bàn thường trú và ảnh minh chứng của
            sinh viên ({item.applicationCode}).
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="space-y-4 py-2">
          {requiresArea ? (
            <div className="rounded-lg border bg-muted/20 p-3 sm:p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <p className="text-xs sm:text-sm font-semibold text-foreground">
                  1. Địa bàn thường trú sinh viên chọn
                </p>
                <Badge variant="outline" className="font-mono text-[11px]">
                  {item.priorityResidenceAreaCodeSnapshot ?? "Mã địa bàn"}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Địa bàn:{" "}
                <span className="font-medium text-foreground">
                  {item.priorityResidenceAreaNameSnapshot ?? "Chưa chọn"}
                </span>{" "}
                · Tỉnh/TP:{" "}
                <span className="font-medium text-foreground">
                  {item.priorityResidenceProvinceSnapshot ?? "—"}
                </span>
                {item.priorityResidenceVillageSnapshot ? (
                  <>
                    {" "}
                    · Thôn/Ấp:{" "}
                    <span className="font-semibold text-primary">
                      {item.priorityResidenceVillageSnapshot}
                    </span>
                  </>
                ) : null}
              </p>
              <div className="grid gap-2.5 pt-1">
                <Label htmlFor="residence-status" className="text-xs">
                  Trạng thái thẩm định địa bàn
                </Label>
                <Select
                  value={residenceStatus}
                  onValueChange={(value) =>
                    setResidenceStatus(value as PriorityResidenceReviewStatus)
                  }
                >
                  <SelectTrigger id="residence-status">
                    <SelectValue placeholder="Chọn trạng thái" />
                  </SelectTrigger>
                  <SelectContent>
                    {RESIDENCE_REVIEW_OPTIONS.map((value) => (
                      <SelectItem key={value} value={value}>
                        {priorityResidenceReviewStatusLabels[value]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Label htmlFor="residence-note" className="text-xs">
                  Ghi chú nhận xét (tùy chọn)
                </Label>
                <Textarea
                  id="residence-note"
                  className="min-h-16 text-sm"
                  value={residenceNote}
                  onChange={(event) => setResidenceNote(event.target.value)}
                  placeholder="Lý do không hợp lệ hoặc hướng dẫn sinh viên..."
                />
              </div>
            </div>
          ) : null}

          {requiresEvidence ? (
            <div className="rounded-lg border bg-muted/20 p-3 sm:p-4 space-y-2.5">
              <p className="text-xs sm:text-sm font-semibold text-foreground">
                2. Ảnh minh chứng đính kèm
              </p>
              <p className="text-xs text-muted-foreground">
                Sinh viên đã nộp{" "}
                <span className="font-semibold text-foreground">
                  {
                    item.attachments.filter(
                      (a) => a.attachmentType === "priority_evidence",
                    ).length
                  }
                </span>{" "}
                tệp minh chứng.
              </p>
              <div className="grid gap-2.5 pt-1">
                <Label htmlFor="evidence-status" className="text-xs">
                  Trạng thái thẩm định ảnh minh chứng
                </Label>
                <Select
                  value={evidenceStatus}
                  onValueChange={(value) =>
                    setEvidenceStatus(value as PriorityEvidenceReviewStatus)
                  }
                >
                  <SelectTrigger id="evidence-status">
                    <SelectValue placeholder="Chọn trạng thái" />
                  </SelectTrigger>
                  <SelectContent>
                    {EVIDENCE_REVIEW_OPTIONS.map((value) => (
                      <SelectItem key={value} value={value}>
                        {priorityEvidenceReviewStatusLabels[value]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Label htmlFor="evidence-note" className="text-xs">
                  Ghi chú nhận xét (tùy chọn)
                </Label>
                <Textarea
                  id="evidence-note"
                  className="min-h-16 text-sm"
                  value={evidenceNote}
                  onChange={(event) => setEvidenceNote(event.target.value)}
                  placeholder="Lý do yêu cầu bổ sung hoặc từ chối..."
                />
              </div>
            </div>
          ) : null}

          <div className="flex items-start gap-3 rounded-lg border bg-background p-3">
            <Checkbox
              id="propagate-status"
              checked={propagate}
              onCheckedChange={(checked) => setPropagate(Boolean(checked))}
              className="mt-0.5"
            />
            <label
              htmlFor="propagate-status"
              className="text-xs leading-relaxed text-muted-foreground cursor-pointer select-none"
            >
              Tự động chuyển hồ sơ về trạng thái{" "}
              <strong className="text-foreground">"Cần bổ sung"</strong> nếu có
              hạng mục bị đánh giá Cần chỉnh sửa / Từ chối.
            </label>
          </div>
        </div>
        <ResponsiveDialogFooter className="flex-col-reverse sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={review.isPending}
            className="w-full sm:w-auto"
          >
            Hủy
          </Button>
          <Button
            onClick={() => {
              if (!payload) {
                toast.error(
                  "Vui lòng chọn trạng thái duyệt cho ít nhất một mục.",
                );
                return;
              }
              if (!isDirty) {
                toast.info("Không có thay đổi để lưu.");
                return;
              }
              void review
                .mutateAsync({ id: applicationId, input: payload })
                .then(() => {
                  toast.success("Đã cập nhật duyệt minh chứng thành công.");
                  onClose();
                })
                .catch((error: unknown) =>
                  toast.error(
                    error instanceof ApiError
                      ? error.message
                      : "Không thể cập nhật minh chứng.",
                  ),
                );
            }}
            disabled={!canSubmit}
            className="w-full sm:w-auto"
          >
            {review.isPending ? "Đang lưu..." : "Lưu thẩm định"}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

// Skeleton Loader
function ApplicationDetailSkeleton() {
  return (
    <div className="space-y-6 w-full">
      <div className="flex justify-between items-center border-b pb-4">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-9 w-48" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <Skeleton className="h-[520px] w-full rounded-xl" />
        </div>
        <div className="lg:col-span-4">
          <Skeleton className="h-[420px] w-full rounded-xl" />
        </div>
      </div>
    </div>
  );
}

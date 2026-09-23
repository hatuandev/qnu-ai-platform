import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  Info,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMyApplicationsQuery,
  useOpenRegistrationPeriodsQuery,
  useSaveStudentApplicationDraft,
  useStudentRegistrationCatalogQuery,
  useSubmitStudentApplication,
  useSubmitStudentApplicationWithEvidence,
} from "@/features/student/api";
import {
  type PriorityEvidenceFile,
  StudentPriorityEvidenceCard,
} from "@/features/student/student-priority-evidence-card";
import { formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

export function StudentRegistrationPage() {
  const navigate = useNavigate();
  const [periodId, setPeriodId] = useState("");
  const [priorityObjectId, setPriorityObjectId] = useState<string>("none");
  const [agreedTerms, setAgreedTerms] = useState(false);
  const [evidenceFiles, setEvidenceFiles] = useState<PriorityEvidenceFile[]>(
    [],
  );
  const evidenceFilesRef = useRef(evidenceFiles);
  evidenceFilesRef.current = evidenceFiles;
  const [residenceAreaId, setResidenceAreaId] = useState<string | null>(null);
  const [residenceVillage, setResidenceVillage] = useState<string | null>(null);

  // Editable student profile form state (except studentCode and fullName)
  const [classAndFaculty, setClassAndFaculty] = useState("");
  const [major, setMajor] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [schoolEmail, setSchoolEmail] = useState("");
  const [ethnicity, setEthnicity] = useState("kinh");
  const [permanentAddress, setPermanentAddress] = useState("");
  const [isProfileInitialized, setIsProfileInitialized] = useState(false);

  const periodsQuery = useOpenRegistrationPeriodsQuery();
  const catalogQuery = useStudentRegistrationCatalogQuery(
    periodId || undefined,
  );
  const applicationsQuery = useMyApplicationsQuery();
  const submitMutation = useSubmitStudentApplication();
  const submitEvidenceMutation = useSubmitStudentApplicationWithEvidence();
  const draftMutation = useSaveStudentApplicationDraft();

  const periods = periodsQuery.data ?? [];
  const selectedPeriod =
    periods.find((period) => period.id === periodId) ?? periods[0];
  const existingApplication = applicationsQuery.data?.find(
    (application) => application.registrationPeriodId === selectedPeriod?.id,
  );

  const isEditableApplication =
    existingApplication?.status === "draft" ||
    existingApplication?.status === "need_supplement" ||
    existingApplication?.status === "cancelled";

  const draftApplication = isEditableApplication
    ? existingApplication
    : undefined;
  const requiresSupplement = existingApplication?.status === "need_supplement";
  const wasWithdrawn = existingApplication?.status === "cancelled";
  const finalApplication =
    existingApplication && !isEditableApplication
      ? existingApplication
      : undefined;

  const priorityObjects = (catalogQuery.data?.priorityObjects ?? []).filter(
    (priority) => priority.code !== "NONE",
  );
  const selectedPriorityObject =
    priorityObjects.find((priority) => priority.id === priorityObjectId) ??
    null;
  const requiresEvidence =
    selectedPriorityObject?.verificationType === "image_evidence" ||
    selectedPriorityObject?.verificationType === "image_and_residence_area";
  const requiresResidence =
    selectedPriorityObject?.verificationType === "residence_area" ||
    selectedPriorityObject?.verificationType === "image_and_residence_area";
  const evidenceReady = !requiresEvidence || evidenceFiles.length > 0;
  const residenceReady = !requiresResidence || Boolean(residenceAreaId);
  const studentProfile = catalogQuery.data?.student;

  const isLoading = periodsQuery.isLoading || catalogQuery.isLoading;
  const hasError = periodsQuery.isError || catalogQuery.isError;
  const isCheckingApplication = applicationsQuery.isPending;
  const profileNotLinked =
    applicationsQuery.error instanceof ApiError &&
    applicationsQuery.error.status === 403;
  const applicationCheckFailed = applicationsQuery.isError && !profileNotLinked;

  useEffect(() => {
    if (!periodId && periods[0]) setPeriodId(periods[0].id);
  }, [periodId, periods]);

  useEffect(() => {
    if (draftApplication?.priorityObjectId) {
      setPriorityObjectId(draftApplication.priorityObjectId);
    } else {
      setPriorityObjectId("none");
    }
  }, [draftApplication?.priorityObjectId]);

  useEffect(() => {
    if (priorityObjectId === "none") return;
    // Revoke previews from the previous selection before resetting state.
    for (const item of evidenceFilesRef.current) {
      URL.revokeObjectURL(item.previewUrl);
    }
    setEvidenceFiles([]);
    setResidenceAreaId(null);
    setResidenceVillage(null);
  }, [priorityObjectId]);

  // Final teardown: revoke any leftover preview URLs when the page unmounts.
  useEffect(() => {
    return () => {
      for (const item of evidenceFilesRef.current) {
        URL.revokeObjectURL(item.previewUrl);
      }
    };
  }, []);

  useEffect(() => {
    if (studentProfile && !isProfileInitialized) {
      setClassAndFaculty(
        [studentProfile.className, studentProfile.faculty]
          .filter(Boolean)
          .join(" / "),
      );
      setMajor(studentProfile.major ?? "");
      setEmail(studentProfile.email ?? "");
      setPhoneNumber(studentProfile.phoneNumber ?? "");
      setSchoolEmail(studentProfile.schoolEmail ?? "");
      setPermanentAddress(studentProfile.permanentAddress ?? "");
      setIsProfileInitialized(true);
    }
  }, [studentProfile, isProfileInitialized]);

  const formReady = useMemo(
    () =>
      Boolean(
        selectedPeriod &&
          !finalApplication &&
          Boolean(studentProfile) &&
          !isCheckingApplication &&
          !applicationsQuery.isError &&
          !submitMutation.isPending &&
          !draftMutation.isPending &&
          agreedTerms &&
          evidenceReady &&
          residenceReady,
      ),
    [
      agreedTerms,
      applicationsQuery.isError,
      finalApplication,
      studentProfile,
      draftMutation.isPending,
      isCheckingApplication,
      selectedPeriod,
      submitMutation.isPending,
      evidenceReady,
      residenceReady,
    ],
  );

  const draftReady = Boolean(
    selectedPeriod &&
      !finalApplication &&
      Boolean(studentProfile) &&
      !isCheckingApplication &&
      !applicationsQuery.isError &&
      !submitMutation.isPending &&
      !draftMutation.isPending,
  );

  const buildInput = () => ({
    registrationPeriodId: selectedPeriod?.id ?? "",
    priorityObjectId:
      priorityObjectId && priorityObjectId !== "none"
        ? priorityObjectId
        : undefined,
    applicantClassAndFaculty: classAndFaculty.trim() || undefined,
    applicantMajor: major.trim() || undefined,
    applicantEmail: email.trim() || undefined,
    applicantPhoneNumber: phoneNumber.trim() || undefined,
    applicantSchoolEmail: schoolEmail.trim() || undefined,
    applicantPermanentAddress: permanentAddress.trim() || undefined,
    applicantEthnicity: ethnicity.trim() || undefined,
  });
  const needsEvidenceSubmission = requiresEvidence || requiresResidence;

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPeriod || !formReady) return;
    const promise = needsEvidenceSubmission
      ? submitEvidenceMutation.mutateAsync({
          ...buildInput(),
          priorityResidenceAreaId: residenceAreaId,
          priorityResidenceVillage: residenceVillage,
          evidenceFiles: evidenceFiles.map((item) => item.file),
        })
      : submitMutation.mutateAsync(buildInput());
    void promise
      .then(() => {
        toast.success("Nộp hồ sơ đăng ký thành công!");
        void navigate({ to: "/dashboard" });
      })
      .catch(() => undefined);
  }

  function saveDraft() {
    if (!draftReady) return;
    void draftMutation
      .mutateAsync(buildInput())
      .then(() => toast.success("Đã lưu bản nháp hồ sơ."))
      .catch(() => undefined);
  }

  if (isLoading) {
    return <RegistrationPageSkeleton />;
  }

  if (hasError) {
    return (
      <Alert variant="destructive">
        <Info className="size-4" />
        <div>
          <AlertTitle>Không thể tải biểu mẫu đăng ký</AlertTitle>
          <AlertDescription>
            Đã có lỗi xảy ra khi kết nối máy chủ. Vui lòng quay lại tổng quan và
            thử lại.
          </AlertDescription>
        </div>
      </Alert>
    );
  }

  if (!selectedPeriod) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <FileText className="size-6" />
          </div>
          <div className="space-y-1">
            <p className="text-base font-semibold">Chưa có đợt đăng ký mở</p>
            <p className="text-sm text-muted-foreground">
              Hiện tại nhà trường chưa mở đợt đăng ký mới nào cho ký túc xá.
            </p>
          </div>
          <Button asChild variant="outline" className="mt-2">
            <Link to="/dashboard">
              <ArrowLeft className="size-4" /> Quay lại tổng quan
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (finalApplication) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <Button asChild variant="ghost" className="-ml-3">
          <Link to="/dashboard">
            <ArrowLeft className="size-4" /> Quay lại tổng quan
          </Link>
        </Button>
        <Card className="border-primary/20 bg-linear-to-b from-primary/5 via-card to-card shadow-sm">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <span className="flex size-14 items-center justify-center rounded-full bg-success/15 text-success">
              <CheckCircle2 className="size-7" />
            </span>
            <div className="space-y-1.5">
              <Badge variant="success">Hồ sơ đã tiếp nhận</Badge>
              <h1 className="text-2xl font-bold tracking-tight">
                Bạn đã có hồ sơ trong đợt này
              </h1>
              <p className="text-sm text-muted-foreground">
                Mã hồ sơ:{" "}
                <span className="font-mono font-semibold text-foreground">
                  {finalApplication.applicationCode}
                </span>
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <Button asChild>
                <Link to="/dashboard">
                  Theo dõi trạng thái <ArrowRight className="size-4" />
                </Link>
              </Button>
              {finalApplication.status === "approved" ? (
                <Button asChild variant="outline">
                  <Link
                    to="/student/room-selection"
                    search={{
                      registrationPeriodId:
                        finalApplication.registrationPeriodId,
                    }}
                  >
                    Chọn phòng <ArrowRight className="size-4" />
                  </Link>
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-3.5 pb-16 sm:space-y-6 sm:px-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:gap-4">
        <Button asChild variant="ghost" size="sm" className="-ml-2 w-fit">
          <Link to="/dashboard">
            <ArrowLeft className="size-4" /> Quay lại tổng quan
          </Link>
        </Button>
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-primary">
            <Sparkles className="size-3.5" /> Hồ sơ trực tuyến
          </div>
          <h1 className="mt-1.5 text-xl font-bold tracking-tight sm:text-2xl md:text-3xl">
            Đăng ký ở ký túc xá
          </h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            Kiểm tra thông tin và hoàn tất phiếu đăng ký. Bạn chỉ có thể nộp một
            hồ sơ trong mỗi đợt đăng ký.
          </p>
        </div>
      </div>

      {/* Draft / Supplement / Withdrawn Banners */}
      {draftApplication ? (
        <Alert variant={wasWithdrawn ? "warning" : "info"}>
          <FileText className="size-4" />
          <div>
            <AlertTitle>
              {wasWithdrawn
                ? "Hồ sơ đã được kích hoạt lại"
                : requiresSupplement
                  ? "Hồ sơ yêu cầu bổ sung"
                  : "Bạn đang tiếp tục bản nháp"}
            </AlertTitle>
            <AlertDescription>
              {wasWithdrawn
                ? "Hồ sơ trước đã được rút. Bạn có thể nộp lại hồ sơ này khi đợt đăng ký vẫn còn mở."
                : requiresSupplement
                  ? "Cập nhật thông tin theo ghi chú của cán bộ rồi nộp lại hồ sơ."
                  : "Thông tin hiện tại chưa được gửi đến nhà trường. Bạn có thể lưu lại nhiều lần rồi nộp khi đã hoàn tất."}
            </AlertDescription>
            {requiresSupplement && draftApplication?.reviewNote ? (
              <div className="mt-2.5 rounded-md border border-warning/30 bg-warning/10 p-3 text-xs text-foreground sm:text-sm">
                <span className="font-semibold">Ghi chú xét duyệt:</span>{" "}
                {draftApplication.reviewNote}
              </div>
            ) : null}
          </div>
        </Alert>
      ) : null}

      {isCheckingApplication ? (
        <Alert>
          <LoaderCircle className="size-4 animate-spin" />
          <div>
            <AlertTitle>Đang kiểm tra hồ sơ hiện có</AlertTitle>
            <AlertDescription>
              Bạn có thể xem trước biểu mẫu trong lúc hệ thống kiểm tra hồ sơ
              của bạn.
            </AlertDescription>
          </div>
        </Alert>
      ) : null}

      {profileNotLinked ? (
        <Alert variant="warning">
          <Info className="size-4" />
          <div>
            <AlertTitle>Chưa thể nộp hồ sơ</AlertTitle>
            <AlertDescription>
              Chưa tìm thấy hồ sơ sinh viên được đồng bộ từ UIS. Vui lòng đăng
              nhập lại hoặc liên hệ phòng Công tác sinh viên để được hỗ trợ.
            </AlertDescription>
          </div>
        </Alert>
      ) : null}

      {applicationCheckFailed ? (
        <Alert variant="destructive">
          <Info className="size-4" />
          <div>
            <AlertTitle>Không thể kiểm tra hồ sơ hiện có</AlertTitle>
            <AlertDescription>
              {applicationsQuery.error instanceof Error
                ? applicationsQuery.error.message
                : "Vui lòng tải lại trang và thử lại."}
            </AlertDescription>
          </div>
        </Alert>
      ) : null}

      <form onSubmit={submit} className="space-y-5 sm:space-y-6">
        {/* Card 1: Chọn đợt đăng ký */}
        <Card>
          <CardHeader className="p-4 sm:p-6 sm:pb-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-0.5 sm:space-y-1">
                <CardTitle className="text-sm font-semibold sm:text-base">
                  1. Chọn đợt đăng ký
                </CardTitle>
                <CardDescription className="text-xs sm:text-sm">
                  Hồ sơ sẽ được gửi vào đợt bạn chọn bên dưới.
                </CardDescription>
              </div>
              <Badge
                variant="success"
                className="w-fit self-start sm:self-auto"
              >
                Đang mở
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 p-4 pt-0 sm:p-6 sm:pt-0">
            <Select value={selectedPeriod.id} onValueChange={setPeriodId}>
              <SelectTrigger className="h-10 text-xs sm:text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {periods.map((period) => (
                  <SelectItem
                    key={period.id}
                    value={period.id}
                    className="text-xs sm:text-sm"
                  >
                    {period.name} · Hạn {formatDateValue(period.endAt)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <Calendar className="size-3.5 text-primary shrink-0" />
                Đợt: {selectedPeriod.name}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="size-3.5 shrink-0" />
                Hạn nộp:{" "}
                <strong className="text-foreground">
                  {formatDateValue(selectedPeriod.endAt)}
                </strong>
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Thông tin sinh viên - đã thêm Ngành & sắp xếp 2 cột đều (8 half + 1 full) */}
        <Card>
          <CardHeader className="p-4 sm:p-6 sm:pb-3">
            <CardTitle className="text-base font-semibold">
              2. Thông tin sinh viên
            </CardTitle>
            <CardDescription>
              Thông tin được lấy từ hồ sơ sinh viên. Nếu có sai lệch, hãy liên
              hệ phòng Công tác sinh viên để cập nhật.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0 sm:p-6 sm:pt-0">
            {studentProfile ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="student-code">Mã sinh viên</Label>
                  <Input
                    id="student-code"
                    value={studentProfile.studentCode}
                    readOnly
                    className="bg-muted/40 font-mono cursor-not-allowed"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-full-name">Họ và tên</Label>
                  <Input
                    id="student-full-name"
                    value={studentProfile.fullName}
                    readOnly
                    className="bg-muted/40 font-medium cursor-not-allowed"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-class-faculty">Lớp / Khoa</Label>
                  <Input
                    id="student-class-faculty"
                    value={classAndFaculty}
                    onChange={(e) => setClassAndFaculty(e.target.value)}
                    placeholder="VD: CNTT-K45 / Khoa CNTT"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-major">Ngành</Label>
                  <Input
                    id="student-major"
                    value={major}
                    onChange={(e) => setMajor(e.target.value)}
                    placeholder="VD: Công nghệ thông tin"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-personal-email">Email cá nhân</Label>
                  <Input
                    id="student-personal-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="VD: ten@vidu.com"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-phone-number">Số điện thoại</Label>
                  <Input
                    id="student-phone-number"
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="VD: 0901234567"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-school-email">Email trường</Label>
                  <Input
                    id="student-school-email"
                    type="email"
                    value={schoolEmail}
                    onChange={(e) => setSchoolEmail(e.target.value)}
                    placeholder="VD: masv@qnu.edu.vn"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="student-ethnicity">Dân tộc</Label>
                  <Select value={ethnicity} onValueChange={setEthnicity}>
                    <SelectTrigger id="student-ethnicity" aria-label="Dân tộc">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="kinh">Kinh</SelectItem>
                      <SelectItem value="khac">Khác</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="student-permanent-address">
                    Nơi thường trú
                  </Label>
                  <Input
                    id="student-permanent-address"
                    value={permanentAddress}
                    onChange={(e) => setPermanentAddress(e.target.value)}
                    placeholder="VD: 123 Đường ... , Quy Nhơn"
                  />
                </div>
              </div>
            ) : (
              <Alert variant="warning">
                <Info className="size-4" />
                <div>
                  <AlertTitle>Chưa có hồ sơ sinh viên được đồng bộ</AlertTitle>
                  <AlertDescription>
                    Bạn chưa thể gửi đăng ký cho đến khi hệ thống đồng bộ hồ sơ
                    sinh viên từ UIS.
                  </AlertDescription>
                </div>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Card 3: Thuộc đối tượng ưu tiên (Radio Group Cards) */}
        <Card>
          <CardHeader className="p-4 sm:p-6 sm:pb-3">
            <div className="space-y-0.5 sm:space-y-1">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold sm:text-base">
                <Award className="size-4 text-primary shrink-0" />
                3. Thuộc đối tượng ưu tiên
              </CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Vui lòng chọn đối tượng phù hợp với hoàn cảnh của bạn. Nếu không
                thuộc diện ưu tiên, bạn có thể bỏ qua phần này.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0 sm:p-6 sm:pt-0">
            <RadioGroup
              value={priorityObjectId}
              onValueChange={setPriorityObjectId}
              className="space-y-2 sm:space-y-2.5"
            >
              {/* Default none option */}
              <label
                htmlFor="priority-none"
                className={cn(
                  "flex cursor-pointer items-center justify-between rounded-lg border p-3 transition-all hover:bg-muted/40 sm:p-3.5",
                  priorityObjectId === "none"
                    ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                    : "border-border",
                )}
              >
                <div className="flex items-center gap-2.5 sm:gap-3">
                  <RadioGroupItem value="none" id="priority-none" />
                  <span className="text-xs font-medium text-foreground sm:text-sm">
                    Không thuộc diện ưu tiên (Mặc định)
                  </span>
                </div>
              </label>

              {/* Priority list */}
              {priorityObjects.map((priority) => {
                const isSelected = priorityObjectId === priority.id;
                const priorityInputId = `priority-${priority.id}`;
                return (
                  <label
                    key={priority.id}
                    htmlFor={priorityInputId}
                    className={cn(
                      "flex cursor-pointer items-start justify-between gap-2.5 rounded-lg border p-3 transition-all hover:bg-muted/40 sm:gap-3 sm:p-3.5",
                      isSelected
                        ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                        : "border-border",
                    )}
                  >
                    <div className="flex items-start gap-2.5 sm:gap-3">
                      <RadioGroupItem
                        value={priority.id}
                        id={priorityInputId}
                        className="mt-0.5 shrink-0"
                      />
                      <div className="space-y-0.5">
                        <span className="block text-xs font-medium leading-snug text-foreground sm:text-sm sm:leading-normal">
                          {priority.name}
                        </span>
                        {priority.description ? (
                          <p className="text-[11px] text-muted-foreground sm:text-xs">
                            {priority.description}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </label>
                );
              })}
            </RadioGroup>
          </CardContent>
        </Card>

        {/* Card minh chứng cho đối tượng ưu tiên (render động theo VerificationType) */}
        {selectedPriorityObject ? (
          <StudentPriorityEvidenceCard
            priorityObjectId={selectedPriorityObject.id}
            priorityObjectCode={selectedPriorityObject.code}
            priorityObjectName={selectedPriorityObject.name}
            verificationType={selectedPriorityObject.verificationType}
            evidenceInstructions={selectedPriorityObject.evidenceInstructions}
            maxEvidenceFiles={selectedPriorityObject.maxEvidenceFiles}
            maxEvidenceFileSizeBytes={
              selectedPriorityObject.maxEvidenceFileSizeBytes
            }
            files={evidenceFiles}
            residenceAreaId={residenceAreaId}
            residenceVillage={residenceVillage}
            onFilesChange={setEvidenceFiles}
            onResidenceAreaChange={setResidenceAreaId}
            onResidenceVillageChange={setResidenceVillage}
            disabled={submitMutation.isPending || draftMutation.isPending}
          />
        ) : null}

        {/* Card 4: Cam kết */}
        <Card>
          <CardHeader className="p-4 sm:p-6 sm:pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold sm:text-base">
              <ShieldCheck className="size-4 text-primary shrink-0" />
              4. Cam kết
            </CardTitle>
            <CardDescription className="text-xs sm:text-sm">
              Sinh viên cam kết các thông tin kê khai trong biểu mẫu là đúng sự
              thật và chịu trách nhiệm trước Nhà trường về nội dung đã cung cấp.
              Trường hợp phát hiện kê khai không đúng hoặc không đầy đủ, Nhà
              trường có quyền hủy kết quả xét duyệt theo quy định.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0 sm:p-6 sm:pt-0">
            <label
              htmlFor="agreed-terms"
              className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-primary/20 bg-primary/5 p-3.5 transition-colors hover:bg-primary/8 sm:gap-3 sm:p-4"
            >
              <Checkbox
                id="agreed-terms"
                checked={agreedTerms}
                onCheckedChange={(checked) => setAgreedTerms(Boolean(checked))}
                className="mt-0.5 shrink-0"
              />
              <span className="text-xs leading-relaxed text-foreground sm:text-sm">
                Tôi xin cam đoan các thông tin kê khai trên là hoàn toàn chính
                xác và chịu trách nhiệm trước Nhà trường.
              </span>
            </label>
          </CardContent>
        </Card>

        {/* Errors */}
        {submitMutation.isError ? (
          <Alert variant="destructive">
            <Info className="size-4" />
            <div>
              <AlertTitle>Chưa thể nộp hồ sơ</AlertTitle>
              <AlertDescription>
                {submitMutation.error instanceof Error
                  ? submitMutation.error.message
                  : "Vui lòng kiểm tra lại thông tin và thử lại."}
              </AlertDescription>
            </div>
          </Alert>
        ) : null}

        {draftMutation.isError ? (
          <Alert variant="destructive">
            <Info className="size-4" />
            <div>
              <AlertTitle>Chưa thể lưu bản nháp</AlertTitle>
              <AlertDescription>
                {draftMutation.error instanceof Error
                  ? draftMutation.error.message
                  : "Vui lòng kiểm tra lại thông tin và thử lại."}
              </AlertDescription>
            </div>
          </Alert>
        ) : null}

        {/* Actions - Responsive */}
        <div className="flex flex-col-reverse gap-2.5 pt-2 sm:flex-row sm:justify-end sm:gap-3">
          <Button
            type="button"
            variant="outline"
            asChild
            className="h-10 sm:h-9"
          >
            <Link to="/dashboard">Hủy</Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!draftReady}
            onClick={saveDraft}
            className="h-10 sm:h-9"
          >
            {draftMutation.isPending ? (
              <>
                <LoaderCircle className="size-4 animate-spin" /> Đang lưu...
              </>
            ) : (
              "Lưu bản nháp"
            )}
          </Button>
          <Button
            type="submit"
            disabled={!formReady}
            className="h-10 gap-1.5 sm:h-9 sm:min-w-36"
          >
            {submitMutation.isPending ? (
              <>
                <LoaderCircle className="size-4 animate-spin" /> Đang nộp...
              </>
            ) : (
              <>
                Nộp hồ sơ đăng ký <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </div>

        {selectedPriorityObject && (!evidenceReady || !residenceReady) ? (
          <Alert variant="warning">
            <Info className="size-4" />
            <div>
              <AlertTitle>
                Đối tượng &quot;{selectedPriorityObject.name}&quot; cần thêm
                minh chứng
              </AlertTitle>
              <AlertDescription className="text-xs">
                {requiresEvidence && !evidenceReady
                  ? `Cần tải lên tối thiểu 1 ảnh minh chứng (tối đa ${selectedPriorityObject.maxEvidenceFiles} ảnh).`
                  : null}
                {requiresEvidence &&
                !evidenceReady &&
                requiresResidence &&
                !residenceReady
                  ? " "
                  : null}
                {requiresResidence && !residenceReady
                  ? "Cần chọn một địa bàn hành chính thuộc danh sách được cấu hình."
                  : null}
              </AlertDescription>
            </div>
          </Alert>
        ) : null}
      </form>
    </div>
  );
}

function RegistrationPageSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-5 px-3.5 sm:space-y-6 sm:px-6">
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-7 w-56 sm:h-8 sm:w-64" />
        <Skeleton className="h-4 w-full sm:w-96" />
      </div>

      <Card>
        <CardHeader className="p-4 sm:p-6 sm:pb-3">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-60" />
        </CardHeader>
        <CardContent className="space-y-3 p-4 pt-0 sm:p-6 sm:pt-0">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-4 sm:p-6 sm:pb-3">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="space-y-3.5 p-4 pt-0 sm:p-6 sm:pt-0">
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full sm:col-span-2" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-4 sm:p-6 sm:pb-3">
          <Skeleton className="h-5 w-52" />
          <Skeleton className="h-4 w-80" />
        </CardHeader>
        <CardContent className="space-y-2.5 p-4 pt-0 sm:p-6 sm:pt-0">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  FileCheck,
  Loader2,
  MessageSquare,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { DocumentTypeIcon } from "@/components/admin/document-file-icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/inbox")({
  component: InboxPage,
});

export type SubmissionStatus =
  | "pending"
  | "syncing"
  | "published"
  | "changes_requested";

export type DiffChange = {
  id: string;
  sectionTitle: string;
  originalText: string;
  proposedText: string;
  aiVerification: string;
  isVerified: boolean;
};

export type SubmissionItem = {
  id: string;
  title: string;
  sourceId: string;
  fileName: string;
  version: string;
  author: string;
  department: string;
  summary: string;
  bundleSha256: string;
  submittedAt: string;
  status: SubmissionStatus;
  changesCount: number;
  changes: DiffChange[];
  // Background Task Progress
  syncProgress?: number;
  syncStep?: string;
};

const initialSubmissions: SubmissionItem[] = [
  {
    id: "sub_01",
    title: "Hiệu đính mốc pháp lý thành lập Trường năm 1981",
    sourceId: "du_lieu_rag_2026",
    fileName: "Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx",
    version: "v2.1",
    author: "Nguyễn Văn Hùng",
    department: "Ban Biên tập Tri thức Số",
    summary:
      "Làm rõ sự khác biệt giữa Quyết định số 1842/QĐ ngày 21/12/1977 (thành lập Cơ sở ĐHSP Quy Nhơn) và Quyết định số 02/HĐBT ngày 13/7/1981 (thành lập Trường ĐHSP Quy Nhơn), chống nhầm lẫn câu trả lời của Trợ lý RAG.",
    bundleSha256:
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    submittedAt: "Hôm nay, 09:30",
    status: "pending",
    changesCount: 2,
    changes: [
      {
        id: "c_01",
        sectionTitle: "Mục 2: Lịch sử hình thành và các mốc pháp lý",
        originalText: "Ngày 13/7/1981, thành lập Trường Đại học Quy Nhơn.",
        proposedText:
          "Ngày 13/7/1981, Hội đồng Bộ trưởng ban hành Quyết định số 02/HĐBT thành lập Trường Đại học Sư phạm Quy Nhơn (đến 30/10/2003, Thủ tướng Chính phủ mới ký Quyết định số 221/2003/QĐ-TTg đổi tên thành Trường Đại học Quy Nhơn).",
        aiVerification:
          "Đối chiếu chính xác 100% với tệp lưu trữ Quyết định 02/HĐBT tại Văn phòng Trường.",
        isVerified: true,
      },
      {
        id: "c_02",
        sectionTitle: "Mục 3: Định mức thu học phí theo tín chỉ",
        originalText:
          "Khối ngành Kỹ thuật & CNTT: 55.000đ / tín chỉ (lỗi OCR do vết mờ scan).",
        proposedText:
          "Khối ngành Kỹ thuật & Công nghệ thông tin: Định mức thu là 550.000 VNĐ / tín chỉ.",
        aiVerification:
          "Đã hiệu đính số tiền thiếu số 0, khớp đúng biểu giá theo Nghị định 97/2023/NĐ-CP.",
        isVerified: true,
      },
    ],
  },
  {
    id: "sub_02",
    title: "Cập nhật học phí ngành Trí tuệ Nhân tạo & Khoa học Dữ liệu",
    sourceId: "src_tuition_2026",
    fileName: "Bang_hoc_phi_nam_hoc_2026_2027.xlsx",
    version: "v1.2",
    author: "Trần Thị Mai",
    department: "Phòng Kế hoạch - Tài chính",
    summary:
      "Bổ sung định mức học phí mới theo Nghị định 97 cho khối ngành Kỹ thuật - Công nghệ và chính sách cấp bù sinh hoạt phí Sư phạm năm học 2026 - 2027.",
    bundleSha256:
      "a4f89b1c78432a901e457f6b9021c3d5e789a1b2c3d4e5f6a7b8c9d0e1f2a3b4",
    submittedAt: "Hôm qua, 15:45",
    status: "pending",
    changesCount: 1,
    changes: [
      {
        id: "c_03",
        sectionTitle: "Bảng 1: Biểu phí ngành mới",
        originalText: "Ngành Trí tuệ Nhân tạo: Chưa có định mức riêng.",
        proposedText:
          "Ngành Trí tuệ Nhân tạo & Khoa học Dữ liệu: Áp dụng định mức khối Kỹ thuật 550.000 VNĐ / tín chỉ.",
        aiVerification:
          "Khớp Tờ trình số 45/TTr-KHTC đã được Hội đồng trường phê duyệt.",
        isVerified: true,
      },
    ],
  },
  {
    id: "sub_03",
    title: "Đề án tuyển sinh đại học chính quy năm 2026",
    sourceId: "src_admissions_2026",
    fileName: "De_an_tuyen_sinh_2026.pdf",
    version: "v3.0",
    author: "Lê Hoàng Nam",
    department: "Hội đồng Tuyển sinh",
    summary:
      "Công bố 4 phương thức tuyển sinh cho 50 ngành đào tạo, tổng chỉ tiêu 5.200 sinh viên và chính sách học bổng đầu vào thủ khoa.",
    bundleSha256:
      "9f8e7d6c5b4a3210fedcba9876543210abcdef0123456789abcdef0123456789",
    submittedAt: "2 ngày trước",
    status: "published",
    changesCount: 3,
    changes: [
      {
        id: "c_04",
        sectionTitle: "Phần I: Chỉ tiêu tuyển sinh 2026",
        originalText: "Chỉ tiêu dự kiến: 5.000 sinh viên.",
        proposedText: "Chỉ tiêu chính thức: 5.200 sinh viên đại học chính quy.",
        aiVerification: "Khớp Quyết định phê duyệt chỉ tiêu của Bộ GD&ĐT.",
        isVerified: true,
      },
    ],
  },
];

function InboxPage() {
  const navigate = useNavigate();

  // Submissions State
  const [submissions, setSubmissions] =
    useState<SubmissionItem[]>(initialSubmissions);
  const [selectedId, setSelectedId] = useState<string>("sub_01");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Dialog State: Request Changes
  const [isRequestChangesOpen, setIsRequestChangesOpen] = useState(false);
  const [feedbackReason, setFeedbackReason] = useState("");

  // Background Task Simulation State
  const [isPublishing, setIsPublishing] = useState(false);

  // Selected Submission
  const selectedSubmission =
    submissions.find((s) => s.id === selectedId) || submissions[0];

  // Stats calculation
  const pendingCount = submissions.filter((s) => s.status === "pending").length;
  const syncingCount = submissions.filter((s) => s.status === "syncing").length;
  const publishedCount = submissions.filter(
    (s) => s.status === "published",
  ).length;
  const rejectedCount = submissions.filter(
    (s) => s.status === "changes_requested",
  ).length;

  // Filtered List
  const filteredSubmissions = submissions.filter((s) => {
    if (statusFilter !== "all" && s.status !== statusFilter) return false;
    if (
      searchQuery.trim() &&
      !s.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !s.fileName.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !s.author.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  // Handle Approve & Trigger Background Worker
  const handleApproveAndPublish = (submissionId: string) => {
    setIsPublishing(true);

    // 1. Immediately switch status to syncing with progress
    setSubmissions((prev) =>
      prev.map((s) =>
        s.id === submissionId
          ? {
              ...s,
              status: "syncing",
              syncProgress: 25,
              syncStep: "Đang trích xuất Chunks & Tables (ARQ Worker)...",
            }
          : s,
      ),
    );

    toast.info(
      "Đã phê duyệt bản đệ trình! Tác vụ nền bắt đầu đồng bộ vào Vector Database (Qdrant)...",
    );

    // 2. Simulate step 2: Generating Embeddings
    setTimeout(() => {
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === submissionId
            ? {
                ...s,
                syncProgress: 65,
                syncStep:
                  "Đang tính toán vector embeddings với model BGE-M3...",
              }
            : s,
        ),
      );
    }, 1200);

    // 3. Simulate step 3: Updating Qdrant index
    setTimeout(() => {
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === submissionId
            ? {
                ...s,
                syncProgress: 90,
                syncStep: "Đang cập nhật chỉ mục Qdrant và kích hoạt cờ RAG...",
              }
            : s,
        ),
      );
    }, 2400);

    // 4. Complete background task -> Published & Ready
    setTimeout(() => {
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === submissionId
            ? {
                ...s,
                status: "published",
                syncProgress: 100,
                syncStep: "Đã sẵn sàng phục vụ hỏi đáp trên Trợ lý AI!",
              }
            : s,
        ),
      );
      setIsPublishing(false);
      toast.success(
        "🎉 Tác vụ nền hoàn tất 100%! Bản tri thức đã phát hành chính thức và sẵn sàng phục vụ sinh viên.",
      );
    }, 3600);
  };

  // Handle Request Changes
  const handleConfirmRequestChanges = () => {
    if (!feedbackReason.trim()) {
      toast.error("Vui lòng nhập lý do hoặc nội dung cần chỉnh sửa!");
      return;
    }

    setSubmissions((prev) =>
      prev.map((s) =>
        s.id === selectedId
          ? {
              ...s,
              status: "changes_requested",
            }
          : s,
      ),
    );

    setIsRequestChangesOpen(false);
    setFeedbackReason("");
    toast.warning(
      "Đã gửi yêu cầu chỉnh sửa kèm lý do phản hồi về cho chuyên viên biên soạn.",
    );
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-background select-none overflow-x-hidden">
      {/* ========================================================================= */}
      {/* 1. MASTER HEADER                                                          */}
      {/* ========================================================================= */}
      <header className="flex h-14 items-center justify-between border-b border-border/60 bg-card px-4 gap-4 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground shrink-0"
          >
            <Link to="/knowledge" aria-label="Quay lại kho tri thức">
              <ArrowLeft className="size-4" />
            </Link>
          </Button>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-xs font-bold text-foreground uppercase tracking-tight">
                Hộp thư Duyệt & Xử lý (Review Inbox)
              </h1>
              <Badge
                variant="outline"
                className="text-[10px] h-4 bg-primary/10 text-primary border-primary/30 font-medium"
              >
                Phân hệ 3
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground truncate">
              Thẩm định các bản đệ trình hiệu đính văn bản trước khi phát hành
              vào hệ thống RAG
            </p>
          </div>
        </div>

        {/* Right Header Status */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 px-2.5 py-1 rounded-md border border-border/50">
            <ShieldCheck className="size-3.5 text-emerald-600" />
            <span className="text-[11px] font-medium hidden sm:inline">
              Cổng duyệt có băm chứng từ (SHA-256)
            </span>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSubmissions(initialSubmissions);
              toast.info("Đã làm mới danh sách đệ trình.");
            }}
            className="size-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
            title="Làm mới hộp thư"
          >
            <RefreshCw className="size-3.5" />
          </Button>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* 2. MASTER-DETAIL SPLIT VIEW (50:50 or 40:60)                             */}
      {/* ========================================================================= */}
      <div className="flex flex-1 overflow-hidden min-w-0">
        {/* ======================================================================= */}
        {/* LEFT PANE: SUBMISSIONS LIST (MASTER)                                   */}
        {/* ======================================================================= */}
        <div className="w-full md:w-[420px] lg:w-[460px] flex flex-col border-r border-border/60 bg-muted/10 shrink-0 min-w-0">
          {/* Filter Tabs & Search */}
          <div className="p-3 border-b border-border/60 bg-card space-y-2.5 shrink-0">
            {/* Status Filter Chips */}
            <div className="flex items-center gap-1 overflow-x-auto pb-0.5 text-xs [scrollbar-width:none]">
              <button
                type="button"
                onClick={() => setStatusFilter("all")}
                className={cn(
                  "px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer shrink-0",
                  statusFilter === "all"
                    ? "bg-foreground text-background font-semibold"
                    : "bg-muted/60 text-muted-foreground hover:text-foreground",
                )}
              >
                Tất cả ({submissions.length})
              </button>

              <button
                type="button"
                onClick={() => setStatusFilter("pending")}
                className={cn(
                  "px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer shrink-0 flex items-center gap-1",
                  statusFilter === "pending"
                    ? "bg-amber-500 text-white font-semibold"
                    : "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20",
                )}
              >
                <span>Chờ duyệt</span>
                <span className="text-[10px] bg-amber-600/30 text-amber-950 dark:text-amber-100 px-1 rounded-full">
                  {pendingCount}
                </span>
              </button>

              {syncingCount > 0 && (
                <button
                  type="button"
                  onClick={() => setStatusFilter("syncing")}
                  className={cn(
                    "px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer shrink-0 flex items-center gap-1",
                    statusFilter === "syncing"
                      ? "bg-sky-600 text-white font-semibold"
                      : "bg-sky-500/10 text-sky-600 hover:bg-sky-500/20",
                  )}
                >
                  <Loader2 className="size-2.5 animate-spin" />
                  <span>Đồng bộ ({syncingCount})</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => setStatusFilter("published")}
                className={cn(
                  "px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer shrink-0",
                  statusFilter === "published"
                    ? "bg-emerald-600 text-white font-semibold"
                    : "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20",
                )}
              >
                Đã phát hành ({publishedCount})
              </button>

              <button
                type="button"
                onClick={() => setStatusFilter("changes_requested")}
                className={cn(
                  "px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer shrink-0",
                  statusFilter === "changes_requested"
                    ? "bg-rose-600 text-white font-semibold"
                    : "bg-rose-500/10 text-rose-600 hover:bg-rose-500/20",
                )}
              >
                Cần sửa ({rejectedCount})
              </button>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="size-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Tìm theo tiêu đề, người gửi, tệp..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-8 pl-8 pr-3 rounded-md border border-border/80 bg-background text-xs placeholder:text-muted-foreground/70"
              />
            </div>
          </div>

          {/* Submissions Cards List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {filteredSubmissions.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                Không tìm thấy bản đệ trình nào phù hợp.
              </div>
            ) : (
              filteredSubmissions.map((sub) => {
                const isSelected = sub.id === selectedId;

                return (
                  <button
                    type="button"
                    key={sub.id}
                    onClick={() => setSelectedId(sub.id)}
                    className={cn(
                      "w-full text-left p-3 rounded-xl border transition-all cursor-pointer text-xs space-y-2 block",
                      isSelected
                        ? "bg-card border-primary ring-1 ring-primary shadow-xs"
                        : "bg-card/70 border-border/60 hover:bg-card hover:border-border",
                    )}
                  >
                    {/* Top Row: Icon, Title & Status */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <DocumentTypeIcon
                          fileName={sub.fileName}
                          className="size-4.5 mt-0.5 shrink-0"
                        />
                        <div className="min-w-0">
                          <h3
                            className={cn(
                              "font-semibold text-xs leading-snug line-clamp-2",
                              isSelected ? "text-primary" : "text-foreground",
                            )}
                          >
                            {sub.title}
                          </h3>
                          <p className="text-[10px] text-muted-foreground font-mono truncate mt-0.5">
                            {sub.fileName} · {sub.version}
                          </p>
                        </div>
                      </div>

                      {/* Status Badge */}
                      {sub.status === "pending" ? (
                        <Badge
                          variant="outline"
                          className="text-[9.5px] h-4.5 px-1.5 bg-amber-500/10 text-amber-700 border-amber-500/30 shrink-0"
                        >
                          Chờ duyệt
                        </Badge>
                      ) : sub.status === "syncing" ? (
                        <Badge
                          variant="outline"
                          className="text-[9.5px] h-4.5 px-1.5 bg-sky-500/15 text-sky-700 border-sky-500/40 shrink-0 gap-1 animate-pulse"
                        >
                          <Loader2 className="size-2.5 animate-spin" />
                          <span>Đang nạp vector</span>
                        </Badge>
                      ) : sub.status === "published" ? (
                        <Badge
                          variant="outline"
                          className="text-[9.5px] h-4.5 px-1.5 bg-emerald-500/10 text-emerald-700 border-emerald-500/30 shrink-0"
                        >
                          Đã phát hành
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="text-[9.5px] h-4.5 px-1.5 bg-rose-500/10 text-rose-700 border-rose-500/30 shrink-0"
                        >
                          Yêu cầu sửa
                        </Badge>
                      )}
                    </div>

                    {/* Summary Excerpt */}
                    <p className="text-muted-foreground leading-relaxed line-clamp-2 text-[11px]">
                      {sub.summary}
                    </p>

                    {/* Footer: Author & Changes count */}
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-border/40">
                      <span className="truncate max-w-[200px]">
                        {sub.author} ({sub.department})
                      </span>
                      <span className="font-medium text-foreground shrink-0">
                        {sub.changesCount} điểm sửa
                      </span>
                    </div>

                    {/* Live Progress Bar when Syncing */}
                    {sub.status === "syncing" && (
                      <div className="pt-1 space-y-1">
                        <Progress
                          value={sub.syncProgress ?? 50}
                          className="h-1.5 bg-sky-500/20 [&>div]:bg-sky-600"
                        />
                        <p className="text-[9.5px] text-sky-600 font-mono truncate">
                          {sub.syncStep}
                        </p>
                      </div>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ======================================================================= */}
        {/* RIGHT PANE: DETAIL INSPECTOR & DELTA DIFF (DETAIL)                     */}
        {/* ======================================================================= */}
        {selectedSubmission ? (
          <div className="flex-1 flex flex-col bg-background min-w-0 overflow-hidden">
            {/* Detail Top Header: Action Bar */}
            <div className="p-3 border-b border-border/60 bg-card flex items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  <Link
                    to="/knowledge/$sourceId"
                    params={{ sourceId: selectedSubmission.sourceId }}
                    title="Mở toàn màn hình trong Studio đối chiếu 50:50"
                  >
                    <ExternalLink className="size-3.5" />
                    <span>Mở Studio 50:50</span>
                  </Link>
                </Button>

                <div className="h-4 w-px bg-border/60 hidden sm:block" />

                <span className="text-[11px] text-muted-foreground font-mono hidden sm:inline">
                  Mã đệ trình: {selectedSubmission.id}
                </span>
              </div>

              {/* Action Buttons for Decision */}
              <div className="flex items-center gap-2">
                {selectedSubmission.status === "pending" && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsRequestChangesOpen(true)}
                      className="h-8 gap-1.5 text-xs text-rose-600 border-rose-500/30 hover:bg-rose-500/10 cursor-pointer"
                    >
                      <MessageSquare className="size-3.5" />
                      <span>Yêu cầu sửa</span>
                    </Button>

                    <Button
                      size="sm"
                      disabled={isPublishing}
                      onClick={() =>
                        handleApproveAndPublish(selectedSubmission.id)
                      }
                      className="h-8 gap-1.5 text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 shadow-2xs cursor-pointer"
                    >
                      {isPublishing ? (
                        <>
                          <Loader2 className="size-3.5 animate-spin" />
                          <span>Đang duyệt...</span>
                        </>
                      ) : (
                        <>
                          <Check className="size-3.5" />
                          <span>Duyệt & Phát hành</span>
                        </>
                      )}
                    </Button>
                  </>
                )}

                {selectedSubmission.status === "syncing" && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-sky-500/10 text-sky-700 border border-sky-500/30 text-xs">
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>
                      Đang chạy tác vụ nền ({selectedSubmission.syncProgress}%)
                    </span>
                  </div>
                )}

                {selectedSubmission.status === "published" && (
                  <Button
                    size="sm"
                    onClick={() => navigate({ to: "/chat" })}
                    className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-2xs"
                  >
                    <Bot className="size-3.5" />
                    <span>Hỏi đáp với Trợ lý AI</span>
                  </Button>
                )}

                {selectedSubmission.status === "changes_requested" && (
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-rose-500/10 text-rose-700 border border-rose-500/30 text-xs">
                    <AlertCircle className="size-3.5" />
                    <span>Đã gửi phản hồi yêu cầu hiệu chỉnh</span>
                  </div>
                )}
              </div>
            </div>

            {/* Detail Body Viewport */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
              {/* Submission Title & Metadata Overview Box */}
              <div className="bg-card border border-border/70 rounded-xl p-5 shadow-xs space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h2 className="text-sm font-bold text-foreground">
                      {selectedSubmission.title}
                    </h2>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {selectedSubmission.summary}
                    </p>
                  </div>

                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono px-2 py-0.5 shrink-0"
                  >
                    {selectedSubmission.version}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-border/50 text-[11px]">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">
                      Người đệ trình
                    </span>
                    <span className="font-medium text-foreground">
                      {selectedSubmission.author}
                    </span>
                    <p className="text-muted-foreground text-[10px]">
                      {selectedSubmission.department}
                    </p>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">
                      Tệp văn bản nguồn
                    </span>
                    <span className="font-mono text-foreground font-medium">
                      {selectedSubmission.fileName}
                    </span>
                    <p className="text-muted-foreground text-[10px]">
                      Gửi lúc: {selectedSubmission.submittedAt}
                    </p>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">
                      Mã băm chứng từ (SHA-256)
                    </span>
                    <span className="font-mono text-muted-foreground text-[10px] truncate block">
                      {selectedSubmission.bundleSha256.substring(0, 24)}...
                    </span>
                    <p className="text-emerald-600 text-[10px] flex items-center gap-1 font-medium">
                      <ShieldCheck className="size-3" />
                      <span>Toàn vẹn dữ liệu gốc</span>
                    </p>
                  </div>
                </div>
              </div>

              {/* ================================================================= */}
              {/* BACKGROUND WORKER PIPELINE VISUALIZATION                          */}
              {/* ================================================================= */}
              <div className="bg-card border border-border/70 rounded-xl p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="size-4 text-primary" />
                    <h3 className="text-xs font-bold text-foreground uppercase tracking-tight">
                      Tiến trình Tác vụ Nền (Background Processing Pipeline)
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    ARQ Worker + Redis + Qdrant
                  </span>
                </div>

                {/* 3 Steps Pipeline Visualization */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                  {/* Step 1: Review Gate */}
                  <div className="p-3 rounded-lg border border-border/70 bg-muted/20 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-muted-foreground">
                        Bước 1: Review Gate
                      </span>
                      <CheckCircle2 className="size-3.5 text-emerald-600" />
                    </div>
                    <p className="text-xs font-semibold text-foreground">
                      Bóc tách & Kiểm tra lỗi
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Hoàn tất 100% (0 xung đột)
                    </p>
                  </div>

                  {/* Step 2: Approval */}
                  <div
                    className={cn(
                      "p-3 rounded-lg border space-y-1",
                      selectedSubmission.status === "pending"
                        ? "border-amber-500/40 bg-amber-500/5 text-amber-700"
                        : "border-border/70 bg-muted/20 text-foreground",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold opacity-80">
                        Bước 2: Phê duyệt
                      </span>
                      {selectedSubmission.status === "pending" ? (
                        <Clock className="size-3.5 text-amber-600 animate-pulse" />
                      ) : (
                        <CheckCircle2 className="size-3.5 text-emerald-600" />
                      )}
                    </div>
                    <p className="text-xs font-semibold">
                      Xác nhận của Lãnh đạo
                    </p>
                    <p className="text-[10px] opacity-80">
                      {selectedSubmission.status === "pending"
                        ? "Đang chờ Lãnh đạo bấm Duyệt"
                        : "Đã ký duyệt có băm"}
                    </p>
                  </div>

                  {/* Step 3: Vector Qdrant Sync */}
                  <div
                    className={cn(
                      "p-3 rounded-lg border space-y-1",
                      selectedSubmission.status === "syncing"
                        ? "border-sky-500/40 bg-sky-500/5 text-sky-700"
                        : selectedSubmission.status === "published"
                          ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-700"
                          : "border-border/70 bg-muted/10 text-muted-foreground",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold opacity-80">
                        Bước 3: Nạp Vector Qdrant
                      </span>
                      {selectedSubmission.status === "syncing" ? (
                        <Loader2 className="size-3.5 text-sky-600 animate-spin" />
                      ) : selectedSubmission.status === "published" ? (
                        <CheckCircle2 className="size-3.5 text-emerald-600" />
                      ) : (
                        <Database className="size-3.5 opacity-40" />
                      )}
                    </div>
                    <p className="text-xs font-semibold">Chỉ mục RAG tự động</p>
                    <p className="text-[10px] opacity-80">
                      {selectedSubmission.status === "syncing"
                        ? `Đang chạy nền (${selectedSubmission.syncProgress}%)`
                        : selectedSubmission.status === "published"
                          ? "Sẵn sàng phục vụ hỏi đáp"
                          : "Sẽ kích hoạt sau khi Duyệt"}
                    </p>
                  </div>
                </div>

                {/* Live Progress Bar when Syncing */}
                {selectedSubmission.status === "syncing" && (
                  <div className="p-3 rounded-lg bg-sky-500/10 border border-sky-500/20 space-y-2">
                    <div className="flex items-center justify-between text-xs text-sky-800 dark:text-sky-200">
                      <span className="font-medium flex items-center gap-1.5">
                        <Loader2 className="size-3.5 animate-spin" />
                        <span>{selectedSubmission.syncStep}</span>
                      </span>
                      <span className="font-mono font-bold">
                        {selectedSubmission.syncProgress}%
                      </span>
                    </div>
                    <Progress
                      value={selectedSubmission.syncProgress ?? 50}
                      className="h-2 bg-sky-500/20 [&>div]:bg-sky-600"
                    />
                  </div>
                )}
              </div>

              {/* ================================================================= */}
              {/* SIDE-BY-SIDE DELTA DIFF VIEW (BẢNG ĐỐI CHIẾU THAY ĐỔI)           */}
              {/* ================================================================= */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCheck className="size-4 text-primary" />
                    <h3 className="text-xs font-bold text-foreground uppercase tracking-tight">
                      Đối chiếu thay đổi chi tiết (
                      {selectedSubmission.changesCount} điểm)
                    </h3>
                  </div>
                  <span className="text-[10px] text-muted-foreground">
                    So sánh giữa Bản gốc & Bản đã biên soạn
                  </span>
                </div>

                {/* Diff Cards */}
                {selectedSubmission.changes.map((change, index) => (
                  <Card
                    key={change.id}
                    className="border-border/70 bg-card shadow-xs overflow-hidden"
                  >
                    <CardHeader className="p-3 bg-muted/25 border-b border-border/50 py-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-foreground">
                          {change.sectionTitle}
                        </span>
                        <Badge
                          variant="secondary"
                          className="text-[9.5px] font-mono"
                        >
                          Điểm sửa #{index + 1}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4 space-y-3 text-xs">
                      {/* Side by side comparison */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {/* Original Text (Red strike) */}
                        <div className="space-y-1.5 p-3 rounded-lg border border-rose-500/20 bg-rose-500/5">
                          <span className="text-[10px] uppercase font-bold text-rose-600 flex items-center gap-1">
                            <span className="size-2 rounded-full bg-rose-500 inline-block" />
                            <span>Bản gốc trước đó</span>
                          </span>
                          <p className="line-through text-rose-700/80 dark:text-rose-300/80 leading-relaxed font-sans">
                            {change.originalText}
                          </p>
                        </div>

                        {/* Proposed Text (Green highlight) */}
                        <div className="space-y-1.5 p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5">
                          <span className="text-[10px] uppercase font-bold text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                            <span className="size-2 rounded-full bg-emerald-600 inline-block" />
                            <span>Bản đề xuất hiệu đính</span>
                          </span>
                          <p className="text-emerald-950 dark:text-emerald-200 font-medium leading-relaxed font-sans">
                            {change.proposedText}
                          </p>
                        </div>
                      </div>

                      {/* AI Verification Note */}
                      <div className="flex items-start gap-2 p-2.5 rounded-lg bg-primary/5 border border-primary/20 text-[11px] text-primary">
                        <Sparkles className="size-3.5 mt-0.5 shrink-0 text-primary" />
                        <div>
                          <strong>Đánh giá của AI Thẩm định:</strong>{" "}
                          <span>{change.aiVerification}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8 text-xs text-muted-foreground">
            Vui lòng chọn một bản đệ trình bên cột trái để xem xét.
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* 3. DIALOG: YÊU CẦU CHỈNH SỬA                                              */}
      {/* ========================================================================= */}
      <Dialog
        open={isRequestChangesOpen}
        onOpenChange={setIsRequestChangesOpen}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold flex items-center gap-2 text-rose-600">
              <MessageSquare className="size-4" />
              <span>Yêu cầu hiệu chỉnh đệ trình</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Ý kiến phản hồi sẽ được gửi trực tiếp về cho chuyên viên biên soạn
              để tiếp tục hoàn thiện văn bản.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <label
                htmlFor="feedback-reason-input"
                className="font-semibold text-foreground text-xs"
              >
                Nội dung góp ý / Lý do chưa phê duyệt:
              </label>
              <Textarea
                id="feedback-reason-input"
                placeholder="VD: Cần bổ sung thêm phụ lục biểu phí ngành mới theo Nghị định 97 hoặc kiểm tra lại mốc năm ban hành..."
                value={feedbackReason}
                onChange={(e) => setFeedbackReason(e.target.value)}
                className="min-h-[90px] text-xs bg-background"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsRequestChangesOpen(false)}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmRequestChanges}
              className="h-8 text-xs bg-rose-600 hover:bg-rose-700 text-white"
            >
              <Send className="size-3 mr-1" />
              <span>Gửi yêu cầu sửa</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

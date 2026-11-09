import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  Download,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Folder,
  FolderInput,
  FolderOpen,
  FolderPlus,
  GripVertical,
  HardDrive,
  History,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useEffect, useId, useState } from "react";
import { toast } from "sonner";
import { DocumentTypeIcon } from "@/components/admin/document-file-icon";
import { Field, FieldLabel } from "@/components/admin/field";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  type ViewMode,
  ViewModeToggle,
} from "@/components/ui/view-mode-toggle";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/knowledge/")({
  component: KnowledgeExplorerPage,
});

export type DocumentStatus = "ready" | "needs_review" | "processing";
export type FileTypeFilter = "all" | "docx" | "pdf" | "xlsx";

export type DocumentItem = {
  id: string;
  title: string;
  fileName: string;
  fileType: "docx" | "pdf" | "xlsx";
  size: string;
  revision: number;
  folderId: string;
  status: DocumentStatus;
  updatedAt: string;
  effectiveYear: string;
  summary: string;
  aiKeypoints: string[];
  sampleContent: string;
};

export type FolderItem = {
  id: string;
  name: string;
};

const initialFolders: FolderItem[] = [
  { id: "f_training", name: "Đào tạo & Quy chế" },
  { id: "f_admissions", name: "Tuyển sinh 2026" },
  { id: "f_student", name: "Hồ sơ sinh viên" },
  { id: "f_finance", name: "Học phí & Tài chính" },
  { id: "f_standards", name: "Chuẩn đầu ra & Khảo thí" },
];

const initialDocuments: DocumentItem[] = [
  {
    id: "src_43564f0133c57",
    title: "Dữ liệu tri thức về Trường Đại học Quy Nhơn 2026",
    fileName: "Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx",
    fileType: "docx",
    size: "24.5 KB",
    revision: 1,
    folderId: "f_training",
    status: "ready",
    updatedAt: "Vừa xong",
    effectiveYear: "2026 - 2030",
    summary:
      "Cơ sở dữ liệu toàn diện về lịch sử thành lập, cơ cấu 12 khoa chuyên ngành, 4 viện nghiên cứu, và định hướng phát triển trường đại học đa ngành đạt chuẩn chất lượng quốc gia.",
    aiKeypoints: [
      "Thành lập theo Quyết định số 02/HĐBT ngày 13/7/1981 của Hội đồng Bộ trưởng.",
      "Quy mô đào tạo trên 16.000 sinh viên, gồm 50 ngành cử nhân và 28 chuyên ngành sau đại học.",
      "Đạt chuẩn kiểm định chất lượng giáo dục chu kỳ 2 theo chuẩn MOET.",
    ],
    sampleContent:
      "Trường Đại học Quy Nhơn (tiền thân là Trường Đại học Sư phạm Quy Nhơn) được thành lập theo Quyết định số 02/HĐBT ngày 13/7/1981 của Hội đồng Bộ trưởng. Qua hơn 45 năm xây dựng và phát triển, Trường đã trở thành trung tâm đào tạo nguồn nhân lực chất lượng cao, nghiên cứu khoa học và chuyển giao công nghệ hàng đầu khu vực Nam Trung Bộ và Tây Nguyên.",
  },
  {
    id: "src_02_admissions",
    title: "Đề án tuyển sinh đại học chính quy năm 2026",
    fileName: "De_an_tuyen_sinh_2026.pdf",
    fileType: "pdf",
    size: "1.2 MB",
    revision: 1,
    folderId: "f_admissions",
    status: "ready",
    updatedAt: "Hôm qua 14:30",
    effectiveYear: "Năm 2026",
    summary:
      "Chỉ tiêu tuyển sinh 5.200 sinh viên, cơ chế 4 phương thức xét tuyển thẳng, chính sách học bổng đầu vào toàn phần cho thủ khoa và tổ hợp môn thi theo ngành.",
    aiKeypoints: [
      "Tổng chỉ tiêu 5.200 sinh viên chính quy trên toàn bộ 50 ngành đào tạo.",
      "4 phương thức: Điểm thi THPT, Học bạ THPT, ĐGNL ĐHQG, và Xét tuyển thẳng.",
      "Miễn 100% học phí năm 1 cho thí sinh đạt từ 27.0 điểm trở lên.",
    ],
    sampleContent:
      "Năm 2026, Trường Đại học Quy Nhơn tuyển sinh 5.200 chỉ tiêu hệ chính quy. Các phương thức gồm: Phương thức 1: Xét kết quả thi tốt nghiệp THPT năm 2026; Phương thức 2: Xét kết quả học tập cấp THPT (học bạ); Phương thức 3: Xét kết quả thi ĐGNL của ĐHQG TP.HCM và ĐHQG Hà Nội; Phương thức 4: Xét tuyển thẳng theo quy chế của Bộ GD&ĐT và Đề án riêng của Trường.",
  },
  {
    id: "src_03_training",
    title: "Quy chế đào tạo trình độ đại học theo hệ thống tín chỉ",
    fileName: "Quy_che_dao_tao_tin_chi_2026.docx",
    fileType: "docx",
    size: "86.0 KB",
    revision: 1,
    folderId: "f_training",
    status: "ready",
    updatedAt: "2 ngày trước",
    effectiveYear: "Năm học 2026 - 2027",
    summary:
      "Quy định đăng ký học phần, đánh giá thang điểm chữ (A, B, C, D, F), thi cải thiện điểm, cảnh báo học vụ và điều kiện công nhận tốt nghiệp đại học chuẩn.",
    aiKeypoints: [
      "Thang điểm đánh giá: A (4.0), B (3.0), C (2.0), D (1.0), F (0.0).",
      "Điều kiện tốt nghiệp: Tích lũy đủ số tín chỉ, điểm TB tích lũy đạt tối thiểu 2.00/4.00.",
      "Cảnh báo học vụ: Sinh viên có điểm TB học kỳ dưới 1.00 lần đầu hoặc 1.20 hai học kỳ liên tiếp.",
    ],
    sampleContent:
      "Quy chế này quy định việc tổ chức đào tạo trình độ đại học theo hệ thống tín chỉ tại Trường Đại học Quy Nhơn, bao gồm: tổ chức lớp học, đăng ký khối lượng học tập, kiểm tra và đánh giá kết quả, xử lý học vụ và xét tốt nghiệp...",
  },
  {
    id: "src_04_conduct",
    title: "Hướng dẫn đánh giá điểm rèn luyện sinh viên",
    fileName: "Huong_dan_danh_gia_diem_ren_luyen.pdf",
    fileType: "pdf",
    size: "450 KB",
    revision: 1,
    folderId: "f_student",
    status: "needs_review", // Waiting for review/publication
    updatedAt: "3 ngày trước",
    effectiveYear: "Năm học 2026 - 2027",
    summary:
      "Văn bản dự thảo khung thang điểm 100 đánh giá rèn luyện sinh viên theo 5 tiêu chí. Đang chờ duyệt trước khi đưa vào chỉ mục hỏi đáp.",
    aiKeypoints: [
      "Thang điểm tối đa 100 điểm, chia làm 6 bậc: Xuất sắc, Tốt, Khá, Trung bình, Yếu, Kém.",
      "Điểm rèn luyện từ 80 điểm trở lên là điều kiện bắt buộc để xét học bổng khuyến khích.",
      "Sinh viên bị kỷ luật từ mức Khiển trách không được xếp loại Rèn luyện Khá trở lên.",
    ],
    sampleContent:
      "Điểm rèn luyện được đánh giá theo từng học kỳ. Khung điểm gồm 5 tiêu chí: 1. Ý thức học tập (tối đa 20 điểm); 2. Chấp hành nội quy, quy chế (tối đa 25 điểm); 3. Hoạt động phong trào, văn thể mỹ (tối đa 20 điểm); 4. Phẩm chất công dân và quan hệ cộng đồng (tối đa 25 điểm); 5. Tham gia công tác cán bộ lớp, đoàn hội (tối đa 10 điểm).",
  },
  {
    id: "src_05_tuition",
    title: "Bảng định mức học phí năm học 2026 - 2027",
    fileName: "Bang_hoc_phi_nam_hoc_2026_2027.xlsx",
    fileType: "xlsx",
    size: "32.0 KB",
    revision: 1,
    folderId: "f_finance",
    status: "ready",
    updatedAt: "4 ngày trước",
    effectiveYear: "2026 - 2027",
    summary:
      "Định mức học phí theo tín chỉ của các nhóm ngành Sư phạm, Kỹ thuật - Công nghệ, Kinh tế và chính sách cấp sinh hoạt phí theo Nghị định 116.",
    aiKeypoints: [
      "Khối Kỹ thuật & Công nghệ thông tin: 550.000 VNĐ / tín chỉ.",
      "Khối Kinh tế & Quản trị kinh doanh: 480.000 VNĐ / tín chỉ.",
      "Sinh viên Sư phạm được miễn học phí và hỗ trợ 3.630.000 VNĐ / tháng theo NĐ 116/2020/NĐ-CP.",
    ],
    sampleContent:
      "Bảng tổng hợp mức thu học phí năm học 2026 - 2027 theo Nghị định 81/2021/NĐ-CP và Nghị định 97/2023/NĐ-CP sửa đổi của Chính phủ đối với các ngành đào tạo chuẩn của Trường Đại học Quy Nhơn...",
  },
  {
    id: "src_08_scholarships",
    title: "Thông tin học bổng khuyến khích & trợ cấp xã hội",
    fileName: "Thong_tin_hoc_bong_tro_cap_xa_hoi.docx",
    fileType: "docx",
    size: "42.8 KB",
    revision: 1,
    folderId: "f_student",
    status: "needs_review", // Waiting for review/publication
    updatedAt: "Tuần trước",
    effectiveYear: "2026 - 2027",
    summary:
      "Dự thảo quy định mức học bổng khuyến khích học tập loại Xuất sắc (120%), Giỏi (100%), Khá (80%) và trợ cấp hàng tháng cho sinh viên thuộc hộ nghèo.",
    aiKeypoints: [
      "Quỹ học bổng trích tối thiểu 8% từ nguồn thu học phí hệ chính quy.",
      "Học bổng Xuất sắc: Tương đương 120% mức học phí của ngành đào tạo.",
      "Hỗ trợ tiền trợ cấp xã hội chi trả trực tiếp vào tài khoản ngân hàng định kỳ hàng tháng.",
    ],
    sampleContent:
      "Nhà trường trích tối thiểu 8% từ nguồn thu học phí chính quy để lập quỹ học bổng khuyến khích học tập. Mức học bổng được chi trả theo kỳ học và chuyển trực tiếp vào tài khoản ngân hàng của sinh viên đủ điều kiện...",
  },
  {
    id: "src_07_graduation",
    title: "Chuẩn đầu ra ngoại ngữ và tin học các ngành đào tạo",
    fileName: "Chuan_dau_ra_ngoai_ngu_tin_hoc.pdf",
    fileType: "pdf",
    size: "720 KB",
    revision: 1,
    folderId: "f_standards",
    status: "ready",
    updatedAt: "Tuần trước",
    effectiveYear: "2026 - 2028",
    summary:
      "Bảng quy đổi chứng chỉ ngoại ngữ quốc tế (TOEIC, IELTS, VSTEP Bậc 3, Bậc 4) và chuẩn tin học ứng dụng bắt buộc để tốt nghiệp đại học chính quy.",
    aiKeypoints: [
      "Khối ngành Ngôn ngữ: Chuẩn VSTEP Bậc 4 (B2) hoặc IELTS 5.5 trở lên.",
      "Khối ngành Không chuyên ngữ: Chuẩn TOEIC 450, VSTEP Bậc 3 (B1) hoặc tương đương.",
      "Chuẩn Tin học: Chứng chỉ ứng dụng CNTT cơ bản hoặc chứng chỉ quốc tế MOS/IC3.",
    ],
    sampleContent:
      "Quy định yêu cầu chuẩn đầu ra ngoại ngữ và công nghệ thông tin là điều kiện bắt buộc để được xét cấp bằng tốt nghiệp đại học chính quy tại Trường Đại học Quy Nhơn...",
  },
  {
    id: "src_09_calendar",
    title: "Khung kế hoạch thời gian năm học 2026 - 2027",
    fileName: "Ke_hoach_nam_hoc_2026_2027.docx",
    fileType: "docx",
    size: "54.0 KB",
    revision: 1,
    folderId: "f_training",
    status: "processing", // Processing
    updatedAt: "Vừa xong",
    effectiveYear: "2026 - 2027",
    summary:
      "Kế hoạch thời gian giảng dạy, thi học kỳ 1, học kỳ 2 và kỳ học hè năm học 2026 - 2027. Hệ thống AI đang đọc hiểu văn bản.",
    aiKeypoints: [
      "Học kỳ 1 bắt đầu từ ngày 01/09/2026 đến hết ngày 15/01/2027.",
      "Học kỳ 2 bắt đầu từ ngày 15/02/2027 đến hết ngày 30/06/2027.",
      "Kỳ học hè và thực tập doanh nghiệp: Tháng 7 và tháng 8 năm 2027.",
    ],
    sampleContent:
      "Kế hoạch năm học 2026 - 2027 áp dụng cho tất cả các khóa sinh viên chính quy và học viên cao học của Trường Đại học Quy Nhơn...",
  },
];

const fileTypeChips: {
  label: string;
  value: FileTypeFilter;
  icon: typeof FileText;
}[] = [
  { label: "Tất cả tệp", value: "all", icon: FileText },
  { label: "Văn bản Word (.docx)", value: "docx", icon: FileText },
  { label: "Tệp PDF (.pdf)", value: "pdf", icon: FileText },
  { label: "Bảng tính Excel (.xlsx)", value: "xlsx", icon: FileSpreadsheet },
];

export type DragPayload =
  | { type: "document"; doc: DocumentItem }
  | { type: "folder"; folder: FolderItem; index: number };

function KnowledgeExplorerPage() {
  const navigate = useNavigate();
  const folderNameInputId = useId();
  const uploadTitleInputId = useId();
  const moveFolderSelectId = useId();

  const [documents, setDocuments] = useState<DocumentItem[]>(initialDocuments);
  const [folders, setFolders] = useState<FolderItem[]>(initialFolders);
  const [activeFolderId, setActiveFolderId] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedFileType, setSelectedFileType] =
    useState<FileTypeFilter>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [searchQuery, setSearchQuery] = useState("");

  // In-page Drag & Drop State (File & Folder management)
  const [dragPayload, setDragPayload] = useState<DragPayload | null>(null);
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null>(null);
  const [isRootDropTargetHovered, setIsRootDropTargetHovered] = useState(false);

  // Manual Move Dialog State (accessible alternative to drag & drop)
  const [isMoveDialogOpen, setIsMoveDialogOpen] = useState(false);
  const [docToMove, setDocToMove] = useState<DocumentItem | null>(null);
  const [selectedTargetFolderId, setSelectedTargetFolderId] =
    useState<string>("root");

  // Quick Preview Sheet State
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [activeDrawerTab, setActiveDrawerTab] = useState<string>("summary");

  // Upload Dialog State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [customTitle, setCustomTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Create Folder Dialog State
  const [isCreateFolderOpen, setIsCreateFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");

  // Full-page External File Drag and Drop State
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  // Status counts for filtering
  const readyCount = documents.filter((d) => d.status === "ready").length;
  const reviewCount = documents.filter(
    (d) => d.status === "needs_review",
  ).length;
  const processingCount = documents.filter(
    (d) => d.status === "processing",
  ).length;

  // Active folder object (if inside folder)
  const activeFolder = folders.find((f) => f.id === activeFolderId);

  // Filter logic
  const filteredDocs = documents.filter((doc) => {
    // 1. Folder match
    if (activeFolderId !== "all" && doc.folderId !== activeFolderId) {
      return false;
    }
    // 2. Status filter
    if (statusFilter !== "all" && doc.status !== statusFilter) {
      return false;
    }
    // 3. File type filter
    if (selectedFileType !== "all" && doc.fileType !== selectedFileType) {
      return false;
    }
    // 4. Search query match
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = doc.title.toLowerCase().includes(q);
      const matchFile = doc.fileName.toLowerCase().includes(q);
      const matchSummary = doc.summary.toLowerCase().includes(q);
      return matchTitle || matchFile || matchSummary;
    }
    return true;
  });

  // Open Preview Drawer
  const handleOpenPreview = (doc: DocumentItem) => {
    setPreviewDoc(doc);
    setActiveDrawerTab("summary");
    setIsPreviewOpen(true);
  };

  // Upload handler
  const handleUploadFile = useCallback(
    (file: File, targetFolderId?: string, titleOverride?: string) => {
      const isPdfFile = file.name.toLowerCase().endsWith(".pdf");
      const isXlsxFile =
        file.name.toLowerCase().endsWith(".xlsx") ||
        file.name.toLowerCase().endsWith(".csv");

      const finalFolderId =
        targetFolderId || (activeFolderId === "all" ? "root" : activeFolderId);
      const docTitle =
        titleOverride?.trim() ||
        file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ");

      const newDocId = `src_${Date.now()}`;
      const newDoc: DocumentItem = {
        id: newDocId,
        title: docTitle,
        fileName: file.name,
        fileType: isPdfFile ? "pdf" : isXlsxFile ? "xlsx" : "docx",
        size: `${(file.size / 1024).toFixed(1)} KB`,
        revision: 1,
        folderId: finalFolderId,
        status: "processing", // Simulate auto-pipeline
        updatedAt: "Vừa xong",
        effectiveYear: "2026 - 2027",
        summary: `Tệp vừa được nạp vào kho. Trí tuệ nhân tạo QNU AI đang trích xuất văn bản và cấu trúc dữ liệu từ tệp ${file.name}.`,
        aiKeypoints: [
          "Tệp tải lên nguyên vẹn, đã xác thực mã kiểm tra SHA-256.",
          "Hệ thống tự động phân loại cấu trúc nội dung và trích xuất bảng biểu.",
          "Chuẩn bị hoàn tất để gửi duyệt và đưa vào cơ sở dữ liệu hỏi đáp.",
        ],
        sampleContent: `Nội dung trích xuất từ tệp "${docTitle}": Hệ thống đang tự động lập bảng chỉ mục phục vụ hỏi đáp với độ chính xác cao nhất.`,
      };

      setDocuments((prev) => [newDoc, ...prev]);
      toast.info("Đang đọc hiểu văn bản bằng Trí tuệ nhân tạo QNU...");

      // Simulate completion to "needs_review" after 1.5s
      setTimeout(() => {
        setDocuments((prev) =>
          prev.map((d) =>
            d.id === newDocId ? { ...d, status: "needs_review" as const } : d,
          ),
        );
        toast.success(
          `Văn bản "${docTitle}" đã chuẩn bị xong, sẵn sàng để duyệt phát hành!`,
        );
      }, 1500);
    },
    [activeFolderId],
  );

  // Document Dragging
  const handleDocDragStart = (
    e: React.DragEvent<HTMLElement>,
    doc: DocumentItem,
  ) => {
    setDragPayload({ type: "document", doc });
    e.dataTransfer.setData("application/qnu-doc-id", doc.id);
    e.dataTransfer.setData("application/qnu-type", "document");
    e.dataTransfer.effectAllowed = "move";
  };

  // Folder Dragging (reordering or dragging folders)
  const handleFolderDragStart = (
    e: React.DragEvent<HTMLElement>,
    folder: FolderItem,
    index: number,
  ) => {
    setDragPayload({ type: "folder", folder, index });
    e.dataTransfer.setData("application/qnu-folder-id", folder.id);
    e.dataTransfer.setData("application/qnu-type", "folder");
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    setDragPayload(null);
    setDragOverFolderId(null);
    setIsRootDropTargetHovered(false);
  };

  // Drag over a folder card
  const handleFolderDragOver = (
    e: React.DragEvent<HTMLElement>,
    targetFolderId: string,
  ) => {
    if (!dragPayload) return;

    if (dragPayload.type === "document") {
      // Don't drop into folder the doc is already in
      if (dragPayload.doc.folderId === targetFolderId) return;
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "move";
      if (dragOverFolderId !== targetFolderId) {
        setDragOverFolderId(targetFolderId);
      }
    } else if (dragPayload.type === "folder") {
      // Don't drop on itself
      if (dragPayload.folder.id === targetFolderId) return;
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "move";
      if (dragOverFolderId !== targetFolderId) {
        setDragOverFolderId(targetFolderId);
      }
    }
  };

  const handleFolderDragLeave = (
    e: React.DragEvent<HTMLElement>,
    targetFolderId: string,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    if (dragOverFolderId === targetFolderId) {
      setDragOverFolderId(null);
    }
  };

  // Dropping onto a folder card
  const handleFolderDrop = (
    e: React.DragEvent<HTMLElement>,
    targetFolder: FolderItem,
  ) => {
    e.preventDefault();
    e.stopPropagation();

    if (!dragPayload) return;

    if (dragPayload.type === "document") {
      const movingDoc = dragPayload.doc;
      if (movingDoc.folderId !== targetFolder.id) {
        setDocuments((prev) =>
          prev.map((d) =>
            d.id === movingDoc.id ? { ...d, folderId: targetFolder.id } : d,
          ),
        );
        toast.success(
          `Đã di chuyển "${movingDoc.title}" vào thư mục "${targetFolder.name}"`,
        );
      }
    } else if (dragPayload.type === "folder") {
      const movingFolder = dragPayload.folder;
      if (movingFolder.id !== targetFolder.id) {
        setFolders((prev) => {
          const sourceIdx = prev.findIndex((f) => f.id === movingFolder.id);
          const targetIdx = prev.findIndex((f) => f.id === targetFolder.id);
          if (sourceIdx === -1 || targetIdx === -1) return prev;
          const next = [...prev];
          const [removed] = next.splice(sourceIdx, 1);
          next.splice(targetIdx, 0, removed);
          return next;
        });
        toast.success(`Đã sắp xếp lại vị trí thư mục "${movingFolder.name}"`);
      }
    }

    handleDragEnd();
  };

  // Dropping a document onto Root ("Gốc kho") when inside a subfolder
  const handleDropOnRoot = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();

    if (dragPayload?.type === "document") {
      const movingDoc = dragPayload.doc;
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === movingDoc.id ? { ...d, folderId: "root" } : d,
        ),
      );
      toast.success(`Đã di chuyển "${movingDoc.title}" ra Gốc kho tri thức`);
    }

    handleDragEnd();
  };

  // Move document via Modal Dialog
  const handleConfirmMoveDialog = () => {
    if (!docToMove) return;
    const targetFolder = folders.find((f) => f.id === selectedTargetFolderId);
    const targetName = targetFolder ? targetFolder.name : "Gốc kho tri thức";

    setDocuments((prev) =>
      prev.map((d) =>
        d.id === docToMove.id ? { ...d, folderId: selectedTargetFolderId } : d,
      ),
    );
    toast.success(`Đã di chuyển "${docToMove.title}" vào "${targetName}"`);
    setIsMoveDialogOpen(false);
    setDocToMove(null);
  };

  // Full-page window drag & drop event listener (for OS files upload)
  useEffect(() => {
    const handleDragOver = (e: DragEvent) => {
      // Only show upload overlay if dragging files from the OS, not internal items
      if (
        e.dataTransfer?.types.includes("Files") &&
        !e.dataTransfer?.types.includes("application/qnu-type")
      ) {
        e.preventDefault();
        setIsDraggingOver(true);
      }
    };
    const handleDragLeave = (e: DragEvent) => {
      if (e.relatedTarget === null) {
        setIsDraggingOver(false);
      }
    };
    const handleDrop = (e: DragEvent) => {
      if (
        e.dataTransfer?.types.includes("Files") &&
        !e.dataTransfer?.types.includes("application/qnu-type")
      ) {
        e.preventDefault();
        setIsDraggingOver(false);
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
          handleUploadFile(files[0]);
        }
      }
    };

    window.addEventListener("dragover", handleDragOver);
    window.addEventListener("dragleave", handleDragLeave);
    window.addEventListener("drop", handleDrop);

    return () => {
      window.removeEventListener("dragover", handleDragOver);
      window.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("drop", handleDrop);
    };
  }, [handleUploadFile]);

  // Handle Manual Upload from Dialog
  const handleManualUpload = () => {
    if (!selectedFile) return;
    const targetFolder = activeFolderId === "all" ? "root" : activeFolderId;
    handleUploadFile(selectedFile, targetFolder, customTitle);
    setSelectedFile(null);
    setCustomTitle("");
    setIsUploadOpen(false);
  };

  // Direct Publish Action (Approve & Publish 1-click in demo)
  const handlePublishDocument = (docId: string, docTitle: string) => {
    setDocuments((prev) =>
      prev.map((d) =>
        d.id === docId
          ? { ...d, status: "ready" as const, updatedAt: "Vừa duyệt" }
          : d,
      ),
    );
    if (previewDoc?.id === docId) {
      setPreviewDoc((prev) =>
        prev
          ? { ...prev, status: "ready" as const, updatedAt: "Vừa duyệt" }
          : null,
      );
    }
    toast.success(
      `Đã duyệt và phát hành "${docTitle}" thành công! Trợ lý AI đã sẵn sàng phục vụ hỏi đáp.`,
    );
  };

  // Create folder
  const handleCreateFolder = () => {
    if (!newFolderName.trim()) {
      toast.error("Vui lòng nhập tên thư mục!");
      return;
    }
    const newFolder: FolderItem = {
      id: `f_${Date.now()}`,
      name: newFolderName.trim(),
    };
    setFolders((prev) => [...prev, newFolder]);
    setActiveFolderId(newFolder.id);
    setNewFolderName("");
    setIsCreateFolderOpen(false);
    toast.success(`Đã tạo thư mục "${newFolder.name}"`);
  };

  // Delete document
  const handleDelete = (id: string, name: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (previewDoc?.id === id) {
      setIsPreviewOpen(false);
    }
    toast.success(`Đã xóa tệp "${name}"`);
  };

  // Resolve folder name helper
  const getFolderName = (folderId: string) => {
    if (folderId === "root") return "Gốc kho tri thức";
    return folders.find((f) => f.id === folderId)?.name || "Thư mục chung";
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 min-h-screen relative">
      {/* Drag & Drop Anywhere Full-page Glass Overlay */}
      {isDraggingOver && (
        <div className="fixed inset-0 z-50 bg-background/85 backdrop-blur-md flex flex-col items-center justify-center p-8 transition-all animate-in fade-in-0 duration-150">
          <div className="flex flex-col items-center max-w-md text-center p-10 rounded-2xl border-2 border-dashed border-primary bg-primary/5 shadow-xl">
            <div className="size-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 ring-8 ring-primary/5 animate-pulse">
              <Upload className="size-8" />
            </div>
            <h3 className="text-base font-semibold text-foreground">
              Thả tệp vào đây để nạp vào kho lưu trữ
            </h3>
            <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
              Trợ lý AI sẽ tự động đọc hiểu văn bản, trích xuất bảng biểu và
              chuẩn bị sẵn sàng cho quy trình duyệt phát hành.
            </p>
            <div className="mt-4 flex items-center gap-2 text-[11px] text-primary font-medium bg-primary/10 px-3 py-1 rounded-full">
              <span>Hỗ trợ .DOCX, .PDF, .XLSX (Tối đa 60 MB)</span>
            </div>
          </div>
        </div>
      )}

      {/* 1. Page Header with Single Primary CTA */}
      <PageHeader
        eyebrow="Quản lý tài liệu"
        title="Kho tri thức số"
        description="Quản lý thư mục và tệp văn bản phục vụ Trợ lý AI hỏi đáp."
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs font-medium"
              onClick={() => setIsCreateFolderOpen(true)}
            >
              <FolderPlus className="size-3.5" />
              <span>Thư mục mới</span>
            </Button>
            <Button
              size="sm"
              className="h-8 gap-1.5 text-xs font-medium"
              onClick={() => setIsUploadOpen(true)}
            >
              <Upload className="size-3.5" />
              <span>Tải tệp lên</span>
            </Button>
          </div>
        }
      />

      {/* 2. Folder Navigation (Pure Google Drive / File Explorer Model with Drag & Drop) */}
      {activeFolderId === "all" ? (
        /* Root View: Folder Grid */
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs font-semibold text-foreground px-0.5">
            <div className="flex items-center gap-1.5">
              <Folder className="size-4 text-primary" />
              <span>Thư mục</span>
              {dragPayload?.type === "document" && (
                <span className="text-[11px] text-primary font-normal animate-pulse ml-1">
                  (Kéo tệp thả vào thư mục bất kỳ để di chuyển)
                </span>
              )}
              {dragPayload?.type === "folder" && (
                <span className="text-[11px] text-primary font-normal animate-pulse ml-1">
                  (Kéo thả thư mục để sắp xếp lại vị trí)
                </span>
              )}
            </div>
            <span className="text-[11px] text-muted-foreground font-normal">
              {folders.length} thư mục
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {folders.map((f, index) => {
              const count = documents.filter((d) => d.folderId === f.id).length;
              const isDragOver = dragOverFolderId === f.id;
              const isDocDragging = dragPayload?.type === "document";
              const isThisDocFolder =
                isDocDragging && dragPayload.doc.folderId === f.id;
              const isFolderDragging =
                dragPayload?.type === "folder" &&
                dragPayload.folder.id === f.id;

              return (
                <button
                  key={f.id}
                  type="button"
                  draggable={true}
                  onDragStart={(e) => handleFolderDragStart(e, f, index)}
                  onDragEnd={handleDragEnd}
                  onDragOver={(e) => handleFolderDragOver(e, f.id)}
                  onDragLeave={(e) => handleFolderDragLeave(e, f.id)}
                  onDrop={(e) => handleFolderDrop(e, f)}
                  onClick={() => setActiveFolderId(f.id)}
                  className={cn(
                    "relative flex items-center gap-3 p-3 rounded-xl border text-left transition-all cursor-pointer group shadow-2xs select-none",
                    isFolderDragging
                      ? "opacity-40 scale-95 border-dashed border-primary"
                      : isDragOver
                        ? "border-primary ring-2 ring-primary/60 bg-primary/15 scale-[1.04] shadow-md z-10"
                        : isDocDragging && !isThisDocFolder
                          ? "border-dashed border-primary/50 bg-primary/5 hover:border-primary/80 hover:bg-primary/10"
                          : "border-border/70 bg-card hover:bg-muted/40 hover:border-primary/50",
                  )}
                >
                  <div
                    className={cn(
                      "flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                      isDragOver
                        ? "bg-primary text-primary-foreground shadow-xs"
                        : "bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground",
                    )}
                  >
                    {isDragOver ? (
                      <FolderOpen className="size-4.5" />
                    ) : (
                      <Folder className="size-4.5" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                      {f.name}
                    </div>
                    <div className="text-[11px] text-muted-foreground truncate mt-0.5 font-normal">
                      {count} tệp
                    </div>
                  </div>

                  {/* Active Drop Badge */}
                  {isDragOver && (
                    <Badge
                      variant="outline"
                      className="absolute -top-2.5 right-2 bg-primary text-primary-foreground text-[9px] h-4 px-1.5 font-medium border-none shadow-xs animate-in zoom-in-90"
                    >
                      {dragPayload?.type === "document"
                        ? "Thả tệp vào đây"
                        : "Đổi vị trí"}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        /* Inside Folder: Folder Header Banner & Breadcrumb Drop Target */
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-primary/30 bg-primary/5 transition-all">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Breadcrumb Root Button - Drop target to move doc out of folder */}
              <button
                type="button"
                onClick={() => setActiveFolderId("all")}
                onDragOver={(e) => {
                  if (dragPayload?.type === "document") {
                    e.preventDefault();
                    e.stopPropagation();
                    e.dataTransfer.dropEffect = "move";
                    setIsRootDropTargetHovered(true);
                  }
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setIsRootDropTargetHovered(false);
                }}
                onDrop={handleDropOnRoot}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer border select-none",
                  isRootDropTargetHovered
                    ? "ring-2 ring-primary border-primary bg-primary/25 text-primary font-semibold scale-105 shadow-sm"
                    : dragPayload?.type === "document"
                      ? "border-dashed border-primary/70 bg-primary/15 text-primary animate-pulse"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:bg-background/80",
                )}
              >
                <HardDrive className="size-3.5 text-primary" />
                <span>Gốc kho tri thức</span>
              </button>

              <ChevronRight className="size-3.5 text-muted-foreground/60" />

              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-background/90 border border-primary/30 text-xs font-semibold text-foreground shadow-2xs">
                <FolderOpen className="size-3.5 text-primary" />
                <span>{activeFolder?.name}</span>
                <Badge
                  variant="secondary"
                  className="text-[10px] h-4 px-1.5 font-normal ml-1"
                >
                  {filteredDocs.length} tệp
                </Badge>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setActiveFolderId("all")}
              className="h-8 text-xs font-medium gap-1.5 bg-background hover:bg-muted"
            >
              <ArrowLeft className="size-3.5" />
              <span>Tất cả thư mục</span>
            </Button>
          </div>

          {/* Animated Drop-out Zone when user is dragging a file inside a subfolder */}
          {dragPayload?.type === "document" && (
            <button
              type="button"
              onClick={() => setActiveFolderId("all")}
              onDragOver={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.dataTransfer.dropEffect = "move";
                setIsRootDropTargetHovered(true);
              }}
              onDragLeave={() => setIsRootDropTargetHovered(false)}
              onDrop={handleDropOnRoot}
              className={cn(
                "w-full p-3 rounded-xl border-2 border-dashed flex items-center justify-center gap-2 text-xs font-medium transition-all animate-in fade-in-0 duration-150 select-none cursor-pointer",
                isRootDropTargetHovered
                  ? "border-primary bg-primary/25 text-primary ring-2 ring-primary/40 scale-[1.01] shadow-sm font-semibold"
                  : "border-primary/60 bg-primary/10 text-primary hover:bg-primary/15",
              )}
            >
              <HardDrive className="size-4 animate-bounce text-primary" />
              <span>
                Thả vào đây (hoặc nhấn) để đưa văn bản ra ngoài "Gốc kho tri
                thức"
              </span>
            </button>
          )}
        </div>
      )}

      {/* 3. Flat Filter Bar with Natural Search & 3-tier Status Filters */}
      <div className="space-y-3 pt-1">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2 border-b border-border/60">
          {/* Smart Search Bar */}
          <div className="relative w-full sm:w-96">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm theo tên tệp, nội dung văn bản..."
              className="w-full h-8.5 rounded-md border border-border/70 bg-muted/30 pl-8 pr-8 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:bg-background transition-colors"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          {/* Status Filter Dropdown & View Mode */}
          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            {/* Status Selector */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-8.5 text-xs w-[180px]">
                <SelectValue placeholder="Trạng thái" />
              </SelectTrigger>
              <SelectContent className="text-xs">
                <SelectItem value="all">
                  Tất cả trạng thái ({documents.length})
                </SelectItem>
                <SelectItem value="ready">
                  🟢 Đã sẵn sàng ({readyCount})
                </SelectItem>
                <SelectItem value="needs_review">
                  🔵 Chờ duyệt ({reviewCount})
                </SelectItem>
                <SelectItem value="processing">
                  🟡 Đang đọc hiểu ({processingCount})
                </SelectItem>
              </SelectContent>
            </Select>

            <div className="h-4 w-px bg-border/60" />
            <ViewModeToggle value={viewMode} onChange={setViewMode} />
          </div>
        </div>

        {/* Quick File Format Chips (Filter by .docx, .pdf, .xlsx) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {fileTypeChips.map((chip) => {
            const isActive = selectedFileType === chip.value;
            return (
              <button
                key={chip.value}
                type="button"
                onClick={() => setSelectedFileType(chip.value)}
                className={cn(
                  "px-2.5 py-1 rounded-full text-xs transition-colors shrink-0 cursor-pointer font-medium border",
                  isActive
                    ? "bg-primary text-primary-foreground border-primary shadow-2xs"
                    : "bg-muted/40 text-muted-foreground border-border/60 hover:bg-muted hover:text-foreground",
                )}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. Table or Cards View */}
      {filteredDocs.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl bg-card">
          <div className="size-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-3">
            <FileText className="size-5" />
          </div>
          <p className="text-xs font-semibold text-foreground">
            Không tìm thấy tệp tài liệu nào
          </p>
          <p className="text-[11px] text-muted-foreground mt-1 max-w-sm">
            Thử thay đổi từ khóa tìm kiếm hoặc chọn lại thư mục khác để xem tệp.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSearchQuery("");
              setActiveFolderId("all");
              setStatusFilter("all");
              setSelectedFileType("all");
            }}
            className="mt-4 h-8 text-xs font-medium"
          >
            Đặt lại bộ lọc
          </Button>
        </div>
      ) : viewMode === "table" ? (
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden shadow-2xs">
          <Table>
            <TableHeader>
              <TableRow className="h-10 text-xs bg-muted/20">
                <TableHead className="w-[450px]">Tên tệp / Văn bản</TableHead>
                <TableHead className="w-[120px]">Định dạng</TableHead>
                <TableHead className="w-[110px]">Kích thước</TableHead>
                <TableHead className="w-[100px]">Phiên bản</TableHead>
                <TableHead className="w-[160px]">Trạng thái AI</TableHead>
                <TableHead className="w-[120px]">Cập nhật</TableHead>
                <TableHead className="w-[50px] text-right" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDocs.map((doc) => (
                <TableRow
                  key={doc.id}
                  draggable={true}
                  onDragStart={(e) => handleDocDragStart(e, doc)}
                  onDragEnd={handleDragEnd}
                  className={cn(
                    "h-11 text-xs group hover:bg-muted/40 transition-colors select-none",
                    dragPayload?.type === "document" &&
                      dragPayload.doc.id === doc.id
                      ? "opacity-40 bg-primary/10 border-dashed border-primary"
                      : "cursor-grab active:cursor-grabbing",
                  )}
                >
                  {/* File Name & Title */}
                  <TableCell className="py-2">
                    <div className="flex items-center gap-2">
                      <GripVertical className="size-3.5 text-muted-foreground/30 group-hover:text-muted-foreground/80 shrink-0 transition-colors" />
                      <DocumentTypeIcon fileName={doc.fileName} />
                      <div className="min-w-0">
                        <button
                          type="button"
                          onClick={() => handleOpenPreview(doc)}
                          className="font-semibold text-foreground hover:text-primary transition-colors block truncate max-w-[400px] text-left cursor-pointer"
                        >
                          {doc.title}
                        </button>
                        <span className="text-[11px] text-muted-foreground truncate block font-mono">
                          {doc.fileName}
                        </span>
                      </div>
                    </div>
                  </TableCell>

                  {/* File Format */}
                  <TableCell className="text-muted-foreground text-[11px]">
                    <span className="uppercase font-mono font-semibold">
                      {doc.fileType}
                    </span>
                  </TableCell>

                  {/* Size */}
                  <TableCell className="text-muted-foreground text-[11px] font-mono">
                    {doc.size}
                  </TableCell>

                  {/* Revision */}
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className="text-[10px] h-4 px-1.5 font-mono"
                    >
                      v{doc.revision}
                    </Badge>
                  </TableCell>

                  {/* 3-tier Human-friendly AI Status */}
                  <TableCell>
                    {doc.status === "ready" ? (
                      <Badge
                        variant="outline"
                        className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] gap-1 font-medium"
                      >
                        <CheckCircle2 className="size-2.5" />
                        <span>Đã sẵn sàng hỏi đáp</span>
                      </Badge>
                    ) : doc.status === "needs_review" ? (
                      <Badge
                        variant="outline"
                        className="bg-sky-500/10 text-sky-600 border-sky-500/20 text-[10px] gap-1 font-medium"
                      >
                        <FileCheck className="size-2.5" />
                        <span>Chờ duyệt phát hành</span>
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="bg-amber-500/10 text-amber-600 border-amber-500/20 text-[10px] gap-1 font-medium animate-pulse"
                      >
                        <Loader2 className="size-2.5 animate-spin" />
                        <span>Đang đọc hiểu văn bản...</span>
                      </Badge>
                    )}
                  </TableCell>

                  {/* Updated at */}
                  <TableCell className="text-muted-foreground text-[11px]">
                    {doc.updatedAt}
                  </TableCell>

                  {/* Single ⋯ Menu */}
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="size-7 p-0 text-muted-foreground hover:text-foreground opacity-60 group-hover:opacity-100"
                        >
                          <MoreHorizontal className="size-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-52 text-xs">
                        <DropdownMenuItem
                          onClick={() => handleOpenPreview(doc)}
                          className="gap-2 cursor-pointer"
                        >
                          <Sparkles className="size-3.5 text-primary" />
                          <span>Xem nhanh & Tóm tắt AI</span>
                        </DropdownMenuItem>

                        <DropdownMenuItem
                          onClick={() => {
                            setDocToMove(doc);
                            setSelectedTargetFolderId(doc.folderId || "root");
                            setIsMoveDialogOpen(true);
                          }}
                          className="gap-2 cursor-pointer"
                        >
                          <FolderInput className="size-3.5 text-primary" />
                          <span>Di chuyển vào thư mục...</span>
                        </DropdownMenuItem>

                        {doc.status === "needs_review" && (
                          <DropdownMenuItem
                            onClick={() =>
                              handlePublishDocument(doc.id, doc.title)
                            }
                            className="gap-2 text-sky-600 font-medium cursor-pointer"
                          >
                            <Check className="size-3.5" />
                            <span>Duyệt & Phát hành ngay</span>
                          </DropdownMenuItem>
                        )}

                        {doc.status === "ready" && (
                          <DropdownMenuItem
                            onClick={() => navigate({ to: "/chat" })}
                            className="gap-2 cursor-pointer"
                          >
                            <Bot className="size-3.5 text-primary" />
                            <span>Hỏi đáp với Trợ lý AI</span>
                          </DropdownMenuItem>
                        )}

                        <DropdownMenuItem asChild>
                          <Link
                            to="/knowledge/$sourceId"
                            params={{ sourceId: doc.id }}
                            className="gap-2 cursor-pointer font-medium text-primary"
                          >
                            <FileText className="size-3.5" />
                            <span>Mở Studio soát văn bản (50:50)</span>
                          </Link>
                        </DropdownMenuItem>

                        <DropdownMenuItem
                          onClick={() =>
                            toast.success(`Đang tải tệp ${doc.fileName}...`)
                          }
                          className="gap-2 cursor-pointer"
                        >
                          <Download className="size-3.5" />
                          <span>Tải tệp gốc</span>
                        </DropdownMenuItem>

                        <DropdownMenuItem
                          onClick={() =>
                            toast.info(
                              `Đang cập nhật lại dữ liệu cho ${doc.title}`,
                            )
                          }
                          className="gap-2 cursor-pointer"
                        >
                          <RefreshCw className="size-3.5" />
                          <span>Cập nhật dữ liệu AI</span>
                        </DropdownMenuItem>

                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => handleDelete(doc.id, doc.title)}
                          className="gap-2 text-destructive cursor-pointer"
                        >
                          <Trash2 className="size-3.5" />
                          <span>Xóa tệp</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        /* Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocs.map((doc) => (
            <Card
              key={doc.id}
              draggable={true}
              onDragStart={(e) => handleDocDragStart(e, doc)}
              onDragEnd={handleDragEnd}
              className={cn(
                "h-full flex flex-col justify-between hover:border-primary/60 transition-all shadow-2xs group select-none",
                dragPayload?.type === "document" &&
                  dragPayload.doc.id === doc.id
                  ? "opacity-40 scale-95 border-dashed border-primary ring-2 ring-primary/20"
                  : "cursor-grab active:cursor-grabbing",
              )}
            >
              <CardHeader className="p-3.5 pb-2 flex flex-row items-start justify-between space-y-0">
                <div className="flex items-start gap-2.5 min-w-0 flex-1 pr-1">
                  <GripVertical className="size-3.5 text-muted-foreground/30 group-hover:text-muted-foreground/80 shrink-0 mt-0.5 transition-colors" />
                  <DocumentTypeIcon
                    fileName={doc.fileName}
                    className="size-5 shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <button
                      type="button"
                      title={doc.title}
                      onClick={() => handleOpenPreview(doc)}
                      className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors truncate block w-full text-left cursor-pointer"
                    >
                      {doc.title}
                    </button>
                    <p
                      title={doc.fileName}
                      className="text-[11px] text-muted-foreground mt-0.5 truncate font-mono"
                    >
                      {doc.fileName}
                    </p>
                  </div>
                </div>

                {/* 1 Menu ⋯ on Card */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="size-7 p-0 shrink-0 text-muted-foreground hover:text-foreground -mr-1"
                    >
                      <MoreHorizontal className="size-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-52 text-xs">
                    <DropdownMenuItem
                      onClick={() => handleOpenPreview(doc)}
                      className="gap-2 cursor-pointer"
                    >
                      <Sparkles className="size-3.5 text-primary" />
                      <span>Xem nhanh & Tóm tắt AI</span>
                    </DropdownMenuItem>

                    <DropdownMenuItem
                      onClick={() => {
                        setDocToMove(doc);
                        setSelectedTargetFolderId(doc.folderId || "root");
                        setIsMoveDialogOpen(true);
                      }}
                      className="gap-2 cursor-pointer"
                    >
                      <FolderInput className="size-3.5 text-primary" />
                      <span>Di chuyển vào thư mục...</span>
                    </DropdownMenuItem>

                    {doc.status === "needs_review" && (
                      <DropdownMenuItem
                        onClick={() => handlePublishDocument(doc.id, doc.title)}
                        className="gap-2 text-sky-600 font-medium cursor-pointer"
                      >
                        <Check className="size-3.5" />
                        <span>Duyệt & Phát hành ngay</span>
                      </DropdownMenuItem>
                    )}

                    {doc.status === "ready" && (
                      <DropdownMenuItem
                        onClick={() => navigate({ to: "/chat" })}
                        className="gap-2 cursor-pointer"
                      >
                        <Bot className="size-3.5 text-primary" />
                        <span>Hỏi đáp với Trợ lý AI</span>
                      </DropdownMenuItem>
                    )}

                    <DropdownMenuItem asChild>
                      <Link
                        to="/knowledge/$sourceId"
                        params={{ sourceId: doc.id }}
                        className="gap-2 cursor-pointer font-medium text-primary"
                      >
                        <FileText className="size-3.5" />
                        <span>Mở Studio soát văn bản (50:50)</span>
                      </Link>
                    </DropdownMenuItem>

                    <DropdownMenuItem
                      onClick={() =>
                        toast.success(`Đang tải tệp ${doc.fileName}...`)
                      }
                      className="gap-2 cursor-pointer"
                    >
                      <Download className="size-3.5" />
                      <span>Tải tệp gốc</span>
                    </DropdownMenuItem>

                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleDelete(doc.id, doc.title)}
                      className="text-destructive cursor-pointer gap-2"
                    >
                      <Trash2 className="size-3.5" />
                      <span>Xóa tệp</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>

              <CardContent className="px-3.5 pt-0 pb-2.5">
                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
                  <span className="uppercase font-semibold text-foreground/80">
                    {doc.fileType}
                  </span>
                  <span>·</span>
                  <span>{doc.size}</span>
                  <span>·</span>
                  <span>v{doc.revision}</span>
                  <span>·</span>
                  <span>{doc.updatedAt}</span>
                </div>
              </CardContent>

              <CardFooter className="px-3.5 py-2.5 border-t border-border/40 text-[11px] text-muted-foreground flex items-center justify-between">
                {doc.status === "ready" ? (
                  <Badge
                    variant="outline"
                    className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] h-4 px-1 gap-1 font-medium"
                  >
                    <CheckCircle2 className="size-2.5" />
                    <span>Sẵn sàng hỏi đáp</span>
                  </Badge>
                ) : doc.status === "needs_review" ? (
                  <Badge
                    variant="outline"
                    className="bg-sky-500/10 text-sky-600 border-sky-500/20 text-[10px] h-4 px-1 gap-1 font-medium"
                  >
                    <FileCheck className="size-2.5" />
                    <span>Chờ duyệt</span>
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="bg-amber-500/10 text-amber-600 border-amber-500/20 text-[10px] h-4 px-1 gap-1 font-medium"
                  >
                    <Loader2 className="size-2.5 animate-spin" />
                    <span>Đang đọc hiểu...</span>
                  </Badge>
                )}

                <button
                  type="button"
                  onClick={() => handleOpenPreview(doc)}
                  className="text-primary font-medium hover:underline text-xs flex items-center gap-0.5 cursor-pointer"
                >
                  <span>Xem nhanh</span>
                  <ChevronRight className="size-3" />
                </button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* 5. Comprehensive Quick Preview & AI Summary Drawer (Slide-over Sheet) */}
      <Sheet open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <SheetContent
          side="right"
          className="w-[min(100vw-1rem,580px)] sm:max-w-xl p-0 flex flex-col"
        >
          {previewDoc && (
            <>
              {/* Drawer Header */}
              <SheetHeader className="p-4 border-b border-border/60 bg-muted/20">
                <div className="flex items-start gap-3 pr-6">
                  <DocumentTypeIcon
                    fileName={previewDoc.fileName}
                    className="size-7 mt-0.5 shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <SheetTitle className="text-sm font-semibold text-foreground leading-snug">
                      {previewDoc.title}
                    </SheetTitle>

                    <SheetDescription className="text-xs text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
                      <span className="font-mono uppercase font-semibold">
                        {previewDoc.fileType}
                      </span>
                      <span>·</span>
                      <span>{previewDoc.size}</span>
                      <span>·</span>
                      <span>v{previewDoc.revision}</span>
                      <span>·</span>
                      <span>{previewDoc.updatedAt}</span>
                      <span>·</span>
                      {previewDoc.status === "ready" ? (
                        <span className="text-emerald-600 font-medium">
                          ✓ Đã sẵn sàng hỏi đáp
                        </span>
                      ) : previewDoc.status === "needs_review" ? (
                        <span className="text-sky-600 font-medium">
                          ● Chờ duyệt phát hành
                        </span>
                      ) : (
                        <span className="text-amber-600 font-medium">
                          ◐ Đang đọc hiểu văn bản
                        </span>
                      )}
                    </SheetDescription>
                  </div>
                </div>
              </SheetHeader>

              {/* Drawer Content Tabs */}
              <Tabs
                value={activeDrawerTab}
                onValueChange={setActiveDrawerTab}
                className="flex-1 flex flex-col min-h-0"
              >
                <div className="px-5 border-b border-border/60 bg-card">
                  <TabsList className="h-9 border-none p-0 gap-4">
                    <TabsTrigger
                      value="summary"
                      className="text-xs gap-1.5 h-9 data-[state=active]:border-b-2 data-[state=active]:border-primary"
                    >
                      <Sparkles className="size-3" />
                      <span>Tóm tắt AI</span>
                    </TabsTrigger>
                    <TabsTrigger
                      value="content"
                      className="text-xs gap-1.5 h-9 data-[state=active]:border-b-2 data-[state=active]:border-primary"
                    >
                      <FileText className="size-3" />
                      <span>Nội dung văn bản</span>
                    </TabsTrigger>
                    <TabsTrigger
                      value="lifecycle"
                      className="text-xs gap-1.5 h-9 data-[state=active]:border-b-2 data-[state=active]:border-primary"
                    >
                      <History className="size-3" />
                      <span>Tiến trình & Phiên bản</span>
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="flex-1 overflow-y-auto p-5">
                  {/* Tab 1: AI Summary & Highlights */}
                  <TabsContent value="summary" className="mt-0 space-y-4">
                    <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-primary font-semibold text-xs">
                          <Sparkles className="size-4" />
                          <span>Tóm tắt từ Trí tuệ nhân tạo QNU AI</span>
                        </div>
                        <Badge
                          variant="outline"
                          className="text-[10px] border-primary/30 text-primary bg-primary/10"
                        >
                          Độ tin cậy 100%
                        </Badge>
                      </div>
                      <p className="text-xs text-foreground leading-relaxed">
                        {previewDoc.summary}
                      </p>

                      <div className="space-y-1.5 pt-2 border-t border-primary/20">
                        <span className="text-[11px] font-semibold text-foreground">
                          Các điểm cốt lõi cần lưu ý:
                        </span>
                        <ul className="space-y-1 text-xs text-muted-foreground list-disc pl-4">
                          {previewDoc.aiKeypoints.map((point) => (
                            <li key={point} className="leading-snug">
                              {point}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Pure File Metadata boxes (No units/departments!) */}
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg border border-border/60 bg-card space-y-1">
                        <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
                          <Folder className="size-3.5" />
                          <span>Thư mục lưu trữ</span>
                        </div>
                        <p className="font-semibold text-foreground truncate">
                          {getFolderName(previewDoc.folderId)}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg border border-border/60 bg-card space-y-1">
                        <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
                          <HardDrive className="size-3.5" />
                          <span>Dung lượng tệp</span>
                        </div>
                        <p className="font-semibold text-foreground">
                          {previewDoc.size} · v{previewDoc.revision}
                        </p>
                      </div>
                    </div>
                  </TabsContent>

                  {/* Tab 2: Document Content */}
                  <TabsContent value="content" className="mt-0 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                        <FileText className="size-3.5 text-muted-foreground" />
                        <span>Trích đoạn nội dung tệp</span>
                      </span>
                      <span className="text-[11px] text-muted-foreground font-mono">
                        {previewDoc.fileName}
                      </span>
                    </div>

                    <div className="p-5 rounded-xl border border-border/60 bg-card text-xs text-foreground/90 font-serif leading-relaxed shadow-2xs whitespace-pre-wrap">
                      {previewDoc.sampleContent}
                    </div>
                  </TabsContent>

                  {/* Tab 3: Lifecycle Timeline */}
                  <TabsContent value="lifecycle" className="mt-0 space-y-3">
                    <div className="p-4 rounded-xl border border-border/60 bg-card space-y-3 text-xs">
                      <span className="font-semibold text-foreground block">
                        Dòng đời tài liệu chuẩn Backend V1
                      </span>

                      <div className="space-y-3 pl-2 border-l-2 border-primary/30">
                        {/* Step 1 */}
                        <div className="relative pl-4">
                          <div className="absolute -left-[21px] top-0.5 size-3 rounded-full bg-primary" />
                          <div className="font-semibold text-foreground">
                            1. Nạp tệp & Bóc tách OCR
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            Hoàn tất · Tệp gốc giữ nguyên mã hash SHA-256
                          </p>
                        </div>

                        {/* Step 2 */}
                        <div className="relative pl-4">
                          <div className="absolute -left-[21px] top-0.5 size-3 rounded-full bg-primary" />
                          <div className="font-semibold text-foreground">
                            2. Chuẩn bị nội dung tự động (Auto Mode)
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            Hoàn tất · Bản nháp biên soạn sẵn sàng
                          </p>
                        </div>

                        {/* Step 3 */}
                        <div className="relative pl-4">
                          <div
                            className={cn(
                              "absolute -left-[21px] top-0.5 size-3 rounded-full",
                              previewDoc.status === "ready"
                                ? "bg-emerald-500"
                                : "bg-sky-500 animate-pulse",
                            )}
                          />
                          <div className="font-semibold text-foreground">
                            3. Duyệt & Phát hành vào chỉ mục AI
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {previewDoc.status === "ready"
                              ? "✓ Đã phát hành chính thức · Sẵn sàng hỏi đáp"
                              : "Đang chờ duyệt trước khi đưa vào chỉ mục"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                </div>
              </Tabs>

              {/* Drawer Action Footer */}
              <SheetFooter className="p-4 border-t border-border/60 bg-muted/10 gap-2.5 sm:gap-2.5">
                {previewDoc.status === "needs_review" ? (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      asChild
                      className="h-9 px-3 text-xs font-medium"
                    >
                      <Link
                        to="/knowledge/$sourceId"
                        params={{ sourceId: previewDoc.id }}
                        className="gap-1.5"
                      >
                        <FileText className="size-3.5" />
                        <span>Mở Studio soát</span>
                      </Link>
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={() =>
                        handlePublishDocument(previewDoc.id, previewDoc.title)
                      }
                      className="h-9 px-4 text-xs font-medium gap-1.5 bg-sky-600 hover:bg-sky-700 text-white"
                    >
                      <Check className="size-3.5" />
                      <span>Duyệt & Phát hành ngay</span>
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      asChild
                      className="h-9 px-3 text-xs font-medium"
                    >
                      <Link
                        to="/knowledge/$sourceId"
                        params={{ sourceId: previewDoc.id }}
                        className="gap-1.5"
                      >
                        <FileText className="size-3.5" />
                        <span>Mở Studio soát</span>
                      </Link>
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => {
                        setIsPreviewOpen(false);
                        navigate({ to: "/chat" });
                      }}
                      className="h-9 px-4 text-xs font-medium gap-1.5"
                    >
                      <Bot className="size-3.5" />
                      <span>Hỏi đáp cùng AI</span>
                    </Button>
                  </>
                )}
              </SheetFooter>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* 6. Pure File Upload Modal (No Department fields!) */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Tải tệp lên kho lưu trữ
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Tệp sẽ được nạp trực tiếp vào{" "}
              <span className="font-semibold text-foreground">
                {activeFolder
                  ? `thư mục "${activeFolder.name}"`
                  : "Gốc kho tri thức"}
              </span>
              . Trợ lý AI sẽ tự động đọc hiểu và chuẩn bị sẵn sàng cho quy trình
              duyệt phát hành.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Custom Document Title */}
            <Field className="gap-2">
              <FieldLabel
                htmlFor={uploadTitleInputId}
                className="text-xs font-semibold text-foreground"
              >
                Tên văn bản hiển thị (Tùy chọn)
              </FieldLabel>
              <Input
                id={uploadTitleInputId}
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="VD: Quy chế đào tạo tín chỉ năm học 2026..."
                className="h-9 text-xs"
              />
            </Field>

            {/* Dropzone */}
            <label
              htmlFor="manual-file-input"
              className="flex flex-col items-center justify-center border-2 border-dashed border-border/80 hover:border-primary/60 rounded-xl p-6 bg-muted/20 hover:bg-muted/40 cursor-pointer transition-colors text-center"
            >
              <div className="size-10 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-2.5">
                <Upload className="size-5" />
              </div>
              <p className="text-xs font-medium text-foreground">
                Kéo thả tệp vào đây, hoặc nhấn để chọn
              </p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Hỗ trợ .DOCX, .PDF, .XLSX (Tối đa 60 MB/tệp)
              </p>
              <input
                id="manual-file-input"
                type="file"
                accept=".docx,.pdf,.xlsx,.csv"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
                }}
              />
            </label>

            {selectedFile && (
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/60 bg-card text-xs">
                <div className="flex items-center gap-2 truncate">
                  <DocumentTypeIcon fileName={selectedFile.name} />
                  <span className="truncate font-medium">
                    {selectedFile.name}
                  </span>
                </div>
                <span className="text-[11px] text-muted-foreground shrink-0 ml-2 font-mono">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </span>
              </div>
            )}
          </div>

          <DialogFooter className="gap-3 sm:gap-3 pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedFile(null);
                setCustomTitle("");
                setIsUploadOpen(false);
              }}
              className="h-9 px-4 text-xs font-medium"
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!selectedFile}
              onClick={handleManualUpload}
              className="h-9 px-4 text-xs font-medium gap-1.5"
            >
              <Upload className="size-3.5" />
              <span>Bắt đầu nạp tệp</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 7. Pure Create Folder Dialog (No Department field!) */}
      <Dialog open={isCreateFolderOpen} onOpenChange={setIsCreateFolderOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Tạo thư mục mới
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Tạo thư mục mới để gom nhóm và quản lý các tệp tài liệu liên quan.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <Field className="gap-2">
              <FieldLabel
                htmlFor={folderNameInputId}
                className="text-xs font-semibold text-foreground flex items-center gap-1"
              >
                <span>Tên thư mục</span>
                <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id={folderNameInputId}
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="VD: Đề thi, Tài liệu hướng dẫn, Biểu mẫu..."
                className="h-9 text-xs"
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
              />
            </Field>
          </div>

          <DialogFooter className="gap-3 sm:gap-3 pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsCreateFolderOpen(false)}
              className="h-9 px-4 text-xs font-medium"
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!newFolderName.trim()}
              onClick={handleCreateFolder}
              className="h-9 px-4 text-xs font-medium gap-1.5"
            >
              <Check className="size-3.5" />
              <span>Tạo thư mục</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 8. Move Document Dialog (Accessible Modal alternative to Drag & Drop) */}
      <Dialog open={isMoveDialogOpen} onOpenChange={setIsMoveDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <FolderInput className="size-4.5 text-primary" />
              <span>Di chuyển văn bản</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              {docToMove ? (
                <>
                  Chọn vị trí mới cho tệp{" "}
                  <span className="font-semibold text-foreground">
                    "{docToMove.title}"
                  </span>
                </>
              ) : (
                "Chọn thư mục đích để di chuyển tài liệu."
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="p-3 rounded-lg border border-border/60 bg-muted/20 text-xs flex items-center justify-between">
              <span className="text-muted-foreground">Vị trí hiện tại:</span>
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Folder className="size-3.5 text-primary" />
                {docToMove ? getFolderName(docToMove.folderId) : "Kho tri thức"}
              </span>
            </div>

            <Field className="gap-2">
              <FieldLabel
                htmlFor={moveFolderSelectId}
                className="text-xs font-semibold text-foreground"
              >
                Chọn thư mục chuyển đến
              </FieldLabel>
              <Select
                value={selectedTargetFolderId}
                onValueChange={setSelectedTargetFolderId}
              >
                <SelectTrigger id={moveFolderSelectId} className="h-9 text-xs">
                  <SelectValue placeholder="Chọn thư mục" />
                </SelectTrigger>
                <SelectContent className="text-xs">
                  <SelectItem value="root">
                    🏠 Gốc kho tri thức (Không thuộc thư mục con)
                  </SelectItem>
                  {folders.map((f) => (
                    <SelectItem key={f.id} value={f.id}>
                      📁 {f.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          <DialogFooter className="gap-3 sm:gap-3 pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setIsMoveDialogOpen(false);
                setDocToMove(null);
              }}
              className="h-9 px-4 text-xs font-medium"
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleConfirmMoveDialog}
              className="h-9 px-4 text-xs font-medium gap-1.5"
            >
              <Check className="size-3.5" />
              <span>Xác nhận di chuyển</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

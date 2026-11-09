import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Columns2,
  Copy,
  Download,
  Edit3,
  FileCode,
  FileDown,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Save,
  Trash2,
  Upload,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { DocumentTypeIcon } from "@/components/admin/document-file-icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/knowledge/$sourceId")({
  component: SourceStudioPage,
});

export type DocumentSection = {
  id: string;
  type: "meta" | "heading" | "paragraph" | "table";
  headingLevel?: number;
  content: string;
  editedContent?: string;
  isEdited?: boolean;
  tableData?: {
    headers: string[];
    rows: { stt: string; major: string; tuition: string; note?: string }[];
  };
};

const initialSections: DocumentSection[] = [
  {
    id: "sec_meta",
    type: "meta",
    content:
      "Phiên bản dữ liệu: 15/10/2026. Nguồn ưu tiên: Cổng thông tin chính thức qnu.edu.vn.",
  },
  {
    id: "sec_scope",
    type: "paragraph",
    content:
      "Phạm vi dữ liệu: nhận diện, lịch sử, triết lý giáo dục, sứ mạng, tầm nhìn, lãnh đạo, cơ cấu tổ chức, đào tạo, tuyển sinh năm 2026, nghiên cứu khoa học, kiểm định, hoạt động sinh viên và thông tin liên hệ. Các số liệu theo năm học hoặc thời điểm công bố được nêu cụ thể; không suy diễn khi nguồn không có số liệu cố định.",
  },
  {
    id: "sec_h1",
    type: "heading",
    headingLevel: 2,
    content: "1. Thông tin nhận diện Trường Đại học Quy Nhơn",
  },
  {
    id: "sec_p1",
    type: "paragraph",
    content:
      "Trường Đại học Quy Nhơn có tên tiếng Anh là Quy Nhon University, viết tắt là QNU. Trường Đại học Quy Nhơn là cơ sở giáo dục đại học công lập, trực thuộc Bộ Giáo dục và Đào tạo. Trụ sở chính của Trường Đại học Quy Nhơn theo công khai năm học 2026–2027 đặt tại số 170 đường An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai. Cổng thông tin chính thức của trường là https://www.qnu.edu.vn. [S1]",
  },
  {
    id: "sec_p2",
    type: "paragraph",
    content:
      "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn sử dụng trong tuyển sinh đại học năm 2026 là DQN. Website thông tin tuyển sinh của Trường Đại học Quy Nhơn là https://tuyensinh.qnu.edu.vn. Mã DQN là thông tin tuyển sinh, khác với tên viết tắt QNU dùng để nhận diện trường trong tiếng Anh và truyền thông. [S0]",
  },
  {
    id: "sec_h2",
    type: "heading",
    headingLevel: 2,
    content: "2. Lịch sử hình thành và các mốc pháp lý",
  },
  {
    id: "sec_p3",
    type: "paragraph",
    content:
      "Ngày 21/12/1977, Bộ trưởng Bộ Giáo dục ban hành Quyết định số 1842/QĐ thành lập Cơ sở Đại học Sư phạm Quy Nhơn. Đây là mốc khởi đầu trong lịch sử hình thành Trường Đại học Quy Nhơn và là cơ sở để trường tính số năm truyền thống. Vì vậy, khi được hỏi Trường Đại học Quy Nhơn thành lập năm nào, mốc trả lời phù hợp theo lịch sử nhà trường là năm 1977, cụ thể ngày 21 tháng 12 năm 1977. [S1] [S2]",
  },
  {
    id: "sec_p4",
    type: "paragraph",
    content:
      "Ngày 13/7/1981, Hội đồng Bộ trưởng ban hành Quyết định số 02/HĐBT thành lập Trường Đại học Sư phạm Quy Nhơn. Mốc 13 tháng 7 năm 1981 đánh dấu việc thành lập trường đại học toàn diện trên nền tảng cơ sở đã mở từ năm 1977. Hai mốc năm 1977 và năm 1981 phản ánh hai sự kiện pháp lý khác nhau, không nên dùng thay thế cho nhau. [S2]",
  },
  {
    id: "sec_p5",
    type: "paragraph",
    content:
      "Ngày 30/10/2003, Thủ tướng Chính phủ ban hành Quyết định số 221/2003/QĐ-TTg đổi tên Trường Đại học Sư phạm Quy Nhơn thành Trường Đại học Quy Nhơn. Tên gọi Trường Đại học Quy Nhơn gắn với định hướng phát triển đa ngành, đa lĩnh vực thay cho mô hình đào tạo chủ yếu về sư phạm trước đó. Ngày 30 tháng 10 năm 2003 là ngày đổi tên, không phải mốc thành lập ban đầu của trường. [S1] [S2]",
  },
  {
    id: "sec_h3",
    type: "heading",
    headingLevel: 2,
    content: "3. Định mức thu học phí theo tín chỉ (Năm học 2026 - 2027)",
  },
  {
    id: "sec_t1",
    type: "table",
    content:
      "Căn cứ Nghị định số 81/2021/NĐ-CP và Nghị định số 97/2023/NĐ-CP của Chính phủ, định mức thu học phí đối với các ngành đào tạo chuẩn áp dụng theo Bảng 1:",
    tableData: {
      headers: ["STT", "Khối ngành đào tạo", "Định mức thu (VNĐ/tín chỉ)"],
      rows: [
        {
          stt: "1",
          major: "Khối ngành Kỹ thuật & Công nghệ thông tin",
          tuition: "550.000 VNĐ",
        },
        {
          stt: "2",
          major: "Khối ngành Kinh tế & Quản trị kinh doanh",
          tuition: "480.000 VNĐ",
        },
        {
          stt: "3",
          major: "Khối ngành Sư phạm & Đào tạo giáo viên",
          tuition: "Miễn 100% (NĐ 116)",
        },
      ],
    },
  },
];

function SourceStudioPage() {
  const navigate = useNavigate();

  // Document Content & Editing State
  const [sections, setSections] = useState<DocumentSection[]>(initialSections);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftContent, setDraftContent] = useState("");

  // Left Viewer Controls
  const [docFormat, setDocFormat] = useState<"docx" | "pdf">("docx");
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Right Tabs
  const [activeTab, setActiveTab] = useState<"text" | "markdown" | "json">(
    "text",
  );

  const hasUnsaved = sections.some((s) => s.isEdited);

  const startEdit = (sec: DocumentSection) => {
    setEditingId(sec.id);
    setDraftContent(sec.editedContent ?? sec.content);
  };

  const saveEdit = (id: string) => {
    setSections((prev) =>
      prev.map((s) =>
        s.id === id
          ? {
              ...s,
              editedContent: draftContent,
              isEdited: draftContent !== s.content,
            }
          : s,
      ),
    );
    setEditingId(null);
    toast.success("Đã ghi nhận thay đổi đoạn văn bản!");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraftContent("");
  };

  const handleSaveAll = () => {
    setSections((prev) =>
      prev.map((s) => ({
        ...s,
        content: s.editedContent ?? s.content,
        isEdited: false,
        editedContent: undefined,
      })),
    );
    toast.success("Đã lưu tất cả các chỉnh sửa vào kho tri thức!");
  };

  const handlePublish = () => {
    toast.success("🎉 Đã duyệt và phát hành văn bản thành công vào Trợ lý AI!");
    navigate({ to: "/knowledge" });
  };

  // Generate markdown representation
  const markdownContent = `# DỮ LIỆU TRI THỨC VỀ TRƯỜNG ĐẠI HỌC QUY NHƠN
*Phiên bản dữ liệu: 15/10/2026. Nguồn ưu tiên: Cổng thông tin chính thức qnu.edu.vn.*

Phạm vi dữ liệu: nhận diện, lịch sử, triết lý giáo dục, sứ mạng, tầm nhìn, lãnh đạo, cơ cấu tổ chức, đào tạo, tuyển sinh năm 2026.

## 1. Thông tin nhận diện Trường Đại học Quy Nhơn
Trường Đại học Quy Nhơn có tên tiếng Anh là Quy Nhon University, viết tắt là QNU. Trường Đại học Quy Nhơn là cơ sở giáo dục đại học công lập, trực thuộc Bộ Giáo dục và Đào tạo. Trụ sở chính: số 170 đường An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai.

Mã cơ sở đào tạo sử dụng trong tuyển sinh đại học năm 2026 là DQN. Website: https://tuyensinh.qnu.edu.vn.

## 2. Lịch sử hình thành và các mốc pháp lý
- **21/12/1977**: Thành lập Cơ sở Đại học Sư phạm Quy Nhơn theo QĐ 1842/QĐ của Bộ Giáo dục.
- **13/7/1981**: Thành lập Trường Đại học Sư phạm Quy Nhơn theo QĐ 02/HĐBT của Hội đồng Bộ trưởng.
- **30/10/2003**: Đổi tên thành Trường Đại học Quy Nhơn theo QĐ 221/2003/QĐ-TTg của Thủ tướng Chính phủ.

## 3. Định mức thu học phí theo tín chỉ (Năm học 2026 - 2027)
| STT | Khối ngành đào tạo | Định mức thu (VNĐ/tín chỉ) |
|---|---|---|
| 1 | Khối ngành Kỹ thuật & CNTT | 550.000 VNĐ |
| 2 | Khối ngành Kinh tế & Quản trị kinh doanh | 480.000 VNĐ |
| 3 | Khối ngành Sư phạm & Đào tạo giáo viên | Miễn 100% (Nghị định 116) |`;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-background select-none overflow-x-hidden">
      {/* ========================================================================= */}
      {/* 1. MASTER HEADER: Clean, Focused, Pure 50:50 Document Studio              */}
      {/* ========================================================================= */}
      <header className="flex h-14 items-center justify-between border-b border-border/60 bg-card px-4 gap-4 shrink-0">
        {/* Left: Back & Document Metadata */}
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

          <div className="flex items-center gap-2.5 min-w-0">
            <DocumentTypeIcon
              fileName="Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx"
              className="size-5 shrink-0"
            />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-xs font-semibold text-foreground max-w-[200px] sm:max-w-xs md:max-w-sm block">
                  Dữ liệu tri thức về Trường Đại học Quy Nhơn 2026
                </span>
                <Badge
                  variant="secondary"
                  className="text-[10px] h-4 px-1.5 font-mono shrink-0"
                >
                  v1
                </Badge>
                <Badge
                  variant="outline"
                  className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] h-4 px-1.5 hidden md:inline-flex shrink-0"
                >
                  Đã bóc tách
                </Badge>
              </div>
              <p className="text-[10px] text-muted-foreground truncate font-mono">
                Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx · 3 trang
              </p>
            </div>
          </div>
        </div>

        {/* Center: Mode Indicator Badge */}
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-medium shrink-0">
          <Columns2 className="size-3.5" />
          <span>Không gian Soát văn bản (Đối chiếu song song 50:50)</span>
        </div>

        {/* Right: Actions & Single ⋯ Menu */}
        <div className="flex items-center gap-2 shrink-0">
          {hasUnsaved && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveAll}
              className="h-8 gap-1.5 text-xs font-medium border-amber-500/40 bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 transition-all shadow-2xs"
            >
              <Save className="size-3.5" />
              <span>Lưu thay đổi</span>
            </Button>
          )}

          <Button
            size="sm"
            onClick={handlePublish}
            className="h-8 gap-1.5 text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 shadow-2xs cursor-pointer"
          >
            <CheckCircle2 className="size-3.5" />
            <span>Duyệt & Phát hành</span>
          </Button>

          {/* Single ⋯ Menu for all secondary & file actions */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="size-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 text-xs">
              <DropdownMenuItem
                onClick={() =>
                  toast.success("Đang tải tệp Word gốc (.docx)...")
                }
                className="gap-2 cursor-pointer"
              >
                <Download className="size-3.5" />
                <span>Tải tệp Word gốc (.docx)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  toast.success("Đang tải bản scan PDF có dấu đỏ...")
                }
                className="gap-2 cursor-pointer"
              >
                <FileDown className="size-3.5" />
                <span>Tải bản scan PDF (.pdf)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  toast.success("Đang tải bản Markdown chuẩn hóa (.md)...")
                }
                className="gap-2 cursor-pointer"
              >
                <FileCode className="size-3.5" />
                <span>Tải bản Markdown (.md)</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => {
                  toast.info("Đang kích hoạt quy trình quét lại OCR...");
                }}
                className="gap-2 cursor-pointer"
              >
                <RefreshCw className="size-3.5" />
                <span>Bóc tách lại OCR</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  toast.info("Đang mở hộp thoại tải phiên bản mới...")
                }
                className="gap-2 cursor-pointer"
              >
                <Upload className="size-3.5" />
                <span>Tải phiên bản mới</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  toast.info("Đang mở chức năng đổi tên tài liệu...")
                }
                className="gap-2 cursor-pointer"
              >
                <Pencil className="size-3.5" />
                <span>Đổi tên tài liệu</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => toast.error("Đã hủy bỏ hành động xóa.")}
                className="gap-2 cursor-pointer text-destructive focus:text-destructive"
              >
                <Trash2 className="size-3.5" />
                <span>Xóa vĩnh viễn tài liệu</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* 2. DUAL-PANE VIEWPORT: PIXEL-PERFECT 50:50 ALIGNMENT                      */}
      {/* ========================================================================= */}
      <div className="flex flex-1 overflow-hidden min-w-0">
        {/* ======================================================================= */}
        {/* LEFT PANE: BẢN GỐC NGUYÊN BẢN (PDF Dấu đỏ HOẶC Word .docx)              */}
        {/* ======================================================================= */}
        <div className="w-1/2 flex-1 flex flex-col border-r border-border/60 bg-muted/15 min-w-0">
          {/* Left Toolbar: Exactly h-10 to match Right Toolbar */}
          <div className="h-10 border-b border-border/60 bg-card px-3 flex items-center justify-between shrink-0 text-xs">
            {/* Format toggle: Word or PDF */}
            <div className="flex items-center gap-1 border border-border/70 rounded-md p-0.5 bg-muted/40 text-xs">
              <button
                type="button"
                onClick={() => setDocFormat("docx")}
                className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer",
                  docFormat === "docx"
                    ? "bg-background text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <span>📝 Bản thảo Word .docx</span>
              </button>
              <button
                type="button"
                onClick={() => setDocFormat("pdf")}
                className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer",
                  docFormat === "pdf"
                    ? "bg-background text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <span>📄 Bản scan PDF dấu đỏ</span>
              </button>
            </div>

            {/* Zoom & Page Controls */}
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                onClick={() => setZoomLevel((z) => Math.max(60, z - 10))}
                title="Thu nhỏ"
              >
                <ZoomOut className="size-3.5" />
              </Button>
              <span className="text-[11px] font-mono text-muted-foreground w-9 text-center">
                {zoomLevel}%
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                onClick={() => setZoomLevel((z) => Math.min(140, z + 10))}
                title="Phóng to"
              >
                <ZoomIn className="size-3.5" />
              </Button>

              <div className="h-3.5 w-px bg-border/60 mx-1" />

              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                title="Trang trước"
              >
                <ChevronLeft className="size-3.5" />
              </Button>
              <span className="text-[11px] text-muted-foreground font-mono">
                {currentPage} / 3
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                disabled={currentPage >= 3}
                onClick={() => setCurrentPage((p) => Math.min(3, p + 1))}
                title="Trang tiếp"
              >
                <ChevronRight className="size-3.5" />
              </Button>
            </div>
          </div>

          {/* Left Content Viewport: Padding exactly p-6 to match Right Pane */}
          <div className="flex-1 overflow-y-auto p-6 flex justify-center">
            <div
              style={{
                transform: `scale(${zoomLevel / 100})`,
                transformOrigin: "top center",
              }}
              className="w-full max-w-2xl transition-transform duration-150"
            >
              {docFormat === "docx" ? (
                /* WORD DOCX VIEW: Matches the right pane line-for-line */
                <div className="bg-card border border-border/70 rounded-xl p-8 shadow-xs space-y-4 text-xs leading-relaxed text-foreground select-text">
                  {/* Top Document Header */}
                  <div className="text-center pb-4 border-b border-border/40 space-y-1">
                    <h1 className="text-sm font-bold tracking-tight uppercase text-foreground">
                      DỮ LIỆU TRI THỨC VỀ TRƯỜNG ĐẠI HỌC QUY NHƠN
                    </h1>
                    <p className="text-[11px] text-muted-foreground italic">
                      Phiên bản dữ liệu: 15/10/2026. Nguồn ưu tiên: Cổng thông
                      tin chính thức qnu.edu.vn.
                    </p>
                  </div>

                  {/* Body Paragraphs matching Right Pane */}
                  <p className="text-justify indent-4 leading-normal text-muted-foreground">
                    Phạm vi dữ liệu: nhận diện, lịch sử, triết lý giáo dục, sứ
                    mạng, tầm nhìn, lãnh đạo, cơ cấu tổ chức, đào tạo, tuyển
                    sinh năm 2026, nghiên cứu khoa học, kiểm định, hoạt động
                    sinh viên và thông tin liên hệ. Các số liệu theo năm học
                    hoặc thời điểm công bố được nêu cụ thể; không suy diễn khi
                    nguồn không có số liệu cố định.
                  </p>

                  <h2 className="font-bold text-xs text-foreground uppercase tracking-tight pt-2">
                    1. Thông tin nhận diện Trường Đại học Quy Nhơn
                  </h2>
                  <p className="text-justify indent-4 leading-normal">
                    Trường Đại học Quy Nhơn có tên tiếng Anh là Quy Nhon
                    University, viết tắt là QNU. Trường Đại học Quy Nhơn là cơ
                    sở giáo dục đại học công lập, trực thuộc Bộ Giáo dục và Đào
                    tạo. Trụ sở chính của Trường Đại học Quy Nhơn theo công khai
                    năm học 2026–2027 đặt tại số 170 đường An Dương Vương,
                    phường Quy Nhơn Nam, tỉnh Gia Lai. Cổng thông tin chính thức
                    của trường là https://www.qnu.edu.vn. [S1]
                  </p>
                  <p className="text-justify indent-4 leading-normal">
                    Mã cơ sở đào tạo của Trường Đại học Quy Nhơn sử dụng trong
                    tuyển sinh đại học năm 2026 là DQN. Website thông tin tuyển
                    sinh của Trường Đại học Quy Nhơn là
                    https://tuyensinh.qnu.edu.vn. Mã DQN là thông tin tuyển
                    sinh, khác với tên viết tắt QNU dùng để nhận diện trường
                    trong tiếng Anh và truyền thông. [S0]
                  </p>

                  <h2 className="font-bold text-xs text-foreground uppercase tracking-tight pt-2">
                    2. Lịch sử hình thành và các mốc pháp lý
                  </h2>
                  <p className="text-justify indent-4 leading-normal">
                    Ngày 21/12/1977, Bộ trưởng Bộ Giáo dục ban hành Quyết định
                    số 1842/QĐ thành lập Cơ sở Đại học Sư phạm Quy Nhơn. Đây là
                    mốc khởi đầu trong lịch sử hình thành Trường Đại học Quy
                    Nhơn và là cơ sở để trường tính số năm truyền thống. Vì vậy,
                    khi được hỏi Trường Đại học Quy Nhơn thành lập năm nào, mốc
                    trả lời phù hợp theo lịch sử nhà trường là năm 1977, cụ thể
                    ngày 21 tháng 12 năm 1977. [S1] [S2]
                  </p>
                  <p className="text-justify indent-4 leading-normal">
                    Ngày 13/7/1981, Hội đồng Bộ trưởng ban hành Quyết định số
                    02/HĐBT thành lập Trường Đại học Sư phạm Quy Nhơn. Mốc 13
                    tháng 7 năm 1981 đánh dấu việc thành lập trường đại học toàn
                    diện trên nền tảng cơ sở đã mở từ năm 1977. Hai mốc năm 1977
                    và năm 1981 phản ánh hai sự kiện pháp lý khác nhau, không
                    nên dùng thay thế cho nhau. [S2]
                  </p>
                  <p className="text-justify indent-4 leading-normal">
                    Ngày 30/10/2003, Thủ tướng Chính phủ ban hành Quyết định số
                    221/2003/QĐ-TTg đổi tên Trường Đại học Sư phạm Quy Nhơn
                    thành Trường Đại học Quy Nhơn. Tên gọi Trường Đại học Quy
                    Nhơn gắn với định hướng phát triển đa ngành, đa lĩnh vực
                    thay cho mô hình đào tạo chủ yếu về sư phạm trước đó. [S1]
                    [S2]
                  </p>

                  <h2 className="font-bold text-xs text-foreground uppercase tracking-tight pt-2">
                    3. Định mức thu học phí theo tín chỉ (Năm học 2026 - 2027)
                  </h2>
                  <p className="text-muted-foreground leading-normal">
                    Căn cứ Nghị định số 81/2021/NĐ-CP và Nghị định số
                    97/2023/NĐ-CP của Chính phủ, định mức thu học phí đối với
                    các ngành đào tạo chuẩn áp dụng theo Bảng 1:
                  </p>
                  <div className="rounded-md border border-border/80 overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-muted/60 font-semibold text-muted-foreground border-b border-border/80">
                        <tr>
                          <th className="p-2 w-10 text-center">STT</th>
                          <th className="p-2">Khối ngành đào tạo</th>
                          <th className="p-2 text-right">
                            Định mức thu (VNĐ/tín chỉ)
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        <tr>
                          <td className="p-2 text-center font-mono">1</td>
                          <td className="p-2 font-medium">
                            Khối ngành Kỹ thuật & CNTT
                          </td>
                          <td className="p-2 text-right font-bold font-mono text-primary">
                            550.000 VNĐ
                          </td>
                        </tr>
                        <tr>
                          <td className="p-2 text-center font-mono">2</td>
                          <td className="p-2 font-medium">
                            Khối ngành Kinh tế & Quản trị kinh doanh
                          </td>
                          <td className="p-2 text-right font-mono">
                            480.000 VNĐ
                          </td>
                        </tr>
                        <tr>
                          <td className="p-2 text-center font-mono">3</td>
                          <td className="p-2 font-medium">
                            Khối ngành Sư phạm & Đào tạo giáo viên
                          </td>
                          <td className="p-2 text-right font-medium italic text-emerald-600">
                            Miễn 100% (NĐ 116)
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                /* PDF SCAN VIEW: Authentic scanned decision with red seal stamp */
                <div className="bg-white text-zinc-900 border border-zinc-300 rounded-sm shadow-md p-8 md:p-10 space-y-5 font-serif text-[11px] leading-relaxed relative select-text">
                  <div className="flex justify-between items-start border-b border-zinc-200 pb-3">
                    <div>
                      <p className="font-bold uppercase text-[9.5px]">
                        BỘ GIÁO DỤC VÀ ĐÀO TẠO
                      </p>
                      <p className="font-bold uppercase text-[10.5px] text-teal-900">
                        TRƯỜNG ĐẠI HỌC QUY NHƠN
                      </p>
                      <p className="italic text-[9px] text-zinc-600">
                        Số: 128/QĐ-ĐHQN
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold uppercase text-[9.5px]">
                        CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
                      </p>
                      <p className="font-bold text-[9.5px]">
                        Độc lập - Tự do - Hạnh phúc
                      </p>
                      <p className="italic text-[9px] text-zinc-600">
                        Quy Nhơn, ngày 15 tháng 10 năm 2026
                      </p>
                    </div>
                  </div>

                  <div className="text-center py-2 space-y-1">
                    <h2 className="font-bold text-xs uppercase tracking-tight font-serif text-zinc-950">
                      QUYẾT ĐỊNH
                    </h2>
                    <p className="font-bold text-[10.5px] uppercase tracking-tight text-teal-950">
                      Về việc công bố Quy định Đào tạo và Định mức học phí năm
                      học 2026 - 2027
                    </p>
                  </div>

                  <p className="text-justify indent-4 leading-normal">
                    Trường Đại học Quy Nhơn (tên tiếng Anh: Quy Nhon University
                    - QNU) là cơ sở giáo dục đại học công lập, trực thuộc Bộ
                    Giáo dục và Đào tạo. Cơ sở thành lập theo Quyết định số
                    1842/QĐ ngày 21/12/1977 của Bộ trưởng Bộ Giáo dục và Quyết
                    định số 02/HĐBT ngày 13/7/1981 của Hội đồng Bộ trưởng thành
                    lập Trường Đại học Sư phạm Quy Nhơn.
                  </p>

                  <div className="pt-2">
                    <table className="w-full border-collapse border border-zinc-400 text-[10px] text-zinc-900 font-sans">
                      <thead>
                        <tr className="bg-zinc-200 font-bold">
                          <th className="border border-zinc-400 p-1 text-center w-10">
                            STT
                          </th>
                          <th className="border border-zinc-400 p-1">
                            Khối ngành đào tạo
                          </th>
                          <th className="border border-zinc-400 p-1 text-right">
                            Định mức thu (VNĐ/tín chỉ)
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="border border-zinc-400 p-1 text-center font-mono">
                            1
                          </td>
                          <td className="border border-zinc-400 p-1 font-medium">
                            Khối ngành Kỹ thuật & CNTT
                          </td>
                          <td className="border border-zinc-400 p-1 text-right font-mono font-bold text-teal-800">
                            550.000 VNĐ
                          </td>
                        </tr>
                        <tr>
                          <td className="border border-zinc-400 p-1 text-center font-mono">
                            2
                          </td>
                          <td className="border border-zinc-400 p-1 font-medium">
                            Khối ngành Kinh tế & Quản trị
                          </td>
                          <td className="border border-zinc-400 p-1 text-right font-mono">
                            480.000 VNĐ
                          </td>
                        </tr>
                        <tr>
                          <td className="border border-zinc-400 p-1 text-center font-mono">
                            3
                          </td>
                          <td className="border border-zinc-400 p-1 font-medium">
                            Khối ngành Sư phạm
                          </td>
                          <td className="border border-zinc-400 p-1 text-right text-emerald-800 italic">
                            Miễn 100% (NĐ 116)
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Authentic Red Stamp & Signature */}
                  <div className="pt-6 flex items-end justify-between">
                    <div className="text-[9px] text-zinc-500 italic">
                      <p>Nơi nhận:</p>
                      <p>- Ban Giám hiệu;</p>
                      <p>- Các đơn vị trực thuộc;</p>
                      <p>- Lưu VT, ĐT.</p>
                    </div>
                    <div className="relative text-center pr-6">
                      <p className="font-bold text-[9.5px] uppercase">
                        TM. HỘI ĐỒNG TRƯỜNG / HIỆU TRƯỞNG
                      </p>
                      <div className="h-16 relative flex items-center justify-center">
                        <div className="size-16 rounded-full border-2 border-red-600/90 flex flex-col items-center justify-center p-0.5 text-red-600 font-serif text-[6.5px] uppercase font-bold text-center leading-none shadow-xs rotate-[-8deg] opacity-90 select-none">
                          <div className="size-14 rounded-full border border-dashed border-red-600/80 flex flex-col items-center justify-center p-1">
                            <span>TRƯỜNG ĐH</span>
                            <span className="text-[8px] font-black tracking-wider text-red-700">
                              QUY NHƠN
                            </span>
                            <span className="text-[5.5px]">★ BỘ GD&ĐT ★</span>
                          </div>
                        </div>
                        <span className="absolute font-serif italic text-blue-700 font-bold text-sm rotate-[-12deg] left-3">
                          Nguyễn Quang
                        </span>
                      </div>
                      <p className="font-bold text-[10px] text-zinc-800 pt-1">
                        PGS.TS. Nguyễn Quang Ngoạn
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ======================================================================= */}
        {/* RIGHT PANE: BẢN BÓC TÁCH OCR & BIÊN SOẠN (PIXEL-PERFECT ALIGNED)        */}
        {/* ======================================================================= */}
        <div className="w-1/2 flex-1 flex flex-col bg-background min-w-0">
          {/* Right Toolbar: Exactly h-10 to match Left Toolbar */}
          <div className="h-10 border-b border-border/60 bg-card px-4 flex items-center justify-between shrink-0 text-xs">
            {/* View format tabs */}
            <Tabs
              value={activeTab}
              onValueChange={(v) =>
                setActiveTab(v as "text" | "markdown" | "json")
              }
              className="w-auto"
            >
              <TabsList className="h-7 bg-muted/50 p-0.5">
                <TabsTrigger value="text" className="text-xs h-6 px-3">
                  Văn bản bóc tách
                </TabsTrigger>
                <TabsTrigger value="markdown" className="text-xs h-6 px-3">
                  Markdown
                </TabsTrigger>
                <TabsTrigger value="json" className="text-xs h-6 px-3">
                  JSON cấu trúc
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <span className="text-[11px] text-muted-foreground font-mono">
              {sections.length} mục · Đã index RAG
            </span>
          </div>

          {/* Right Content Viewport: Padding exactly p-6 to match Left Pane */}
          <div className="flex-1 overflow-y-auto p-6 flex justify-center">
            <div className="w-full max-w-2xl">
              {activeTab === "text" ? (
                /* Continuous Document Sheet: Exactly matches Left Container Padding & Headers */
                <div className="bg-card border border-border/70 rounded-xl p-8 shadow-xs space-y-4 text-xs leading-relaxed text-foreground">
                  {/* Top Document Header: Exactly matches Left Title & Subtitle */}
                  <div className="text-center pb-4 border-b border-border/40 space-y-1">
                    <h1 className="text-sm font-bold tracking-tight uppercase text-foreground">
                      DỮ LIỆU TRI THỨC VỀ TRƯỜNG ĐẠI HỌC QUY NHƠN
                    </h1>
                    <p className="text-[11px] text-muted-foreground italic">
                      Phiên bản dữ liệu: 15/10/2026. Nguồn ưu tiên: Cổng thông
                      tin chính thức qnu.edu.vn.
                    </p>
                  </div>

                  {/* Render Sections with Inline Editing */}
                  <div className="space-y-3">
                    {sections
                      .filter((s) => s.type !== "meta")
                      .map((sec) => {
                        const isEditing = editingId === sec.id;
                        const displayText = sec.editedContent ?? sec.content;

                        if (isEditing) {
                          return (
                            <div
                              key={sec.id}
                              className="rounded-lg border border-primary/50 bg-primary/5 p-3 space-y-2 shadow-2xs"
                            >
                              <Textarea
                                value={draftContent}
                                onChange={(e) =>
                                  setDraftContent(e.target.value)
                                }
                                className="min-h-[80px] text-xs bg-background resize-y"
                                autoFocus
                              />
                              <div className="flex items-center justify-end gap-1.5 pt-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={cancelEdit}
                                  className="h-7 px-2 text-xs text-muted-foreground"
                                >
                                  <X className="size-3 mr-1" />
                                  <span>Hủy</span>
                                </Button>
                                <Button
                                  size="sm"
                                  onClick={() => saveEdit(sec.id)}
                                  className="h-7 px-2.5 text-xs bg-primary text-primary-foreground"
                                >
                                  <Check className="size-3 mr-1" />
                                  <span>Lưu đoạn</span>
                                </Button>
                              </div>
                            </div>
                          );
                        }

                        if (sec.type === "heading") {
                          return (
                            <div
                              key={sec.id}
                              className="group relative flex items-center justify-between pt-2"
                            >
                              <h2 className="font-bold text-xs text-foreground uppercase tracking-tight">
                                {displayText}
                              </h2>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startEdit(sec)}
                                className="size-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-primary cursor-pointer"
                                title="Chỉnh sửa tiêu đề"
                              >
                                <Edit3 className="size-3" />
                              </Button>
                            </div>
                          );
                        }

                        if (sec.type === "table") {
                          return (
                            <div key={sec.id} className="space-y-2 pt-1">
                              <p className="text-muted-foreground leading-normal">
                                {displayText}
                              </p>
                              {sec.tableData && (
                                <div className="rounded-md border border-border/80 overflow-hidden">
                                  <table className="w-full text-xs text-left">
                                    <thead className="bg-muted/60 font-semibold text-muted-foreground border-b border-border/80">
                                      <tr>
                                        {sec.tableData.headers.map((h) => (
                                          <th
                                            key={h}
                                            className={cn(
                                              "p-2",
                                              h === "STT"
                                                ? "w-10 text-center"
                                                : h.includes("Định mức")
                                                  ? "text-right"
                                                  : "",
                                            )}
                                          >
                                            {h}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border/60">
                                      {sec.tableData.rows.map((row) => (
                                        <tr
                                          key={row.stt}
                                          className="hover:bg-muted/30 transition-colors"
                                        >
                                          <td className="p-2 text-center font-mono">
                                            {row.stt}
                                          </td>
                                          <td className="p-2 font-medium">
                                            {row.major}
                                          </td>
                                          <td
                                            className={cn(
                                              "p-2 text-right font-mono",
                                              row.stt === "1"
                                                ? "font-bold text-primary"
                                                : row.stt === "3"
                                                  ? "font-medium italic text-emerald-600"
                                                  : "",
                                            )}
                                          >
                                            {row.tuition}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          );
                        }

                        return (
                          <div
                            key={sec.id}
                            className={cn(
                              "group relative rounded-lg p-2 transition-colors",
                              sec.isEdited
                                ? "border-l-2 border-amber-500 bg-amber-500/5 pl-3"
                                : "hover:bg-muted/30",
                            )}
                          >
                            <p className="text-justify indent-4 leading-normal text-foreground/90">
                              {displayText}
                            </p>

                            {/* Floating Action Badge on Hover */}
                            <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                              {sec.isEdited && (
                                <Badge
                                  variant="outline"
                                  className="text-[9px] bg-amber-500/10 text-amber-600 border-amber-500/30 font-normal"
                                >
                                  Đã sửa
                                </Badge>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startEdit(sec)}
                                className="size-6 p-0 text-muted-foreground hover:text-primary cursor-pointer bg-card/80 shadow-2xs border border-border/50"
                                title="Chỉnh sửa đoạn này"
                              >
                                <Edit3 className="size-3" />
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              ) : activeTab === "markdown" ? (
                /* MARKDOWN VIEW */
                <div className="bg-card border border-border/70 rounded-xl p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-border/50">
                    <span className="text-xs font-mono font-semibold text-muted-foreground">
                      Bản Markdown định dạng chuẩn hóa (.md)
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(markdownContent);
                        toast.success("Đã sao chép Markdown vào khay nhớ tạm!");
                      }}
                      className="h-7 text-xs gap-1"
                    >
                      <Copy className="size-3" />
                      <span>Sao chép Markdown</span>
                    </Button>
                  </div>
                  <pre className="font-mono text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap bg-muted/30 p-4 rounded-lg overflow-x-auto">
                    {markdownContent}
                  </pre>
                </div>
              ) : (
                /* JSON DATA VIEW */
                <div className="bg-card border border-border/70 rounded-xl p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-border/50">
                    <span className="text-xs font-mono font-semibold text-muted-foreground">
                      Cấu trúc bóc tách JSON (Chunks & Metadata)
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(
                          JSON.stringify(sections, null, 2),
                        );
                        toast.success("Đã sao chép JSON vào khay nhớ tạm!");
                      }}
                      className="h-7 text-xs gap-1"
                    >
                      <Copy className="size-3" />
                      <span>Sao chép JSON</span>
                    </Button>
                  </div>
                  <pre className="font-mono text-[11px] leading-relaxed text-muted-foreground whitespace-pre-wrap bg-muted/30 p-4 rounded-lg overflow-x-auto max-h-[500px]">
                    {JSON.stringify(sections, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

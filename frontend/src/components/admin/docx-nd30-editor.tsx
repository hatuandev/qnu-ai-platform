import {
  CheckCircle2,
  Copy,
  Download,
  FileCheck,
  FileText,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
} from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import { type ToolExecuteResponse, apiClient } from "../../services/api-client";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

export interface DocxParagraphItem {
  id: string;
  text: string;
}

export interface DocxNd30FormData {
  documentType: string;
  subAgency: string;
  documentNumber: string;
  cityDate: string;
  title: string;
  paragraphs: DocxParagraphItem[];
  recipients: string[];
  signerTitle: string;
  signerName: string;
}

const DEFAULT_PARAGRAPHS: DocxParagraphItem[] = [
  {
    id: "p_1",
    text: "Căn cứ Quyết định số 1024/QĐ-ĐHQN về việc phát triển các nhóm nghiên cứu mạnh giai đoạn 2025-2030;",
  },
  {
    id: "p_2",
    text: "Nhằm đáp ứng nhu cầu đào tạo và thực hành mô hình ngôn ngữ lớn (LLM) và Thị giác máy tính cho sinh viên ngành Trí tuệ Nhân tạo và Kỹ thuật Phần mềm;",
  },
  {
    id: "p_3",
    text: "Khoa Công nghệ Thông tin kính trình Ban Giám hiệu xem xét, phê duyệt chủ trương mua sắm bổ sung 04 máy chủ tính toán GPU chuyên dụng với dự toán kinh phí dự kiến là 450.000.000 VNĐ (Bằng chữ: Bốn trăm năm mươi triệu đồng).",
  },
  {
    id: "p_4",
    text: "Kính đề nghị Ban Giám hiệu xem xét, phê duyệt để Khoa có cơ sở triển khai các bước tiếp theo theo quy định hiện hành.",
  },
];

const DEFAULT_DOC_DATA: DocxNd30FormData = {
  documentType: "TỜ TRÌNH",
  subAgency: "KHOA CÔNG NGHỆ THÔNG TIN",
  documentNumber: "Số: 45 /TTr-CNTT",
  cityDate: "Quy Nhơn, ngày 16 tháng 09 năm 2026",
  title: "Về việc phê duyệt chủ trương nâng cấp hạ tầng phòng thí nghiệm Trí tuệ Nhân tạo",
  paragraphs: DEFAULT_PARAGRAPHS,
  recipients: [
    "Ban Giám hiệu (để báo cáo)",
    "Phòng Kế hoạch - Tài chính",
    "Phòng Quản trị - Thiết bị",
    "Lưu: VT, Khoa CNTT.",
  ],
  signerTitle: "TRƯỞNG KHOA",
  signerName: "TS. Lê Văn Tuấn",
};

export interface DocxNd30EditorProps {
  initialData?: {
    documentType?: string;
    subAgency?: string;
    documentNumber?: string;
    cityDate?: string;
    title?: string;
    paragraphs?: string[];
    recipients?: string[];
    signerTitle?: string;
    signerName?: string;
  };
  onGeneratedSuccess?: (response: ToolExecuteResponse) => void;
}

export const DocxNd30Editor: React.FC<DocxNd30EditorProps> = ({
  initialData,
  onGeneratedSuccess,
}) => {
  const [formData, setFormData] = useState<DocxNd30FormData>(() => {
    if (!initialData) return DEFAULT_DOC_DATA;
    return {
      documentType: initialData.documentType || DEFAULT_DOC_DATA.documentType,
      subAgency: initialData.subAgency || DEFAULT_DOC_DATA.subAgency,
      documentNumber: initialData.documentNumber || DEFAULT_DOC_DATA.documentNumber,
      cityDate: initialData.cityDate || DEFAULT_DOC_DATA.cityDate,
      title: initialData.title || DEFAULT_DOC_DATA.title,
      paragraphs: initialData.paragraphs
        ? initialData.paragraphs.map((text, idx) => ({ id: `p_init_${idx}_${Date.now()}`, text }))
        : DEFAULT_PARAGRAPHS,
      recipients: initialData.recipients || DEFAULT_DOC_DATA.recipients,
      signerTitle: initialData.signerTitle || DEFAULT_DOC_DATA.signerTitle,
      signerName: initialData.signerName || DEFAULT_DOC_DATA.signerName,
    };
  });

  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [lastResponse, setLastResponse] = useState<ToolExecuteResponse | null>(null);

  // Thêm đoạn văn bản
  const handleAddParagraph = () => {
    setFormData((prev) => ({
      ...prev,
      paragraphs: [
        ...prev.paragraphs,
        {
          id: `p_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
          text: "Nhập nội dung điều khoản / đoạn văn mới...",
        },
      ],
    }));
  };

  // Sửa đoạn văn bản
  const handleUpdateParagraph = (id: string, text: string) => {
    setFormData((prev) => ({
      ...prev,
      paragraphs: prev.paragraphs.map((p) => (p.id === id ? { ...p, text } : p)),
    }));
  };

  // Xóa đoạn văn bản
  const handleDeleteParagraph = (id: string) => {
    if (formData.paragraphs.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      paragraphs: prev.paragraphs.filter((p) => p.id !== id),
    }));
  };

  // Khôi phục mặc định
  const handleReset = () => {
    setFormData(DEFAULT_DOC_DATA);
    setLastResponse(null);
  };

  // Thực thi sinh file Word NĐ 30
  const handleGenerateWord = useCallback(async () => {
    setIsGenerating(true);
    try {
      const response = await apiClient.executeTool({
        tool_name: "export_administrative_document",
        parameters: {
          document_type: formData.documentType,
          title: formData.title,
          body_paragraphs: formData.paragraphs.map((p) => p.text),
          signer_title: formData.signerTitle,
          signer_name: formData.signerName,
          recipients: formData.recipients,
        },
      });

      setLastResponse(response);
      if (onGeneratedSuccess) {
        onGeneratedSuccess(response);
      }
    } finally {
      setIsGenerating(false);
    }
  }, [formData, onGeneratedSuccess]);

  // Giả lập tải xuống tệp DOCX
  const handleDownloadFile = () => {
    const content = `VĂN BẢN CHUẨN NGHỊ ĐỊNH 30/2020/NĐ-CP\n${formData.documentType}\n${formData.title}\n\n${formData.paragraphs.map((p) => p.text).join("\n\n")}\n\nNgười ký: ${formData.signerTitle} - ${formData.signerName}`;
    const blob = new Blob([content], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${formData.documentType.toLowerCase()}_${formData.title.slice(0, 20).replace(/\s+/g, "_")}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyText = () => {
    const fullText = `${formData.documentType}\n${formData.title}\n\n${formData.paragraphs.map((p) => p.text).join("\n\n")}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(fullText);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-surface bg-muted/40 border border-border">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-primary/10 text-primary">
            <FileText className="size-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground">
              Soạn Thảo Văn Bản Chuẩn Nghị Định 30/2020/NĐ-CP
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Quy chuẩn lề chuẩn: Trái 30mm, Phải 15mm, Trên 20mm, Dưới 20mm • Phông Times New Roman
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleReset}>
            <RotateCcw className="size-3 mr-1" />
            <span>Mặc định</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={handleCopyText}
            title="Sao chép nội dung"
          >
            <Copy className="size-3 mr-1" />
            <span>{isCopied ? "Đã chép" : "Sao chép"}</span>
          </Button>

          <Button
            size="sm"
            className="h-7 text-xs font-semibold shadow-xs"
            disabled={isGenerating}
            onClick={handleGenerateWord}
          >
            <Sparkles className="size-3 mr-1" />
            <span>{isGenerating ? "Đang xuất bản Word..." : "Xuất File Word (.docx)"}</span>
          </Button>
        </div>
      </div>

      {/* Main Grid: Form Inputs vs Live Paper Sheet */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Form Controls (5 Cols) */}
        <div className="lg:col-span-5 space-y-3.5">
          {/* Metadata Section */}
          <div className="p-4 rounded-surface bg-card border border-border space-y-3">
            <span className="font-semibold text-xs text-foreground flex items-center gap-1.5">
              <FileCheck className="size-3.5 text-primary" />
              <span>Thể Thức & Định Danh Văn Bản</span>
            </span>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <label
                  htmlFor="input-doc-type"
                  className="text-[11px] text-muted-foreground font-medium block mb-1"
                >
                  Loại văn bản:
                </label>
                <select
                  id="input-doc-type"
                  value={formData.documentType}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, documentType: e.target.value }))
                  }
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary"
                >
                  <option value="TỜ TRÌNH">TỜ TRÌNH</option>
                  <option value="QUYẾT ĐỊNH">QUYẾT ĐỊNH</option>
                  <option value="THÔNG BÁO">THÔNG BÁO</option>
                  <option value="KẾ HOẠCH">KẾ HOẠCH</option>
                  <option value="CÔNG VĂN">CÔNG VĂN</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="input-sub-agency"
                  className="text-[11px] text-muted-foreground font-medium block mb-1"
                >
                  Đơn vị soạn thảo:
                </label>
                <input
                  id="input-sub-agency"
                  type="text"
                  value={formData.subAgency}
                  onChange={(e) => setFormData((prev) => ({ ...prev, subAgency: e.target.value }))}
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <label
                  htmlFor="input-doc-number"
                  className="text-[11px] text-muted-foreground font-medium block mb-1"
                >
                  Số & Ký hiệu:
                </label>
                <input
                  id="input-doc-number"
                  type="text"
                  value={formData.documentNumber}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, documentNumber: e.target.value }))
                  }
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary font-mono"
                />
              </div>

              <div>
                <label
                  htmlFor="input-city-date"
                  className="text-[11px] text-muted-foreground font-medium block mb-1"
                >
                  Địa danh, Ngày tháng:
                </label>
                <input
                  id="input-city-date"
                  type="text"
                  value={formData.cityDate}
                  onChange={(e) => setFormData((prev) => ({ ...prev, cityDate: e.target.value }))}
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="input-doc-title"
                className="text-[11px] text-muted-foreground font-medium block mb-1"
              >
                Trích yếu nội dung (Về việc...):
              </label>
              <textarea
                id="input-doc-title"
                rows={2}
                value={formData.title}
                onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full p-2 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary resize-none font-semibold"
              />
            </div>
          </div>

          {/* Paragraphs Section */}
          <div className="p-4 rounded-surface bg-card border border-border space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <FileText className="size-3.5 text-primary" />
                <span>Nội Dung Các Đoạn Văn ({formData.paragraphs.length})</span>
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-[11px] px-2"
                onClick={handleAddParagraph}
              >
                <Plus className="size-3 mr-1" />
                <span>Thêm đoạn</span>
              </Button>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {formData.paragraphs.map((p, pIdx) => (
                <div key={p.id} className="relative group flex items-start gap-1.5">
                  <span className="text-[10px] font-mono text-muted-foreground mt-2 w-4 shrink-0">
                    {pIdx + 1}.
                  </span>
                  <textarea
                    rows={3}
                    value={p.text}
                    onChange={(e) => handleUpdateParagraph(p.id, e.target.value)}
                    className="flex-1 p-2 text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary resize-none leading-relaxed"
                  />
                  {formData.paragraphs.length > 1 && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6 text-muted-foreground hover:text-destructive shrink-0 mt-1"
                      onClick={() => handleDeleteParagraph(p.id)}
                      title="Xóa đoạn này"
                    >
                      <Trash2 className="size-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Signer & Recipients */}
          <div className="p-4 rounded-surface bg-card border border-border space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <label
                  htmlFor="input-signer-title"
                  className="text-[11px] text-muted-foreground font-medium block mb-1"
                >
                  Chức vụ người ký:
                </label>
                <input
                  id="input-signer-title"
                  type="text"
                  value={formData.signerTitle}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, signerTitle: e.target.value }))
                  }
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary font-semibold"
                />
              </div>

              <div>
                <label
                  htmlFor="input-signer-name"
                  className="text-[11px] text-muted-foreground font-medium block mb-1"
                >
                  Họ tên người ký:
                </label>
                <input
                  id="input-signer-name"
                  type="text"
                  value={formData.signerName}
                  onChange={(e) => setFormData((prev) => ({ ...prev, signerName: e.target.value }))}
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary font-semibold"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Live Paper Sheet Preview (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-foreground">
                Tờ Giấy A4 Trực Quan (Live Document Preview)
              </span>
              <Badge variant="outline" className="text-[10px] font-mono">
                Standard: ND 30/2020/NĐ-CP
              </Badge>
            </div>

            {lastResponse && (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="default"
                  className="h-7 text-xs bg-success text-success-foreground hover:bg-success/90"
                  onClick={handleDownloadFile}
                >
                  <Download className="size-3 mr-1" />
                  <span>Tải Word (.docx)</span>
                </Button>
              </div>
            )}
          </div>

          {/* Paper Sheet Container */}
          <div className="flex-1 rounded-surface border border-border bg-muted/30 p-4 sm:p-6 overflow-x-auto flex justify-center">
            {/* Realistic A4 Paper */}
            <div
              data-testid="nd30-paper-preview"
              className="w-full max-w-[560px] min-h-[680px] bg-white text-neutral-900 shadow-xl border border-neutral-200 rounded-xs p-6 sm:p-8 font-serif select-text flex flex-col justify-between"
              style={{
                fontFamily: "'Times New Roman', Times, serif",
                fontSize: "13px",
                lineHeight: "1.35",
              }}
            >
              {/* Header Top: 2 Columns */}
              <div>
                <div className="grid grid-cols-12 gap-2 text-center pb-4 border-b border-neutral-300">
                  {/* Left Header: Cơ Quan Ban Hành */}
                  <div className="col-span-5 space-y-0.5">
                    <p className="text-[11px] font-normal uppercase text-neutral-700">
                      BỘ GIÁO DỤC VÀ ĐÀO TẠO
                    </p>
                    <p className="text-[11px] font-bold uppercase text-neutral-900 leading-tight">
                      TRƯỜNG ĐẠI HỌC QUY NHƠN
                    </p>
                    <p className="text-[10px] font-semibold text-neutral-700">
                      {formData.subAgency}
                    </p>
                    <div className="w-16 h-px bg-neutral-400 mx-auto my-1" />
                    <p className="text-[10px] italic text-neutral-600">{formData.documentNumber}</p>
                  </div>

                  {/* Right Header: Quốc Hiệu - Tiêu Ngữ */}
                  <div className="col-span-7 space-y-0.5">
                    <p className="text-[11px] font-bold uppercase text-neutral-900 leading-tight">
                      CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
                    </p>
                    <p className="text-[12px] font-bold text-neutral-900">
                      Độc lập - Tự do - Hạnh phúc
                    </p>
                    <div className="w-24 h-px bg-neutral-800 mx-auto my-1" />
                    <p className="text-[10px] italic text-neutral-600 pt-1">{formData.cityDate}</p>
                  </div>
                </div>

                {/* Title */}
                <div className="text-center py-5 space-y-1.5">
                  <h2 className="text-base sm:text-lg font-bold uppercase tracking-wider text-neutral-950">
                    {formData.documentType}
                  </h2>
                  <p className="text-xs sm:text-sm font-bold text-neutral-900 max-w-md mx-auto leading-normal">
                    {formData.title}
                  </p>
                </div>

                {/* Document Body Paragraphs */}
                <div className="space-y-2.5 text-justify text-neutral-900 text-xs sm:text-[13px]">
                  {formData.paragraphs.map((p) => (
                    <p key={p.id} className="indent-6 leading-relaxed">
                      {p.text}
                    </p>
                  ))}
                </div>
              </div>

              {/* Bottom Footer: Recipients (Left) & Signer (Right) */}
              <div className="grid grid-cols-12 gap-2 pt-6 mt-6 border-t border-neutral-300 items-start">
                {/* Recipients */}
                <div className="col-span-6 text-[10px] text-neutral-800 space-y-0.5">
                  <p className="font-bold italic text-[11px]">Nơi nhận:</p>
                  {formData.recipients.map((r) => (
                    <p key={r} className="leading-tight">
                      - {r}
                    </p>
                  ))}
                </div>

                {/* Signer */}
                <div className="col-span-6 text-center space-y-1">
                  <p className="font-bold uppercase text-xs text-neutral-900">
                    {formData.signerTitle}
                  </p>
                  <p className="text-[10px] italic text-neutral-500">(Ký và ghi rõ họ tên)</p>
                  <div className="h-12 flex items-center justify-center">
                    <span className="text-[11px] font-serif italic text-primary/70 transform -rotate-3 select-none">
                      (Đã ký điện tử)
                    </span>
                  </div>
                  <p className="font-bold text-xs text-neutral-900">{formData.signerName}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Execution Result Banner */}
          {lastResponse && (
            <div className="p-3 rounded-surface bg-success/10 border border-success/30 flex items-center justify-between text-xs animate-in fade-in duration-200">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-success shrink-0" />
                <div>
                  <span className="font-semibold text-foreground">
                    Đã kết xuất thành công tệp Word (.docx) chuẩn NĐ 30!
                  </span>
                  <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                    {String(lastResponse.result.file_name)} •{" "}
                    {(Number(lastResponse.result.size_bytes) / 1024).toFixed(1)} KB • Lề 20-20-30-15
                    mm
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  onClick={handleDownloadFile}
                >
                  <Download className="size-3 mr-1" />
                  <span>Tải Về</span>
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

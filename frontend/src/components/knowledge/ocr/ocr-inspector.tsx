import {
  Building2,
  Check,
  Code,
  Copy,
  Eye,
  Sparkles,
  Type,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { Field } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { OcrInspectorProps, OcrRightTab } from "./types";

export const OcrInspector: React.FC<OcrInspectorProps> = ({
  pageData,
  allPages,
  documentTitle,
  documentFilename,
  rightTab,
  onTabChange,
  markdownViewMode,
  onMarkdownViewModeChange,
  editableMarkdown,
  onMarkdownChange: _onMarkdownChange,
  selectedRegion: _selectedRegion,
  onSelectRegion: _onSelectRegion,
  onCopyContent,
  isCopied,
  isEditable: _isEditable = true,
}) => {
  const [fontSize, setFontSize] = useState<"sm" | "base">("sm");

  const currentMarkdown = editableMarkdown || pageData?.markdown || "";

  const formattedMarkdown = useMemo(() => {
    if (!currentMarkdown) return "";
    return currentMarkdown
      .split("\n")
      .map((line) => {
        const trimmed = line.trim();
        if (
          !trimmed ||
          trimmed.startsWith("|") ||
          trimmed.startsWith("#") ||
          trimmed.startsWith("---") ||
          trimmed.startsWith("```") ||
          trimmed.endsWith("  ")
        ) {
          return line;
        }
        return `${line}  `;
      })
      .join("\n");
  }, [currentMarkdown]);

  // Bóc tách động thông tin thực thể hành chính từ các trang OCR
  const extractedEntities = useMemo(() => {
    let agency = "";
    let docNumber = "";
    let docType = "";
    let subject = "";
    let locationAndDate = "";
    let year = "";
    let signerTitle = "";
    let signerName = "";
    let recipients = "";

    const p1 = allPages?.[0] || pageData;
    const p1Regions = p1?.regions || [];

    for (const r of p1Regions) {
      const clean = (r.text || "").trim();
      const lines = clean
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean);

      if (r.type === "header") {
        if (r.left < 45) {
          for (const l of lines) {
            if (/^(?:BỘ|SỞ|TRƯỜNG|UBND|VIỆN|HỌC VIỆN)\b/i.test(l)) {
              if (!agency || /ĐẠI HỌC/i.test(l)) {
                agency = l;
              }
            }
            const numMatch = l.match(/(?:Số|So)\s*[:/]\s*([^\n\r]+)/i);
            if (numMatch) {
              const rawNum = numMatch[1].trim();
              docNumber = rawNum.startsWith("/") ? `...${rawNum}` : rawNum;
            }
          }
        } else {
          for (const l of lines) {
            if (/ngày.*năm|năm\s*\d{4}/i.test(l)) {
              locationAndDate = l;
            }
          }
        }
      } else if (r.type === "title" && !docType) {
        if (lines.length > 0) {
          const firstLine = lines[0];
          const typeMatch = firstLine.match(
            /\b(KẾ HOẠCH|QUYẾT ĐỊNH|THÔNG BÁO|PHƯƠNG ÁN|ĐỀ ÁN|TỜ TRÌNH|BÁO CÁO|HƯỚNG DẪN|QUY ĐỊNH|QUY CHẾ|CÔNG VĂN)\b/i,
          );
          if (typeMatch) {
            docType = typeMatch[1].toUpperCase();
            const rest = lines.slice(1);
            if (rest.length > 0) {
              subject = rest.join(" ");
            } else {
              subject = firstLine;
            }
          } else if (!subject) {
            subject = lines.join(" ");
          }
        }
      }
    }

    // Dự phòng nhận diện từ tiêu đề hoặc tên tệp
    const titleSource =
      documentTitle || documentFilename || pageData?.title || "";
    if (!docType) {
      const titleTypeMatch = titleSource.match(
        /\b(KẾ HOẠCH|QUYẾT ĐỊNH|THÔNG BÁO|PHƯƠNG ÁN|ĐỀ ÁN|TỜ TRÌNH|BÁO CÁO|HƯỚNG DẪN|QUY ĐỊNH|QUY CHẾ)\b/i,
      );
      if (titleTypeMatch) {
        docType = titleTypeMatch[1].toUpperCase();
      } else {
        docType = "VĂN BẢN";
      }
    }

    if (!subject) {
      const cleanName = titleSource
        .replace(/^[0-9._\s-]+/, "")
        .replace(/\.(docx?|pdf|xlsx?)$/i, "")
        .trim();
      subject = cleanName || "Văn bản hành chính";
    }

    if (!agency) {
      if (
        /đại học quy nhơn|đhqn/i.test(titleSource) ||
        /đại học quy nhơn/i.test(p1?.rawText || "")
      ) {
        agency = "TRƯỜNG ĐẠI HỌC QUY NHƠN";
      } else {
        agency = "Đơn vị ban hành";
      }
    }

    if (!docNumber) {
      const numFromText = (p1?.rawText || "").match(
        /(?:Số|So)\s*[:/]\s*([^\n\r,]+)/i,
      );
      if (numFromText) {
        const rawNum = numFromText[1].trim();
        docNumber = rawNum.startsWith("/") ? `...${rawNum}` : rawNum;
      } else {
        docNumber = "Đang cập nhật";
      }
    }

    // Trích xuất năm
    const yearMatch = (locationAndDate || subject || titleSource).match(
      /\b(202[4-9]|203\d)\b/,
    );
    if (yearMatch) {
      year = yearMatch[1];
    } else {
      year = new Date().getFullYear().toString();
    }

    // Quét chữ ký và nơi nhận trên toàn bộ các trang
    const pagesToCheck =
      allPages && allPages.length > 0 ? allPages : pageData ? [pageData] : [];
    for (const p of pagesToCheck) {
      for (const r of p.regions || []) {
        const clean = (r.text || "").trim();
        if (r.type === "signature") {
          const lines = clean
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean);
          for (const l of lines) {
            if (
              /^(?:HIỆU TRƯỞNG|KT\.\s*HIỆU TRƯỞNG|PHÓ HIỆU TRƯỞNG|GIÁM ĐỐC|CHỦ TỊCH|TRƯỞNG PHÒNG)\b/i.test(
                l,
              )
            ) {
              signerTitle = l;
            } else if (
              /(?:PGS\.|GS\.|TS\.|ThS\.|[A-ZÀ-ỸĐ][a-zà-ỹđ]+\s+[A-ZÀ-ỸĐ][a-zà-ỹđ]+)/.test(
                l,
              ) &&
              l !== "Chữ ký xác thực"
            ) {
              signerName = l;
            }
          }
        }
        if (r.type === "list" && /nơi nhận\s*[:/]/i.test(clean)) {
          recipients = clean;
        }
      }
    }

    const totalTables = pagesToCheck.reduce(
      (acc, p) => acc + (p.hasTable ? 1 : 0),
      0,
    );
    const totalRegions = pagesToCheck.reduce(
      (acc, p) => acc + (p.regions?.length || 0),
      0,
    );

    return {
      agency,
      docNumber,
      docType,
      subject,
      locationAndDate,
      year,
      signerTitle,
      signerName,
      recipients,
      totalTables,
      totalRegions,
    };
  }, [allPages, pageData, documentTitle, documentFilename]);

  const handleCopyValue = (label: string, value: string) => {
    navigator.clipboard.writeText(value);
    toast.success(`Đã sao chép ${label}`);
  };

  return (
    <div className="flex flex-col h-full bg-card border border-border rounded-lg overflow-hidden shadow-xs">
      <Tabs
        value={rightTab}
        onValueChange={(val) => onTabChange(val as OcrRightTab)}
        className="flex flex-col h-full"
      >
        {/* Tab Header */}
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-muted/20 shrink-0">
          <TabsList className="h-8 bg-muted/60 p-0.5 rounded-md">
            <TabsTrigger
              value="markdown"
              className="text-xs px-3 h-7 gap-1.5 font-medium"
            >
              <Type className="size-3 text-primary" />
              <span>Markdown</span>
            </TabsTrigger>
            <TabsTrigger
              value="entities"
              className="text-xs px-3 h-7 gap-1.5 font-medium"
            >
              <Sparkles className="size-3 text-primary" />
              <span>Thực thể</span>
            </TabsTrigger>
          </TabsList>

          {/* Right actions */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setFontSize(fontSize === "sm" ? "base" : "sm")}
              className="px-1.5 py-0.5 text-muted-foreground hover:text-foreground rounded transition-colors text-xs font-serif border border-transparent hover:border-border"
              title="Thay đổi cỡ chữ"
            >
              Aa
            </button>

            {rightTab === "markdown" && (
              <div className="flex items-center rounded-md border border-border bg-muted/30 p-0.5 text-xs shrink-0">
                <button
                  type="button"
                  onClick={() => onMarkdownViewModeChange("rendered")}
                  className={`flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                    markdownViewMode === "rendered"
                      ? "bg-background text-foreground shadow-2xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="Xem định dạng văn bản hiển thị"
                >
                  <Eye className="size-3 text-primary" />
                  <span>Xem</span>
                </button>
                <button
                  type="button"
                  onClick={() => onMarkdownViewModeChange("raw")}
                  className={`flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                    markdownViewMode === "raw"
                      ? "bg-background text-foreground shadow-2xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="Xem mã nguồn Markdown thô"
                >
                  <Code className="size-3 text-primary" />
                  <span>Mã</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* TAB 1: EXTRACTED ENTITIES (Bóc tách dữ liệu động chuẩn Nghị định 30) */}
        {rightTab === "entities" && (
          <div className="flex-1 overflow-auto p-4 space-y-4 select-text">
            {/* Card 1: Metadata Hành Chính Động */}
            <Card className="rounded-lg border bg-card shadow-2xs">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Building2 className="size-3.5" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold">
                        Thông Tin Văn Bản Hành Chính
                      </CardTitle>
                      <CardDescription className="text-xs text-muted-foreground">
                        Các thuộc tính pháp quy đã được bóc tách tự động
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant="success" className="text-[10px]">
                    Đã chuẩn hóa
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-2 space-y-3 text-xs">
                <Field label="Cơ quan ban hành">
                  <div className="flex items-center justify-between rounded-md border border-border/70 bg-muted/20 px-2.5 py-1.5">
                    <span className="font-medium text-foreground">
                      {extractedEntities.agency}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6 text-muted-foreground hover:text-foreground"
                      onClick={() =>
                        handleCopyValue(
                          "Cơ quan ban hành",
                          extractedEntities.agency,
                        )
                      }
                      title="Sao chép"
                    >
                      <Copy className="size-3" />
                    </Button>
                  </div>
                </Field>

                <div className="grid grid-cols-2 gap-2">
                  <Field label="Số hiệu văn bản">
                    <div className="flex items-center justify-between rounded-md border border-border/70 bg-muted/20 px-2.5 py-1.5">
                      <span className="font-mono font-medium text-foreground">
                        {extractedEntities.docNumber}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-foreground"
                        onClick={() =>
                          handleCopyValue(
                            "Số hiệu văn bản",
                            extractedEntities.docNumber,
                          )
                        }
                        title="Sao chép"
                      >
                        <Copy className="size-3" />
                      </Button>
                    </div>
                  </Field>

                  <Field label="Loại văn bản">
                    <div className="flex items-center h-8 px-2.5 rounded-md border border-border/70 bg-muted/20">
                      <Badge
                        variant="default"
                        className="text-[11px] font-medium"
                      >
                        {extractedEntities.docType}
                      </Badge>
                    </div>
                  </Field>
                </div>

                <Field label="Trích yếu nội dung">
                  <div className="flex items-start justify-between rounded-md border border-border/70 bg-muted/20 px-2.5 py-2">
                    <p className="font-medium text-foreground leading-relaxed">
                      {extractedEntities.subject}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6 shrink-0 ml-1 text-muted-foreground hover:text-foreground"
                      onClick={() =>
                        handleCopyValue(
                          "Trích yếu nội dung",
                          extractedEntities.subject,
                        )
                      }
                      title="Sao chép"
                    >
                      <Copy className="size-3" />
                    </Button>
                  </div>
                </Field>

                <div className="grid grid-cols-2 gap-2">
                  <Field label="Địa danh / Ban hành">
                    <div className="flex items-center h-8 px-2.5 rounded-md border border-border/70 bg-muted/20 truncate">
                      <span className="font-medium text-foreground truncate">
                        {extractedEntities.locationAndDate || "Chưa xác định"}
                      </span>
                    </div>
                  </Field>

                  <Field label="Năm áp dụng">
                    <div className="flex items-center h-8 px-2.5 rounded-md border border-border/70 bg-muted/20">
                      <span className="font-mono font-medium text-foreground">
                        {extractedEntities.year}
                      </span>
                    </div>
                  </Field>
                </div>

                {extractedEntities.signerTitle && (
                  <Field label="Thẩm quyền & Người ký">
                    <div className="rounded-md border border-border/70 bg-muted/20 px-2.5 py-1.5 flex items-center justify-between">
                      <span className="font-medium text-foreground">
                        {extractedEntities.signerTitle}
                        {extractedEntities.signerName
                          ? ` — ${extractedEntities.signerName}`
                          : ""}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-foreground"
                        onClick={() =>
                          handleCopyValue(
                            "Người ký",
                            `${extractedEntities.signerTitle} ${extractedEntities.signerName}`.trim(),
                          )
                        }
                        title="Sao chép"
                      >
                        <Copy className="size-3" />
                      </Button>
                    </div>
                  </Field>
                )}

                {extractedEntities.recipients && (
                  <Field label="Nơi nhận">
                    <div className="rounded-md border border-border/70 bg-muted/20 px-2.5 py-2">
                      <p className="font-mono text-[11px] text-muted-foreground whitespace-pre-line leading-relaxed">
                        {extractedEntities.recipients}
                      </p>
                    </div>
                  </Field>
                )}
              </CardContent>
            </Card>

            {/* Card 2: Dữ liệu Bảng biểu */}
            <Card className="rounded-lg border bg-card shadow-2xs">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex size-7 items-center justify-center rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      <Sparkles className="size-3.5" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold">
                        Bảng Biểu & Cấu Trúc
                      </CardTitle>
                      <CardDescription className="text-xs text-muted-foreground">
                        Bảng số liệu được chuẩn hóa và hiển thị trong Markdown
                      </CardDescription>
                    </div>
                  </div>
                  {pageData?.hasTable ? (
                    <Badge
                      variant="outline"
                      className="text-[10px] text-primary border-primary/30"
                    >
                      Trang này có bảng
                    </Badge>
                  ) : extractedEntities.totalTables > 0 ? (
                    <Badge
                      variant="outline"
                      className="text-[10px] text-amber-600 border-amber-500/30"
                    >
                      {extractedEntities.totalTables} bảng trong tệp
                    </Badge>
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-2 text-xs">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {pageData?.hasTable
                    ? "Dữ liệu bảng đã được chuẩn hóa tự động vào định dạng bảng Markdown. Bạn có thể kiểm tra và hiệu đính trực tiếp tại tab Markdown."
                    : extractedEntities.totalTables > 0
                      ? `Phát hiện ${extractedEntities.totalTables} bảng biểu trên các trang khác trong văn bản. Bạn có thể chuyển trang để kiểm tra.`
                      : "Không phát hiện bảng biểu cấu trúc trong tài liệu này."}
                </p>
                {pageData?.hasTable && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs mt-2.5"
                    onClick={() => onTabChange("markdown")}
                  >
                    Xem tại tab Markdown
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* TAB 2: MARKDOWN */}
        {rightTab === "markdown" && (
          <div className="flex-1 overflow-auto p-4 text-xs">
            {markdownViewMode === "rendered" && (
              <div
                className={`prose prose-xs dark:prose-invert max-w-none text-foreground leading-relaxed ${
                  fontSize === "base" ? "prose-sm" : ""
                }`}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => (
                      <h1 className="text-sm font-semibold text-foreground mt-3 mb-2 pb-1 border-b border-border/80 uppercase tracking-wide">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-xs font-semibold text-foreground mt-2.5 mb-1.5 uppercase">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-xs font-medium text-foreground mt-2 mb-1">
                        {children}
                      </h3>
                    ),
                    p: ({ children }) => (
                      <p className="mb-2 text-xs leading-relaxed text-foreground/90">
                        {children}
                      </p>
                    ),
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-2 border-primary/60 bg-muted/30 pl-3 py-1.5 my-2 italic text-xs text-muted-foreground rounded-r">
                        {children}
                      </blockquote>
                    ),
                    table: ({ children }) => (
                      <div className="my-3 overflow-x-auto rounded border border-border">
                        <table className="w-full border-collapse text-xs text-left">
                          {children}
                        </table>
                      </div>
                    ),
                    th: ({ children }) => (
                      <th className="border-b border-border bg-muted/70 px-2.5 py-1.5 font-semibold text-foreground text-[11px]">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="border-b border-border/60 px-2.5 py-1.5 text-[11px] text-foreground/90">
                        {children}
                      </td>
                    ),
                    ul: ({ children }) => (
                      <ul className="list-disc list-inside my-2 space-y-1 text-xs text-foreground/90 pl-1">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="list-decimal list-inside my-2 space-y-1 text-xs text-foreground/90 pl-1">
                        {children}
                      </ol>
                    ),
                    hr: () => <hr className="my-3 border-border/80" />,
                  }}
                >
                  {formattedMarkdown || "(Trang không có nội dung)"}
                </ReactMarkdown>
              </div>
            )}

            {markdownViewMode === "raw" && (
              <pre className="font-mono text-xs p-3 bg-muted/40 rounded-md border border-border whitespace-pre-wrap select-text leading-relaxed">
                {currentMarkdown || "(Trang không có nội dung)"}
              </pre>
            )}
          </div>
        )}

        {/* Right Pane Footer */}
        <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-t border-border text-xs shrink-0">
          <span className="text-muted-foreground text-xs">
            Số từ:{" "}
            <strong className="text-foreground">
              {pageData?.wordCount || 0}
            </strong>{" "}
            • Số dòng:{" "}
            <strong className="text-foreground">
              {pageData?.lineCount || 0}
            </strong>
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCopyContent(currentMarkdown)}
            className="h-7 text-xs gap-1"
            title="Sao chép toàn bộ nội dung"
          >
            {isCopied ? (
              <Check className="size-3 text-emerald-500" />
            ) : (
              <Copy className="size-3" />
            )}
            <span>{isCopied ? "Đã chép" : "Sao chép toàn bộ"}</span>
          </Button>
        </div>
      </Tabs>
    </div>
  );
};

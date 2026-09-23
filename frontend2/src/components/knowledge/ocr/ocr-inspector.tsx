import {
  Building2,
  Check,
  Copy,
  Edit3,
  FileSpreadsheet,
  Sparkles,
  Table2,
  Type,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import {
  ExcelSpreadsheetViewer,
  parseMarkdownTablesToSheets,
} from "@/components/admin/excel-spreadsheet-viewer";
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
  rightTab,
  onTabChange,
  markdownViewMode,
  onMarkdownViewModeChange,
  editableMarkdown,
  onMarkdownChange,
  onCopyContent,
  isCopied,
  isEditable = true,
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

  const spreadsheetSheets = useMemo(() => {
    if (!currentMarkdown) return [];
    return parseMarkdownTablesToSheets(currentMarkdown);
  }, [currentMarkdown]);

  const hasSpreadsheet = spreadsheetSheets.length > 0;

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
            <TabsTrigger value="entities" className="text-xs px-2.5 h-7 gap-1">
              <Sparkles className="size-3 text-primary" />
              <span>Thực thể</span>
            </TabsTrigger>
            <TabsTrigger value="markdown" className="text-xs px-2.5 h-7 gap-1">
              <Type className="size-3" />
              <span>Markdown</span>
            </TabsTrigger>
            {hasSpreadsheet && (
              <TabsTrigger
                value="excel"
                className="text-xs px-2.5 h-7 gap-1 text-emerald-600 dark:text-emerald-400"
              >
                <FileSpreadsheet className="size-3" />
                <span>Bảng tính ({spreadsheetSheets.length})</span>
              </TabsTrigger>
            )}
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
              <div className="flex items-center rounded-md border border-border bg-muted/30 p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => onMarkdownViewModeChange("rendered")}
                  className={`px-2 py-0.5 text-xs font-medium rounded transition-colors ${
                    markdownViewMode === "rendered"
                      ? "bg-background text-foreground shadow-2xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Xem đẹp
                </button>
                <button
                  type="button"
                  onClick={() => onMarkdownViewModeChange("raw")}
                  className={`px-2 py-0.5 text-xs font-medium rounded transition-colors ${
                    markdownViewMode === "raw"
                      ? "bg-background text-foreground shadow-2xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Mã nguồn
                </button>
                {isEditable && (
                  <button
                    type="button"
                    onClick={() => onMarkdownViewModeChange("edit")}
                    className={`px-2 py-0.5 text-xs font-medium rounded flex items-center gap-1 transition-colors ${
                      markdownViewMode === "edit"
                        ? "bg-primary text-primary-foreground shadow-2xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    title="Chỉnh sửa nội dung văn bản đối soát"
                  >
                    <Edit3 className="size-2.5" />
                    Sửa tay
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* TAB 1: EXTRACTED ENTITIES (Chuẩn QLKTX - Card & Field Structure) */}
        {rightTab === "entities" && (
          <div className="flex-1 overflow-auto p-4 space-y-4 select-text">
            {/* Card 1: Metadata Hành Chính */}
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
                      TRƯỜNG ĐẠI HỌC QUY NHƠN
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6 text-muted-foreground hover:text-foreground"
                      onClick={() =>
                        handleCopyValue(
                          "Cơ quan ban hành",
                          "TRƯỜNG ĐẠI HỌC QUY NHƠN",
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
                        .../TB-ĐHQN
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-foreground"
                        onClick={() =>
                          handleCopyValue("Số hiệu văn bản", "/TB-ĐHQN")
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
                        Thông báo
                      </Badge>
                    </div>
                  </Field>
                </div>

                <Field label="Trích yếu nội dung">
                  <div className="rounded-md border border-border/70 bg-muted/20 px-2.5 py-2">
                    <p className="font-medium text-foreground leading-relaxed">
                      THÔNG TIN TUYỂN SINH ĐẠI HỌC NĂM 2026 (CẬP NHẬT)
                    </p>
                  </div>
                </Field>

                <div className="grid grid-cols-2 gap-2">
                  <Field label="Hình thức đào tạo">
                    <div className="flex items-center h-8 px-2.5 rounded-md border border-border/70 bg-muted/20">
                      <span className="font-medium text-foreground">
                        Chính quy
                      </span>
                    </div>
                  </Field>

                  <Field label="Năm áp dụng">
                    <div className="flex items-center h-8 px-2.5 rounded-md border border-border/70 bg-muted/20">
                      <span className="font-mono font-medium text-foreground">
                        2026
                      </span>
                    </div>
                  </Field>
                </div>
              </CardContent>
            </Card>

            {/* Card 2: Dữ liệu Bảng biểu & Con số */}
            <Card className="rounded-lg border bg-card shadow-2xs">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex size-7 items-center justify-center rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      <Table2 className="size-3.5" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold">
                        Bảng Biểu & Dữ Liệu Số Hóa
                      </CardTitle>
                      <CardDescription className="text-xs text-muted-foreground">
                        Các bảng dữ liệu được nhận diện cấu trúc
                      </CardDescription>
                    </div>
                  </div>
                  {hasSpreadsheet && (
                    <Badge variant="outline" className="text-[10px]">
                      {spreadsheetSheets.length} Bảng
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-2 text-xs">
                {hasSpreadsheet ? (
                  <div className="space-y-2">
                    {spreadsheetSheets.map((sheet) => (
                      <div
                        key={sheet.name}
                        className="flex items-center justify-between p-2 rounded-md border border-border/70 bg-muted/20 hover:bg-muted/40 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <FileSpreadsheet className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                          <div>
                            <p className="font-medium text-foreground">
                              {sheet.name}
                            </p>
                            <p className="text-[11px] text-muted-foreground font-mono">
                              {sheet.rows.length} hàng •{" "}
                              {sheet.rows[0]?.length || sheet.totalCols || 0}{" "}
                              cột
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => onTabChange("excel")}
                        >
                          Mở bảng tính
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic py-2">
                    Không phát hiện bảng biểu cấu trúc trên trang này.
                  </p>
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

            {markdownViewMode === "edit" && (
              <div className="flex flex-col h-full space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Soạn thảo sửa tay nội dung trang đối soát:</span>
                  <Badge
                    variant="outline"
                    className="text-[10px] text-primary border-primary/30"
                  >
                    Human-in-the-loop
                  </Badge>
                </div>
                <textarea
                  value={currentMarkdown}
                  onChange={(e) => onMarkdownChange(e.target.value)}
                  className="w-full flex-1 min-h-[350px] p-3 font-mono text-xs rounded-md border border-border bg-background focus:ring-2 focus:ring-primary focus:outline-hidden leading-relaxed resize-none"
                  placeholder="Nhập hoặc chỉnh sửa nội dung văn bản sau OCR..."
                />
              </div>
            )}
          </div>
        )}

        {/* TAB 3: EXCEL SPREADSHEET */}
        {rightTab === "excel" && (
          <div className="flex-1 overflow-hidden p-2">
            <ExcelSpreadsheetViewer
              sheets={spreadsheetSheets}
              filename={`trang_${pageData?.pageNumber || 1}`}
              className="h-full"
            />
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

import {
  Building2,
  Check,
  Code,
  Copy,
  Eye,
  Layers,
  Pencil,
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
import { Textarea } from "@/components/ui/textarea";
import { SourceDraftFacts } from "./source-draft-facts";
import type { OcrInspectorProps, OcrRightTab } from "./types";

export const OcrInspector: React.FC<OcrInspectorProps> = ({
  pageData,
  allPages,
  citationMetadata,
  structuredArtifact,
  layoutTextAlignment,
  rightTab,
  onTabChange,
  markdownViewMode,
  onMarkdownViewModeChange,
  editableMarkdown,
  onMarkdownChange,
  selectedRegion: _selectedRegion,
  onSelectRegion: _onSelectRegion,
  onCopyContent,
  isCopied,
  isEditable = true,
}) => {
  const [fontSize, setFontSize] = useState<"sm" | "base">("sm");

  const currentMarkdown = editableMarkdown;

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

  // Read revision metadata from the backend; never invent entities from display geometry.
  const extractedEntities = useMemo(() => {
    const value = (key: string) => citationMetadata?.[key] || "Chưa xác định";
    const pages = allPages || (pageData ? [pageData] : []);
    return {
      agency: value("issuing_authority"),
      docNumber: value("document_number"),
      docType: value("document_type_code"),
      subject: value("subject"),
      locationAndDate: value("issued_date"),
      year: citationMetadata?.issued_date?.slice(0, 4) || "Chưa xác định",
      signerTitle: citationMetadata?.signer_title || "",
      signerName: citationMetadata?.signer_name || "",
      recipients: citationMetadata?.recipients || "",
      totalTables: structuredArtifact?.tables.length || 0,
      totalRegions: pages.reduce((sum, page) => sum + page.regions.length, 0),
    };
  }, [citationMetadata, structuredArtifact, allPages, pageData]);

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
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 border-b border-border bg-muted/20 shrink-0">
          <TabsList className="h-8 max-w-full shrink-0 bg-muted/60 p-0.5 rounded-md overflow-x-auto">
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
            <TabsTrigger
              value="regions"
              className="text-xs px-3 h-7 gap-1.5 font-medium"
            >
              <Layers className="size-3 text-primary" />
              <span>Vùng nhận diện</span>
            </TabsTrigger>
          </TabsList>

          {/* Right actions */}
          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFontSize(fontSize === "sm" ? "base" : "sm")}
              className="px-1.5 py-0.5 text-muted-foreground hover:text-foreground rounded transition-colors text-xs font-serif border border-transparent hover:border-border"
              title="Thay đổi cỡ chữ"
            >
              Aa
            </Button>

            {rightTab === "markdown" && (
              <div className="flex items-center rounded-md border border-border bg-muted/30 p-0.5 text-xs shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
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
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
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
                </Button>
                {isEditable && (
                  <Button
                    variant={
                      markdownViewMode === "edit" ? "secondary" : "ghost"
                    }
                    size="sm"
                    className="h-7 px-2 gap-1"
                    onClick={() => onMarkdownViewModeChange("edit")}
                  >
                    <Pencil className="size-3" /> Sửa
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* TAB 1: EXTRACTED ENTITIES (Bóc tách dữ liệu động chuẩn Nghị định 30) */}
        {rightTab === "entities" && (
          <div className="flex-1 overflow-auto p-4 space-y-4 select-text">
            {layoutTextAlignment === "stale" && (
              <p className="text-xs text-warning">
                Khung thuộc tệp gốc, chưa khớp lại với Markdown đã hiệu đính.
              </p>
            )}
            {/* Card 1: Metadata Hành Chính Động */}
            <SourceDraftFacts artifact={structuredArtifact} />
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
                        Metadata đã lưu theo bản nguồn; trường thiếu không được
                        suy đoán
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant="success" className="text-[10px]">
                    Metadata nguồn
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

                  <Field label="Năm ban hành">
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
            {markdownViewMode === "edit" && isEditable && (
              <Textarea
                aria-label="Hiệu đính Markdown của trang"
                value={editableMarkdown}
                onChange={(event) => onMarkdownChange(event.target.value)}
                className="min-h-[400px] h-full font-mono text-sm leading-relaxed"
              />
            )}
          </div>
        )}

        {/* TAB 3: REGIONS (Đối soát 2 chiều khung <-> nội dung) */}
        {rightTab === "regions" && (
          <div className="flex-1 overflow-auto p-4 space-y-3 select-text">
            {!pageData?.regions || pageData.regions.length === 0 ? (
              <div className="py-12 text-center text-xs text-muted-foreground">
                Không có dữ liệu vùng nhận diện trên trang này.
              </div>
            ) : (
              pageData.regions.map((region, idx) => {
                const isSelected = _selectedRegion === region;
                const layoutConf = region.layoutConfidence;
                const textConf = region.textConfidence;

                return (
                  <Button
                    variant="ghost"
                    key={
                      region.id ||
                      `${region.label}-${region.top}-${region.left}`
                    }
                    onClick={() => _onSelectRegion?.(region)}
                    className={`block h-auto w-full whitespace-normal text-left p-3 rounded-lg border text-xs cursor-pointer transition-all space-y-2 ${
                      isSelected
                        ? "border-primary bg-primary/5 shadow-xs ring-1 ring-primary/30"
                        : "border-border bg-card hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono"
                        >
                          #{idx + 1}
                        </Badge>
                        <span className="font-semibold text-foreground">
                          {region.label || "Khối văn bản"}
                        </span>
                      </div>
                      <Badge
                        variant="secondary"
                        className="text-[10px] font-mono"
                      >
                        {region.type}
                      </Badge>
                    </div>

                    <p className="text-xs text-foreground/90 font-mono whitespace-pre-wrap leading-relaxed bg-muted/20 p-2 rounded border border-border/50">
                      {region.text || "(Trống)"}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/40">
                      <span>
                        Khung nhận diện:{" "}
                        <strong className="text-foreground">
                          {typeof layoutConf === "number"
                            ? `${Math.round(layoutConf * 100)}%`
                            : "—"}
                        </strong>
                      </span>
                      <span>
                        Nhận dạng chữ (OCR):{" "}
                        <strong className="text-foreground">
                          {typeof textConf === "number"
                            ? `${Math.round(textConf * 100)}%`
                            : "Không được cung cấp"}
                        </strong>
                      </span>
                    </div>
                  </Button>
                );
              })
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

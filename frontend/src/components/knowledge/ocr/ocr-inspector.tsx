import {
  ExcelSpreadsheetViewer,
  parseMarkdownTablesToSheets,
} from "@/components/admin/excel-spreadsheet-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Check, Copy, Edit3, FileCode, FileSpreadsheet, FileText, Layers } from "lucide-react";
import type React from "react";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { type OcrInspectorProps, type OcrRightTab, REGION_COLORS } from "./types";

export const OcrInspector: React.FC<OcrInspectorProps> = ({
  pageData,
  rightTab,
  onTabChange,
  markdownViewMode,
  onMarkdownViewModeChange,
  editableMarkdown,
  onMarkdownChange,
  selectedRegion,
  onSelectRegion,
  onCopyContent,
  isCopied,
  isEditable = true,
}) => {
  const currentMarkdown = editableMarkdown || pageData?.markdown || "";

  const spreadsheetSheets = useMemo(() => {
    if (!currentMarkdown) return [];
    return parseMarkdownTablesToSheets(currentMarkdown);
  }, [currentMarkdown]);

  const hasSpreadsheet = spreadsheetSheets.length > 0;

  return (
    <div className="flex flex-col h-full bg-card border border-border rounded-lg overflow-hidden shadow-xs">
      <Tabs
        value={rightTab}
        onValueChange={(val) => onTabChange(val as OcrRightTab)}
        className="flex flex-col h-full"
      >
        {/* Tab Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/40 shrink-0">
          <TabsList className="h-7 bg-muted">
            <TabsTrigger value="markdown" className="text-xs px-2.5 h-6 gap-1">
              <FileText className="size-3" />
              <span>Markdown</span>
            </TabsTrigger>
            {hasSpreadsheet && (
              <TabsTrigger
                value="excel"
                className="text-xs px-2.5 h-6 gap-1 text-emerald-600 dark:text-emerald-400"
              >
                <FileSpreadsheet className="size-3" />
                <span>Bảng tính ({spreadsheetSheets.length})</span>
              </TabsTrigger>
            )}
            <TabsTrigger value="regions" className="text-xs px-2.5 h-6 gap-1">
              <Layers className="size-3" />
              <span>Vùng ({pageData?.regions.length || 0})</span>
            </TabsTrigger>
            <TabsTrigger value="json" className="text-xs px-2.5 h-6 gap-1">
              <FileCode className="size-3" />
              <span>JSON</span>
            </TabsTrigger>
          </TabsList>

          {/* View Mode Toggle for Markdown Tab */}
          {rightTab === "markdown" && (
            <div className="flex items-center rounded-md border border-border bg-background p-0.5">
              <button
                type="button"
                onClick={() => onMarkdownViewModeChange("rendered")}
                className={`px-2 py-0.5 text-xs font-medium rounded transition-colors ${
                  markdownViewMode === "rendered"
                    ? "bg-primary text-primary-foreground"
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
                    ? "bg-primary text-primary-foreground"
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
                      ? "bg-primary text-primary-foreground"
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

        {/* TAB 1: MARKDOWN */}
        {rightTab === "markdown" && (
          <div className="flex-1 overflow-auto p-4 text-xs">
            {markdownViewMode === "rendered" && (
              <div className="prose prose-xs dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {currentMarkdown || "(Trang không có nội dung)"}
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
                  <Badge variant="outline" className="text-[10px] text-primary border-primary/30">
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

        {/* TAB 2: EXCEL SPREADSHEET */}
        {rightTab === "excel" && (
          <div className="flex-1 overflow-hidden p-2">
            <ExcelSpreadsheetViewer
              sheets={spreadsheetSheets}
              filename={`trang_${pageData?.pageNumber || 1}`}
              className="h-full"
            />
          </div>
        )}

        {/* TAB 3: REGIONS INSPECTOR */}
        {rightTab === "regions" && (
          <div className="flex-1 overflow-auto p-3 space-y-2">
            {pageData?.regions && pageData.regions.length > 0 ? (
              pageData.regions.map((reg, idx) => {
                const colorStyle = REGION_COLORS[reg.type] || REGION_COLORS.text;
                const isSelected = selectedRegion === reg;
                const regKey = `reg-card-${reg.type}-${idx}-${reg.top}`;
                return (
                  <Card
                    key={regKey}
                    onClick={() => onSelectRegion(reg)}
                    className={`cursor-pointer transition-all border ${
                      isSelected
                        ? "border-primary ring-1 ring-primary bg-primary/5"
                        : "hover:border-border/80"
                    }`}
                  >
                    <CardContent className="p-2.5 space-y-1">
                      <div className="flex items-center justify-between">
                        <Badge
                          variant="outline"
                          className="text-[10px] font-semibold uppercase px-1.5 py-0"
                          style={{ borderColor: colorStyle.border, color: colorStyle.text }}
                        >
                          {reg.type}
                        </Badge>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {reg.top.toFixed(1)}% T • {reg.left.toFixed(1)}% L •{" "}
                          {reg.width.toFixed(1)}% W
                        </span>
                      </div>
                      <p className="text-xs text-foreground/90 font-medium line-clamp-2">
                        {reg.text || `(Vùng ${reg.label})`}
                      </p>
                    </CardContent>
                  </Card>
                );
              })
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                <p className="text-xs">Không phát hiện vùng bố cục nào trên trang này.</p>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: JSON AST */}
        {rightTab === "json" && (
          <div className="flex-1 overflow-auto p-3">
            <pre className="font-mono text-[11px] p-3 bg-muted/40 rounded-md border border-border whitespace-pre-wrap select-text leading-tight text-foreground/80">
              {JSON.stringify(pageData, null, 2)}
            </pre>
          </div>
        )}

        {/* Right Pane Footer */}
        <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-t border-border text-xs shrink-0">
          <span className="text-muted-foreground text-xs">
            Số từ: <strong className="text-foreground">{pageData?.wordCount || 0}</strong> • Số
            dòng: <strong className="text-foreground">{pageData?.lineCount || 0}</strong>
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCopyContent(currentMarkdown)}
            className="h-7 text-xs gap-1"
            title="Sao chép nội dung Markdown"
          >
            {isCopied ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3" />}
            <span>{isCopied ? "Đã chép" : "Sao chép"}</span>
          </Button>
        </div>
      </Tabs>
    </div>
  );
};

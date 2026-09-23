import {
  Check,
  Copy,
  FileSpreadsheet,
  Search,
  Sliders,
  Table as TableIcon,
  X,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface ExcelSheetData {
  name: string;
  rows: string[][];
  total_rows?: number;
  total_cols?: number;
  totalRows?: number;
  totalCols?: number;
}

export interface ExcelSpreadsheetViewerProps {
  sheets: ExcelSheetData[];
  filename?: string;
  activeSheetIndex?: number;
  onSheetChange?: (index: number) => void;
  className?: string;
}

function getExcelColumnLetter(colIndex: number): string {
  let temp = colIndex;
  let letter = "";
  while (temp >= 0) {
    letter = String.fromCharCode((temp % 26) + 65) + letter;
    temp = Math.floor(temp / 26) - 1;
  }
  return letter;
}

function isNumericValue(val: string): boolean {
  if (!val || typeof val !== "string") return false;
  const clean = val.trim().replace(/,/g, "");
  return !Number.isNaN(Number(clean)) && clean !== "";
}

export function parseMarkdownTablesToSheets(
  markdown: string,
  defaultName = "Sheet1",
): ExcelSheetData[] {
  if (!markdown) return [];
  const lines = markdown.split("\n");
  const resultSheets: ExcelSheetData[] = [];
  let currentRows: string[][] = [];
  let currentSheetName = defaultName;

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (
      (line.startsWith("<!--") && line.toLowerCase().includes("trang")) ||
      line.startsWith("## ") ||
      line.startsWith("### ") ||
      line.toLowerCase().includes("sheet")
    ) {
      if (currentRows.length > 0) {
        const maxCols = Math.max(...currentRows.map((r) => r.length), 1);
        const padded = currentRows.map((r) =>
          r.concat(Array(maxCols - r.length).fill("")),
        );
        resultSheets.push({
          name: currentSheetName,
          rows: padded,
          total_rows: padded.length,
          total_cols: maxCols,
          totalRows: padded.length,
          totalCols: maxCols,
        });
        currentRows = [];
      }
      const cleanName = line.replace(/[<>\-!#*]/g, "").trim();
      if (cleanName) {
        currentSheetName = cleanName;
      }
      continue;
    }

    if (line.startsWith("|") && line.endsWith("|")) {
      if (/^\|[\s\-:]+(\|[\s\-:]+)+\|$/.test(line)) {
        continue;
      }
      const cells = line
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim().replace(/<br\s*\/?>/gi, " "));
      if (cells.some((c) => c.length > 0)) {
        currentRows.push(cells);
      }
    }
  }

  if (currentRows.length > 0) {
    const maxCols = Math.max(...currentRows.map((r) => r.length), 1);
    const padded = currentRows.map((r) =>
      r.concat(Array(maxCols - r.length).fill("")),
    );
    resultSheets.push({
      name: currentSheetName,
      rows: padded,
      total_rows: padded.length,
      total_cols: maxCols,
      totalRows: padded.length,
      totalCols: maxCols,
    });
  }

  return resultSheets;
}

export const ExcelSpreadsheetViewer: React.FC<ExcelSpreadsheetViewerProps> = ({
  sheets,
  filename,
  activeSheetIndex,
  onSheetChange,
  className = "",
}) => {
  const [internalSheetIdx, setInternalSheetIdx] = useState(0);
  const activeSheetIdx =
    activeSheetIndex !== undefined ? activeSheetIndex : internalSheetIdx;

  const handleSelectSheet = (idx: number) => {
    setInternalSheetIdx(idx);
    if (onSheetChange) {
      onSheetChange(idx);
    }
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCell, setSelectedCell] = useState<{
    r: number;
    c: number;
    val: string;
  } | null>(null);
  const [isCompact, setIsCompact] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const safeSheets = useMemo(() => {
    if (!sheets || sheets.length === 0) {
      return [
        {
          name: "Sheet1",
          rows: [["(Bảng tính trống)"]],
          total_rows: 1,
          total_cols: 1,
          totalRows: 1,
          totalCols: 1,
        },
      ];
    }
    return sheets;
  }, [sheets]);

  const currentSheet = useMemo(() => {
    return safeSheets[activeSheetIdx] || safeSheets[0];
  }, [safeSheets, activeSheetIdx]);

  const maxColumns = useMemo(() => {
    if (!currentSheet.rows || currentSheet.rows.length === 0) return 1;
    return Math.max(...currentSheet.rows.map((r) => r.length), 1);
  }, [currentSheet]);

  const handleCopyCell = () => {
    if (!selectedCell?.val) return;
    navigator.clipboard.writeText(selectedCell.val);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 1500);
  };

  const handleCopyAsCsv = () => {
    if (!currentSheet.rows || currentSheet.rows.length === 0) return;
    const csvContent = currentSheet.rows
      .map((row) =>
        row
          .map((cell) => {
            const escaped = cell.replace(/"/g, '""');
            return `"${escaped}"`;
          })
          .join(","),
      )
      .join("\n");
    navigator.clipboard.writeText(csvContent);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 1500);
  };

  return (
    <div
      className={`flex flex-col h-full w-full bg-card rounded-lg border border-border overflow-hidden text-xs ${className}`}
    >
      {/* 1. TOP TOOLBAR */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-b border-border gap-2 flex-wrap min-h-10">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center justify-center size-7 rounded-md bg-primary/10 text-primary shrink-0 border border-primary/20">
            <FileSpreadsheet className="size-4" />
          </div>
          <span
            className="font-bold text-foreground truncate max-w-56"
            title={filename || currentSheet.name}
          >
            {filename || currentSheet.name}
          </span>
          <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
            {currentSheet.name}
          </Badge>
          <span className="text-muted-foreground whitespace-nowrap text-[11px]">
            ({currentSheet.total_rows || currentSheet.rows.length} hàng ×{" "}
            {maxColumns} cột)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Search bar */}
          <div className="relative w-44">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Tìm ô..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-7 pl-7 pr-6 text-xs bg-background"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            )}
          </div>

          {/* Density toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCompact(!isCompact)}
            className="size-7 text-muted-foreground hover:text-foreground"
            title={isCompact ? "Chế độ vừa phải" : "Chế độ nén hàng"}
          >
            <Sliders className="size-3.5" />
          </Button>

          {/* Copy CSV */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyAsCsv}
            className="h-7 text-xs px-2 gap-1 text-muted-foreground hover:text-foreground"
            title="Sao chép toàn bộ bảng dạng CSV"
          >
            {isCopied ? (
              <Check className="size-3 text-emerald-500" />
            ) : (
              <Copy className="size-3" />
            )}
            <span>{isCopied ? "Đã chép" : "Chép CSV"}</span>
          </Button>
        </div>
      </div>

      {/* 2. FORMULA / SELECTED CELL BAR */}
      <div className="flex items-center gap-2 px-3 py-1 bg-muted/20 border-b border-border/80 text-[11px]">
        <div className="flex items-center gap-1 font-mono font-bold text-primary min-w-14">
          <TableIcon className="size-3" />
          <span>
            {selectedCell
              ? `${getExcelColumnLetter(selectedCell.c)}${selectedCell.r + 1}`
              : "A1"}
          </span>
        </div>
        <div className="h-3 w-px bg-border shrink-0" />
        <div className="flex-1 font-mono truncate text-muted-foreground">
          {selectedCell ? (
            <span className="text-foreground">{selectedCell.val}</span>
          ) : (
            <span className="italic">
              Bấm vào bất kỳ ô nào để xem và sao chép
            </span>
          )}
        </div>
        {selectedCell && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopyCell}
            className="size-5 shrink-0 text-muted-foreground hover:text-primary"
            title="Sao chép nội dung ô này"
          >
            <Copy className="size-3" />
          </Button>
        )}
      </div>

      {/* 3. SPREADSHEET GRID CANVAS */}
      <div className="flex-1 overflow-auto bg-background select-text">
        <table className="min-w-full border-collapse text-left font-sans">
          <thead>
            <tr className="sticky top-0 z-10 bg-muted text-muted-foreground font-semibold border-b border-border shadow-xs">
              {/* Row number corner header */}
              <th className="w-10 px-2 py-1 text-center font-mono text-[10px] border-r border-border bg-muted/90 select-none">
                #
              </th>
              {Array.from({ length: maxColumns }).map((_, cIdx) => (
                <th
                  key={`header-col-${getExcelColumnLetter(cIdx)}`}
                  className="px-3 py-1 text-center font-mono text-[11px] border-r border-border min-w-24 whitespace-nowrap select-none bg-muted/80"
                >
                  {getExcelColumnLetter(cIdx)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {currentSheet.rows.map((row, rIdx) => {
              const isMatchSearch =
                searchQuery &&
                row.some((cell) =>
                  cell.toLowerCase().includes(searchQuery.toLowerCase()),
                );

              return (
                <tr
                  key={`row-${rIdx + 1}`}
                  className={`border-b border-border/60 hover:bg-muted/30 transition-colors ${
                    isMatchSearch
                      ? "bg-amber-500/10"
                      : rIdx % 2 === 1
                        ? "bg-muted/10"
                        : ""
                  }`}
                >
                  {/* Row index label */}
                  <td className="w-10 px-2 py-1 text-center font-mono text-[10px] text-muted-foreground border-r border-border bg-muted/40 select-none">
                    {rIdx + 1}
                  </td>
                  {Array.from({ length: maxColumns }).map((_, cIdx) => {
                    const val = row[cIdx] || "";
                    const isSelected =
                      selectedCell?.r === rIdx && selectedCell?.c === cIdx;
                    const isCellMatch =
                      searchQuery &&
                      val.toLowerCase().includes(searchQuery.toLowerCase());
                    const isNum = isNumericValue(val);
                    const colLetter = getExcelColumnLetter(cIdx);

                    return (
                      <td
                        key={`cell-${currentSheet.name}-r${rIdx + 1}-c${colLetter}`}
                        className="p-0 border-r border-border/60"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedCell({ r: rIdx, c: cIdx, val })
                          }
                          className={`w-full h-full transition-all cursor-cell max-w-72 truncate block ${
                            isCompact
                              ? "px-2 py-0.5 text-[11px]"
                              : "px-3 py-1.5 text-xs"
                          } ${isNum ? "text-right font-mono" : "text-left"} ${
                            isSelected
                              ? "ring-2 ring-primary ring-inset bg-primary/10 font-semibold"
                              : ""
                          } ${isCellMatch ? "bg-amber-400/25 text-amber-950 dark:text-amber-200" : ""}`}
                          title={val}
                        >
                          {val || "\u00A0"}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 4. BOTTOM SHEET TABS BAR */}
      <div className="flex items-center justify-between px-3 py-1 bg-muted/60 border-t border-border gap-1 shrink-0 overflow-x-auto">
        <div className="flex items-center gap-1">
          {safeSheets.map((sh, idx) => {
            const isActive = idx === activeSheetIdx;
            return (
              <button
                key={`sheet-tab-${sh.name}`}
                type="button"
                onClick={() => handleSelectSheet(idx)}
                className={`px-3 py-1 rounded-t-sm font-semibold transition-all border-b-2 text-[11px] flex items-center gap-1.5 ${
                  isActive
                    ? "bg-card border-primary text-primary shadow-xs"
                    : "text-muted-foreground border-transparent hover:text-foreground hover:bg-muted"
                }`}
              >
                <TableIcon className="size-3" />
                <span>{sh.name}</span>
                <span className="text-[10px] text-muted-foreground/80 font-mono">
                  ({sh.rows.length})
                </span>
              </button>
            );
          })}
        </div>

        <div className="text-[11px] text-muted-foreground whitespace-nowrap">
          Đang xem sheet:{" "}
          <strong className="text-foreground">{currentSheet.name}</strong>
        </div>
      </div>
    </div>
  );
};

import { ChevronDown, Table as TableIcon, Tag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { LiteralTableEntry } from "./compilation-types";

export function SourceTablesView({
  tables,
  onSelectCitation,
  deferContent = false,
}: {
  tables: (Omit<LiteralTableEntry, "page_number"> & { page_number?: number })[];
  onSelectCitation?: (citation: string) => void;
  deferContent?: boolean;
}) {
  if (!tables || tables.length === 0) {
    return (
      <div className="text-center py-6 text-xs text-muted-foreground italic">
        Không có bảng nguồn nào được đính kèm trong bản biên soạn này.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {tables.map((entry, index) => {
        return (
          <Collapsible
            key={entry.citation || index}
            defaultOpen={!deferContent}
            asChild
          >
            <Card className="rounded-xl shadow-2xs overflow-hidden">
              <CardHeader className="p-3 sm:p-4 bg-muted/20 border-b flex flex-row flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <TableIcon className="size-4 text-primary shrink-0" />
                  <CardTitle className="text-xs font-semibold">
                    {deferContent ? (
                      <CollapsibleTrigger asChild>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="gap-2"
                        >
                          Bảng nguồn {index + 1}
                          <ChevronDown className="size-3.5" />
                        </Button>
                      </CollapsibleTrigger>
                    ) : (
                      `Bảng nguồn #${index + 1}`
                    )}
                  </CardTitle>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    Trang {entry.page_number ?? "chưa xác định"}
                  </Badge>
                </div>

                {entry.citation && onSelectCitation && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => onSelectCitation?.(entry.citation)}
                    className="gap-1 text-xs text-primary"
                    aria-label={`Xem dẫn chứng bảng nguồn ${index + 1}`}
                  >
                    <Tag className="size-3" />
                    <span>Dẫn chứng</span>
                  </Button>
                )}
              </CardHeader>

              <CollapsibleContent>
                <CardContent className="p-0 overflow-x-auto">
                  <table className="w-full border-collapse text-xs">
                    <tbody>
                      {entry.table.rows.map((row, rowIndex) => (
                        <tr
                          // biome-ignore lint/suspicious/noArrayIndexKey: sequential matrix rows
                          key={`row-${entry.citation}-${rowIndex}`}
                          className="border-b last:border-b-0 hover:bg-muted/10 transition-colors"
                        >
                          {row.map((cell, cellIndex) => {
                            const TagName = cell.header ? "th" : "td";
                            return (
                              <TagName
                                // biome-ignore lint/suspicious/noArrayIndexKey: sequential matrix cells
                                key={`cell-${entry.citation}-${rowIndex}-${cellIndex}`}
                                rowSpan={
                                  cell.row_span > 1 ? cell.row_span : undefined
                                }
                                colSpan={
                                  cell.col_span > 1 ? cell.col_span : undefined
                                }
                                className={`p-2 border-r last:border-r-0 text-left align-top ${
                                  cell.header
                                    ? "bg-muted/40 font-semibold text-foreground text-[11px]"
                                    : "text-muted-foreground"
                                }`}
                              >
                                <span className="whitespace-pre-wrap font-sans">
                                  {cell.text}
                                </span>
                              </TagName>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        );
      })}
    </div>
  );
}

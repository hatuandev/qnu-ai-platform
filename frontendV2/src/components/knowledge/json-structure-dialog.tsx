import { Check, Copy, Download, FileJson, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface JsonStructureDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  data: unknown;
  fileName?: string;
}

export function JsonStructureDialog({
  open,
  onOpenChange,
  title = "Cấu trúc dữ liệu có định dạng JSON",
  data,
  fileName = "document-data.json",
}: JsonStructureDialogProps) {
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const formattedJson = useMemo(() => {
    if (!data) return "{}";
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson);
      setCopied(true);
      toast.success("Đã sao chép nội dung JSON!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Không thể sao chép vào bộ nhớ tạm.");
    }
  };

  const handleDownload = () => {
    const blob = new Blob([formattedJson], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName.endsWith(".json") ? fileName : `${fileName}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Đã tải tệp JSON về máy.");
  };

  // Filter json lines if searchQuery is present
  const displayLines = useMemo(() => {
    const lines = formattedJson.split("\n");
    if (!searchQuery.trim()) return lines;
    const q = searchQuery.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(q));
  }, [formattedJson, searchQuery]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col p-6 gap-4">
        <DialogHeader className="shrink-0 space-y-1">
          <div className="flex items-center gap-2">
            <FileJson className="size-5 text-primary" />
            <DialogTitle className="text-base font-semibold">
              {title}
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Dữ liệu có cấu trúc thật từ hệ thống bao gồm các đoạn văn, bảng dữ
            liệu, căn cứ truy vết (citations) và chỉ mục phiên bản.
          </DialogDescription>
        </DialogHeader>

        {/* Search bar & Actions */}
        <div className="flex items-center justify-between gap-3 shrink-0">
          <div className="relative flex-1 max-w-sm">
            <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm khóa, giá trị hoặc căn cứ..."
              className="h-8 pl-8 text-xs"
            />
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="h-8 text-xs gap-1.5"
            >
              {copied ? (
                <Check className="size-3.5 text-emerald-600" />
              ) : (
                <Copy className="size-3.5" />
              )}
              <span>{copied ? "Đã chép" : "Sao chép JSON"}</span>
            </Button>

            <Button
              variant="default"
              size="sm"
              onClick={handleDownload}
              className="h-8 text-xs gap-1.5 shadow-2xs"
            >
              <Download className="size-3.5" />
              <span>Tải tệp JSON</span>
            </Button>
          </div>
        </div>

        {/* JSON Content Canvas */}
        <div className="flex-1 min-h-[300px] overflow-y-auto rounded-xl border border-border/70 bg-muted/30 p-4 text-xs font-mono select-text leading-relaxed">
          {searchQuery && displayLines.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              Không tìm thấy dòng nào khớp với từ khóa "{searchQuery}"
            </div>
          ) : (
            <pre className="whitespace-pre-wrap break-words text-foreground/90">
              {displayLines.join("\n")}
            </pre>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

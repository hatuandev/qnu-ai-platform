import {
  Building2,
  Check,
  Copy,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  Scale,
  Settings,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import type {
  DocumentTypeCategory,
  DocumentTypeItem,
} from "@/services/document-types-api";

interface DocumentTypeCardProps {
  item: DocumentTypeItem;
  onOpen: () => void;
  onToggleActive?: (active: boolean) => void;
  isToggling?: boolean;
}

export function getCategoryIcon(category: DocumentTypeCategory) {
  switch (category) {
    case "legal_internal":
      return Scale;
    case "administrative":
      return Building2;
    case "academic":
      return GraduationCap;
    case "forms":
      return FileSpreadsheet;
    default:
      return FileText;
  }
}

export function formatCategoryLabel(category: DocumentTypeCategory): string {
  switch (category) {
    case "legal_internal":
      return "Quy phạm & Nội bộ";
    case "administrative":
      return "Hành chính Điều hành";
    case "academic":
      return "Đào tạo & Học thuật";
    case "forms":
      return "Biểu mẫu & Tiếp nhận";
    default:
      return "Khác";
  }
}

export function DocumentTypeCard({
  item,
  onOpen,
  onToggleActive,
  isToggling,
}: DocumentTypeCardProps) {
  const Icon = getCategoryIcon(item.category);

  const handleCopyCode = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(item.code);
      toast.success(`Đã sao chép mã “${item.code}”!`);
    } catch {
      toast.error("Không thể sao chép mã.");
    }
  };

  return (
    <Card className="group flex h-full flex-col border-border/80 transition-all hover:border-primary/50 hover:shadow-xs">
      <CardHeader className="space-y-2 p-3.5 sm:p-4 pb-2 sm:pb-2.5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform group-hover:scale-105">
              <Icon className="size-4.5" />
            </div>
            <div className="min-w-0">
              <CardTitle
                className="text-sm font-bold text-foreground line-clamp-1 group-hover:text-primary transition-colors cursor-pointer"
                onClick={onOpen}
              >
                {item.name}
              </CardTitle>
              <div className="flex items-center gap-1.5 mt-0.5">
                <button
                  type="button"
                  onClick={handleCopyCode}
                  title="Sao chép mã thể thức"
                  className="inline-flex items-center gap-1 font-mono text-[10px] text-muted-foreground hover:text-primary transition-colors bg-muted/60 hover:bg-primary/10 px-1.5 py-0.5 rounded cursor-pointer group/code"
                >
                  <span className="truncate">{item.code}</span>
                  <Copy className="size-2.5 opacity-60 group-hover/code:opacity-100 shrink-0" />
                </button>
                <Badge
                  variant="outline"
                  className="text-[9px] px-1 py-0 h-4 shrink-0"
                >
                  {formatCategoryLabel(item.category)}
                </Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <Switch
              checked={item.is_active}
              disabled={isToggling}
              onCheckedChange={(checked) => onToggleActive?.(checked)}
              aria-label={`Trạng thái ${item.name}`}
            />
          </div>
        </div>

        <CardDescription className="line-clamp-2 text-xs leading-relaxed text-muted-foreground min-h-0 sm:min-h-8">
          {item.description ||
            "Chưa có hướng dẫn thể thức chi tiết cho loại văn bản này."}
        </CardDescription>
      </CardHeader>

      <CardContent className="mt-auto space-y-2 p-3.5 sm:p-4 pt-0">
        {/* Badges strip */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          {item.nd30 ? (
            <Badge
              variant="secondary"
              className="bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/20 text-[9px] gap-1 h-4.5 px-1.5 font-medium"
            >
              <Check className="size-2.5" />
              <span>NĐ 30/2020</span>
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="text-[9px] h-4.5 px-1.5 text-muted-foreground"
            >
              Nội bộ QNU
            </Badge>
          )}

          {item.is_custom ? (
            <Badge
              variant="outline"
              className="text-[9px] h-4.5 px-1.5 text-amber-600 dark:text-amber-400 border-amber-500/30"
            >
              Tùy chỉnh
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="text-[9px] h-4.5 px-1.5 text-muted-foreground"
            >
              Mặc định
            </Badge>
          )}
        </div>

        {/* Specs grid */}
        <div className="grid gap-1.5 border-t border-border/70 pt-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              Ưu tiên RAG:
            </span>
            <span className="font-mono text-[11px] font-semibold text-primary">
              Mức {item.priority}/10
            </span>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">Lưu trữ:</span>
            <span className="truncate text-[11px] font-medium text-foreground">
              {item.retention_period || "Theo quy định"}
            </span>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">Tài liệu:</span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {item.doc_count || 0} văn bản
            </span>
          </div>
        </div>

        {/* Action Button - 1 nút duy nhất, rõ nghĩa và phẳng phiu */}
        <div className="pt-1">
          <Button
            variant="outline"
            size="sm"
            className="h-8 w-full text-xs gap-1.5 border-primary/20 text-primary hover:bg-primary/10 hover:border-primary/40 font-medium"
            onClick={onOpen}
            title="Xem chi tiết và cấu hình thể thức văn bản"
          >
            <Settings className="size-3.5 shrink-0" />
            <span>Chi tiết</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

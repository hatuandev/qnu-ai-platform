import {
  CheckCircle2,
  FileCheck2,
  Heading,
  Layers,
  ListOrdered,
  Sparkles,
  Stamp,
  Table,
} from "lucide-react";
import type React from "react";
import type { DocumentRegion } from "../../services/api-client";
import { Badge } from "../ui/badge";

export interface RegionsInspectorProps {
  currentPage: number;
  regions: DocumentRegion[];
  activeRegionId?: string | null;
  onSelectRegion?: (regionId: string) => void;
}

export const RegionsInspector: React.FC<RegionsInspectorProps> = ({
  currentPage,
  regions,
  activeRegionId,
  onSelectRegion,
}) => {
  const currentRegions = regions.filter((r) => r.page_number === currentPage);

  const getRegionIcon = (type: string) => {
    switch (type) {
      case "header":
        return <Heading className="size-3.5 text-blue-500" />;
      case "title":
        return <Sparkles className="size-3.5 text-purple-500" />;
      case "table":
        return <Table className="size-3.5 text-amber-500" />;
      case "list":
        return <ListOrdered className="size-3.5 text-emerald-500" />;
      case "stamp":
      case "signature":
        return <Stamp className="size-3.5 text-rose-500" />;
      default:
        return <FileCheck2 className="size-3.5 text-purple-500" />;
    }
  };

  const getRegionBadge = (type: string) => {
    switch (type) {
      case "header":
        return (
          <Badge variant="outline" className="text-[10px] text-blue-600 border-blue-200">
            Tiêu đề đầu
          </Badge>
        );
      case "title":
        return (
          <Badge variant="outline" className="text-[10px] text-purple-600 border-purple-200">
            Tiêu đề
          </Badge>
        );
      case "table":
        return (
          <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-200">
            Bảng biểu
          </Badge>
        );
      case "list":
        return (
          <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-200">
            Danh sách
          </Badge>
        );
      case "stamp":
      case "signature":
        return (
          <Badge variant="outline" className="text-[10px] text-rose-600 border-rose-200">
            Dấu & Ký
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-[10px] text-purple-600 border-purple-200">
            Đoạn văn
          </Badge>
        );
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden bg-background">
      {/* Header info */}
      <div className="p-3 border-b border-border bg-card/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <Layers className="size-4 text-primary" />
            <span>Phân Đoạn Vùng Bố Cục (Layout & Regions)</span>
          </div>
          <Badge variant="secondary" className="font-mono text-[10px]">
            {currentRegions.length} Khối vùng
          </Badge>
        </div>
        <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">
          Thị giác máy tính (Docling LayoutLM) tự động nhận diện vùng quan tâm (ROI), sắp xếp thứ tự
          đọc và loại trừ ký tự rác từ con dấu scan.
        </p>
      </div>

      {/* Regions List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {currentRegions.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted-foreground">
            Không có khối vùng nào trên trang này.
          </div>
        ) : (
          currentRegions.map((region) => {
            const isSelected = activeRegionId === region.id;
            const confidencePercent = Math.round(region.confidence * 100);

            return (
              <button
                type="button"
                key={region.id}
                onClick={() => onSelectRegion?.(region.id)}
                className={`p-3 rounded-surface border transition-all cursor-pointer text-left w-full ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border hover:border-primary/40 bg-card"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="flex size-5 items-center justify-center rounded-full bg-muted font-mono text-[10px] font-bold text-foreground">
                      #{region.reading_order}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {getRegionIcon(region.type)}
                      <span className="text-xs font-semibold text-foreground">{region.title}</span>
                    </div>
                  </div>
                  {getRegionBadge(region.type)}
                </div>

                <p className="text-[11px] text-muted-foreground mt-2 pl-7 leading-relaxed">
                  {region.details}
                </p>

                <div className="flex items-center justify-between pl-7 mt-2 pt-2 border-t border-border/50 text-[10px]">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Sparkles className="size-3 text-amber-500" />
                    Thứ tự đọc: Luồng #{region.reading_order}
                  </span>
                  <span className="font-mono text-emerald-600 font-semibold flex items-center gap-0.5">
                    <CheckCircle2 className="size-3" />
                    Độ tin cậy OCR: {confidencePercent}%
                  </span>
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* Footer hint */}
      <div className="p-2.5 bg-muted/30 border-t border-border text-[11px] text-muted-foreground text-center">
        💡 Click vào từng khối vùng để highlight đối soát trực tiếp trên trang scan gốc.
      </div>
    </div>
  );
};

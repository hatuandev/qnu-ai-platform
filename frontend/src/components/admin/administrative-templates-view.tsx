import {
  ArrowRight,
  BookOpen,
  Check,
  Code2,
  Copy,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Layers,
  Search,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import {
  ADMINISTRATIVE_TEMPLATES,
  type AdministrativeTemplate,
} from "../../services/api-client";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";

interface AdministrativeTemplatesViewProps {
  onSelectTemplateToEdit: (template: AdministrativeTemplate) => void;
}

export const AdministrativeTemplatesView: React.FC<
  AdministrativeTemplatesViewProps
> = ({ onSelectTemplateToEdit }) => {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredTemplates = ADMINISTRATIVE_TEMPLATES.filter((tpl) => {
    const matchQuery =
      tpl.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tpl.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tpl.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCat =
      selectedCategory === "all" || tpl.category === selectedCategory;
    return matchQuery && matchCat;
  });

  const handleCopyTemplate = (tpl: AdministrativeTemplate) => {
    const text = `${tpl.document_type}\n${tpl.default_title}\n\n${tpl.default_paragraphs.join("\n\n")}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedId(tpl.id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "to_trinh":
        return <FileText className="size-4 text-primary" />;
      case "quyet_dinh":
        return <FileCheck className="size-4 text-emerald-500" />;
      case "thong_bao":
        return <BookOpen className="size-4 text-blue-500" />;
      case "de_thi":
        return <FileSpreadsheet className="size-4 text-amber-500" />;
      default:
        return <Layers className="size-4 text-purple-500" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-surface bg-muted/40 border border-border">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-primary/10 text-primary">
            <Layers className="size-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground">
              Thư Viện Phôi Mẫu Văn Bản Hành Chính & Đề Thi Chuẩn QNU
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Các phôi mẫu đã được thẩm định thể thức theo Nghị định
              30/2020/NĐ-CP và thang Bloom
            </p>
          </div>
        </div>

        <Badge variant="outline" className="text-xs font-mono">
          {ADMINISTRATIVE_TEMPLATES.length} Phôi Mẫu Chứng Nhận
        </Badge>
      </div>

      {/* Search & Category Filter Pills */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm phôi mẫu theo tên, phòng ban ban hành hoặc nội dung..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-xs rounded-control border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {[
            { id: "all", label: "Tất cả phôi mẫu" },
            { id: "to_trinh", label: "Tờ trình" },
            { id: "quyet_dinh", label: "Quyết định" },
            { id: "thong_bao", label: "Thông báo" },
            { id: "ke_hoach", label: "Kế hoạch" },
            { id: "de_thi", label: "Ma trận đề thi" },
            { id: "cong_van", label: "Công văn" },
          ].map((cat) => (
            <button
              type="button"
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`text-xs px-2.5 py-1 rounded-control font-medium transition-all cursor-pointer border ${
                selectedCategory === cat.id
                  ? "bg-primary text-primary-foreground border-primary shadow-xs"
                  : "bg-card hover:bg-muted text-foreground border-border"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map((tpl) => (
          <Card
            key={tpl.id}
            data-testid={`template-card-${tpl.id}`}
            className="p-4 flex flex-col justify-between hover:border-primary/50 transition-all space-y-3"
          >
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-control bg-muted">
                    {getCategoryIcon(tpl.category)}
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {tpl.document_type}
                  </Badge>
                </div>
                <span className="text-[10px] font-medium text-primary">
                  {tpl.standard}
                </span>
              </div>

              <div>
                <h4 className="font-semibold text-xs text-foreground leading-snug">
                  {tpl.title}
                </h4>
                <p className="text-[11px] text-muted-foreground line-clamp-2 mt-1 leading-relaxed">
                  {tpl.description}
                </p>
              </div>

              {/* Department */}
              <div className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
                <span>Đơn vị:</span>
                <span className="text-foreground font-semibold">
                  {tpl.department}
                </span>
              </div>

              {/* Placeholders chips */}
              <div className="space-y-1 pt-1 border-t border-border/50">
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Code2 className="size-3" />
                  <span>Biến dữ liệu (Placeholders):</span>
                </span>
                <div className="flex flex-wrap gap-1">
                  {tpl.placeholders.map((p) => (
                    <span
                      key={p}
                      className="px-1.5 py-0.5 rounded-micro bg-primary/10 text-primary font-mono text-[9px]"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-2 border-t border-border/60 flex items-center justify-between gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => handleCopyTemplate(tpl)}
                title="Sao chép phôi mẫu"
              >
                {copiedId === tpl.id ? (
                  <Check className="size-3 mr-1 text-success" />
                ) : (
                  <Copy className="size-3 mr-1" />
                )}
                <span>{copiedId === tpl.id ? "Đã chép" : "Sao chép"}</span>
              </Button>

              <Button
                size="sm"
                variant="default"
                className="h-7 text-xs font-semibold shadow-xs"
                onClick={() => onSelectTemplateToEdit(tpl)}
              >
                <Sparkles className="size-3 mr-1" />
                <span>Nạp Vào Form</span>
                <ArrowRight className="size-3 ml-1" />
              </Button>
            </div>
          </Card>
        ))}

        {filteredTemplates.length === 0 && (
          <div className="col-span-full py-12 text-center text-xs text-muted-foreground">
            Không tìm thấy phôi mẫu nào khớp với từ khóa tìm kiếm.
          </div>
        )}
      </div>
    </div>
  );
};

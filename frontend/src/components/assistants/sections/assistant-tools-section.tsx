import {
  CheckCircle2,
  Database,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Layers,
  Network,
  ShieldAlert,
  Sparkles,
  Wrench,
} from "lucide-react";
import type { AssistantEditForm } from "@/components/assistants/types";
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
import type { WorkflowDefinition } from "@/services/workflows-api";
import type { AssistantItem } from "@/types/assistants";

interface AssistantToolsSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  workflows?: WorkflowDefinition[];
  onNavigate: (path: string) => void;
  assistant?: AssistantItem;
}

interface UniversalToolDef {
  id: string;
  name: string;
  categoryBadge: string;
  description: string;
  details: string;
  icon: typeof Wrench;
}

const UNIVERSAL_TOOLS: UniversalToolDef[] = [
  {
    id: "export_universal_report",
    name: "Kết Xuất Báo Cáo & File Đa Định Dạng (.xlsx, .docx, .pdf)",
    categoryBadge: "Toàn Nền Tảng",
    description:
      "Tự động phân tích, tổng hợp dữ liệu tư vấn thành bảng biểu và xuất các tệp phiếu tư vấn, kế hoạch, ma trận sang Excel, Word, PDF để tải về.",
    details:
      "Áp dụng cho mọi trợ lý: Tuyển sinh, Quy chế học vụ, Thư viện, Soạn thảo văn bản, Ngân hàng đề thi.",
    icon: FileSpreadsheet,
  },
  {
    id: "lookup_fact_layer",
    name: "Tra Cứu Dữ Kiện Số Hóa (Structured Fact Layer)",
    categoryBadge: "Dữ Liệu Động",
    description:
      "Truy vấn trực tiếp số liệu chính xác (điểm chuẩn, chỉ tiêu, học phí, học phần, hạn ngạch) từ bảng facts động của kho tri thức thay vì chỉ phụ thuộc vào văn bản mộc.",
    details:
      "Bảo đảm tính chính xác 100% đối với các con số biến động theo năm học hoặc quy chế mới.",
    icon: Database,
  },
  {
    id: "export_administrative_document",
    name: "Soạn Thảo Văn Bản Hành Chính Chuẩn NĐ 30/2020",
    categoryBadge: "Hành Chính Số",
    description:
      "Tự động đóng gói nội dung đã tạo thành tệp Word (.docx) chuẩn thể thức và kỹ thuật trình bày văn bản hành chính theo Nghị định 30/2020/NĐ-CP.",
    details:
      "Bao gồm Quốc hiệu, Tiêu ngữ, Tên cơ quan ban hành, Thẩm quyền ký và Định dạng văn bản hành chính.",
    icon: FileText,
  },
  {
    id: "export_exam_matrix",
    name: "Biên Soạn Ma Trận Đề Thi Chuẩn Bloom",
    categoryBadge: "Khảo Thí",
    description:
      "Tạo và kết xuất bảng ma trận phân bổ số lượng câu hỏi, thời gian và điểm số theo 4 cấp độ tư duy (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao) chuẩn Excel.",
    details:
      "Phục vụ giảng viên xây dựng đề thi kết thúc học phần và ngân hàng câu hỏi.",
    icon: Sparkles,
  },
];

export function AssistantToolsSection({
  form,
  onChange,
  onNavigate,
  assistant,
}: AssistantToolsSectionProps) {
  const assistantCode = assistant?.code || assistant?.id || "";

  const isToolEnabled = (toolId: string) => {
    return (form.enabled_tools || []).includes(toolId);
  };

  const toggleTool = (toolId: string, enabled: boolean) => {
    const currentTools = form.enabled_tools || [];
    const nextTools = enabled
      ? Array.from(new Set([...currentTools, toolId]))
      : currentTools.filter((t) => t !== toolId);
    onChange({ ...form, enabled_tools: nextTools });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="size-4 text-primary" />
            <CardTitle className="text-sm font-bold">
              Cơ Chế Phê Duyệt & Công Cụ Hành Động
            </CardTitle>
          </div>
          <Badge
            variant="outline"
            className="text-xs bg-primary/5 text-primary border-primary/20"
          >
            Nội bộ trợ lý
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Quản lý chính sách phê duyệt của con người (HITL), kiểm soát kích hoạt
          công cụ (Function Calling) và xem luồng suy luận trực thuộc.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 1. Embedded DAG Workflow Summary Box */}
        <div className="rounded-lg border p-3.5 bg-muted/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
              <Network className="size-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-foreground">
                Sơ Đồ Luồng Suy Luận Trực Thuộc
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Đồ thị DAG nội bộ điều phối các bước tiếp nhận câu hỏi, tra cứu
                kho tri thức và sinh lời giải đáp.
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5 shrink-0 self-start sm:self-center"
            onClick={() =>
              onNavigate(
                `/assistants/${encodeURIComponent(assistantCode)}/workflow`,
              )
            }
          >
            <span>Mở sơ đồ DAG</span>
            <ExternalLink className="size-3 text-muted-foreground" />
          </Button>
        </div>

        {/* 2. Published Version Pin */}
        {assistant && (
          <div className="rounded-lg border p-2.5 bg-muted/20 flex items-center justify-between text-xs">
            <span className="text-muted-foreground flex items-center gap-1.5">
              <Layers className="size-3.5 text-primary" />
              Phiên bản luồng suy luận đã ghim:
            </span>
            <span className="font-mono text-xs font-semibold text-foreground">
              {assistant.published_workflow_version_id
                ? `v${assistant.published_workflow_version_id.slice(0, 8)}...`
                : "Dùng bản nháp mới nhất"}
            </span>
          </div>
        )}

        {/* 3. Human-in-the-Loop Approval Policy */}
        <div className="rounded-lg border p-3.5 bg-muted/20 space-y-3 text-xs">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="size-4 text-warning shrink-0" />
              <div>
                <p className="font-semibold text-foreground text-xs">
                  Phê Duyệt Của Cán Bộ Trước Khi Hành Động (HITL)
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Bắt buộc cán bộ phụ trách xác nhận thủ công các tác vụ nhạy
                  cảm.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Badge
                variant={form.human_approval_required ? "warning" : "outline"}
                className="text-xs"
              >
                {form.human_approval_required ? "Bật" : "Tắt"}
              </Badge>
              <Switch
                checked={form.human_approval_required}
                onCheckedChange={(checked) =>
                  onChange({ ...form, human_approval_required: checked })
                }
                aria-label="Bật/Tắt chế độ phê duyệt của người"
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed pt-1 border-t border-border/50">
            {form.human_approval_required
              ? "Khi kích hoạt, mọi hành động tác động dữ liệu (như kết xuất văn bản hành chính Word NĐ 30, biên soạn ma trận đề thi) đều phải qua bước phê duyệt Human-in-the-loop."
              : "Trợ lý sẽ tự động hoàn tất và kết xuất kết quả theo các bước đã cấu hình trên sơ đồ luồng suy luận."}
          </p>
          <div className="flex items-center gap-2 pt-0.5">
            <CheckCircle2 className="size-3.5 text-success shrink-0" />
            <span className="text-xs text-muted-foreground">
              Tuân thủ chuẩn Function Calling OpenAPI Schema & Ghi vết kiểm toán
              (Audit Trail).
            </span>
          </div>
        </div>

        {/* 4. Universal AI Capabilities & Skills */}
        <div className="space-y-3 pt-2">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              <h4 className="text-xs font-bold text-foreground">
                Kỹ Năng & Công Cụ Nền Tảng (Universal AI Capabilities)
              </h4>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Kích hoạt hoặc thu hồi các kỹ năng thực thi của Trợ lý AI. Hệ
              thống sử dụng hoàn toàn dữ liệu động từ Kho tri thức số hóa và cơ
              chế xuất file tự động mà không gán cứng mã nguồn.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {UNIVERSAL_TOOLS.map((tool) => {
              const enabled = isToolEnabled(tool.id);
              const IconComp = tool.icon;
              return (
                <div
                  key={tool.id}
                  className={`rounded-lg border p-3.5 transition-colors ${
                    enabled
                      ? "bg-card border-primary/30"
                      : "bg-muted/15 border-border/50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <div
                        className={`flex size-8 items-center justify-center rounded-md shrink-0 mt-0.5 ${
                          enabled
                            ? "bg-primary/10 text-primary"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        <IconComp className="size-4" />
                      </div>
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-xs font-semibold text-foreground">
                            {tool.name}
                          </p>
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1.5 font-normal text-muted-foreground bg-muted/40"
                          >
                            {tool.categoryBadge}
                          </Badge>
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          {tool.description}
                        </p>
                        <p className="text-[10px] text-primary/80 font-medium">
                          {tool.details}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 pt-0.5">
                      <Badge
                        variant={enabled ? "default" : "outline"}
                        className="text-[11px]"
                      >
                        {enabled ? "Kích hoạt" : "Tắt"}
                      </Badge>
                      <Switch
                        checked={enabled}
                        onCheckedChange={(checked) =>
                          toggleTool(tool.id, checked)
                        }
                        aria-label={`Bật/Tắt công cụ ${tool.name}`}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

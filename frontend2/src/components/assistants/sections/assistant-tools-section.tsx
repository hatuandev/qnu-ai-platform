import {
  CheckCircle2,
  ExternalLink,
  Layers,
  Network,
  ShieldAlert,
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

export function AssistantToolsSection({
  form,
  onChange,
  onNavigate,
  assistant,
}: AssistantToolsSectionProps) {
  const assistantCode = assistant?.code || assistant?.id || "";

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
      </CardContent>
    </Card>
  );
}

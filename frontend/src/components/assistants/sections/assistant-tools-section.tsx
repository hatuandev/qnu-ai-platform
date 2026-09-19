import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { WorkflowDefinition } from "@/services/workflows-api";
import { CheckCircle2, ExternalLink, Network, ShieldAlert, Wrench } from "lucide-react";

interface AssistantToolsSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  workflows: WorkflowDefinition[];
  onNavigate: (path: string) => void;
}

export function AssistantToolsSection({
  form,
  onChange,
  workflows,
  onNavigate,
}: AssistantToolsSectionProps) {
  const selectedWorkflow = workflows.find((wf) => wf.id === form.workflow_id);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Wrench className="size-4 text-primary" />
          <CardTitle className="text-sm font-bold">
            Quy Trình Điều Phối & Công Cụ (Workflow DAG)
          </CardTitle>
        </div>
        <CardDescription className="text-xs">
          Liên kết Trợ lý với đồ thị thực thi nhiệm vụ chuyên sâu, Function Calling và phê duyệt
          Human-in-the-loop.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Field htmlFor="detail-assistant-workflow" label="Quy Trình Điều Phối (Workflow DAG)">
          <div className="space-y-2">
            <Select
              value={form.workflow_id}
              onValueChange={(val) => onChange({ ...form, workflow_id: val })}
            >
              <SelectTrigger id="detail-assistant-workflow">
                <SelectValue placeholder="Chọn quy trình workflow" />
              </SelectTrigger>
              <SelectContent>
                {workflows.map((wf) => (
                  <SelectItem key={wf.id} value={wf.id}>
                    {wf.display_name} ({wf.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {form.workflow_id && (
              <Button
                className="w-full h-8 text-xs gap-1.5"
                type="button"
                variant="outline"
                onClick={() => onNavigate(`/workflows/${encodeURIComponent(form.workflow_id)}`)}
              >
                <Network className="size-3.5 text-primary" />
                Mở đồ thị DAG Studio: {selectedWorkflow?.display_name || form.workflow_id}
                <ExternalLink className="size-3 ml-auto opacity-50" />
              </Button>
            )}
          </div>
        </Field>

        {/* Thông tin chính sách kiểm soát tác vụ */}
        <div className="rounded-lg border p-3 bg-muted/20 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <ShieldAlert className="size-3.5 text-warning" />
              Chế độ Phê duyệt & Kiểm soát Hành động
            </span>
            <Badge
              variant={form.human_approval_required ? "warning" : "outline"}
              className="text-xs"
            >
              {form.human_approval_required ? "HITL Kích hoạt" : "Tự động"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {form.human_approval_required
              ? "Mọi hành động nhạy cảm (xuất file văn bản NĐ 30, tạo đề thi, cập nhật dữ liệu) đều yêu cầu cán bộ phụ trách xác nhận thủ công trước khi thực thi."
              : "Trợ lý thực thi các bước theo luồng tiêu chuẩn đã cấu hình trên đồ thị DAG."}
          </p>
          <div className="flex items-center gap-2 pt-1">
            <CheckCircle2 className="size-3.5 text-success shrink-0" />
            <span className="text-xs text-muted-foreground">
              Tuân thủ chuẩn OpenAPI Schema Function Calling & Ghi vết kiểm toán (Audit Trail).
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

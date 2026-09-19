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
import type { AssistantItem } from "@/types/assistants";
import {
  CheckCircle2,
  ExternalLink,
  GitFork,
  Loader2,
  Lock,
  Network,
  ShieldAlert,
  Users,
  Wrench,
} from "lucide-react";

interface AssistantToolsSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  workflows: WorkflowDefinition[];
  onNavigate: (path: string) => void;
  assistant?: AssistantItem;
  onForkWorkflow?: () => void;
  isForkingWorkflow?: boolean;
}

export function AssistantToolsSection({
  form,
  onChange,
  workflows,
  onNavigate,
  assistant,
  onForkWorkflow,
  isForkingWorkflow,
}: AssistantToolsSectionProps) {
  const selectedWorkflow = workflows.find((wf) => wf.id === form.workflow_id);
  const isPrivate = assistant?.workflow_ownership === "private";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="size-4 text-primary" />
            <CardTitle className="text-sm font-bold">
              Quy Trình Điều Phối & Công Cụ (Workflow DAG)
            </CardTitle>
          </div>
          {assistant && (
            <Badge
              variant={isPrivate ? "default" : "outline"}
              className={`text-xs gap-1 ${
                isPrivate
                  ? "bg-primary/10 text-primary border-primary/30"
                  : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
              }`}
            >
              {isPrivate ? (
                <>
                  <Lock className="size-3" />
                  Quy trình riêng
                </>
              ) : (
                <>
                  <Users className="size-3" />
                  Dùng chung
                </>
              )}
            </Badge>
          )}
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

            <div className="flex flex-col sm:flex-row gap-2">
              {form.workflow_id && (
                <Button
                  className="flex-1 h-8 text-xs gap-1.5"
                  type="button"
                  variant="outline"
                  onClick={() => onNavigate(`/workflows/${encodeURIComponent(form.workflow_id)}`)}
                >
                  <Network className="size-3.5 text-primary" />
                  Mở đồ thị DAG Studio: {selectedWorkflow?.display_name || form.workflow_id}
                  <ExternalLink className="size-3 ml-auto opacity-50" />
                </Button>
              )}

              {assistant && !isPrivate && onForkWorkflow && (
                <Button
                  className="h-8 text-xs gap-1.5 border-amber-500/30 text-amber-700 dark:text-amber-300 hover:bg-amber-500/10"
                  type="button"
                  variant="outline"
                  disabled={isForkingWorkflow}
                  onClick={onForkWorkflow}
                  title="Nhân bản quy trình này thành một workflow riêng cho trợ lý"
                >
                  {isForkingWorkflow ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <GitFork className="size-3.5" />
                  )}
                  Tách thành quy trình riêng
                </Button>
              )}
            </div>
          </div>
        </Field>

        {/* Thông tin phiên bản xuất bản đã ghim */}
        {assistant && (
          <div className="rounded-lg border p-2.5 bg-muted/20 flex items-center justify-between text-xs">
            <span className="text-muted-foreground flex items-center gap-1.5">
              <Lock className="size-3.5 text-primary" />
              Phiên bản Workflow đã ghim:
            </span>
            <span className="font-mono text-xs font-semibold text-foreground">
              {assistant.published_workflow_version_id
                ? `v${assistant.published_workflow_version_id.slice(0, 8)}...`
                : "Chưa ghim (Dùng bản mới nhất)"}
            </span>
          </div>
        )}

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

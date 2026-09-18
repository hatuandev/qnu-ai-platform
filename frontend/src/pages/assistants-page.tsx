import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AssistantItem } from "@/services/api-client";
import {
  type AssistantBundle,
  importAssistantBundle,
  listAssistants,
  seedDefaultAssistants,
} from "@/services/assistants-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Bot,
  CheckCircle2,
  FileUp,
  GraduationCap,
  Library,
  MessageSquare,
  Network,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { type ChangeEvent, useRef, useState } from "react";
import { toast } from "sonner";

interface AssistantsPageProps {
  onNavigate: (path: string) => void;
}

const CATEGORY_OPTIONS = [
  { value: "all", label: "Tất cả lĩnh vực" },
  { value: "admissions", label: "Tuyển sinh & Hướng nghiệp" },
  { value: "academic", label: "Quy chế & Học vụ" },
  { value: "resources", label: "Thư viện & Học liệu Số" },
  { value: "administration", label: "Soạn thảo Văn bản NĐ 30" },
  { value: "examination", label: "Khảo thí & Đề thi Bloom" },
];

const STATUS_OPTIONS = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang hoạt động" },
  { value: "inactive", label: "Đã tạm dừng" },
];

function AssistantIcon({ category }: { category: string }) {
  const Icon =
    category === "admissions"
      ? GraduationCap
      : category === "academic"
        ? ShieldCheck
        : category === "resources"
          ? Library
          : category === "administration"
            ? BookOpen
            : Bot;
  return <Icon className="size-5" />;
}

function isAssistantBundle(value: unknown): value is AssistantBundle {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return record.format_version === "qnu.assistant.bundle/v1" && "assistant" in record;
}

function AssistantCard({
  item,
  onOpen,
  onChat,
  onOpenWorkflow,
}: {
  item: AssistantItem;
  onOpen: () => void;
  onChat: () => void;
  onOpenWorkflow: () => void;
}) {
  const modelPolicy = item.config.model_policy;
  return (
    <Card className="flex h-full flex-col border-border/80 transition-all hover:border-primary/50 hover:shadow-xs group">
      <CardHeader className="space-y-3 pb-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform group-hover:scale-105">
            <AssistantIcon category={item.category} />
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-[10px] capitalize">
              {item.category}
            </Badge>
            <Badge variant={item.is_active ? "success" : "secondary"} className="text-[10px]">
              {item.is_active ? "Hoạt động" : "Đã tắt"}
            </Badge>
          </div>
        </div>
        <div>
          <CardTitle className="text-sm font-bold text-foreground line-clamp-1">
            {item.name}
          </CardTitle>
          <CardDescription className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground min-h-8">
            {item.description}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="mt-auto space-y-3 pt-0">
        <div className="grid gap-1.5 border-t border-border/70 pt-2.5 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">Mô hình AI:</span>
            <span className="truncate font-mono text-[11px] font-semibold text-foreground">
              {modelPolicy.primary_model}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">Kho Tri Thức:</span>
            <span className="truncate font-mono text-[11px] text-muted-foreground">
              {item.collection_id}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">Chuẩn TM-08:</span>
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-success">
              <CheckCircle2 className="size-3" />
              Faithfulness ≥ 0.90
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-1.5 pt-1">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1 px-2"
            onClick={onChat}
            title="Thử trò chuyện với Trợ lý"
          >
            <MessageSquare className="size-3 text-primary" />
            <span>Chat</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1 px-2"
            onClick={onOpenWorkflow}
            title="Mở sơ đồ quy trình DAG"
          >
            <Network className="size-3 text-primary" />
            <span>DAG</span>
          </Button>
          <Button
            variant="default"
            size="sm"
            className="h-8 text-xs gap-1 px-2"
            onClick={onOpen}
            title="Mở bảng điều khiển quản trị trợ lý"
          >
            <Settings className="size-3" />
            <span>Cấu hình</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function AssistantsPage({ onNavigate }: AssistantsPageProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const assistantsQuery = useQuery({
    queryKey: ["assistants", search, category],
    queryFn: () => listAssistants({ search, category, includeInactive: true }),
  });

  const seedMutation = useMutation({
    mutationFn: seedDefaultAssistants,
    onSuccess: (result) => {
      toast.success(
        `Đã đồng bộ ${result.assistants_added} trợ lý và ${result.workflows_added} workflow (Tổng cộng: ${result.total_assistants} trợ lý).`
      );
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const importMutation = useMutation({
    mutationFn: importAssistantBundle,
    onSuccess: (assistant) => {
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(`Đã nhập thành công bundle trợ lý “${assistant.name}”!`);
      onNavigate(`/assistants/${encodeURIComponent(assistant.code)}`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const items = assistantsQuery.data ?? [];
  const activeCount = items.filter((item) => item.is_active).length;
  const guardedCount = items.filter(
    (item) => item.config.guardrails.require_grounded_answer
  ).length;

  const filteredItems = items.filter((item) => {
    if (statusFilter === "active") return item.is_active;
    if (statusFilter === "inactive") return !item.is_active;
    return true;
  });

  const handleImport = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!isAssistantBundle(parsed)) {
        throw new Error("Tệp không phải bundle trợ lý QNU hợp lệ.");
      }
      importMutation.mutate(parsed);
    } catch (importError) {
      toast.error(
        importError instanceof Error ? importError.message : "Nhập bundle trợ lý thất bại."
      );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Bot className="size-4 text-primary" />
            <span>Vận hành / Danh mục Trợ lý AI</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground">
            Hệ sinh thái Trợ lý AI QNU
          </h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
            Quản trị các Trợ lý AI chuyên trách theo vòng đời 7 lớp, kết nối Kho tri thức thật,
            Workflow DAG chuẩn và rào chắn chống bịa đặt TM-08.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            ref={fileInputRef}
            accept="application/json,.bundle"
            aria-label="Chọn bundle trợ lý để nhập"
            className="hidden"
            type="file"
            onChange={handleImport}
          />
          <Button
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => fileInputRef.current?.click()}
          >
            <FileUp className="size-3.5" />
            Nhập bundle
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            disabled={seedMutation.isPending}
            onClick={() => seedMutation.mutate()}
          >
            <RefreshCw className={seedMutation.isPending ? "size-3.5 animate-spin" : "size-3.5"} />
            Đồng bộ mẫu Core
          </Button>
          <Button
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => onNavigate("/assistants/new")}
          >
            <Plus className="size-3.5" />
            Tạo trợ lý mới
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { label: "Tổng trợ lý hệ thống", value: items.length },
          { label: "Đang hoạt động", value: activeCount },
          { label: "Bắt buộc trích dẫn & Grounded", value: guardedCount },
        ].map((stat) => (
          <Card key={stat.label} className="border-border/80">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{stat.label}</p>
              <p className="mt-1 text-2xl font-semibold tracking-tight text-foreground font-mono">
                {stat.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between pb-3">
          <div>
            <CardTitle className="text-sm font-bold">Danh mục Trợ lý AI</CardTitle>
            <CardDescription className="text-xs">
              Tìm kiếm, lọc trạng thái và truy cập bảng điều khiển cấu hình chuyên sâu của từng Trợ
              lý.
            </CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative min-w-56">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
              <Input
                className="pl-8 h-9 text-xs"
                placeholder="Tìm theo mã, tên, mô tả..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger aria-label="Lọc trợ lý theo lĩnh vực" className="min-w-40 h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger aria-label="Lọc theo trạng thái" className="min-w-36 h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {assistantsQuery.isLoading ? (
            <div className="flex min-h-56 items-center justify-center text-xs text-muted-foreground">
              Đang tải danh mục trợ lý từ Backend…
            </div>
          ) : filteredItems.length === 0 ? (
            <EmptyState
              action={
                <Button onClick={() => seedMutation.mutate()}>
                  <RefreshCw className="size-4" />
                  Nạp 5 trợ lý chuẩn
                </Button>
              }
              description="Không tìm thấy trợ lý phù hợp với bộ lọc tìm kiếm hoặc CSDL chưa có dữ liệu."
              icon={Bot}
              title="Không có kết quả trợ lý"
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredItems.map((item) => (
                <AssistantCard
                  key={item.id}
                  item={item}
                  onOpen={() => onNavigate(`/assistants/${encodeURIComponent(item.code)}`)}
                  onChat={() => onNavigate(`/chat?assistant=${encodeURIComponent(item.code)}`)}
                  onOpenWorkflow={() =>
                    onNavigate(`/workflows/${encodeURIComponent(item.workflow_id)}`)
                  }
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

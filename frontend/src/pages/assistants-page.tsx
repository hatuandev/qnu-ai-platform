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
  FileUp,
  GraduationCap,
  Library,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { type ChangeEvent, useRef, useState } from "react";

interface AssistantsPageProps {
  onNavigate: (path: string) => void;
}

const CATEGORY_OPTIONS = [
  { value: "all", label: "Tất cả lĩnh vực" },
  { value: "admissions", label: "Tuyển sinh" },
  { value: "academic", label: "Đào tạo" },
  { value: "resources", label: "Học liệu" },
  { value: "administration", label: "Hành chính" },
  { value: "examination", label: "Khảo thí" },
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

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Không thể hoàn thành thao tác trợ lý.";
}

function isAssistantBundle(value: unknown): value is AssistantBundle {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return record.format_version === "qnu.assistant.bundle/v1" && "assistant" in record;
}

function AssistantCard({ item, onOpen }: { item: AssistantItem; onOpen: () => void }) {
  const modelPolicy = item.config.model_policy;
  return (
    <Card className="flex h-full flex-col border-border/80 transition-colors hover:border-primary/40">
      <CardHeader className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <AssistantIcon category={item.category} />
          </div>
          <Badge variant={item.is_active ? "success" : "secondary"}>
            {item.is_active ? "Hoạt động" : "Đã tắt"}
          </Badge>
        </div>
        <div>
          <CardTitle className="text-base">{item.name}</CardTitle>
          <CardDescription className="mt-1 line-clamp-3 leading-relaxed">
            {item.description}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="mt-auto space-y-4">
        <div className="grid gap-2 border-t border-border/70 pt-3 text-xs">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">Mô hình chính</span>
            <span className="truncate font-mono">{modelPolicy.primary_model}</span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">Kho tri thức</span>
            <span className="truncate font-mono">{item.collection_id}</span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">Workflow</span>
            <span className="truncate font-mono">{item.workflow_id}</span>
          </div>
        </div>
        <Button className="w-full" variant="outline" onClick={onOpen}>
          Quản trị trợ lý
        </Button>
      </CardContent>
    </Card>
  );
}

export function AssistantsPage({ onNavigate }: AssistantsPageProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [feedback, setFeedback] = useState<string | null>(null);
  const assistantsQuery = useQuery({
    queryKey: ["assistants", search, category],
    queryFn: () => listAssistants({ search, category, includeInactive: true }),
  });
  const seedMutation = useMutation({
    mutationFn: seedDefaultAssistants,
    onSuccess: (result) => {
      setFeedback(
        `Đã thêm ${result.assistants_added} trợ lý và ${result.workflows_added} workflow; tổng cộng ${result.total_assistants} trợ lý.`
      );
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
    },
  });
  const importMutation = useMutation({
    mutationFn: importAssistantBundle,
    onSuccess: (assistant) => {
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      onNavigate(`/assistants/${encodeURIComponent(assistant.code)}`);
    },
  });

  const items = assistantsQuery.data ?? [];
  const activeCount = items.filter((item) => item.is_active).length;
  const guardedCount = items.filter(
    (item) => item.config.guardrails.require_grounded_answer
  ).length;
  const error = assistantsQuery.error || seedMutation.error || importMutation.error;

  const handleImport = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setFeedback(null);
    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!isAssistantBundle(parsed)) {
        throw new Error("Tệp không phải bundle trợ lý QNU hợp lệ.");
      }
      importMutation.mutate(parsed);
    } catch (importError) {
      setFeedback(getErrorMessage(importError));
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
          <h1 className="mt-2 text-2xl font-bold tracking-tight">Trợ lý AI chuyên trách QNU</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Dữ liệu thật từ Backend, liên kết trực tiếp với kho tri thức, workflow và chính sách an
            toàn của từng trợ lý.
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
          <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
            <FileUp className="size-4" />
            Nhập bundle
          </Button>
          <Button variant="outline" onClick={() => seedMutation.mutate()}>
            <RefreshCw className={seedMutation.isPending ? "size-4 animate-spin" : "size-4"} />
            Đồng bộ mẫu Core
          </Button>
          <Button onClick={() => onNavigate("/assistants/new")}>
            <Plus className="size-4" />
            Tạo trợ lý
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { label: "Tổng trợ lý", value: items.length },
          { label: "Đang hoạt động", value: activeCount },
          { label: "Bắt buộc grounded", value: guardedCount },
        ].map((stat) => (
          <Card key={stat.label} className="border-border/80">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{stat.label}</p>
              <p className="mt-1 text-2xl font-semibold tracking-tight">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {feedback ? (
        <div className="rounded-md border border-primary/30 bg-primary/10 px-4 py-3 text-xs text-primary">
          {feedback}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {getErrorMessage(error)}
        </div>
      ) : null}

      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>Danh mục trợ lý</CardTitle>
            <CardDescription>
              Tìm kiếm và mở trang quản trị chuyên sâu của từng trợ lý.
            </CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative min-w-64">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                className="pl-8"
                placeholder="Tìm theo mã, tên, mô tả..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger aria-label="Lọc trợ lý theo lĩnh vực" className="min-w-44">
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
          </div>
        </CardHeader>
        <CardContent>
          {assistantsQuery.isLoading ? (
            <div className="flex min-h-56 items-center justify-center text-sm text-muted-foreground">
              Đang tải danh mục trợ lý từ Backend...
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              action={
                <Button onClick={() => seedMutation.mutate()}>
                  <RefreshCw className="size-4" />
                  Nạp 5 trợ lý chuẩn
                </Button>
              }
              description="Cơ sở dữ liệu chưa có trợ lý. Có thể nạp bộ mẫu chuẩn từ qnu-ai-core mà không ghi đè cấu hình hiện có."
              icon={Bot}
              title="Chưa có dữ liệu trợ lý"
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {items.map((item) => (
                <AssistantCard
                  key={item.id}
                  item={item}
                  onOpen={() => onNavigate(`/assistants/${encodeURIComponent(item.code)}`)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

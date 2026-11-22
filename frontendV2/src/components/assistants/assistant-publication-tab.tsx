import {
  BarChart3,
  Code2,
  Copy,
  ExternalLink,
  Globe,
  Loader2,
  Save,
  Undo2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import type { AssistantResponse } from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import {
  type PublicationResponse,
  type PublicationStats,
  useAssistantPublicationQuery,
  usePublicationStatsQuery,
  useSavePublicationMutation,
} from "@/api/publications";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { READINESS_MAP } from "./readiness";

const SLUG_REGEX = /^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$/;
const MAX_PROMPTS = 6;
const PROMPT_MAX_CHARS = 160;

type PublicationFormState = {
  slug: string;
  displayName: string;
  welcome: string;
  starterPrompts: string;
  allowedEmbedOrigins: string;
  maxTurns: string;
  dailyBudget: string;
  unlimitedBudget: boolean;
  enabled: boolean;
};

type Baseline = { revision: number; data: PublicationResponse };

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/g, "");
}

function initialState(
  publication: PublicationResponse,
  assistantName: string,
): PublicationFormState {
  return {
    slug: publication.slug ?? slugify(assistantName),
    displayName: publication.display_name || assistantName,
    welcome: publication.welcome_message,
    starterPrompts: publication.starter_prompts.join("\n"),
    allowedEmbedOrigins: (publication.allowed_embed_origins || []).join("\n"),
    maxTurns: String(publication.max_turns_per_session || 15),
    dailyBudget:
      publication.daily_token_budget === null
        ? ""
        : String(publication.daily_token_budget),
    unlimitedBudget: publication.daily_token_budget === null,
    enabled: publication.enabled,
  };
}

function parseOrigins(raw: string): string[] {
  const seen = new Set<string>();
  const origins: string[] = [];
  for (const line of raw.split("\n")) {
    let text = line.trim();
    if (!text) continue;
    if (!text.startsWith("http://") && !text.startsWith("https://")) {
      text = `https://${text}`;
    }
    try {
      const url = new URL(text);
      if (url.protocol !== "http:" && url.protocol !== "https:") continue;
      const origin = url.origin.toLowerCase();
      if (!seen.has(origin)) {
        seen.add(origin);
        origins.push(origin);
      }
    } catch {
      // Ignore invalid URL
    }
  }
  return origins;
}

function parsePrompts(raw: string): string[] {
  const seen = new Set<string>();
  const prompts: string[] = [];
  for (const line of raw.split("\n")) {
    const text = line.trim();
    const key = text.toLocaleLowerCase("vi");
    if (!text || seen.has(key)) continue;
    seen.add(key);
    prompts.push(text);
  }
  return prompts;
}

function validateForm(form: PublicationFormState): string | null {
  const slug = form.slug.trim().toLowerCase();
  if (!SLUG_REGEX.test(slug)) {
    return "Đường dẫn phải dài 3–60 ký tự, gồm chữ thường không dấu, số và dấu gạch ngang (không bắt đầu/kết thúc bằng gạch ngang).";
  }
  if (!form.displayName.trim()) {
    return "Tên hiển thị không được để trống.";
  }
  if (form.welcome.length > 2000) {
    return "Lời chào tối đa 2000 ký tự.";
  }
  const prompts = parsePrompts(form.starterPrompts);
  if (prompts.length > MAX_PROMPTS) {
    return `Tối đa ${MAX_PROMPTS} câu hỏi gợi ý.`;
  }
  if (prompts.some((prompt) => prompt.length > PROMPT_MAX_CHARS)) {
    return `Mỗi câu hỏi gợi ý tối đa ${PROMPT_MAX_CHARS} ký tự.`;
  }
  const maxTurns = Number(form.maxTurns);
  if (!Number.isInteger(maxTurns) || maxTurns < 1 || maxTurns > 100) {
    return "Số lượt tối đa mỗi phiên phải là số nguyên từ 1 đến 100.";
  }
  if (!form.unlimitedBudget) {
    if (!form.dailyBudget.trim()) {
      return "Nhập ngân sách token mỗi ngày hoặc chọn Không giới hạn.";
    }
    const budget = Number(form.dailyBudget);
    if (!Number.isInteger(budget) || budget < 1000) {
      return "Ngân sách token mỗi ngày phải là số nguyên từ 1000 trở lên, hoặc chọn Không giới hạn.";
    }
  }
  return null;
}

const updatedAtFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const numberFormatter = new Intl.NumberFormat("vi-VN");

function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

function shortDay(day: string): string {
  const [, month, date] = day.split("-");
  return `${date}/${month}`;
}

function PublicationStatsCard({
  workspaceId,
  assistantId,
}: {
  workspaceId: string;
  assistantId: string;
}) {
  const [days, setDays] = useState<7 | 30>(7);
  const { data, isLoading, isError, refetch } = usePublicationStatsQuery(
    workspaceId,
    assistantId,
    days,
  );

  return (
    <Card className="border-border/60 shadow-2xs">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <BarChart3 className="size-4" />
            </div>
            <div>
              <CardTitle className="text-sm">Hiệu quả kênh công khai</CardTitle>
              <CardDescription>
                Số liệu ẩn danh theo ngày; hệ thống không lưu danh tính hay địa
                chỉ IP của khách.
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant={days === 7 ? "secondary" : "ghost"}
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => setDays(7)}
            >
              7 ngày
            </Button>
            <Button
              variant={days === 30 ? "secondary" : "ghost"}
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => setDays(30)}
            >
              30 ngày
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[0, 1, 2, 3].map((slot) => (
              <Skeleton key={slot} className="h-16 rounded-md" />
            ))}
          </div>
        ) : isError || !data ? (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/30 px-3 py-2">
            <p className="text-xs text-muted-foreground">
              Không tải được số liệu kênh công khai. Kết nối tới máy chủ không
              thành công hoặc phiên đăng nhập đã hết hạn.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => void refetch()}
            >
              Tải lại
            </Button>
          </div>
        ) : !data.configured ? (
          <p className="text-xs text-muted-foreground">
            Bật kênh công khai để bắt đầu ghi nhận số liệu. Số liệu xuất hiện
            sau lượt truy cập đầu tiên.
          </p>
        ) : (
          <StatsContent stats={data} />
        )}
      </CardContent>
    </Card>
  );
}

function StatsContent({ stats }: { stats: PublicationStats }) {
  const { totals } = stats;
  const maxTurns = Math.max(1, ...stats.daily.map((item) => item.turns));
  const insufficientPercent = totals.turns
    ? Math.round((totals.insufficient_turns / totals.turns) * 100)
    : 0;
  const budgetPercent =
    stats.budget_limit && stats.budget_limit > 0
      ? Math.min(
          100,
          Math.round((stats.budget_used_today / stats.budget_limit) * 100),
        )
      : 0;
  const isBudgetExhausted =
    stats.budget_limit !== null &&
    stats.budget_limit > 0 &&
    stats.budget_used_today >= stats.budget_limit;
  const firstDay = stats.daily[0];
  const lastDay = stats.daily[stats.daily.length - 1];

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-md bg-muted/30 px-3 py-2.5">
          <p className="text-[11px] text-muted-foreground">Lượt hỏi</p>
          <p className="text-lg font-semibold tabular-nums">
            {formatNumber(totals.turns)}
          </p>
        </div>
        <div className="rounded-md bg-muted/30 px-3 py-2.5">
          <p className="text-[11px] text-muted-foreground">Phiên trò chuyện</p>
          <p className="text-lg font-semibold tabular-nums">
            {formatNumber(totals.sessions)}
          </p>
        </div>
        <div className="rounded-md bg-muted/30 px-3 py-2.5">
          <p className="text-[11px] text-muted-foreground">Thiếu căn cứ</p>
          <p className="text-lg font-semibold tabular-nums">
            {formatNumber(totals.insufficient_turns)}
          </p>
          <p className="text-[10px] text-muted-foreground">
            {insufficientPercent}% tổng lượt hỏi
          </p>
        </div>
        <div className="rounded-md bg-muted/30 px-3 py-2.5">
          <p className="text-[11px] text-muted-foreground">Lượt lỗi</p>
          <p className="text-lg font-semibold tabular-nums">
            {formatNumber(totals.error_turns)}
          </p>
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-muted-foreground">Token hôm nay</span>
          <span className="font-medium tabular-nums">
            {formatNumber(stats.budget_used_today)}
            {stats.budget_limit !== null
              ? ` / ${formatNumber(stats.budget_limit)}`
              : " · không giới hạn"}
          </span>
        </div>
        {stats.budget_limit !== null ? (
          <Progress
            value={budgetPercent}
            className={
              isBudgetExhausted
                ? "h-1.5 [&_[data-slot=progress-indicator]]:bg-destructive"
                : "h-1.5"
            }
          />
        ) : null}
        {isBudgetExhausted ? (
          <p className="text-[11px] text-destructive">
            Đã chạm trần token hôm nay; khách nhận lời nhắn tạm ngưng cho đến
            khi sang ngày mới.
          </p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground">Lượt hỏi theo ngày</p>
        <div className="flex h-20 items-end gap-1">
          {stats.daily.map((item) => (
            <div
              key={item.day}
              className="flex h-full flex-1 items-end"
              title={`${shortDay(item.day)}: ${formatNumber(item.turns)} lượt hỏi`}
            >
              <div
                className={
                  item.turns > 0
                    ? "w-full rounded-sm bg-primary/70"
                    : "h-0.5 w-full rounded-sm bg-muted"
                }
                style={
                  item.turns > 0
                    ? {
                        height: `${Math.max(6, Math.round((item.turns / maxTurns) * 100))}%`,
                      }
                    : undefined
                }
              />
            </div>
          ))}
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground">
          <span>{firstDay ? shortDay(firstDay.day) : ""}</span>
          <span>{lastDay ? shortDay(lastDay.day) : ""}</span>
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-foreground">
          Câu hỏi chưa trả lời được
        </p>
        {stats.top_questions.length ? (
          <ul className="divide-y divide-border/50 rounded-md bg-muted/30">
            {stats.top_questions.map((item) => (
              <li
                key={`${item.question}-${item.last_asked_at}`}
                className="flex items-start justify-between gap-3 px-3 py-2"
              >
                <p className="min-w-0 text-xs leading-relaxed">
                  {item.question}
                </p>
                <Badge
                  variant="secondary"
                  className="h-5 shrink-0 px-1.5 text-[10px] font-normal"
                >
                  ×{formatNumber(item.times_asked)}
                </Badge>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Chưa ghi nhận câu hỏi nào bị thiếu căn cứ trong khoảng thời gian
            này. Khi khách hỏi ngoài phạm vi tài liệu, câu hỏi sẽ xuất hiện ở
            đây để đơn vị bổ sung nội dung.
          </p>
        )}
      </div>
    </>
  );
}

function saveErrorMessage(err: unknown): string {
  if (err instanceof ApiProblemError) {
    if (err.code === "publication_not_ready") {
      return "Trợ lý chưa sẵn sàng phục vụ: hãy gắn kho tri thức, hoàn tất xuất bản và nạp chỉ mục trước khi bật công khai.";
    }
    if (err.code === "publication_slug_taken") {
      return "Đường dẫn này đã được trợ lý khác sử dụng. Hãy chọn đường dẫn khác.";
    }
    if (err.code === "publication_revision_conflict") {
      return "Cấu hình công khai vừa được cập nhật ở nơi khác. Đã tải lại; vui lòng kiểm tra rồi lưu lại.";
    }
    if (err.kind === "forbidden") {
      return "Chỉ quản trị viên của đơn vị mới có thể thay đổi kênh công khai.";
    }
    return err.message;
  }
  return "Không lưu được cấu hình công khai. Vui lòng thử lại.";
}

export function AssistantPublicationTab({
  workspaceId,
  assistant,
}: {
  workspaceId: string;
  assistant: AssistantResponse;
}) {
  const {
    data: publication,
    isLoading,
    isError,
    refetch,
  } = useAssistantPublicationQuery(workspaceId, assistant.id);
  const saveMutation = useSavePublicationMutation(workspaceId, assistant.id);

  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [form, setForm] = useState<PublicationFormState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const initialForm = useMemo(
    () => (baseline ? initialState(baseline.data, assistant.name) : null),
    [baseline, assistant.name],
  );
  const isDirty = useMemo(
    () =>
      Boolean(form && initialForm) &&
      JSON.stringify(form) !== JSON.stringify(initialForm),
    [form, initialForm],
  );

  useEffect(() => {
    if (!publication) return;
    if (baseline && publication.revision === baseline.revision) return;
    if (baseline && isDirty) return;
    setBaseline({ revision: publication.revision, data: publication });
    setForm(initialState(publication, assistant.name));
    setError(null);
  }, [publication, baseline, isDirty, assistant.name]);

  if (isLoading || !publication || !form || !baseline) {
    if (isError) {
      return (
        <Alert variant="destructive">
          <AlertTitle>Không tải được cấu hình công khai</AlertTitle>
          <AlertDescription>
            <span>
              Kết nối tới máy chủ không thành công hoặc phiên đăng nhập đã hết
              hạn.
            </span>
            <Button
              variant="outline"
              size="sm"
              className="mt-2 h-7 text-xs"
              onClick={() => void refetch()}
            >
              Tải lại
            </Button>
          </AlertDescription>
        </Alert>
      );
    }
    return (
      <div className="space-y-4">
        <Skeleton className="h-40 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  const patch = (values: Partial<PublicationFormState>) =>
    setForm((prev) => (prev ? { ...prev, ...values } : prev));

  const handleReset = () => {
    setForm(initialState(baseline.data, assistant.name));
    setError(null);
  };

  const handleSave = async () => {
    const message = validateForm(form);
    if (message) {
      setError(message);
      return;
    }
    setError(null);
    try {
      const saved = await saveMutation.mutateAsync({
        slug: form.slug.trim().toLowerCase(),
        display_name: form.displayName.trim(),
        welcome_message: form.welcome,
        starter_prompts: parsePrompts(form.starterPrompts),
        allowed_embed_origins: parseOrigins(form.allowedEmbedOrigins),
        max_turns_per_session: Number(form.maxTurns),
        daily_token_budget: form.unlimitedBudget
          ? null
          : Number(form.dailyBudget),
        enabled: form.enabled,
        expected_revision: baseline.data.configured ? baseline.revision : null,
      });
      setBaseline({ revision: saved.revision, data: saved });
      setForm(initialState(saved, assistant.name));
      toast.success(
        saved.enabled
          ? "Đã cập nhật kênh công khai"
          : "Đã lưu cấu hình công khai (đang tắt)",
      );
    } catch (err: unknown) {
      if (
        err instanceof ApiProblemError &&
        err.code === "publication_revision_conflict"
      ) {
        void refetch();
      }
      setError(saveErrorMessage(err));
    }
  };

  const savedPublicPath = baseline.data.public_path;
  const publicUrl = savedPublicPath
    ? `${window.location.origin}${savedPublicPath}`
    : null;
  const isLive =
    baseline.data.configured &&
    baseline.data.enabled &&
    baseline.data.system_enabled;
  const readinessBadge = READINESS_MAP[baseline.data.readiness];

  const handleCopyLink = async () => {
    if (!publicUrl) return;
    try {
      await navigator.clipboard.writeText(publicUrl);
      toast.success("Đã sao chép liên kết công khai");
    } catch {
      toast.error(
        "Trình duyệt không cho phép sao chép. Hãy chọn và sao chép thủ công.",
      );
    }
  };

  const savedDisplayName = baseline.data.display_name || assistant.name;
  const embedUrl = publicUrl ? `${publicUrl}?embed=1` : null;
  const embedSnippet = embedUrl
    ? `<iframe src="${embedUrl}" title="${savedDisplayName.replaceAll('"', "&quot;")}" width="100%" height="600" style="border:0;border-radius:12px;max-width:100%" loading="lazy"></iframe>`
    : "";

  const handleCopySnippet = async () => {
    if (!embedSnippet) return;
    try {
      await navigator.clipboard.writeText(embedSnippet);
      toast.success("Đã sao chép mã nhúng");
    } catch {
      toast.error(
        "Trình duyệt không cho phép sao chép. Hãy chọn và sao chép thủ công.",
      );
    }
  };

  return (
    <div className="space-y-4">
      {!baseline.data.system_enabled ? (
        <Alert variant="warning">
          <AlertTitle>Kênh công khai đang tắt toàn hệ thống</AlertTitle>
          <AlertDescription>
            Quản trị hệ thống đã tạm đóng mọi liên kết công khai. Cấu hình bên
            dưới vẫn được giữ; liên kết sẽ hoạt động trở lại khi hệ thống mở
            lại.
          </AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Chưa lưu được cấu hình công khai</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="border-b border-border/50 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Globe className="size-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold">
                  Kênh công khai
                </CardTitle>
                <CardDescription>
                  Người ngoài tổ chức có thể mở liên kết và hỏi trợ lý mà không
                  cần đăng nhập.
                </CardDescription>
              </div>
            </div>
            <Badge
              variant={
                isLive
                  ? "success"
                  : baseline.data.enabled
                    ? "warning"
                    : "secondary"
              }
              className="h-5 px-2 text-[11px] font-normal"
            >
              {isLive
                ? "Đang công khai"
                : baseline.data.enabled
                  ? "Đang tạm ẩn"
                  : "Đang tắt"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 pt-5">
          <div className="flex items-center justify-between gap-4 rounded-lg border border-border/60 bg-muted/20 px-4 py-3">
            <div className="space-y-0.5">
              <Label
                htmlFor="publication-enabled-switch"
                className="cursor-pointer text-xs font-medium text-foreground"
              >
                Cho phép truy cập công khai
              </Label>
              <p className="text-[11px] text-muted-foreground">
                Chỉ bật được khi trợ lý sẵn sàng phục vụ. Hệ thống tự tạm ẩn
                liên kết khi kho tri thức mất chỉ mục hoặc nguồn bị thu hồi.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge
                variant={readinessBadge.variant}
                className="h-5 px-1.5 text-[10px] font-normal"
              >
                {readinessBadge.label}
              </Badge>
              <Switch
                id="publication-enabled-switch"
                checked={form.enabled}
                onCheckedChange={(checked) => patch({ enabled: checked })}
                disabled={
                  saveMutation.isPending || !baseline.data.system_enabled
                }
              />
            </div>
          </div>

          <Separator />

          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel required className="text-xs font-medium">
                Đường dẫn công khai
              </FieldLabel>
              <Input
                value={form.slug}
                onChange={(event) => patch({ slug: event.target.value })}
                maxLength={60}
                placeholder="VD: tu-van-tuyen-sinh-2026"
                className="h-9 bg-background font-mono text-xs"
                disabled={saveMutation.isPending}
              />
              <FieldDescription>
                Liên kết dạng {window.location.origin}/chatbot/
                {form.slug || "duong-dan"}
              </FieldDescription>
            </Field>

            <Field>
              <FieldLabel required className="text-xs font-medium">
                Tên hiển thị với khách
              </FieldLabel>
              <Input
                value={form.displayName}
                onChange={(event) => patch({ displayName: event.target.value })}
                maxLength={160}
                placeholder="VD: Trợ lý Tuyển sinh 2026"
                className="h-9 bg-background text-xs"
                disabled={saveMutation.isPending}
              />
              <FieldDescription>
                Tên này xuất hiện trên trang công khai, không kèm mã nội bộ.
              </FieldDescription>
            </Field>
          </div>

          <Field>
            <FieldLabel className="text-xs font-medium">Lời chào</FieldLabel>
            <Textarea
              value={form.welcome}
              onChange={(event) => patch({ welcome: event.target.value })}
              maxLength={2000}
              placeholder="Giới thiệu ngắn về trợ lý và cách đặt câu hỏi..."
              rows={3}
              className="resize-none bg-background text-xs leading-relaxed"
              disabled={saveMutation.isPending}
            />
          </Field>

          <Field>
            <FieldLabel className="text-xs font-medium">
              Câu hỏi gợi ý
            </FieldLabel>
            <Textarea
              value={form.starterPrompts}
              onChange={(event) =>
                patch({ starterPrompts: event.target.value })
              }
              placeholder={
                "Mỗi dòng một câu hỏi gợi ý, tối đa 6 câu.\nHọc phí năm 2026 là bao nhiêu?\nHồ sơ xét tuyển gồm những gì?"
              }
              rows={4}
              className="resize-none bg-background text-xs leading-relaxed"
              disabled={saveMutation.isPending}
            />
            <FieldDescription>
              Hiển thị thành các nút bấm nhanh trên trang công khai; mỗi câu tối
              đa {PROMPT_MAX_CHARS} ký tự.
            </FieldDescription>
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel className="text-xs font-medium">
                Số lượt hỏi mỗi phiên
              </FieldLabel>
              <Input
                type="number"
                min={1}
                max={100}
                value={form.maxTurns}
                onChange={(event) => patch({ maxTurns: event.target.value })}
                className="h-9 bg-background text-xs"
                disabled={saveMutation.isPending}
              />
              <FieldDescription>
                Mỗi khách được hỏi tối đa số lượt này trong một phiên trò
                chuyện.
              </FieldDescription>
            </Field>

            <Field>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <FieldLabel className="text-xs font-medium">
                  Ngân sách token mỗi ngày
                </FieldLabel>
                <div className="flex items-center gap-1.5">
                  <Label
                    htmlFor="publication-unlimited-budget"
                    className="cursor-pointer text-[11px] font-normal text-muted-foreground"
                  >
                    Không giới hạn
                  </Label>
                  <Switch
                    id="publication-unlimited-budget"
                    checked={form.unlimitedBudget}
                    onCheckedChange={(checked) =>
                      patch(
                        checked
                          ? { unlimitedBudget: true, dailyBudget: "" }
                          : { unlimitedBudget: false },
                      )
                    }
                    disabled={saveMutation.isPending}
                  />
                </div>
              </div>
              <Input
                type="number"
                min={1000}
                value={form.dailyBudget}
                onChange={(event) => patch({ dailyBudget: event.target.value })}
                placeholder={
                  form.unlimitedBudget ? "Không giới hạn" : "VD: 200000"
                }
                className="h-9 bg-background text-xs"
                disabled={saveMutation.isPending || form.unlimitedBudget}
              />
              <FieldDescription>
                Khi chạm trần, khách nhận lời nhắn tạm ngưng thay vì lỗi. Bật
                Không giới hạn cho kênh tư vấn liên tục như tuyển sinh.
              </FieldDescription>
            </Field>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Liên kết chia sẻ</CardTitle>
          <CardDescription>
            {publicUrl
              ? "Chỉ liên kết đã lưu mới hoạt động; sao chép để gửi cho khách."
              : "Liên kết xuất hiện sau khi lưu cấu hình lần đầu."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Input
              readOnly
              value={publicUrl ?? ""}
              placeholder="Chưa có liên kết"
              className="h-9 bg-muted/30 font-mono text-xs"
              aria-label="Liên kết công khai"
            />
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs"
                disabled={!publicUrl}
                onClick={() => void handleCopyLink()}
              >
                <Copy className="size-3.5" />
                <span>Sao chép</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs"
                disabled={!publicUrl || !isLive}
                onClick={() => {
                  if (publicUrl) {
                    window.open(publicUrl, "_blank", "noopener,noreferrer");
                  }
                }}
              >
                <ExternalLink className="size-3.5" />
                <span>Xem trước</span>
              </Button>
            </div>
          </div>
          {baseline.data.configured && baseline.data.updated_at ? (
            <p className="text-[11px] text-muted-foreground">
              Phiên bản {baseline.revision} · cập nhật{" "}
              {updatedAtFormatter.format(new Date(baseline.data.updated_at))}
              {baseline.data.updated_by
                ? ` bởi ${baseline.data.updated_by}`
                : ""}
            </p>
          ) : (
            <p className="text-[11px] text-muted-foreground">
              Kênh công khai chưa được thiết lập cho trợ lý này.
            </p>
          )}
          {isDirty ? (
            <p className="text-[11px] text-warning">
              Có thay đổi chưa lưu; liên kết phía trên phản ánh bản đã lưu gần
              nhất.
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Code2 className="size-4" />
            </div>
            <div>
              <CardTitle className="text-sm">Nhúng vào website</CardTitle>
              <CardDescription>
                Dán mã bên dưới vào trang của đơn vị để khách trò chuyện ngay
                trên website, không cần mở liên kết riêng.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field>
            <FieldLabel className="text-xs font-medium">
              Tên miền được phép nhúng
            </FieldLabel>
            <Textarea
              value={form.allowedEmbedOrigins}
              onChange={(event) =>
                patch({ allowedEmbedOrigins: event.target.value })
              }
              placeholder={
                "Mỗi dòng một tên miền/origin (VD: https://qnu.edu.vn, http://localhost:3000).\nĐể trống nghĩa là chỉ cho phép chính hệ thống này (self)."
              }
              rows={3}
              className="resize-none bg-background font-mono text-xs leading-relaxed"
              disabled={saveMutation.isPending}
            />
            <FieldDescription>
              Kiểm soát trang web nào được phép nhúng iframe trợ lý này. Để
              trống để giới hạn nội bộ.
            </FieldDescription>
          </Field>

          <div className="space-y-2">
            <FieldLabel className="text-xs font-medium">
              Mã nhúng iframe
            </FieldLabel>
            <Textarea
              readOnly
              value={embedSnippet}
              placeholder="Lưu cấu hình để nhận mã nhúng"
              rows={3}
              className="resize-none bg-muted/30 font-mono text-[11px] leading-relaxed"
              aria-label="Mã nhúng iframe"
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[11px] text-muted-foreground">
                {isLive
                  ? "Mã nhúng hoạt động ngay khi kênh đang công khai; có thể chỉnh height cho vừa khung website."
                  : "Mã nhúng chỉ hiển thị trò chuyện khi kênh công khai đang bật."}
              </p>
              <div className="flex shrink-0 items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={!embedUrl}
                  onClick={() => void handleCopySnippet()}
                >
                  <Copy className="size-3.5" />
                  <span>Sao chép mã</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={!embedUrl || !isLive}
                  onClick={() => {
                    if (embedUrl) {
                      window.open(embedUrl, "_blank", "noopener,noreferrer");
                    }
                  }}
                >
                  <ExternalLink className="size-3.5" />
                  <span>Xem dạng nhúng</span>
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <PublicationStatsCard
        workspaceId={workspaceId}
        assistantId={assistant.id}
      />

      <div className="sticky bottom-4 z-10 flex flex-col gap-2 rounded-lg border border-border/70 bg-card/95 px-4 py-3 shadow-sm backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium text-foreground">
            {isDirty
              ? "Có thay đổi chưa lưu"
              : baseline.data.configured
                ? `Đã lưu · phiên bản ${baseline.revision}`
                : "Chưa thiết lập kênh công khai"}
          </p>
          <p className="text-[11px] text-muted-foreground">
            Khách ẩn danh không thấy mã đơn vị, kho hay tài liệu nội bộ.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={!isDirty || saveMutation.isPending}
            onClick={handleReset}
          >
            <Undo2 className="size-3.5" />
            <span>Hoàn tác</span>
          </Button>
          <Button
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={!isDirty || saveMutation.isPending}
            onClick={() => void handleSave()}
          >
            {saveMutation.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Save className="size-3.5" />
            )}
            <span>
              {saveMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
}

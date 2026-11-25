import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  CheckCircle2,
  Copy,
  Cpu,
  Database,
  GraduationCap,
  Loader2,
  MessageCircle,
  Plus,
  Quote,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  User,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  type AssistantResponse,
  useAssistantReadinessQuery,
  useAssistantsQuery,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import {
  type ConversationTurn,
  conversationKeys,
  type DocumentDraft,
  downloadTurnExport,
  type ExportFormat,
  useAssistantConversationsQuery,
  useConversationTurnsQuery,
  useCreateConversationMutation,
  useSendTurnMutation,
} from "@/api/conversations";
import { useCatalogQuery } from "@/api/modelops";
import { EmptyState } from "@/components/admin/empty-state";
import {
  DocumentDraftCard,
  DocumentPreviewPane,
  extractTurnDocumentDraft,
} from "@/components/assistants/document-preview-pane";
import { EvidenceDrawer } from "@/components/assistants/evidence-drawer";
import { providerLabel } from "@/components/assistants/model-label";
import { TurnFeedback } from "@/components/assistants/turn-feedback";
import {
  TURN_ERROR_TEXT,
  TurnResult,
} from "@/components/assistants/turn-result";
import { TurnTraceDetails } from "@/components/assistants/turn-trace";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useUiStore } from "@/lib/ui-store";
import { cn, sanitizeDisplayText } from "@/lib/utils";

export const Route = createFileRoute("/chat")({
  component: ChatPage,
  validateSearch: (search: Record<string, unknown>): { q?: string } => {
    const question = typeof search.q === "string" ? search.q.trim() : "";
    return question ? { q: question.slice(0, 500) } : {};
  },
});

const DRAFT_VALUE = "__draft__";
const DEFAULT_MODEL_VALUE = "__default__";
const MODEL_OVERRIDE_STORAGE_KEY = "qnu.chat.modelOverrides.v1";

function readStoredModelOverrides(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(MODEL_OVERRIDE_STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return Object.fromEntries(
      Object.entries(parsed).filter(
        (entry): entry is [string, string] =>
          typeof entry[0] === "string" &&
          typeof entry[1] === "string" &&
          entry[1].trim().length > 0,
      ),
    );
  } catch {
    return {};
  }
}

function writeStoredModelOverrides(map: Record<string, string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      MODEL_OVERRIDE_STORAGE_KEY,
      JSON.stringify(map),
    );
  } catch {
    // Ignore storage quota or private browsing errors.
  }
}

const SMART_STARTER_PROMPTS = [
  {
    icon: GraduationCap,
    tag: "Tuyển sinh 2025",
    title: "Chỉ tiêu SP Lịch sử - Địa lý",
    prompt:
      "Chỉ tiêu tuyển sinh ngành Sư phạm Lịch sử - Địa lý năm 2024 và 2025 là bao nhiêu?",
  },
  {
    icon: CheckCircle2,
    tag: "Quy chuẩn & Tiêu chí",
    title: "Tiêu chí chấm điểm LMS/LCMS",
    prompt:
      "Tiêu chí chấm điểm LMS/LCMS theo Quyết định 4740 gồm những chức năng nào và điểm tối đa là bao nhiêu?",
  },
  {
    icon: BookOpen,
    tag: "Phương thức",
    title: "Điều kiện xét tuyển học bạ",
    prompt:
      "Phương thức xét tuyển bằng học bạ năm 2025 có những điều kiện và mốc thời gian nào?",
  },
  {
    icon: Sparkles,
    tag: "Tra cứu kho",
    title: "Tài liệu đang có trong kho",
    prompt:
      "Trong kho tri thức hiện có những tài liệu, quyết định và kế hoạch nào đã được ban hành?",
  },
];

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function turnAnswerText(turn: ConversationTurn): string | null {
  if (!turn.result) return null;
  if (turn.result.status === "direct_reply") {
    const ans = turn.result.answer?.trim();
    return ans && ans !== "{}" ? ans : null;
  }
  const text =
    turn.result.statements.length > 0
      ? turn.result.statements.map((statement) => statement.text).join("\n")
      : (turn.result.answer ?? "");
  const trimmed = text.trim();
  return trimmed && trimmed !== "{}" ? trimmed : null;
}

function UserBubble({ question }: { question: string }) {
  return (
    <div className="flex justify-end gap-2.5">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-xs bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-2xs">
        {question}
      </div>
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/50 bg-muted text-muted-foreground">
        <User className="size-4" />
      </div>
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
      <Bot className="size-4" />
    </div>
  );
}

function TurnRow({
  turn,
  onCopy,
  onOpenEvidence,
  onPromptClick,
  enabledExportFormats = [],
  isActivePreview = false,
  downloadingFormat = null,
  onOpenPreview,
  onDownloadExport,
}: {
  turn: ConversationTurn;
  onCopy: (text: string) => void;
  onOpenEvidence?: (evidenceId?: string, index?: number) => void;
  onPromptClick?: (prompt: string) => void;
  enabledExportFormats?: ExportFormat[];
  isActivePreview?: boolean;
  downloadingFormat?: ExportFormat | null;
  onOpenPreview?: (draft: DocumentDraft) => void;
  onDownloadExport?: (format: ExportFormat, draft: DocumentDraft) => void;
}) {
  const copyText = turnAnswerText(turn);
  const documentDraft = useMemo(
    () => extractTurnDocumentDraft(turn.rewrite_trace),
    [turn.rewrite_trace],
  );
  const trace =
    turn.result && turn.result.status !== "direct_reply"
      ? turn.result.trace
      : null;

  const durationSec = useMemo(() => {
    if (!turn.finished_at || !turn.created_at) return null;
    const diff =
      (new Date(turn.finished_at).getTime() -
        new Date(turn.created_at).getTime()) /
      1000;
    return diff > 0 ? `${diff.toFixed(1)}s` : null;
  }, [turn.finished_at, turn.created_at]);

  const sourcesCount =
    turn.result && turn.result.status !== "direct_reply"
      ? turn.result.sources?.length ?? 0
      : 0;

  return (
    <div className="space-y-3">
      <UserBubble question={turn.question} />
      <div className="flex gap-2.5">
        <AssistantAvatar />
        <div className="min-w-0 flex-1 space-y-2.5 rounded-2xl rounded-tl-xs border border-border/50 bg-card px-4 py-3 shadow-2xs">
          <TurnResult
            turn={turn}
            onSelectEvidence={(evidenceId, idx) =>
              onOpenEvidence?.(evidenceId, idx)
            }
            onPromptClick={onPromptClick}
          />
          {documentDraft && enabledExportFormats.length > 0 ? (
            <DocumentDraftCard
              draft={documentDraft}
              enabledFormats={enabledExportFormats}
              isActivePreview={isActivePreview}
              downloadingFormat={downloadingFormat}
              onOpenPreview={() => onOpenPreview?.(documentDraft)}
              onDownload={(fmt) => onDownloadExport?.(fmt, documentDraft)}
            />
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/40 pt-1.5 text-[10px] text-muted-foreground">
            <div className="flex items-center gap-2 flex-wrap">
              <span>
                {formatTime(turn.created_at)}
                {durationSec ? ` (${durationSec})` : ""} · Lượt {turn.turn_no}
              </span>
              {trace ? <TurnTraceDetails turn={turn} trace={trace} /> : null}
              {sourcesCount > 0 && onOpenEvidence ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-5 px-1.5 text-[10px] gap-1 text-primary border-primary/30 hover:bg-primary/10 cursor-pointer shadow-2xs"
                  onClick={() => onOpenEvidence(undefined, 1)}
                  title="Mở ngăn đối soát nguồn dẫn chứng"
                >
                  <Quote className="size-2.5" />
                  <span>{sourcesCount} căn cứ đối soát</span>
                </Button>
              ) : null}
            </div>
            <div className="flex items-center gap-1">
              <TurnFeedback
                turnId={turn.id}
                conversationId={turn.conversation_id}
                initialFeedback={turn.feedback}
              />
              {copyText ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="relative size-6 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
                  title="Sao chép câu trả lời"
                  onClick={() => onCopy(copyText)}
                >
                  <Copy className="size-3" />
                  <span className="sr-only">Sao chép câu trả lời</span>
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PendingRow({
  question,
  onCancel,
}: {
  question: string;
  onCancel?: () => void;
}) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const stageText = useMemo(() => {
    if (seconds < 3) return "Đang phân tích câu hỏi & tra cứu kho tri thức...";
    if (seconds < 8) return "Đang đối soát bảng biểu & trích xuất dẫn chứng...";
    if (seconds < 16)
      return "Đang tổng hợp câu trả lời & kiểm chứng số liệu...";
    return "Câu hỏi phức tạp nhiều vế; đang hoàn tất câu trả lời...";
  }, [seconds]);

  return (
    <div className="space-y-3">
      <UserBubble question={question} />
      <div className="flex gap-2.5">
        <AssistantAvatar />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-3 rounded-2xl rounded-tl-xs border border-border/50 bg-card px-4 py-3 text-xs text-muted-foreground shadow-2xs">
          <div className="flex min-w-0 items-center gap-2.5">
            <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" />
            <span className="truncate">{stageText}</span>
            <span className="font-mono text-[10px] text-muted-foreground/70 shrink-0">
              ({seconds}s)
            </span>
          </div>
          {onCancel ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 px-2 text-[11px] gap-1 text-muted-foreground hover:text-destructive hover:border-destructive/40 cursor-pointer shrink-0"
              onClick={onCancel}
              title="Hủy lượt hỏi này"
            >
              <Square className="size-2.5 fill-current" />
              <span>Hủy</span>
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function WelcomePanel({
  assistant,
  isCollectionEmpty,
  isCollectionUnbound,
  onPick,
}: {
  assistant: AssistantResponse;
  isCollectionEmpty: boolean;
  isCollectionUnbound: boolean;
  onPick: (question: string) => void;
}) {
  const customPrompts = useMemo(() => {
    const prompts =
      assistant.rag_policy?.suggested_prompts ??
      (assistant.suggested_prompts ?? []);
    return prompts.map((p) => p.trim()).filter(Boolean);
  }, [assistant]);

  return (
    <div className="animate-in space-y-6 py-6 duration-300 fade-in-50 max-w-2xl mx-auto">
      <div className="space-y-2 text-center">
        <div className="mx-auto flex size-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary shadow-2xs">
          <Bot className="size-6" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-center gap-2">
            <h2 className="text-base font-semibold text-foreground">
              {assistant.name}
            </h2>
            <Badge
              variant={assistant.is_active ? "success" : "secondary"}
              className="h-4 px-1.5 text-[10px] font-normal"
            >
              {assistant.is_active ? "Sẵn sàng" : "Tạm dừng"}
            </Badge>
          </div>
          <p className="mx-auto max-w-md text-xs leading-relaxed text-muted-foreground">
            {sanitizeDisplayText(assistant.description) ||
              "Hệ thống trợ lý AI hỗ trợ tra cứu văn bản, đối chiếu số liệu bảng biểu và trích xuất nguồn dẫn chứng chính thức."}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <p className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-1.5">
            <Sparkles className="size-3 text-primary" />
            <span>Câu hỏi gợi ý</span>
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {customPrompts.length > 0
            ? customPrompts.map((promptText, idx) => (
                <button
                  key={`custom-prompt-${promptText.slice(0, 30)}-${idx}`}
                  type="button"
                  disabled={isCollectionUnbound}
                  onClick={() => onPick(promptText)}
                  className={cn(
                    "group flex flex-col items-start gap-1.5 rounded-xl border border-border/60 bg-card p-3 text-left transition-all duration-200 shadow-2xs hover:border-primary/40 hover:bg-muted/30 cursor-pointer",
                    isCollectionUnbound && "opacity-50 cursor-not-allowed",
                  )}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                      <Sparkles className="size-3.5 text-primary shrink-0" />
                      <span>Gợi ý {idx + 1}</span>
                    </span>
                    <Badge
                      variant="outline"
                      className="h-4 px-1 text-[9px] font-normal text-muted-foreground border-border/50"
                    >
                      Mẫu câu
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                    "{promptText}"
                  </p>
                </button>
              ))
            : SMART_STARTER_PROMPTS.map((item) => (
                <button
                  key={item.title}
                  type="button"
                  disabled={isCollectionUnbound}
                  onClick={() => onPick(item.prompt)}
                  className={cn(
                    "group flex flex-col items-start gap-1.5 rounded-xl border border-border/60 bg-card p-3 text-left transition-all duration-200 shadow-2xs hover:border-primary/40 hover:bg-muted/30 cursor-pointer",
                    isCollectionUnbound && "opacity-50 cursor-not-allowed",
                  )}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                      <item.icon className="size-3.5 text-primary shrink-0" />
                      <span>{item.title}</span>
                    </span>
                    <Badge
                      variant="outline"
                      className="h-4 px-1 text-[9px] font-normal text-muted-foreground border-border/50"
                    >
                      {item.tag}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                    "{item.prompt}"
                  </p>
                </button>
              ))}
        </div>

        <p className="px-1 text-center text-[11px] leading-relaxed text-muted-foreground">
          {isCollectionUnbound
            ? "Trợ lý hoạt động ở chế độ hội thoại trực tiếp với mô hình AI theo Persona cấu hình."
            : isCollectionEmpty
              ? "Kho tri thức chưa có tài liệu xuất bản nên hiện chỉ trả lời được câu hỏi chào hỏi, giới thiệu."
              : "Câu trả lời được đối soát trực tiếp từ kho tri thức và có trích dẫn [1], [2] để kiểm chứng."}
        </p>
      </div>
    </div>
  );
}

function ChatPage() {
  const workspaceId = useUiStore((state) => state.activeWorkspaceId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const [selectedAssistantId, setSelectedAssistantId] = useState<string | null>(
    null,
  );
  const [selectedConversationId, setSelectedConversationId] = useState<
    string | null
  >(null);
  const [isDraftMode, setIsDraftMode] = useState(false);
  const [localTurn, setLocalTurn] = useState<{
    conversationId: string;
    turnNo: number;
  } | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const { q: presetQuestion } = Route.useSearch();

  const [evidenceState, setEvidenceState] = useState<{
    open: boolean;
    sources: any[];
    selectedEvidenceId?: string | null;
    selectedIndex?: number | null;
    turnNo?: number;
    question?: string;
  }>({
    open: false,
    sources: [],
  });
  const [previewState, setPreviewState] = useState<{
    turnId: string;
    conversationId: string;
    draft: DocumentDraft;
  } | null>(null);
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(false);
  const [downloadingState, setDownloadingState] = useState<{
    turnId: string;
    format: ExportFormat;
  } | null>(null);

  // A question handed over from the landing page prefills the composer once,
  // then the query param is dropped so a reload starts a clean conversation.
  useEffect(() => {
    if (!presetQuestion) return;
    setInput(presetQuestion);
    void navigate({ to: "/chat", search: {}, replace: true });
  }, [presetQuestion, navigate]);

  const assistantsQuery = useAssistantsQuery(workspaceId);
  const assistants = assistantsQuery.data ?? [];

  const assistant = useMemo(() => {
    if (selectedAssistantId) {
      const selected = assistants.find(
        (item) => item.id === selectedAssistantId,
      );
      if (selected) return selected;
    }
    return assistants.find((item) => item.is_active) ?? assistants[0] ?? null;
  }, [assistants, selectedAssistantId]);

  const enabledExportFormats = useMemo<ExportFormat[]>(() => {
    const policy = assistant?.rag_policy;
    const formats: ExportFormat[] = [];
    if (policy?.allow_export_docx) formats.push("docx");
    if (policy?.allow_export_pdf) formats.push("pdf");
    if (policy?.allow_export_xlsx) formats.push("xlsx");
    return formats;
  }, [assistant?.rag_policy]);

  const conversationsQuery = useAssistantConversationsQuery(
    workspaceId,
    assistant?.id,
  );
  const conversations = conversationsQuery.data ?? [];

  const activeConversationId = isDraftMode
    ? null
    : selectedConversationId ?? conversations[0]?.id ?? null;

  const activeConversation = useMemo(() => {
    if (isDraftMode || !activeConversationId) return null;
    return (
      conversations.find((item) => item.id === activeConversationId) ?? null
    );
  }, [conversations, isDraftMode, activeConversationId]);

  const turnsQuery = useConversationTurnsQuery(
    workspaceId,
    activeConversationId,
    !isDraftMode,
  );
  const turns = turnsQuery.data ?? [];

  const readinessQuery = useAssistantReadinessQuery(workspaceId, assistant?.id);
  const readiness = readinessQuery.data;

  const catalogQuery = useCatalogQuery(workspaceId, Boolean(workspaceId));
  const chatModels = useMemo(
    () =>
      (catalogQuery.data ?? []).filter((item) =>
        item.capabilities.includes("chat"),
      ),
    [catalogQuery.data],
  );

  const [modelOverrides, setModelOverrides] = useState<Record<string, string>>(
    () => readStoredModelOverrides(),
  );

  const modelSessionKey = useMemo(() => {
    if (!workspaceId || !assistant) return null;
    const scope = activeConversationId ?? DRAFT_VALUE;
    return `${workspaceId}:${assistant.id}:${scope}`;
  }, [workspaceId, assistant, activeConversationId]);

  const storedModelId = modelSessionKey
    ? (modelOverrides[modelSessionKey] ?? null)
    : null;
  const selectedModelItem = useMemo(() => {
    if (!storedModelId) return null;
    return chatModels.find((entry) => entry.id === storedModelId) ?? null;
  }, [chatModels, storedModelId]);
  const effectiveModelId = selectedModelItem ? selectedModelItem.id : null;
  const modelSelectValue = effectiveModelId ?? DEFAULT_MODEL_VALUE;

  const createMutation = useCreateConversationMutation(workspaceId);
  const sendMutation = useSendTurnMutation(workspaceId);

  const isSending = pendingQuestion !== null;
  const isInactive = assistant ? !assistant.is_active : false;
  const isCollectionUnbound =
    Boolean(assistant) && (assistant?.collection_ids?.length ?? 0) === 0;
  const isCollectionEmpty =
    !isCollectionUnbound && readiness?.status === "empty";
  const isIndexWarning =
    readiness?.status === "outdated" ||
    readiness?.status === "not_indexed" ||
    readiness?.status === "failed" ||
    readiness?.status === "uncertain" ||
    readiness?.status === "syncing";
  const isComposerDisabled =
    !assistant ||
    isInactive ||
    isSending ||
    !workspaceId;

  const modelLabel = useMemo(() => {
    if (!assistant) return "";
    if (selectedModelItem) {
      return `Mô hình: ${providerLabel(selectedModelItem)} (tùy chọn phiên)`;
    }
    if (assistant.chat_provider_id) {
      const item = catalogQuery.data?.find(
        (entry) => entry.id === assistant.chat_provider_id,
      );
      return item ? `Mô hình: ${providerLabel(item)}` : "Mô hình đã cấu hình";
    }
    const systemDefault = chatModels.find((entry) =>
      entry.default_capabilities.includes("chat"),
    );
    return systemDefault
      ? `Mô hình: ${providerLabel(systemDefault)} (mặc định)`
      : "Dùng mô hình mặc định của hệ thống";
  }, [assistant, catalogQuery.data, chatModels, selectedModelItem]);

  const handleModelChange = (value: string) => {
    if (isSending || !modelSessionKey) return;
    setModelOverrides((prev) => {
      const next = { ...prev };
      if (value === DEFAULT_MODEL_VALUE) {
        delete next[modelSessionKey];
      } else {
        next[modelSessionKey] = value;
      }
      writeStoredModelOverrides(next);
      return next;
    });
  };

  const turnCount = turns.length;

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    if (turnCount === 0 && !pendingQuestion && !activeConversationId) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [turnCount, pendingQuestion, activeConversationId]);

  const handleAssistantChange = (assistantId: string) => {
    if (isSending) return;
    setSelectedAssistantId(assistantId);
    setSelectedConversationId(null);
    setIsDraftMode(false);
    setLocalTurn(null);
    setInput("");
  };

  const handleConversationChange = (value: string) => {
    if (isSending) return;
    setLocalTurn(null);
    if (value === DRAFT_VALUE) {
      setSelectedConversationId(null);
      setIsDraftMode(true);
      return;
    }
    setSelectedConversationId(value);
    setIsDraftMode(false);
  };

  const handleNewConversation = () => {
    if (isSending) return;
    setSelectedConversationId(null);
    setIsDraftMode(true);
    setLocalTurn(null);
    setInput("");
  };

  const handleRefresh = () => {
    void conversationsQuery.refetch();
    if (activeConversationId) {
      void turnsQuery.refetch();
    }
  };

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Đã sao chép câu trả lời.");
    } catch {
      toast.error("Trình duyệt không cho phép sao chép nội dung.");
    }
  };

  const appendTurnToCache = (
    conversationId: string,
    turn: ConversationTurn,
  ) => {
    if (!workspaceId) return;
    const key = conversationKeys.turns(workspaceId, conversationId);
    queryClient.setQueryData<ConversationTurn[]>(key, (previous) =>
      previous
        ? [...previous.filter((item) => item.id !== turn.id), turn].sort(
            (left, right) => left.turn_no - right.turn_no,
          )
        : [turn],
    );
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setPendingQuestion(null);
    toast.info("Đã hủy lượt hỏi.");
  };

  const handleSendError = (error: unknown, failedQuestion?: string) => {
    setLocalTurn(null);
    const restoreQuestion = () => {
      if (failedQuestion) {
        setInput((prev) => (prev.trim() ? prev : failedQuestion));
      }
    };
    if (!(error instanceof ApiProblemError)) {
      if (error instanceof Error && error.name === "AbortError") {
        toast.info("Đã hủy lượt hỏi.");
        return;
      }
      restoreQuestion();
      toast.error(
        error instanceof Error ? error.message : "Không gửi được câu hỏi.",
      );
      return;
    }
    if (error.status === 0) {
      restoreQuestion();
      toast.error(
        "Không kết nối được máy chủ hoặc yêu cầu bị quá thời gian. Vui lòng thử lại.",
      );
      return;
    }
    if (error.code === "conversation_sequence_conflict") {
      restoreQuestion();
      toast.error(
        "Hội thoại vừa thay đổi ở nơi khác. Danh sách đã được tải lại; hãy gửi lại câu hỏi.",
      );
      return;
    }
    if (error.code === "conversation_busy") {
      restoreQuestion();
      toast.warning(
        "Hội thoại đang xử lý một lượt khác. Chờ lượt đó xong rồi gửi lại.",
      );
      return;
    }
    if (error.code === "idempotency_conflict") {
      restoreQuestion();
      toast.error("Yêu cầu bị trùng mã gửi. Hãy gửi lại câu hỏi.");
      return;
    }
    if (error.code === "request_aborted") {
      toast.info("Đã hủy lượt hỏi.");
      return;
    }
    if (error.status >= 500) {
      restoreQuestion();
    }
    const mapped = TURN_ERROR_TEXT[error.code];
    if (mapped) {
      toast.error(`${mapped} Lượt hỏi đã được ghi nhận trong hội thoại.`);
      return;
    }
    toast.error(error.message || "Không gửi được câu hỏi.");
  };

  useEffect(() => {
    setPreviewState(null);
    setIsPreviewExpanded(false);
  }, [assistant?.id, activeConversationId]);

  const handleDownloadExport = async (
    conversationId: string,
    turnId: string,
    format: ExportFormat,
    draft: DocumentDraft,
  ) => {
    if (!workspaceId || downloadingState !== null) return;
    setDownloadingState({ turnId, format });
    try {
      const filename = await downloadTurnExport(
        workspaceId,
        conversationId,
        turnId,
        format,
        draft.title,
      );
      toast.success(`Đã tải xuống ${filename}`);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        toast.error(error.message);
      } else {
        toast.error(`Chưa xuất được tệp ${format.toUpperCase()}.`);
      }
    } finally {
      setDownloadingState(null);
    }
  };

  const handleSend = async (questionOverride?: string) => {
    const question = (questionOverride ?? input).trim();
    if (!question || isSending || !assistant) return;
    if (!assistant.is_active) {
      toast.error("Trợ lý đang tạm dừng nên không nhận câu hỏi mới.");
      return;
    }
    if (!workspaceId) return;

    setInput("");
    setPendingQuestion(question);
    const assistantId = assistant.id;
    const selectedModelForSend = effectiveModelId;

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      let conversation = activeConversation;
      if (!conversation) {
        conversation = await createMutation.mutateAsync({
          assistantId,
          title: question.slice(0, 160),
        });
        if (selectedModelForSend) {
          const newConversationKey = `${workspaceId}:${assistantId}:${conversation.id}`;
          setModelOverrides((prev) => {
            const next = { ...prev, [newConversationKey]: selectedModelForSend };
            writeStoredModelOverrides(next);
            return next;
          });
        }
        setSelectedConversationId(conversation.id);
        setIsDraftMode(false);
      }

      const expectedTurnNo =
        localTurn && localTurn.conversationId === conversation.id
          ? localTurn.turnNo
          : conversation.last_turn_no;

      const conversationId = conversation.id;
      const turn = await sendMutation.mutateAsync({
        conversationId,
        question,
        expectedTurnNo,
        model: selectedModelForSend,
        signal: controller.signal,
      });

      appendTurnToCache(conversationId, turn);
      setLocalTurn({ conversationId, turnNo: turn.turn_no });

      if (enabledExportFormats.length > 0) {
        const draft = extractTurnDocumentDraft(turn.rewrite_trace);
        if (draft) {
          setPreviewState({ turnId: turn.id, conversationId, draft });
        }
      }

      if (turn.status === "failed") {
        toast.error(
          TURN_ERROR_TEXT[turn.error_code ?? ""] ?? "Lượt hỏi thất bại.",
        );
      } else if (turn.status === "uncertain") {
        toast.warning("Lượt hỏi bị gián đoạn trước khi hoàn tất.");
      }
    } catch (error) {
      handleSendError(error, question);
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setPendingQuestion(null);
    }
  };

  if (!workspaceId) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center bg-background px-4">
        <EmptyState
          icon={MessageCircle}
          title="Chưa chọn đơn vị"
          description="Chọn đơn vị ở thanh bên để sử dụng trợ lý."
        />
      </div>
    );
  }

  if (assistantsQuery.isLoading) {
    return (
      <div className="flex h-full min-h-0 flex-col gap-3 bg-background p-4">
        <Skeleton className="h-14 w-full" />
        <div className="mx-auto w-full max-w-3xl space-y-3 pt-6">
          <Skeleton className="ml-auto h-12 w-2/3" />
          <Skeleton className="h-36 w-full" />
          <Skeleton className="ml-auto h-12 w-1/2" />
        </div>
      </div>
    );
  }

  if (assistantsQuery.isError) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center bg-background px-4">
        <EmptyState
          icon={Bot}
          title="Không tải được danh sách trợ lý"
          description={
            assistantsQuery.error instanceof Error
              ? assistantsQuery.error.message
              : "Lỗi không xác định."
          }
          action={{
            label: "Thử lại",
            onClick: () => void assistantsQuery.refetch(),
          }}
        />
      </div>
    );
  }

  if (!assistant) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center bg-background px-4">
        <EmptyState
          icon={Bot}
          title="Chưa có trợ lý"
          description="Tạo trợ lý trong mục Trợ lý và gắn kho tri thức trước khi bắt đầu hội thoại."
          action={{
            label: "Mở danh sách trợ lý",
            onClick: () => void navigate({ to: "/assistants" }),
          }}
        />
      </div>
    );
  }

  const conversationValue = isDraftMode
    ? DRAFT_VALUE
    : (activeConversation?.id ?? DRAFT_VALUE);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-card px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
            <Bot className="size-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-sm font-semibold text-foreground">
                {assistant.name}
              </h1>
              <Badge
                variant={assistant.is_active ? "success" : "secondary"}
                className="h-4 shrink-0 px-1.5 text-[10px] font-normal"
              >
                {assistant.is_active ? "Hoạt động" : "Tạm dừng"}
              </Badge>
            </div>
            <p className="truncate text-[11px] text-muted-foreground">
              {modelLabel}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={assistant.id}
            onValueChange={handleAssistantChange}
            disabled={isSending}
          >
            <SelectTrigger
              className="h-8 w-[170px] text-xs"
              aria-label="Chọn trợ lý"
            >
              <Bot className="size-3.5 text-muted-foreground" />
              <SelectValue placeholder="Chọn trợ lý" />
            </SelectTrigger>
            <SelectContent>
              {assistants.map((item) => (
                <SelectItem key={item.id} value={item.id} className="text-xs">
                  {item.is_active ? item.name : `${item.name} (tạm dừng)`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={modelSelectValue}
            onValueChange={handleModelChange}
            disabled={isSending || catalogQuery.isLoading}
          >
            <SelectTrigger
              className="h-8 w-[195px] text-xs"
              aria-label="Chọn mô hình AI"
              title={
                selectedModelItem
                  ? `Đang dùng: ${providerLabel(selectedModelItem)}`
                  : "Mặc định theo trợ lý"
              }
            >
              <Cpu className="size-3.5 shrink-0 text-muted-foreground" />
              <SelectValue placeholder="Mặc định theo trợ lý" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={DEFAULT_MODEL_VALUE} className="text-xs">
                Mặc định theo trợ lý
              </SelectItem>
              {chatModels.map((item) => (
                <SelectItem key={item.id} value={item.id} className="text-xs">
                  {providerLabel(item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={conversationValue}
            onValueChange={handleConversationChange}
            disabled={isSending}
          >
            <SelectTrigger
              className="h-8 w-[200px] text-xs"
              aria-label="Chọn hội thoại"
            >
              <MessageCircle className="size-3.5 text-muted-foreground" />
              <SelectValue placeholder="Chọn hội thoại" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={DRAFT_VALUE} className="text-xs">
                Hội thoại mới
              </SelectItem>
              {conversations.map((conversation) => (
                <SelectItem
                  key={conversation.id}
                  value={conversation.id}
                  className="text-xs"
                >
                  {conversation.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={handleNewConversation}
            disabled={isSending}
          >
            <Plus className="size-3.5" />
            <span className="hidden sm:inline">Hội thoại mới</span>
            <span className="sr-only sm:hidden">Hội thoại mới</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground"
            title="Tải lại hội thoại"
            onClick={handleRefresh}
            disabled={
              isSending ||
              conversationsQuery.isFetching ||
              turnsQuery.isFetching
            }
          >
            <RefreshCw
              className={cn(
                "size-4",
                (conversationsQuery.isFetching || turnsQuery.isFetching) &&
                  "animate-spin",
              )}
            />
            <span className="sr-only">Tải lại hội thoại</span>
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col overflow-hidden",
          previewState && enabledExportFormats.length > 0 && "hidden lg:flex",
        )}
      >
      <div ref={scrollRef} className="relative min-h-0 flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto w-full max-w-3xl space-y-5">
          {isInactive ? (
            <Alert variant="warning">
              <AlertTitle>Trợ lý đang tạm dừng</AlertTitle>
              <AlertDescription>
                Bật lại trợ lý trong trang Trợ lý trước khi tiếp tục hội thoại.
              </AlertDescription>
            </Alert>
          ) : null}

          {!isInactive && isCollectionEmpty ? (
            <Alert variant="warning">
              <AlertTitle>Kho tri thức chưa có tài liệu xuất bản</AlertTitle>
              <AlertDescription>
                <span>
                  Trợ lý chỉ trả lời từ nội dung đã xuất bản. Câu hỏi tra cứu sẽ
                  lỗi cho tới khi kho có ít nhất một tài liệu được xuất bản và
                  lập chỉ mục.
                </span>
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="mt-2 h-7 gap-1.5 text-xs"
                >
                  <Link
                    to="/knowledge"
                    search={{
                      collectionId: assistant.collection_id ?? undefined,
                    }}
                  >
                    <Database className="size-3.5" />
                    <span>Mở kho tri thức</span>
                  </Link>
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          {!isInactive && !isCollectionEmpty && isIndexWarning ? (
            <Alert variant="info">
              <AlertTitle>Chỉ mục chưa sẵn sàng</AlertTitle>
              <AlertDescription>
                Kho có thể đang chờ nạp lại chỉ mục; câu trả lời có thể thiếu
                nguồn cho tới khi quá trình này hoàn tất.
              </AlertDescription>
            </Alert>
          ) : null}

          {conversationsQuery.isError && conversations.length === 0 ? (
            <Alert variant="destructive">
              <AlertTitle>Không tải được danh sách hội thoại</AlertTitle>
              <AlertDescription>
                <span>
                  {conversationsQuery.error instanceof Error
                    ? conversationsQuery.error.message
                    : "Lỗi không xác định."}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 h-7 text-xs"
                  onClick={() => void conversationsQuery.refetch()}
                >
                  Thử lại
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          {turnsQuery.isLoading && !isDraftMode ? (
            <div className="space-y-4 pt-2">
              <Skeleton className="ml-auto h-12 w-2/3" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : turnsQuery.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Không tải được lượt hỏi</AlertTitle>
              <AlertDescription>
                <span>
                  {turnsQuery.error instanceof Error
                    ? turnsQuery.error.message
                    : "Lỗi không xác định."}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 h-7 text-xs"
                  onClick={() => void turnsQuery.refetch()}
                >
                  Thử lại
                </Button>
              </AlertDescription>
            </Alert>
          ) : turns.length === 0 && !pendingQuestion ? (
            <WelcomePanel
              assistant={assistant}
              isCollectionEmpty={Boolean(isCollectionEmpty)}
              isCollectionUnbound={isCollectionUnbound}
              onPick={(question) => void handleSend(question)}
            />
          ) : (
            <>
              {turns.map((turn) => (
                <TurnRow
                  key={turn.id}
                  turn={turn}
                  onCopy={(text) => void handleCopy(text)}
                  onOpenEvidence={(evidenceId, idx) => {
                    const sources =
                      turn.result && turn.result.status !== "direct_reply"
                        ? turn.result.sources
                        : [];
                    setEvidenceState({
                      open: true,
                      sources,
                      selectedEvidenceId: evidenceId,
                      selectedIndex: idx,
                      turnNo: turn.turn_no,
                      question: turn.question,
                    });
                  }}
                  onPromptClick={(prompt) => void handleSend(prompt)}
                  enabledExportFormats={enabledExportFormats}
                  isActivePreview={previewState?.turnId === turn.id}
                  downloadingFormat={
                    downloadingState?.turnId === turn.id
                      ? downloadingState.format
                      : null
                  }
                  onOpenPreview={(draft) => {
                    setPreviewState({
                      turnId: turn.id,
                      conversationId: turn.conversation_id,
                      draft,
                    });
                  }}
                  onDownloadExport={(format, draft) => {
                    void handleDownloadExport(
                      turn.conversation_id,
                      turn.id,
                      format,
                      draft,
                    );
                  }}
                />
              ))}
              {pendingQuestion && !turns.some((t) => t.status === "running") ? (
                <PendingRow
                  question={pendingQuestion}
                  onCancel={handleCancel}
                />
              ) : null}
            </>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-border/60 bg-card p-3">
        <div className="mx-auto w-full max-w-3xl">
          <div className="flex items-end gap-2 rounded-xl border border-border/60 bg-muted/40 p-1.5 shadow-2xs transition-colors focus-within:border-primary/60 focus-within:bg-background">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void handleSend();
                }
              }}
              placeholder={
                isInactive
                  ? "Trợ lý đang tạm dừng nhận câu hỏi..."
                  : "Nhập câu hỏi..."
              }
              rows={1}
              maxLength={8000}
              disabled={isComposerDisabled}
              className="max-h-32 min-h-[38px] flex-1 resize-none border-0 bg-transparent px-3 py-2 text-xs leading-relaxed shadow-none placeholder:text-muted-foreground focus-visible:ring-0"
            />
            <Button
              size="sm"
              onClick={() => void handleSend()}
              disabled={isComposerDisabled || !input.trim()}
              className="h-8 shrink-0 gap-1.5 rounded-lg px-3 text-xs font-medium shadow-2xs"
            >
              {isSending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Send className="size-3.5" />
              )}
              <span className="hidden sm:inline">
                {isSending ? "Đang gửi" : "Gửi"}
              </span>
            </Button>
          </div>
        </div>
      </div>
      </div>

      {previewState && enabledExportFormats.length > 0 ? (
        <DocumentPreviewPane
          draft={previewState.draft}
          enabledFormats={enabledExportFormats}
          downloadingFormat={
            downloadingState?.turnId === previewState.turnId
              ? downloadingState.format
              : null
          }
          isExpanded={isPreviewExpanded}
          onToggleExpand={() => setIsPreviewExpanded((prev) => !prev)}
          onDownload={(format) => {
            void handleDownloadExport(
              previewState.conversationId,
              previewState.turnId,
              format,
              previewState.draft,
            );
          }}
          onClose={() => {
            setPreviewState(null);
            setIsPreviewExpanded(false);
          }}
        />
      ) : null}
      </div>

      <EvidenceDrawer
        open={evidenceState.open}
        onOpenChange={(open) =>
          setEvidenceState((prev) => ({ ...prev, open }))
        }
        sources={evidenceState.sources}
        selectedEvidenceId={evidenceState.selectedEvidenceId}
        selectedIndex={evidenceState.selectedIndex}
        turnNo={evidenceState.turnNo}
        question={evidenceState.question}
      />
    </div>
  );
}

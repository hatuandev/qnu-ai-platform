import {
  ArrowDown,
  ArrowUp,
  Cpu,
  MoreHorizontal,
  Plus,
  Star,
  Trash2,
} from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/api/client";
import {
  type DocumentMode,
  type DocumentModelEntry,
  type DocumentProcessingSettings,
  THINKING_LEVEL_LABEL,
  useDocumentProcessing,
} from "@/api/modelops/document-processing";
import type { Connection, ModelProvider } from "@/api/modelops/types";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { formatModelLabel, formatProviderLabel } from "@/lib/default-models";

type DraftModel = { provider_id: string; concurrency: number };

type Draft = {
  base: DocumentProcessingSettings;
  mode: DocumentMode;
  models: DraftModel[];
};

const MODE_OPTIONS: {
  value: DocumentMode;
  title: string;
  description: string;
}[] = [
  {
    value: "priority",
    title: "Một model ưu tiên",
    description:
      "Mọi tác vụ dùng model đầu danh sách; các model còn lại chưa tham gia.",
  },
  {
    value: "parallel",
    title: "Nhiều model song song",
    description:
      "Các phần độc lập chạy trên nhiều model theo số lượt đã đặt; model xong trước nhận phần tiếp theo (work-stealing). Áp dụng cho biên soạn và soát chính tả.",
  },
];

function thinkingLabel(entry: DocumentModelEntry | undefined): string {
  if (!entry) return "Chưa áp dụng";
  const { thinking } = entry;
  const label = THINKING_LEVEL_LABEL[thinking.effective];
  return thinking.configured === thinking.effective
    ? label
    : `${label} (khai báo chưa xác minh)`;
}

export function DocumentProcessingPanel({
  models,
  connections,
}: {
  models: ModelProvider[];
  connections: Connection[];
}) {
  const { query, update } = useDocumentProcessing();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const policy = query.data;

  if (query.isPending) return <Skeleton className="h-64 w-full" />;
  if (query.isError || !policy) {
    return (
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p role="alert">Không tải được cài đặt xử lý văn bản.</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void query.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  }

  const serverModels: DraftModel[] = policy.models.map((model) => ({
    provider_id: model.provider_id,
    concurrency: model.concurrency,
  }));
  const hasDraft = draft !== null && draft.base === policy;
  const currentMode = hasDraft ? draft.mode : policy.mode;
  const currentModels = hasDraft ? draft.models : serverModels;
  const entryById = new Map(
    policy.models.map((model) => [model.provider_id, model]),
  );
  const providerById = new Map(models.map((model) => [model.id, model]));
  const isDirty =
    currentMode !== policy.mode ||
    currentModels.length !== serverModels.length ||
    currentModels.some(
      (model, index) =>
        model.provider_id !== serverModels[index].provider_id ||
        model.concurrency !== serverModels[index].concurrency,
    );
  const unavailableCount = policy.models.filter(
    (model) => !model.available,
  ).length;
  const limits = Array.from(
    { length: Math.min(policy.max_concurrency, 16) },
    (_, i) => i + 1,
  );

  const edit = (mode: DocumentMode, list: DraftModel[]) =>
    setDraft({ base: policy, mode, models: list });
  const move = (index: number, delta: number) => {
    const next = [...currentModels];
    const [item] = next.splice(index, 1);
    next.splice(index + delta, 0, item);
    edit(currentMode, next);
  };
  const promote = (index: number) => {
    const next = [...currentModels];
    const [item] = next.splice(index, 1);
    next.unshift(item);
    edit(currentMode, next);
  };
  const setLimit = (index: number, limit: number) =>
    edit(
      currentMode,
      currentModels.map((model, position) =>
        position === index ? { ...model, concurrency: limit } : model,
      ),
    );
  const remove = (index: number) =>
    edit(
      currentMode,
      currentModels.filter((_, position) => position !== index),
    );

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-base font-semibold">Xử lý văn bản</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Áp dụng cho biên soạn, chuẩn bị nội dung AI và rà soát bản biên soạn.
          Không ảnh hưởng model trò chuyện của trợ lý.
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-medium">Cách dùng model</h3>
        <ModeSelector
          value={currentMode}
          disabled={update.isPending}
          onChange={(mode) => edit(mode, currentModels)}
        />
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-medium">Model xử lý văn bản</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={update.isPending}
            onClick={() => setIsAdding(true)}
          >
            <Plus className="size-3.5" />
            Thêm model
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Danh sách theo thứ tự ưu tiên. Mỗi model chạy đúng số lượt đồng thời
          bạn chọn ở đây, tối đa {Math.min(policy.max_concurrency, 16)} lượt
          (khuyến nghị 1–4 để tránh quá tải GPU/VRAM).
        </p>
        {currentModels.length === 0 ? (
          <EmptyState
            icon={Cpu}
            title="Chưa thêm model nào"
            description="Khi danh sách trống, hệ thống dùng model trò chuyện mặc định cho mọi tác vụ văn bản."
            action={{ label: "Thêm model", onClick: () => setIsAdding(true) }}
          />
        ) : (
          <div className="divide-y divide-border border-y border-border">
            {currentModels.map((model, index) => {
              const entry = entryById.get(model.provider_id);
              const provider = providerById.get(model.provider_id);
              return (
                <ModelRow
                  key={model.provider_id}
                  entry={entry}
                  provider={provider}
                  mode={currentMode}
                  index={index}
                  total={currentModels.length}
                  concurrency={model.concurrency}
                  maxConcurrency={policy.max_concurrency}
                  limits={limits}
                  disabled={update.isPending}
                  onLimitChange={(limit) => setLimit(index, limit)}
                  onPromote={() => promote(index)}
                  onMove={(delta) => move(index, delta)}
                  onRemove={() => remove(index)}
                />
              );
            })}
          </div>
        )}
        {unavailableCount > 0 && (
          <p className="text-xs text-destructive">
            Model không khả dụng sẽ bị bỏ qua khi chạy cho đến khi được bật lại.
          </p>
        )}
      </div>

      <Button
        disabled={!isDirty || update.isPending}
        onClick={() =>
          update.mutate(
            { mode: currentMode, models: currentModels },
            {
              onSuccess: () => {
                setDraft(null);
                toast.success("Đã lưu cấu hình xử lý văn bản.");
              },
              onError: (error) =>
                toast.error(
                  error instanceof ApiProblemError
                    ? error.message
                    : "Chưa lưu được cấu hình xử lý văn bản.",
                ),
            },
          )
        }
      >
        {update.isPending ? "Đang lưu…" : "Lưu thay đổi"}
      </Button>

      <AddDocumentModelDialog
        open={isAdding}
        onOpenChange={setIsAdding}
        models={models}
        connections={connections}
        taken={currentModels.map((model) => model.provider_id)}
        maxConcurrency={policy.max_concurrency}
        onAdd={(providerId, concurrency) => {
          edit(currentMode, [
            ...currentModels,
            { provider_id: providerId, concurrency },
          ]);
          setIsAdding(false);
        }}
      />
    </section>
  );
}

function ModeSelector({
  value,
  disabled,
  onChange,
}: {
  value: DocumentMode;
  disabled: boolean;
  onChange: (mode: DocumentMode) => void;
}) {
  const groupId = useId();
  return (
    <RadioGroup
      value={value}
      disabled={disabled}
      onValueChange={(next) => onChange(next as DocumentMode)}
      className="grid gap-2 sm:grid-cols-2"
    >
      {MODE_OPTIONS.map((option) => {
        const id = `${groupId}-${option.value}`;
        const isActive = value === option.value;
        return (
          <div
            key={option.value}
            className={
              isActive
                ? "flex items-start gap-3 rounded-lg border border-primary/50 bg-primary/5 p-3"
                : "flex items-start gap-3 rounded-lg border border-border p-3"
            }
          >
            <RadioGroupItem id={id} value={option.value} className="mt-0.5" />
            <Label htmlFor={id} className="cursor-pointer space-y-0.5">
              <span className="block text-sm font-medium">{option.title}</span>
              <span className="block text-xs font-normal text-muted-foreground">
                {option.description}
              </span>
            </Label>
          </div>
        );
      })}
    </RadioGroup>
  );
}

function ModelRow({
  entry,
  provider,
  mode,
  index,
  total,
  concurrency,
  maxConcurrency,
  limits,
  disabled,
  onLimitChange,
  onPromote,
  onMove,
  onRemove,
}: {
  entry?: DocumentModelEntry;
  provider?: ModelProvider;
  mode: DocumentMode;
  index: number;
  total: number;
  concurrency: number;
  maxConcurrency: number;
  limits: number[];
  disabled: boolean;
  onLimitChange: (limit: number) => void;
  onPromote: () => void;
  onMove: (delta: number) => void;
  onRemove: () => void;
}) {
  const source = entry ?? provider;
  const label = source ? formatModelLabel(source) : "Model đã xóa";
  const providerName = source ? formatProviderLabel(source) : "Không xác định";
  const isUnavailable = entry !== undefined && !entry.available;

  return (
    <div className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="break-words text-sm font-medium">{label}</span>
          {index === 0 && mode === "priority" && (
            <Badge variant="default">Ưu tiên</Badge>
          )}
          {isUnavailable && <Badge variant="destructive">Không khả dụng</Badge>}
        </div>
        <p className="text-xs text-muted-foreground">
          {providerName} · Suy nghĩ: {thinkingLabel(entry)}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Select
          value={String(concurrency)}
          disabled={disabled}
          onValueChange={(limit) => onLimitChange(Number(limit))}
        >
          <SelectTrigger
            aria-label={`Số lượt đồng thời cho ${label}`}
            className="w-20 shrink-0"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {concurrency > maxConcurrency && (
              <SelectItem value={String(concurrency)} disabled>
                {concurrency} (giới hạn {maxConcurrency})
              </SelectItem>
            )}
            {limits.map((limit) => (
              <SelectItem key={limit} value={String(limit)}>
                {limit}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-8 shrink-0"
              aria-label={`Thao tác cho ${label}`}
              disabled={disabled}
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem disabled={index === 0} onSelect={onPromote}>
              <Star className="size-4" />
              Đặt ưu tiên
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={index === 0}
              onSelect={() => onMove(-1)}
            >
              <ArrowUp className="size-4" />
              Chuyển lên
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={index === total - 1}
              onSelect={() => onMove(1)}
            >
              <ArrowDown className="size-4" />
              Chuyển xuống
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={onRemove}>
              <Trash2 className="size-4" />
              Gỡ khỏi danh sách
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

function AddDocumentModelDialog({
  open,
  onOpenChange,
  models,
  connections,
  taken,
  maxConcurrency,
  onAdd,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  models: ModelProvider[];
  connections: Connection[];
  taken: string[];
  maxConcurrency: number;
  onAdd: (providerId: string, concurrency: number) => void;
}) {
  const fieldId = useId();
  const [connectionId, setConnectionId] = useState("");
  const [modelId, setModelId] = useState("");
  const [concurrency, setConcurrency] = useState(1);

  useEffect(() => {
    if (open) {
      setConnectionId("");
      setModelId("");
      setConcurrency(1);
    }
  }, [open]);

  const groups = useMemo(() => {
    const takenIds = new Set(taken);
    const byConnection = new Map<
      string,
      { label: string; models: ModelProvider[] }
    >();
    for (const model of models) {
      if (takenIds.has(model.id)) continue;
      const key = model.parent_id ?? "__standalone__";
      const group = byConnection.get(key) ?? {
        label:
          connections.find((connection) => connection.id === key)?.name ??
          "Model độc lập",
        models: [],
      };
      group.models.push(model);
      byConnection.set(key, group);
    }
    return [...byConnection.entries()].map(([id, group]) => ({ id, ...group }));
  }, [models, connections, taken]);

  const selectedGroup = groups.find((group) => group.id === connectionId);
  const safeMax = Math.min(maxConcurrency, 16);
  const limits = Array.from({ length: safeMax }, (_, i) => i + 1);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-md">
        <DialogHeader>
          <DialogTitle>Thêm model xử lý văn bản</DialogTitle>
          <DialogDescription>
            Chỉ model trò chuyện đang hoạt động thuộc nhà cung cấp đang bật mới
            thêm được, mỗi model một lần.
          </DialogDescription>
        </DialogHeader>
        {groups.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có model trò chuyện đang hoạt động để thêm.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-connection`}>Nhà cung cấp</Label>
              <Select
                value={connectionId}
                onValueChange={(value) => {
                  setConnectionId(value);
                  setModelId("");
                }}
              >
                <SelectTrigger id={`${fieldId}-connection`} className="w-full">
                  <SelectValue placeholder="Chọn nhà cung cấp" />
                </SelectTrigger>
                <SelectContent>
                  {groups.map((group) => (
                    <SelectItem key={group.id} value={group.id}>
                      {group.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-model`}>Model</Label>
              <Select
                value={modelId}
                disabled={selectedGroup === undefined}
                onValueChange={setModelId}
              >
                <SelectTrigger id={`${fieldId}-model`} className="w-full">
                  <SelectValue placeholder="Chọn model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>{selectedGroup?.label ?? "Model"}</SelectLabel>
                    {(selectedGroup?.models ?? []).map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.model_name}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-concurrency`}>
                Số lượt đồng thời
              </Label>
              <Select
                value={String(concurrency)}
                onValueChange={(value) => setConcurrency(Number(value))}
              >
                <SelectTrigger id={`${fieldId}-concurrency`} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {limits.map((limit) => (
                    <SelectItem key={limit} value={String(limit)}>
                      {limit}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Tối đa {safeMax} luồng đồng thời cho mỗi model (khuyến nghị
                1–4). Mặc định 1.
              </p>
            </div>
          </div>
        )}
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            type="button"
            disabled={!modelId}
            onClick={() => onAdd(modelId, concurrency)}
          >
            Thêm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

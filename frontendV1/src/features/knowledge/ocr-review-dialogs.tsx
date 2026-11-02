import { diffWordsWithSpace } from "diff";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  Clock,
  Info,
  Loader2,
  RotateCcw,
  Save,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  formatUnitLocator,
  MAX_SPELL_CHECK_UNITS,
} from "@/features/knowledge/ocr-schemas";
import type {
  ReviewDocument,
  TextChange,
} from "@/features/knowledge/ocr-types";
import { ConsumerModelBudgetNotice } from "@/features/modelops/capacity-badge";
import { useCatalogQuery } from "@/features/modelops/queries";

/**
 * Hiển thị so sánh chi tiết từng từ (Word-level diff) an toàn qua React nodes,
 * giúp cán bộ nhận diện ngay những chữ được sửa trong đoạn văn dài mà không dùng innerHTML.
 */
export function OcrWordDiffView({
  before,
  after,
  className,
}: {
  before: string;
  after: string;
  className?: string;
}) {
  const parts = useMemo(
    () => diffWordsWithSpace(before, after),
    [before, after],
  );

  return (
    <p
      data-testid="ocr-word-diff"
      className={
        className ??
        "whitespace-pre-wrap break-words leading-relaxed text-xs text-foreground"
      }
    >
      {parts.map((part, idx) => {
        const key = `${idx}-${part.added ? "add" : part.removed ? "del" : "eq"}`;
        if (part.removed) {
          return (
            <del
              key={key}
              className="line-through text-destructive bg-destructive/15 px-1 rounded-xs mx-0.5"
            >
              {part.value}
            </del>
          );
        }
        if (part.added) {
          return (
            <ins
              key={key}
              className="no-underline font-semibold text-success bg-success/15 px-1 rounded-xs mx-0.5"
            >
              {part.value}
            </ins>
          );
        }
        return <span key={key}>{part.value}</span>;
      })}
    </p>
  );
}

export function OcrSaveConfirmDialog({
  open,
  onOpenChange,
  doc,
  pendingChanges,
  baseMovedOn,
  isSaving,
  onConfirmSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  doc: ReviewDocument;
  pendingChanges: TextChange[];
  baseMovedOn: boolean;
  isSaving: boolean;
  onConfirmSave: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold flex items-center gap-2">
            <Save className="size-4 text-primary" />
            <span>Xác nhận lưu thay đổi ({pendingChanges.length} đoạn)</span>
          </DialogTitle>
          <DialogDescription className="text-xs">
            Lưu các thay đổi vào máy chủ sẽ tạo phiên bản văn bản hiệu đính mới
            (v{doc.version + 1}). Tệp OCR gốc và tài liệu nguồn được bảo toàn
            bất biến.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto space-y-3 py-2 pr-1">
          {pendingChanges.map((change) => {
            const unit = doc.units.find(
              (u) => u.evidence_id === change.evidence_id,
            );
            const locator = unit
              ? formatUnitLocator(unit, doc.units)
              : "Đoạn văn đã chỉnh sửa";
            return (
              <div
                key={change.evidence_id}
                className="p-3 rounded-lg border text-xs space-y-1.5 bg-muted/10"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-foreground">
                    {locator}
                  </span>
                  <Badge variant="outline" className="text-[10px] py-0">
                    Đánh dấu từ thay đổi
                  </Badge>
                </div>
                <div className="p-2.5 rounded-md bg-background border border-border/70">
                  <OcrWordDiffView
                    before={change.before}
                    after={change.after}
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-destructive/5 border border-destructive/20 text-destructive">
                    <span className="font-semibold block text-[10px] uppercase mb-0.5">
                      Trước khi sửa (v{doc.version}):
                    </span>
                    <p className="whitespace-pre-wrap break-words">
                      {change.before}
                    </p>
                  </div>
                  <div className="p-2 rounded bg-success/5 border border-success/20 text-success">
                    <span className="font-semibold block text-[10px] uppercase mb-0.5">
                      Sau khi sửa (v{doc.version + 1}):
                    </span>
                    <p className="whitespace-pre-wrap break-words">
                      {change.after}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <DialogFooter className="gap-2 sm:gap-0 border-t pt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={onConfirmSave}
            disabled={isSaving || baseMovedOn || pendingChanges.length === 0}
            className="gap-1.5"
          >
            {isSaving ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                <span>Đang lưu...</span>
              </>
            ) : (
              <>
                <Check className="size-3.5" />
                <span>Xác nhận lưu v{doc.version + 1}</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function OcrSpellCheckDialog({
  open,
  onOpenChange,
  workspaceId,
  doc,
  activePage,
  selectedUnitIds,
  onChangeSelectedUnitIds,
  providerId,
  onChangeProviderId,
  pendingDraftCount,
  isSubmitting,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  doc: ReviewDocument;
  activePage: number;
  selectedUnitIds: ReadonlySet<string>;
  onChangeSelectedUnitIds: (next: Set<string>) => void;
  providerId: string;
  onChangeProviderId: (providerId: string) => void;
  pendingDraftCount: number;
  isSubmitting: boolean;
  onSubmit: () => void;
}) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Measure actual elapsed time while request is in flight (no fake progress%)
  useEffect(() => {
    if (!isSubmitting) {
      setElapsedSeconds(0);
      return;
    }
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isSubmitting]);

  const catalogQuery = useCatalogQuery(workspaceId, { enabled: open });
  const chatProviders = useMemo(
    () =>
      (catalogQuery.data ?? []).filter((p) => p.capabilities.includes("chat")),
    [catalogQuery.data],
  );
  const defaultChatProvider = useMemo(
    () =>
      chatProviders.find((p) => p.default_capabilities?.includes("chat")) ??
      null,
    [chatProviders],
  );
  const selectedProviderItem = useMemo(
    () =>
      providerId === "default"
        ? defaultChatProvider
        : (chatProviders.find((p) => p.id === providerId) ?? null),
    [providerId, defaultChatProvider, chatProviders],
  );

  // Selectable non-empty text units in the document and on the active page
  const selectableUnits = useMemo(
    () =>
      doc.units.filter(
        (u) =>
          u.kind !== "image" && u.kind !== "figure" && u.text.trim().length > 0,
      ),
    [doc.units],
  );
  const currentPageUnits = useMemo(
    () => selectableUnits.filter((u) => u.page === activePage),
    [selectableUnits, activePage],
  );

  const selectedCount = selectedUnitIds.size;
  const exceedsLimit = selectedCount > MAX_SPELL_CHECK_UNITS;

  // Determine whether selection matches current page
  const isCurrentPageSelection = useMemo(() => {
    if (
      currentPageUnits.length === 0 ||
      selectedCount !== currentPageUnits.length
    ) {
      return false;
    }
    return currentPageUnits.every((u) => selectedUnitIds.has(u.evidence_id));
  }, [currentPageUnits, selectedCount, selectedUnitIds]);

  const handleToggleUnit = (evidenceId: string) => {
    const next = new Set(selectedUnitIds);
    if (next.has(evidenceId)) {
      next.delete(evidenceId);
    } else {
      next.add(evidenceId);
    }
    onChangeSelectedUnitIds(next);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            <span>Kiểm tra chính tả bằng AI</span>
          </DialogTitle>
          <DialogDescription className="text-xs">
            Chọn phạm vi đoạn văn và mô hình ngôn ngữ (Chat) để AI rà soát và đề
            xuất sửa lỗi chính tả tiếng Việt trên phiên bản v{doc.version}.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-2 pr-1 text-xs">
          {/* Unsaved Draft Notice */}
          {pendingDraftCount > 0 ? (
            <Alert className="border-warning/50 bg-warning/10 text-foreground py-2.5">
              <AlertTriangle className="size-4 text-warning" />
              <AlertTitle className="text-xs font-semibold">
                Lưu ý: Đang có {pendingDraftCount} đoạn sửa nháp chưa lưu
              </AlertTitle>
              <AlertDescription className="text-xs mt-1">
                AI chỉ kiểm tra phiên bản đã lưu trên máy chủ (
                <strong>Phiên bản v{doc.version}</strong>), không kiểm tra nội
                dung nháp chưa lưu trên màn hình. Nếu muốn AI kiểm tra cả các
                chữ bạn vừa sửa, hãy đóng cửa sổ này và bấm{" "}
                <strong>Lưu thay đổi</strong> trước.
              </AlertDescription>
            </Alert>
          ) : null}

          {/* 1. Scope & Unit Selection */}
          <div className="rounded-lg border p-3 space-y-2.5 bg-muted/20">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="space-y-0.5">
                <span className="font-semibold text-foreground block">
                  Phạm vi kiểm tra:{" "}
                  {isCurrentPageSelection
                    ? `Trang hiện tại (Trang ${activePage})`
                    : "Các đoạn/ô được chọn"}
                </span>
                <span className="text-muted-foreground text-[11px]">
                  Đã chọn{" "}
                  <strong className="text-foreground">{selectedCount}</strong>{" "}
                  đoạn/ô có chữ (Giới hạn: 1 – {MAX_SPELL_CHECK_UNITS}{" "}
                  đoạn/lượt)
                </span>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap">
                {currentPageUnits.length > 0 ? (
                  <Button
                    type="button"
                    size="sm"
                    variant={isCurrentPageSelection ? "secondary" : "outline"}
                    className="h-7 px-2 text-xs"
                    disabled={isSubmitting}
                    onClick={() =>
                      onChangeSelectedUnitIds(
                        new Set(currentPageUnits.map((u) => u.evidence_id)),
                      )
                    }
                  >
                    Chọn trang {activePage} ({currentPageUnits.length})
                  </Button>
                ) : null}
                {selectedCount > 0 ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-xs"
                    disabled={isSubmitting}
                    onClick={() => onChangeSelectedUnitIds(new Set())}
                  >
                    Bỏ chọn tất cả
                  </Button>
                ) : null}
              </div>
            </div>

            {/* Limit exceeded alert — never silently slice */}
            {exceedsLimit ? (
              <Alert variant="destructive" className="py-2">
                <AlertCircle className="size-4" />
                <AlertTitle className="text-xs font-semibold">
                  Vượt giới hạn số đoạn cho một lượt kiểm tra
                </AlertTitle>
                <AlertDescription className="text-xs mt-0.5">
                  Bạn đang chọn {selectedCount} đoạn, vượt quá giới hạn tối đa{" "}
                  {MAX_SPELL_CHECK_UNITS} đoạn của hệ thống. Hệ thống không tự
                  động cắt bỏ đoạn vượt giới hạn — vui lòng bỏ chọn bớt để thu
                  hẹp phạm vi (còn tối đa {MAX_SPELL_CHECK_UNITS} đoạn).
                </AlertDescription>
              </Alert>
            ) : null}

            {/* Checklist of units on current page (and any other selected units) */}
            {selectableUnits.length === 0 ? (
              <p className="text-muted-foreground py-2">
                Tài liệu này chưa có đoạn văn bản nào có chữ để kiểm tra.
              </p>
            ) : (
              <div className="max-h-44 overflow-y-auto rounded-md border bg-background divide-y">
                {(currentPageUnits.length > 0
                  ? currentPageUnits
                  : selectableUnits
                ).map((unit) => {
                  const checked = selectedUnitIds.has(unit.evidence_id);
                  const locator = formatUnitLocator(unit, doc.units);
                  return (
                    <label
                      key={unit.evidence_id}
                      htmlFor={`spell-unit-${unit.evidence_id}`}
                      className="flex items-start gap-2.5 p-2 hover:bg-muted/40 cursor-pointer text-xs select-none"
                    >
                      <Checkbox
                        id={`spell-unit-${unit.evidence_id}`}
                        checked={checked}
                        disabled={isSubmitting}
                        onCheckedChange={() =>
                          handleToggleUnit(unit.evidence_id)
                        }
                        className="mt-0.5"
                      />
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <span className="font-medium text-foreground block">
                          {locator}
                        </span>
                        <p className="text-muted-foreground line-clamp-2 break-words">
                          {unit.text}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          {/* 2. Model Selector from Workspace Catalog */}
          <div className="space-y-2">
            <Label
              htmlFor="spell-check-model-select"
              className="text-xs font-medium"
            >
              Mô hình kiểm tra (Chat)
            </Label>

            {catalogQuery.isError ? (
              <Alert variant="destructive" className="py-2">
                <AlertCircle className="size-4" />
                <AlertTitle className="text-xs font-semibold">
                  Không tải được danh mục mô hình của đơn vị
                </AlertTitle>
                <AlertDescription className="text-xs mt-1 space-y-2">
                  <p>
                    {catalogQuery.error instanceof Error
                      ? catalogQuery.error.message
                      : "Không thể kết nối tới dịch vụ ModelOps."}
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs bg-background"
                    onClick={() => void catalogQuery.refetch()}
                  >
                    <RotateCcw className="size-3 mr-1" />
                    <span>Thử tải lại danh mục</span>
                  </Button>
                </AlertDescription>
              </Alert>
            ) : (
              <>
                <Select
                  value={providerId}
                  onValueChange={onChangeProviderId}
                  disabled={isSubmitting}
                >
                  <SelectTrigger
                    id="spell-check-model-select"
                    aria-label="Mô hình kiểm tra (Chat)"
                    className="h-9 text-xs"
                  >
                    <SelectValue placeholder="Chọn mô hình Chat" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default" className="text-xs">
                      Theo mặc định workspace
                      {defaultChatProvider
                        ? ` (${defaultChatProvider.name} · ${defaultChatProvider.model_name})`
                        : ""}
                    </SelectItem>
                    {chatProviders.map((p) => (
                      <SelectItem key={p.id} value={p.id} className="text-xs">
                        {p.name}
                        {p.model_name && p.model_name !== p.name
                          ? ` · ${p.model_name}`
                          : ""}
                        {p.default_capabilities?.includes("chat")
                          ? " (Mặc định)"
                          : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {selectedProviderItem ? (
                  <ConsumerModelBudgetNotice
                    model={selectedProviderItem}
                    defaultModel={defaultChatProvider}
                    isDefaultSelection={providerId === "default"}
                    capability="chat"
                  />
                ) : null}

                {!catalogQuery.isPending && chatProviders.length === 0 ? (
                  <Alert className="border-warning/50 bg-warning/10 text-foreground py-2">
                    <AlertTriangle className="size-4 text-warning" />
                    <AlertDescription className="text-xs">
                      Danh mục hiện chưa có mô hình Chat nào được cấp trực tiếp
                      cho đơn vị này. Quản trị viên có thể cấp quyền mô hình (ví
                      dụ: Qwen, Luna...) trong mục{" "}
                      <strong>Quản trị ModelOps</strong>. Hệ thống không tự động
                      chuyển sang mô hình chưa được cấp phép.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Chỉ hiển thị các mô hình đã được cấp cho đơn vị. Nếu chưa
                    thấy mô hình mong muốn (như Luna), quản trị viên có thể bật
                    và cấp quyền qua <strong>ModelOps</strong>; hệ thống không
                    tự đổi mô hình mặc định hoặc tự chuyển sang mô hình khác.
                  </p>
                )}
              </>
            )}
          </div>

          {/* 3. In-flight Status & Elapsed Time */}
          {isSubmitting ? (
            <Alert className="border-primary/40 bg-primary/5 py-2.5">
              <Loader2 className="size-4 animate-spin text-primary" />
              <AlertTitle className="text-xs font-semibold flex items-center justify-between gap-2">
                <span>Đang gửi và phân tích chính tả...</span>
                <Badge
                  variant="outline"
                  className="font-mono text-[11px] gap-1"
                >
                  <Clock className="size-3" />
                  <span>Đã trôi qua: {elapsedSeconds}s</span>
                </Badge>
              </AlertTitle>
              <AlertDescription className="text-xs mt-1 text-muted-foreground">
                Vui lòng đợi phản hồi từ mô hình. Hệ thống đã khóa nút gửi để
                tránh gọi trùng và không tự động gửi lại nếu quá hạn.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert className="text-xs py-2 border-info/40 bg-info/5 text-foreground">
              <Info className="size-3.5 text-info" />
              <AlertDescription className="text-[11px] text-muted-foreground">
                AI chỉ đề xuất các vị trí nghi sai chính tả và không tự sửa văn
                bản của bạn. Bạn sẽ xem xét, đối chiếu ảnh và chọn áp dụng từng
                gợi ý vào bản nháp.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0 border-t pt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={onSubmit}
            disabled={
              isSubmitting ||
              selectedCount === 0 ||
              exceedsLimit ||
              catalogQuery.isError
            }
            className="gap-1.5"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                <span>Đang phân tích ({elapsedSeconds}s)...</span>
              </>
            ) : (
              <>
                <Sparkles className="size-3.5" />
                <span>Bắt đầu kiểm tra ({selectedCount} đoạn)</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

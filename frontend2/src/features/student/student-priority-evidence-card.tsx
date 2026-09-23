import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Info,
  Loader2,
  MapPin,
  Search,
  UploadCloud,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useEligibleAreasQuery,
  usePriorityObjectProvincesQuery,
} from "@/features/priority-objects/api";

const ACCEPTED_MIME = ["image/jpeg", "image/png", "image/webp"] as const;
const ACCEPT_ATTR = ACCEPTED_MIME.join(",");

type VerificationType =
  | "none"
  | "image_evidence"
  | "residence_area"
  | "image_and_residence_area";

export type PriorityEvidenceFile = {
  id: string;
  file: File;
  previewUrl: string;
};

export type StudentPriorityEvidenceCardProps = {
  priorityObjectId: string;
  priorityObjectCode: string;
  priorityObjectName: string;
  verificationType: VerificationType;
  evidenceInstructions?: string | null;
  maxEvidenceFiles: number;
  maxEvidenceFileSizeBytes: number;
  files: PriorityEvidenceFile[];
  residenceAreaId: string | null;
  residenceVillage?: string | null;
  onFilesChange: (next: PriorityEvidenceFile[]) => void;
  onResidenceAreaChange: (areaId: string | null) => void;
  onResidenceVillageChange?: (village: string | null) => void;
  disabled?: boolean;
};

function needsEvidence(type: VerificationType): boolean {
  return type === "image_evidence" || type === "image_and_residence_area";
}

function needsResidenceArea(type: VerificationType): boolean {
  return type === "residence_area" || type === "image_and_residence_area";
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function EvidenceFilesSection({
  files,
  maxFiles,
  maxSizeBytes,
  instructions,
  disabled,
  onFilesChange,
}: {
  files: PriorityEvidenceFile[];
  maxFiles: number;
  maxSizeBytes: number;
  instructions?: string | null;
  disabled?: boolean;
  onFilesChange: (next: PriorityEvidenceFile[]) => void;
}) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function handleFileSelection(event: React.ChangeEvent<HTMLInputElement>) {
    setErrorMessage(null);
    const selected = Array.from(event.target.files ?? []);
    if (selected.length === 0) return;

    if (files.length + selected.length > maxFiles) {
      setErrorMessage(
        `Bạn chỉ được tải lên tối đa ${maxFiles} ảnh minh chứng.`,
      );
      event.target.value = "";
      return;
    }

    const next: PriorityEvidenceFile[] = [...files];
    for (const file of selected) {
      if (
        !ACCEPTED_MIME.includes(file.type as (typeof ACCEPTED_MIME)[number])
      ) {
        setErrorMessage(
          `Định dạng "${file.name}" không được hỗ trợ. Vui lòng chọn ảnh JPG, PNG hoặc WebP.`,
        );
        event.target.value = "";
        return;
      }
      if (file.size > maxSizeBytes) {
        setErrorMessage(
          `Tệp "${file.name}" (${formatBytes(file.size)}) vượt quá dung lượng tối đa ${formatBytes(maxSizeBytes)}.`,
        );
        event.target.value = "";
        return;
      }
      next.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        previewUrl: URL.createObjectURL(file),
      });
    }

    onFilesChange(next);
    event.target.value = "";
  }

  function removeFile(id: string) {
    const target = files.find((item) => item.id === id);
    if (target) {
      URL.revokeObjectURL(target.previewUrl);
    }
    onFilesChange(files.filter((item) => item.id !== id));
  }

  return (
    <div className="space-y-3">
      {instructions ? (
        <Alert className="border-sky-200 bg-sky-50 text-sky-950 dark:border-sky-900/50 dark:bg-sky-950/30 dark:text-sky-200">
          <Info className="size-4 text-sky-600 dark:text-sky-400" />
          <div className="space-y-1">
            <AlertTitle className="text-xs font-semibold sm:text-sm">
              Hướng dẫn minh chứng
            </AlertTitle>
            <AlertDescription className="text-xs leading-relaxed">
              {instructions}
            </AlertDescription>
          </div>
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Label className="text-xs text-muted-foreground sm:text-sm">
          Đã chọn {files.length}/{maxFiles} ảnh · Tối đa{" "}
          {formatBytes(maxSizeBytes)}/ảnh
        </Label>
        {files.length < maxFiles ? (
          <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border bg-background px-3 py-1.5 text-xs font-medium shadow-xs transition hover:bg-muted focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2">
            <UploadCloud className="size-3.5" />
            <span>Thêm ảnh</span>
            <input
              type="file"
              accept={ACCEPT_ATTR}
              multiple
              className="sr-only"
              disabled={disabled}
              onChange={handleFileSelection}
            />
          </label>
        ) : null}
      </div>

      {files.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground sm:text-sm">
          <UploadCloud className="mb-2 size-8 text-muted-foreground/60" />
          <p>
            Chưa có ảnh minh chứng nào. Nhấn &ldquo;Thêm ảnh&rdquo; để tải lên
            (tối đa {maxFiles} ảnh).
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {files.map((item, index) => (
            <div
              key={item.id}
              className="group relative aspect-4/3 overflow-hidden rounded-md border bg-muted"
            >
              <img
                src={item.previewUrl}
                alt={`Minh chứng ${index + 1}`}
                className="size-full object-cover"
              />
              {!disabled ? (
                <button
                  type="button"
                  onClick={() => removeFile(item.id)}
                  aria-label="Xóa ảnh"
                  className="absolute top-1 right-1 rounded-full bg-black/60 p-1 text-white opacity-90 transition hover:bg-black hover:opacity-100"
                >
                  <X className="size-3" />
                </button>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Không thể tải ảnh</AlertTitle>
          <AlertDescription className="text-xs">
            {errorMessage}
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

function ResidenceAreaSection({
  priorityObjectId,
  priorityObjectName,
  value,
  villageValue,
  disabled,
  onChange,
  onVillageChange,
}: {
  priorityObjectId: string;
  priorityObjectName: string;
  value: string | null;
  villageValue?: string | null;
  disabled?: boolean;
  onChange: (id: string | null) => void;
  onVillageChange?: (village: string | null) => void;
}) {
  const [selectedProvince, setSelectedProvince] = useState<string>("all");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSearch, setPickerSearch] = useState("");

  const provincesQuery = usePriorityObjectProvincesQuery(priorityObjectId);
  const provinces = provincesQuery.data ?? [];

  const eligibleQuery = useEligibleAreasQuery(priorityObjectId, {
    provinceName: selectedProvince === "all" ? undefined : selectedProvince,
    search: pickerSearch.trim() || undefined,
    page: 1,
    pageSize: 500,
    isActive: true,
  });

  const eligibleAreas = eligibleQuery.data?.items ?? [];

  const selectedAreaQuery = useEligibleAreasQuery(priorityObjectId, {
    page: 1,
    pageSize: 500,
    isActive: true,
  });

  const selectedArea = useMemo(() => {
    if (!value) return null;
    return (
      eligibleAreas.find((area) => area.administrativeAreaId === value) ??
      selectedAreaQuery.data?.items.find(
        (area) => area.administrativeAreaId === value,
      ) ??
      null
    );
  }, [eligibleAreas, selectedAreaQuery.data, value]);

  useEffect(() => {
    if (selectedArea?.provinceName && selectedProvince === "all") {
    }
  }, [selectedArea, selectedProvince]);

  function selectArea(areaId: string | null) {
    onChange(areaId);
    setPickerOpen(false);
    setPickerSearch("");
    if (!areaId && onVillageChange) {
      onVillageChange(null);
    }
  }

  const isLoading = eligibleQuery.isLoading || provincesQuery.isLoading;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-muted/30 p-3.5 text-xs text-muted-foreground sm:text-sm">
        <p className="font-medium text-foreground">
          Đối tượng <strong>{priorityObjectName}</strong>
        </p>
        <p className="mt-1 text-xs">
          Vui lòng chọn Tỉnh/Thành phố và Xã/Phường nơi bạn đăng ký thường trú
          theo danh mục Quyết định của Nhà nước.
        </p>
        {provinces.length > 0 && (
          <p className="mt-1 text-[11px] text-muted-foreground/80">
            Hệ thống hỗ trợ tra cứu trên <strong>{provinces.length}</strong>{" "}
            Tỉnh/TP có địa bàn đặc biệt khó khăn.
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label
            htmlFor="province-filter"
            className="text-xs font-semibold text-foreground"
          >
            1. Tỉnh / Thành phố <span className="text-destructive">*</span>
          </Label>
          <Select
            value={selectedProvince}
            disabled={disabled || provincesQuery.isLoading}
            onValueChange={(val) => {
              setSelectedProvince(val);
              if (
                val !== "all" &&
                selectedArea &&
                selectedArea.provinceName !== val
              ) {
                selectArea(null);
              }
            }}
          >
            <SelectTrigger id="province-filter" className="w-full text-xs">
              <SelectValue placeholder="Chọn Tỉnh / Thành phố..." />
            </SelectTrigger>
            <SelectContent className="max-h-60">
              <SelectItem value="all">
                Tất cả tỉnh / thành ({provinces.length})
              </SelectItem>
              {provinces.map((prov) => (
                <SelectItem key={prov} value={prov}>
                  {prov}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label
            htmlFor="priority-residence"
            className="text-xs font-semibold text-foreground"
          >
            2. Xã / Phường <span className="text-destructive">*</span>
          </Label>
          <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
            <PopoverTrigger asChild>
              <Button
                id="priority-residence"
                type="button"
                variant="outline"
                role="combobox"
                aria-expanded={pickerOpen}
                className="w-full justify-between px-3 text-xs font-normal"
                disabled={disabled || isLoading}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <MapPin className="size-3.5 shrink-0 text-muted-foreground" />
                  {selectedArea ? (
                    <span className="truncate font-medium text-foreground">
                      {selectedArea.name}
                      {selectedArea.provinceName ? (
                        <span className="text-muted-foreground font-normal">
                          {" "}
                          · {selectedArea.provinceName}
                        </span>
                      ) : null}
                    </span>
                  ) : (
                    <span className="truncate text-muted-foreground">
                      {selectedProvince === "all"
                        ? "Tìm và chọn xã/phường..."
                        : `Chọn xã thuộc ${selectedProvince}...`}
                    </span>
                  )}
                </span>
                <Search className="size-3.5 shrink-0 text-muted-foreground" />
              </Button>
            </PopoverTrigger>
            <PopoverContent
              className="w-[min(460px,calc(100vw-2rem))] p-0"
              align="start"
            >
              <Command shouldFilter={false}>
                <CommandInput
                  value={pickerSearch}
                  onValueChange={setPickerSearch}
                  placeholder={
                    selectedProvince === "all"
                      ? "Gõ tên xã/phường để tìm..."
                      : `Tìm xã thuộc ${selectedProvince}...`
                  }
                  className="text-xs"
                />
                <CommandList className="max-h-72 text-xs">
                  {isLoading ? (
                    <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
                      <Loader2 className="size-4 animate-spin" /> Đang tải danh
                      sách địa bàn...
                    </div>
                  ) : eligibleAreas.length === 0 ? (
                    <CommandEmpty className="p-4 text-center text-xs text-muted-foreground">
                      Không tìm thấy xã/phường phù hợp trong danh mục khó khăn.
                    </CommandEmpty>
                  ) : (
                    eligibleAreas.map((area) => (
                      <CommandItem
                        key={area.administrativeAreaId}
                        value={area.administrativeAreaId}
                        onSelect={() => selectArea(area.administrativeAreaId)}
                        className="items-start px-3 py-2 text-xs"
                      >
                        <div className="flex size-4 shrink-0 items-center justify-center mt-0.5">
                          {area.administrativeAreaId === value ? (
                            <CheckCircle2 className="size-3.5 text-primary" />
                          ) : (
                            <div className="size-1.5 rounded-full bg-muted-foreground/30" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1 ml-1.5">
                          <p className="font-medium text-foreground">
                            {area.name}
                            {area.provinceName ? (
                              <span className="text-muted-foreground font-normal">
                                {" "}
                                · {area.provinceName}
                              </span>
                            ) : null}
                          </p>
                          {area.isWholeArea !== false ? (
                            <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                              ✓ Toàn bộ xã thuộc diện khó khăn
                            </p>
                          ) : (
                            <p className="text-[11px] text-amber-600 dark:text-amber-400 truncate">
                              ⚠ Chỉ áp dụng: {area.specificVillages}
                            </p>
                          )}
                        </div>
                      </CommandItem>
                    ))
                  )}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {selectedArea ? (
        <div className="space-y-3 rounded-lg border border-border/80 bg-muted/20 p-3.5 text-xs animate-in fade-in-50">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <Building2 className="size-4 text-primary shrink-0" />
              <div>
                <span className="font-semibold text-foreground text-sm">
                  {selectedArea.name}
                </span>
                {selectedArea.provinceName && (
                  <span className="text-muted-foreground ml-1.5">
                    ({selectedArea.provinceName})
                  </span>
                )}
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => selectArea(null)}
              disabled={disabled}
            >
              <X className="size-3.5 mr-1" /> Đổi địa bàn
            </Button>
          </div>

          {selectedArea.isWholeArea !== false ? (
            <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/30 p-2.5 rounded-md border border-emerald-200 dark:border-emerald-900/50">
              <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              <span>
                Toàn bộ xã/phường này thuộc diện đặc biệt khó khăn được hưởng
                chế độ ưu tiên.
              </span>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-start gap-2 text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-950/30 p-2.5 rounded-md border border-amber-200 dark:border-amber-900/50">
                <AlertCircle className="size-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold">
                    Lưu ý: Địa bàn này chỉ áp dụng cho các thôn/xóm/ấp sau:
                  </p>
                  <p className="text-foreground font-medium">
                    {selectedArea.specificVillages}
                  </p>
                </div>
              </div>

              <div className="space-y-1.5 pt-1">
                <Label
                  htmlFor="residence-village"
                  className="text-xs font-semibold text-foreground"
                >
                  Thôn / Xóm / Ấp / Khóm nơi bạn thường trú{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="residence-village"
                  value={villageValue ?? ""}
                  placeholder="Nhập tên thôn/xóm/ấp nơi bạn đăng ký thường trú theo CCCD..."
                  className="text-xs"
                  disabled={disabled}
                  onChange={(e) => onVillageChange?.(e.target.value)}
                />
                <p className="text-[11px] text-muted-foreground">
                  Vui lòng nhập chính xác tên thôn/xóm/ấp ghi trên CCCD để cán
                  bộ đối chiếu xét duyệt.
                </p>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {eligibleQuery.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Không tải được danh sách địa bàn</AlertTitle>
          <AlertDescription className="text-xs">
            Vui lòng tải lại trang hoặc liên hệ phòng Công tác sinh viên nếu lỗi
            tiếp tục xảy ra.
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

export function StudentPriorityEvidenceCard({
  priorityObjectId,
  priorityObjectCode,
  priorityObjectName,
  verificationType,
  evidenceInstructions,
  maxEvidenceFiles,
  maxEvidenceFileSizeBytes,
  files,
  residenceAreaId,
  residenceVillage,
  onFilesChange,
  onResidenceAreaChange,
  onResidenceVillageChange,
  disabled,
}: StudentPriorityEvidenceCardProps) {
  const showEvidence = needsEvidence(verificationType);
  const showResidence = needsResidenceArea(verificationType);

  if (!showEvidence && !showResidence) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="p-4 sm:p-6 sm:pb-3">
        <div className="space-y-0.5 sm:space-y-1">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold sm:text-base">
            <Badge
              variant="warning"
              className="px-2 py-0.5 font-mono text-[11px]"
            >
              {priorityObjectCode}
            </Badge>
            Minh chứng cho đối tượng ưu tiên
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            Cung cấp đầy đủ minh chứng theo yêu cầu của đối tượng{" "}
            <strong>{priorityObjectName}</strong>.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 p-4 pt-0 sm:p-6 sm:pt-0">
        {showEvidence ? (
          <EvidenceFilesSection
            files={files}
            maxFiles={maxEvidenceFiles}
            maxSizeBytes={maxEvidenceFileSizeBytes}
            instructions={evidenceInstructions}
            disabled={disabled}
            onFilesChange={onFilesChange}
          />
        ) : null}
        {showResidence ? (
          <ResidenceAreaSection
            priorityObjectId={priorityObjectId}
            priorityObjectName={priorityObjectName}
            value={residenceAreaId}
            villageValue={residenceVillage}
            disabled={disabled}
            onChange={onResidenceAreaChange}
            onVillageChange={onResidenceVillageChange}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

import {
  AlertCircle,
  CheckCircle2,
  FileJson,
  Layers,
  RefreshCw,
  UploadCloud,
} from "lucide-react";
import type React from "react";
import { useRef, useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { apiClient } from "../../services/api-client";
import type {
  ConflictStrategy,
  ProviderImportResponse,
} from "../../types/modelops";

export interface ImportProvidersDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ParsedProviderSummary {
  name: string;
  providerType: string;
  modelsCount: number;
  keysCount: number;
  accountId?: string;
}

export const ImportProvidersDialog: React.FC<ImportProvidersDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedData, setParsedData] = useState<unknown | null>(null);
  const [previewItems, setPreviewItems] = useState<ParsedProviderSummary[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [conflictStrategy, setConflictStrategy] =
    useState<ConflictStrategy>("overwrite");
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] =
    useState<ProviderImportResponse | null>(null);

  const resetState = () => {
    setSelectedFile(null);
    setParsedData(null);
    setPreviewItems([]);
    setParseError(null);
    setConflictStrategy("overwrite");
    setIsImporting(false);
    setImportResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const parseAndSetJson = (content: string, fileName: string) => {
    try {
      setParseError(null);
      setImportResult(null);
      const json = JSON.parse(content);
      setParsedData(json);

      // Extract preview items
      const items: ParsedProviderSummary[] = [];
      if (json && typeof json === "object") {
        const rawObj = json as Record<string, unknown>;
        if (
          rawObj.export_type === "single_provider" &&
          typeof rawObj.provider === "object"
        ) {
          const p = rawObj.provider as Record<string, unknown>;
          items.push({
            name: String(p.name || "Provider Không Tên"),
            providerType: String(p.provider_type || p.type || "custom"),
            modelsCount: Array.isArray(p.models)
              ? p.models.length
              : p.model_name
                ? 1
                : 0,
            keysCount: Array.isArray(p.api_keys) ? p.api_keys.length : 0,
            accountId:
              typeof p.account_id === "string" ? p.account_id : undefined,
          });
        } else if (
          rawObj.export_type === "all_providers" &&
          Array.isArray(rawObj.providers)
        ) {
          for (const item of rawObj.providers) {
            if (item && typeof item === "object") {
              const p = item as Record<string, unknown>;
              items.push({
                name: String(p.name || "Provider Không Tên"),
                providerType: String(p.provider_type || p.type || "custom"),
                modelsCount: Array.isArray(p.models)
                  ? p.models.length
                  : p.model_name
                    ? 1
                    : 0,
                keysCount: Array.isArray(p.api_keys) ? p.api_keys.length : 0,
                accountId:
                  typeof p.account_id === "string" ? p.account_id : undefined,
              });
            }
          }
        } else if (Array.isArray(json)) {
          for (const item of json) {
            if (item && typeof item === "object") {
              const p = item as Record<string, unknown>;
              items.push({
                name: String(p.name || "Provider Không Tên"),
                providerType: String(p.provider_type || p.type || "custom"),
                modelsCount: Array.isArray(p.models)
                  ? p.models.length
                  : p.model_name
                    ? 1
                    : 0,
                keysCount: Array.isArray(p.api_keys) ? p.api_keys.length : 0,
                accountId:
                  typeof p.account_id === "string" ? p.account_id : undefined,
              });
            }
          }
        } else if (
          typeof rawObj.name === "string" &&
          (rawObj.provider_type || rawObj.type)
        ) {
          items.push({
            name: String(rawObj.name),
            providerType: String(
              rawObj.provider_type || rawObj.type || "custom",
            ),
            modelsCount: Array.isArray(rawObj.models)
              ? rawObj.models.length
              : rawObj.model_name
                ? 1
                : 0,
            keysCount: Array.isArray(rawObj.api_keys)
              ? rawObj.api_keys.length
              : 0,
            accountId:
              typeof rawObj.account_id === "string"
                ? rawObj.account_id
                : undefined,
          });
        }
      }

      if (items.length === 0) {
        setParseError(
          `Tệp '${fileName}' không chứa cấu trúc Provider hoặc danh sách Providers hợp lệ.`,
        );
      } else {
        setPreviewItems(items);
      }
    } catch {
      setParseError(
        `Định dạng tệp '${fileName}' không phải là cú pháp JSON hợp lệ.`,
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        parseAndSetJson(content, file.name);
      }
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        parseAndSetJson(content, file.name);
      }
    };
    reader.readAsText(file);
  };

  const handleExecuteImport = async () => {
    if (!parsedData) return;
    setIsImporting(true);
    setParseError(null);
    try {
      const res = await apiClient.importProviders(parsedData, conflictStrategy);
      setImportResult(res);
      onSuccess();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Đã xảy ra lỗi khi nạp cấu hình.";
      setParseError(msg);
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-base font-bold flex items-center gap-2">
            <FileJson className="h-5 w-5 text-primary" />
            Nhập Cấu Hình Nhà Cung Cấp (Import JSON)
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Tải lên tệp sao lưu JSON chứa cấu hình của 1 Provider hoặc toàn bộ
            các Provider trong hệ thống.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Dropzone Area */}
          <button
            type="button"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`w-full border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              selectedFile
                ? "border-primary/50 bg-primary/5"
                : "border-border hover:border-primary/40 hover:bg-muted/30"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center gap-2">
              <div className="p-3 rounded-full bg-primary/10 text-primary">
                <UploadCloud className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {selectedFile
                    ? selectedFile.name
                    : "Kéo thả tệp JSON vào đây hoặc click để chọn"}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Hỗ trợ tệp cấu hình đơn lẻ hoặc tệp sao lưu toàn bộ (tối đa
                  10MB)
                </p>
              </div>
            </div>
          </button>

          {/* Parse Error Alert */}
          {parseError && (
            <div className="p-3 rounded-md bg-destructive/10 text-destructive border border-destructive/30 text-xs flex items-start gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{parseError}</span>
            </div>
          )}

          {/* Import Result Alert */}
          {importResult && (
            <div
              className={`p-3.5 rounded-md text-xs border flex items-start gap-2.5 ${
                importResult.success
                  ? "bg-success/10 text-success border-success/30"
                  : "bg-destructive/10 text-destructive border-destructive/30"
              }`}
            >
              <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold">{importResult.message}</p>
                <div className="flex flex-wrap gap-2 text-[11px] font-mono">
                  <span>Mới: {importResult.imported}</span>
                  <span>•</span>
                  <span>Cập nhật: {importResult.updated}</span>
                  <span>•</span>
                  <span>Bỏ qua: {importResult.skipped}</span>
                </div>
              </div>
            </div>
          )}

          {/* Preview Section */}
          {previewItems.length > 0 && (
            <div className="space-y-3 pt-1">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-primary" />
                  Danh Sách Xem Trước ({previewItems.length} Nhà Cung Cấp)
                </h4>
                <Badge variant="outline" className="text-[11px] font-mono">
                  {previewItems.length === 1
                    ? "1 Provider"
                    : "Tất Cả Providers"}
                </Badge>
              </div>

              <div className="border border-border rounded-md overflow-hidden max-h-48 overflow-y-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-muted/50 border-b border-border text-muted-foreground text-[11px] font-semibold uppercase">
                    <tr>
                      <th className="py-2 px-3">Tên Provider</th>
                      <th className="py-2 px-3">Loại</th>
                      <th className="py-2 px-3 text-center">Models</th>
                      <th className="py-2 px-3 text-center">API Keys</th>
                      <th className="py-2 px-3">Account ID</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {previewItems.map((item) => (
                      <tr
                        key={`${item.providerType}-${item.name}`}
                        className="hover:bg-muted/20"
                      >
                        <td className="py-2 px-3 font-medium text-foreground">
                          {item.name}
                        </td>
                        <td className="py-2 px-3 font-mono text-[11px] text-muted-foreground uppercase">
                          {item.providerType}
                        </td>
                        <td className="py-2 px-3 text-center font-mono">
                          {item.modelsCount}
                        </td>
                        <td className="py-2 px-3 text-center font-mono">
                          {item.keysCount}
                        </td>
                        <td className="py-2 px-3 font-mono text-[11px] text-muted-foreground truncate max-w-[140px]">
                          {item.accountId || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Conflict Strategy Selector */}
              <div className="space-y-1.5 pt-2 border-t border-border/70">
                <span className="text-xs font-semibold text-foreground block">
                  Chiến Lược Xử Lý Khi Trùng Lặp:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <label
                    htmlFor="strategy-overwrite"
                    className={`flex items-start gap-2 p-2.5 rounded-md border cursor-pointer text-xs transition-colors ${
                      conflictStrategy === "overwrite"
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-border text-muted-foreground hover:bg-muted/30"
                    }`}
                  >
                    <input
                      id="strategy-overwrite"
                      type="radio"
                      name="conflict-strategy"
                      value="overwrite"
                      checked={conflictStrategy === "overwrite"}
                      onChange={() => setConflictStrategy("overwrite")}
                      className="mt-0.5"
                    />
                    <div>
                      <strong className="block font-medium text-foreground">
                        Ghi Đè
                      </strong>
                      <span className="text-[11px] text-muted-foreground leading-tight block">
                        Cập nhật thông số và gộp khóa API mới
                      </span>
                    </div>
                  </label>

                  <label
                    htmlFor="strategy-skip"
                    className={`flex items-start gap-2 p-2.5 rounded-md border cursor-pointer text-xs transition-colors ${
                      conflictStrategy === "skip"
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-border text-muted-foreground hover:bg-muted/30"
                    }`}
                  >
                    <input
                      id="strategy-skip"
                      type="radio"
                      name="conflict-strategy"
                      value="skip"
                      checked={conflictStrategy === "skip"}
                      onChange={() => setConflictStrategy("skip")}
                      className="mt-0.5"
                    />
                    <div>
                      <strong className="block font-medium text-foreground">
                        Bỏ Qua
                      </strong>
                      <span className="text-[11px] text-muted-foreground leading-tight block">
                        Giữ nguyên cấu hình đã có, chỉ thêm mới
                      </span>
                    </div>
                  </label>

                  <label
                    htmlFor="strategy-create-new"
                    className={`flex items-start gap-2 p-2.5 rounded-md border cursor-pointer text-xs transition-colors ${
                      conflictStrategy === "create_new"
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-border text-muted-foreground hover:bg-muted/30"
                    }`}
                  >
                    <input
                      id="strategy-create-new"
                      type="radio"
                      name="conflict-strategy"
                      value="create_new"
                      checked={conflictStrategy === "create_new"}
                      onChange={() => setConflictStrategy("create_new")}
                      className="mt-0.5"
                    />
                    <div>
                      <strong className="block font-medium text-foreground">
                        Tạo Mới
                      </strong>
                      <span className="text-[11px] text-muted-foreground leading-tight block">
                        Tạo thêm bản ghi mới kèm nhãn (Imported)
                      </span>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="outline"
              size="sm"
              onClick={handleClose}
              className="h-8 text-xs"
            >
              {importResult ? "Đóng" : "Hủy"}
            </Button>
            <Button
              size="sm"
              disabled={previewItems.length === 0 || isImporting}
              onClick={handleExecuteImport}
              className="h-8 text-xs gap-1.5"
            >
              {isImporting ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <UploadCloud className="h-3.5 w-3.5" />
              )}
              <span>{isImporting ? "Đang nạp..." : "Thực Hiện Nhập"}</span>
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

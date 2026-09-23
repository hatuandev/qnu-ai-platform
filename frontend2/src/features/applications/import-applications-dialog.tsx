import {
  AlertCircle,
  Download,
  FileSpreadsheet,
  Info,
  Loader2,
  UploadCloud,
} from "lucide-react";
import { useId, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  downloadApplicationsImportTemplate,
  useImportApplications,
} from "@/features/applications/api";
import type { ImportDormitoryApplicationsResult } from "@/features/applications/types";
import { useRegistrationPeriodsQuery } from "@/features/registration-periods/api";

export function ImportApplicationsDialog({
  open,
  onOpenChange,
  defaultPeriodId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultPeriodId?: string;
}) {
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>(
    defaultPeriodId && defaultPeriodId !== "all" ? defaultPeriodId : "",
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState(false);
  const [importResult, setImportResult] =
    useState<ImportDormitoryApplicationsResult | null>(null);

  const periodsQuery = useRegistrationPeriodsQuery({ page: 1, pageSize: 100 });
  const importMutation = useImportApplications();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
        toast.error("Vui lòng chọn file Excel có định dạng .xlsx hoặc .xls");
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      setIsDownloadingTemplate(true);
      await downloadApplicationsImportTemplate();
      toast.success("Đã tải file mẫu Excel thành công.");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Không thể tải file mẫu Excel.",
      );
    } finally {
      setIsDownloadingTemplate(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPeriodId) {
      toast.warning("Vui lòng chọn đợt đăng ký.");
      return;
    }
    if (!selectedFile) {
      toast.warning("Vui lòng chọn file Excel để nhập.");
      return;
    }

    try {
      const result = await importMutation.mutateAsync({
        registrationPeriodId: selectedPeriodId,
        file: selectedFile,
      });

      setImportResult(result);
      if (result.successCount > 0) {
        toast.success(
          `Đã nhập thành công ${result.successCount} hồ sơ đăng ký.`,
        );
      } else {
        toast.warning(
          "Không có hồ sơ nào được nhập thành công. Vui lòng kiểm tra danh sách lỗi.",
        );
      }
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Đã xảy ra lỗi trong quá trình nhập file Excel.");
      }
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setImportResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleClose = () => {
    handleReset();
    onOpenChange(false);
  };

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(v) => {
        if (!v) handleClose();
        else onOpenChange(true);
      }}
    >
      <ResponsiveDialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="size-5 text-primary" />
            Nhập danh sách hồ sơ từ Excel
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Nhập danh sách sinh viên đăng ký nội trú từ file Excel (.xlsx). Hồ
            sơ sẽ được tạo ở trạng thái <strong>Chờ duyệt</strong>.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        {!importResult ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Chọn đợt đăng ký */}
            <div className="space-y-1.5">
              <Label htmlFor="registration-period">
                Đợt đăng ký <span className="text-destructive">*</span>
              </Label>
              <Select
                value={selectedPeriodId}
                onValueChange={setSelectedPeriodId}
              >
                <SelectTrigger id="registration-period">
                  <SelectValue placeholder="-- Chọn đợt đăng ký --" />
                </SelectTrigger>
                <SelectContent>
                  {periodsQuery.data?.items.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.code} - {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Khung tải file mẫu & Lưu ý */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 rounded-lg bg-muted/50 border">
              <div className="text-xs text-muted-foreground space-y-0.5">
                <p className="font-medium text-foreground">
                  File Excel mẫu chuẩn của trường:
                </p>
                <p>
                  Gồm 10 cột: TT, Họ và tên, Ngày sinh, Mã SV, Giới tính,
                  Lớp/Khóa, Email, SĐT, Địa chỉ, Đối tượng.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0 gap-1.5"
                onClick={handleDownloadTemplate}
                disabled={isDownloadingTemplate}
              >
                {isDownloadingTemplate ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Download className="size-3.5" />
                )}
                Tải file mẫu Excel
              </Button>
            </div>

            {/* Khung Upload File */}
            <div className="space-y-1.5">
              <Label htmlFor={fileInputId}>
                Chọn file Excel dữ liệu{" "}
                <span className="text-destructive">*</span>
              </Label>
              <div
                className="border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center gap-2 text-center hover:bg-muted/40 cursor-pointer transition-colors"
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <input
                  id={fileInputId}
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx, .xls"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <UploadCloud className="size-10 text-muted-foreground/80" />
                {selectedFile ? (
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-primary">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(selectedFile.size / 1024).toFixed(1)} KB — Nhấp để chọn
                      lại file khác
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      Nhấp để chọn file hoặc kéo thả file vào đây
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Hỗ trợ định dạng .xlsx, .xls
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Alert thông tin cơ chế tự động */}
            <Alert
              variant="info"
              className="bg-blue-500/10 border-blue-500/20 text-blue-900 dark:text-blue-200 text-xs"
            >
              <Info className="size-4 text-blue-600 dark:text-blue-400" />
              <AlertTitle className="font-semibold mb-1">
                Cơ chế tự động đối chiếu & phân loại:
              </AlertTitle>
              <AlertDescription className="space-y-1 text-xs text-blue-800/90 dark:text-blue-300">
                <p>
                  • <strong>Đối chiếu UIS</strong>: Hệ thống thử lấy thông tin
                  gốc từ API UIS; nếu API không khả dụng sẽ tự động dùng dữ liệu
                  trong file Excel.
                </p>
                <p>
                  • <strong>Phân loại Email</strong>: Email đuôi{" "}
                  <code>@st.qnu.edu.vn</code> được gán là Email trường; email
                  khác được gán là Email cá nhân.
                </p>
              </AlertDescription>
            </Alert>

            <ResponsiveDialogFooter className="pt-2">
              <Button type="button" variant="ghost" onClick={handleClose}>
                Hủy
              </Button>
              <Button
                type="submit"
                disabled={
                  !selectedPeriodId || !selectedFile || importMutation.isPending
                }
              >
                {importMutation.isPending ? (
                  <>
                    <Loader2 className="size-4 mr-2 animate-spin" />
                    Đang xử lý import...
                  </>
                ) : (
                  <>
                    <FileSpreadsheet className="size-4 mr-2" />
                    Bắt đầu Import
                  </>
                )}
              </Button>
            </ResponsiveDialogFooter>
          </form>
        ) : (
          /* Kết quả Import */
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-lg border p-3 bg-muted/30 text-center">
                <p className="text-xs text-muted-foreground">Tổng số dòng</p>
                <p className="text-xl font-bold text-foreground">
                  {importResult.totalRows}
                </p>
              </div>
              <div className="rounded-lg border border-emerald-500/30 p-3 bg-emerald-500/10 text-center">
                <p className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                  Thành công
                </p>
                <p className="text-xl font-bold text-emerald-700 dark:text-emerald-400">
                  {importResult.successCount}
                </p>
              </div>
              <div className="rounded-lg border border-blue-500/30 p-3 bg-blue-500/10 text-center">
                <p className="text-xs text-blue-700 dark:text-blue-400 font-medium">
                  SV mới tạo
                </p>
                <p className="text-xl font-bold text-blue-700 dark:text-blue-400">
                  {importResult.newStudentsCount}
                </p>
              </div>
              <div className="rounded-lg border border-destructive/30 p-3 bg-destructive/10 text-center">
                <p className="text-xs text-destructive font-medium">
                  Bị lỗi / Trùng
                </p>
                <p className="text-xl font-bold text-destructive">
                  {importResult.failedCount}
                </p>
              </div>
            </div>

            {importResult.errors.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-semibold text-destructive flex items-center gap-1.5">
                    <AlertCircle className="size-4" />
                    Chi tiết các dòng không thể nhập (
                    {importResult.errors.length}):
                  </Label>
                </div>
                <div className="max-h-56 overflow-y-auto border rounded-md">
                  <Table>
                    <TableHeader className="bg-muted/60 sticky top-0">
                      <TableRow>
                        <TableHead className="w-14 text-center">Dòng</TableHead>
                        <TableHead className="w-28">Mã SV</TableHead>
                        <TableHead className="w-40">Họ và tên</TableHead>
                        <TableHead>Lý do</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {importResult.errors.map((err, idx) => (
                        <TableRow key={idx} className="text-xs">
                          <TableCell className="text-center font-medium">
                            {err.rowNumber}
                          </TableCell>
                          <TableCell className="font-mono">
                            {err.studentCode || "—"}
                          </TableCell>
                          <TableCell>{err.studentName || "—"}</TableCell>
                          <TableCell className="text-destructive">
                            {err.errorMessage}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            <ResponsiveDialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={handleReset}>
                Nhập file khác
              </Button>
              <Button type="button" onClick={handleClose}>
                Hoàn tất & Đóng
              </Button>
            </ResponsiveDialogFooter>
          </div>
        )}
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

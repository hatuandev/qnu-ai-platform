import { FileSpreadsheet, RefreshCw, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface CollectionExcelImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
  isPending: boolean;
  onImport: (file: File) => void;
}

export function CollectionExcelImportDialog({
  open,
  onOpenChange,
  selectedFile,
  setSelectedFile,
  isPending,
  onImport,
}: CollectionExcelImportDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-bold">
            <FileSpreadsheet className="size-4 text-primary" />
            <span>Nạp Bảng Biểu Số Liệu (Excel / CSV)</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          <p className="text-muted-foreground leading-relaxed">
            Chọn tệp bảng tính <code>.xlsx</code>, <code>.xls</code> hoặc{" "}
            <code>.csv</code> chứa các cột số liệu (Điểm chuẩn, Chỉ tiêu, Học
            phí, Tổ hợp xét tuyển). Hệ thống sẽ tự động bóc tách từng dòng thành
            các facts định lượng.
          </p>

          <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
            <input
              type="file"
              id="excel-facts-upload"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setSelectedFile(f);
              }}
            />
            <label
              htmlFor="excel-facts-upload"
              className="cursor-pointer block"
            >
              <FileSpreadsheet className="size-10 mx-auto mb-2 text-primary/70" />
              {selectedFile ? (
                <div>
                  <p className="font-semibold text-foreground text-sm">
                    {selectedFile.name}
                  </p>
                  <p className="text-muted-foreground text-xs mt-0.5">
                    {(selectedFile.size / 1024).toFixed(1)} KB — Nhấp để chọn
                    tệp khác
                  </p>
                </div>
              ) : (
                <div>
                  <p className="font-medium text-foreground">
                    Kéo thả hoặc nhấp để chọn tệp
                  </p>
                  <p className="text-muted-foreground text-xs mt-0.5">
                    Hỗ trợ .xlsx, .xls, .csv
                  </p>
                </div>
              )}
            </label>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              onOpenChange(false);
              setSelectedFile(null);
            }}
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            className="h-8 text-xs gap-1.5"
            disabled={!selectedFile || isPending}
            onClick={() => {
              if (selectedFile) {
                onImport(selectedFile);
              }
            }}
          >
            {isPending ? (
              <>
                <RefreshCw className="size-3.5 animate-spin" />
                <span>Đang trích xuất...</span>
              </>
            ) : (
              <>
                <Upload className="size-3.5" />
                <span>Bắt đầu nạp facts</span>
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

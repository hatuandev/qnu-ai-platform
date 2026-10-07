import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileStack, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { FileUpload } from "@/components/admin/file-upload";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type DocumentTypeItem,
  documentTypesApi,
} from "@/services/document-types-api";
import { documentsApi } from "@/services/documents-api";

interface DocumentUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function DocumentUploadModal({
  open,
  onOpenChange,
  onSuccess,
}: DocumentUploadModalProps) {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [documentNumber, setDocumentNumber] = useState("");
  const [issuingAuthority, setIssuingAuthority] = useState(
    "Trường Đại học Quy Nhơn",
  );
  const [issuedDate, setIssuedDate] = useState("");
  const [signer, setSigner] = useState("");
  const [documentTypeCode, setDocumentTypeCode] = useState("");
  const [autoParse, setAutoParse] = useState(true);

  // Fetch document types
  const { data: documentTypes = [] } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.listDocumentTypes(),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (files.length === 0) {
        throw new Error("Vui lòng chọn tệp văn bản cần tải lên.");
      }
      const file = files[0];
      return await documentsApi.uploadDocument(file, {
        title: title.trim() || undefined,
        document_number: documentNumber.trim() || undefined,
        issuing_authority: issuingAuthority.trim() || undefined,
        issued_date: issuedDate || undefined,
        signer: signer.trim() || undefined,
        document_type_code: documentTypeCode || undefined,
        auto_parse: autoParse,
      });
    },
    onSuccess: (data) => {
      toast.success(
        `Đã tải lên và lưu vào MinIO S3: ${data.file_name} (${data.id})`,
      );
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      queryClient.invalidateQueries({ queryKey: ["repository-stats"] });
      // Reset form
      setFiles([]);
      setTitle("");
      setDocumentNumber("");
      setIssuedDate("");
      setSigner("");
      setDocumentTypeCode("");
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Tải lên tài liệu thất bại.");
    },
  });

  const handleFilesChange = (newFiles: File[]) => {
    setFiles(newFiles);
    if (newFiles.length > 0 && !title) {
      // Tự động gợi ý tên tài liệu từ tên file
      const rawName = newFiles[0].name.replace(/\.[^/.]+$/, "");
      setTitle(rawName.replace(/[_-]/g, " "));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileStack className="size-5" />
            </div>
            <div>
              <DialogTitle>Tải Tài Liệu Vào Kho Tập Trung</DialogTitle>
              <DialogDescription>
                Lưu trữ tệp gốc vào MinIO S3, tính toán SHA-256 chống trùng lặp
                và bóc tách sẵn Markdown.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* File Drag & Drop */}
          <div className="space-y-1.5">
            <span className="text-xs font-semibold text-foreground">
              Tệp tài liệu văn bản <span className="text-destructive">*</span>
            </span>
            <FileUpload
              accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md"
              multiple={false}
              maxFiles={1}
              value={files}
              onFilesChange={handleFilesChange}
            />
          </div>

          {/* Tiêu đề & Loại văn bản */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-foreground">
                Tiêu đề / Trích yếu văn bản
              </span>
              <Input
                placeholder="VD: Quy chế đào tạo đại học chính quy 2026..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-foreground">
                Loại văn bản (Nghị định 30)
              </span>
              <Select
                value={documentTypeCode}
                onValueChange={setDocumentTypeCode}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Chọn loại văn bản..." />
                </SelectTrigger>
                <SelectContent className="max-h-56">
                  {documentTypes.map((dt: DocumentTypeItem) => (
                    <SelectItem key={dt.code} value={dt.code}>
                      {dt.name} ({dt.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Số hiệu & Cơ quan ban hành */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-foreground">
                Số hiệu văn bản
              </span>
              <Input
                placeholder="VD: 1234/QĐ-ĐHQN"
                value={documentNumber}
                onChange={(e) => setDocumentNumber(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-foreground">
                Cơ quan / Đơn vị ban hành
              </span>
              <Input
                placeholder="Trường Đại học Quy Nhơn"
                value={issuingAuthority}
                onChange={(e) => setIssuingAuthority(e.target.value)}
              />
            </div>
          </div>

          {/* Ngày ban hành & Người ký */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-foreground">
                Ngày ban hành
              </span>
              <Input
                type="date"
                value={issuedDate}
                onChange={(e) => setIssuedDate(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-foreground">
                Người ký văn bản
              </span>
              <Input
                placeholder="VD: Hiệu trưởng / Trưởng phòng ĐT"
                value={signer}
                onChange={(e) => setSigner(e.target.value)}
              />
            </div>
          </div>

          {/* Checkbox Auto Parse */}
          <div className="flex items-center space-x-2 rounded-md border border-border/60 bg-muted/30 p-3">
            <Checkbox
              id="auto-parse-checkbox"
              checked={autoParse}
              onCheckedChange={(checked) => setAutoParse(Boolean(checked))}
            />
            <label
              htmlFor="auto-parse-checkbox"
              className="text-xs text-foreground cursor-pointer select-none leading-relaxed"
            >
              <span className="font-semibold text-primary">
                Tự động bóc tách sang Markdown sạch ngay lập tức
              </span>
              <br />
              <span className="text-muted-foreground">
                Trích xuất tiêu đề, bảng biểu, chuẩn hóa NFC Tiếng Việt để sẵn
                sàng nạp vào mọi Kho Tri Thức.
              </span>
            </label>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={uploadMutation.isPending}
          >
            Hủy Bỏ
          </Button>
          <Button
            onClick={() => uploadMutation.mutate()}
            disabled={uploadMutation.isPending || files.length === 0}
            className="gap-1.5"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Đang Tải Lên & Xử Lý...
              </>
            ) : (
              <>
                <Upload className="size-4" />
                Lưu Vào Kho Tài Liệu
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

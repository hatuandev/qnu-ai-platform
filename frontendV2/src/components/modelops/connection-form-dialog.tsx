import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useCreateConnectionMutation,
  useUpdateConnectionMutation,
} from "@/api/modelops/queries";
import { createConnectionKey } from "@/api/modelops/requests";
import type { Connection, ConnectionFamily } from "@/api/modelops/types";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
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
import { Switch } from "@/components/ui/switch";
import { CONNECTION_FAMILIES } from "./constants";

export function ConnectionFormDialog({
  open,
  onOpenChange,
  connection,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection?: Connection | null;
}) {
  const isEditing = Boolean(connection);
  const createMutation = useCreateConnectionMutation();
  const updateMutation = useUpdateConnectionMutation();

  const [name, setName] = useState("");
  const [family, setFamily] = useState<ConnectionFamily>("openai");
  const [baseUrl, setBaseUrl] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(30);
  const [initialApiKey, setInitialApiKey] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (connection) {
      setName(connection.name);
      setFamily(connection.family);
      setBaseUrl(connection.base_url);
      setTimeoutSeconds(connection.timeout_seconds || 30);
      setIsActive(connection.is_active);
      setInitialApiKey("");
    } else {
      setName("");
      setFamily("openai");
      setBaseUrl(CONNECTION_FAMILIES.openai.defaultUrl);
      setTimeoutSeconds(30);
      setIsActive(true);
      setInitialApiKey("");
    }
  }, [connection, open]);

  const handleFamilyChange = (nextFamily: ConnectionFamily) => {
    setFamily(nextFamily);
    const preset = CONNECTION_FAMILIES[nextFamily];
    if (
      preset &&
      (!baseUrl ||
        Object.values(CONNECTION_FAMILIES).some(
          (f) => f.defaultUrl === baseUrl,
        ))
    ) {
      setBaseUrl(preset.defaultUrl);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Vui lòng nhập tên nhà cung cấp");
      return;
    }
    if (!baseUrl.trim()) {
      toast.error("Vui lòng nhập Endpoint URL");
      return;
    }

    setIsSubmitting(true);
    try {
      if (isEditing && connection) {
        await updateMutation.mutateAsync({
          connectionId: connection.id,
          input: {
            name: name.trim(),
            family,
            base_url: baseUrl.trim(),
            timeout_seconds: timeoutSeconds,
            is_active: isActive,
          },
        });
        toast.success(`Đã cập nhật nhà cung cấp "${name}"`);
      } else {
        const newConn = await createMutation.mutateAsync({
          name: name.trim(),
          family,
          base_url: baseUrl.trim(),
          timeout_seconds: timeoutSeconds,
          is_active: true,
        });

        // If user provided an initial API key, save it now
        if (initialApiKey.trim() && newConn?.id) {
          try {
            await createConnectionKey(newConn.id, {
              name: `Khóa mặc định (${name})`,
              secret: initialApiKey.trim(),
              priority: 5,
            });
            toast.success(
              `Đã thêm nhà cung cấp "${name}" kèm API Key hoạt động`,
            );
          } catch {
            toast.warning(
              `Đã tạo nhà cung cấp "${name}", nhưng không thể lưu API key ban đầu. Vui lòng thêm lại trong phần Quản lý Khóa.`,
            );
          }
        } else {
          toast.success(`Đã thêm nhà cung cấp "${name}" thành công`);
        }
      }
      onOpenChange(false);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Có lỗi xảy ra khi lưu nhà cung cấp";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              {isEditing
                ? "Chỉnh sửa nhà cung cấp AI"
                : "Thêm nhà cung cấp AI mới"}
            </DialogTitle>
            <DialogDescription>
              {isEditing
                ? "Cập nhật thông tin endpoint, thời gian chờ hoặc trạng thái kích hoạt."
                : "Khai báo máy chủ hoặc nhà cung cấp API hỗ trợ các mô hình AI (LLM, Embedding, OCR)."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Field>
              <FieldLabel htmlFor="conn-name">Tên nhà cung cấp *</FieldLabel>
              <Input
                id="conn-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="VD: OpenAI Cloud, vLLM Server QNU, Google Vertex AI..."
                required
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="conn-family">
                Chuẩn giao thức / Nhà phát triển *
              </FieldLabel>
              <Select
                value={family}
                onValueChange={(val) =>
                  handleFamilyChange(val as ConnectionFamily)
                }
              >
                <SelectTrigger id="conn-family">
                  <SelectValue placeholder="Chọn chuẩn giao thức" />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(CONNECTION_FAMILIES).map((fam) => (
                    <SelectItem key={fam.id} value={fam.id}>
                      <div className="flex flex-col">
                        <span className="font-medium">{fam.label}</span>
                        <span className="text-[11px] text-muted-foreground">
                          {fam.description}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field>
              <FieldLabel htmlFor="conn-url">
                Endpoint URL (Base URL) *
              </FieldLabel>
              <Input
                id="conn-url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="font-mono text-xs"
                required
              />
              <FieldDescription>
                Đường dẫn gốc của API (không bao gồm các hậu tố
                `/chat/completions` hay `/models`).
              </FieldDescription>
            </Field>

            {!isEditing && (
              <Field>
                <FieldLabel htmlFor="conn-apikey">
                  Khóa API bí mật (API Key)
                  <span className="text-xs text-muted-foreground font-normal ml-1">
                    (Tùy chọn nhập ngay)
                  </span>
                </FieldLabel>
                <Input
                  id="conn-apikey"
                  type="password"
                  value={initialApiKey}
                  onChange={(e) => setInitialApiKey(e.target.value)}
                  placeholder="sk-... (tối thiểu 8 ký tự)"
                  autoComplete="off"
                />
                <FieldDescription>
                  Khóa API sẽ được mã hóa an toàn ở server. Có thể bỏ qua và
                  thêm sau.
                </FieldDescription>
              </Field>
            )}

            <div className="grid grid-cols-2 gap-4">
              <Field>
                <FieldLabel htmlFor="conn-timeout">
                  Thời gian chờ (giây)
                </FieldLabel>
                <Input
                  id="conn-timeout"
                  type="number"
                  min={5}
                  max={300}
                  value={timeoutSeconds}
                  onChange={(e) =>
                    setTimeoutSeconds(Number(e.target.value) || 30)
                  }
                />
              </Field>

              {isEditing && (
                <Field className="flex flex-col justify-end">
                  <div className="flex items-center justify-between h-9 px-3 rounded-md border bg-muted/20">
                    <FieldLabel
                      htmlFor="conn-active"
                      className="text-xs cursor-pointer"
                    >
                      Trạng thái hoạt động
                    </FieldLabel>
                    <Switch
                      id="conn-active"
                      checked={isActive}
                      onCheckedChange={setIsActive}
                    />
                  </div>
                </Field>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={isSubmitting}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? "Đang lưu..."
                : isEditing
                  ? "Lưu thay đổi"
                  : "Tạo kết nối"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

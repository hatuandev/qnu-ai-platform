import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SettingsSaveBar({
  dirty,
  canUpdate,
  isSaving = false,
  onCancel,
  onSave,
}: {
  dirty: boolean;
  canUpdate: boolean;
  isSaving?: boolean;
  onCancel: () => void;
  onSave?: () => void;
}) {
  return (
    <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
      <Button
        variant="outline"
        disabled={!dirty || isSaving}
        onClick={onCancel}
      >
        Hủy thay đổi
      </Button>
      <Button disabled={!dirty || !canUpdate || isSaving} onClick={onSave}>
        <Save />
        {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
      </Button>
    </div>
  );
}

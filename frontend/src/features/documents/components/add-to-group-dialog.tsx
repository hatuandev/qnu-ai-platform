import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
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
import { Textarea } from "@/components/ui/textarea";
import { documentsApi } from "@/services/documents-api";

interface AddToGroupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  documentIds: string[];
  onSuccess?: () => void;
}

export function AddToGroupDialog({
  open,
  onOpenChange,
  documentIds,
  onSuccess,
}: AddToGroupDialogProps) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"select" | "create">("select");
  const [selectedGroupId, setSelectedGroupId] = useState<string>("");
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupDesc, setNewGroupDesc] = useState("");

  // Fetch groups list
  const { data: groupsData, isLoading } = useQuery({
    queryKey: ["document-groups"],
    queryFn: () => documentsApi.getGroups({ page_size: 100 }),
    enabled: open,
  });

  const groups = groupsData?.items ?? [];

  // Mutation to add docs to group
  const addMutation = useMutation({
    mutationFn: async () => {
      let targetGroupId = selectedGroupId;
      if (mode === "create") {
        if (!newGroupName.trim()) {
          throw new Error("Vui lòng nhập tên nhóm tài liệu mới.");
        }
        const created = await documentsApi.createGroup({
          name: newGroupName.trim(),
          description: newGroupDesc.trim() || undefined,
        });
        targetGroupId = created.id;
      }

      if (!targetGroupId) {
        throw new Error("Vui lòng chọn hoặc tạo nhóm tài liệu.");
      }

      return await documentsApi.addDocumentsToGroup(targetGroupId, {
        document_ids: documentIds,
      });
    },
    onSuccess: (res) => {
      toast.success(
        `Đã xử lý thêm tài liệu vào nhóm: ${res.added_count} mới, ${res.skipped_existing_count} đã tồn tại.`,
      );
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      onOpenChange(false);
      setMode("select");
      setSelectedGroupId("");
      setNewGroupName("");
      setNewGroupDesc("");
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Thêm tài liệu vào nhóm thất bại.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FolderPlus className="size-5" />
            </div>
            <div>
              <DialogTitle>Thêm Vào Nhóm Tài Liệu</DialogTitle>
              <DialogDescription>
                Đang chọn {documentIds.length} tài liệu để đưa vào nhóm quản lý.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Mode Switcher */}
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <Button
              type="button"
              variant={mode === "select" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("select")}
              className="text-xs h-8"
            >
              Chọn nhóm có sẵn
            </Button>
            <Button
              type="button"
              variant={mode === "create" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("create")}
              className="text-xs h-8 gap-1"
            >
              <Plus className="size-3.5" />
              Tạo nhóm mới
            </Button>
          </div>

          {mode === "select" ? (
            <div className="space-y-2">
              <label
                htmlFor="group-select"
                className="text-xs font-medium text-foreground"
              >
                Chọn nhóm mục tiêu
              </label>
              {isLoading ? (
                <div className="h-9 w-full rounded-md bg-muted/40 animate-pulse" />
              ) : groups.length === 0 ? (
                <div className="rounded-md border border-dashed border-border p-4 text-center">
                  <p className="text-xs text-muted-foreground mb-2">
                    Chưa có nhóm tài liệu nào.
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setMode("create")}
                    className="text-xs"
                  >
                    Tạo nhóm đầu tiên
                  </Button>
                </div>
              ) : (
                <Select
                  value={selectedGroupId}
                  onValueChange={setSelectedGroupId}
                >
                  <SelectTrigger id="group-select" className="w-full">
                    <SelectValue placeholder="-- Chọn một nhóm tài liệu --" />
                  </SelectTrigger>
                  <SelectContent>
                    {groups.map((g) => (
                      <SelectItem key={g.id} value={g.id}>
                        {g.name} ({g.total_documents} tài liệu)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label
                  htmlFor="group-name-input"
                  className="text-xs font-medium text-foreground"
                >
                  Tên nhóm tài liệu <span className="text-destructive">*</span>
                </label>
                <Input
                  id="group-name-input"
                  placeholder="Ví dụ: Tuyển sinh 2026, Quy chế đào tạo..."
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="group-desc-input"
                  className="text-xs font-medium text-foreground"
                >
                  Mô tả nhóm (Tùy chọn)
                </label>
                <Textarea
                  id="group-desc-input"
                  placeholder="Mô tả phạm vi hoặc mục đích của nhóm tài liệu..."
                  value={newGroupDesc}
                  onChange={(e) => setNewGroupDesc(e.target.value)}
                  rows={3}
                  className="text-sm resize-none"
                />
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={addMutation.isPending}
          >
            Hủy
          </Button>
          <Button
            type="button"
            onClick={() => addMutation.mutate()}
            disabled={
              addMutation.isPending ||
              (mode === "select" && !selectedGroupId) ||
              (mode === "create" && !newGroupName.trim())
            }
            className="gap-1.5"
          >
            <FolderPlus className="size-4" />
            {mode === "create" ? "Tạo & Thêm Vào Nhóm" : "Thêm Vào Nhóm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

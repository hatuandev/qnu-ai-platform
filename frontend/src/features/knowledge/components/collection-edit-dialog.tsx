import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Field } from "@/components/admin/field";
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
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type { KnowledgeCollection } from "@/types/knowledge";

export function CollectionEditDialog({
  collection,
  onClose,
}: {
  collection: KnowledgeCollection;
  onClose: () => void;
}) {
  const client = useQueryClient();
  const [name, setName] = useState(collection.name);
  const [description, setDescription] = useState(collection.description || "");
  const save = useMutation({
    mutationFn: () => {
      if (!name.trim()) throw new Error("Hãy nhập tên kho tri thức.");
      return knowledgeApi.updateCollection(collection.id, {
        name: name.trim(),
        description: description.trim(),
      });
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["collections"] });
      client.invalidateQueries({
        queryKey: ["knowledge-collection", collection.id],
      });
      toast.success("Đã cập nhật kho tri thức.");
      onClose();
    },
    onError: (error) =>
      toast.error(extractErrorMessage(error, "Không lưu được thông tin kho.")),
  });
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !save.isPending) onClose();
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Sửa kho tri thức</DialogTitle>
          <DialogDescription>
            Chỉ cập nhật thông tin kho, không thay đổi model hoặc chỉ mục đang
            phục vụ.
          </DialogDescription>
        </DialogHeader>
        <Field label="Tên kho" htmlFor="edit-knowledge-name" required>
          <Input
            id="edit-knowledge-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={save.isPending}
          />
        </Field>
        <Field
          label="Mã định danh"
          htmlFor="edit-knowledge-code"
          hint="Mã định danh không thay đổi."
        >
          <Input id="edit-knowledge-code" value={collection.code} readOnly />
        </Field>
        <Field label="Mô tả" htmlFor="edit-knowledge-description">
          <Textarea
            id="edit-knowledge-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            disabled={save.isPending}
          />
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={save.isPending}>
            Hủy
          </Button>
          <Button
            onClick={() => save.mutate()}
            disabled={!name.trim() || save.isPending}
          >
            {save.isPending ? "Đang lưu…" : "Lưu"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

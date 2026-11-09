import { createFileRoute, Link } from "@tanstack/react-router";
import { Bot, Check, MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";
import { Field, FieldLabel } from "@/components/admin/field";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/assistants")({
  component: AssistantsPage,
});

type Assistant = {
  id: string;
  name: string;
  description: string;
  model: string;
  collection: string;
  systemPrompt: string;
  conversations: number;
};

const initialAssistants: Assistant[] = [
  {
    id: "bot_admissions",
    name: "Trợ lý Tuyển sinh 2026",
    description:
      "Tư vấn thông tin xét tuyển, phương thức tuyển sinh và học phí năm học 2026-2027.",
    model: "Qwen 2.5 Coder 32B Instruct",
    collection: "Dữ liệu tuyển sinh QNU 2026",
    systemPrompt:
      "Bạn là trợ lý tư vấn tuyển sinh đại học chính quy của Trường Đại học Quy Nhơn. Hãy trả lời ngắn gọn, chính xác dựa trên Đề án tuyển sinh 2026 và dẫn chứng mã số văn bản.",
    conversations: 42,
  },
  {
    id: "bot_training",
    name: "Trợ lý Quy chế Đào tạo",
    description:
      "Giải đáp các thắc mắc về tín chỉ, học phần tiên quyết, bảo lưu kết quả và xét tốt nghiệp.",
    model: "GPT-4o",
    collection: "Quy chế & Đào tạo đại học",
    systemPrompt:
      "Bạn là trợ lý học vụ giải đáp quy chế đào tạo tín chỉ của Trường Đại học Quy Nhơn. Luôn căn cứ theo Quyết định số 1842 và các quy định sửa đổi bổ sung mới nhất.",
    conversations: 18,
  },
];

function AssistantsPage() {
  const [assistants, setAssistants] = useState<Assistant[]>(initialAssistants);
  const [editingBot, setEditingBot] = useState<Assistant | null>(null);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Tương tác & Triển khai"
        title="Danh sách Trợ lý AI"
        description="Quản lý các trợ lý thông minh theo từng lĩnh vực, liên kết với kho tri thức tương ứng."
        actions={
          <Button
            size="sm"
            onClick={() =>
              setEditingBot({
                id: `bot_${Date.now()}`,
                name: "Trợ lý mới",
                description: "Mô tả mục đích hoạt động của trợ lý...",
                model: "Qwen 2.5 Coder 32B Instruct",
                collection: "Dữ liệu tuyển sinh QNU 2026",
                systemPrompt:
                  "Bạn là trợ lý AI chuyên nghiệp của Trường Đại học Quy Nhơn.",
                conversations: 0,
              })
            }
            className="h-8 gap-1.5 text-xs"
          >
            <Plus className="size-3.5" />
            <span>Tạo trợ lý mới</span>
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {assistants.map((bot) => (
          <Card
            key={bot.id}
            className="relative flex flex-col hover:border-primary/50 transition-colors shadow-2xs"
          >
            <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
              <div className="flex items-center gap-2.5">
                <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Bot className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    {bot.name}
                  </CardTitle>
                  <p className="text-[11px] text-muted-foreground">
                    {bot.model}
                  </p>
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="size-7 p-0">
                    <MoreHorizontal className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40 text-xs">
                  <DropdownMenuItem onClick={() => setEditingBot(bot)}>
                    Chỉnh sửa cấu hình
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/chat">Thử nghiệm hỏi đáp</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      setAssistants((prev) =>
                        prev.filter((b) => b.id !== bot.id),
                      )
                    }
                    className="text-destructive"
                  >
                    Lưu trữ trợ lý
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardHeader>
            <CardContent className="flex-1 space-y-3 pb-3">
              <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                {bot.description}
              </p>
              <div className="flex items-center gap-1.5">
                <Badge
                  variant="secondary"
                  className="text-[10px] h-4 px-1.5 font-normal"
                >
                  {bot.collection}
                </Badge>
              </div>
            </CardContent>
            <CardFooter className="pt-2 border-t border-border/40 text-[11px] text-muted-foreground flex justify-between items-center">
              <span>{bot.conversations} phiên trao đổi</span>
              <button
                type="button"
                onClick={() => setEditingBot(bot)}
                className="text-primary font-medium hover:underline flex items-center gap-1"
              >
                <span>Cấu hình ▸</span>
              </button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {/* Assistant Config Dialog */}
      {editingBot && (
        <Dialog open={!!editingBot} onOpenChange={() => setEditingBot(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-semibold">
                Cấu hình Trợ lý
              </DialogTitle>
              <DialogDescription className="text-xs">
                Thiết lập thông tin mô hình ngôn ngữ và prompt hướng dẫn sinh
                câu trả lời.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <Field className="gap-2">
                <FieldLabel
                  htmlFor="bot-name"
                  className="text-xs font-semibold text-foreground"
                >
                  Tên trợ lý
                </FieldLabel>
                <Input
                  id="bot-name"
                  value={editingBot.name}
                  onChange={(e) =>
                    setEditingBot({ ...editingBot, name: e.target.value })
                  }
                  className="h-9 text-xs"
                />
              </Field>

              <Field className="gap-2">
                <FieldLabel
                  htmlFor="bot-model"
                  className="text-xs font-semibold text-foreground"
                >
                  Mô hình AI
                </FieldLabel>
                <Input
                  id="bot-model"
                  value={editingBot.model}
                  onChange={(e) =>
                    setEditingBot({ ...editingBot, model: e.target.value })
                  }
                  className="h-9 text-xs font-mono"
                />
              </Field>

              <Field className="gap-2">
                <FieldLabel
                  htmlFor="bot-collection"
                  className="text-xs font-semibold text-foreground"
                >
                  Kho tri thức liên kết
                </FieldLabel>
                <Input
                  id="bot-collection"
                  value={editingBot.collection}
                  onChange={(e) =>
                    setEditingBot({ ...editingBot, collection: e.target.value })
                  }
                  className="h-9 text-xs"
                />
              </Field>

              <Field className="gap-2">
                <FieldLabel
                  htmlFor="bot-system-prompt"
                  className="text-xs font-semibold text-foreground"
                >
                  Chỉ dẫn hệ thống (System Prompt)
                </FieldLabel>
                <Textarea
                  id="bot-system-prompt"
                  value={editingBot.systemPrompt}
                  onChange={(e) =>
                    setEditingBot({
                      ...editingBot,
                      systemPrompt: e.target.value,
                    })
                  }
                  rows={3}
                  className="text-xs resize-none"
                />
              </Field>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditingBot(null)}
                className="h-9 text-xs"
              >
                Đóng
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setAssistants((prev) => {
                    const exists = prev.some((b) => b.id === editingBot.id);
                    if (exists) {
                      return prev.map((b) =>
                        b.id === editingBot.id ? editingBot : b,
                      );
                    }
                    return [editingBot, ...prev];
                  });
                  setEditingBot(null);
                }}
                className="h-9 text-xs gap-1"
              >
                <Check className="size-3" />
                <span>Lưu cấu hình</span>
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

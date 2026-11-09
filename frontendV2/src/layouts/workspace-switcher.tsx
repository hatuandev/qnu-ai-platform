import {
  BookOpen,
  Building2,
  Check,
  ChevronsUpDown,
  Cpu,
  GraduationCap,
  Landmark,
  Plus,
  School,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Field, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type Workspace = {
  id: string;
  name: string;
  plan: string;
  icon: typeof GraduationCap;
  shortcut: string;
};

const initialWorkspaces: Workspace[] = [
  {
    id: "ws_qnu_main",
    name: "Trường Đại học Quy Nhơn",
    plan: "Đơn vị chính",
    icon: GraduationCap,
    shortcut: "⌘1",
  },
  {
    id: "ws_fit",
    name: "Khoa Công nghệ Thông tin",
    plan: "Khoa đào tạo",
    icon: Cpu,
    shortcut: "⌘2",
  },
  {
    id: "ws_academic",
    name: "Phòng Đào tạo",
    plan: "Phòng chức năng",
    icon: BookOpen,
    shortcut: "⌘3",
  },
  {
    id: "ws_admissions",
    name: "Hội đồng Tuyển sinh 2026",
    plan: "Ban chuyên trách",
    icon: Sparkles,
    shortcut: "⌘4",
  },
];

const availableIcons = [
  { label: "Mũ cử nhân / Giáo dục", icon: GraduationCap },
  { label: "Công nghệ thông tin", icon: Cpu },
  { label: "Sách / Đào tạo", icon: BookOpen },
  { label: "Đổi mới & Sáng tạo", icon: Sparkles },
  { label: "Tòa nhà & Cơ sở", icon: Building2 },
  { label: "Trường / Viện", icon: School },
  { label: "Ban Giám hiệu", icon: Landmark },
];

export function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const [workspaceList, setWorkspaceList] =
    useState<Workspace[]>(initialWorkspaces);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>(
    initialWorkspaces[0],
  );

  // Dialog State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [newWsPlan, setNewWsPlan] = useState("Khoa đào tạo");
  const [selectedIconIndex, setSelectedIconIndex] = useState(0);

  const handleCreateWorkspace = () => {
    if (!newWsName.trim()) {
      toast.error("Vui lòng nhập tên đơn vị làm việc!");
      return;
    }

    const chosenIcon = availableIcons[selectedIconIndex].icon;
    const newWs: Workspace = {
      id: `ws_${Date.now()}`,
      name: newWsName.trim(),
      plan: newWsPlan,
      icon: chosenIcon,
      shortcut: `⌘${workspaceList.length + 1}`,
    };

    setWorkspaceList((prev) => [...prev, newWs]);
    setActiveWorkspace(newWs);
    setIsCreateOpen(false);
    setNewWsName("");
    setNewWsPlan("Khoa đào tạo");
    setSelectedIconIndex(0);

    toast.success(`Đã thêm đơn vị "${newWs.name}" thành công!`);
  };

  const ActiveIcon = activeWorkspace.icon;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg p-1.5 text-left transition-colors hover:bg-muted/70 focus:outline-none focus:ring-1 focus:ring-ring data-[state=open]:bg-muted/80",
              collapsed && "justify-center p-1",
            )}
            aria-label="Chọn đơn vị làm việc"
          >
            {/* Workspace Icon */}
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-2xs">
              <ActiveIcon className="size-4" />
            </div>

            {/* Workspace Info (Hidden when sidebar is collapsed) */}
            {!collapsed && (
              <>
                <div className="flex flex-1 flex-col min-w-0">
                  <span className="truncate text-xs font-semibold text-foreground leading-tight">
                    {activeWorkspace.name}
                  </span>
                  <span className="truncate text-[11px] text-muted-foreground leading-tight mt-0.5">
                    {activeWorkspace.plan}
                  </span>
                </div>
                <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground ml-auto" />
              </>
            )}
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent
          align={collapsed ? "center" : "start"}
          side={collapsed ? "right" : "bottom"}
          sideOffset={6}
          className="w-64 p-1.5"
        >
          <DropdownMenuLabel className="text-[11px] font-medium text-muted-foreground px-2 py-1">
            Đơn vị làm việc
          </DropdownMenuLabel>

          {workspaceList.map((ws) => {
            const WsIcon = ws.icon;
            const isSelected = ws.id === activeWorkspace.id;

            return (
              <DropdownMenuItem
                key={ws.id}
                onClick={() => setActiveWorkspace(ws)}
                className={cn(
                  "flex items-center gap-2.5 p-2 text-xs rounded-md cursor-pointer",
                  isSelected && "bg-muted font-medium text-foreground",
                )}
              >
                <div
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-md border",
                    isSelected
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border/80 bg-background text-muted-foreground",
                  )}
                >
                  <WsIcon className="size-3.5" />
                </div>
                <span className="flex-1 truncate">{ws.name}</span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {ws.shortcut}
                </span>
              </DropdownMenuItem>
            );
          })}

          <DropdownMenuSeparator className="-mx-1.5 my-1" />

          {/* "+ Thêm đơn vị mới" Trigger */}
          <DropdownMenuItem
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2.5 p-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <div className="flex size-6 shrink-0 items-center justify-center rounded-md border border-dashed border-border/80 bg-background">
              <Plus className="size-3.5" />
            </div>
            <span>Thêm đơn vị mới</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Modal Thêm đơn vị làm việc mới */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Thêm đơn vị làm việc mới
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Tạo không gian làm việc độc lập cho Khoa, Phòng ban hoặc Trung tâm
              để phân quyền và quản lý kho tri thức riêng biệt.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Tên đơn vị */}
            <Field className="gap-2">
              <FieldLabel
                htmlFor="workspace-name-input"
                className="text-xs font-semibold text-foreground flex items-center gap-1"
              >
                <span>Tên đơn vị</span>
                <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id="workspace-name-input"
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                placeholder="VD: Khoa Toán - Thống kê, Phòng CTSV..."
                className="h-9 text-xs"
                onKeyDown={(e) => e.key === "Enter" && handleCreateWorkspace()}
              />
            </Field>

            {/* Phân loại đơn vị */}
            <Field className="gap-2">
              <FieldLabel
                htmlFor="workspace-plan-select"
                className="text-xs font-semibold text-foreground"
              >
                Phân loại đơn vị
              </FieldLabel>
              <Select value={newWsPlan} onValueChange={setNewWsPlan}>
                <SelectTrigger
                  id="workspace-plan-select"
                  className="h-9 text-xs"
                >
                  <SelectValue placeholder="Chọn loại đơn vị" />
                </SelectTrigger>
                <SelectContent className="text-xs">
                  <SelectItem value="Khoa đào tạo">Khoa đào tạo</SelectItem>
                  <SelectItem value="Phòng chức năng">
                    Phòng chức năng
                  </SelectItem>
                  <SelectItem value="Ban chuyên trách">
                    Ban chuyên trách
                  </SelectItem>
                  <SelectItem value="Viện / Trung tâm">
                    Viện / Trung tâm
                  </SelectItem>
                  <SelectItem value="Tổ bộ môn">Tổ bộ môn</SelectItem>
                </SelectContent>
              </Select>
            </Field>

            {/* Biểu tượng nhận diện */}
            <Field className="gap-2">
              <FieldLabel className="text-xs font-semibold text-foreground">
                Biểu tượng nhận diện
              </FieldLabel>

              <div className="flex items-center gap-2">
                {availableIcons.map((item, idx) => {
                  const Icon = item.icon;
                  const isChosen = idx === selectedIconIndex;

                  return (
                    <button
                      key={item.label}
                      type="button"
                      onClick={() => setSelectedIconIndex(idx)}
                      title={item.label}
                      className={cn(
                        "flex size-9 items-center justify-center rounded-lg border transition-colors cursor-pointer",
                        isChosen
                          ? "border-primary bg-primary text-primary-foreground shadow-2xs"
                          : "border-border/80 bg-background text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                      aria-label={item.label}
                    >
                      <Icon className="size-4" />
                    </button>
                  );
                })}
              </div>
            </Field>
          </div>

          <DialogFooter className="gap-3 sm:gap-3 pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsCreateOpen(false)}
              className="h-9 px-4 text-xs font-medium"
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!newWsName.trim()}
              onClick={handleCreateWorkspace}
              className="h-9 px-4 text-xs font-medium gap-1.5"
            >
              <Check className="size-3.5" />
              <span>Tạo đơn vị</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

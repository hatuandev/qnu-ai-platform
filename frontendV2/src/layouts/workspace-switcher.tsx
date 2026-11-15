import {
  BookOpen,
  Building2,
  Check,
  ChevronsUpDown,
  Cpu,
  GraduationCap,
  Info,
  Loader2,
  Plus,
  RefreshCw,
  School,
  Settings,
  Shield,
  Sparkles,
  UserPlus,
  Users,
} from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  useAddMemberMutation,
  useCreateWorkspaceMutation,
  useRevokeMemberMutation,
  useWorkspaceMembersQuery,
  useWorkspaceQuotaQuery,
  useWorkspacesQuery,
  type Workspace,
} from "@/api/workspaces";
import { Field, FieldLabel } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
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
import { slugify } from "@/lib/slug";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

function getWorkspaceIcon(code: string, name: string) {
  const text = `${code} ${name}`.toLowerCase();
  if (
    text.includes("it") ||
    text.includes("cntt") ||
    text.includes("cong nghe")
  ) {
    return Cpu;
  }
  if (
    text.includes("dao tao") ||
    text.includes("academic") ||
    text.includes("sach")
  ) {
    return BookOpen;
  }
  if (text.includes("tuyen sinh") || text.includes("admissions")) {
    return Sparkles;
  }
  if (
    text.includes("vien") ||
    text.includes("trung tam") ||
    text.includes("phong")
  ) {
    return Building2;
  }
  if (text.includes("truong") || text.includes("dai hoc")) {
    return School;
  }
  return GraduationCap;
}

const fallbackWorkspaces: Workspace[] = [
  {
    id: "ws_qnu_main",
    code: "qnu-main",
    name: "Trường Đại học Quy Nhơn",
    description: "Đơn vị chính",
    status: "active",
    member_count: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const {
    activeWorkspaceId,
    activeWorkspace: storeActiveWorkspace,
    setActiveWorkspace,
  } = useUiStore();
  const nameInputId = useId();
  const codeInputId = useId();
  const descInputId = useId();

  // Queries & Mutations
  const { data, isLoading, isError, refetch } = useWorkspacesQuery({
    page: 1,
    pageSize: 50,
  });

  const workspaces = useMemo(() => {
    if (data?.items && data.items.length > 0) {
      return data.items;
    }
    if (storeActiveWorkspace) {
      return [storeActiveWorkspace];
    }
    return isError ? fallbackWorkspaces : [];
  }, [data?.items, isError, storeActiveWorkspace]);

  // Synchronize active workspace ID with loaded items
  useEffect(() => {
    if (workspaces.length > 0) {
      const exists = workspaces.some((w) => w.id === activeWorkspaceId);
      if (!exists && !activeWorkspaceId) {
        setActiveWorkspace(workspaces[0]);
      }
    }
  }, [workspaces, activeWorkspaceId, setActiveWorkspace]);

  const activeWorkspace = useMemo(() => {
    if (workspaces.length === 0)
      return storeActiveWorkspace || fallbackWorkspaces[0];
    return (
      workspaces.find((w) => w.id === activeWorkspaceId) ??
      storeActiveWorkspace ??
      workspaces[0]
    );
  }, [workspaces, activeWorkspaceId, storeActiveWorkspace]);

  // Create Workspace Dialog State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [newWsCode, setNewWsCode] = useState("");
  const [newWsDesc, setNewWsDesc] = useState("");
  const [isCodeManuallyEdited, setIsCodeManuallyEdited] = useState(false);

  const createMutation = useCreateWorkspaceMutation();

  // Manage Workspace Dialog State
  const [isManageOpen, setIsManageOpen] = useState(false);
  const [newMemberActorRef, setNewMemberActorRef] = useState("");
  const [newMemberDisplayName, setNewMemberDisplayName] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<
    "admin" | "editor" | "reviewer" | "member"
  >("member");

  const { data: membersData, isLoading: isMembersLoading } =
    useWorkspaceMembersQuery(isManageOpen ? activeWorkspace.id : null);

  const {
    data: quotaData,
    isLoading: isQuotaLoading,
    isError: isQuotaError,
  } = useWorkspaceQuotaQuery(isManageOpen ? activeWorkspace.id : null);

  const addMemberMutation = useAddMemberMutation(activeWorkspace.id);
  const revokeMemberMutation = useRevokeMemberMutation(activeWorkspace.id);

  const handleNameChange = (val: string) => {
    setNewWsName(val);
    if (!isCodeManuallyEdited) {
      setNewWsCode(slugify(val));
    }
  };

  const handleCreateWorkspace = async () => {
    const trimmedName = newWsName.trim();
    const trimmedCode = newWsCode.trim();

    if (!trimmedName) {
      toast.error("Vui lòng nhập tên đơn vị làm việc!");
      return;
    }

    if (!trimmedCode || !/^[a-z0-9]+(?:[-_][a-z0-9]+)*$/.test(trimmedCode)) {
      toast.error(
        "Mã định danh (code) không hợp lệ! Chỉ dùng chữ thường không dấu, số, dấu gạch nối (2-64 ký tự).",
      );
      return;
    }

    try {
      const created = await createMutation.mutateAsync({
        code: trimmedCode,
        name: trimmedName,
        description: newWsDesc.trim() || null,
      });

      toast.success(`Đã tạo đơn vị "${created.name}" thành công!`);
      setActiveWorkspace(created);
      setIsCreateOpen(false);
      setNewWsName("");
      setNewWsCode("");
      setNewWsDesc("");
      setIsCodeManuallyEdited(false);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Không thể tạo đơn vị. Kiểm tra quyền hoặc mã code đã tồn tại.";
      toast.error(msg);
    }
  };

  const handleAddMember = async () => {
    const trimmedActor = newMemberActorRef.trim();
    if (!trimmedActor) {
      toast.error("Vui lòng nhập mã định danh người dùng!");
      return;
    }

    try {
      await addMemberMutation.mutateAsync({
        actor_ref: trimmedActor,
        role: newMemberRole,
        display_name: newMemberDisplayName.trim() || null,
      });

      toast.success(`Đã thêm thành viên "${trimmedActor}" vào đơn vị!`);
      setNewMemberActorRef("");
      setNewMemberDisplayName("");
      setNewMemberRole("member");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Không thể thêm thành viên.";
      toast.error(msg);
    }
  };

  const handleRevokeMember = async (memberId: string, actorRef: string) => {
    try {
      await revokeMemberMutation.mutateAsync(memberId);
      toast.success(`Đã thu hồi quyền thành viên "${actorRef}".`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Không thể thu hồi thành viên.";
      toast.error(msg);
    }
  };

  const ActiveIcon = getWorkspaceIcon(
    activeWorkspace.code,
    activeWorkspace.name,
  );

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
              {isLoading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <ActiveIcon className="size-4" />
              )}
            </div>

            {/* Workspace Info (Hidden when sidebar is collapsed) */}
            {!collapsed && (
              <>
                <div className="flex flex-1 flex-col min-w-0">
                  <span className="truncate text-xs font-semibold text-foreground leading-tight">
                    {activeWorkspace.name}
                  </span>
                  <span className="truncate text-[11px] text-muted-foreground leading-tight mt-0.5 font-mono">
                    {activeWorkspace.code}
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
          className="w-72 p-1.5"
        >
          <div className="flex items-center justify-between px-2 py-1">
            <DropdownMenuLabel className="text-[11px] font-medium text-muted-foreground p-0">
              Đơn vị làm việc
            </DropdownMenuLabel>
            {isError && (
              <button
                type="button"
                onClick={() => refetch()}
                className="text-[10px] text-primary hover:underline flex items-center gap-1"
                title="Tải lại danh sách từ API"
              >
                <RefreshCw className="size-2.5" />
                <span>Thử lại</span>
              </button>
            )}
          </div>

          {isLoading && workspaces.length === 0 && (
            <div className="p-3 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="size-3.5 animate-spin" />
              <span>Đang tải đơn vị từ API...</span>
            </div>
          )}

          {workspaces.map((ws, idx) => {
            const WsIcon = getWorkspaceIcon(ws.code, ws.name);
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
                <div className="flex-1 min-w-0">
                  <div className="truncate">{ws.name}</div>
                  <div className="text-[10px] text-muted-foreground truncate font-mono">
                    {ws.code} • {ws.member_count} thành viên
                  </div>
                </div>
                {ws.status === "suspended" ? (
                  <Badge variant="warning" className="text-[9px] px-1.5 py-0">
                    Tạm dừng
                  </Badge>
                ) : (
                  <span className="text-[10px] text-muted-foreground font-mono">
                    ⌘{idx + 1}
                  </span>
                )}
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

          {/* "Chi tiết & Thành viên" Trigger */}
          <DropdownMenuItem
            onClick={() => setIsManageOpen(true)}
            className="flex items-center gap-2.5 p-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <div className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border/80 bg-background">
              <Settings className="size-3.5" />
            </div>
            <span>Quản lý đơn vị hiện tại</span>
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
              Tạo không gian làm việc độc lập (Khoa, Phòng ban, Trung tâm) để
              phân quyền biên soạn và cách ly kho tri thức.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Tên đơn vị */}
            <Field className="gap-2">
              <FieldLabel
                htmlFor={nameInputId}
                className="text-xs font-semibold text-foreground flex items-center gap-1"
              >
                <span>Tên đơn vị</span>
                <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id={nameInputId}
                value={newWsName}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="VD: Khoa Công nghệ Thông tin, Phòng Đào tạo..."
                className="h-9 text-xs"
                onKeyDown={(e) => e.key === "Enter" && handleCreateWorkspace()}
              />
            </Field>

            {/* Mã định danh (Code) */}
            <Field className="gap-2">
              <FieldLabel
                htmlFor={codeInputId}
                className="text-xs font-semibold text-foreground flex items-center gap-1"
              >
                <span>Mã định danh (code)</span>
                <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id={codeInputId}
                value={newWsCode}
                onChange={(e) => {
                  setIsCodeManuallyEdited(true);
                  setNewWsCode(e.target.value);
                }}
                placeholder="VD: khoa-cntt, phong-dao-tao"
                className="h-9 text-xs font-mono"
              />
              <p className="text-[11px] text-muted-foreground leading-tight">
                Chỉ dùng chữ thường không dấu, số, gạch ngang (regex:{" "}
                <code className="text-primary font-mono text-[10px]">
                  ^[a-z0-9]+(?:[-_][a-z0-9]+)*$
                </code>
                ).
              </p>
            </Field>

            {/* Mô tả */}
            <Field className="gap-2">
              <FieldLabel
                htmlFor={descInputId}
                className="text-xs font-semibold text-foreground"
              >
                Mô tả đơn vị (tùy chọn)
              </FieldLabel>
              <Input
                id={descInputId}
                value={newWsDesc}
                onChange={(e) => setNewWsDesc(e.target.value)}
                placeholder="VD: Quản lý kho tri thức tuyển sinh và đề cương..."
                className="h-9 text-xs"
              />
            </Field>
          </div>

          <DialogFooter className="gap-3 sm:gap-3 pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={createMutation.isPending}
              onClick={() => setIsCreateOpen(false)}
              className="h-9 px-4 text-xs font-medium"
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={
                !newWsName.trim() ||
                !newWsCode.trim() ||
                createMutation.isPending
              }
              onClick={handleCreateWorkspace}
              className="h-9 px-4 text-xs font-medium gap-1.5"
            >
              {createMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Check className="size-3.5" />
              )}
              <span>Tạo đơn vị</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Quản lý thông tin & Thành viên đơn vị */}
      <Dialog open={isManageOpen} onOpenChange={setIsManageOpen}>
        <DialogContent className="sm:max-w-xl max-h-[85vh] flex flex-col">
          <DialogHeader className="shrink-0">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center">
                <ActiveIcon className="size-4" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold">
                  {activeWorkspace.name}
                </DialogTitle>
                <DialogDescription className="text-xs font-mono text-muted-foreground">
                  Mã: {activeWorkspace.code} • ID: {activeWorkspace.id}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto space-y-5 py-2 pr-1">
            {/* Quick KPI stats */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-lg border border-border/70 bg-muted/20 space-y-1">
                <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
                  <Users className="size-3.5" />
                  <span>Thành viên</span>
                </div>
                <div className="text-base font-semibold text-foreground">
                  {membersData?.meta?.total ?? activeWorkspace.member_count}
                </div>
              </div>

              <div className="p-3 rounded-lg border border-border/70 bg-muted/20 space-y-1">
                <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
                  <Shield className="size-3.5" />
                  <span>Trạng thái</span>
                </div>
                <div className="text-xs font-medium text-foreground">
                  {activeWorkspace.status === "active" ? (
                    <span className="text-emerald-600 font-semibold">
                      Hoạt động
                    </span>
                  ) : (
                    <span className="text-amber-600 font-semibold">
                      Tạm dừng
                    </span>
                  )}
                </div>
              </div>

              <div className="p-3 rounded-lg border border-border/70 bg-muted/20 space-y-1">
                <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
                  <Info className="size-3.5" />
                  <span>Token đã dùng</span>
                </div>
                <div className="text-xs font-medium font-mono text-foreground">
                  {isQuotaLoading ? (
                    <span className="text-muted-foreground font-sans">
                      Đang tải...
                    </span>
                  ) : isQuotaError ? (
                    <span className="text-destructive font-sans text-[11px]">
                      Lỗi tải dữ liệu
                    </span>
                  ) : quotaData ? (
                    quotaData.tokens_used.toLocaleString()
                  ) : (
                    <span className="text-muted-foreground font-sans">
                      Chưa có dữ liệu
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Danh sách thành viên */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Users className="size-3.5 text-primary" />
                  <span>Danh sách thành viên</span>
                </h4>
                <span className="text-[11px] text-muted-foreground">
                  {membersData?.items?.length ?? 0} người
                </span>
              </div>

              {isMembersLoading ? (
                <div className="p-4 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang tải thành viên...</span>
                </div>
              ) : membersData?.items && membersData.items.length > 0 ? (
                <div className="divide-y divide-border/60 rounded-lg border border-border/70 bg-card overflow-hidden">
                  {membersData.items.map((m) => (
                    <div
                      key={m.id}
                      className="p-2.5 flex items-center justify-between text-xs"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-foreground truncate">
                          {m.display_name || m.actor_ref}
                        </div>
                        <div className="text-[10px] text-muted-foreground font-mono">
                          {m.actor_ref}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={m.role === "admin" ? "default" : "secondary"}
                          className="text-[10px] px-2 py-0 uppercase"
                        >
                          {m.role}
                        </Badge>
                        {m.status === "active" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={revokeMemberMutation.isPending}
                            onClick={() =>
                              handleRevokeMember(m.id, m.actor_ref)
                            }
                            className="h-7 text-[11px] text-destructive hover:bg-destructive/10"
                          >
                            Thu hồi
                          </Button>
                        ) : (
                          <Badge variant="outline" className="text-[10px]">
                            {m.status}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-muted-foreground border border-dashed rounded-lg">
                  Chưa có thành viên nào khác trong đơn vị này.
                </div>
              )}
            </div>

            {/* Thêm thành viên mới */}
            <div className="p-3 rounded-lg border border-border/70 bg-muted/20 space-y-3">
              <h5 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <UserPlus className="size-3.5 text-primary" />
                <span>Thêm thành viên mới</span>
              </h5>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <Input
                  value={newMemberActorRef}
                  onChange={(e) => setNewMemberActorRef(e.target.value)}
                  placeholder="Mã định danh QNU SSO..."
                  className="h-8 text-xs sm:col-span-1"
                />
                <Input
                  value={newMemberDisplayName}
                  onChange={(e) => setNewMemberDisplayName(e.target.value)}
                  placeholder="Họ tên hiển thị..."
                  className="h-8 text-xs sm:col-span-1"
                />
                <div className="flex items-center gap-2 sm:col-span-1">
                  <Select
                    value={newMemberRole}
                    onValueChange={(v) =>
                      setNewMemberRole(
                        v as "admin" | "editor" | "reviewer" | "member",
                      )
                    }
                  >
                    <SelectTrigger className="h-8 text-xs flex-1">
                      <SelectValue placeholder="Vai trò" />
                    </SelectTrigger>
                    <SelectContent className="text-xs">
                      <SelectItem value="member">Thành viên</SelectItem>
                      <SelectItem value="editor">Biên tập viên</SelectItem>
                      <SelectItem value="reviewer">Kiểm duyệt</SelectItem>
                      <SelectItem value="admin">Quản trị viên</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    size="sm"
                    disabled={
                      !newMemberActorRef.trim() || addMemberMutation.isPending
                    }
                    onClick={handleAddMember}
                    className="h-8 px-3 text-xs shrink-0 gap-1"
                  >
                    {addMemberMutation.isPending ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Plus className="size-3" />
                    )}
                    <span>Thêm</span>
                  </Button>
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground leading-tight">
                Dùng đúng mã định danh QNU SSO của người dùng (claim sub); hệ
                thống đối chiếu chính xác, không tra theo email.
              </p>
            </div>
          </div>

          <DialogFooter className="shrink-0 pt-2 border-t border-border/60">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsManageOpen(false)}
              className="h-8 px-4 text-xs font-medium"
            >
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { Field } from "@/components/admin/field";
import { FileUpload } from "@/components/admin/file-upload";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { StatusBadge } from "@/components/admin/status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { Kbd } from "@/components/ui/kbd";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Activity,
  ChevronDown,
  Coins,
  Cpu,
  Filter,
  Info,
  Layers,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import * as React from "react";

export function DesignSystemPage() {
  const [testFile, setTestFile] = React.useState<File | null>(null);
  const [switchState, setSwitchState] = React.useState(true);
  const [progressVal] = React.useState(68);
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [dialogOpen, setDialogOpen] = React.useState(false);

  return (
    <TooltipProvider>
      <div className="space-y-10 pb-16">
        {/* Intro */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Design System Showcase</h1>
          <p className="text-xs text-muted-foreground mt-1">
            Quy chuẩn linh kiện giao diện (UI Primitives) & linh kiện quản trị Trường ĐH Quy Nhơn
            (chuẩn QLKTX - OKLCH Teal, Bo góc 6px controls / 8px surfaces).
          </p>
        </div>

        {/* SECTION 1: BUTTONS */}
        <Card>
          <CardHeader>
            <CardTitle>1. Buttons (Nút bấm & Kích cỡ)</CardTitle>
            <CardDescription>
              Chuẩn chiều cao 36px (default) và 32px (sm). Bo góc 6px (rounded-md).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="default">
                <Sparkles className="size-4" />
                <span>Primary Teal</span>
              </Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="destructive">
                <Trash2 className="size-4" />
                <span>Destructive</span>
              </Button>
              <Button variant="link">Link Button</Button>
              <Button disabled>Disabled</Button>
            </div>

            <Separator />

            <div className="flex flex-wrap items-center gap-3">
              <Button size="sm">Small (32px)</Button>
              <Button size="default">Default (36px)</Button>
              <Button size="lg">Large (40px)</Button>
              <Button size="icon" variant="outline" aria-label="Settings">
                <Filter className="size-4" />
              </Button>
              <Button size="icon-sm" variant="ghost" aria-label="Search">
                <Search className="size-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* SECTION 2: FORM CONTROLS & FIELDS */}
        <Card>
          <CardHeader>
            <CardTitle>2. Form Controls & Field Wrappers</CardTitle>
            <CardDescription>
              Input, Textarea, Label và Field tích hợp lỗi kiểm tra dữ liệu.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Field
              label="Tên bộ sưu tập tri thức"
              required
              hint="Ví dụ: Quy chế Đào tạo Tín chỉ 2024"
            >
              <Input placeholder="Nhập tên tài liệu..." />
            </Field>

            <Field
              label="Khóa định danh (API Key)"
              required
              error="Mã API Key không đúng định dạng qnu_live_..."
            >
              <Input defaultValue="qnu_invalid_123" />
            </Field>

            <div className="md:col-span-2">
              <Field label="System Prompt bổ trợ" hint="Chỉ dẫn chuyên môn ràng buộc cho Trợ lý AI">
                <Textarea
                  placeholder="Bạn là Trợ lý Tư vấn Tuyển sinh Đại học Quy Nhơn..."
                  rows={3}
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        {/* SECTION 3: STATUS BADGES & KPI METRICS */}
        <Card>
          <CardHeader>
            <CardTitle>3. Status Badges & Thẻ Đo Lường KPI</CardTitle>
            <CardDescription>
              Các nhãn trạng thái mạch ngắt Circuit Breaker và thẻ FinOps/TM-08.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Status Badges */}
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status="ready" />
              <StatusBadge status="processing" pulse />
              <StatusBadge status="closed" />
              <StatusBadge status="half_open" pulse />
              <StatusBadge status="open" />
              <StatusBadge status="warning" />
              <StatusBadge status="error" />
              <StatusBadge status="offline" />
            </div>

            {/* Badges Variants */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default">Primary</Badge>
              <Badge variant="secondary">Secondary</Badge>
              <Badge variant="outline">Outline</Badge>
              <Badge variant="success">Faithfulness 1.00</Badge>
              <Badge variant="warning">Quota 85%</Badge>
              <Badge variant="destructive">Error</Badge>
              <Badge variant="info">Dense BGE-M3</Badge>
            </div>

            {/* KPI Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <KpiMetric
                title="Tổng Tokens Sử Dụng Tháng"
                value="1,458,200"
                change="+12.4%"
                changeType="increase"
                description="So với tháng trước"
                icon={Cpu}
              />
              <KpiMetric
                title="Chi Phí FinOps Tạm Tính"
                value="$0.4374"
                change="-5.2%"
                changeType="decrease"
                description="Tối ưu prompt caching"
                icon={Coins}
              />
              <KpiMetric
                title="Độ Trung Thực Ragas TM-08"
                value="0.94 / 1.00"
                change="Đạt Chuẩn"
                changeType="increase"
                description="Ngưỡng quy định >= 0.90"
                icon={ShieldCheck}
              />
            </div>
          </CardContent>
        </Card>

        {/* SECTION 4: TABS & TABLES */}
        <Card>
          <CardHeader>
            <CardTitle>4. Tabs Chức Năng & Bảng Dữ Liệu</CardTitle>
            <CardDescription>
              Bảng biểu chuẩn chiều cao dòng 44px, header 12px muted.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="documents" className="w-full">
              <TabsList>
                <TabsTrigger value="documents">Tài liệu (Documents)</TabsTrigger>
                <TabsTrigger value="jobs">Hàng đợi Ingestion (Jobs)</TabsTrigger>
                <TabsTrigger value="playground">RAG Playground</TabsTrigger>
              </TabsList>

              <TabsContent value="documents" className="mt-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Mã Tài Liệu</TableHead>
                      <TableHead>Tên Văn Bản</TableHead>
                      <TableHead>Số Chunks</TableHead>
                      <TableHead>Trạng Thái</TableHead>
                      <TableHead className="text-right">Thao Tác</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        doc_admissions_2024
                      </TableCell>
                      <TableCell className="font-medium">
                        Đề án Tuyển sinh Đại học chính quy năm 2024
                      </TableCell>
                      <TableCell>42 chunks</TableCell>
                      <TableCell>
                        <StatusBadge status="ready" label="Đã Index" />
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="ghost">
                          Chi tiết
                        </Button>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        doc_regulations_tc
                      </TableCell>
                      <TableCell className="font-medium">
                        Quy chế đào tạo trình độ đại học theo học chế tín chỉ
                      </TableCell>
                      <TableCell>128 chunks</TableCell>
                      <TableCell>
                        <StatusBadge status="ready" label="Đã Index" />
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="ghost">
                          Chi tiết
                        </Button>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TabsContent>

              <TabsContent value="jobs" className="mt-4">
                <EmptyState
                  icon={Activity}
                  title="Không có tác vụ ngầm đang chạy"
                  description="Các tiến trình bóc tách OCR và tạo nhúng vector đã hoàn tất trọn vẹn."
                />
              </TabsContent>

              <TabsContent
                value="playground"
                className="mt-4 p-4 border border-dashed border-border rounded-lg text-center text-xs text-muted-foreground"
              >
                Sân chơi thử nghiệm truy xuất Hybrid RAG (Dense + Sparse FTS + Rerank)
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* SECTION 5: MODALS, DRAWERS, TOOLTIPS & MENUS */}
        <Card>
          <CardHeader>
            <CardTitle>5. Modals, Dropdown Menu, Tooltips & Popover</CardTitle>
            <CardDescription>
              Các cấu phần tương tác nổi, hộp thoại xác nhận và thanh tiến độ.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex flex-wrap items-center gap-4">
              {/* Dialog Trigger */}
              <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Layers className="size-4" />
                    <span>Mở Hộp Thoại Modal</span>
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Cấu Hình Trợ Lý AI</DialogTitle>
                    <DialogDescription>
                      Thiết lập thông số kỹ thuật và bộ lọc an toàn cho mô hình ngôn ngữ.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-3 py-2">
                    <Field label="Nhiệt độ sáng tạo (Temperature)">
                      <Input defaultValue="0.2" />
                    </Field>
                    <div className="flex items-center justify-between pt-2">
                      <div>
                        <p className="text-xs font-medium">Kích hoạt PII Redaction</p>
                        <p className="text-[11px] text-muted-foreground">
                          Tự động che CCCD, SĐT và Email
                        </p>
                      </div>
                      <Switch checked={switchState} onCheckedChange={setSwitchState} />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                      Hủy
                    </Button>
                    <Button onClick={() => setDialogOpen(false)}>Lưu thay đổi</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              {/* Confirm Dialog */}
              <ConfirmDialog
                open={confirmOpen}
                onOpenChange={setConfirmOpen}
                title="Xác nhận dừng luồng DAG?"
                description="Hành động này sẽ hủy tiến trình điều phối đang thực thi và hoàn tiền token chưa dùng."
                onConfirm={() => setConfirmOpen(false)}
                trigger={
                  <Button variant="destructive">
                    <Trash2 className="size-4" />
                    <span>Thử Confirm Dialog</span>
                  </Button>
                }
              />

              {/* Dropdown Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    <span>Thao Tác Thả Xuống</span>
                    <ChevronDown className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Tùy chọn xuất bản</DropdownMenuLabel>
                  <DropdownMenuItem>Xuất Word Nghị định 30 (.docx)</DropdownMenuItem>
                  <DropdownMenuItem>Xuất Excel Bloom (.xlsx)</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive">Xóa bộ sưu tập</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Tooltip */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="icon" variant="outline" aria-label="Thông tin">
                    <Info className="size-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Trường Đại học Quy Nhơn — Nền tảng AI Middleware</p>
                </TooltipContent>
              </Tooltip>

              {/* Popover */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="secondary" size="sm">
                    Mở Popover
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-64">
                  <div className="space-y-2">
                    <h4 className="font-semibold text-xs">Cấu hình nhanh</h4>
                    <p className="text-[11px] text-muted-foreground">
                      Tra cứu nhanh bảng sự thật (Structured Fact Layer) mà không cần gọi LLM.
                    </p>
                  </div>
                </PopoverContent>
              </Popover>
            </div>

            <Separator />

            {/* Progress & Spinners */}
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Tiến độ nhúng Vector BGE-M3:</span>
                <span className="font-mono font-medium">{progressVal}%</span>
              </div>
              <Progress value={progressVal} />

              <div className="flex items-center gap-6 pt-2">
                <div className="flex items-center gap-2">
                  <Spinner size="sm" />
                  <span className="text-xs text-muted-foreground">Đang phân tích token...</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Phím tắt tìm kiếm:</span>
                  <Kbd>Ctrl + K</Kbd>
                </div>
                <div className="flex items-center gap-2">
                  <Avatar>
                    <AvatarFallback>QNU</AvatarFallback>
                  </Avatar>
                  <div className="text-xs">
                    <p className="font-medium leading-none">Cán bộ QNU</p>
                    <p className="text-[11px] text-muted-foreground">Ban Tuyển sinh</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* SECTION 6: FILE UPLOAD ZONE */}
        <Card>
          <CardHeader>
            <CardTitle>6. Vùng Kéo Thả Tải Tệp (File Upload)</CardTitle>
            <CardDescription>
              Tự động nhận diện định dạng PDF, DOCX, XLSX và hiển thị xem trước trước khi ingest.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload selectedFile={testFile} onFileSelect={setTestFile} />
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  );
}

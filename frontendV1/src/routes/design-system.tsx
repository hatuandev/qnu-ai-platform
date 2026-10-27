import { createFileRoute } from "@tanstack/react-router";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Bell,
  CheckCircle2,
  CircleAlert,
  Loader2,
  MoreHorizontal,
  PanelLeft,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import type { DateRange } from "react-day-picker";
import { AccountMenuContent } from "@/components/admin/account-menu";
import {
  ChartCard,
  ChartEmpty,
  ChartError,
  ChartLoading,
} from "@/components/admin/chart-card";
import { Combobox, MultiCombobox } from "@/components/admin/combobox";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTableFacetedFilter } from "@/components/admin/data-table/data-table-faceted-filter";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { DataTableColumnHeader } from "@/components/admin/data-table-column-header";
import {
  DateInput,
  DatePicker,
  DateRangePicker,
  DateTimePicker,
  MonthYearPicker,
} from "@/components/admin/date-pickers";
import { EmptyState } from "@/components/admin/empty-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { FileUpload } from "@/components/admin/file-upload";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { NotificationsPopover } from "@/components/admin/notifications-popover";
import { PageHeader } from "@/components/admin/page-header";
import { QuickCreateMenu } from "@/components/admin/quick-create-menu";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
  ResponsiveDialogTrigger,
} from "@/components/admin/responsive-dialog";
import { StatusBadge } from "@/components/admin/status-badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  SidebarMenuButton,
  SidebarMenuSubButton,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getAnalyticsData } from "@/features/analytics/analytics-data";
import { ActivityTrendChart, CategoryChart } from "@/features/analytics/charts";
import { Breadcrumbs } from "@/layouts/breadcrumbs";
import { formatDateTime } from "@/lib/date-utils";

export const Route = createFileRoute("/design-system")({
  component: DesignSystemPage,
});

type PatternRow = { id: string; name: string; role: string };

function DataTablePatterns() {
  const [selectedRows, setSelectedRows] = useState(["row-1", "row-2"]);
  const patternData: PatternRow[] = [
    { id: "row-1", name: "Example record", role: "Administrator" },
    { id: "row-2", name: "Another record", role: "Viewer" },
  ];
  const patternColumns: ColumnDef<PatternRow>[] = [
    {
      id: "select",
      header: () => <Checkbox aria-label="Select all pattern rows" checked />,
      cell: ({ row }) => (
        <Checkbox
          aria-label={`Select ${row.original.name}`}
          checked={selectedRows.includes(row.original.id)}
          onCheckedChange={(checked) =>
            setSelectedRows((current) =>
              checked
                ? [...current, row.original.id]
                : current.filter((id) => id !== row.original.id),
            )
          }
        />
      ),
      enableHiding: false,
      enableSorting: false,
    },
    {
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="User" />
      ),
    },
    {
      accessorKey: "role",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Vai trò" />
      ),
    },
    {
      id: "actions",
      enableHiding: false,
      enableSorting: false,
      cell: () => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Row actions">
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Xem chi tiết</DropdownMenuItem>
            <DropdownMenuItem>Chỉnh sửa người dùng</DropdownMenuItem>
            <DropdownMenuItem variant="destructive">
              <Trash2 />
              Xóa người dùng
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];
  const table = useReactTable({
    data: patternData,
    columns: patternColumns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  return (
    <section className="space-y-3">
      <h2 className="type-section-title">Mẫu bảng dữ liệu</h2>
      <Card>
        <CardHeader>
          <CardTitle>Tương tác tham chiếu cho người dùng</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <DataTableFacetedFilter
              title="Vai trò"
              options={[
                { value: "admin", label: "Administrator", count: 12 },
                { value: "viewer", label: "Viewer", count: 8 },
              ]}
              selectedValues={["viewer"]}
              onChange={() => undefined}
            />
            <DataTableViewOptions
              table={table}
              labels={{ name: "Người dùng", role: "Vai trò" }}
            />
            <Badge variant="secondary">Đã chọn 2 dòng</Badge>
            <span className="text-xs text-muted-foreground">
              Tiêu đề có thể sắp xếp, bộ lọc nhiều lựa chọn, tùy chọn hiển thị
              và thao tác dòng
            </span>
          </div>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader className="bg-muted/30">
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id} data-state="selected">
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <DataTableEmpty
            title="Trạng thái bảng trống"
            description="Dùng trạng thái này khi chưa có bản ghi hoặc bộ lọc không trả về kết quả."
          />
          <DataTablePagination
            page={2}
            pageSize={20}
            pageCount={8}
            onPageChange={() => undefined}
            onPageSizeChange={() => undefined}
          />
          <DataTableBulkActions
            selectedCount={selectedRows.length}
            selectedLabel="dòng"
            onClear={() => setSelectedRows([])}
          >
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                  aria-label="Kích hoạt các mục đã chọn"
                >
                  <CheckCircle2 className="size-4 text-emerald-500" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Kích hoạt các mục đã chọn
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  aria-label="Xóa các mục đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">Xóa các mục đã chọn</TooltipContent>
            </Tooltip>
          </DataTableBulkActions>
        </CardContent>
      </Card>
    </section>
  );
}

function DataVisualizationPatterns() {
  const data = getAnalyticsData("30d");
  return (
    <section className="space-y-3">
      <h2 className="type-section-title">Trực quan hóa dữ liệu</h2>
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>KPI metric</CardTitle>
          </CardHeader>
          <CardContent className="grid overflow-hidden rounded-md border p-0 sm:grid-cols-2">
            <KpiMetric
              label="Người dùng"
              value="1,248"
              delta="+8.2%"
              trend="positive"
              helper="so với kỳ trước"
            />
            <div className="border-t sm:border-t-0 sm:border-l">
              <KpiMetric
                label="Lỗi hệ thống"
                value="3"
                delta="+2"
                trend="negative"
                helper="cần theo dõi"
              />
            </div>
            <div className="border-t sm:border-t-0">
              <KpiMetric
                label="Vai trò"
                value="12"
                delta="Ổn định"
                trend="neutral"
                helper="catalog hiện tại"
              />
            </div>
          </CardContent>
        </Card>
        <ChartCard
          title="Biểu đồ xu hướng"
          description="Chart foundation dùng Recharts với màu semantic."
        >
          <div className="h-[240px] p-3 sm:h-[280px] sm:p-5">
            <ActivityTrendChart data={data.trend} />
          </div>
        </ChartCard>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Biểu đồ so sánh">
          <div className="h-[220px] p-3 sm:h-[260px] sm:p-5">
            <CategoryChart data={data.categories} />
          </div>
        </ChartCard>
        <Card>
          <CardHeader>
            <CardTitle>Trạng thái biểu đồ</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border">
              <ChartLoading />
            </div>
            <div className="rounded-md border">
              <ChartEmpty title="Không có dữ liệu" />
            </div>
            <div className="rounded-md border">
              <ChartError />
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function ApplicationChromePatterns() {
  return (
    <section className="space-y-3">
      <h2 className="type-section-title">Chrome ứng dụng</h2>
      <Card>
        <CardHeader>
          <CardTitle>Thanh công cụ và menu dùng chung</CardTitle>
          <p className="type-supporting text-muted-foreground">
            Các trigger giữ cùng nhịp 36px, hit area rõ ràng và hoạt động với
            keyboard focus.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 rounded-md border bg-background p-2">
            <Button variant="outline" size="sm">
              <Search />
              Tìm kiếm
              <kbd className="rounded border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                Ctrl K
              </kbd>
            </Button>
            <NotificationsPopover />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Mở menu tài khoản"
                >
                  <Avatar className="size-8">
                    <AvatarFallback>OR</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <AccountMenuContent />
            </DropdownMenu>
            <QuickCreateMenu />
          </div>
          <div className="rounded-md border px-4 py-3">
            <Breadcrumbs />
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function FinalComponentPatterns() {
  return (
    <section className="space-y-3">
      <h2 className="type-section-title">Thành phần nền tảng</h2>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Tabs phẳng</CardTitle>
            <p className="type-supporting text-muted-foreground">
              Dùng cho các nhóm nội dung liên quan, không dùng kiểu pill lớn.
            </p>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Tổng quan</TabsTrigger>
                <TabsTrigger value="permissions">Quyền hạn</TabsTrigger>
                <TabsTrigger value="activity">Hoạt động</TabsTrigger>
              </TabsList>
              <TabsContent
                value="overview"
                className="text-sm text-muted-foreground"
              >
                Nội dung tổng quan của thực thể.
              </TabsContent>
              <TabsContent
                value="permissions"
                className="text-sm text-muted-foreground"
              >
                Nội dung quyền hạn của thực thể.
              </TabsContent>
              <TabsContent
                value="activity"
                className="text-sm text-muted-foreground"
              >
                Nội dung hoạt động của thực thể.
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Radio group</CardTitle>
            <p className="type-supporting text-muted-foreground">
              Lựa chọn ngắn, hiển thị đầy đủ và hỗ trợ bàn phím.
            </p>
          </CardHeader>
          <CardContent>
            <RadioGroup defaultValue="standard" className="gap-2">
              <label
                htmlFor="ds-radio-standard"
                className="flex min-h-9 items-center gap-3 rounded-md border px-3 py-2"
              >
                <RadioGroupItem id="ds-radio-standard" value="standard" />
                <span className="text-sm">Tiêu chuẩn</span>
              </label>
              <label
                htmlFor="ds-radio-compact"
                className="flex min-h-9 items-center gap-3 rounded-md border px-3 py-2"
              >
                <RadioGroupItem id="ds-radio-compact" value="compact" />
                <span className="text-sm">Mật độ cao</span>
              </label>
              <label
                htmlFor="ds-radio-disabled"
                className="flex min-h-9 items-center gap-3 rounded-md border px-3 py-2 opacity-60"
              >
                <RadioGroupItem
                  id="ds-radio-disabled"
                  value="disabled"
                  disabled
                />
                <span className="text-sm">Không khả dụng</span>
              </label>
            </RadioGroup>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Alert và Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Alert variant="info">
              <CircleAlert />
              <AlertTitle>Thông tin</AlertTitle>
              <AlertDescription>
                Đây là thông báo theo ngữ cảnh.
              </AlertDescription>
            </Alert>
            <Alert variant="success">
              <CheckCircle2 />
              <AlertTitle>Đã lưu</AlertTitle>
              <AlertDescription>Thay đổi đã được ghi nhận.</AlertDescription>
            </Alert>
            <div className="space-y-2">
              <div className="type-supporting flex justify-between">
                <span>Hoàn thành</span>
                <span className="font-medium">68%</span>
              </div>
              <Progress value={68} aria-label="Tiến độ hoàn thành" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Empty state và Field</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <EmptyState
              icon={CircleAlert}
              title="Chưa có bản ghi"
              description="Dữ liệu sẽ xuất hiện sau khi có hoạt động mới."
            />
            <Field>
              <FieldLabel htmlFor="ds-field">Tên hiển thị</FieldLabel>
              <Input
                id="ds-field"
                aria-describedby="ds-field-help ds-field-error"
                defaultValue="Giá trị mẫu"
              />
              <FieldDescription id="ds-field-help">
                Tên này hiển thị trong workspace.
              </FieldDescription>
              <FieldError id="ds-field-error">
                Thông báo lỗi nằm ngay dưới control.
              </FieldError>
            </Field>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function MotionPatterns() {
  return (
    <section className="space-y-3">
      <h2 className="type-section-title">Chuyển động &amp; tương tác</h2>
      <Card>
        <CardHeader>
          <CardTitle>Motion là chức năng, không phải trang trí</CardTitle>
          <p className="type-supporting text-muted-foreground">
            Chuyển động giải thích nội dung mở ra từ đâu và trạng thái nào vừa
            thay đổi. Các ví dụ dưới đây dùng chính primitive của ứng dụng.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["Fast", "140ms", "Hover, màu sắc và phản hồi nhỏ"],
              ["Base", "180ms", "Menu, popover và collapsible"],
              ["Slow", "240ms", "Sheet và chuyển động không gian lớn"],
            ].map(([name, value, description]) => (
              <div key={name} className="rounded-md border p-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-semibold">{name}</span>
                  <span className="text-xs text-muted-foreground">{value}</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {description}
                </p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline">Mở Dialog</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Dialog chuyển động nhẹ</DialogTitle>
                  <DialogDescription>
                    Fade và zoom chỉ ở mức 98%, không làm chậm thao tác.
                  </DialogDescription>
                </DialogHeader>
              </DialogContent>
            </Dialog>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">Mở Dropdown</Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem>Xem chi tiết</DropdownMenuItem>
                <DropdownMenuItem>Chỉnh sửa</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline">Mở Popover</Button>
              </PopoverTrigger>
              <PopoverContent>
                <p className="text-sm">
                  Popover dùng cùng motion với Dropdown.
                </p>
              </PopoverContent>
            </Popover>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline">Mở Sheet</Button>
              </SheetTrigger>
              <SheetContent side="right">
                <SheetHeader>
                  <SheetTitle>Sheet chuyển động không gian</SheetTitle>
                  <SheetDescription>
                    Sheet trượt từ đúng cạnh mở ra và đóng nhanh hơn khi thoát.
                  </SheetDescription>
                </SheetHeader>
              </SheetContent>
            </Sheet>
          </div>
          <p className="text-xs text-muted-foreground">
            Easing mở dùng ease-out, đóng dùng ease-in. prefers-reduced-motion
            được tôn trọng tự động.
          </p>
        </CardContent>
      </Card>
    </section>
  );
}

function ExtendedComponentPatterns() {
  const [date, setDate] = useState<Date | undefined>(
    () => new Date(2026, 7, 9),
  );
  const [range, setRange] = useState<DateRange | undefined>({
    from: new Date(2026, 7, 1),
    to: new Date(2026, 7, 9),
  });
  const [month, setMonth] = useState<Date | undefined>(
    () => new Date(2026, 7, 1),
  );
  const [dateTime, setDateTime] = useState<Date | undefined>(
    () => new Date(2026, 7, 9, 17, 30),
  );
  const [invalidDate, setInvalidDate] = useState<string>();
  const [timezone, setTimezone] = useState("Asia/Ho_Chi_Minh");
  const [roles, setRoles] = useState(["editor", "viewer"]);

  const timezoneOptions = [
    { value: "Asia/Ho_Chi_Minh", label: "Asia/Ho_Chi_Minh" },
    { value: "Asia/Tokyo", label: "Asia/Tokyo" },
    { value: "Europe/London", label: "Europe/London" },
    { value: "America/New_York", label: "America/New_York" },
  ];
  const roleOptions = [
    { value: "admin", label: "Quản trị viên" },
    { value: "editor", label: "Biên tập viên" },
    { value: "manager", label: "Quản lý" },
    { value: "viewer", label: "Người xem" },
  ];

  return (
    <>
      <section className="space-y-3">
        <h2 className="type-section-title">Date &amp; Time</h2>
        <Card>
          <CardHeader>
            <CardTitle>Hệ thống ngày giờ</CardTitle>
            <p className="type-supporting text-muted-foreground">
              Mặc định hiển thị DD/MM/YYYY, ngày lịch dùng giờ địa phương và
              không chuyển qua UTC.
            </p>
          </CardHeader>
          <CardContent className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            <Field>
              <FieldLabel htmlFor="ds-date-input">Date Input</FieldLabel>
              <DateInput id="ds-date-input" value={date} onChange={setDate} />
            </Field>
            <Field>
              <FieldLabel htmlFor="ds-date-picker">Date Picker</FieldLabel>
              <DatePicker id="ds-date-picker" value={date} onChange={setDate} />
            </Field>
            <Field>
              <FieldLabel>Date Range</FieldLabel>
              <DateRangePicker value={range} onChange={setRange} />
            </Field>
            <Field>
              <FieldLabel>Month / Year</FieldLabel>
              <MonthYearPicker value={month} onChange={setMonth} />
            </Field>
            <Field>
              <FieldLabel>Date Time</FieldLabel>
              <DateTimePicker value={dateTime} onChange={setDateTime} />
              <FieldDescription>{formatDateTime(dateTime)}</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="ds-invalid-date">Ngày nhập lỗi</FieldLabel>
              <DateInput
                id="ds-invalid-date"
                aria-invalid={Boolean(invalidDate)}
                onValidationChange={setInvalidDate}
              />
              {invalidDate ? <FieldError>{invalidDate}</FieldError> : null}
            </Field>
            <Field>
              <FieldLabel>Ngày cuối tuần bị vô hiệu</FieldLabel>
              <Calendar
                mode="single"
                selected={date}
                onSelect={(nextDate) => nextDate && setDate(nextDate)}
                disabled={[{ dayOfWeek: [0, 6] }]}
              />
            </Field>
            <Field>
              <FieldLabel>Giới hạn ngày tương lai</FieldLabel>
              <DatePicker
                value={date}
                onChange={setDate}
                maxDate={new Date()}
                placeholder="Không chọn ngày tương lai"
              />
            </Field>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Extended Inputs</h2>
        <Card>
          <CardHeader>
            <CardTitle>Combobox và File Upload</CardTitle>
            <p className="type-supporting text-muted-foreground">
              Select cho danh sách nhỏ; Combobox cho lựa chọn có tìm kiếm hoặc
              nhiều giá trị.
            </p>
          </CardHeader>
          <CardContent className="grid gap-5 md:grid-cols-2">
            <Field>
              <FieldLabel>Timezone</FieldLabel>
              <Combobox
                options={timezoneOptions}
                value={timezone}
                onValueChange={(next) => setTimezone(next ?? "")}
                clearable
              />
            </Field>
            <Field>
              <FieldLabel>Vai trò</FieldLabel>
              <MultiCombobox
                options={roleOptions}
                value={roles}
                onValueChange={setRoles}
              />
            </Field>
            <Field className="md:col-span-2">
              <FieldLabel>File Upload</FieldLabel>
              <FileUpload
                accept="image/*,application/pdf"
                multiple
                maxFiles={3}
                maxSize={10 * 1024 * 1024}
                progress={65}
                progressLabel="Ví dụ tiến trình"
              />
            </Field>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">
          Disclosure &amp; Responsive Overlays
        </h2>
        <Card>
          <CardContent className="grid gap-5 pt-5 lg:grid-cols-2">
            <Accordion
              type="single"
              collapsible
              className="rounded-md border px-3"
            >
              <AccordionItem value="filters">
                <AccordionTrigger>Bộ lọc nâng cao</AccordionTrigger>
                <AccordionContent>
                  Accordion dùng cho nhóm các vùng nội dung liên quan;
                  Collapsible vẫn dành cho một vùng tùy ý.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="help">
                <AccordionTrigger>Trợ giúp quyền hạn</AccordionTrigger>
                <AccordionContent>
                  Nội dung đóng/mở dùng Radix keyboard semantics và motion Base
                  180ms.
                </AccordionContent>
              </AccordionItem>
            </Accordion>
            <div className="flex flex-wrap items-start gap-2">
              <Drawer>
                <DrawerTrigger asChild>
                  <Button variant="outline">Mở Drawer</Button>
                </DrawerTrigger>
                <DrawerContent>
                  <DrawerHeader>
                    <DrawerTitle>Drawer hành động mobile</DrawerTitle>
                    <DrawerDescription>
                      Drawer dành cho surface tạm thời ở đáy màn hình; Sheet
                      dành cho panel bên lớn.
                    </DrawerDescription>
                  </DrawerHeader>
                  <div className="min-h-20 overflow-y-auto px-4 text-sm text-muted-foreground">
                    Nội dung có thể cuộn và footer giữ khoảng safe area.
                  </div>
                  <DrawerFooter>
                    <Button>Tiếp tục</Button>
                  </DrawerFooter>
                </DrawerContent>
              </Drawer>
              <ResponsiveDialog>
                <ResponsiveDialogTrigger asChild>
                  <Button variant="outline">Responsive Dialog</Button>
                </ResponsiveDialogTrigger>
                <ResponsiveDialogContent>
                  <ResponsiveDialogHeader>
                    <ResponsiveDialogTitle>
                      Responsive modal
                    </ResponsiveDialogTitle>
                    <ResponsiveDialogDescription>
                      Desktop dùng Dialog, mobile dùng Drawer với cùng nội dung.
                    </ResponsiveDialogDescription>
                  </ResponsiveDialogHeader>
                  <ResponsiveDialogFooter>
                    <Button>Đóng</Button>
                  </ResponsiveDialogFooter>
                </ResponsiveDialogContent>
              </ResponsiveDialog>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  );
}

function DesignSystemPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Phát triển"
        title="Hệ thống thiết kế"
        description="Trang kiểm tra trực quan. Mọi thay đổi token hoặc primitive cần được kiểm tra tại đây trước khi tiếp tục phát triển tính năng."
      />
      <section className="space-y-3">
        <h2 className="type-section-title">Kiểu chữ</h2>
        <Card>
          <CardContent className="space-y-3 pt-5">
            <div className="type-page-title">
              Tiêu đề trang — 30px trên máy tính
            </div>
            <div className="type-section-title">Tiêu đề mục — 18px</div>
            <p className="text-sm">
              Nội dung — 14px. Đây là kích thước đọc mặc định.
            </p>
            <p className="type-control">Nội dung điều khiển — 14px.</p>
            <p className="type-supporting text-muted-foreground">
              Nội dung phụ — 14px.
            </p>
            <p className="type-caption text-muted-foreground">
              Chú thích — 14px.
            </p>
            <p className="type-metadata text-muted-foreground">
              Metadata — 11px trên máy tính, 12px trên mobile.
            </p>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Màu sắc</h2>
        <Card>
          <CardContent className="grid gap-3 pt-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Nền", "bg-background text-foreground"],
              ["Chính", "bg-primary text-primary-foreground"],
              ["Phụ", "bg-secondary text-secondary-foreground"],
              ["Nhấn", "bg-accent text-accent-foreground"],
              ["Thành công", "bg-success text-primary-foreground"],
              ["Thông tin", "bg-info text-primary-foreground"],
              ["Cảnh báo", "bg-warning text-foreground"],
              ["Nguy hiểm", "bg-destructive text-destructive-foreground"],
            ].map(([label, classes]) => (
              <div
                key={label}
                className={`flex h-12 items-center rounded-md border px-3 text-sm font-semibold ${classes}`}
              >
                {label}
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Khoảng cách và mật độ</h2>
        <Card>
          <CardContent className="grid gap-4 pt-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Điều khiển", "36px", "--control-height"],
              ["Điều khiển nhỏ", "32px", "--control-height-sm"],
              ["Mục sidebar", "36px", "--sidebar-item-height"],
              ["Dòng bảng", "44px", "--table-row-height"],
            ].map(([label, value, token]) => (
              <div key={token} className="rounded-md border p-3">
                <div className="text-sm font-semibold">{label}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {value} · {token}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Bề mặt &amp; độ nổi</h2>
        <Card>
          <CardContent className="grid gap-4 pt-5 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-md border bg-background p-4 text-sm font-semibold">
              <div>Control</div>
              <div className="mt-1 text-xs font-normal text-muted-foreground">
                6px · border · không shadow
              </div>
            </div>
            <div className="rounded-lg border bg-card p-4 text-sm font-semibold">
              <div>Surface</div>
              <div className="mt-1 text-xs font-normal text-muted-foreground">
                8px · border · không shadow
              </div>
            </div>
            <div className="rounded-lg border bg-popover p-4 text-sm font-semibold shadow-sm">
              <div>Overlay</div>
              <div className="mt-1 text-xs font-normal text-muted-foreground">
                8px · border · shadow-sm
              </div>
            </div>
            <div className="rounded-lg border bg-background p-4 text-sm font-semibold shadow-md">
              <div>Modal</div>
              <div className="mt-1 text-xs font-normal text-muted-foreground">
                8px · border · shadow-md
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Thao tác và trạng thái</h2>
        <Card>
          <CardContent className="flex flex-wrap items-center gap-2 pt-5">
            <Button>
              <Plus />
              Chính
            </Button>
            <Button variant="secondary">Phụ</Button>
            <Button variant="outline">Viền</Button>
            <Button variant="ghost">Trong suốt</Button>
            <Button variant="destructive">Nguy hiểm</Button>
            <Button disabled>Đã vô hiệu hóa</Button>
            <Button disabled>
              <Loader2 className="animate-spin" />
              Đang tải
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Thao tác biểu tượng"
            >
              <MoreHorizontal />
            </Button>
            <StatusBadge status="active" />
            <StatusBadge status="pending" />
            <Badge variant="warning">Cảnh báo</Badge>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Điều khiển biểu mẫu</h2>
        <Card>
          <CardContent className="grid gap-5 pt-5 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="ds-email">Email</Label>
              <Input id="ds-email" placeholder="ten@vidu.com" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-value">Có giá trị</Label>
              <Input id="ds-value" defaultValue="Giá trị mẫu" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-disabled">Vô hiệu hóa</Label>
              <Input
                id="ds-disabled"
                disabled
                value="Không thể chỉnh sửa"
                readOnly
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-invalid">Không hợp lệ</Label>
              <Input id="ds-invalid" aria-invalid defaultValue="Giá trị lỗi" />
              <p className="text-xs text-destructive">
                Vui lòng kiểm tra giá trị này.
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-icon">Có biểu tượng</Label>
              <div className="relative">
                <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="ds-icon"
                  className="pl-9"
                  placeholder="Tìm kiếm..."
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-textarea">Textarea</Label>
              <Textarea id="ds-textarea" placeholder="Nhập nội dung..." />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-textarea-value">Có giá trị</Label>
              <Textarea
                id="ds-textarea-value"
                defaultValue="Nội dung mô tả mẫu."
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-textarea-disabled">Vô hiệu hóa</Label>
              <Textarea
                id="ds-textarea-disabled"
                disabled
                value="Không thể chỉnh sửa"
                readOnly
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ds-textarea-invalid">Không hợp lệ</Label>
              <Textarea
                id="ds-textarea-invalid"
                aria-invalid
                defaultValue="Giá trị lỗi"
              />
              <p className="text-xs text-destructive">
                Vui lòng kiểm tra giá trị này.
              </p>
            </div>
            <div className="grid gap-2">
              <Label>Vai trò</Label>
              <Select defaultValue="viewer">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Quản trị viên</SelectItem>
                  <SelectItem value="viewer">Người xem</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Label
              className="flex items-center gap-2 text-sm"
              htmlFor="ds-remember"
            >
              <Checkbox id="ds-remember" defaultChecked />
              Ghi nhớ lựa chọn
            </Label>
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <Label className="flex items-center gap-2" htmlFor="ds-unchecked">
                <Checkbox id="ds-unchecked" />
                Chưa chọn
              </Label>
              <Label
                className="flex items-center gap-2"
                htmlFor="ds-indeterminate"
              >
                <Checkbox id="ds-indeterminate" checked="indeterminate" />
                Một phần
              </Label>
              <Label
                className="flex items-center gap-2"
                htmlFor="ds-disabled-check"
              >
                <Checkbox id="ds-disabled-check" disabled />
                Vô hiệu hóa
              </Label>
            </div>
            <Label
              className="flex items-center gap-2 text-sm"
              htmlFor="ds-notifications"
            >
              <Switch id="ds-notifications" defaultChecked />
              Bật thông báo
            </Label>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Lớp phủ</h2>
        <Card>
          <CardContent className="flex flex-wrap gap-2 pt-5">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline">Mở hộp thoại</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Hộp thoại mẫu</DialogTitle>
                  <DialogDescription>
                    Hành vi Radix theo hợp đồng giao diện của dự án.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button>Tiếp tục</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <MoreHorizontal />
                  Trình đơn
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem>Xem</DropdownMenuItem>
                <DropdownMenuItem>Chỉnh sửa</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon">
                  <Bell />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Thông báo</TooltipContent>
            </Tooltip>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline">Mở popover</Button>
              </PopoverTrigger>
              <PopoverContent>
                <div className="space-y-1">
                  <div className="text-sm font-semibold">Popover mẫu</div>
                  <p className="text-sm text-muted-foreground">
                    Khoảng cách và bóng đổ dùng chung.
                  </p>
                </div>
              </PopoverContent>
            </Popover>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline">Mở sheet</Button>
              </SheetTrigger>
              <SheetContent side="right">
                <SheetHeader>
                  <SheetTitle>Sheet mẫu</SheetTitle>
                  <SheetDescription>
                    Nội dung an toàn trên desktop và mobile.
                  </SheetDescription>
                </SheetHeader>
              </SheetContent>
            </Sheet>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Điều hướng</h2>
        <Card>
          <CardContent className="grid gap-1 pt-5 sm:max-w-sm">
            <SidebarMenuButton isActive>
              <PanelLeft />
              <span>Bảng điều khiển</span>
            </SidebarMenuButton>
            <SidebarMenuButton>
              <PanelLeft />
              <span>Người dùng</span>
              <Badge variant="secondary" className="ml-auto">
                14
              </Badge>
            </SidebarMenuButton>
            <SidebarMenuSubButton isActive>
              <span>Tất cả người dùng</span>
            </SidebarMenuSubButton>
            <SidebarMenuSubButton>
              <span>Lời mời</span>
            </SidebarMenuSubButton>
          </CardContent>
        </Card>
      </section>
      <DataTablePatterns />
      <DataVisualizationPatterns />
      <ApplicationChromePatterns />
      <FinalComponentPatterns />
      <MotionPatterns />
      <ExtendedComponentPatterns />
      <section className="space-y-3">
        <h2 className="type-section-title">Bảng</h2>
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader className="bg-muted/30">
              <TableRow>
                <TableHead>Tên</TableHead>
                <TableHead>Trạng thái</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="font-medium">Bản ghi mẫu</TableCell>
                <TableCell>
                  <StatusBadge status="active" />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Đang tải</h2>
        <Card>
          <CardHeader>
            <CardTitle>Nhịp skeleton</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-3/4" />
            <Separator />
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Trạng thái tải, trống và lỗi</h2>
        <Card>
          <CardContent className="grid gap-5 pt-5 md:grid-cols-3">
            <div className="space-y-2">
              <div className="text-sm font-semibold">Đang tải bảng</div>
              <div className="space-y-2 rounded-md border p-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-semibold">
                Bộ lọc không có kết quả
              </div>
              <DataTableEmpty
                title="Không tìm thấy kết quả"
                description="Hãy thử xóa hoặc mở rộng bộ lọc."
              />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-semibold">Lỗi tải dữ liệu</div>
              <div className="rounded-md border border-dashed p-4 text-center">
                <CircleAlert className="mx-auto size-5 text-destructive" />
                <p className="mt-2 text-sm font-semibold">
                  Không thể tải dữ liệu
                </p>
                <Button className="mt-3" variant="outline" size="sm">
                  Thử lại
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
      <section className="space-y-3">
        <h2 className="type-section-title">Trạng thái accessibility</h2>
        <Card>
          <CardContent className="space-y-3 pt-5">
            <p className="text-sm text-muted-foreground">
              Các control dùng focus-visible, nhãn liên kết với input và
              aria-label cho thao tác chỉ có biểu tượng.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Button autoFocus variant="outline">
                Focus-visible
              </Button>
              <Button aria-label="Thông báo" size="icon" variant="ghost">
                <Bell />
              </Button>
              <Button disabled>Không khả dụng</Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

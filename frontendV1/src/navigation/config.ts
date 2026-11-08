import {
  Award,
  BarChart3,
  Bell,
  Building2,
  CalendarClock,
  CheckCheck,
  CircleDollarSign,
  ClipboardList,
  CreditCard,
  DoorOpen,
  GraduationCap,
  Headphones,
  History,
  Home,
  Hotel,
  Layers3,
  LayoutDashboard,
  MapPin,
  PenLine,
  QrCode,
  Receipt,
  ScrollText,
  Server,
  Settings2,
  Tag,
  UserCheck,
  UserRoundCog,
  UsersRound,
} from "lucide-react";
import type { NavGroup, NavItem } from "@/navigation/types";

export const providerNavigation = {
  id: "providers",
  title: "Nhà cung cấp",
  to: "/providers",
  icon: Server,
  scope: "v1",
  permission: "ai.models.manage",
} satisfies NavItem;

export {
  activePrimaryWorkspaceFeature,
  isPrimarySidebarFeatureActive,
  isSettingsRouteActive,
  primaryWorkspaceFeatureKeys,
  resolveWorkspaceExperience,
  workspaceFeatureGroups,
  workspaceFeatureKeys,
  workspaceFeatures,
  workspacePrimaryFeatures,
} from "./workspace-features";

export const navigationGroups: NavGroup[] = [
  // 0. QNU AI — dữ liệu thật từ backendV1 (không phải màn hình mẫu)
  {
    id: "qnu-ai",
    label: "Điều hướng",
    items: [
      {
        id: "dashboard",
        title: "Tổng quan",
        to: "/dashboard",
        icon: LayoutDashboard,
        scope: "v1",
      },
      providerNavigation,
      {
        id: "settings",
        title: "Cấu hình",
        to: "/settings",
        icon: Settings2,
        scope: "v1",
      },
    ],
  },

  // 1. Trang chủ
  {
    id: "overview",
    label: "Trang chủ",
    template: true,
    items: [
      {
        id: "reference-dashboard",
        title: "Tổng quan KTX",
        to: "/reference-dashboard",
        icon: LayoutDashboard,
      },
    ],
  },

  // 2. Xét duyệt & sinh viên
  {
    id: "student-services",
    label: "Xét duyệt & sinh viên",
    template: true,
    items: [
      {
        id: "applications",
        title: "Hồ sơ đăng ký",
        to: "/applications",
        icon: ClipboardList,
        permission: "ktx.applications.view",
        audience: "staff",
      },
      {
        id: "students",
        title: "Danh sách sinh viên",
        to: "/students",
        icon: UsersRound,
        permission: "ktx.students.view",
        audience: "staff",
      },
    ],
  },

  // 3. Phân phòng & Cư trú
  {
    id: "housing-operations",
    label: "Xếp phòng & cư trú",
    template: true,
    items: [
      {
        id: "assignments",
        title: "Xếp phòng",
        to: "/assignments",
        icon: UserCheck,
        permission: "ktx.assignments.view",
      },
      {
        id: "residence-contracts",
        title: "Hợp đồng nội trú",
        to: "/residence-contracts",
        icon: ScrollText,
        permission: "ktx.contracts.view",
      },
      {
        id: "residences",
        title: "Quản lý cư trú",
        to: "/residences",
        icon: Home,
        permission: "ktx.residences.view",
      },
    ],
  },

  // 4. Học vụ & Cấu hình đợt
  {
    id: "academic",
    label: "Học vụ & cấu hình",
    template: true,
    items: [
      {
        id: "academic-years",
        title: "Năm học",
        to: "/academic-years",
        icon: GraduationCap,
        permission: "ktx.academic_years.view",
      },
      {
        id: "registration-periods",
        title: "Đợt đăng ký",
        to: "/registration-periods",
        icon: CalendarClock,
        permission: "ktx.registration_periods.view",
      },
      {
        id: "priority-objects",
        title: "Đối tượng ưu tiên",
        to: "/priority-objects",
        icon: Award,
        permission: "ktx.priority_objects.view",
      },
      {
        id: "difficult-areas",
        title: "Địa bàn ưu tiên",
        to: "/difficult-areas",
        icon: MapPin,
        permission: "ktx.difficult_areas.view",
      },
    ],
  },

  // 5. Tài chính
  {
    id: "finance",
    label: "Tài chính",
    template: true,
    items: [
      {
        id: "fee-rates",
        title: "Mức phí",
        to: "/fee-rates",
        icon: Tag,
        permission: "ktx.fee_rates.view",
      },
      {
        id: "payment-configurations",
        title: "Cấu hình thanh toán",
        to: "/payment-configurations",
        icon: QrCode,
        permission: "ktx.registration_periods.view",
        audience: "staff",
      },
      {
        id: "invoices",
        title: "Hóa đơn",
        to: "/invoices",
        icon: Receipt,
        permission: "ktx.invoices.view",
      },
      {
        id: "payment-submissions",
        title: "Đối soát thanh toán",
        to: "/payment-submissions",
        icon: CheckCheck,
        permission: "ktx.payments.view",
        audience: "staff",
      },
      {
        id: "debts",
        title: "Công nợ",
        to: "/debts",
        icon: CircleDollarSign,
        permission: "ktx.debts.view",
      },
    ],
  },

  // 6. Cơ sở vật chất
  {
    id: "dormitory-facilities",
    label: "Cơ sở vật chất",
    template: true,
    items: [
      {
        id: "buildings",
        title: "Tòa nhà",
        to: "/buildings",
        icon: Building2,
        permission: "ktx.buildings.view",
      },
      {
        id: "floors",
        title: "Tầng",
        to: "/floors",
        icon: Layers3,
        permission: "ktx.floors.view",
      },
      {
        id: "rooms",
        title: "Phòng",
        to: "/rooms",
        icon: DoorOpen,
        permission: "ktx.rooms.view",
      },
      {
        id: "room-types",
        title: "Loại phòng",
        to: "/room-types",
        icon: Hotel,
        permission: "ktx.room_types.view",
      },
    ],
  },

  // 7. Báo cáo thống kê
  {
    id: "reports",
    label: "Báo cáo",
    template: true,
    items: [
      {
        id: "reports",
        title: "Báo cáo",
        to: "/reports",
        icon: BarChart3,
        permission: "ktx.reports.view",
      },
    ],
  },

  // 8. Không gian sinh viên (Dành riêng cho SV)
  {
    id: "student-workspace",
    label: "Không gian sinh viên",
    template: true,
    items: [
      {
        id: "student-registration",
        title: "Đăng ký phòng",
        to: "/student/register",
        icon: PenLine,
        permission: "ktx.applications.submit",
        audience: "student",
      },
      {
        id: "student-registration-history",
        title: "Lịch sử đăng ký",
        to: "/student/registration-history",
        icon: History,
        permission: "ktx.applications.view",
        audience: "student",
      },
      {
        id: "student-room-selection",
        title: "Chọn phòng",
        to: "/student/room-selection",
        icon: DoorOpen,
        permission: "ktx.room_selection.view",
        audience: "student",
      },
      {
        id: "student-payments",
        title: "Thanh toán",
        to: "/student/payments",
        icon: CreditCard,
        permission: "ktx.payments.view",
        audience: "student",
      },
    ],
  },

  // 9. Trao đổi & Hỗ trợ
  {
    id: "communication",
    label: "Trao đổi & hỗ trợ",
    template: true,
    items: [
      {
        id: "notifications",
        title: "Thông báo",
        to: "/notifications",
        icon: Bell,
        permission: "ktx.notifications.view",
      },
      {
        id: "support",
        title: "Hỗ trợ sinh viên",
        to: "/support",
        icon: Headphones,
        permission: "ktx.support.view",
      },
    ],
  },
];

export const hiddenRouteMeta = [
  {
    id: "profile",
    title: "Hồ sơ cá nhân",
    to: "/profile" as const,
    icon: UserRoundCog,
  },
];

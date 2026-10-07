import {
  BookOpen,
  Bot,
  Cpu,
  FileStack,
  FileText,
  LayoutDashboard,
  Network,
  Palette,
  Share2,
  Sparkles,
  UserRoundCog,
} from "lucide-react";
import type { NavGroup } from "@/navigation/types";

export const navigationGroups: NavGroup[] = [
  // 1. Tổng quan
  {
    id: "overview",
    label: "Tổng Quan",
    items: [
      {
        id: "dashboard",
        title: "Bảng Điều Khiển",
        to: "/dashboard",
        icon: LayoutDashboard,
      },
      {
        id: "public_portal",
        title: "Cổng Trợ Lý AI",
        to: "/",
        icon: Sparkles,
      },
    ],
  },

  // 2. Xây dựng AI
  {
    id: "ai_builder",
    label: "Xây Dựng AI",
    items: [
      {
        id: "assistants",
        title: "Trợ Lý AI",
        to: "/assistants",
        icon: Bot,
      },
      {
        id: "documents",
        title: "Kho Tài Liệu",
        to: "/documents",
        icon: FileStack,
      },
      {
        id: "knowledge",
        title: "Kho Tri Thức",
        to: "/knowledge",
        icon: BookOpen,
      },
      {
        id: "models",
        title: "Mô Hình & Provider",
        to: "/models",
        icon: Cpu,
      },
      {
        id: "channels",
        title: "Kênh & Web Widget",
        to: "/channels",
        icon: Share2,
      },
    ],
  },

  // 3. Nâng cao
  {
    id: "advanced",
    label: "Nâng Cao",
    items: [
      {
        id: "nodes",
        title: "Thư Viện Nodes",
        to: "/capabilities/nodes",
        icon: Network,
      },
      {
        id: "document-types",
        title: "Loại Văn Bản",
        to: "/document-types",
        icon: FileText,
      },
      {
        id: "design-system",
        title: "Design System",
        to: "/design-system",
        icon: Palette,
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

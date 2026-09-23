import {
  BookOpen,
  Bot,
  Cpu,
  FileText,
  History,
  LayoutDashboard,
  MessagesSquare,
  Network,
  Palette,
  Scan,
  Share2,
  ShieldCheck,
  UserRoundCog,
  Workflow,
  Wrench,
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
    ],
  },

  // 3. Vận hành
  {
    id: "operations",
    label: "Vận Hành",
    items: [
      {
        id: "conversations",
        title: "Hội Thoại & Handoff",
        to: "/conversations",
        icon: MessagesSquare,
      },
      {
        id: "quality",
        title: "Chất Lượng & Lỗ Hổng",
        to: "/quality",
        icon: ShieldCheck,
      },
      {
        id: "runs",
        title: "Giám Sát Thực Thi",
        to: "/runs",
        icon: History,
      },
    ],
  },

  // 4. Hệ thống
  {
    id: "system",
    label: "Hệ Thống",
    items: [
      {
        id: "integrations",
        title: "Tích Hợp & Kênh",
        to: "/settings/integrations",
        icon: Share2,
      },
    ],
  },

  // 5. Nâng cao
  {
    id: "advanced",
    label: "Nâng Cao",
    items: [
      {
        id: "workflows",
        title: "Thư Viện Workflow",
        to: "/workflows",
        icon: Workflow,
      },
      {
        id: "nodes",
        title: "Thư Viện Nodes",
        to: "/capabilities/nodes",
        icon: Network,
      },
      {
        id: "tools",
        title: "Cổng Công Cụ",
        to: "/capabilities/tools",
        icon: Wrench,
      },
      {
        id: "document-types",
        title: "Loại Văn Bản",
        to: "/document-types",
        icon: FileText,
      },
      {
        id: "ocr-lab",
        title: "OCR Studio Lab",
        to: "/ocr-lab",
        icon: Scan,
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

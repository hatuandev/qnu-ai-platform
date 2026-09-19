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
  Workflow,
  Wrench,
} from "lucide-react";
import type * as React from "react";

export interface NavItem {
  id: string;
  title: string;
  path: string;
  icon: React.ElementType;
  badge?: string;
  badgeVariant?: "default" | "secondary" | "outline" | "success" | "warning" | "info";
  description?: string;
  isDevOnly?: boolean;
}

export interface NavSection {
  id: string;
  title: string;
  items: NavItem[];
  isAdvancedSection?: boolean;
}

export const NAVIGATION_CONFIG: NavSection[] = [
  {
    id: "overview",
    title: "Tổng Quan",
    items: [
      {
        id: "dashboard",
        title: "Bảng Điều Khiển",
        path: "/",
        icon: LayoutDashboard,
        description: "Thống kê Tokens, chi phí FinOps USD và trạng thái các services",
      },
    ],
  },
  {
    id: "ai_builder",
    title: "Xây Dựng AI",
    items: [
      {
        id: "assistants",
        title: "Trợ Lý AI",
        path: "/assistants",
        icon: Bot,
        badge: "5 Trợ lý",
        badgeVariant: "default",
        description: "Tuyển sinh, Quy chế, Thư viện, Soạn thảo NĐ 30, Ngân hàng đề thi Bloom",
      },
      {
        id: "knowledge",
        title: "Kho Tri Thức",
        path: "/knowledge",
        icon: BookOpen,
        badge: "RAG",
        badgeVariant: "success",
        description: "Collections tài liệu, Ingestion wizard, OCR đa tầng và Facts số hóa",
      },
      {
        id: "models",
        title: "Mô Hình & Provider",
        path: "/models",
        icon: Cpu,
        badge: "Providers",
        badgeVariant: "default",
        description: "OpenAI, Gemini, Mistral, Cloudflare, Local vLLM/Ollama và Circuit Breaker",
      },
    ],
  },
  {
    id: "operations",
    title: "Vận Hành",
    items: [
      {
        id: "conversations",
        title: "Hội Thoại & Handoff",
        path: "/conversations",
        icon: MessagesSquare,
        description: "Lịch sử tương tác đa kênh và bàn giao trực tiếp cho Cán bộ tư vấn",
      },
      {
        id: "quality",
        title: "Chất Lượng & Lỗ Hổng",
        path: "/quality",
        icon: ShieldCheck,
        badge: "TM-08",
        badgeVariant: "warning",
        description: "Kiểm định Ragas TM-08, Hòm thư lỗ hổng tri thức và cải tiến liên tục",
      },
      {
        id: "operations_runs",
        title: "Giám Sát Thực Thi",
        path: "/operations/runs",
        icon: History,
        description: "Lịch sử thực thi DAG runs, thời gian xử lý và Hộp thư phê duyệt HITL",
      },
    ],
  },
  {
    id: "system",
    title: "Hệ Thống",
    items: [
      {
        id: "integrations",
        title: "Tích Hợp & Kênh",
        path: "/settings/integrations",
        icon: Share2,
        description: "Cấu hình Web Chat Widget nhúng, CDN script và Khóa API phòng ban",
      },
    ],
  },
  {
    id: "advanced",
    title: "Nâng Cao",
    isAdvancedSection: true,
    items: [
      {
        id: "workflows",
        title: "Thư Viện Workflow",
        path: "/advanced/workflows",
        icon: Workflow,
        badge: "5 DAGs",
        badgeVariant: "outline",
        description: "Điều phối luồng xử lý thông minh 05 Trợ lý AI qua đồ thị topo",
      },
      {
        id: "nodes",
        title: "Thư Viện Nodes",
        path: "/advanced/capabilities/nodes",
        icon: Network,
        description: "Danh mục đặc tả các Node: Input, Route, Approval, RAG, Export",
      },
      {
        id: "tools",
        title: "Cổng Công Cụ",
        path: "/advanced/capabilities/tools",
        icon: Wrench,
        badge: "3 Tools",
        badgeVariant: "secondary",
        description: "Tra cứu UIS điểm chuẩn, xuất Word NĐ 30, xuất bảng tính Excel Bloom",
      },
      {
        id: "document_types",
        title: "Loại Văn Bản",
        path: "/knowledge/settings/document-types",
        icon: FileText,
        description: "Quy chuẩn mẫu biểu hành chính: Quyết định, Quy chế, Tờ trình, Thông báo",
      },
      {
        id: "ocr_lab",
        title: "OCR Studio Lab",
        path: "/knowledge/ocr-lab",
        icon: Scan,
        badge: "Lab",
        badgeVariant: "info",
        description: "Phòng thử nghiệm bóc tách scan, nhận diện bảng biểu và con dấu độc lập",
      },
      {
        id: "design_system",
        title: "Design System",
        path: "/design-system",
        icon: Palette,
        badge: "Dev",
        badgeVariant: "secondary",
        isDevOnly: true,
        description: "Kiểm tra UI Primitives, bảng màu OKLCH, typography và linh kiện",
      },
    ],
  },
];

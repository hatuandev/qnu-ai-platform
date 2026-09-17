import {
  BookOpen,
  Bot,
  Code2,
  Cpu,
  FileText,
  History,
  LayoutDashboard,
  MessageSquare,
  MessagesSquare,
  Network,
  Palette,
  Scan,
  Share2,
  ShieldCheck,
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
}

export interface NavSection {
  id: string;
  title: string;
  items: NavItem[];
}

export const NAVIGATION_CONFIG: NavSection[] = [
  {
    id: "operations",
    title: "Vận Hành & Trợ Lý",
    items: [
      {
        id: "dashboard",
        title: "Bảng Điều Khiển",
        path: "/",
        icon: LayoutDashboard,
        description: "Thống kê Tokens, chi phí FinOps USD và trạng thái các services",
      },
      {
        id: "assistants",
        title: "05 Trợ Lý Chuẩn QNU",
        path: "/assistants",
        icon: Bot,
        badge: "5 Trợ lý",
        badgeVariant: "default",
        description: "Tuyển sinh, Quy chế, Thư viện, Soạn thảo NĐ 30, Ngân hàng đề thi Bloom",
      },
      {
        id: "chat",
        title: "Studio Chat Toàn Năng",
        path: "/chat",
        icon: MessageSquare,
        badge: "SSE",
        badgeVariant: "info",
        description: "Hỏi đáp trực tiếp với Trợ lý AI kèm token streaming và dẫn chứng",
      },
      {
        id: "conversations",
        title: "Hội Thoại & Handoff",
        path: "/conversations",
        icon: MessagesSquare,
        description: "Lịch sử tương tác đa kênh và bàn giao trực tiếp cho Cán bộ tư vấn",
      },
      {
        id: "channels",
        title: "Kênh & Mã Nhúng",
        path: "/channels",
        icon: Share2,
        description: "Cấu hình Web Chat Widget nhúng và CDN script cho Cổng thông tin trường",
      },
      {
        id: "runs",
        title: "Lịch Sử Thực Thi DAG",
        path: "/runs",
        icon: History,
        description: "Truy vết chi tiết từng bước chạy node, input/output và độ trễ",
      },
    ],
  },
  {
    id: "knowledge_hub",
    title: "Kho Tri Thức & Quy Trình",
    items: [
      {
        id: "knowledge",
        title: "Quản Trị Tri Thức",
        path: "/knowledge",
        icon: BookOpen,
        badge: "RAG",
        badgeVariant: "success",
        description: "Collections tài liệu, Ingestion wizard, OCR đa tầng và Hybrid Playground",
      },
      {
        id: "scan-studio",
        title: "Scan & OCR Studio",
        path: "/ocr",
        icon: Scan,
        badge: "Studio",
        badgeVariant: "success",
        description:
          "Bóc tách văn bản scan, nhận diện bảng biểu, con dấu và xem trước Split-Screen",
      },
      {
        id: "document-types",
        title: "Loại Văn Bản",
        path: "/document-types",
        icon: FileText,
        description: "Quy chuẩn mẫu biểu hành chính: Quyết định, Quy chế, Tờ trình, Thông báo",
      },
      {
        id: "nodes",
        title: "Thư Viện DAG Nodes",
        path: "/nodes",
        icon: Network,
        description: "Danh mục đặc tả các Node: Input, Route, Approval, RAG, Export",
      },
      {
        id: "tools",
        title: "Cổng Công Cụ & Tools",
        path: "/tools",
        icon: Wrench,
        badge: "3 Tools",
        badgeVariant: "secondary",
        description: "Tra cứu UIS điểm chuẩn, xuất Word NĐ 30, xuất bảng tính Excel Bloom",
      },
      {
        id: "evaluation",
        title: "Kiểm Định Ragas TM-08",
        path: "/evaluation",
        icon: ShieldCheck,
        badge: "TM-08",
        badgeVariant: "warning",
        description: "Đo lường độ trung thực (>=0.90), độ liên quan (>=0.85), Gap Inbox",
      },
    ],
  },
  {
    id: "system",
    title: "Hệ Thống & Quản Trị",
    items: [
      {
        id: "models",
        title: "Quản Lý Provider",
        path: "/models",
        icon: Cpu,
        badge: "Providers",
        badgeVariant: "default",
        description: "OpenAI, Gemini, Claude, Local vLLM/Ollama, DeepSeek và cấu hình mô hình",
      },
      {
        id: "developer",
        title: "Cổng Developer & API",
        path: "/developer",
        icon: Code2,
        description: "Quản lý khóa API các phòng ban, Webhooks và tài liệu tích hợp",
      },
      {
        id: "design-system",
        title: "Design System QNU",
        path: "/design-system",
        icon: Palette,
        badge: "Showcase",
        badgeVariant: "secondary",
        description: "Kiểm tra UI Primitives, bảng màu OKLCH, typography và linh kiện",
      },
    ],
  },
];

import {
  Award,
  BookOpen,
  DollarSign,
  FileCheck,
  FileText,
  HelpCircle,
  Layers,
  Scale,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import type { Assistant } from "@/features/assistants/types";

export interface QuickPromptItem {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
  query: string;
  color: string;
}

interface QuickPromptsProps {
  assistant?: Assistant | null;
  collectionName?: string;
  onSelectPrompt: (promptText: string) => void;
}

export function QuickPrompts({
  assistant,
  collectionName,
  onSelectPrompt,
}: QuickPromptsProps) {
  const assistantName = (assistant?.name ?? "").toLowerCase();
  const collName = (collectionName ?? "").toLowerCase();
  const isAdmissionRelated =
    assistantName.includes("tuyển sinh") ||
    assistantName.includes("tuyen sinh") ||
    collName.includes("tuyển sinh") ||
    collName.includes("tuyen sinh");

  const prompts: QuickPromptItem[] = isAdmissionRelated
    ? [
        {
          icon: Award,
          title: "Điểm sàn & Chỉ tiêu",
          desc: "Ngưỡng bảo đảm chất lượng đầu vào các ngành",
          query:
            "Ngưỡng bảo đảm chất lượng đầu vào (điểm sàn) và điều kiện tuyển sinh đại học chính quy của trường quy định thế nào?",
          color: "bg-primary/10 border-primary/20 text-primary",
        },
        {
          icon: DollarSign,
          title: "Học phí & Chính sách",
          desc: "Mức thu học phí và các chế độ miễn giảm",
          query:
            "Mức học phí theo quy chế hiện hành và chính sách hỗ trợ học phí, học bổng được quy định ra sao?",
          color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400",
        },
        {
          icon: Layers,
          title: "Tổ hợp xét tuyển",
          desc: "Mã ngành và các môn xét tuyển đại học",
          query:
            "Các phương thức xét tuyển và tổ hợp môn quy định cho từng nhóm ngành được áp dụng thế nào?",
          color: "bg-teal-500/10 border-teal-500/20 text-teal-600 dark:text-teal-400",
        },
        {
          icon: FileCheck,
          title: "Quy đổi chứng chỉ",
          desc: "Quy đổi điểm ngoại ngữ quốc tế (IELTS/TOEIC)",
          query:
            "Quy định quy đổi điểm chứng chỉ ngoại ngữ quốc tế sang thang điểm xét tuyển được thực hiện như thế nào?",
          color: "bg-amber-500/10 border-amber-500/20 text-amber-600 dark:text-amber-400",
        },
        {
          icon: BookOpen,
          title: "Hồ sơ & Thủ tục",
          desc: "Quy trình đăng ký và giấy tờ cần chuẩn bị",
          query:
            "Quy trình nộp hồ sơ, đăng ký nhập học và các mốc thời gian quan trọng cần lưu ý là gì?",
          color: "bg-sky-500/10 border-sky-500/20 text-sky-600 dark:text-sky-400",
        },
        {
          icon: Scale,
          title: "Đối chiếu căn cứ",
          desc: "Văn bản, quyết định ban hành có giá trị pháp lý",
          query:
            "Những quyết định và văn bản ban hành chính thức nào đang là căn cứ quy định cho nội dung này?",
          color: "bg-indigo-500/10 border-indigo-500/20 text-indigo-600 dark:text-indigo-400",
        },
      ]
    : [
        {
          icon: FileText,
          title: "Tóm tắt nội dung chính",
          desc: "Nêu các điểm cốt lõi, phạm vi và mục tiêu",
          query:
            "Hãy tóm tắt ngắn gọn các nội dung cốt lõi và mục tiêu chính trong tài liệu này.",
          color: "bg-primary/10 border-primary/20 text-primary",
        },
        {
          icon: Scale,
          title: "Quy định & Điều kiện",
          desc: "Các tiêu chuẩn, điều kiện áp dụng và thời hạn",
          query:
            "Các quy định, điều kiện hoặc mốc thời gian quan trọng được quy định cụ thể như thế nào?",
          color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400",
        },
        {
          icon: BookOpen,
          title: "Thủ tục & Biểu mẫu",
          desc: "Các bước tiến hành và hồ sơ cần chuẩn bị",
          query:
            "Quy trình thực hiện, các bước tiến hành và hồ sơ biểu mẫu cần chuẩn bị gồm những gì?",
          color: "bg-teal-500/10 border-teal-500/20 text-teal-600 dark:text-teal-400",
        },
        {
          icon: HelpCircle,
          title: "Đối chiếu căn cứ",
          desc: "Dẫn chứng từ các điều khoản, quyết định liên quan",
          query:
            "Những căn cứ pháp lý hoặc quyết định nào được trích dẫn liên quan đến vấn đề này?",
          color: "bg-sky-500/10 border-sky-500/20 text-sky-600 dark:text-sky-400",
        },
      ];

  return (
    <div className="w-full max-w-3xl mx-auto px-2 py-4">
      <div className="flex items-center gap-1.5 mb-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        <Sparkles className="size-3.5 text-primary" />
        <span>Gợi ý câu hỏi bắt đầu</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {prompts.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectPrompt(item.query)}
              className="flex items-start gap-3 p-3 rounded-xl border border-border bg-card hover:bg-muted/50 hover:border-primary/40 hover:shadow-xs transition-all text-left group cursor-pointer"
            >
              <div
                className={`p-2 rounded-lg border ${item.color} mt-0.5 shrink-0 group-hover:scale-105 transition-transform`}
              >
                <Icon className="size-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors flex items-center justify-between">
                  <span className="truncate">{item.title}</span>
                  <ArrowRight className="size-3 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all shrink-0 ml-1" />
                </div>
                <div className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                  {item.desc}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}


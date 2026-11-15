import {
  Building2,
  CheckCircle2,
  FileCheck,
  GraduationCap,
  HelpCircle,
  MapPin,
  MessageSquare,
  Phone,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { scrollToPublicAssistants } from "@/components/landing/landing-assistants";
import { Button } from "@/components/ui/button";

const KPI_STATS = [
  {
    value: "45+",
    label: "Ngành đào tạo chính quy",
    desc: "Đa dạng lĩnh vực: Sư phạm, CNTT, Kinh tế, Kỹ thuật",
    icon: GraduationCap,
  },
  {
    value: "05",
    label: "Phương thức xét tuyển",
    desc: "Linh hoạt cơ hội trúng tuyển đại học chính quy 2026",
    icon: Sparkles,
  },
  {
    value: "100%",
    label: "Căn cứ pháp lý chính thức",
    desc: "Dữ liệu chuẩn hóa từ đề án tuyển sinh & văn bản QNU",
    icon: ShieldCheck,
  },
  {
    value: "24/7",
    label: "Tư vấn trực tuyến",
    desc: "Phản hồi tức thì, giải đáp không giới hạn thời gian",
    icon: CheckCircle2,
  },
];

const STEPS = [
  {
    step: "01",
    title: "Nhập câu hỏi thắc mắc",
    desc: "Đặt bất kỳ câu hỏi nào về phương thức tuyển sinh, điểm sàn, học phí hoặc điều kiện nội trú KTX.",
    icon: HelpCircle,
  },
  {
    step: "02",
    title: "AI đối chiếu văn bản gốc",
    desc: "Hệ thống tự động tra cứu và trích xuất căn cứ từ Đề án tuyển sinh QNU 2026 và các văn bản quy chế chính thức.",
    icon: FileCheck,
  },
  {
    step: "03",
    title: "Nhận kết quả chính xác",
    desc: "Câu trả lời súc tích, minh bạch, kèm trích dẫn văn bản pháp lý và đầu mối liên hệ chính thức.",
    icon: ShieldCheck,
  },
];

export function LandingShowcase({
  onAsk: _onAsk,
}: {
  onAsk?: (question?: string) => void;
}) {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-10 px-4 pb-14 sm:px-6">
      {/* KHỐI 1: 4 KPI STATS NỔI BẬT VỀ TRƯỜNG ĐH QUY NHƠN */}
      <section aria-label="Thông số nổi bật">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
          {KPI_STATS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="group relative flex flex-col justify-between rounded-xl border border-border/70 bg-card/80 p-4 text-center shadow-2xs transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card hover:shadow-xs sm:p-5"
              >
                <div>
                  <div className="mx-auto mb-2 flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform group-hover:scale-105">
                    <Icon className="size-4" />
                  </div>
                  <p className="text-2xl font-bold tracking-tight text-primary sm:text-3xl">
                    {item.value}
                  </p>
                  <p className="mt-1 text-xs font-semibold text-foreground sm:text-sm">
                    {item.label}
                  </p>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                  {item.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* KHỐI 2: KHUÔN VIÊN & GIỚI THIỆU TRƯỜNG ĐẠI HỌC QUY NHƠN */}
      <section
        aria-label="Khuôn viên Đại học Quy Nhơn"
        className="group relative overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm"
      >
        <div className="relative h-64 w-full sm:h-80 md:h-96">
          <img
            src="/qnu_campus.jpg?v=2"
            onError={(e) => {
              const target = e.currentTarget;
              if (!target.src.includes("/slider-qnu.jpg")) {
                target.src = "/slider-qnu.jpg";
              }
            }}
            alt="Khuôn viên Trường Đại học Quy Nhơn"
            className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-transparent" />

          <div className="absolute top-4 left-4 right-4 flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur-md">
              <span className="size-1.5 rounded-full bg-emerald-400" />
              Trực Tuyến · Tuyển Sinh 2026
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white/90 backdrop-blur-md">
              <Building2 className="size-3.5 text-primary" />
              Đại học Công lập · Trực thuộc Bộ GD&ĐT
            </span>
          </div>

          <div className="absolute bottom-4 left-4 right-4 space-y-2 sm:bottom-6 sm:left-6 sm:right-6">
            <div className="flex items-center gap-1.5 text-xs text-emerald-300">
              <MapPin className="size-3.5" />
              <span>170 An Dương Vương, TP. Quy Nhơn, Tỉnh Bình Định</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl md:text-3xl">
              Khuôn Viên Đại Học Quy Nhơn (QNU)
            </h2>
            <p className="max-w-2xl text-xs sm:text-sm leading-relaxed text-white/80">
              Cơ sở đào tạo đại học trọng điểm khu vực Miền Trung - Tây Nguyên
              với khuôn viên khang trang ven biển, hệ thống giảng đường hiện
              đại, thư viện số phong phú và ký túc xá tiện nghi sát biển.
            </p>
          </div>
        </div>
      </section>

      {/* KHỐI 3: QUY TRÌNH "TƯ VẤN NHANH CHÓNG TRONG 3 BƯỚC" */}
      <section
        aria-label="Quy trình tư vấn"
        className="rounded-2xl border border-border/70 bg-card/60 p-6 sm:p-8 backdrop-blur-xs"
      >
        <div className="text-center space-y-1 mb-6 sm:mb-8">
          <p className="type-metadata font-semibold text-primary uppercase tracking-wide">
            Quy trình trực tuyến
          </p>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Tư Vấn Nhanh Chóng Trong 3 Bước
          </h2>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-xl mx-auto">
            Đơn giản hóa hành trình tìm hiểu thông tin tuyển sinh và học vụ của
            bạn
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {STEPS.map((s) => {
            const Icon = s.icon;
            return (
              <div
                key={s.step}
                className="relative flex flex-col justify-between rounded-xl border border-border/60 bg-background/80 p-5 text-left transition-all duration-200 hover:border-primary/40 hover:shadow-2xs"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="size-4.5" />
                    </div>
                    <span className="font-mono text-xs font-bold text-muted-foreground/60">
                      {s.step}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-foreground mb-1">
                    {s.title}
                  </h3>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {s.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* KHỐI 4: BANNER LIÊN HỆ BAN TUYỂN SINH */}
      <section
        aria-label="Liên hệ Ban Tuyển sinh"
        className="relative overflow-hidden rounded-2xl border border-border/70 bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 shadow-sm"
      >
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-xl space-y-1.5">
            <span className="type-metadata font-semibold text-primary uppercase">
              Trường Đại học Quy Nhơn (QNU)
            </span>
            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-foreground">
              Cần Hỗ Trợ Trực Tiếp Từ Ban Tuyển Sinh?
            </h2>
            <p className="text-xs sm:text-sm leading-relaxed text-muted-foreground">
              Đội ngũ cán bộ tuyển sinh QNU luôn sẵn sàng hỗ trợ giải đáp mọi
              thắc mắc chuyên sâu về ngành học, học bổng và thủ tục xác nhận
              nhập học.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2.5">
            <Button
              asChild
              size="sm"
              className="h-9 gap-1.5 text-xs font-medium"
            >
              <a href="tel:1800558849">
                <Phone className="size-3.5" />
                <span>Gọi miễn cước 1800 55 88 49</span>
              </a>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 gap-1.5 bg-background/80 text-xs font-medium"
              onClick={scrollToPublicAssistants}
            >
              <MessageSquare className="size-3.5 text-primary" />
              <span>Trò chuyện cùng AI</span>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

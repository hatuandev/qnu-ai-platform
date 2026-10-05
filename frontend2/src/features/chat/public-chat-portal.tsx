import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Bot,
  Clock,
  Compass,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  MessageSquare,
  Moon,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  X,
  Zap,
} from "lucide-react";
import * as React from "react";
import { useAuth } from "@/app/auth";
import { useTheme } from "@/app/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { listAssistants } from "@/services/assistants-api";

interface CategoryMeta {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

const CATEGORY_MAP: Record<string, CategoryMeta> = {
  all: {
    label: "Tất cả Trợ lý",
    icon: Sparkles,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  admissions: {
    label: "Tuyển sinh Đại học",
    icon: GraduationCap,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  academic: {
    label: "Quy chế & Học vụ",
    icon: BookOpen,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  regulations: {
    label: "Quy chế & Đào tạo",
    icon: BookOpen,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  resources: {
    label: "Thư viện & Học liệu",
    icon: Library,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  library: {
    label: "Thư viện Số",
    icon: Library,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  administration: {
    label: "Soạn thảo Văn bản",
    icon: FileText,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  drafting: {
    label: "Soạn thảo Hành chính",
    icon: FileText,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
  examination: {
    label: "Khảo thí & Đề thi",
    icon: HelpCircle,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  },
};

function resolveCategoryMeta(categorySlug: string): CategoryMeta {
  const norm = (categorySlug || "").toLowerCase();
  for (const [key, meta] of Object.entries(CATEGORY_MAP)) {
    if (norm === key || norm.includes(key)) {
      return meta;
    }
  }
  return {
    label: categorySlug,
    icon: Bot,
    accentColor: "text-primary bg-primary/10 border-primary/20",
  };
}

function formatAssistantDisplayName(name: string, code?: string): string {
  const c = (code || "").toLowerCase();
  const n = (name || "").toLowerCase();
  if (
    c.includes("admission") ||
    c.includes("tuyen_sinh") ||
    n.includes("tuyển sinh")
  ) {
    return "Trợ lý Tư vấn Tuyển sinh 2026";
  }
  if (
    c.includes("regulation") ||
    c.includes("quy_che") ||
    c.includes("academic") ||
    n.includes("quy chế") ||
    n.includes("học vụ")
  ) {
    return "Trợ lý Quy chế & Học vụ";
  }
  if (
    c.includes("library") ||
    c.includes("thu_vien") ||
    c.includes("resources") ||
    n.includes("thư viện") ||
    n.includes("học liệu")
  ) {
    return "Trợ lý Thư viện & Học liệu Số";
  }
  if (
    c.includes("draft") ||
    c.includes("soan_thao") ||
    c.includes("administration") ||
    n.includes("soạn thảo")
  ) {
    return "Trợ lý Soạn thảo Văn bản";
  }
  if (
    c.includes("exam") ||
    c.includes("khao_thi") ||
    c.includes("ngan_hang") ||
    c.includes("question") ||
    c.includes("cau_hoi") ||
    c.includes("de_thi") ||
    n.includes("câu hỏi") ||
    n.includes("ngân hàng") ||
    n.includes("khảo thí") ||
    n.includes("đề thi")
  ) {
    return "Trợ lý Ngân hàng Đề & Khảo thí";
  }
  return name.replace(
    /^Mô-đun trợ lý ảo\s*(tư vấn\s*|hỗ trợ\s*|tra cứu,\s*tư vấn\s*)?/i,
    "Trợ lý ",
  );
}

const TRENDING_QUICK_QUESTIONS = [
  {
    query: "Điểm chuẩn các ngành Sư phạm Toán và CNTT năm gần nhất?",
    slug: "admissions",
    label: "Điểm chuẩn Sư phạm & CNTT",
  },
  {
    query: "Cách tính điểm xét tuyển học bạ 3 năm năm 2026 như thế nào?",
    slug: "admissions",
    label: "Xét tuyển học bạ 2026",
  },
  {
    query: "Điều kiện và tiêu chuẩn xét nhận học bổng khuyến khích học tập?",
    slug: "regulations",
    label: "Học bổng khuyến khích",
  },
  {
    query: "Quy định mượn trả giáo trình và truy cập cơ sở dữ liệu số?",
    slug: "library",
    label: "Mượn sách thư viện số",
  },
];

export function PublicChatPortal() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();
  const [searchTerm, setSearchTerm] = React.useState("");
  const [selectedCategory, setSelectedCategory] = React.useState<string>("all");

  const { data: assistants = [], isLoading } = useQuery({
    queryKey: ["public-assistants"],
    queryFn: () => listAssistants(),
  });

  const categories = React.useMemo(() => {
    const cats = new Set<string>();
    for (const a of assistants) {
      if (a.category) cats.add(a.category);
    }
    return ["all", ...Array.from(cats)];
  }, [assistants]);

  const filteredAssistants = React.useMemo(() => {
    return assistants.filter((item) => {
      const matchSearch =
        !searchTerm ||
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        Boolean(item.code?.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchCat =
        selectedCategory === "all" || item.category === selectedCategory;
      return matchSearch && matchCat;
    });
  }, [assistants, searchTerm, selectedCategory]);

  const spotlightAssistant = React.useMemo(() => {
    if (selectedCategory !== "all" || searchTerm) return null;
    return assistants.find(
      (a) =>
        (a.code || "").toLowerCase().includes("admission") ||
        (a.category || "").toLowerCase().includes("admission"),
    );
  }, [assistants, selectedCategory, searchTerm]);

  const otherAssistants = React.useMemo(() => {
    if (!spotlightAssistant) return filteredAssistants;
    return filteredAssistants.filter((a) => a.id !== spotlightAssistant.id);
  }, [filteredAssistants, spotlightAssistant]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchTerm.trim();
    if (!query) return;

    // Smart routing to most relevant assistant
    const lower = query.toLowerCase();
    let targetSlug = "admissions";
    if (
      lower.includes("học bổng") ||
      lower.includes("tín chỉ") ||
      lower.includes("quy chế") ||
      lower.includes("học vụ")
    ) {
      targetSlug = "regulations";
    } else if (
      lower.includes("thư viện") ||
      lower.includes("giáo trình") ||
      lower.includes("luận văn")
    ) {
      targetSlug = "library";
    } else if (
      lower.includes("soạn thảo") ||
      lower.includes("văn bản") ||
      lower.includes("nghị định")
    ) {
      targetSlug = "drafting";
    } else if (
      lower.includes("đề thi") ||
      lower.includes("câu hỏi") ||
      lower.includes("khảo thí")
    ) {
      targetSlug = "question-bank";
    }

    void navigate({
      to: "/chat/$assistantSlug",
      params: { assistantSlug: targetSlug },
      search: { q: query },
    });
  };

  return (
    <div className="min-h-screen bg-[#faf9f6] dark:bg-background text-foreground flex flex-col selection:bg-primary/20 relative overflow-x-hidden">
      {/* 1. Subtle Architectural Grid with Radial Mask (Fade out towards bottom) */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      >
        {/* Soft Linear Grid - Visible at Top Hero, smoothly fading down before cards */}
        <div
          className="absolute inset-0 bg-repeat [background-size:40px_40px]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(26, 115, 101, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(26, 115, 101, 0.08) 1px, transparent 1px)",
            maskImage:
              "linear-gradient(to bottom, rgba(0, 0, 0, 0.95) 0%, rgba(0, 0, 0, 0.6) 320px, rgba(0, 0, 0, 0) 580px)",
            WebkitMaskImage:
              "linear-gradient(to bottom, rgba(0, 0, 0, 0.95) 0%, rgba(0, 0, 0, 0.6) 320px, rgba(0, 0, 0, 0) 580px)",
          }}
        />

        {/* Ambient Radial Academic Teal Glow behind Hero */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[64rem] h-[24rem] bg-gradient-to-b from-primary/15 via-teal-500/8 to-transparent blur-3xl opacity-60" />
      </div>

      {/* Top Header with Ultra-Glass Navbar */}
      <header className="sticky top-0 z-40 border-b border-border/70 bg-[#faf9f6]/85 dark:bg-background/80 backdrop-blur-xl transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-3 select-none text-inherit no-underline group"
          >
            {/* Real University Logo in crisp container */}
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-white p-1 shadow-xs border border-border/60 group-hover:border-primary/50 transition-colors">
              <img
                src="/logo.png"
                alt="Logo Trường Đại học Quy Nhơn"
                className="size-8 object-contain"
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm sm:text-base tracking-tight text-foreground group-hover:text-primary transition-colors">
                  QNU AI Platform
                </span>
                <Badge
                  variant="outline"
                  className="text-[10px] uppercase font-mono tracking-wider border-primary/40 bg-primary/10 text-primary rounded-micro"
                >
                  Cổng Trực Tuyến
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground hidden sm:block">
                Hệ sinh thái Trợ lý Trí tuệ Nhân tạo Trường Đại học Quy Nhơn
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="size-9 rounded-md text-muted-foreground hover:text-foreground"
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
              aria-label="Đổi giao diện Sáng / Tối"
            >
              {resolvedTheme === "dark" ? (
                <Sun className="size-4 text-amber-400" />
              ) : (
                <Moon className="size-4 text-muted-foreground" />
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs h-9 rounded-md gap-1.5 border-border/80 bg-background hover:bg-muted font-medium"
              onClick={() => void navigate({ to: "/dashboard" })}
            >
              <span>
                {isAuthenticated ? "Vào Bảng Điều Khiển" : "Dành cho Cán bộ"}
              </span>
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12 w-full space-y-12">
        {/* ASYMMETRIC 2-COLUMN HERO (Linear Bento Style) */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* Left Column: Value Prop & Interactive Smart Dock */}
          <div className="lg:col-span-7 space-y-6">
            {/* Glowing Pill Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1 text-xs font-semibold text-primary shadow-xs">
              <Sparkles className="size-3.5 animate-pulse text-primary" />
              <span>Hệ sinh thái Trợ lý AI · ĐH Quy Nhơn</span>
            </div>

            {/* Bold H1 Headline with Academic Teal Gradient (No Orphan Words) */}
            <div className="space-y-2">
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-[1.2]">
                <span className="text-foreground">Một Điểm Chạm.</span>
                <br />
                <span className="bg-gradient-to-r from-primary via-teal-500 to-emerald-600 bg-clip-text text-transparent">
                  Mọi Thông Tin ĐH Quy Nhơn.
                </span>
              </h1>
              <p className="text-muted-foreground text-sm sm:text-base leading-relaxed max-w-xl pt-1">
                Trực tiếp giải đáp tuyển sinh 2026, điểm chuẩn, quy chế học vụ,
                giáo trình thư viện số và hỗ trợ soạn thảo văn bản — cam kết
                100% bám sát văn bản pháp lý chính thức.
              </p>
            </div>

            {/* Glassmorphic AI Prompt Dock */}
            <form onSubmit={handleSearchSubmit} className="relative max-w-xl">
              <div className="flex items-center gap-2 rounded-xl border border-primary/40 bg-card/95 dark:bg-card/85 p-1.5 shadow-md backdrop-blur-md focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                <Search className="size-5 ml-2.5 text-muted-foreground shrink-0" />
                <Input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Hỏi bất kỳ điều gì về Điểm chuẩn, Tuyển sinh, Quy chế..."
                  className="border-0 shadow-none focus-visible:ring-0 text-sm h-10 bg-transparent px-1 placeholder:text-muted-foreground/70"
                />
                {searchTerm && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-8 rounded-md text-muted-foreground hover:text-foreground shrink-0"
                    onClick={() => setSearchTerm("")}
                    aria-label="Xóa từ khóa tìm kiếm"
                  >
                    <X className="size-4" />
                  </Button>
                )}
                <Button
                  type="submit"
                  size="sm"
                  className="h-10 px-4 rounded-md gap-1.5 shrink-0 font-medium shadow-sm bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
                >
                  <span>Hỏi ngay</span>
                  <ArrowRight className="size-4" />
                </Button>
              </div>
            </form>

            {/* 1-Click Trending Hot Queries */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-xs text-muted-foreground font-medium flex items-center gap-1 shrink-0">
                <Zap className="size-3.5 text-amber-500" /> Gợi ý nhanh:
              </span>
              {TRENDING_QUICK_QUESTIONS.map((item) => (
                <Button
                  key={item.label}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs rounded-md px-2.5 py-0 border-border/70 hover:border-primary/50 hover:bg-primary/5 hover:text-primary transition-colors gap-1 text-muted-foreground cursor-pointer font-normal"
                  onClick={() =>
                    void navigate({
                      to: "/chat/$assistantSlug",
                      params: { assistantSlug: item.slug },
                      search: { q: item.query },
                    })
                  }
                >
                  <span>{item.label}</span>
                  <ArrowUpRight className="size-3 opacity-60" />
                </Button>
              ))}
            </div>

            {/* Metric Counters (4 items like 9Router) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border/60 max-w-xl">
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-primary tracking-tight">
                  45+
                </div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mt-0.5">
                  Ngành Đào tạo
                </div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-primary tracking-tight">
                  05
                </div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mt-0.5">
                  Trợ lý AI
                </div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-primary tracking-tight">
                  1.300+
                </div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mt-0.5">
                  Facts Số hóa
                </div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-primary tracking-tight">
                  24/7
                </div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mt-0.5">
                  Hỗ trợ Tức thì
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Hero Visual Showcase (3D Interactive Live Card) */}
          <div className="lg:col-span-5 relative group">
            {/* Ambient backlight glow behind card */}
            <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-primary/30 via-teal-500/20 to-emerald-500/30 opacity-40 blur-xl group-hover:opacity-65 transition duration-500 -z-10" />

            <div className="rounded-2xl border border-border/80 bg-card shadow-xl overflow-hidden backdrop-blur-md">
              {/* Upper Image Showcase: Real Coastal Campus of QNU */}
              <div className="relative h-44 sm:h-52 w-full overflow-hidden">
                <img
                  src="/images/qnu-campus-hero.jpg"
                  alt="Khuôn viên Trường Đại học Quy Nhơn bên bờ biển"
                  className="w-full h-full object-cover object-center filter brightness-[0.92] dark:brightness-[0.6] saturate-[1.15] group-hover:scale-105 transition-transform duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-card via-card/30 to-transparent" />

                {/* Floating Real-time status badge */}
                <div className="absolute top-3 left-3 flex items-center gap-2 rounded-md bg-background/90 backdrop-blur-md border border-border/60 px-2.5 py-1 text-xs font-semibold shadow-xs">
                  <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-foreground">
                    Trực tuyến · Tư vấn 2026
                  </span>
                </div>

                <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground/95 drop-shadow-xs">
                    Trường Đại học Quy Nhơn · 170 An Dương Vương
                  </span>
                  <Badge className="bg-primary text-primary-foreground text-xs rounded-micro shadow-xs">
                    Chính thức
                  </Badge>
                </div>
              </div>

              {/* Lower Simulated Conversational Showcase */}
              <div className="p-5 sm:p-6 space-y-3.5 bg-card border-t border-border/50">
                {/* Simulated User Question */}
                <div className="flex items-start gap-2.5">
                  <div className="size-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold shrink-0 text-muted-foreground">
                    TS
                  </div>
                  <div className="rounded-xl rounded-tl-xs bg-muted/80 px-3.5 py-2 text-xs leading-relaxed text-foreground max-w-[85%]">
                    Năm 2026 trường có những phương thức xét tuyển nào và chỉ
                    tiêu ngành Sư phạm Toán?
                  </div>
                </div>

                {/* Simulated AI Answer with Citation */}
                <div className="flex items-start gap-2.5">
                  <div className="size-7 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center shrink-0">
                    <Bot className="size-4 text-primary" />
                  </div>
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="rounded-xl rounded-tl-xs bg-primary/5 border border-primary/15 px-3.5 py-2.5 text-xs leading-relaxed text-foreground">
                      <p className="font-semibold text-primary mb-1">
                        Trường Đại học Quy Nhơn áp dụng 05 phương thức xét
                        tuyển:
                      </p>
                      <p className="text-muted-foreground text-xs leading-relaxed">
                        1. Điểm thi TN THPT · 2. Học bạ THPT · 3. ĐGNL ĐHQG · 4.
                        Tuyển thẳng · 5. Năng khiếu kết hợp.
                      </p>
                      <div className="mt-2 pt-1.5 border-t border-primary/10 flex items-center gap-1.5 text-xs text-primary/90 font-mono">
                        <ShieldCheck className="size-3.5 text-emerald-500 shrink-0" />
                        <span className="truncate">
                          Căn cứ: [Đề án Tuyển sinh 2026 - QĐ số 2139]
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Direct Action Link Button */}
                <Button
                  className="w-full h-10 rounded-md gap-2 font-medium text-xs shadow-xs bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
                  onClick={() =>
                    void navigate({
                      to: "/chat/$assistantSlug",
                      params: { assistantSlug: "admissions" },
                    })
                  }
                >
                  <MessageSquare className="size-3.5" />
                  <span>Bắt đầu cuộc trò chuyện thực tế</span>
                  <ArrowRight className="size-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* BENTO GRID: CÁC TRỢ LÝ AI CHUYÊN TRÁCH */}
        <section className="space-y-6 pt-4">
          {/* Header & Category Filter (Separated lines, no scrollbar, full visible) */}
          <div className="space-y-4 pb-3 border-b border-border/70">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                <Sparkles className="size-5 text-primary" />
                <span>Khám Phá Các Trợ Lý AI Chuyên Trách</span>
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                Mỗi trợ lý được huấn luyện chuyên biệt theo kho dữ liệu văn bản
                chính thức của Nhà trường
              </p>
            </div>

            {/* Category Filter Pills (Full width, wrapping naturally, 100% visible) */}
            <div className="flex flex-wrap items-center gap-2">
              {categories.map((cat) => {
                const meta = resolveCategoryMeta(cat);
                const Icon = meta.icon;
                const isSelected = selectedCategory === cat;
                return (
                  <Button
                    key={cat}
                    variant={isSelected ? "default" : "outline"}
                    size="sm"
                    className={cn(
                      "h-8 px-3 rounded-md text-xs font-medium gap-1.5 transition-all cursor-pointer",
                      isSelected
                        ? "bg-primary text-primary-foreground shadow-xs"
                        : "border-border/70 bg-card/80 hover:bg-muted text-muted-foreground hover:text-foreground",
                    )}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    <Icon className="size-3.5" />
                    <span>{meta.label}</span>
                  </Button>
                );
              })}
            </div>
          </div>

          {/* Loading Skeleton */}
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Card key={i} className="h-48 rounded-lg">
                  <CardHeader className="p-5">
                    <Skeleton className="h-6 w-3/4 mb-2" />
                    <Skeleton className="h-4 w-full" />
                  </CardHeader>
                  <CardContent className="p-5 pt-0">
                    <Skeleton className="h-10 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && filteredAssistants.length === 0 && (
            <div className="text-center py-16 px-4 rounded-lg border border-dashed border-border/80 bg-card/50">
              <Compass className="size-10 text-muted-foreground mx-auto mb-3 opacity-60" />
              <h3 className="font-semibold text-base text-foreground mb-1">
                Không tìm thấy trợ lý phù hợp
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto mb-4">
                Không có trợ lý AI nào khớp với từ khóa "{searchTerm}". Vui lòng
                thử từ khóa khác hoặc xóa bộ lọc.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="rounded-md"
                onClick={() => {
                  setSearchTerm("");
                  setSelectedCategory("all");
                }}
              >
                Xóa bộ lọc tìm kiếm
              </Button>
            </div>
          )}

          {/* BENTO CARD 1: ADMISSIONS SPOTLIGHT (Featured Hero Bento Box) */}
          {spotlightAssistant && (
            <div className="rounded-xl border border-primary/40 bg-white dark:bg-card p-6 sm:p-7 shadow-xs transition-all hover:border-primary/60 hover:shadow-md">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                <div className="lg:col-span-7 space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className="bg-primary text-primary-foreground text-xs font-semibold px-2.5 py-0.5 rounded-micro">
                      Trọng Điểm Tuyển Sinh 2026
                    </Badge>
                  </div>

                  <div>
                    <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-3">
                      <div className="size-10 rounded-md bg-primary text-primary-foreground flex items-center justify-center shrink-0 shadow-xs">
                        <GraduationCap className="size-6" />
                      </div>
                      <span>
                        {formatAssistantDisplayName(
                          spotlightAssistant.name,
                          spotlightAssistant.code,
                        )}
                      </span>
                    </h3>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed mt-2 max-w-2xl">
                      {spotlightAssistant.description ||
                        "Giải đáp chi tiết về đề án tuyển sinh, điểm chuẩn các năm, phương thức xét tuyển, mức học phí, chính sách học bổng và ký túc xá từ nguồn chính thức của Trường Đại học Quy Nhơn."}
                    </p>
                  </div>

                  {/* Feature assurance chips */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                    <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 dark:bg-background px-2.5 py-1 text-muted-foreground border border-border/70 font-medium">
                      <Sparkles className="size-3 text-primary" /> 45 Ngành đào
                      tạo
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 dark:bg-background px-2.5 py-1 text-muted-foreground border border-border/70 font-medium">
                      <ShieldCheck className="size-3 text-emerald-500" /> 05
                      Phương thức xét tuyển
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 dark:bg-background px-2.5 py-1 text-muted-foreground border border-border/70 font-medium">
                      <Zap className="size-3 text-amber-500" /> Đối soát 100%
                      văn bản gốc
                    </span>
                  </div>
                </div>

                <div className="lg:col-span-5 flex flex-col justify-between h-full space-y-4 bg-slate-50/80 dark:bg-muted/30 p-5 rounded-lg border border-border/60">
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                      <MessageSquare className="size-3.5 text-primary" /> Câu
                      hỏi thường gặp:
                    </span>
                    <div className="space-y-2">
                      <Link
                        to="/chat/$assistantSlug"
                        params={{
                          assistantSlug:
                            spotlightAssistant.code || "admissions",
                        }}
                        search={{
                          q: "Điểm chuẩn ngành Sư phạm Toán học và Công nghệ thông tin năm 2025 là bao nhiêu?",
                        }}
                        className="flex items-center justify-between text-xs text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted/70 p-2.5 rounded-md transition-colors border border-border/50 hover:border-primary/40 group/p"
                      >
                        <span className="truncate">
                          "Điểm chuẩn ngành Sư phạm Toán và CNTT năm gần nhất?"
                        </span>
                        <ArrowUpRight className="size-3.5 text-primary opacity-60 group-hover/p:opacity-100 shrink-0 ml-1.5" />
                      </Link>
                      <Link
                        to="/chat/$assistantSlug"
                        params={{
                          assistantSlug:
                            spotlightAssistant.code || "admissions",
                        }}
                        search={{
                          q: "Trường Đại học Quy Nhơn áp dụng những phương thức xét tuyển nào năm 2026?",
                        }}
                        className="flex items-center justify-between text-xs text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted/70 p-2.5 rounded-md transition-colors border border-border/50 hover:border-primary/40 group/p"
                      >
                        <span className="truncate">
                          "Các phương thức xét tuyển năm 2026?"
                        </span>
                        <ArrowUpRight className="size-3.5 text-primary opacity-60 group-hover/p:opacity-100 shrink-0 ml-1.5" />
                      </Link>
                    </div>
                  </div>

                  <Button
                    className="w-full text-xs h-10 rounded-md gap-2 font-medium shadow-sm bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
                    onClick={() =>
                      void navigate({
                        to: "/chat/$assistantSlug",
                        params: {
                          assistantSlug:
                            spotlightAssistant.code || "admissions",
                        },
                      })
                    }
                  >
                    <span>Bắt đầu tư vấn tuyển sinh</span>
                    <ArrowRight className="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* BENTO CARDS 2: CÁC TRỢ LÝ CHUYÊN TRÁCH KHÁC (Grid 2x2 Bento Box) */}
          {otherAssistants.length > 0 && (
            <div className="space-y-4">
              {spotlightAssistant && (
                <div className="flex items-center gap-2 pt-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Các Trợ Lý Chuyên Trách Khác ({otherAssistants.length})
                  </span>
                  <div className="flex-1 h-px bg-border/60" />
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {otherAssistants.map((assistant) => {
                  const meta = resolveCategoryMeta(assistant.category || "");
                  const Icon = meta.icon;
                  const slug = (
                    assistant.code ||
                    assistant.id ||
                    ""
                  ).toLowerCase();
                  const name = (assistant.name || "").toLowerCase();

                  const isExam =
                    slug.includes("exam") ||
                    slug.includes("khao_thi") ||
                    slug.includes("de_thi") ||
                    slug.includes("question") ||
                    slug.includes("cau_hoi") ||
                    slug.includes("ngan_hang") ||
                    name.includes("câu hỏi") ||
                    name.includes("ngân hàng") ||
                    name.includes("khảo thí") ||
                    name.includes("đề thi");

                  const isDraft =
                    slug.includes("draft") ||
                    slug.includes("soan_thao") ||
                    name.includes("soạn thảo");

                  const isLib =
                    slug.includes("lib") ||
                    slug.includes("thu_vien") ||
                    slug.includes("hoc_lieu") ||
                    name.includes("thư viện");

                  const isReg =
                    slug.includes("regulation") ||
                    slug.includes("quy_che") ||
                    slug.includes("academic") ||
                    name.includes("quy chế") ||
                    name.includes("học vụ");

                  let sampleQuestion =
                    "Cách tính điểm trung bình tích lũy thang điểm 4?";
                  if (isDraft) {
                    sampleQuestion =
                      "Soạn thông báo tổ chức Hội nghị Nghiên cứu Khoa học sinh viên cấp Trường.";
                  } else if (isExam) {
                    sampleQuestion =
                      "Ma trận đề thi tự luận theo thang nhận thức Bloom 4 mức độ như thế nào?";
                  } else if (isLib) {
                    sampleQuestion =
                      "Cách truy cập cơ sở dữ liệu quốc tế ScienceDirect từ xa?";
                  } else if (isReg) {
                    sampleQuestion =
                      "Quy định cảnh báo học tập và thôi học tại Điều 16 như thế nào?";
                  }

                  const displayName = formatAssistantDisplayName(
                    assistant.name,
                    assistant.code,
                  );

                  return (
                    <Card
                      key={assistant.id}
                      className="rounded-xl border border-border/80 bg-white dark:bg-card hover:border-primary/50 shadow-xs hover:shadow-md transition-all duration-300 hover:-translate-y-0.5 flex flex-col justify-between overflow-hidden group"
                    >
                      <CardHeader className="p-5 pb-3 space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-micro border border-primary/25 bg-primary/10 text-primary">
                            {meta.label}
                          </span>
                        </div>

                        <div className="flex items-start gap-3">
                          {/* Crisp white logo container */}
                          <div className="size-10 rounded-md bg-white dark:bg-card p-2 shadow-xs border border-border/60 flex items-center justify-center shrink-0">
                            <Icon className="size-5 text-primary" />
                          </div>
                          <div>
                            <CardTitle className="text-base font-bold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                              {displayName}
                            </CardTitle>
                            <p className="text-xs text-muted-foreground line-clamp-2 mt-1 leading-relaxed">
                              {assistant.description ||
                                "Hệ thống trợ lý thông minh hỗ trợ giải đáp chính xác và bảo đảm căn cứ văn bản chuẩn ĐH Quy Nhơn."}
                            </p>
                          </div>
                        </div>
                      </CardHeader>

                      <CardContent className="p-5 pt-0 space-y-3 mt-auto">
                        {/* 1 Single prominent prompt chip */}
                        <div className="pt-2 border-t border-border/50">
                          <Link
                            to="/chat/$assistantSlug"
                            params={{ assistantSlug: slug }}
                            search={{ q: sampleQuestion }}
                            className="flex items-center justify-between text-xs text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted/70 p-2.5 rounded-md transition-colors border border-border/50 hover:border-primary/40 group/q"
                          >
                            <span className="truncate">"{sampleQuestion}"</span>
                            <ArrowUpRight className="size-3.5 text-primary opacity-60 group-hover/q:opacity-100 shrink-0 ml-1.5" />
                          </Link>
                        </div>

                        <Button
                          className="w-full text-xs h-9 rounded-md gap-1.5 shadow-none font-medium border border-border/80 bg-background hover:bg-primary hover:text-primary-foreground hover:border-primary text-foreground transition-all cursor-pointer group/btn"
                          onClick={() =>
                            void navigate({
                              to: "/chat/$assistantSlug",
                              params: { assistantSlug: slug },
                            })
                          }
                        >
                          <span>Trò chuyện ngay</span>
                          <ArrowRight className="size-3.5 group-hover/btn:translate-x-1 transition-transform" />
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        {/* TRUST & GUARANTEE BAR */}
        <section className="rounded-xl border border-border/70 bg-white/90 dark:bg-card/80 backdrop-blur-xs p-6 grid grid-cols-1 md:grid-cols-3 gap-6 shadow-xs">
          <div className="flex items-start gap-3.5">
            <div className="size-10 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <ShieldCheck className="size-5" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-foreground">
                100% Căn cứ chính thức
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Dữ liệu được đối soát trực tiếp từ văn bản, đề án tuyển sinh và
                quy chế chuẩn của ĐH Quy Nhơn.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="size-10 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Zap className="size-5" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-foreground">
                Hybrid RAG & Fact Layer
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Tra cứu sự thật dạng bảng số hóa, kèm trích dẫn văn bản minh
                chứng chống ảo giác tuyệt đối.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="size-10 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Clock className="size-5" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-foreground">
                Phản hồi trực tuyến 24/7
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Hỗ trợ sinh viên, giảng viên và thí sinh mọi lúc, mọi nơi với
                thời gian phản hồi dưới 2 giây.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER ACADEMIC & UNIVERSITY BRANDING */}
      <footer className="relative z-10 border-t border-border/70 bg-card/60 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-6 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <img
              src="/logo.png"
              alt="Logo QNU"
              className="size-10 object-contain shrink-0 bg-white p-1 rounded-md border border-border/50"
            />
            <div className="space-y-0.5 text-left">
              <p className="font-bold text-foreground text-sm">
                Trường Đại học Quy Nhơn
              </p>
              <p className="text-xs">
                Nền Tảng Trợ Lý Trí Tuệ Nhân Tạo (QNU AI Platform)
              </p>
              <p className="text-xs text-muted-foreground/80">
                170 An Dương Vương, TP. Quy Nhơn, Tỉnh Bình Định • Hotline:
                0256.3846.156
              </p>
            </div>
          </div>

          <div className="text-center sm:text-right space-y-1">
            <p className="text-xs text-muted-foreground/80 max-w-sm">
              Dữ liệu câu trả lời được kiểm soát bằng công nghệ Hybrid RAG kết
              hợp Fact Layer số hóa và Groundedness Guardrails chống ảo giác.
            </p>
            <p className="text-xs font-mono text-muted-foreground/60">
              © 2026 QNU AI Platform. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

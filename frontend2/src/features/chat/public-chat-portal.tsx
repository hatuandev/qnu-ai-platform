import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  MessageSquare,
  Moon,
  Search,
  Sparkles,
  Sun,
} from "lucide-react";
import * as React from "react";
import { useTheme } from "@/app/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { listAssistants } from "@/services/assistants-api";

function getCategoryIcon(category?: string, code?: string) {
  const cat = (category || code || "").toLowerCase();
  if (cat.includes("admission") || cat.includes("tuyen_sinh")) {
    return <GraduationCap className="size-5" />;
  }
  if (cat.includes("regulation") || cat.includes("quy_che") || cat.includes("dao_tao")) {
    return <BookOpen className="size-5" />;
  }
  if (cat.includes("library") || cat.includes("thu_vien")) {
    return <Library className="size-5" />;
  }
  if (cat.includes("draft") || cat.includes("soan_thao") || cat.includes("van_ban")) {
    return <FileText className="size-5" />;
  }
  if (cat.includes("exam") || cat.includes("khao_thi") || cat.includes("ngan_hang")) {
    return <HelpCircle className="size-5" />;
  }
  return <Bot className="size-5" />;
}

export function PublicChatPortal() {
  const navigate = useNavigate();
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
        item.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchCat =
        selectedCategory === "all" || item.category === selectedCategory;
      return matchSearch && matchCat;
    });
  }, [assistants, searchTerm, selectedCategory]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-primary/20">
      {/* Top Header */}
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm font-bold text-sm tracking-wider">
              QNU
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm sm:text-base tracking-tight text-foreground">
                  QNU.AI Platform
                </span>
                <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider border-primary/30 text-primary">
                  Cổng Trực Tuyến
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground hidden sm:block">
                Hệ sinh thái Trợ lý Trí tuệ Nhân tạo Trường Đại học Quy Nhơn
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="size-9 rounded-md"
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
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
              className="text-xs h-9 rounded-md gap-1.5"
              onClick={() => void navigate({ to: "/dashboard" })}
            >
              <span>Dành cho Cán bộ</span>
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 w-full space-y-8">
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
            <Sparkles className="size-3.5" />
            <span>05 Trợ lý AI Chuyên trách Chuẩn Thuyết Minh QNU</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-foreground leading-tight">
            Bạn cần hỗ trợ thông tin gì hôm nay?
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
            Hệ thống trợ lý AI hoạt động 24/7, bám sát 100% văn bản quy chế, đề án tuyển sinh
            và học liệu chính thức của Trường Đại học Quy Nhơn.
          </p>

          {/* Search Box */}
          <div className="pt-2 relative max-w-md mx-auto">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Tìm kiếm trợ lý hoặc nghiệp vụ cần hỏi..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 h-11 text-xs sm:text-sm rounded-lg border-border/80 bg-card shadow-sm"
            />
          </div>
        </div>

        {/* Category Filter Chips */}
        {categories.length > 2 && (
          <div className="flex flex-wrap items-center justify-center gap-1.5 pt-2">
            {categories.map((cat) => (
              <Button
                key={cat}
                variant={selectedCategory === cat ? "default" : "outline"}
                size="sm"
                className="h-8 text-xs rounded-md capitalize"
                onClick={() => setSelectedCategory(cat)}
              >
                {cat === "all" ? "Tất cả trợ lý" : cat}
              </Button>
            ))}
          </div>
        )}

        {/* Assistant Cards Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5].map((i) => (
              <Card key={i} className="p-5 space-y-4">
                <div className="flex items-center gap-3">
                  <Skeleton className="size-11 rounded-lg" />
                  <div className="space-y-1.5 flex-1">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-9 w-full" />
              </Card>
            ))}
          </div>
        ) : filteredAssistants.length === 0 ? (
          <Card className="p-8 text-center space-y-3 bg-muted/20 border-dashed">
            <Bot className="size-10 text-muted-foreground mx-auto" />
            <p className="text-sm font-semibold text-foreground">
              Không tìm thấy trợ lý AI phù hợp
            </p>
            <p className="text-xs text-muted-foreground">
              Vui lòng thử từ khóa tìm kiếm khác hoặc chọn xem tất cả.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredAssistants.map((ast) => {
              const slug = ast.code || ast.id;
              const sampleQuestions =
                Array.isArray(ast.sample_questions) && ast.sample_questions.length > 0
                  ? ast.sample_questions
                  : Array.isArray(ast.config?.sample_questions) &&
                    ast.config.sample_questions.length > 0
                    ? ast.config.sample_questions
                    : [];

              return (
                <Card
                  key={ast.id}
                  className="group flex flex-col justify-between hover:border-primary/50 transition-all hover:shadow-md bg-card"
                >
                  <CardHeader className="p-5 pb-3">
                    <div className="flex items-start gap-3">
                      <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                        {getCategoryIcon(ast.category, ast.code)}
                      </div>
                      <div className="space-y-1 flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <Badge variant="outline" className="text-[10px] font-medium uppercase text-muted-foreground">
                            {ast.category || "AI"}
                          </Badge>
                          <Badge variant="secondary" className="text-[10px] gap-1 text-primary">
                            <CheckCircle2 className="size-3" />
                            <span>Chính thức</span>
                          </Badge>
                        </div>
                        <CardTitle className="text-sm sm:text-base font-bold text-foreground leading-snug line-clamp-1 group-hover:text-primary transition-colors">
                          {ast.name}
                        </CardTitle>
                      </div>
                    </div>
                    <CardDescription className="text-xs text-muted-foreground pt-2 line-clamp-2 leading-relaxed">
                      {ast.description || "Hỗ trợ giải đáp nghiệp vụ chuyên biệt của Nhà trường."}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="p-5 pt-0 space-y-4">
                    {/* Sample questions */}
                    {sampleQuestions.length > 0 && (
                      <div className="space-y-1.5 pt-1 border-t border-border/60">
                        <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
                          <MessageSquare className="size-3" />
                          Câu hỏi gợi ý:
                        </span>
                        <div className="space-y-1">
                          {sampleQuestions.slice(0, 2).map((q, idx) => (
                            <Link
                              key={idx}
                              to="/chat/$assistantSlug"
                              params={{ assistantSlug: slug }}
                              search={{ q }}
                              className="block text-[11px] text-muted-foreground hover:text-primary bg-muted/40 hover:bg-primary/5 px-2.5 py-1.5 rounded-md transition-colors truncate"
                            >
                              "{q}"
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}

                    <Button
                      className="w-full text-xs h-9 rounded-md gap-1.5 shadow-none font-medium"
                      onClick={() =>
                        void navigate({
                          to: "/chat/$assistantSlug",
                          params: { assistantSlug: slug },
                        })
                      }
                    >
                      <span>Trò chuyện ngay</span>
                      <ArrowRight className="size-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/70 bg-card/60 py-6 mt-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center space-y-2 text-xs text-muted-foreground">
          <p className="font-semibold text-foreground">
            Trường Đại học Quy Nhơn — Nền Tảng Trợ Lý Trí Tuệ Nhân Tạo (QNU AI Platform)
          </p>
          <p>
            Địa chỉ: 170 An Dương Vương, TP. Quy Nhơn, Tỉnh Bình Định • Hotline: 0256.3846.156
          </p>
          <p className="text-[11px] text-muted-foreground/80 pt-1">
            Dữ liệu câu trả lời được kiểm soát bằng công nghệ Hybrid RAG kết hợp Fact Layer số hóa và Groundedness Guardrails chống ảo giác.
          </p>
        </div>
      </footer>
    </div>
  );
}

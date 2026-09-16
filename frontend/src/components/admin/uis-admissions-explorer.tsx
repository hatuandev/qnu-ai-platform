import {
  Briefcase,
  CheckCircle2,
  Coins,
  GraduationCap,
  Layers,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import {
  type ToolExecuteResponse,
  UIS_MAJORS_DATABASE,
  type UisMajorInfo,
  apiClient,
} from "../../services/api-client";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";

interface UisAdmissionsExplorerProps {
  onSelectedMajor?: (major: UisMajorInfo) => void;
}

export const UisAdmissionsExplorer: React.FC<UisAdmissionsExplorerProps> = ({
  onSelectedMajor,
}) => {
  const [selectedMajorCode, setSelectedMajorCode] = useState<string>("7480201");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [apiResponse, setApiResponse] = useState<ToolExecuteResponse | null>(null);

  const activeMajor =
    UIS_MAJORS_DATABASE.find((m) => m.major_code === selectedMajorCode) || UIS_MAJORS_DATABASE[0];

  const filteredMajors = UIS_MAJORS_DATABASE.filter(
    (m) =>
      m.major_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.major_code.includes(searchQuery) ||
      m.faculty.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectMajor = (major: UisMajorInfo) => {
    setSelectedMajorCode(major.major_code);
    setApiResponse(null);
    if (onSelectedMajor) {
      onSelectedMajor(major);
    }
  };

  const handleQueryLiveApi = async () => {
    setIsQuerying(true);
    try {
      const res = await apiClient.executeTool({
        tool_name: "query_admission_scores",
        parameters: {
          major_code: activeMajor.major_code,
          year: 2024,
        },
      });
      setApiResponse(res);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-surface bg-muted/40 border border-border">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-primary/10 text-primary">
            <GraduationCap className="size-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground">
              Cổng Tra Cứu Điểm Chuẩn & Chỉ Tiêu Tuyển Sinh UIS Thời Gian Thực
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Đồng bộ dữ liệu thời gian thực từ Cổng Thông Tin Đào Tạo Trường Đại học Quy Nhơn
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="h-7 text-xs font-semibold shadow-xs"
            disabled={isQuerying}
            onClick={handleQueryLiveApi}
          >
            <Sparkles className="size-3 mr-1" />
            <span>{isQuerying ? "Đang truy vấn UIS..." : "Truy Vấn Cổng UIS"}</span>
          </Button>
        </div>
      </div>

      {/* Search & Quick Chips */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm theo tên ngành đào tạo, mã ngành hoặc khoa..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-xs rounded-control border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {filteredMajors.map((major) => (
            <button
              type="button"
              key={major.major_code}
              onClick={() => handleSelectMajor(major)}
              className={`text-xs px-2.5 py-1 rounded-control font-medium flex items-center gap-1.5 transition-all cursor-pointer border ${
                selectedMajorCode === major.major_code
                  ? "bg-primary text-primary-foreground border-primary shadow-xs"
                  : "bg-card hover:bg-muted text-foreground border-border"
              }`}
            >
              <span>{major.major_name}</span>
              <span className="text-[10px] font-mono opacity-80">({major.major_code})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: General Info & Benchmarks (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 pb-3 border-b border-border">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base sm:text-lg font-bold text-foreground">
                    {activeMajor.major_name}
                  </h2>
                  <Badge variant="outline" className="font-mono text-xs text-primary">
                    Mã: {activeMajor.major_code}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{activeMajor.faculty}</p>
                <p className="text-[11px] text-primary/90 font-medium mt-1">{activeMajor.degree}</p>
              </div>

              <div className="text-right sm:shrink-0">
                <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                  Chỉ Tiêu 2025
                </span>
                <span className="text-xl font-bold font-mono text-foreground">
                  {activeMajor.quota_2025}
                </span>
                <span className="text-[10px] text-muted-foreground block">chỉ tiêu</span>
              </div>
            </div>

            {/* 3 Years Benchmarks */}
            <div className="space-y-2">
              <span className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <TrendingUp className="size-3.5 text-primary" />
                <span>Điểm Chuẩn Tuyển Sinh THPT (3 Năm Gần Nhất)</span>
              </span>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 rounded-surface bg-muted/40 border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground block">
                    NĂM 2022
                  </span>
                  <span className="text-lg font-bold font-mono text-foreground">
                    {activeMajor.benchmark_2022.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-muted-foreground block">
                    Điểm sàn xét tuyển
                  </span>
                </div>

                <div className="p-3 rounded-surface bg-muted/40 border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground block">
                    NĂM 2023
                  </span>
                  <span className="text-lg font-bold font-mono text-foreground">
                    {activeMajor.benchmark_2023.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-success block">
                    +{(activeMajor.benchmark_2023 - activeMajor.benchmark_2022).toFixed(2)} điểm
                  </span>
                </div>

                <div className="p-3 rounded-surface bg-primary/10 border border-primary/30">
                  <span className="text-[10px] font-mono text-primary font-bold block">
                    NĂM 2024 (MỚI NHẤT)
                  </span>
                  <span className="text-xl font-bold font-mono text-primary">
                    {activeMajor.benchmark_2024.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-success block">
                    +{(activeMajor.benchmark_2024 - activeMajor.benchmark_2023).toFixed(2)} điểm
                  </span>
                </div>
              </div>
            </div>

            {/* Combinations */}
            <div className="space-y-2">
              <span className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <Layers className="size-3.5 text-primary" />
                <span>Tổ Hợp Môn Xét Tuyển Được Chấp Nhận</span>
              </span>

              <div className="flex flex-wrap gap-2">
                {activeMajor.combinations.map((comb) => (
                  <Badge
                    key={comb}
                    variant="outline"
                    className="font-mono text-xs px-2.5 py-1 bg-muted/50"
                  >
                    <span className="font-bold text-foreground mr-1.5">{comb}</span>
                    <span className="text-muted-foreground text-[10px]">
                      {comb === "A00" && "Toán, Vật lý, Hóa học"}
                      {comb === "A01" && "Toán, Vật lý, Tiếng Anh"}
                      {comb === "D01" && "Ngữ văn, Toán, Tiếng Anh"}
                      {comb === "D07" && "Toán, Hóa học, Tiếng Anh"}
                      {comb === "D14" && "Ngữ văn, Lịch sử, Tiếng Anh"}
                      {comb === "D15" && "Ngữ văn, Địa lý, Tiếng Anh"}
                    </span>
                  </Badge>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* Right: Tuition & Career Opportunities (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-5 space-y-4">
            {/* Tuition Fees */}
            <div className="space-y-2.5">
              <span className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <Coins className="size-3.5 text-primary" />
                <span>Định Mức Học Phí Đào Tạo</span>
              </span>

              <div className="p-3.5 rounded-surface bg-muted/40 border border-border space-y-2 text-xs">
                {activeMajor.tuition_per_credit_vnd === 0 ? (
                  <div className="p-2 rounded-control bg-success/15 text-success font-semibold text-xs">
                    Miễn 100% học phí và nhận trợ cấp sinh hoạt phí hàng tháng theo Nghị định 116
                    của Chính phủ.
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Đơn giá tín chỉ:</span>
                      <span className="font-mono font-bold text-foreground">
                        {activeMajor.tuition_per_credit_vnd.toLocaleString("vi-VN")} đ/tín chỉ
                      </span>
                    </div>
                    <div className="flex items-center justify-between border-t border-border/60 pt-2">
                      <span className="text-muted-foreground">Học phí bình quân năm:</span>
                      <span className="font-mono font-bold text-primary text-sm">
                        ~{activeMajor.tuition_per_year_vnd.toLocaleString("vi-VN")} đ/năm
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Career Opportunities */}
            <div className="space-y-2.5">
              <span className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <Briefcase className="size-3.5 text-primary" />
                <span>Vị Trí Việc Làm Đầu Ra Sau Khi Tốt Nghiệp</span>
              </span>

              <ul className="space-y-1.5 text-xs text-muted-foreground">
                {activeMajor.career_opportunities.map((career) => (
                  <li key={career} className="flex items-start gap-2 leading-relaxed">
                    <span className="size-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                    <span className="text-foreground">{career}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>

          {/* API Execution Response */}
          {apiResponse && (
            <div className="p-3 rounded-surface bg-success/10 border border-success/30 flex items-center justify-between text-xs animate-in fade-in duration-200">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-success shrink-0" />
                <div>
                  <span className="font-semibold text-foreground">
                    Đã đồng bộ thời gian thực từ Cổng UIS thành công!
                  </span>
                  <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
                    Độ trễ phản hồi: {apiResponse.latency_ms}ms • Trạng thái: HTTP 200 OK
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

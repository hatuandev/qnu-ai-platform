import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Code,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  Layers,
  Play,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { type ToolItem, apiClient } from "../services/api-client";

export const ToolsPage: React.FC = () => {
  const [selectedToolCode, setSelectedToolCode] = useState<string>("uis_admissions_query");
  const [inputParam, setInputParam] = useState<string>("7480201");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const { data: tools = [] } = useQuery({
    queryKey: ["tools"],
    queryFn: () => apiClient.getTools(),
  });

  const activeTool = tools.find((t) => t.code === selectedToolCode) || tools[0];

  const getToolIcon = (code: string) => {
    switch (code) {
      case "uis_admissions_query":
        return <GraduationCap className="h-4 w-4" />;
      case "docx_nd30_exporter":
        return <FileText className="h-4 w-4" />;
      case "xlsx_bloom_matrix_exporter":
        return <FileSpreadsheet className="h-4 w-4" />;
      default:
        return <Wrench className="h-4 w-4" />;
    }
  };

  const handleRunTool = () => {
    setIsRunning(true);
    setTestResult(null);

    setTimeout(() => {
      setIsRunning(false);
      if (selectedToolCode === "uis_admissions_query") {
        setTestResult(
          JSON.stringify(
            {
              status: "success",
              tool: "uis_admissions_query",
              input_major_code: inputParam,
              result: {
                major_name: "Công nghệ thông tin",
                benchmark_2024: 24.5,
                quota_2025: 180,
                tuition_per_year: 16500000,
                combinations: ["A00", "A01", "D01", "D07"],
                source: "Cơ sở dữ liệu UIS ĐH Quy Nhơn",
              },
            },
            null,
            2
          )
        );
      } else if (selectedToolCode === "docx_nd30_exporter") {
        setTestResult(
          JSON.stringify(
            {
              status: "pending_human_approval",
              tool: "docx_nd30_exporter",
              document_title: "Quyết định khen thưởng sinh viên NCKH",
              margins_mm: { top: 20, bottom: 20, left: 30, right: 15 },
              font: "Times New Roman 13pt",
              s3_preview_url: "https://s3.qnu.edu.vn/drafts/QD_khen_thuong_draft.docx",
              checkpoint_id: "chk_99812",
              message: "Bản thảo Word đã được sinh và gửi tới Cán bộ Phòng Hành chính phê duyệt.",
            },
            null,
            2
          )
        );
      } else {
        setTestResult(
          JSON.stringify(
            {
              status: "success",
              tool: "xlsx_bloom_matrix_exporter",
              course_code: "IT204",
              course_name: "Cơ sở Dữ liệu",
              total_questions: 20,
              matrix_breakdown: {
                level_1_remember: 6,
                level_2_understand: 6,
                level_3_apply: 5,
                level_4_analyze: 3,
              },
              s3_download_url: "https://s3.qnu.edu.vn/exams/IT204_Bloom_Matrix_2025.xlsx",
            },
            null,
            2
          )
        );
      }
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          Cổng Công Cụ Ngoại Vi & Function Calling
          <Badge variant="outline" className="font-mono text-xs">
            OpenAPI Gateway
          </Badge>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Các công cụ nghiệp vụ được cấp phép cho Trợ lý AI gọi hành động (UIS Tuyển sinh, Xuất Word
          NĐ 30, Xuất Excel Bloom).
        </p>
      </div>

      {/* 03 Standard Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tools.map((tool: ToolItem) => {
          const isSelected = tool.code === selectedToolCode;
          return (
            <Card
              key={tool.id}
              onClick={() => {
                setSelectedToolCode(tool.code);
                setTestResult(null);
                if (tool.code === "uis_admissions_query") setInputParam("7480201");
                else if (tool.code === "docx_nd30_exporter")
                  setInputParam("Quyết định khen thưởng NCKH");
                else setInputParam("IT204 - Cơ sở Dữ liệu");
              }}
              className={`p-4 space-y-3 cursor-pointer transition-all flex flex-col justify-between ${
                isSelected
                  ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                  : "hover:border-primary/40"
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-control bg-primary/10 text-primary">
                      {getToolIcon(tool.code)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-xs text-foreground">{tool.name}</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {tool.code}
                      </span>
                    </div>
                  </div>
                  {tool.requires_approval ? (
                    <Badge variant="warning" className="text-[10px]">
                      Duyệt Cán Bộ
                    </Badge>
                  ) : (
                    <Badge variant="success" className="text-[10px]">
                      Tự Động
                    </Badge>
                  )}
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">{tool.description}</p>
              </div>

              <div className="border-t border-border/60 pt-2.5 flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="font-mono text-primary truncate max-w-[180px]">
                  {tool.endpoint}
                </span>
                <span className="font-mono font-bold text-foreground">
                  {tool.usage_count.toLocaleString("vi-VN")} lượt
                </span>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Interactive Tool Playground */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="text-xs sm:text-sm font-bold text-foreground uppercase tracking-wider">
              Tool Playground — Kiểm Thử Tương Tác: {activeTool?.name}
            </h2>
          </div>
          <Badge variant="outline" className="font-mono text-[11px]">
            {activeTool?.endpoint}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Input Panel */}
          <div className="space-y-3 p-4 rounded-surface bg-muted/30 border border-border">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Code className="h-3.5 w-3.5 text-primary" />
                Tham số đầu vào (Input Parameters)
              </span>
              <span className="text-[11px] text-muted-foreground">JSON payload</span>
            </div>

            <div className="space-y-1.5">
              <span className="text-[11px] text-muted-foreground block">
                {selectedToolCode === "uis_admissions_query"
                  ? "Mã ngành đào tạo (major_code):"
                  : selectedToolCode === "docx_nd30_exporter"
                    ? "Tên văn bản / Trích yếu nội dung:"
                    : "Mã học phần & Tên môn học:"}
              </span>
              <input
                type="text"
                value={inputParam}
                onChange={(e) => setInputParam(e.target.value)}
                className="w-full h-9 rounded-control border border-border bg-background px-3 text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <Button
              onClick={handleRunTool}
              disabled={isRunning || !inputParam.trim()}
              className="w-full text-xs h-9 gap-1.5 font-semibold"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>
                {isRunning ? "Đang gọi Function Calling..." : "Thực Thi Công Cụ (Execute)"}
              </span>
            </Button>
          </div>

          {/* Output Panel */}
          <div className="space-y-3 p-4 rounded-surface bg-muted/30 border border-border">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-info" />
                Phản hồi JSON Schema (Output Response)
              </span>
              {testResult && (
                <span className="text-[10px] text-success flex items-center gap-1 font-mono">
                  <CheckCircle2 className="h-3 w-3" /> HTTP 200 OK
                </span>
              )}
            </div>

            <pre className="p-3 rounded-control bg-card font-mono text-[11px] text-foreground overflow-x-auto border border-border h-44 leading-relaxed whitespace-pre-wrap select-text">
              {testResult ||
                "// Bấm 'Thực Thi Công Cụ' để gửi yêu cầu và quan sát phản hồi JSON..."}
            </pre>
          </div>
        </div>
      </Card>

      {/* Human-in-the-loop Governance Banner */}
      <Card className="p-4 bg-primary/5 border-primary/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-control bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h4 className="font-semibold text-foreground">
              Chính Sách Kiểm Soát Cán Bộ Phê Duyệt (Human-in-the-loop)
            </h4>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Mọi công cụ làm thay đổi dữ liệu chính thức hoặc phát hành văn bản pháp quy bắt buộc
              phải tạo điểm dừng (checkpoint) chờ cán bộ chuyên trách duyệt trước khi hoàn tất.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

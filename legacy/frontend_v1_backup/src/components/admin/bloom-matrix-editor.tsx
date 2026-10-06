import {
  BarChart3,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { type ToolExecuteResponse, apiClient } from "../../services/api-client";
import { Button } from "../ui/button";

export interface BloomTopicRow {
  id: string;
  topicName: string;
  rememberCount: number; // Cấp 1: Nhận biết
  understandCount: number; // Cấp 2: Thông hiểu
  applyCount: number; // Cấp 3: Vận dụng
  analyzeCount: number; // Cấp 4: Vận dụng cao
  topicScore: number;
}

const DEFAULT_TOPICS: BloomTopicRow[] = [
  {
    id: "topic_1",
    topicName: "Chương 1: Tổng quan Cơ sở Dữ liệu & Mô hình Quan hệ",
    rememberCount: 4,
    understandCount: 3,
    applyCount: 1,
    analyzeCount: 0,
    topicScore: 2.0,
  },
  {
    id: "topic_2",
    topicName: "Chương 2: Ngôn ngữ Truy vấn SQL & Tối ưu Hóa Truy vấn",
    rememberCount: 2,
    understandCount: 3,
    applyCount: 3,
    analyzeCount: 1,
    topicScore: 3.5,
  },
  {
    id: "topic_3",
    topicName: "Chương 3: Phụ thuộc Hàm & Chuẩn Hóa BCNF / 3NF",
    rememberCount: 1,
    understandCount: 2,
    applyCount: 2,
    analyzeCount: 1,
    topicScore: 2.5,
  },
  {
    id: "topic_4",
    topicName: "Chương 4: Giao tác (Transaction) & Khóa Đồng Thời ACID",
    rememberCount: 1,
    understandCount: 1,
    applyCount: 1,
    analyzeCount: 1,
    topicScore: 2.0,
  },
];

interface BloomMatrixEditorProps {
  onGeneratedSuccess?: (response: ToolExecuteResponse) => void;
}

export const BloomMatrixEditor: React.FC<BloomMatrixEditorProps> = ({ onGeneratedSuccess }) => {
  const [courseName, setCourseName] = useState<string>("Lập trình Cơ sở Dữ liệu");
  const [courseCode, setCourseCode] = useState<string>("IT204");
  const [examDuration, setExamDuration] = useState<number>(60);
  const [topics, setTopics] = useState<BloomTopicRow[]>(DEFAULT_TOPICS);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [lastResponse, setLastResponse] = useState<ToolExecuteResponse | null>(null);

  // Tính tổng số câu hỏi theo từng cấp độ
  const totals = useMemo(() => {
    let remember = 0;
    let understand = 0;
    let apply = 0;
    let analyze = 0;
    let totalScore = 0;

    for (const t of topics) {
      remember += Number(t.rememberCount) || 0;
      understand += Number(t.understandCount) || 0;
      apply += Number(t.applyCount) || 0;
      analyze += Number(t.analyzeCount) || 0;
      totalScore += Number(t.topicScore) || 0;
    }

    const totalQuestions = remember + understand + apply + analyze;
    const safeTotal = totalQuestions || 1;

    return {
      remember,
      understand,
      apply,
      analyze,
      totalQuestions,
      totalScore: Number(totalScore.toFixed(1)),
      rememberPct: Math.round((remember / safeTotal) * 100),
      understandPct: Math.round((understand / safeTotal) * 100),
      applyPct: Math.round((apply / safeTotal) * 100),
      analyzePct: Math.round((analyze / safeTotal) * 100),
    };
  }, [topics]);

  // Thêm chủ đề mới
  const handleAddTopic = () => {
    const newId = `topic_${Date.now()}`;
    setTopics((prev) => [
      ...prev,
      {
        id: newId,
        topicName: `Chương ${prev.length + 1}: Chủ đề kiến thức mới`,
        rememberCount: 2,
        understandCount: 2,
        applyCount: 1,
        analyzeCount: 0,
        topicScore: 1.5,
      },
    ]);
  };

  // Cập nhật giá trị ô trong hàng
  const handleUpdateField = (
    id: string,
    field: keyof Omit<BloomTopicRow, "id">,
    value: string | number
  ) => {
    setTopics((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        return { ...item, [field]: value };
      })
    );
  };

  // Xóa chủ đề
  const handleDeleteTopic = (id: string) => {
    if (topics.length <= 1) return;
    setTopics((prev) => prev.filter((t) => t.id !== id));
  };

  // Khôi phục mặc định
  const handleReset = () => {
    setCourseName("Lập trình Cơ sở Dữ liệu");
    setCourseCode("IT204");
    setExamDuration(60);
    setTopics(DEFAULT_TOPICS);
    setLastResponse(null);
  };

  // Gọi API xuất Excel
  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      const res = await apiClient.executeTool({
        tool_name: "export_exam_matrix",
        parameters: {
          course_name: courseName,
          course_code: courseCode,
          exam_duration_minutes: examDuration,
          topics: topics.map((t) => ({
            topic_name: t.topicName,
            recognition_count: t.rememberCount,
            comprehension_count: t.understandCount,
            application_count: t.applyCount,
            advanced_application_count: t.analyzeCount,
            total_score: t.topicScore,
          })),
        },
      });

      setLastResponse(res);
      if (res.status === "success" && onGeneratedSuccess) {
        onGeneratedSuccess(res);
      }
    } finally {
      setIsExporting(false);
    }
  };

  // Giả lập tải xuống tệp XLSX
  const handleDownloadExcel = () => {
    const csvContent = `Chủ đề,Nhận biết,Thông hiểu,Vận dụng,Vận dụng cao,Tổng điểm\n${topics
      .map(
        (t) =>
          `"${t.topicName}",${t.rememberCount},${t.understandCount},${t.applyCount},${t.analyzeCount},${t.topicScore}`
      )
      .join("\n")}`;
    const blob = new Blob([csvContent], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Ma_Tran_De_Thi_${courseCode}_Bloom.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Top Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-surface bg-muted/40 border border-border">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-emerald-500/10 text-emerald-600">
            <FileSpreadsheet className="size-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground">
              Thiết Kế Ma Trận Đề Thi Chuẩn Tư Duy Bloom (4 Cấp Độ)
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Tự động tính phân bổ tỷ lệ nhận thức, trọng số điểm và kết xuất bảng tính Excel
              (.xlsx)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleReset}>
            <RotateCcw className="size-3 mr-1" />
            <span>Mặc định</span>
          </Button>

          <Button
            size="sm"
            className="h-7 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
            disabled={isExporting}
            onClick={handleExportExcel}
          >
            <Sparkles className="size-3 mr-1" />
            <span>{isExporting ? "Đang xuất Excel..." : "Xuất File Excel (.xlsx)"}</span>
          </Button>
        </div>
      </div>

      {/* Course Info Ribbon */}
      <div className="p-3.5 rounded-surface bg-card border border-border grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <label
            htmlFor="input-course-name"
            className="text-[11px] text-muted-foreground font-medium block mb-1"
          >
            Tên học phần / Môn thi:
          </label>
          <input
            id="input-course-name"
            type="text"
            value={courseName}
            onChange={(e) => setCourseName(e.target.value)}
            className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary font-semibold"
          />
        </div>

        <div>
          <label
            htmlFor="input-course-code"
            className="text-[11px] text-muted-foreground font-medium block mb-1"
          >
            Mã học phần:
          </label>
          <input
            id="input-course-code"
            type="text"
            value={courseCode}
            onChange={(e) => setCourseCode(e.target.value)}
            className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary font-mono font-semibold"
          />
        </div>

        <div>
          <label
            htmlFor="input-exam-duration"
            className="text-[11px] text-muted-foreground font-medium block mb-1"
          >
            Thời gian thi (phút):
          </label>
          <input
            id="input-exam-duration"
            type="number"
            value={examDuration}
            onChange={(e) => setExamDuration(Number(e.target.value))}
            className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary font-mono"
          />
        </div>

        <div>
          <span className="text-[11px] text-muted-foreground font-medium block mb-1">
            Tổng kết kiểm tra:
          </span>
          <div className="flex items-center gap-2 h-8 px-2.5 rounded-control bg-muted/60 border border-border text-xs font-mono font-bold">
            <span className="text-primary">{totals.totalQuestions} câu</span>
            <span className="text-muted-foreground">•</span>
            <span className={totals.totalScore === 10 ? "text-success" : "text-amber-500"}>
              {totals.totalScore} / 10.0 đ
            </span>
          </div>
        </div>
      </div>

      {/* Visual Bloom Distribution Bar */}
      <div className="p-3.5 rounded-surface bg-card border border-border space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-foreground flex items-center gap-1.5">
            <BarChart3 className="size-3.5 text-primary" />
            <span>Biểu Đồ Phân Bổ Tỷ Lệ Cấp Độ Nhận Thức Bloom</span>
          </span>
          <span className="text-[11px] font-mono text-muted-foreground">
            Tổng cộng: 100% tỷ trọng đề thi
          </span>
        </div>

        {/* 4 Colors Segmented Bar */}
        <div className="h-4 w-full rounded-full overflow-hidden flex bg-muted/60 border border-border/80">
          <div
            style={{ width: `${totals.rememberPct}%` }}
            className="bg-blue-500 transition-all duration-300"
            title={`Nhận biết: ${totals.remember} câu (${totals.rememberPct}%)`}
          />
          <div
            style={{ width: `${totals.understandPct}%` }}
            className="bg-emerald-500 transition-all duration-300"
            title={`Thông hiểu: ${totals.understand} câu (${totals.understandPct}%)`}
          />
          <div
            style={{ width: `${totals.applyPct}%` }}
            className="bg-amber-500 transition-all duration-300"
            title={`Vận dụng: ${totals.apply} câu (${totals.applyPct}%)`}
          />
          <div
            style={{ width: `${totals.analyzePct}%` }}
            className="bg-purple-500 transition-all duration-300"
            title={`Vận dụng cao: ${totals.analyze} câu (${totals.analyzePct}%)`}
          />
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-blue-500 shrink-0" />
            <span className="text-muted-foreground">Nhận biết:</span>
            <span className="font-mono font-bold text-foreground">
              {totals.remember} ({totals.rememberPct}%)
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-emerald-500 shrink-0" />
            <span className="text-muted-foreground">Thông hiểu:</span>
            <span className="font-mono font-bold text-foreground">
              {totals.understand} ({totals.understandPct}%)
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-amber-500 shrink-0" />
            <span className="text-muted-foreground">Vận dụng:</span>
            <span className="font-mono font-bold text-foreground">
              {totals.apply} ({totals.applyPct}%)
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-purple-500 shrink-0" />
            <span className="text-muted-foreground">Vận dụng cao:</span>
            <span className="font-mono font-bold text-foreground">
              {totals.analyze} ({totals.analyzePct}%)
            </span>
          </div>
        </div>
      </div>

      {/* Main Interactive Matrix Table */}
      <div className="p-4 rounded-surface bg-card border border-border space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-xs text-foreground">
            Bảng Ma Trận Phân Phối Chi Tiết ({topics.length} Chủ Đề)
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-6 text-[11px] px-2"
            onClick={handleAddTopic}
          >
            <Plus className="size-3 mr-1" />
            <span>Thêm chủ đề</span>
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/50 text-[11px] text-muted-foreground">
                <th className="p-2.5 w-10 text-center font-mono">STT</th>
                <th className="p-2.5 min-w-[220px]">Tên Chủ Đề / Chương Kiến Thức</th>
                <th className="p-2.5 w-24 text-center text-blue-600 dark:text-blue-400">
                  Nhận Biết
                </th>
                <th className="p-2.5 w-24 text-center text-emerald-600 dark:text-emerald-400">
                  Thông Hiểu
                </th>
                <th className="p-2.5 w-24 text-center text-amber-600 dark:text-amber-400">
                  Vận Dụng
                </th>
                <th className="p-2.5 w-24 text-center text-purple-600 dark:text-purple-400">
                  Vận Dụng Cao
                </th>
                <th className="p-2.5 w-20 text-center">Điểm</th>
                <th className="p-2.5 w-10 text-center">Xóa</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {topics.map((t, idx) => (
                <tr key={t.id} className="hover:bg-muted/30 transition-colors">
                  <td className="p-2.5 text-center font-mono text-muted-foreground">{idx + 1}</td>
                  <td className="p-2.5">
                    <input
                      type="text"
                      value={t.topicName}
                      onChange={(e) => handleUpdateField(t.id, "topicName", e.target.value)}
                      className="w-full h-7 px-2 text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary"
                    />
                  </td>
                  <td className="p-2.5 text-center">
                    <input
                      type="number"
                      min={0}
                      value={t.rememberCount}
                      onChange={(e) =>
                        handleUpdateField(t.id, "rememberCount", Number(e.target.value))
                      }
                      className="w-16 h-7 text-center font-mono text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary mx-auto block"
                    />
                  </td>
                  <td className="p-2.5 text-center">
                    <input
                      type="number"
                      min={0}
                      value={t.understandCount}
                      onChange={(e) =>
                        handleUpdateField(t.id, "understandCount", Number(e.target.value))
                      }
                      className="w-16 h-7 text-center font-mono text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary mx-auto block"
                    />
                  </td>
                  <td className="p-2.5 text-center">
                    <input
                      type="number"
                      min={0}
                      value={t.applyCount}
                      onChange={(e) =>
                        handleUpdateField(t.id, "applyCount", Number(e.target.value))
                      }
                      className="w-16 h-7 text-center font-mono text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary mx-auto block"
                    />
                  </td>
                  <td className="p-2.5 text-center">
                    <input
                      type="number"
                      min={0}
                      value={t.analyzeCount}
                      onChange={(e) =>
                        handleUpdateField(t.id, "analyzeCount", Number(e.target.value))
                      }
                      className="w-16 h-7 text-center font-mono text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary mx-auto block"
                    />
                  </td>
                  <td className="p-2.5 text-center">
                    <input
                      type="number"
                      step={0.5}
                      min={0}
                      value={t.topicScore}
                      onChange={(e) =>
                        handleUpdateField(t.id, "topicScore", Number(e.target.value))
                      }
                      className="w-14 h-7 text-center font-mono font-bold text-xs rounded-control border border-border bg-background text-foreground focus:ring-1 focus:ring-primary mx-auto block"
                    />
                  </td>
                  <td className="p-2.5 text-center">
                    {topics.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-destructive mx-auto"
                        onClick={() => handleDeleteTopic(t.id)}
                        title="Xóa chủ đề này"
                      >
                        <Trash2 className="size-3" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-border bg-muted/40 font-bold text-xs">
                <td colSpan={2} className="p-2.5 text-right font-semibold">
                  TỔNG CỘNG:
                </td>
                <td className="p-2.5 text-center font-mono text-blue-600 dark:text-blue-400">
                  {totals.remember} câu
                </td>
                <td className="p-2.5 text-center font-mono text-emerald-600 dark:text-emerald-400">
                  {totals.understand} câu
                </td>
                <td className="p-2.5 text-center font-mono text-amber-600 dark:text-amber-400">
                  {totals.apply} câu
                </td>
                <td className="p-2.5 text-center font-mono text-purple-600 dark:text-purple-400">
                  {totals.analyze} câu
                </td>
                <td
                  className={`p-2.5 text-center font-mono ${totals.totalScore === 10 ? "text-success" : "text-amber-500"}`}
                >
                  {totals.totalScore} đ
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Export Result Banner */}
      {lastResponse && (
        <div className="p-3 rounded-surface bg-success/10 border border-success/30 flex items-center justify-between text-xs animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-4 text-success shrink-0" />
            <div>
              <span className="font-semibold text-foreground">
                Đã kết xuất thành công tệp bảng tính Excel (.xlsx) chuẩn khảo thí!
              </span>
              <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                {String(lastResponse.result.file_name)} • {courseName} ({courseCode}) • 4 Cấp độ
                Bloom
              </p>
            </div>
          </div>

          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs bg-success/20 border-success/40 text-success hover:bg-success/30"
            onClick={handleDownloadExcel}
          >
            <Download className="size-3 mr-1" />
            <span>Tải Bảng Tính (.xlsx)</span>
          </Button>
        </div>
      )}
    </div>
  );
};

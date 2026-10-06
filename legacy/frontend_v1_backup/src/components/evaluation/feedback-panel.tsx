import { useQuery } from "@tanstack/react-query";
import { ThumbsDown, ThumbsUp, TrendingUp } from "lucide-react";
import type React from "react";
import { conversationsApi } from "../../services/conversations-api";
import { EmptyState } from "../admin/empty-state";
import { KpiMetric } from "../admin/kpi-metric";
import { Badge } from "../ui/badge";
import { Card, CardContent } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";

export const FeedbackPanel: React.FC = () => {
  const { data: stats } = useQuery({
    queryKey: ["feedback-stats"],
    queryFn: () => conversationsApi.getFeedbackStats(),
  });

  const { data: trend } = useQuery({
    queryKey: ["feedback-trend"],
    queryFn: () => conversationsApi.getFeedbackTrend(14),
  });

  const { data: downSamples = [] } = useQuery({
    queryKey: ["feedback-samples", "down"],
    queryFn: () => conversationsApi.getFeedbackSamples("down", 20),
  });

  const upRate = stats ? Math.round(stats.up_rate * 1000) / 10 : 0;
  const points = trend?.points ?? [];
  const maxCount = Math.max(1, ...points.map((p) => p.up + p.down));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <KpiMetric
          label="Tỷ lệ hài lòng (up)"
          value={stats ? `${upRate}%` : "—"}
          helper={stats ? `${stats.up}/${stats.total} votes` : "Chưa có vote nào"}
          icon={ThumbsUp}
        />
        <KpiMetric
          label="Vote down cần đối soát"
          value={stats ? `${stats.down}` : "—"}
          helper="Ưu tiên đọc các mẫu mới nhất bên dưới"
          icon={ThumbsDown}
        />
        <KpiMetric
          label="Xu hướng 14 ngày"
          value={points.length > 0 ? `${points.length} ngày có vote` : "—"}
          helper="Phát hiện drift khi down tăng đột biến"
          icon={TrendingUp}
        />
      </div>

      <Card>
        <CardContent className="p-4 space-y-2">
          <h4 className="text-sm font-semibold text-foreground">Vote theo ngày</h4>
          {points.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Chưa có dữ liệu vote. Khuyến khích người dùng bấm 👍/👎 dưới mỗi câu trả lời.
            </p>
          ) : (
            <div className="space-y-1.5">
              {points.map((p) => (
                <div key={p.date} className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-muted-foreground w-24 shrink-0">{p.date}</span>
                  <div className="flex-1 h-4 rounded-micro bg-muted overflow-hidden flex">
                    <div
                      className="h-full bg-success"
                      style={{ width: `${((p.up / maxCount) * 100).toFixed(1)}%` }}
                    />
                    <div
                      className="h-full bg-destructive"
                      style={{ width: `${((p.down / maxCount) * 100).toFixed(1)}%` }}
                    />
                  </div>
                  <span className="font-mono w-20 text-right shrink-0">
                    <span className="text-success">{p.up} up</span>
                    {" / "}
                    <span className="text-destructive">{p.down} down</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="rounded-surface border border-border bg-card overflow-hidden">
        <div className="p-4 pb-2">
          <h4 className="text-sm font-semibold text-foreground">
            Vote down mới nhất (cần đối soát)
          </h4>
        </div>
        {downSamples.length === 0 ? (
          <EmptyState
            icon={ThumbsUp}
            title="Chưa có vote down"
            description="Mọi câu trả lời được đánh giá đều hài lòng hoặc chưa có lượt vote nào."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Trợ Lý</TableHead>
                <TableHead>Câu Hỏi</TableHead>
                <TableHead>Trích Đoạn Trả Lời</TableHead>
                <TableHead>Thời Gian</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {downSamples.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {s.assistant_code}
                    </Badge>
                  </TableCell>
                  <TableCell
                    className="text-xs max-w-xs truncate"
                    title={s.question_excerpt || undefined}
                  >
                    {s.question_excerpt || "—"}
                  </TableCell>
                  <TableCell
                    className="text-xs text-muted-foreground max-w-sm truncate"
                    title={s.answer_excerpt || undefined}
                  >
                    {s.answer_excerpt || "—"}
                  </TableCell>
                  <TableCell className="text-[11px] font-mono text-muted-foreground">
                    {new Date(s.created_at).toLocaleString("vi-VN")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
};

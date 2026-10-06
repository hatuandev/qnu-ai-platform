import {
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Sparkles,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

export interface QuestionnaireOption {
  key: "A" | "B" | "C" | "D";
  text: string;
}

export interface QuestionnaireCardProps {
  questionNumber?: number;
  bloomLevel?: "Nhận biết" | "Thông hiểu" | "Vận dụng" | "Vận dụng cao";
  clo?: string; // Course Learning Outcome e.g., "CLO 2.1"
  question: string;
  options: QuestionnaireOption[];
  correctKey: "A" | "B" | "C" | "D";
  explanation: string;
  citationTitle?: string;
  className?: string;
}

export const QuestionnaireCard: React.FC<QuestionnaireCardProps> = ({
  questionNumber = 1,
  bloomLevel = "Thông hiểu",
  clo,
  question,
  options,
  correctKey,
  explanation,
  citationTitle,
  className,
}) => {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);

  const isAnswered = selectedKey !== null;
  const isCorrect = selectedKey === correctKey;

  const getBloomBadgeVariant = () => {
    switch (bloomLevel) {
      case "Nhận biết":
        return "secondary";
      case "Thông hiểu":
        return "info";
      case "Vận dụng":
        return "success";
      case "Vận dụng cao":
        return "warning";
      default:
        return "outline";
    }
  };

  const handleSelect = (key: string) => {
    if (isAnswered) return;
    setSelectedKey(key);
    setIsExplanationOpen(true);
  };

  return (
    <div
      className={cn(
        "rounded-surface border border-border bg-card p-4 shadow-xs space-y-3.5 transition-all text-sm",
        className
      )}
    >
      {/* Header with Bloom tag & Question number */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center h-6 w-6 rounded-micro bg-primary text-primary-foreground font-bold text-xs">
            Q{questionNumber}
          </span>
          <Badge variant={getBloomBadgeVariant()} className="text-[11px] font-medium">
            Bloom: {bloomLevel}
          </Badge>
          {clo && (
            <Badge variant="outline" className="text-[11px] font-mono text-muted-foreground">
              {clo}
            </Badge>
          )}
        </div>

        {isAnswered && (
          <div className="flex items-center gap-1.5 text-xs font-semibold animate-in fade-in duration-200">
            {isCorrect ? (
              <span className="inline-flex items-center gap-1 text-success bg-success/10 px-2 py-0.5 rounded-micro">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Chính xác!
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-destructive bg-destructive/10 px-2 py-0.5 rounded-micro">
                <XCircle className="h-3.5 w-3.5" />
                Chưa chính xác
              </span>
            )}
          </div>
        )}
      </div>

      {/* Question Content */}
      <p className="font-semibold text-foreground leading-relaxed text-sm">{question}</p>

      {/* Options List */}
      <div className="space-y-2">
        {options.map((option) => {
          const isSelected = selectedKey === option.key;
          const isThisCorrect = option.key === correctKey;

          let optionStyle =
            "bg-muted/40 hover:bg-muted/80 text-foreground border-border/80 hover:border-primary/50";

          if (isAnswered) {
            if (isThisCorrect) {
              optionStyle = "bg-success/10 border-success text-success-foreground font-medium";
            } else if (isSelected && !isCorrect) {
              optionStyle = "bg-destructive/10 border-destructive text-destructive font-medium";
            } else {
              optionStyle = "bg-muted/20 border-border/40 text-muted-foreground opacity-60";
            }
          }

          return (
            <button
              key={option.key}
              type="button"
              disabled={isAnswered}
              onClick={() => handleSelect(option.key)}
              className={cn(
                "w-full text-left p-3 rounded-control border text-xs flex items-start gap-3 transition-all cursor-pointer disabled:cursor-default",
                optionStyle
              )}
            >
              <span
                className={cn(
                  "flex items-center justify-center h-5 w-5 rounded-micro font-bold shrink-0 text-xs",
                  isAnswered && isThisCorrect
                    ? "bg-success text-white"
                    : isAnswered && isSelected && !isCorrect
                      ? "bg-destructive text-white"
                      : "bg-muted text-muted-foreground border border-border"
                )}
              >
                {option.key}
              </span>
              <span className="flex-1 leading-relaxed">{option.text}</span>
            </button>
          );
        })}
      </div>

      {/* Explanation accordion */}
      {isAnswered && (
        <div className="pt-1 border-t border-border/60">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExplanationOpen((prev) => !prev)}
            className="w-full justify-between h-8 text-xs text-muted-foreground hover:text-foreground px-2"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Giải thích chi tiết & Đáp án đối chiếu
            </span>
            {isExplanationOpen ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </Button>

          {isExplanationOpen && (
            <div className="mt-2 p-3.5 rounded-control bg-muted/50 border border-border/80 text-xs leading-relaxed space-y-2 animate-in fade-in duration-200">
              <p className="text-foreground/90">
                <span className="font-semibold text-primary">Đáp án đúng: {correctKey}</span>.{" "}
                {explanation}
              </p>
              {citationTitle && (
                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground pt-1 border-t border-border/40">
                  <Award className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span>Trích dẫn tài liệu: {citationTitle}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Reset button if answered */}
      {isAnswered && (
        <div className="flex justify-end pt-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelectedKey(null);
              setIsExplanationOpen(false);
            }}
            className="text-[11px] h-7 text-muted-foreground hover:text-primary gap-1"
          >
            <HelpCircle className="h-3 w-3" />
            Làm lại câu này
          </Button>
        </div>
      )}
    </div>
  );
};

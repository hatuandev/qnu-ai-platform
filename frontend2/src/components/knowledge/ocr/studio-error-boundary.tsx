import { AlertCircle, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  onReset: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class StudioErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("StudioErrorBoundary caught an error:", error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[500px] p-8 space-y-4 bg-card rounded-lg border border-border">
          <div className="relative flex items-center justify-center size-14 rounded-full bg-destructive/10 text-destructive">
            <AlertCircle className="size-7" />
          </div>
          <div className="text-center space-y-1 max-w-md">
            <h3 className="text-sm font-semibold text-foreground">
              Đã xảy ra lỗi khi hiển thị Studio bóc tách
            </h3>
            <p className="text-xs text-muted-foreground font-mono bg-muted/50 p-2 rounded-sm text-left overflow-auto max-h-24">
              {this.state.error?.message ||
                "Không thể khởi tạo vùng làm việc bóc tách tài liệu."}
            </p>
          </div>
          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                this.props.onReset();
              }}
            >
              Quay lại danh sách tài liệu
            </Button>
            <Button
              size="sm"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="gap-1.5"
            >
              <RefreshCw className="size-3.5" />
              Thử lại
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

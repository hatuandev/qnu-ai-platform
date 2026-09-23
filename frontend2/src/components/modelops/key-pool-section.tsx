import {
  Check,
  Copy,
  KeyRound,
  Layers,
  Play,
  Plus,
  RefreshCw,
  RotateCw,
  ShieldCheck,
  Trash2,
  Zap,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Switch } from "../../components/ui/switch";
import type { ModelProvider, ProviderApiKey } from "../../services/api-client";

export interface KeyPoolSectionProps {
  selectedProvider: ModelProvider;
  providerKeys: ProviderApiKey[];
  loadingKeys: boolean;
  simulatingRotation: boolean;
  rotationResult: {
    success: boolean;
    rotated: boolean;
    message: string;
  } | null;
  testingKeyId: string | null;
  keyTestFeedback: Record<string, string>;
  isAddingKey?: boolean;
  onSimulateRotation: (providerId: string) => void;
  onSaveNewKey: (payload: {
    name: string;
    api_key: string;
    account_id?: string;
    priority: number;
    quota_limit?: number;
  }) => void;
  onTestSingleKey: (providerId: string, keyId: string) => void;
  onDeleteKey: (providerId: string, keyId: string) => void;
  onToggleKeyActive: (
    providerId: string,
    keyId: string,
    isActive: boolean,
  ) => void;
}

export const KeyPoolSection: React.FC<KeyPoolSectionProps> = ({
  selectedProvider,
  providerKeys,
  loadingKeys,
  simulatingRotation,
  rotationResult,
  testingKeyId,
  keyTestFeedback,
  isAddingKey,
  onSimulateRotation,
  onSaveNewKey,
  onTestSingleKey,
  onDeleteKey,
  onToggleKeyActive,
}) => {
  const [showAddKeyForm, setShowAddKeyForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeySecret, setNewKeySecret] = useState("");
  const [newKeyAccountId, setNewKeyAccountId] = useState("");
  const [newKeyPriority, setNewKeyPriority] = useState(1);
  const [newKeyQuota, setNewKeyQuota] = useState("");
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const handleCopyKey = (keyId: string, text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKeyId(keyId);
      setTimeout(() => setCopiedKeyId(null), 2000);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim() || !newKeySecret.trim()) return;
    onSaveNewKey({
      name: newKeyName.trim(),
      api_key: newKeySecret.trim(),
      account_id: newKeyAccountId.trim() || undefined,
      priority: newKeyPriority,
      quota_limit: newKeyQuota ? Number.parseInt(newKeyQuota, 10) : undefined,
    });
    setNewKeyName("");
    setNewKeySecret("");
    setNewKeyAccountId("");
    setNewKeyPriority(1);
    setNewKeyQuota("");
    setShowAddKeyForm(false);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      {/* LEFT 2 COLS: KEY POOL & ROTATION FAILOVER */}
      <div className="lg:col-span-2 space-y-6">
        <Card className="p-5 space-y-4 border-border">
          {/* Header Key Pool */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                Nhóm Khóa API (Key Pool)
                <Badge variant="outline" className="font-mono text-xs">
                  {providerKeys.length} Keys
                </Badge>
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Hỗ trợ nạp nhiều API key, tự động xoay vòng khi chạm Rate Limit
                429 hoặc cạn Token Quota.
              </p>
            </div>

            {/* Toolbar Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                disabled={simulatingRotation || providerKeys.length <= 1}
                onClick={() => onSimulateRotation(selectedProvider.id)}
                className="h-8 text-xs gap-1.5"
                title="Mô phỏng sự cố 429 trên khóa hiện tại để kiểm tra cơ chế nhảy khóa tự động"
              >
                <Zap
                  className={`h-3.5 w-3.5 text-warning ${simulatingRotation ? "animate-spin" : ""}`}
                />
                <span>
                  {simulatingRotation ? "Đang test..." : "Test 429 Failover"}
                </span>
              </Button>

              <Button
                size="sm"
                onClick={() => setShowAddKeyForm(!showAddKeyForm)}
                className="h-8 text-xs gap-1.5"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>{showAddKeyForm ? "Đóng Form" : "Thêm Khóa"}</span>
              </Button>
            </div>
          </div>

          {/* Simulation Result Alert */}
          {rotationResult && (
            <div
              className={`p-3 rounded-md text-xs flex items-start gap-2.5 ${
                rotationResult.rotated
                  ? "bg-warning/10 text-warning border border-warning/30"
                  : rotationResult.success
                    ? "bg-success/10 text-success border border-success/30"
                    : "bg-destructive/10 text-destructive border border-destructive/30"
              }`}
            >
              <Zap className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold">
                  {rotationResult.rotated
                    ? "⚡ Tự Động Xoay Khóa Thành Công!"
                    : "Thông Báo Xử Lý Token"}
                </strong>
                <span className="leading-relaxed">
                  {rotationResult.message}
                </span>
              </div>
            </div>
          )}

          {/* Add New Key Form Card */}
          {showAddKeyForm && (
            <form
              onSubmit={handleFormSubmit}
              className="p-4 bg-muted/30 rounded-md border border-border space-y-3.5"
            >
              <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <KeyRound className="h-3.5 w-3.5 text-primary" />
                Thêm Khóa API Mới Vào Nhóm
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-foreground block">
                    Tên nhãn gợi nhớ *
                  </span>
                  <Input
                    required
                    placeholder="VD: Key Khoa CNTT 2, Free Tier B..."
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-foreground block">
                    Mã khóa Secret Key *
                  </span>
                  <Input
                    required
                    type="password"
                    placeholder="sk-proj-..."
                    value={newKeySecret}
                    onChange={(e) => setNewKeySecret(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-foreground block">
                    Độ ưu tiên (Priority)
                  </span>
                  <Input
                    type="number"
                    min={1}
                    max={99}
                    value={newKeyPriority}
                    onChange={(e) =>
                      setNewKeyPriority(
                        Number.parseInt(e.target.value, 10) || 1,
                      )
                    }
                    className="h-8 text-xs"
                  />
                  <span className="text-[10px] text-muted-foreground block">
                    1 = Ưu tiên cao nhất (được sử dụng trước)
                  </span>
                </div>

                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-foreground block">
                    Hạn mức Token (Quota Limit)
                  </span>
                  <Input
                    type="number"
                    placeholder="Để trống = Không giới hạn quota"
                    value={newKeyQuota}
                    onChange={(e) => setNewKeyQuota(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              {selectedProvider.type === "cloudflare" && (
                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-foreground block">
                    Cloudflare Account ID (Tài khoản)
                  </span>
                  <Input
                    placeholder={
                      selectedProvider.account_id ||
                      "VD: ab6bf689e472cb9a61358ef23d13330c"
                    }
                    value={newKeyAccountId}
                    onChange={(e) => setNewKeyAccountId(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                  <span className="text-[10px] text-muted-foreground block">
                    Nhập Account ID riêng của tài khoản này (để trống sẽ kế thừa
                    Account ID của Provider:{" "}
                    {selectedProvider.account_id || "chưa gán"})
                  </span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-1 border-t border-border/60">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAddKeyForm(false)}
                  className="h-8 text-xs"
                >
                  Hủy
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={
                    !newKeyName.trim() || !newKeySecret.trim() || isAddingKey
                  }
                  className="h-8 text-xs"
                >
                  {isAddingKey ? "Đang lưu..." : "Lưu Khóa"}
                </Button>
              </div>
            </form>
          )}

          {/* Keys List */}
          <div className="space-y-3">
            {loadingKeys ? (
              <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                <span>Đang tải danh sách khóa API...</span>
              </div>
            ) : providerKeys.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground border border-dashed rounded-md space-y-2">
                <p className="font-medium text-foreground">
                  Chưa có khóa API nào trong nhóm.
                </p>
                <p className="text-muted-foreground">
                  Bấm nút "Thêm Khóa Mới" ở trên để thiết lập khóa đầu tiên cho
                  Provider này.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {providerKeys.map((keyItem: ProviderApiKey) => {
                  const isKeyTesting = testingKeyId === keyItem.id;
                  const testFeedback = keyTestFeedback[keyItem.id];
                  const hasQuota =
                    keyItem.quota_limit && keyItem.quota_limit > 0;
                  const quotaLimit = keyItem.quota_limit || 1;
                  const pct = hasQuota
                    ? Math.min(
                        100,
                        Math.round((keyItem.usage_tokens / quotaLimit) * 100),
                      )
                    : 0;

                  return (
                    <div
                      key={keyItem.id}
                      className={`p-3.5 rounded-md border transition-all space-y-2.5 ${
                        keyItem.status === "rate_limited"
                          ? "bg-warning/5 border-warning/40"
                          : keyItem.is_active
                            ? "bg-card border-border hover:border-border/80"
                            : "bg-muted/20 border-dashed opacity-60"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        {/* Key Identity */}
                        <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
                          <span
                            className="font-mono text-[11px] font-bold px-1.5 py-0.5 rounded bg-muted border border-border text-foreground"
                            title="Độ ưu tiên sử dụng"
                          >
                            #{keyItem.priority}
                          </span>
                          <span className="font-semibold text-xs text-foreground">
                            {keyItem.name}
                          </span>
                          <div className="flex items-center gap-1.5 bg-muted/60 px-2 py-0.5 rounded border border-border/70">
                            <code className="text-xs font-mono font-medium text-foreground tracking-wide select-all">
                              {keyItem.api_key_masked}
                            </code>
                            <button
                              type="button"
                              onClick={() =>
                                handleCopyKey(
                                  keyItem.id,
                                  keyItem.api_key_masked,
                                )
                              }
                              className="p-0.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                              title="Sao chép mã khóa"
                            >
                              {copiedKeyId === keyItem.id ? (
                                <Check className="h-3 w-3 text-success" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </button>
                          </div>

                          {keyItem.account_id && (
                            <span
                              className="text-[11px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 flex items-center gap-1"
                              title={`Tài khoản Cloudflare Account ID: ${keyItem.account_id}`}
                            >
                              <span className="text-[9px] uppercase tracking-wider text-muted-foreground font-sans font-semibold">
                                Acc:
                              </span>
                              {keyItem.account_id.length > 14
                                ? `${keyItem.account_id.slice(0, 6)}...${keyItem.account_id.slice(-4)}`
                                : keyItem.account_id}
                            </span>
                          )}
                        </div>

                        {/* Status Badge & Actions */}
                        <div className="flex items-center gap-2 shrink-0">
                          {keyItem.status === "rate_limited" ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] bg-warning/10 text-warning border-warning/30 flex items-center gap-1"
                            >
                              <RotateCw className="h-2.5 w-2.5 animate-spin" />
                              <span>Cooldown 429</span>
                            </Badge>
                          ) : keyItem.status === "exhausted" ? (
                            <Badge
                              variant="destructive"
                              className="text-[10px]"
                            >
                              Hết Quota
                            </Badge>
                          ) : keyItem.is_active ? (
                            <Badge variant="success" className="text-[10px]">
                              Sẵn Sàng
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px]">
                              Đã Tắt
                            </Badge>
                          )}

                          <Switch
                            checked={keyItem.is_active}
                            onCheckedChange={(checked) =>
                              onToggleKeyActive(
                                selectedProvider.id,
                                keyItem.id,
                                checked,
                              )
                            }
                            aria-label={`Bật hoặc tắt khóa ${keyItem.name}`}
                          />
                        </div>
                      </div>

                      {/* Usage & Quota Bar */}
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>
                          Đã dùng:{" "}
                          <strong className="text-foreground font-mono">
                            {keyItem.usage_tokens.toLocaleString()}
                          </strong>{" "}
                          {hasQuota
                            ? `/ ${keyItem.quota_limit?.toLocaleString()} tokens (${pct}%)`
                            : "tokens (không giới hạn)"}
                        </span>
                        {keyItem.last_used_at && (
                          <span className="text-[10px]">
                            Lần dùng cuối:{" "}
                            {new Date(keyItem.last_used_at).toLocaleTimeString(
                              "vi-VN",
                            )}
                          </span>
                        )}
                      </div>

                      {hasQuota && (
                        <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              pct > 90
                                ? "bg-destructive"
                                : pct > 70
                                  ? "bg-warning"
                                  : "bg-primary"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      )}

                      {/* Test Feedback Banner */}
                      {testFeedback && (
                        <div className="text-[11px] text-primary p-2 bg-primary/5 rounded border border-primary/20">
                          {testFeedback}
                        </div>
                      )}

                      {/* Action Toolbar */}
                      <div className="flex items-center justify-between border-t border-border/50 pt-2 text-xs">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isKeyTesting}
                          onClick={() =>
                            onTestSingleKey(selectedProvider.id, keyItem.id)
                          }
                          className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                        >
                          <Play className="h-3 w-3 text-primary" />
                          <span>
                            {isKeyTesting
                              ? "Đang kiểm tra..."
                              : "Test Khóa Này"}
                          </span>
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (
                              window.confirm(
                                `Xóa khóa '${keyItem.name}' khỏi nhóm?`,
                              )
                            ) {
                              onDeleteKey(selectedProvider.id, keyItem.id);
                            }
                          }}
                          className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive gap-1"
                          title="Xóa khóa khỏi nhóm"
                        >
                          <Trash2 className="h-3 w-3" />
                          <span>Xóa</span>
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Card>

        {/* Resilience Policy Info Card */}
        <Card className="p-5 space-y-3 bg-muted/10 border-border/70">
          <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Cơ Chế Điều Phối JIT Key Failover & Fallback
          </h4>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Khi thực hiện suy luận LLM, Gateway sẽ tự động chọn khóa khả dụng có
            độ ưu tiên cao nhất (#1). Nếu khóa đó gặp lỗi{" "}
            <code className="text-warning">HTTP 429 Too Many Requests</code>{" "}
            hoặc chạm hạn ngạch token, hệ thống lập tức chuyển sang khóa dự
            phòng kế tiếp và đưa khóa cũ vào trạng thái Cooldown trong 60 giây
            mà không làm gián đoạn trải nghiệm người dùng.
          </p>
        </Card>
      </div>

      {/* RIGHT 1 COL: SPECIFICATIONS */}
      <div className="space-y-6">
        <Card className="p-5 space-y-3 border-border">
          <h3 className="text-sm font-bold text-foreground">
            Thông Số Kỹ Thuật
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">ID:</span>
              <span className="text-foreground truncate max-w-[150px]">
                {selectedProvider.id}
              </span>
            </div>
            {selectedProvider.type === "cloudflare" && (
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Account ID:</span>
                <span className="text-foreground truncate max-w-[150px] font-mono">
                  {selectedProvider.account_id || "(Chưa cấu hình)"}
                </span>
              </div>
            )}
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Giao thức:</span>
              <span className="text-foreground uppercase">
                {selectedProvider.type}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Trạng thái:</span>
              <span
                className={
                  selectedProvider.is_active
                    ? "text-success"
                    : "text-muted-foreground"
                }
              >
                {selectedProvider.is_active
                  ? "Kích Hoạt (Active)"
                  : "Tạm Ngừng"}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Tổng Keys:</span>
              <span className="text-foreground font-bold">
                {providerKeys.length}
              </span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

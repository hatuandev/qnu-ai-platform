import { Check, Code2, Copy, ExternalLink, KeyRound, Plus, Sparkles, Trash2 } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";

interface ApiKeyItem {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used: string;
  status: "active" | "revoked";
}

const INITIAL_KEYS: ApiKeyItem[] = [
  {
    id: "key_01",
    name: "Cổng Tuyển Sinh Web Widget (tuyensinh.qnu.edu.vn)",
    prefix: "qnu_live_7a9f...81c2",
    created_at: "2026-09-01",
    last_used: "Vừa xong",
    status: "active",
  },
  {
    id: "key_02",
    name: "Hệ Thống Đào Tạo Tín Chỉ (daotao.qnu.edu.vn)",
    prefix: "qnu_live_3b1d...45e0",
    created_at: "2026-09-05",
    last_used: "2 giờ trước",
    status: "active",
  },
];

export const DeveloperPage: React.FC = () => {
  const [keys, setKeys] = useState<ApiKeyItem[]>(INITIAL_KEYS);
  const [selectedLang, setSelectedLang] = useState<string>("curl");
  const [copied, setCopied] = useState<boolean>(false);

  const handleRevoke = (id: string) => {
    setKeys((prev) => prev.map((k) => (k.id === id ? { ...k, status: "revoked" as const } : k)));
  };

  const handleCreateKey = () => {
    const newKey: ApiKeyItem = {
      id: `key_${Date.now()}`,
      name: `Khóa Tích Hợp Mới #${keys.length + 1}`,
      prefix: `qnu_live_${Math.random().toString(36).substring(2, 6)}...${Math.random().toString(36).substring(2, 6)}`,
      created_at: new Date().toISOString().split("T")[0],
      last_used: "Chưa sử dụng",
      status: "active",
    };
    setKeys((prev) => [...prev, newKey]);
  };

  const codeSnippets: Record<string, string> = {
    curl: `# 1. Hỏi đáp với Trợ lý Tuyển sinh QNU (SSE Token Streaming)
curl -X POST "http://localhost:8001/platform/v1alpha1/assistants/admissions/chat" \\
  -H "Authorization: Bearer qnu_live_YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Điểm chuẩn ngành Công nghệ thông tin năm 2024?",
    "stream": true
  }'`,

    python: `import requests

url = "http://localhost:8001/platform/v1alpha1/assistants/admissions/chat"
headers = {
    "Authorization": "Bearer qnu_live_YOUR_API_KEY",
    "Content-Type": "application/json"
}
payload = {
    "message": "Học phí và chỉ tiêu ngành Sư phạm Toán năm 2025?",
    "stream": False
}

response = requests.post(url, json=payload, headers=headers)
data = response.json()
print("Câu trả lời:", data["answer"])
print("Minh chứng:", data.get("citations", []))`,

    typescript: `// Gọi Trợ lý AI QNU từ ứng dụng Node.js / React
const res = await fetch("http://localhost:8001/platform/v1alpha1/assistants/regulations/chat", {
  method: "POST",
  headers: {
    "Authorization": "Bearer qnu_live_YOUR_API_KEY",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    message: "Số tín chỉ tối thiểu cần đăng ký trong một học kỳ?",
    stream: false,
  }),
});

const data = await res.json();
console.log(data.answer);`,
  };

  const activeSnippet = codeSnippets[selectedLang];

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(activeSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Cổng Developer & Tích Hợp REST API
            <Badge variant="outline" className="font-mono text-xs">
              OpenAPI 3.1
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Quản lý khóa truy cập API Keys, tài liệu Swagger và mã nguồn tích hợp vào các hệ thống
            vệ tinh của ĐH Quy Nhơn.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="http://localhost:8001/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control border border-border bg-card hover:bg-muted text-xs font-semibold text-primary transition-colors"
          >
            <span>Tài Liệu Swagger API</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <Button size="sm" onClick={handleCreateKey} className="h-8 text-xs gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            <span>Tạo Khóa API Mới</span>
          </Button>
        </div>
      </div>

      {/* API Keys Table */}
      <Card className="p-4 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-primary" />
            <h2 className="text-xs font-bold text-foreground uppercase tracking-wider">
              Danh Sách Khóa Truy Cập Đang Hoạt Động
            </h2>
          </div>
          <span className="text-[11px] text-muted-foreground">
            Bảo mật AES-256 mã hóa per-tenant
          </span>
        </div>

        <div className="rounded-surface border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tên Định Danh Khóa</TableHead>
                <TableHead>Tiền Tố Bí Mật (Prefix)</TableHead>
                <TableHead>Ngày Tạo</TableHead>
                <TableHead>Truy Cập Gần Nhất</TableHead>
                <TableHead>Trạng Thái</TableHead>
                <TableHead className="text-right">Thao Tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((k) => (
                <TableRow key={k.id}>
                  <TableCell className="font-semibold text-xs text-foreground">{k.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {k.prefix}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {k.created_at}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{k.last_used}</TableCell>
                  <TableCell>
                    {k.status === "active" ? (
                      <Badge variant="success" className="text-[10px]">
                        Active
                      </Badge>
                    ) : (
                      <Badge variant="destructive" className="text-[10px]">
                        Revoked
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {k.status === "active" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRevoke(k.id)}
                        className="h-7 text-xs text-destructive hover:bg-destructive/10 gap-1"
                        title="Thu hồi khóa này"
                      >
                        <Trash2 className="h-3 w-3" />
                        <span>Thu hồi</span>
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Code Snippets Section */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-primary" />
            <h2 className="text-xs font-bold text-foreground uppercase tracking-wider">
              Mã Mẫu Tích Hợp SDK (Integration Quickstart)
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <Tabs value={selectedLang} onValueChange={setSelectedLang}>
              <TabsList className="bg-muted p-0.5 rounded-control h-7">
                <TabsTrigger value="curl" className="text-xs px-2.5 py-0.5 h-6">
                  cURL
                </TabsTrigger>
                <TabsTrigger value="python" className="text-xs px-2.5 py-0.5 h-6">
                  Python
                </TabsTrigger>
                <TabsTrigger value="typescript" className="text-xs px-2.5 py-0.5 h-6">
                  TypeScript
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="h-7 text-xs gap-1 text-primary"
            >
              {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
              <span>{copied ? "Đã sao chép!" : "Sao chép"}</span>
            </Button>
          </div>
        </div>

        <pre className="p-4 rounded-surface bg-muted/90 font-mono text-xs text-foreground overflow-x-auto border border-border leading-relaxed select-text">
          {activeSnippet}
        </pre>
      </Card>

      {/* Architectural Notice */}
      <Card className="p-4 bg-primary/5 border-primary/20 flex items-center gap-3 text-xs">
        <Sparkles className="h-5 w-5 text-primary shrink-0" />
        <span className="text-muted-foreground leading-relaxed">
          Nền tảng tuân thủ chuẩn <strong>RFC 7807 (Problem Details for HTTP APIs)</strong>. Mọi
          phản hồi lỗi nghiệp vụ đều chứa mã `type`, `title`, `detail`, và `correlation_id` phục vụ
          kiểm tra và gỡ lỗi phân tán.
        </span>
      </Card>
    </div>
  );
};

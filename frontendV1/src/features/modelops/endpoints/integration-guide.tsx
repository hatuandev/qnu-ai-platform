import { Check, Code2, Copy, FileCode, Terminal } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { IntegrationConfig } from "@/features/modelops/types";

interface IntegrationGuideProps {
  config?: IntegrationConfig;
  defaultModel?: string;
}

export function IntegrationGuide({
  config,
  defaultModel = "tro-ly-tuyen-sinh",
}: IntegrationGuideProps) {
  const [copiedTab, setCopiedTab] = React.useState<string | null>(null);

  if (!config) {
    return (
      <p className="text-sm text-muted-foreground">
        Chưa có cấu hình endpoint từ server.
      </p>
    );
  }
  const openAiBaseUrl = config.openai_endpoint;

  const curlCode = `# 1. Lấy danh sách trợ lý được cấp phép:
curl -X GET "${openAiBaseUrl}/models" \\
  -H "Authorization: Bearer YOUR_API_KEY"

# 2. Gửi câu hỏi đến trợ lý QNU:
curl -X POST "${openAiBaseUrl}/chat/completions" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${defaultModel}",
    "messages": [
      {"role": "user", "content": "Điểm chuẩn ngành Công nghệ thông tin năm 2025 là bao nhiêu?"}
    ],
    "stream": false
  }'`;

  const pythonCode = `from openai import OpenAI

# Khởi tạo client chuẩn OpenAI trỏ về Gateway QNU AI
client = OpenAI(
    base_url="${openAiBaseUrl}",
    api_key="YOUR_API_KEY",  # Khóa bí mật đã tạo
)

# Gửi câu hỏi đến trợ lý
response = client.chat.completions.create(
    model="${defaultModel}",  # ID trợ lý từ GET /models
    messages=[
        {"role": "user", "content": "Học phí ngành Sư phạm Toán năm 2025?"}
    ],
)

# In câu trả lời
print("Trợ lý trả lời:", response.choices[0].message.content)

# Đọc trích dẫn nguồn bằng chứng qua qnu_extensions (nếu có)
extra = getattr(response, "qnu_extensions", None)
if extra:
    print("\\nDẫn chứng thực tế:")
    for src in extra.get("sources", []):
        print(f"- [Tài liệu {src['document_id']}, Trang {src.get('page_no')}]: {src['text']}")`;

  const tsCode = `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${openAiBaseUrl}",
  apiKey: "YOUR_API_KEY", // Thay bằng khóa bí mật đã tạo
});

async function askAssistant() {
  const completion = await client.chat.completions.create({
    model: "${defaultModel}",
    messages: [
      { role: "user", content: "Quy định đăng ký học phần học kỳ 1 năm học 2025-2026?" },
    ],
  });

  console.log("Câu trả lời:", completion.choices[0].message.content);

  // Truy vết dẫn chứng chính xác từ nguồn tài liệu gốc
  const qnuExt = (completion as any).qnu_extensions;
  if (qnuExt?.sources) {
    console.log("Trích dẫn nguồn:");
    qnuExt.sources.forEach((src: any) => {
      console.log(\`* Trang \${src.page_no} (điểm tương đồng: \${src.score}): \${src.text}\`);
    });
  }
}

askAssistant();`;

  const handleCopyCode = async (code: string, tabName: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedTab(tabName);
      toast.success(`Đã sao chép code mẫu ${tabName}!`);
      setTimeout(() => setCopiedTab(null), 2000);
    } catch {
      toast.error("Không thể sao chép tự động.");
    }
  };

  return (
    <Card className="rounded-xl border border-border bg-card shadow-2xs overflow-hidden">
      <CardHeader className="border-b bg-muted/20 pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="size-4 text-primary" />
            <CardTitle className="text-sm font-semibold">
              Hướng Dẫn Tích Hợp (Mã Mẫu)
            </CardTitle>
          </div>
          <span className="text-[11px] text-muted-foreground">
            Sử dụng thư viện OpenAI SDK chuẩn cho mọi ngôn ngữ
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5">
        <p className="mb-4 text-sm text-muted-foreground">
          API hiện hỗ trợ một tin nhắn user mỗi yêu cầu, stream=false. Lấy ID
          trợ lý từ GET /models. History, system message, tools và tham số
          sampling chưa được hỗ trợ; API sẽ trả lỗi 400. Persona, giới hạn đầu
          ra và chính sách RAG dùng cấu hình của trợ lý.
        </p>
        <Tabs defaultValue="curl" className="w-full">
          <div className="flex items-center justify-between border-b pb-1 mb-3">
            <TabsList className="bg-transparent p-0 h-8 gap-2">
              <TabsTrigger value="curl" className="text-xs h-7 gap-1.5 px-3">
                <Terminal className="size-3.5" />
                <span>cURL</span>
              </TabsTrigger>
              <TabsTrigger value="python" className="text-xs h-7 gap-1.5 px-3">
                <FileCode className="size-3.5" />
                <span>Python</span>
              </TabsTrigger>
              <TabsTrigger value="ts" className="text-xs h-7 gap-1.5 px-3">
                <FileCode className="size-3.5" />
                <span>TypeScript</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="curl" className="space-y-2 mt-0">
            <div className="relative">
              <pre className="rounded-lg bg-muted/80 p-3.5 font-mono text-[11px] leading-relaxed overflow-x-auto text-foreground border border-border">
                {curlCode}
              </pre>
              <Button
                size="sm"
                variant="secondary"
                className="absolute top-2.5 right-2.5 h-6 gap-1 px-2 text-[10px]"
                onClick={() => handleCopyCode(curlCode, "cURL")}
              >
                {copiedTab === "cURL" ? (
                  <Check className="size-3 text-emerald-500" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>{copiedTab === "cURL" ? "Đã chép" : "Sao chép"}</span>
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="python" className="space-y-2 mt-0">
            <div className="relative">
              <pre className="rounded-lg bg-muted/80 p-3.5 font-mono text-[11px] leading-relaxed overflow-x-auto text-foreground border border-border">
                {pythonCode}
              </pre>
              <Button
                size="sm"
                variant="secondary"
                className="absolute top-2.5 right-2.5 h-6 gap-1 px-2 text-[10px]"
                onClick={() => handleCopyCode(pythonCode, "Python")}
              >
                {copiedTab === "Python" ? (
                  <Check className="size-3 text-emerald-500" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>{copiedTab === "Python" ? "Đã chép" : "Sao chép"}</span>
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="ts" className="space-y-2 mt-0">
            <div className="relative">
              <pre className="rounded-lg bg-muted/80 p-3.5 font-mono text-[11px] leading-relaxed overflow-x-auto text-foreground border border-border">
                {tsCode}
              </pre>
              <Button
                size="sm"
                variant="secondary"
                className="absolute top-2.5 right-2.5 h-6 gap-1 px-2 text-[10px]"
                onClick={() => handleCopyCode(tsCode, "TypeScript")}
              >
                {copiedTab === "TypeScript" ? (
                  <Check className="size-3 text-emerald-500" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>
                  {copiedTab === "TypeScript" ? "Đã chép" : "Sao chép"}
                </span>
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

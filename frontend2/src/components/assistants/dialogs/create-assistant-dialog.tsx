import {
  Award,
  BookOpen,
  Bot,
  GraduationCap,
  Loader2,
  Plus,
  ShieldCheck,
  Sparkles,
  Wand2,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Field } from "@/components/admin/field";
import { CATEGORY_OPTIONS } from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  type AssistantInput,
  createAssistant,
  generateAssistantSpec,
} from "@/services/assistants-api";
import type { AssistantItem } from "@/types/assistants";

interface CreateAssistantDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (assistant: AssistantItem) => void;
  collections?: { id: string; name: string }[];
  workflows?: { id: string; name: string }[];
}

const PRESET_TEMPLATES = [
  {
    code: "ast_admissions_demo",
    name: "Tư Vấn Tuyển Sinh QNU 2026",
    category: "admissions",
    icon: GraduationCap,
    description:
      "Trợ lý tư vấn chỉ tiêu, đề án tuyển sinh, phương thức xét tuyển và điểm chuẩn các ngành ĐH Quy Nhơn.",
    system_prompt:
      "Bạn là Trợ lý Tư vấn Tuyển sinh chính thức của Trường Đại học Quy Nhơn. Hãy giải đáp chính xác, văn phong chuẩn mực và chỉ sử dụng thông tin từ Đề án tuyển sinh đã ban hành.",
    sample_questions: [
      "Trường tuyển sinh những phương thức nào trong năm 2026?",
      "Điểm chuẩn ngành Công nghệ thông tin năm ngoái là bao nhiêu?",
    ],
  },
  {
    code: "ast_regulations_demo",
    name: "Quy Chế & Học Vụ Sinh Viên",
    category: "academic",
    icon: ShieldCheck,
    description:
      "Giải đáp các quy định đào tạo tín chỉ, đăng ký học phần, miễn giảm học phí và học bổng khuyến khích.",
    system_prompt:
      "Bạn là Trợ lý Học vụ Trường Đại học Quy Nhơn. Nhiệm vụ của bạn là giải đáp điều lệ đào tạo tín chỉ, học bổng và quy chế sinh viên căn cứ chính xác vào các văn bản ban hành.",
    sample_questions: [
      "Điều kiện để được xét học bổng khuyến khích học tập là gì?",
      "Quy định cảnh báo học vụ và buộc thôi học được tính như thế nào?",
    ],
  },
  {
    code: "ast_admin_nd30_demo",
    name: "Soạn Thảo Văn Bản Nghị Định 30",
    category: "administration",
    icon: BookOpen,
    description:
      "Trợ lý hỗ trợ cán bộ, giảng viên soạn thảo Tờ trình, Thông báo, Quyết định chuẩn thể thức Nghị định 30/2020/NĐ-CP.",
    system_prompt:
      "Bạn là Chuyên gia Soạn thảo Văn bản hành chính theo Nghị định 30/2020/NĐ-CP của Trường Đại học Quy Nhơn. Hãy xuất đúng cấu trúc Quốc hiệu, Tiêu ngữ, Số ký hiệu, Thẩm quyền ban hành.",
    sample_questions: [
      "Soạn thảo dự thảo Thông báo nghỉ lễ 30/4 cho sinh viên toàn trường.",
      "Mẫu Tờ trình xin phê duyệt kinh phí hoạt động nghiên cứu khoa học.",
    ],
  },
  {
    code: "ast_exam_bloom_demo",
    name: "Khảo Thí & Ngân Hàng Đề Thi Bloom",
    category: "examination",
    icon: Award,
    description:
      "Hỗ trợ phân bổ ma trận đề thi và soạn thảo câu hỏi trắc nghiệm theo 6 bậc thang tư duy Bloom.",
    system_prompt:
      "Bạn là Trợ lý Khảo thí & Đảm bảo Chất lượng Giáo dục Trường Đại học Quy Nhơn. Hãy xây dựng câu hỏi bám sát chuẩn đầu ra môn học và thang đo năng lực Bloom.",
    sample_questions: [
      "Tạo ma trận đề thi kết thúc học phần gồm 40 câu trắc nghiệm cho môn Cơ sở dữ liệu.",
    ],
  },
];

export function CreateAssistantDialog({
  open,
  onOpenChange,
  onSuccess,
  collections = [],
  workflows = [],
}: CreateAssistantDialogProps) {
  const [mode, setMode] = React.useState<"template" | "ai" | "manual">(
    "template",
  );
  const [code, setCode] = React.useState("");
  const [name, setName] = React.useState("");
  const [category, setCategory] = React.useState("admissions");
  const [description, setDescription] = React.useState("");
  const [systemPrompt, setSystemPrompt] = React.useState("");
  const [collectionId, setCollectionId] = React.useState("");
  const [workflowId, setWorkflowId] = React.useState("");
  const [aiBrief, setAiBrief] = React.useState("");
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const applyTemplate = React.useCallback(
    (tpl: (typeof PRESET_TEMPLATES)[0]) => {
      setCode(tpl.code);
      setName(tpl.name);
      setCategory(tpl.category);
      setDescription(tpl.description);
      setSystemPrompt(tpl.system_prompt);
    },
    [],
  );

  // Reset form when dialog opens
  React.useEffect(() => {
    if (open) {
      const defaultColl = collections[0]?.id || "col_tuyensinh_2026";
      const defaultWf = workflows[0]?.id || "wf_qnu_admissions_rag";
      setCollectionId(defaultColl);
      setWorkflowId(defaultWf);
      applyTemplate(PRESET_TEMPLATES[0]);
    }
  }, [open, collections, workflows, applyTemplate]);

  const handleAiGenerate = async () => {
    if (!aiBrief.trim()) {
      toast.error("Vui lòng nhập mô tả sơ bộ về trợ lý AI cần tạo.");
      return;
    }
    setIsGenerating(true);
    try {
      const spec = await generateAssistantSpec(aiBrief);
      const generatedCode = `ast_${spec.category || "ai"}_${Date.now().toString(36).slice(-4)}`;
      setCode(generatedCode);
      setName(spec.name);
      setCategory(spec.category || "admissions");
      setDescription(spec.description);
      setSystemPrompt(spec.system_prompt);
      if (spec.suggested_workflow_id) setWorkflowId(spec.suggested_workflow_id);
      toast.success("AI đã phác thảo cấu hình trợ lý thành công!");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Phác thảo cấu hình thất bại.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim() || !name.trim()) {
      toast.error("Vui lòng điền đầy đủ Mã định danh và Tên trợ lý.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: AssistantInput = {
        code: code.trim(),
        name: name.trim(),
        description: description.trim(),
        category,
        system_prompt:
          systemPrompt.trim() ||
          `Bạn là Trợ lý AI ${name.trim()} của Trường Đại học Quy Nhơn.`,
        workflow_id: workflowId || workflows[0]?.id || "wf_qnu_admissions_rag",
        collection_id:
          collectionId || collections[0]?.id || "col_tuyensinh_2026",
        is_active: true,
        tenant_id: "qnu_default",
        config: {
          sample_questions: [
            `Trợ lý ${name} có thể giúp được gì cho tôi?`,
            "Thông tin quy định mới nhất của trường là gì?",
          ],
          persona_scope: {
            persona: `Trợ lý chính thức Trường Đại học Quy Nhơn chuyên trách ${name}`,
            allowed_topics: [category, "quy định", "thông tin chính thức"],
            out_of_scope_policy:
              "Từ chối lịch sự và hướng dẫn liên hệ văn phòng trường.",
          },
          knowledge_policy: {
            chunking_strategy: "ClauseBasedChunker",
            require_structured_facts: true,
            retrieval_limit: 5,
          },
          model_policy: {
            primary_model: "gpt-4o-mini",
            fallback_model: "gemini-2.5-flash-lite",
            temperature: 0.2,
            max_tokens: 1200,
          },
          guardrails: {
            block_prompt_injection: true,
            mask_pii: true,
            require_grounded_answer: true,
            protect_system_prompt: true,
            no_answer_message:
              "Thông tin này chưa có trong nguồn văn bản chính thức của Trường Đại học Quy Nhơn. Vui lòng liên hệ đơn vị phụ trách.",
          },
          tools: {
            enabled_tools: ["admission_score_lookup", "document_exporter_nd30"],
            human_approval_required: true,
          },
          output_policy: {
            formats: ["markdown", "table"],
            require_citations: true,
            citation_format: "[Tên văn bản, Điều/Khoản, Trang]",
          },
          evaluation_policy: {
            faithfulness_threshold: 0.9,
            answer_relevance_threshold: 0.85,
            context_precision_threshold: 0.8,
          },
        },
      };

      const result = await createAssistant(payload);
      toast.success(`Đã khởi tạo thành công Trợ lý AI “${result.name}”!`);
      onSuccess(result);
      onOpenChange(false);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Khởi tạo trợ lý thất bại.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Plus className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Thêm Trợ Lý AI Mới
              </DialogTitle>
              <DialogDescription className="text-xs">
                Khởi tạo Trợ lý AI chuyên trách theo chuẩn 7 lớp của Trường Đại
                học Quy Nhơn.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Tabs
          value={mode}
          onValueChange={(v) => setMode(v as "template" | "ai" | "manual")}
          className="w-full flex-1 flex flex-col min-h-0"
        >
          <TabsList className="grid grid-cols-3 h-9 w-full mb-3">
            <TabsTrigger value="template" className="text-xs gap-1.5">
              <Bot className="size-3.5" />
              <span>Mẫu QNU</span>
            </TabsTrigger>
            <TabsTrigger value="ai" className="text-xs gap-1.5">
              <Wand2 className="size-3.5" />
              <span>AI phác thảo</span>
            </TabsTrigger>
            <TabsTrigger value="manual" className="text-xs gap-1.5">
              <Sparkles className="size-3.5" />
              <span>Tùy chỉnh</span>
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pr-1 space-y-4">
            <TabsContent value="template" className="mt-0 space-y-3">
              <span className="text-[11px] font-semibold text-muted-foreground block">
                Chọn mẫu trợ lý hạt nhân được cấu hình sẵn:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {PRESET_TEMPLATES.map((tpl) => {
                  const Icon = tpl.icon;
                  const isSelected = code === tpl.code;
                  return (
                    <button
                      type="button"
                      key={tpl.code}
                      onClick={() => applyTemplate(tpl)}
                      className={`text-left p-3 rounded-lg border text-xs transition-all flex flex-col justify-between gap-2 ${
                        isSelected
                          ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                          : "border-border hover:border-primary/40 hover:bg-muted/40"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
                          <Icon className="size-3.5" />
                        </div>
                        <span className="font-semibold text-foreground line-clamp-1">
                          {tpl.name}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground line-clamp-2">
                        {tpl.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </TabsContent>

            <TabsContent value="ai" className="mt-0 space-y-3">
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs space-y-2">
                <div className="flex items-center gap-1.5 font-semibold text-primary">
                  <Sparkles className="size-3.5" />
                  <span>Trình tạo tự động cấu hình Trợ lý AI</span>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  Nhập tóm tắt vai trò hoặc nghiệp vụ của trợ lý, AI sẽ tự động
                  soạn thảo System Prompt, phạm vi chuyên môn và các câu hỏi
                  mẫu.
                </p>
                <Textarea
                  value={aiBrief}
                  onChange={(e) => setAiBrief(e.target.value)}
                  placeholder="Ví dụ: Trợ lý hướng dẫn sinh viên thủ tục xin cấp bảng điểm, chứng nhận tốt nghiệp và xác nhận nghĩa vụ quân sự..."
                  rows={3}
                  className="bg-background text-xs"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs gap-1.5 border-primary/30 text-primary hover:bg-primary/10"
                  onClick={handleAiGenerate}
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Wand2 className="size-3.5" />
                  )}
                  <span>Phác thảo cấu hình</span>
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="manual" className="mt-0">
              <p className="text-xs text-muted-foreground mb-3">
                Nhập thông tin tùy biến để khởi tạo Trợ lý AI từ đầu:
              </p>
            </TabsContent>

            {/* Common Form Fields for All Modes */}
            <form
              id="create-assistant-form"
              onSubmit={handleSubmit}
              className="space-y-3 border-t border-border pt-3"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field
                  label="Mã định danh (Code)"
                  htmlFor="assistant-code"
                  required
                >
                  <Input
                    id="assistant-code"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="ví dụ: ast_hoc_bong_2026"
                    className="font-mono text-xs h-9"
                    required
                  />
                </Field>

                <Field label="Lĩnh vực chuyên môn" htmlFor="assistant-category">
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger
                      id="assistant-category"
                      className="h-9 text-xs"
                    >
                      <SelectValue placeholder="Chọn lĩnh vực" />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORY_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              <Field label="Tên Trợ lý AI" htmlFor="assistant-name" required>
                <Input
                  id="assistant-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="ví dụ: Trợ Lý Học Bổng & Miễn Giảm Học Phí"
                  className="text-xs h-9"
                  required
                />
              </Field>

              <Field label="Mô tả tóm tắt" htmlFor="assistant-desc">
                <Input
                  id="assistant-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Mô tả phạm vi hỗ trợ và đối tượng phục vụ..."
                  className="text-xs h-9"
                />
              </Field>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label="Kho Tri Thức liên kết" htmlFor="assistant-col">
                  <Select value={collectionId} onValueChange={setCollectionId}>
                    <SelectTrigger id="assistant-col" className="h-9 text-xs">
                      <SelectValue placeholder="Chọn kho tri thức" />
                    </SelectTrigger>
                    <SelectContent>
                      {collections.map((col) => (
                        <SelectItem key={col.id} value={col.id}>
                          {col.name} ({col.id})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>

                <Field label="Quy trình DAG" htmlFor="assistant-wf">
                  <Select value={workflowId} onValueChange={setWorkflowId}>
                    <SelectTrigger id="assistant-wf" className="h-9 text-xs">
                      <SelectValue placeholder="Chọn quy trình DAG" />
                    </SelectTrigger>
                    <SelectContent>
                      {workflows.map((wf) => (
                        <SelectItem key={wf.id} value={wf.id}>
                          {wf.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              <Field
                label="Chỉ dẫn cốt lõi (System Prompt)"
                htmlFor="assistant-prompt"
              >
                <Textarea
                  id="assistant-prompt"
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Nhập vai trò, tư cách phát ngôn và nguyên tắc giải đáp..."
                  rows={4}
                  className="text-xs font-mono"
                />
              </Field>
            </form>
          </div>
        </Tabs>

        <DialogFooter className="border-t border-border pt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
            className="h-8 text-xs"
          >
            Hủy
          </Button>
          <Button
            type="submit"
            form="create-assistant-form"
            size="sm"
            disabled={isSubmitting}
            className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {isSubmitting ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Plus className="size-3.5" />
            )}
            <span>Tạo trợ lý</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

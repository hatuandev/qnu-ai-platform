/**
 * QNU AI Platform Typed API Client
 * Connects to FastAPI Backend (/platform/v1alpha1/*) with high-fidelity fallback mock data
 */

const BASE_URL = "/platform/v1alpha1";

export interface BackendHealth {
  status: "ok" | "degraded" | "offline";
  service: string;
  version: string;
  dependencies?: {
    database: string;
    redis: string;
  };
}

export interface AssistantItem {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  workflow_id: string;
  collection_id: string;
  is_active: boolean;
  sample_questions: string[];
}

export interface KnowledgeCollection {
  id: string;
  name: string;
  code: string;
  description: string;
  document_count: number;
  chunk_count: number;
  chunking_strategy: "ClauseBasedChunker" | "SemanticChunker";
  ocr_profile: "PyMuPDF" | "Docling" | "EasyOCR";
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  collection_id: string;
  collection_name: string;
  title: string;
  filename: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  status: "completed" | "processing" | "pending" | "failed";
  ocr_method: string;
  created_at: string;
}

export interface ProviderApiKey {
  id: string;
  name: string;
  api_key_masked: string;
  priority: number;
  is_active: boolean;
  status: "active" | "rate_limited" | "exhausted" | "inactive";
  quota_limit?: number | null;
  usage_tokens: number;
  cooldown_until?: string | null;
  last_used_at?: string | null;
  created_at?: string | null;
}

export interface ProviderPreset {
  code: string;
  name: string;
  category: "cloud" | "local" | "custom";
  icon: string;
  description: string;
  default_base_url?: string | null;
  placeholder_key: string;
  help_text: string;
  requires_account_id?: boolean;
  suggested_models?: string[];
}

export interface ModelProvider {
  id: string;
  name: string;
  code: string;
  type:
    | "openai"
    | "gemini"
    | "claude"
    | "local"
    | "local_vllm"
    | "ollama"
    | "deepseek"
    | "groq"
    | "openrouter"
    | "mistral"
    | "cloudflare"
    | "nvidia"
    | "sentence_transformers"
    | "docling"
    | "custom";
  is_active: boolean;
  circuit_breaker_status: "CLOSED" | "OPEN" | "HALF_OPEN";
  models: string[];
  model_name?: string;
  api_base_url?: string;
  api_key_masked?: string;
  account_id?: string;
  latency_ms: number;
  failure_rate: number;
  priority?: number;
  timeout_seconds?: number;
  keys_count?: number;
  api_keys?: ProviderApiKey[];
}

export interface TokenQuota {
  tenant_id: string;
  total_tokens: number;
  limit_tokens: number;
  usd_cost: number;
  reset_date: string;
  provider_breakdown: {
    openai_tokens: number;
    gemini_tokens: number;
    local_tokens: number;
  };
}

export interface ToolItem {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  requires_approval: boolean;
  status: "ready" | "maintenance";
  usage_count: number;
  endpoint: string;
}

export interface EvaluationMetrics {
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  target_faithfulness: number;
  target_relevance: number;
  target_precision: number;
  total_evaluations: number;
  last_evaluated_at: string;
}

export interface GapInboxItem {
  id: string;
  question: string;
  assistant_code: string;
  assistant_name: string;
  reason: string;
  frequency: number;
  timestamp: string;
  status: "pending" | "resolved";
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: "completed" | "running" | "failed";
  duration_ms: number;
  steps_completed: number;
  total_steps: number;
  started_at: string;
}

// ---------------- Fallback Seed Data ----------------

const MOCK_COLLECTIONS: KnowledgeCollection[] = [
  {
    id: "col_admissions",
    code: "admissions",
    name: "Kho Tri Thức Đề Án Tuyển Sinh",
    description: "Đề án tuyển sinh chính quy, bảng chỉ tiêu, điểm chuẩn và thông tin học phí.",
    document_count: 8,
    chunk_count: 246,
    chunking_strategy: "SemanticChunker",
    ocr_profile: "Docling",
    updated_at: "2026-09-15 08:30",
  },
  {
    id: "col_regulations",
    code: "regulations",
    name: "Kho Quy Chế Đào Tạo & Học Vụ",
    description: "Quy chế tín chỉ, đăng ký học phần, tiêu chuẩn học bổng, chuẩn đầu ra B1.",
    document_count: 14,
    chunk_count: 512,
    chunking_strategy: "ClauseBasedChunker",
    ocr_profile: "PyMuPDF",
    updated_at: "2026-09-14 16:45",
  },
  {
    id: "col_library",
    code: "library",
    name: "Kho Mục Lục & Học Liệu Thư Viện",
    description: "Danh mục sách giáo trình, luận án, kết nối cơ sở dữ liệu Scopus/ScienceDirect.",
    document_count: 32,
    chunk_count: 1040,
    chunking_strategy: "SemanticChunker",
    ocr_profile: "PyMuPDF",
    updated_at: "2026-09-15 11:20",
  },
  {
    id: "col_drafting",
    code: "drafting",
    name: "Kho Thể Thức Văn Bản Nghị Định 30",
    description: "Quy chuẩn trình bày văn bản hành chính, mẫu quyết định, tờ trình của trường.",
    document_count: 6,
    chunk_count: 180,
    chunking_strategy: "ClauseBasedChunker",
    ocr_profile: "Docling",
    updated_at: "2026-09-13 14:10",
  },
  {
    id: "col_question_bank",
    code: "question_bank",
    name: "Kho Ngân Hàng Đề Thi & Đề Cương",
    description: "Đề cương chi tiết học phần, chuẩn đầu ra CLO, ma trận câu hỏi chuẩn Bloom.",
    document_count: 18,
    chunk_count: 620,
    chunking_strategy: "ClauseBasedChunker",
    ocr_profile: "Docling",
    updated_at: "2026-09-15 09:00",
  },
];

const MOCK_DOCUMENTS: KnowledgeDocument[] = [
  {
    id: "doc_01",
    collection_id: "col_admissions",
    collection_name: "Đề Án Tuyển Sinh",
    title: "Đề án Tuyển sinh Đại học Chính quy năm 2025",
    filename: "De_an_Tuyen_sinh_QNU_2025.pdf",
    file_size: 2450000,
    page_count: 48,
    chunk_count: 124,
    status: "completed",
    ocr_method: "Docling Table Parser",
    created_at: "2026-09-12 10:20",
  },
  {
    id: "doc_02",
    collection_id: "col_regulations",
    collection_name: "Quy Chế Đào Tạo",
    title: "Quyết định 1234/QĐ-ĐHQN Ban hành Quy chế Đào tạo Tín chỉ",
    filename: "Quy_che_Dao_tao_Dai_hoc_QNU_Quyet_Dinh_1234.pdf",
    file_size: 4120000,
    page_count: 64,
    chunk_count: 218,
    status: "completed",
    ocr_method: "PyMuPDF Fast",
    created_at: "2026-09-10 14:00",
  },
  {
    id: "doc_03",
    collection_id: "col_regulations",
    collection_name: "Quy Chế Đào Tạo",
    title: "Quy định Chuẩn đầu ra Ngoại ngữ & Tin học 2024",
    filename: "Chuan_Dau_Ra_Ngoai_Ngu_QNU.pdf",
    file_size: 980000,
    page_count: 12,
    chunk_count: 36,
    status: "completed",
    ocr_method: "PyMuPDF Fast",
    created_at: "2026-09-11 09:15",
  },
  {
    id: "doc_04",
    collection_id: "col_drafting",
    collection_name: "Thể Thức Văn Bản",
    title: "Nghị định 30/2020/NĐ-CP của Chính phủ về Công tác văn thư",
    filename: "Nghi_dinh_30_2020_ND_CP_Van_thu.pdf",
    file_size: 1850000,
    page_count: 32,
    chunk_count: 88,
    status: "completed",
    ocr_method: "Docling Table Parser",
    created_at: "2026-09-08 11:30",
  },
  {
    id: "doc_05",
    collection_id: "col_question_bank",
    collection_name: "Ngân Hàng Đề Thi",
    title: "Đề cương Chi tiết Học phần Cơ sở Dữ liệu (IT204)",
    filename: "De_cuong_Co_so_du_lieu_IT204_QNU.pdf",
    file_size: 1420000,
    page_count: 22,
    chunk_count: 64,
    status: "completed",
    ocr_method: "Docling Table Parser",
    created_at: "2026-09-14 15:45",
  },
];

const MOCK_PROVIDERS: ModelProvider[] = [];

const MOCK_QUOTA: TokenQuota = {
  tenant_id: "tenant_qnu",
  total_tokens: 1458200,
  limit_tokens: 10000000,
  usd_cost: 0.4374,
  reset_date: "2026-10-01",
  provider_breakdown: {
    openai_tokens: 820000,
    gemini_tokens: 490000,
    local_tokens: 148200,
  },
};

const MOCK_TOOLS: ToolItem[] = [
  {
    id: "tool_uis",
    code: "uis_admissions_query",
    name: "Cổng Tra Cứu UIS Tuyển Sinh",
    description:
      "Truy vấn điểm chuẩn THPT, học bạ, và chỉ tiêu tuyển sinh theo mã ngành thời gian thực.",
    category: "Đào tạo & UIS",
    requires_approval: false,
    status: "ready",
    usage_count: 1248,
    endpoint: "POST /platform/v1alpha1/tools/uis/query",
  },
  {
    id: "tool_word",
    code: "docx_nd30_exporter",
    name: "Trình Xuất Word (.docx) Chuẩn NĐ 30",
    description:
      "Tự động kết xuất văn bản hành chính theo quy chuẩn lề 20-25-30-15 mm và phông chữ chuẩn.",
    category: "Hành chính & Văn thư",
    requires_approval: true,
    status: "ready",
    usage_count: 382,
    endpoint: "POST /platform/v1alpha1/tools/export/docx",
  },
  {
    id: "tool_excel",
    code: "xlsx_bloom_matrix_exporter",
    name: "Trình Xuất Excel (.xlsx) Ma Trận Bloom",
    description:
      "Xuất ngân hàng câu hỏi trắc nghiệm 4 mức độ nhận thức vào tệp bảng tính theo mẫu Khảo thí.",
    category: "Khảo thí & ĐBCL",
    requires_approval: false,
    status: "ready",
    usage_count: 516,
    endpoint: "POST /platform/v1alpha1/tools/export/xlsx",
  },
];

const MOCK_EVALUATION: EvaluationMetrics = {
  faithfulness: 0.942,
  answer_relevance: 0.895,
  context_precision: 0.884,
  target_faithfulness: 0.9,
  target_relevance: 0.85,
  target_precision: 0.8,
  total_evaluations: 1250,
  last_evaluated_at: "2026-09-15 14:00",
};

const MOCK_GAP_INBOX: GapInboxItem[] = [
  {
    id: "gap_01",
    question: "Trường có ký túc xá cho sinh viên học văn bằng hai buổi tối không?",
    assistant_code: "admissions",
    assistant_name: "Trợ lý Tuyển sinh",
    reason: "Không tìm thấy quy định cụ thể về đối tượng văn bằng hai trong Đề án KTX.",
    frequency: 8,
    timestamp: "2026-09-15 10:15",
    status: "pending",
  },
  {
    id: "gap_02",
    question: "Chứng chỉ Aptis ESOL có được miễn học phần tiếng Anh chuyên ngành không?",
    assistant_code: "regulations",
    assistant_name: "Trợ lý Quy chế",
    reason: "Bảng quy đổi chứng chỉ mới cập nhật theo quyết định bổ sung chưa được nạp vào RAG.",
    frequency: 14,
    timestamp: "2026-09-14 16:20",
    status: "pending",
  },
  {
    id: "gap_03",
    question: "Phòng tự học tầng 2 thư viện có mở cửa qua đêm vào tuần thi không?",
    assistant_code: "library",
    assistant_name: "Trợ lý Thư viện",
    reason: "Nội quy thư viện chỉ ghi thời gian đến 21h00, chưa có thông báo đặc thù kỳ thi.",
    frequency: 5,
    timestamp: "2026-09-13 18:40",
    status: "pending",
  },
];

const MOCK_RUNS: WorkflowRun[] = [
  {
    id: "run_8819",
    workflow_id: "admissions-assistant",
    workflow_name: "Luồng Trợ lý Tuyển sinh QNU",
    status: "completed",
    duration_ms: 385,
    steps_completed: 4,
    total_steps: 4,
    started_at: "2026-09-15 19:42:10",
  },
  {
    id: "run_8818",
    workflow_id: "regulations-assistant",
    workflow_name: "Luồng Trợ lý Quy chế Học vụ",
    status: "completed",
    duration_ms: 412,
    steps_completed: 4,
    total_steps: 4,
    started_at: "2026-09-15 19:40:05",
  },
  {
    id: "run_8817",
    workflow_id: "drafting-assistant",
    workflow_name: "Luồng Soạn thảo NĐ 30",
    status: "completed",
    duration_ms: 1250,
    steps_completed: 3,
    total_steps: 3,
    started_at: "2026-09-15 19:35:12",
  },
  {
    id: "run_8816",
    workflow_id: "question-bank-assistant",
    workflow_name: "Luồng Ngân hàng Câu hỏi Bloom",
    status: "completed",
    duration_ms: 540,
    steps_completed: 3,
    total_steps: 3,
    started_at: "2026-09-15 19:28:44",
  },
];

// ---------------- API Methods with Smart Fallback ----------------

export const apiClient = {
  async getHealth(): Promise<BackendHealth> {
    try {
      const res = await fetch("/health/live");
      if (res.ok) {
        const data = await res.json();
        return {
          status: "ok",
          service: data.service || "qnu-ai-platform",
          version: data.version || "0.1.0",
          dependencies: { database: "connected", redis: "connected" },
        };
      }
    } catch {
      // Fallback
    }
    return {
      status: "offline",
      service: "qnu-ai-platform (Simulation)",
      version: "0.1.0",
    };
  },

  async getAssistants(): Promise<AssistantItem[]> {
    try {
      const res = await fetch(`${BASE_URL}/assistants`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return [
      {
        id: "ast_01",
        code: "admissions",
        name: "Trợ lý Tuyển sinh QNU",
        description: "Giải đáp chỉ tiêu, điểm chuẩn, phương thức xét tuyển & học phí năm 2025.",
        category: "admissions",
        workflow_id: "admissions-assistant",
        collection_id: "col_admissions",
        is_active: true,
        sample_questions: [
          "Điểm chuẩn ngành Công nghệ thông tin năm 2024?",
          "Học phí ngành Sư phạm Toán và chính sách NĐ 116?",
        ],
      },
      {
        id: "ast_02",
        code: "regulations",
        name: "Trợ lý Quy chế Học vụ",
        description:
          "Tra cứu quy chế tín chỉ, đăng ký học phần, cảnh báo học vụ và chuẩn đầu ra B1.",
        category: "regulations",
        workflow_id: "regulations-assistant",
        collection_id: "col_regulations",
        is_active: true,
        sample_questions: [
          "Số tín chỉ tối thiểu sinh viên cần đăng ký một học kỳ?",
          "Điều kiện nhận học bổng khuyến khích loại Xuất sắc?",
        ],
      },
      {
        id: "ast_03",
        code: "library",
        name: "Trợ lý Thư viện Số QNU",
        description:
          "Tra cứu giáo trình, luận văn tốt nghiệp, cơ sở dữ liệu Scopus & ScienceDirect.",
        category: "library",
        workflow_id: "library-assistant",
        collection_id: "col_library",
        is_active: true,
        sample_questions: [
          "Thời hạn mượn và số lượng sách tối đa của sinh viên?",
          "Cách truy cập cơ sở dữ liệu ScienceDirect từ xa?",
        ],
      },
      {
        id: "ast_04",
        code: "drafting",
        name: "Trợ lý Soạn thảo Văn bản NĐ 30",
        description:
          "Hỗ trợ soạn thảo tờ trình, quyết định, công văn chuẩn thể thức văn bản hành chính.",
        category: "drafting",
        workflow_id: "drafting-assistant",
        collection_id: "col_drafting",
        is_active: true,
        sample_questions: [
          "Quy cách căn lề theo Nghị định 30/2020/NĐ-CP?",
          "Mẫu quyết định khen thưởng sinh viên đạt thành tích?",
        ],
      },
      {
        id: "ast_05",
        code: "question-bank",
        name: "Trợ lý Ngân hàng Đề thi Bloom",
        description:
          "Biên soạn câu hỏi trắc nghiệm theo 4 mức Bloom, ma trận CLO và kết xuất Excel.",
        category: "question_bank",
        workflow_id: "question-bank-assistant",
        collection_id: "col_question_bank",
        is_active: true,
        sample_questions: [
          "Biên soạn 1 câu hỏi trắc nghiệm Bloom mức Vận dụng?",
          "Giải thích ma trận tương quan giữa chuẩn đầu ra CLO và Bloom?",
        ],
      },
    ];
  },

  async getCollections(): Promise<KnowledgeCollection[]> {
    try {
      const res = await fetch(`${BASE_URL}/knowledge/collections`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((item, idx) => {
            const d = item as Record<string, unknown>;
            const code = (d.code as string) || (d.module_code as string) || `col_${idx + 1}`;
            return {
              id: (d.id as string) || `col_${idx + 1}`,
              name: (d.name as string) || "Kho Tri Thức",
              code,
              description: (d.description as string) || "",
              document_count: typeof d.document_count === "number" ? d.document_count : 8,
              chunk_count: typeof d.chunk_count === "number" ? d.chunk_count : 246,
              chunking_strategy:
                (d.chunking_strategy as KnowledgeCollection["chunking_strategy"]) ||
                (code.includes("regulation") || code.includes("draft")
                  ? "ClauseBasedChunker"
                  : "SemanticChunker"),
              ocr_profile:
                (d.ocr_profile as KnowledgeCollection["ocr_profile"]) ||
                (code.includes("regulation") || code.includes("library") ? "PyMuPDF" : "Docling"),
              updated_at: typeof d.updated_at === "string" ? d.updated_at : "2026-09-15 08:30",
            };
          });
        }
      }
    } catch {
      // Fallback
    }
    return MOCK_COLLECTIONS;
  },

  async getDocuments(collectionId?: string): Promise<KnowledgeDocument[]> {
    try {
      const url = collectionId
        ? `${BASE_URL}/knowledge/documents?collection_id=${collectionId}`
        : `${BASE_URL}/knowledge/documents`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((item, idx) => {
            const d = item as Record<string, unknown>;
            const fn =
              (d.filename as string) || (d.file_name as string) || `document_${idx + 1}.pdf`;
            const fs =
              typeof d.file_size === "number"
                ? d.file_size
                : typeof d.file_size_bytes === "number"
                  ? d.file_size_bytes
                  : 1024000;
            return {
              id: (d.id as string) || `doc_${idx + 1}`,
              collection_id: (d.collection_id as string) || "col_admissions",
              collection_name: (d.collection_name as string) || "Kho Tri Thức",
              title: (d.title as string) || fn,
              filename: fn,
              file_size: fs,
              page_count: typeof d.page_count === "number" ? d.page_count : 16,
              chunk_count: typeof d.chunk_count === "number" ? d.chunk_count : 42,
              status: ((d.status as string) || "completed") as
                | "completed"
                | "processing"
                | "pending"
                | "failed",
              ocr_method: (d.ocr_method as string) || "Docling Table Parser",
              created_at: typeof d.created_at === "string" ? d.created_at : "2026-09-15 10:00",
            };
          });
        }
      }
    } catch {
      // Fallback
    }
    if (collectionId) {
      return MOCK_DOCUMENTS.filter((d) => d.collection_id === collectionId);
    }
    return MOCK_DOCUMENTS;
  },

  async getModelProviders(): Promise<ModelProvider[]> {
    try {
      const res = await fetch(`${BASE_URL}/modelops/providers`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          return data.map((item, idx) => {
            const d = item as Record<string, unknown>;
            const rawModels = Array.isArray(d.models)
              ? (d.models as string[])
              : typeof d.model_name === "string" && d.model_name
                ? [d.model_name]
                : [];
            return {
              id: (d.id as string) || `prov_${idx + 1}`,
              name: (d.name as string) || "LLM Provider",
              code: (d.code as string) || (d.provider_type as string) || "llm",
              type: ((d.type as string) ||
                (d.provider_type as string) ||
                "openai") as ModelProvider["type"],
              is_active: typeof d.is_active === "boolean" ? d.is_active : true,
              circuit_breaker_status:
                (d.circuit_breaker_status as "CLOSED" | "OPEN" | "HALF_OPEN") || "CLOSED",
              models: rawModels,
              model_name: (d.model_name as string) || undefined,
              api_base_url: (d.api_base_url as string) || undefined,
              api_key_masked: (d.api_key_masked as string) || undefined,
              account_id: (d.account_id as string) || undefined,
              latency_ms: typeof d.latency_ms === "number" ? d.latency_ms : 120,
              failure_rate: typeof d.failure_rate === "number" ? d.failure_rate : 0.0,
              priority: typeof d.priority === "number" ? d.priority : idx + 1,
              timeout_seconds: typeof d.timeout_seconds === "number" ? d.timeout_seconds : 15,
              keys_count: typeof d.keys_count === "number" ? d.keys_count : 0,
              api_keys: Array.isArray(d.api_keys) ? (d.api_keys as ProviderApiKey[]) : [],
            };
          });
        }
      }
    } catch {
      // Fallback
    }
    return MOCK_PROVIDERS;
  },

  async getProviderPresets(): Promise<ProviderPreset[]> {
    try {
      const res = await fetch(`${BASE_URL}/modelops/presets`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return [];
  },

  async seedDefaultProviders(overwrite = false): Promise<ModelProvider[]> {
    try {
      const res = await fetch(
        `${BASE_URL}/modelops/providers/seed-defaults?overwrite=${overwrite}`,
        {
          method: "POST",
        }
      );
      if (res.ok) {
        return await this.getModelProviders();
      }
    } catch {
      // Fallback
    }
    return await this.getModelProviders();
  },

  async createModelProvider(payload: {
    name: string;
    provider_type: string;
    model_name?: string;
    models?: string[];
    api_base_url?: string;
    api_key?: string;
    account_id?: string;
    priority?: number;
    timeout_seconds?: number;
    is_active?: boolean;
  }): Promise<ModelProvider> {
    const res = await fetch(`${BASE_URL}/modelops/providers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Thêm Provider thất bại");
    return await res.json();
  },

  async updateModelProvider(
    id: string,
    payload: Partial<{
      name: string;
      provider_type: string;
      model_name?: string;
      models?: string[];
      api_base_url?: string;
      api_key?: string;
      account_id?: string;
      priority?: number;
      timeout_seconds?: number;
      is_active?: boolean;
    }>
  ): Promise<ModelProvider> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Cập nhật Provider thất bại");
    return await res.json();
  },

  async deleteModelProvider(id: string): Promise<{ deleted: boolean }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Xóa Provider thất bại");
    return await res.json();
  },

  async toggleModelProvider(id: string): Promise<{ id: string; is_active: boolean }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}/toggle`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Đổi trạng thái Provider thất bại");
    return await res.json();
  },

  async testModelProvider(
    id: string
  ): Promise<{ success: boolean; latency_ms: number; message: string }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}/test`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Kiểm tra kết nối thất bại");
    return await res.json();
  },

  async getProviderKeys(providerId: string): Promise<ProviderApiKey[]> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${providerId}/keys`);
    if (!res.ok) throw new Error("Không thể tải danh sách khóa API");
    return await res.json();
  },

  async addProviderKey(
    providerId: string,
    payload: {
      name: string;
      api_key: string;
      priority?: number;
      quota_limit?: number;
    }
  ): Promise<ProviderApiKey> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${providerId}/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Thêm khóa API vào nhóm thất bại");
    return await res.json();
  },

  async updateProviderKey(
    providerId: string,
    keyId: string,
    payload: Partial<{
      name: string;
      priority: number;
      is_active: boolean;
      status: string;
      quota_limit: number;
    }>
  ): Promise<ProviderApiKey> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Cập nhật khóa API thất bại");
    return await res.json();
  },

  async toggleProviderKey(
    providerId: string,
    keyId: string,
    isActive: boolean
  ): Promise<ProviderApiKey> {
    return this.updateProviderKey(providerId, keyId, { is_active: isActive });
  },

  async deleteProviderKey(
    providerId: string,
    keyId: string
  ): Promise<{ success: boolean; deleted_id: string }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Xóa khóa API thất bại");
    return await res.json();
  },

  async testProviderKey(
    providerId: string,
    keyId: string
  ): Promise<{ success: boolean; latency_ms: number; message: string }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}/test`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Kiểm tra khóa thất bại");
    return await res.json();
  },

  async simulateKeyRotation(
    providerId: string,
    payload: {
      tokens_consumed?: number;
      trigger_rate_limit?: boolean;
      cooldown_seconds?: number;
    }
  ): Promise<{
    success: boolean;
    previous_key_id: string;
    previous_key_name: string;
    next_key_id: string | null;
    next_key_name: string | null;
    tokens_consumed: number;
    rate_limit_triggered: boolean;
    rotated: boolean;
    message: string;
  }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${providerId}/keys/simulate-rotation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Mô phỏng xoay key thất bại");
    }
    return await res.json();
  },

  async getTokenQuotas(): Promise<TokenQuota> {
    try {
      const res = await fetch(`${BASE_URL}/modelops/quotas/tenant_qnu`);
      if (res.ok) {
        const raw = await res.json();
        const d = raw as Record<string, unknown>;
        return {
          tenant_id: (d.tenant_id as string) || "tenant_qnu",
          total_tokens:
            typeof d.tokens_used === "number"
              ? d.tokens_used
              : typeof d.total_tokens === "number"
                ? d.total_tokens
                : 0,
          limit_tokens:
            typeof d.monthly_token_limit === "number"
              ? d.monthly_token_limit
              : typeof d.limit_tokens === "number"
                ? d.limit_tokens
                : 5000000,
          usd_cost:
            typeof d.cost_used_usd === "number"
              ? d.cost_used_usd
              : typeof d.usd_cost === "number"
                ? d.usd_cost
                : 0.0,
          reset_date: (d.reset_date as string) || "2026-10-01",
          provider_breakdown: (d.provider_breakdown as TokenQuota["provider_breakdown"]) || {
            openai_tokens: 0,
            gemini_tokens: 0,
            local_tokens: 0,
          },
        };
      }
    } catch {
      // Fallback
    }
    return MOCK_QUOTA;
  },

  async getTools(): Promise<ToolItem[]> {
    try {
      const res = await fetch(`${BASE_URL}/tools`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((item, idx) => {
            const d = item as Record<string, unknown>;
            const rawName = (d.display_name as string) || (d.name as string) || "Tool";
            const code = (d.code as string) || (d.name as string) || `tool_${idx}`;
            let normalizedCode = code;
            if (code.includes("admission") || code.includes("score")) {
              normalizedCode = "uis_admissions_query";
            } else if (code.includes("document") || code.includes("nd30")) {
              normalizedCode = "docx_nd30_exporter";
            } else if (code.includes("exam") || code.includes("matrix") || code.includes("bloom")) {
              normalizedCode = "xlsx_bloom_matrix";
            }

            return {
              id: (d.id as string) || `tool_${idx + 1}`,
              code: normalizedCode,
              name: rawName,
              description: (d.description as string) || "",
              category: (d.category as string) || "general",
              requires_approval:
                typeof d.requires_approval === "boolean" ? d.requires_approval : false,
              status: ((d.status as string) || (d.is_active ? "ready" : "maintenance")) as
                | "ready"
                | "maintenance",
              usage_count: typeof d.usage_count === "number" ? d.usage_count : 142,
              endpoint: (d.endpoint as string) || `/platform/v1alpha1/tools/${code}`,
            };
          });
        }
      }
    } catch {
      // Fallback
    }
    return MOCK_TOOLS;
  },

  async getEvaluationMetrics(): Promise<EvaluationMetrics> {
    try {
      const res = await fetch(`${BASE_URL}/evaluation/metrics`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return MOCK_EVALUATION;
  },

  async getGapInbox(): Promise<GapInboxItem[]> {
    try {
      const res = await fetch(`${BASE_URL}/evaluation/gap-inbox`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((item, idx) => {
            const d = item as Record<string, unknown>;
            return {
              id: (d.id as string) || `gap_${idx + 1}`,
              question: (d.question as string) || "Câu hỏi cần bổ sung tri thức",
              assistant_code: (d.assistant_code as string) || "admissions",
              assistant_name: (d.assistant_name as string) || "Trợ lý QNU",
              reason: (d.reason as string) || "Chưa có tài liệu tương ứng trong Kho tri thức.",
              frequency: typeof d.frequency === "number" ? d.frequency : 1,
              timestamp: (d.timestamp as string) || "2026-09-15 10:00",
              status: ((d.status as string) || "pending") as "pending" | "resolved",
            };
          });
        }
      }
    } catch {
      // Fallback
    }
    return MOCK_GAP_INBOX;
  },

  async getWorkflowRuns(): Promise<WorkflowRun[]> {
    try {
      const res = await fetch(`${BASE_URL}/workflows/executions`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((item, idx) => {
            const d = item as Record<string, unknown>;
            return {
              id: (d.id as string) || `run_${idx + 1}`,
              workflow_id: (d.workflow_id as string) || "admissions-assistant",
              workflow_name: (d.workflow_name as string) || "Luồng Điều Phối QNU",
              status: ((d.status as string) || "completed") as "completed" | "running" | "failed",
              duration_ms: typeof d.duration_ms === "number" ? d.duration_ms : 450,
              steps_completed: typeof d.steps_completed === "number" ? d.steps_completed : 4,
              total_steps: typeof d.total_steps === "number" ? d.total_steps : 4,
              started_at: (d.started_at as string) || "2026-09-15 19:42:10",
            };
          });
        }
      }
    } catch {
      // Fallback
    }
    return MOCK_RUNS;
  },
};

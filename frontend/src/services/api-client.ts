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

export interface WorkflowExecuteRequest {
  workflow_id: string;
  inputs: Record<string, unknown>;
  tenant_id?: string;
  conversation_id?: string;
}

export interface WorkflowExecuteResponse {
  execution_id: string;
  workflow_id: string;
  status: "completed" | "failed" | "paused_for_approval";
  outputs: Record<string, unknown>;
  executed_nodes: string[];
  latency_ms: number;
  error_message?: string | null;
}

export interface ToolExecuteRequest {
  tool_name: string;
  parameters: Record<string, unknown>;
  tenant_id?: string;
  assistant_code?: string;
  conversation_id?: string;
}

export interface ToolExecuteResponse {
  tool_name: string;
  status: "success" | "failed" | "requires_approval";
  result: Record<string, unknown>;
  latency_ms: number;
  error_message?: string | null;
}

export interface AdministrativeTemplate {
  id: string;
  title: string;
  category: "to_trinh" | "quyet_dinh" | "thong_bao" | "ke_hoach" | "de_thi" | "cong_van";
  document_type: string;
  department: string;
  description: string;
  standard: string;
  placeholders: string[];
  default_title: string;
  default_paragraphs: string[];
  default_signer_title: string;
  default_signer_name: string;
  default_recipients: string[];
}

export interface UisMajorInfo {
  major_code: string;
  major_name: string;
  faculty: string;
  degree: string;
  quota_2025: number;
  benchmark_2024: number;
  benchmark_2023: number;
  benchmark_2022: number;
  combinations: string[];
  tuition_per_credit_vnd: number;
  tuition_per_year_vnd: number;
  career_opportunities: string[];
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

const MOCK_PROVIDERS: ModelProvider[] = [
  {
    id: "prov_docling",
    name: "IBM Docling OCR & Layout Parser",
    code: "docling_parser",
    type: "docling",
    is_active: true,
    circuit_breaker_status: "CLOSED",
    models: ["docling-tableformer-local", "docling-layout-v2"],
    latency_ms: 85,
    failure_rate: 0.0,
    priority: 1,
    timeout_seconds: 60,
    keys_count: 1,
    api_keys: [
      {
        id: "key_docling_01",
        name: "Local Service Key",
        api_key_masked: "local-worker-key-********",
        created_at: "2026-09-01",
        is_active: true,
        priority: 1,
        status: "active",
        usage_tokens: 45000,
      },
    ],
  },
  {
    id: "prov_mistral",
    name: "Mistral AI Vision & OCR",
    code: "mistral_ocr",
    type: "mistral",
    is_active: true,
    circuit_breaker_status: "CLOSED",
    models: ["mistral-ocr-2503", "mistral-large-latest"],
    latency_ms: 120,
    failure_rate: 0.0,
    priority: 2,
    timeout_seconds: 30,
    keys_count: 1,
    api_keys: [
      {
        id: "key_mistral_01",
        name: "Production Cloud Key",
        api_key_masked: "mis-live-key-qnu-********",
        created_at: "2026-09-01",
        is_active: true,
        priority: 1,
        status: "active",
        usage_tokens: 128000,
      },
    ],
  },
  {
    id: "prov_bge",
    name: "BAAI BGE-M3 Embedding & Rerank",
    code: "bge_m3",
    type: "sentence_transformers",
    is_active: true,
    circuit_breaker_status: "CLOSED",
    models: ["bge-m3-vietnamese-1024d", "bge-reranker-large"],
    latency_ms: 45,
    failure_rate: 0.0,
    priority: 1,
    timeout_seconds: 15,
    keys_count: 1,
    api_keys: [
      {
        id: "key_bge_01",
        name: "Qdrant Node Local Key",
        api_key_masked: "qdrant-local-key-********",
        created_at: "2026-09-01",
        is_active: true,
        priority: 1,
        status: "active",
        usage_tokens: 350000,
      },
    ],
  },
  {
    id: "prov_cloudflare",
    name: "Cloudflare Workers AI",
    code: "cf_workers_ai",
    type: "cloudflare",
    is_active: true,
    circuit_breaker_status: "CLOSED",
    models: ["@cf/baai/bge-large-en-v1.5", "@cf/meta/llama-3.1-8b-instruct"],
    latency_ms: 95,
    failure_rate: 0.0,
    priority: 3,
    timeout_seconds: 20,
    keys_count: 1,
    api_keys: [
      {
        id: "key_cf_01",
        name: "Cloudflare API Token",
        api_key_masked: "cf-token-auth-********",
        created_at: "2026-09-01",
        is_active: true,
        priority: 1,
        status: "active",
        usage_tokens: 88000,
      },
    ],
  },
];

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

export const ADMINISTRATIVE_TEMPLATES: AdministrativeTemplate[] = [
  {
    id: "tpl_to_trinh_mua_sam",
    title: "Tờ trình Mua sắm Trang thiết bị Phòng Lab AI",
    category: "to_trinh",
    document_type: "TỜ TRÌNH",
    department: "KHOA CÔNG NGHỆ THÔNG TIN",
    description:
      "Mẫu tờ trình đề xuất kinh phí trang bị máy chủ GPU và thiết bị phục vụ nghiên cứu AI.",
    standard: "Nghị định 30/2020/NĐ-CP",
    placeholders: [
      "{{so_van_ban}}",
      "{{kinh_phi_du_kien}}",
      "{{muc_dich_su_dung}}",
      "{{thoi_gian_trien_khai}}",
    ],
    default_title:
      "Về việc phê duyệt chủ trương nâng cấp hạ tầng phòng thí nghiệm Trí tuệ Nhân tạo",
    default_paragraphs: [
      "Căn cứ Quyết định số 1024/QĐ-ĐHQN về việc phát triển các nhóm nghiên cứu mạnh giai đoạn 2025-2030;",
      "Nhằm đáp ứng nhu cầu đào tạo và thực hành mô hình ngôn ngữ lớn (LLM) và Thị giác máy tính cho sinh viên ngành Trí tuệ Nhân tạo;",
      "Khoa Công nghệ Thông tin kính trình Ban Giám hiệu xem xét, phê duyệt chủ trương mua sắm bổ sung 04 máy chủ tính toán GPU chuyên dụng với dự toán kinh phí dự kiến là 450.000.000 VNĐ.",
      "Kính đề nghị Ban Giám hiệu xem xét, phê duyệt để Khoa có cơ sở triển khai các bước tiếp theo theo quy định hiện hành.",
    ],
    default_signer_title: "TRƯỞNG KHOA",
    default_signer_name: "TS. Lê Văn Tuấn",
    default_recipients: [
      "Ban Giám hiệu",
      "Phòng Kế hoạch - Tài chính",
      "Phòng Quản trị - Thiết bị",
      "Lưu: VT, Khoa CNTT.",
    ],
  },
  {
    id: "tpl_quyet_dinh_khen_thuong",
    title: "Quyết định Khen thưởng Sinh viên Đạt giải NCKH",
    category: "quyet_dinh",
    document_type: "QUYẾT ĐỊNH",
    department: "PHÒNG KHOA HỌC & CÔNG NGHỆ",
    description:
      "Mẫu quyết định trao tặng giấy khen và tiền thưởng cho đề tài NCKH xuất sắc cấp Trường.",
    standard: "Nghị định 30/2020/NĐ-CP",
    placeholders: ["{{so_quyet_dinh}}", "{{danh_sach_sinh_vien}}", "{{muc_tien_thuong}}"],
    default_title:
      "Về việc tặng Giấy khen của Hiệu trưởng cho sinh viên đạt giải Nhất Sinh viên Nghiên cứu Khoa học 2026",
    default_paragraphs: [
      "Căn cứ Điều lệ Trường Đại học ban hành kèm theo Quyết định của Thủ tướng Chính phủ;",
      "Căn cứ Quy chế Nghiên cứu Khoa học sinh viên Trường Đại học Quy Nhơn ban hành ngày 15/09/2023;",
      "Xét đề nghị của Trưởng phòng Khoa học và Công nghệ và Trưởng phòng Công tác Chính trị - Sinh viên;",
      "Điều 1: Tặng Giấy khen của Hiệu trưởng kèm theo tiền thưởng 5.000.000 VNĐ cho nhóm sinh viên ngành Kỹ thuật Phần mềm đạt Giải Nhất Hội thi NCKH cấp Trường năm học 2025-2026 với đề tài 'Xây dựng Nền tảng Hỏi đáp QNU AI Platform'.",
      "Điều 2: Các ông (bà) Trưởng phòng Hành chính - Tổng hợp, Kế hoạch - Tài chính, Khoa học & Công nghệ và các cá nhân có tên tại Điều 1 chịu trách nhiệm thi hành Quyết định này.",
    ],
    default_signer_title: "HIỆU TRƯỞNG",
    default_signer_name: "PGS.TS. Đỗ Ngọc Mỹ",
    default_recipients: ["Như Điều 2", "Đảng ủy, BGH", "Đoàn Thanh niên", "Lưu: VT, KHCN."],
  },
  {
    id: "tpl_thong_bao_hoc_vu",
    title: "Thông báo Kế hoạch Thi & Kiểm tra Học kỳ II",
    category: "thong_bao",
    document_type: "THÔNG BÁO",
    department: "PHÒNG ĐÀO TẠO",
    description:
      "Mẫu thông báo lịch thi kết thúc học phần và quy định phòng thi cho sinh viên toàn trường.",
    standard: "Nghị định 30/2020/NĐ-CP",
    placeholders: ["{{so_thong_bao}}", "{{hoc_ky}}", "{{nam_hoc}}", "{{ngay_bat_dau_thi}}"],
    default_title: "Về việc tổ chức thi kết thúc học phần Học kỳ II năm học 2025-2026",
    default_paragraphs: [
      "Phòng Đào tạo thông báo đến các Khoa chuyên môn và toàn thể sinh viên lịch thi chính thức Học kỳ II năm học 2025-2026 bắt đầu từ ngày 15/06/2026 đến hết ngày 30/06/2026.",
      "Sinh viên có trách nhiệm kiểm tra lịch thi, phòng thi cụ thể trên Cổng thông tin đào tạo (UIS) trước ngày thi 07 ngày.",
      "Thí sinh phải mang theo Thẻ sinh viên hoặc Căn cước công dân khi vào phòng thi; nghiêm cấm mang thiết bị di động, đồng hồ thông minh vào phòng thi.",
    ],
    default_signer_title: "TRƯỞNG PHÒNG ĐÀO TẠO",
    default_signer_name: "TS. Nguyễn Thanh Bình",
    default_recipients: [
      "Các Khoa đào tạo",
      "Các phòng ban chức năng",
      "Sinh viên các khóa",
      "Lưu: ĐT.",
    ],
  },
  {
    id: "tpl_de_thi_bloom",
    title: "Ma trận Phân phối Đề thi Kết thúc Học phần Chuẩn Bloom",
    category: "de_thi",
    document_type: "MA TRẬN ĐỀ THI",
    department: "TRUNG TÂM KHẢO THÍ & ĐẢM BẢO CHẤT LƯỢNG",
    description:
      "Khung ma trận 4 cấp độ tư duy (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao) chuẩn quy chế khảo thí.",
    standard: "Thang đo tư duy Bloom",
    placeholders: ["{{mon_hoc}}", "{{ma_hoc_phan}}", "{{thoi_gian_thi}}", "{{so_chu_de}}"],
    default_title: "Ma trận đề thi kết thúc học phần Lập trình Cơ sở Dữ liệu (IT204)",
    default_paragraphs: [
      "Học phần: Lập trình Cơ sở Dữ liệu — Mã học phần: IT204 — Số tín chỉ: 3 (2 lý thuyết, 1 thực hành).",
      "Hình thức đánh giá: Trắc nghiệm kết hợp Tự luận trên máy tính — Thời gian làm bài: 60 phút.",
      "Tỷ lệ phân bổ cấp độ nhận thức: Nhận biết 30%, Thông hiểu 30%, Vận dụng 25%, Vận dụng cao 15%.",
    ],
    default_signer_title: "TRƯỞNG BỘ MÔN",
    default_signer_name: "TS. Huỳnh Trọng Thìn",
    default_recipients: ["Khoa CNTT", "TT Khảo thí & ĐBCL", "Giảng viên phụ trách", "Lưu: BM."],
  },
  {
    id: "tpl_ke_hoach_hoi_thao",
    title: "Kế hoạch Tổ chức Hội nghị Khoa học Trẻ QNU",
    category: "ke_hoach",
    document_type: "KẾ HOẠCH",
    department: "ĐOÀN THANH NIÊN - HỘI SINH VIÊN",
    description: "Mẫu kế hoạch chi tiết tổ chức sự kiện học thuật, timeline và phân công nhiệm vụ.",
    standard: "Nghị định 30/2020/NĐ-CP",
    placeholders: ["{{ten_hoi_thao}}", "{{dia_diem}}", "{{thanh_phan_tham_du}}"],
    default_title: "Tổ chức Diễn đàn Khoa học Sinh viên và Khởi nghiệp Đổi mới Sáng tạo 2026",
    default_paragraphs: [
      "Mục đích: Khích lệ phong trào nghiên cứu khoa học, đổi mới sáng tạo và chuyển đổi số trong đoàn viên thanh niên.",
      "Thời gian và địa điểm: Ngày 26/03/2026 tại Hội trường A, Trường Đại học Quy Nhơn.",
      "Thành phần tham dự: Toàn thể sinh viên, học viên cao học và các doanh nghiệp đối tác công nghệ trên địa bàn tỉnh Bình Định.",
    ],
    default_signer_title: "BÍ THƯ ĐOÀN TRƯỜNG",
    default_signer_name: "ThS. Cao Kỳ Nam",
    default_recipients: ["Đảng ủy, BGH (để báo cáo)", "Các Liên chi đoàn", "Lưu: ĐTN."],
  },
  {
    id: "tpl_cong_van_thuc_tap",
    title: "Công văn Tiếp nhận Sinh viên Thực tập Doanh nghiệp",
    category: "cong_van",
    document_type: "CÔNG VĂN",
    department: "TRƯỜNG ĐẠI HỌC QUY NHƠN",
    description:
      "Mẫu công văn gửi các công ty công nghệ đề nghị tiếp nhận sinh viên thực tập tốt nghiệp.",
    standard: "Nghị định 30/2020/NĐ-CP",
    placeholders: ["{{ten_doanh_nghiep}}", "{{so_luong_sinh_vien}}", "{{chuyen_nganh}}"],
    default_title:
      "Về việc cử sinh viên ngành Công nghệ Thông tin thực tập tốt nghiệp tại Doanh nghiệp",
    default_paragraphs: [
      "Trường Đại học Quy Nhơn trân trọng gửi lời chào và lời chúc hợp tác thành công đến Ban Giám đốc Quý Công ty.",
      "Thực hiện kế hoạch đào tạo năm học 2025-2026, Nhà trường trân trọng đề nghị Quý Công ty tạo điều kiện tiếp nhận 15 sinh viên khóa 45 ngành Công nghệ Thông tin đến thực tập chuyên môn từ ngày 01/07/2026 đến ngày 31/08/2026.",
      "Nhà trường cam kết sinh viên tuân thủ nghiêm ngặt nội quy lao động và bảo mật thông tin của Quý Doanh nghiệp.",
    ],
    default_signer_title: "KT. HIỆU TRƯỞNG - PHÓ HIỆU TRƯỞNG",
    default_signer_name: "PGS.TS. Nguyễn Đình Hiền",
    default_recipients: [
      "Ban Giám đốc Quý Công ty",
      "Khoa CNTT",
      "Phòng Đào tạo",
      "Lưu: VT, HSSV.",
    ],
  },
];

export const UIS_MAJORS_DATABASE: UisMajorInfo[] = [
  {
    major_code: "7480201",
    major_name: "Công nghệ Thông tin",
    faculty: "Khoa Công nghệ Thông tin",
    degree: "Kỹ sư / Cử nhân (4.5 năm)",
    quota_2025: 220,
    benchmark_2024: 24.5,
    benchmark_2023: 23.5,
    benchmark_2022: 23.0,
    combinations: ["A00", "A01", "D01", "D07"],
    tuition_per_credit_vnd: 450000,
    tuition_per_year_vnd: 16500000,
    career_opportunities: [
      "Kỹ sư Phát triển Phần mềm (Fullstack, Mobile, Cloud)",
      "Chuyên viên Phân tích Hệ thống và Cơ sở Dữ liệu",
      "Kỹ sư Vận hành AI và Trí tuệ Nhân tạo",
    ],
  },
  {
    major_code: "7480103",
    major_name: "Kỹ thuật Phần mềm",
    faculty: "Khoa Công nghệ Thông tin",
    degree: "Kỹ sư (4.5 năm)",
    quota_2025: 140,
    benchmark_2024: 23.0,
    benchmark_2023: 22.0,
    benchmark_2022: 21.5,
    combinations: ["A00", "A01", "D01"],
    tuition_per_credit_vnd: 450000,
    tuition_per_year_vnd: 16500000,
    career_opportunities: [
      "Kỹ sư Thiết kế Kiến trúc Phần mềm (Software Architect)",
      "Kiểm thử tự động & Đảm bảo chất lượng (QA/QC Engineer)",
      "Quản trị Dự án Agile / Scrum Master",
    ],
  },
  {
    major_code: "7480107",
    major_name: "Trí tuệ Nhân tạo & Khoa học Dữ liệu",
    faculty: "Khoa Công nghệ Thông tin & Khoa Toán - Thống kê",
    degree: "Cử nhân Chất lượng Cao (4 năm)",
    quota_2025: 80,
    benchmark_2024: 24.0,
    benchmark_2023: 23.0,
    benchmark_2022: 22.5,
    combinations: ["A00", "A01", "D07"],
    tuition_per_credit_vnd: 520000,
    tuition_per_year_vnd: 18500000,
    career_opportunities: [
      "Kỹ sư Học máy & Học sâu (Machine Learning / Deep Learning)",
      "Chuyên gia Khoa học Dữ liệu (Data Scientist)",
      "Chuyên viên Tinh chỉnh Mô hình AI & RAG Engineer",
    ],
  },
  {
    major_code: "7140209",
    major_name: "Sư phạm Toán học",
    faculty: "Khoa Toán - Thống kê",
    degree: "Cử nhân Sư phạm (4 năm, Miễn 100% học phí & Trợ cấp theo NĐ 116)",
    quota_2025: 100,
    benchmark_2024: 26.5,
    benchmark_2023: 25.5,
    benchmark_2022: 25.0,
    combinations: ["A00", "A01", "D07"],
    tuition_per_credit_vnd: 0,
    tuition_per_year_vnd: 0,
    career_opportunities: [
      "Giáo viên môn Toán tại các Trường THPT chuyên và chuẩn quốc gia",
      "Giảng viên Toán học tại các trường Đại học, Cao đẳng",
      "Chuyên viên Nghiên cứu và Phát triển Chương trình Đào tạo",
    ],
  },
  {
    major_code: "7220201",
    major_name: "Ngôn ngữ Anh",
    faculty: "Khoa Ngoại ngữ",
    degree: "Cử nhân (4 năm)",
    quota_2025: 180,
    benchmark_2024: 22.5,
    benchmark_2023: 21.5,
    benchmark_2022: 21.0,
    combinations: ["D01", "A01", "D14", "D15"],
    tuition_per_credit_vnd: 410000,
    tuition_per_year_vnd: 15000000,
    career_opportunities: [
      "Biên - Phiên dịch viên cao cấp tại các tập đoàn đa quốc gia",
      "Chuyên viên Đối ngoại và Hợp tác Quốc tế",
      "Giáo viên và Chuyên gia Đào tạo Tiếng Anh học thuật (IELTS/TOEIC)",
    ],
  },
  {
    major_code: "7340101",
    major_name: "Quản trị Kinh doanh",
    faculty: "Khoa Kinh tế & Kế toán",
    degree: "Cử nhân (4 năm)",
    quota_2025: 200,
    benchmark_2024: 21.0,
    benchmark_2023: 20.5,
    benchmark_2022: 20.0,
    combinations: ["A00", "A01", "D01", "D07"],
    tuition_per_credit_vnd: 410000,
    tuition_per_year_vnd: 15000000,
    career_opportunities: [
      "Chuyên viên Quản trị Chiến lược và Vận hành Doanh nghiệp",
      "Chuyên viên Marketing & Phát triển Thị trường",
      "Khởi nghiệp và Điều hành Doanh nghiệp Vừa và Nhỏ",
    ],
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

  async uploadDocument(
    collectionId: string,
    file: File,
    title?: string
  ): Promise<KnowledgeDocument> {
    const formData = new FormData();
    formData.append("file", file);
    if (title) {
      formData.append("title", title);
    }
    try {
      const res = await fetch(`${BASE_URL}/knowledge/collections/${collectionId}/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const d = await res.json();
        const fn = (d.filename as string) || (d.file_name as string) || file.name;
        const newDoc: KnowledgeDocument = {
          id: (d.id as string) || `doc_${Date.now()}`,
          collection_id: (d.collection_id as string) || collectionId,
          collection_name: (d.collection_name as string) || "Kho Tri Thức",
          title: (d.title as string) || fn,
          filename: fn,
          file_size: typeof d.file_size === "number" ? d.file_size : file.size,
          page_count:
            typeof d.page_count === "number"
              ? d.page_count
              : Math.max(1, Math.round(file.size / 50000)),
          chunk_count:
            typeof d.chunk_count === "number"
              ? d.chunk_count
              : Math.max(4, Math.round(file.size / 20000)),
          status: "completed",
          ocr_method: (d.ocr_method as string) || "Docling Table Parser",
          created_at: new Date().toISOString().replace("T", " ").substring(0, 16),
        };
        MOCK_DOCUMENTS.unshift(newDoc);
        return newDoc;
      }
    } catch {
      // Fallback
    }

    const cleanTitle = title || file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
    const newDoc: KnowledgeDocument = {
      id: `doc_${Date.now()}`,
      collection_id: collectionId,
      collection_name: "Kho Tri Thức",
      title: cleanTitle,
      filename: file.name,
      file_size: file.size,
      page_count: Math.max(1, Math.round(file.size / 50000)),
      chunk_count: Math.max(4, Math.round(file.size / 20000)),
      status: "completed",
      ocr_method: "Docling Table Parser",
      created_at: new Date().toISOString().replace("T", " ").substring(0, 16),
    };
    MOCK_DOCUMENTS.unshift(newDoc);
    return newDoc;
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

  async executeWorkflow(payload: WorkflowExecuteRequest): Promise<WorkflowExecuteResponse> {
    try {
      const res = await fetch(`${BASE_URL}/workflows/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: payload.workflow_id,
          inputs: payload.inputs,
          tenant_id: payload.tenant_id || "tenant_qnu",
          conversation_id: payload.conversation_id,
        }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Smart Fallback Simulation
    }

    const msg = String(payload.inputs.message || payload.inputs.text || "");
    const lower = msg.toLowerCase();
    const isGreeting =
      lower.includes("chào") ||
      lower.includes("hello") ||
      lower.includes("hi") ||
      lower.includes("xin chào");

    let executed: string[] = [];
    let answerText = "";

    if (payload.workflow_id.includes("admissions")) {
      if (isGreeting) {
        executed = ["chat_input", "condition_route", "greeting_output"];
        answerText =
          "Xin chào bạn! Tôi là Trợ lý Tuyển sinh Trường Đại học Quy Nhơn. Tôi có thể giải đáp thông tin về phương thức xét tuyển, điểm chuẩn 2024, học phí các ngành đào tạo và chỉ tiêu tuyển sinh.";
      } else {
        executed = [
          "chat_input",
          "condition_route",
          "knowledge_answer",
          "citation_guard",
          "final_output",
        ];
        answerText =
          "Dựa trên Đề án Tuyển sinh chính quy năm 2024 của Trường Đại học Quy Nhơn:\n\n- **Ngành Công nghệ thông tin** (Mã ngành: 7480201):\n  - Điểm chuẩn thi THPT: **25.50 điểm** (Tổ hợp A00, A01, D01).\n  - Chỉ tiêu: **150 sinh viên**.\n  - Học phí: Khoảng **18.500.000 VNĐ/năm học**.\n\n*(Trích dẫn: Đề án Tuyển sinh 2024, Phụ lục 01, Trang 14)*";
      }
    } else if (payload.workflow_id.includes("drafting")) {
      executed = [
        "chat_input",
        "condition_route",
        "nd30_formatter",
        "human_approval",
        "final_output",
      ];
      answerText =
        "Đã khởi tạo văn bản Quyết định khen thưởng sinh viên chuẩn thể thức Nghị định 30/2020/NĐ-CP. Bản thảo đã chuyển tới Cán bộ Phòng Hành chính - Tổng hợp để phê duyệt (Human Approval Checkpoint).";
    } else if (payload.workflow_id.includes("regulations")) {
      executed = [
        "chat_input",
        "condition_route",
        "regulations_rag",
        "citation_check",
        "final_output",
      ];
      answerText =
        "Theo Quy chế Đào tạo tín chỉ Trường Đại học Quy Nhơn (Quyết định số 1284/QĐ-ĐHQN):\n\n- Số tín chỉ tối thiểu sinh viên cần đăng ký trong một học kỳ chính là **14 tín chỉ** (đối với sinh viên xếp hạng học lực bình thường) và tối đa là **24 tín chỉ**.";
    } else if (payload.workflow_id.includes("question-bank")) {
      executed = ["chat_input", "condition_route", "bloom_generator", "clo_matrix", "final_output"];
      answerText =
        "Đã biên soạn câu hỏi trắc nghiệm mức Vận dụng (Bloom Level 3) cho học phần Cơ sở Dữ liệu (IT204):\n\n**Câu 1**: Cho lược đồ quan hệ R(A,B,C,D) với tập phụ thuộc hàm F = {A->B, B->C, C->D}. Khóa chính của R là gì?\n- A. A\n- B. B\n- C. C\n- D. AB\n\n*Đáp án đúng*: **A**. Chuẩn đầu ra CLO 2: Vận dụng thuật toán tìm khóa của lược đồ quan hệ.";
    } else {
      executed = ["chat_input", "condition_route", "knowledge_answer", "final_output"];
      answerText = `Phản hồi cho câu hỏi "${msg}": Dữ liệu đã được truy xuất thành công từ cơ sở dữ liệu tri thức QNU.`;
    }

    return {
      execution_id: `exec_${Date.now()}`,
      workflow_id: payload.workflow_id,
      status: "completed",
      outputs: {
        text: answerText,
        message: answerText,
        intent: isGreeting ? "greeting" : "knowledge_query",
      },
      executed_nodes: executed,
      latency_ms: 385,
    };
  },

  /**
   * Lấy danh sách phôi mẫu văn bản hành chính chuẩn QNU.
   */
  async getAdministrativeTemplates(): Promise<AdministrativeTemplate[]> {
    return Promise.resolve(ADMINISTRATIVE_TEMPLATES);
  },

  /**
   * Lấy danh sách thông tin tuyển sinh & điểm chuẩn các ngành từ Cổng UIS.
   */
  async getUisMajors(): Promise<UisMajorInfo[]> {
    return Promise.resolve(UIS_MAJORS_DATABASE);
  },

  /**
   * Thực thi công cụ ngoại vi (Function Calling Execution) với smart offline fallback.
   */
  async executeTool(payload: ToolExecuteRequest): Promise<ToolExecuteResponse> {
    try {
      const res = await fetch("/platform/v1alpha1/tools/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (_err) {
      // Graceful offline fallback
    }

    const startTs = Date.now();
    const tool = payload.tool_name;
    const params = payload.parameters || {};

    if (tool === "export_administrative_document" || tool === "docx_nd30_exporter") {
      const docType = String(params.document_type || "THÔNG BÁO").toUpperCase();
      const title = String(params.title || "Về việc triển khai công tác đào tạo");
      const filename = `${docType.toLowerCase()}_${title.slice(0, 30).trim().replace(/\s+/g, "_")}.docx`;

      return {
        tool_name: tool,
        status: "success",
        result: {
          status: "generated",
          file_name: filename,
          file_path: `D:/DuAnPhanMem/qnu-ai-platform/data/artifacts/${filename}`,
          document_type: docType,
          title,
          standard: "Decree 30/2020/ND-CP",
          margins: { top_mm: 20, bottom_mm: 20, left_mm: 30, right_mm: 15 },
          font: "Times New Roman (12-13pt)",
          signer: {
            title: String(params.signer_title || "HIỆU TRƯỞNG"),
            name: String(params.signer_name || "PGS.TS. Đỗ Ngọc Mỹ"),
          },
          recipients: (params.recipients as string[]) || ["Như Điều 3", "Lưu: VT, ĐT."],
          minio_s3_uri: `s3://knowledge-processed/administrative/${filename}`,
          size_bytes: 28450,
          created_at: new Date().toISOString(),
        },
        latency_ms: Date.now() - startTs + 120,
      };
    }

    if (tool === "export_exam_matrix" || tool === "xlsx_bloom_matrix_exporter") {
      const courseName = String(params.course_name || "Học phần mẫu");
      const courseCode = String(params.course_code || "QNU101");
      const filename = `Exam_Matrix_${courseCode}_Bloom.xlsx`;

      return {
        tool_name: tool,
        status: "success",
        result: {
          status: "generated",
          file_name: filename,
          file_path: `D:/DuAnPhanMem/qnu-ai-platform/data/artifacts/${filename}`,
          course_name: courseName,
          course_code: courseCode,
          duration_minutes: Number(params.exam_duration_minutes || 60),
          bloom_levels: {
            level_1_remember_percent: 30,
            level_2_understand_percent: 30,
            level_3_apply_percent: 25,
            level_4_advanced_apply_percent: 15,
          },
          total_questions: 20,
          max_score: 10.0,
          minio_s3_uri: `s3://knowledge-processed/exams/${filename}`,
          size_bytes: 18720,
          created_at: new Date().toISOString(),
        },
        latency_ms: Date.now() - startTs + 150,
      };
    }

    // Default: UIS admissions query
    const code = String(params.major_code || "7480201");
    const major = UIS_MAJORS_DATABASE.find((m) => m.major_code === code) || UIS_MAJORS_DATABASE[0];

    return {
      tool_name: tool,
      status: "success",
      result: {
        status: "found",
        source: "Cổng Thông Tin Đào Tạo & Tuyển Sinh UIS Trường ĐH Quy Nhơn",
        major_info: major,
        sync_timestamp: new Date().toISOString(),
      },
      latency_ms: Date.now() - startTs + 85,
    };
  },
};

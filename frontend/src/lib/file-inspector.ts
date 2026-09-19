export interface FileRecommendation {
  fileType: "word" | "pdf" | "spreadsheet" | "text" | "unknown";
  fileTypeLabel: string;
  targetOcrKeyword: "docling" | "mistral" | "pymupdf" | "easyocr" | "auto";
  recommendedChunking: "ClauseBasedChunker" | "SemanticChunker";
  title: string;
  reason: string;
  technicalDetails: string;
  badgeText: string;
}

/**
 * Phân tích tệp tin và đề xuất mô hình bóc tách tối ưu dựa trên quy chuẩn QNU AI Core:
 * 1. DOCX/DOC/XLSX: Tệp số hóa có sẵn lớp text & bảng biểu -> Docling TableFormer Local (Bảo toàn 100% bảng & đoạn, không tốn token Cloud OCR).
 * 2. PDF: Fast-path PDF Inspector (10-30ms) cho trang số hóa + Mistral OCR Cloud / Docling cho trang scan ảnh.
 * 3. TXT/MD: Bóc tách native tức thì không qua OCR, SemanticChunker.
 */
export function inspectFileAndRecommend(
  file: File,
  collectionDefaultStrategy?: "ClauseBasedChunker" | "SemanticChunker"
): FileRecommendation {
  const fileName = file.name.toLowerCase();
  const ext = fileName.includes(".") ? fileName.slice(fileName.lastIndexOf(".")) : "";

  // 1. Tệp Microsoft Word (.docx, .doc)
  if (ext === ".docx" || ext === ".doc") {
    return {
      fileType: "word",
      fileTypeLabel: "Microsoft Word (.docx)",
      targetOcrKeyword: "docling",
      recommendedChunking: "ClauseBasedChunker",
      title: "Đề Xuất Tối Ưu Cho Tệp Word (.docx)",
      badgeText: "Tự Động Đề Xuất • Docling",
      reason: "Tệp Word có sẵn cấu trúc đoạn văn bản, tiêu đề và bảng biểu dạng XML nguyên bản.",
      technicalDetails:
        "Sử dụng Docling TableFormer Local để bảo toàn 100% bảng điểm chuẩn, chỉ tiêu và tiêu đề Điều/Khoản mà không tiêu tốn token Cloud OCR.",
    };
  }

  // 2. Tệp Bảng tính Excel / CSV (.xlsx, .xls, .csv)
  if (ext === ".xlsx" || ext === ".xls" || ext === ".csv") {
    return {
      fileType: "spreadsheet",
      fileTypeLabel: "Bảng tính Excel (.xlsx, .csv)",
      targetOcrKeyword: "docling",
      recommendedChunking: "ClauseBasedChunker",
      title: "Đề Xuất Tối Ưu Cho Bảng Tính Số Liệu",
      badgeText: "Bảo Toàn Bảng • Docling",
      reason:
        "Tệp bảng tính chứa ma trận ô số liệu phức tạp (điểm chuẩn, học phí, chỉ tiêu tuyển sinh).",
      technicalDetails:
        "Tự động định tuyến sang Docling TableFormer để chuyển đổi ma trận bảng sang Markdown Table chuẩn, chống lỗi Vision API và giúp LLM tra cứu chính xác 100%.",
    };
  }

  // 3. Tệp Adobe PDF (.pdf)
  if (ext === ".pdf") {
    const hasTableKeywords = [
      "bang",
      "sheet",
      "du_toan",
      "thong_ke",
      "table",
      "diem",
      "chi_tieu",
    ].some((k) => fileName.includes(k));

    if (hasTableKeywords) {
      return {
        fileType: "pdf",
        fileTypeLabel: "Adobe PDF Chứa Bảng Biểu (.pdf)",
        targetOcrKeyword: "docling",
        recommendedChunking: "ClauseBasedChunker",
        title: "Đề Xuất Cho PDF Bảng Biểu & Số Liệu",
        badgeText: "TableFormer • Docling",
        reason: "Phát hiện tệp PDF chứa từ khóa bảng biểu điểm thi/chỉ tiêu đào tạo.",
        technicalDetails:
          "Kích hoạt cơ chế PDF Inspector native siêu tốc (10-30ms) và ưu tiên Docling TableFormer để tái tạo cấu trúc bảng điểm chuẩn đa cột.",
      };
    }

    return {
      fileType: "pdf",
      fileTypeLabel: "Adobe PDF Tiêu Chuẩn (.pdf)",
      targetOcrKeyword: "auto",
      recommendedChunking: collectionDefaultStrategy || "ClauseBasedChunker",
      title: "Đề Xuất Cho Văn Bản Adobe PDF",
      badgeText: "Fast-path + Mistral OCR",
      reason: "Tệp PDF hành chính, quyết định, quy chế học vụ hoặc tài liệu scan con dấu đỏ.",
      technicalDetails:
        "Fast-path trích xuất text kỹ thuật số siêu tốc (10-30ms). Tự động kích hoạt Mistral OCR Cloud (1-2s) nếu là bản scan ảnh, tự động chuyển Local OCR nếu không có key.",
    };
  }

  // 4. Tệp Hình ảnh & Bản Scan (.png, .jpg, .jpeg, .webp, .bmp)
  if ([".png", ".jpg", ".jpeg", ".webp", ".bmp"].includes(ext)) {
    return {
      fileType: "unknown",
      fileTypeLabel: `Ảnh tài liệu / scan (${ext})`,
      targetOcrKeyword: "mistral",
      recommendedChunking: "SemanticChunker",
      title: "Đề Xuất Cho Tệp Hình Ảnh & Bản Scan",
      badgeText: "Vision OCR • Mistral",
      reason: "Tệp hình ảnh chứa văn bản scan, bảng biểu hoặc con dấu trường.",
      technicalDetails:
        "Sử dụng Mistral OCR Cloud Vision API trích xuất ký tự và bảng biểu siêu tốc, tự động chuyển Local OCR nếu không có key.",
    };
  }

  // 5. Tệp Văn bản thuần (.txt, .md)
  if (ext === ".txt" || ext === ".md") {
    return {
      fileType: "text",
      fileTypeLabel: "Văn bản thuần (.txt, .md)",
      targetOcrKeyword: "pymupdf",
      recommendedChunking: "SemanticChunker",
      title: "Đề Xuất Cho Văn Bản Thuần",
      badgeText: "Native Reader",
      reason: "Tệp văn bản thuần túy không có lớp hình ảnh hay bảng tính phức tạp.",
      technicalDetails:
        "Bóc tách trực tiếp siêu tốc 0ms không qua bộ máy OCR, áp dụng SemanticChunker để gom các đoạn văn theo ngữ nghĩa chặt chẽ.",
    };
  }

  // 5. Định dạng khác
  return {
    fileType: "unknown",
    fileTypeLabel: `Tệp định dạng ${ext || "tùy chỉnh"}`,
    targetOcrKeyword: "auto",
    recommendedChunking: collectionDefaultStrategy || "ClauseBasedChunker",
    title: "Cấu Hình Bóc Tách Tự Động",
    badgeText: "Tự Động Nhận Diện",
    reason: "Định dạng tệp tiêu chuẩn cho kho tri thức QNU.",
    technicalDetails: "Áp dụng pipeline phân tích tổng quát bảo toàn văn bản và bảng biểu.",
  };
}

/**
 * Chuẩn hóa tên tệp thành chuỗi không dấu phục vụ so khớp từ khóa
 */
function normalizeForMatching(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/đ/g, "d")
    .replace(/[_-]+/g, " ");
}

/**
 * Tự động nhận diện Loại văn bản (Document Type) từ tên tệp tin đối chiếu với 37 loại trong Taxonomy QNU.
 * Có cơ chế thông minh nhận diện từ khóa tuyển sinh/đào tạo và dự phòng theo ngữ cảnh Kho Tri Thức (Collection Context).
 */
export function detectDocumentTypeFromFilename(
  fileName: string,
  availableCodes?: string[],
  collectionContext?: string | { id?: string; name?: string; code?: string }
): string | undefined {
  const norm = normalizeForMatching(fileName);

  // 1. So khớp từ khóa đặc trưng từ tên tệp (Ưu tiên từ khóa cụ thể trước)
  const patterns: [RegExp, string][] = [
    // Quyết định
    [/(?:quyet\s*dinh|\bqd\b|so\s*\d+.*qd)/, "quyet_dinh"],
    // Quy chế
    [/(?:quy\s*che|\bqc\b)/, "quy_che"],
    // Quy định
    [/(?:quy\s*dinh|\bqdin\b|\bqdinh\b)/, "quy_dinh"],
    // Đề án tuyển sinh / Thông tin tuyển sinh / Đề án đào tạo
    [/(?:de\s*an|tuyen\s*sinh|thong\s*tin\s*tuyen\s*sinh)/, "de_an"],
    // Thông báo / Thông tin công khai / Tin tức
    [/(?:thong\s*bao|\btb\b|thong\s*tin|\btin\s*tuc\b)/, "thong_bao"],
    // Kế hoạch
    [/(?:ke\s*hoach|\bkh\b)/, "ke_hoach"],
    // Phương án
    [/(?:phuong\s*an|\bpa\b)/, "phuong_an"],
    // Tờ trình
    [/(?:to\s*trinh|\bttr\b)/, "to_trinh"],
    // Công văn
    [/(?:cong\s*van|\bcv\b)/, "cong_van"],
    // Báo cáo
    [/(?:bao\s*cao|\bbc\b)/, "bao_cao"],
    // Đề cương chi tiết học phần / Ma trận đề thi / Khảo thí
    [/(?:de\s*cuong|ma\s*tran|de\s*thi|cau\s*hoi|khao\s*thi)/, "de_cuong_mon_hoc"],
    // Giáo trình
    [/(?:giao\s*trinh|\bsach\b)/, "giao_trinh"],
    // Bài giảng
    [/(?:bai\s*giang|\bslide\b)/, "bai_giang"],
    // Đề tài NCKH
    [/(?:de\s*tai|nckh)/, "de_tai_nckh"],
    // Bài báo khoa học
    [/(?:bai\s*bao|scopus|tap\s*chi)/, "bai_bao_khoa_hoc"],
    // Kỷ yếu hội thảo
    [/(?:ky\s*yeu|hoi\s*thao|hoi\s*nghi)/, "ky_yeu_hoi_thao"],
    // Hướng dẫn
    [/(?:huong\s*dan|\bhd\b)/, "huong_dan"],
    // Biên bản
    [/(?:bien\s*ban|\bbb\b)/, "bien_ban"],
    // Giấy mời
    [/(?:giay\s*moi|\bgm\b)/, "giay_moi"],
    // Giấy giới thiệu
    [/(?:giay\s*gioi\s*thieu|\bggt\b)/, "giay_gioi_thieu"],
    // Giấy nghỉ phép
    [/(?:giay\s*nghi\s*phep|\bnghi\s*phep\b)/, "giay_nghi_phep"],
    // Hợp đồng
    [/(?:hop\s*dong|\bhdong\b)/, "hop_dong"],
    // Thỏa thuận / MOU
    [/(?:thoa\s*thuan|\bmou\b|\bmoa\b|ghi\s*nho)/, "thoa_thuan_mou"],
    // Biểu mẫu hành chính
    [/(?:bieu\s*mau|\bbm\b|mau\s*bieu)/, "bieu_mau_hanh_chinh"],
    // Đơn từ sinh viên
    [/(?:don\s*tu|don\s*xin|don\s*de\s*nghi)/, "don_tu_sinh_vien"],
    // Phiếu khảo sát
    [/(?:phieu\s*khao\s*sat|khao\s*sat)/, "phieu_khao_sat"],
    // Nghị quyết
    [/(?:nghi\s*quyet|\bnq\b)/, "nghi_quyet"],
    // Chỉ thị
    [/(?:chi\s*thi)/, "chi_thi"],
    // Chương trình
    [/(?:chuong\s*trinh)/, "chuong_trinh"],
    // Công điện
    [/(?:cong\s*dien)/, "cong_dien"],
  ];

  if (norm.trim()) {
    for (const [regex, candidateCode] of patterns) {
      if (regex.test(norm)) {
        if (
          !availableCodes ||
          availableCodes.length === 0 ||
          availableCodes.includes(candidateCode)
        ) {
          return candidateCode;
        }
      }
    }
  }

  // 2. Dự phòng thông minh theo ngữ cảnh Kho Tri Thức (Collection Context)
  if (collectionContext) {
    const colId =
      typeof collectionContext === "string" ? collectionContext : collectionContext.id || "";
    const colName = typeof collectionContext === "object" ? collectionContext.name || "" : "";
    const colCode = typeof collectionContext === "object" ? collectionContext.code || "" : "";
    const normCol = normalizeForMatching(`${colId} ${colName} ${colCode}`);

    const colDefaults: [RegExp, string][] = [
      [/(?:tuyen\s*sinh|admissions)/, "de_an"],
      [/(?:quy\s*che|hoc\s*vu|regulations)/, "quy_che"],
      [/(?:thu\s*vien|giao\s*trinh|library)/, "giao_trinh"],
      [/(?:khao\s*thi|ngan\s*hang|de\s*thi|question)/, "de_cuong_mon_hoc"],
      [/(?:soan\s*thao|van\s*ban|drafting)/, "cong_van"],
    ];

    for (const [re, code] of colDefaults) {
      if (re.test(normCol)) {
        if (!availableCodes || availableCodes.length === 0 || availableCodes.includes(code)) {
          return code;
        }
      }
    }
  }

  // 3. Không ép fallback giả mạo nếu không có căn cứ từ khóa hoặc ngữ cảnh kho
  return undefined;
}

/**
 * Trích xuất năm hiệu lực / ban hành 4 chữ số từ tên tệp tin (ví dụ: "De_An_2026_Lan2" -> "2026").
 */
export function extractYearFromFilename(fileName: string): string | undefined {
  const match = fileName.match(/(?:^|[^0-9])((?:19|20)\d{2})(?:[^0-9]|$)/);
  return match ? match[1] : undefined;
}

/**
 * Làm sạch và chuyển đổi tên tệp thành tiêu đề văn bản chuẩn tiếng Việt.
 */
export function cleanTitleFromFilename(fileName: string): string {
  const nameWithoutExt = fileName.replace(/\.[^/.]+$/, "");
  return nameWithoutExt.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
}

/**
 * Tính toán mức độ ưu tiên pháp lý chuẩn QNU theo mã loại văn bản hoặc điểm priority (1-10).
 */
export function getPriorityForDocumentType(
  documentTypeCode?: string,
  priorityScore?: number
): {
  scoreText: string;
  label: string;
  multiplierText: string;
  badgeClass: string;
} {
  if (typeof priorityScore === "number" && !Number.isNaN(priorityScore)) {
    const score = Math.max(1, Math.min(10, Math.round(priorityScore)));
    if (score >= 9) {
      return {
        scoreText: `Điểm: ${score}/10`,
        label: "Ưu tiên Cao (Cốt lõi) (x100)",
        multiplierText: "x100",
        badgeClass: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30",
      };
    }
    if (score >= 7) {
      return {
        scoreText: `Điểm: ${score}/10`,
        label: "Ưu tiên Tiêu chuẩn (x50)",
        multiplierText: "x50",
        badgeClass: "bg-blue-500/10 text-blue-600 border-blue-500/30",
      };
    }
    if (score >= 5) {
      return {
        scoreText: `Điểm: ${score}/10`,
        label: "Ưu tiên Cơ bản (x25)",
        multiplierText: "x25",
        badgeClass: "bg-sky-500/10 text-sky-600 border-sky-500/30",
      };
    }
    return {
      scoreText: `Điểm: ${score}/10`,
      label: "Ưu tiên Tham khảo (x10)",
      multiplierText: "x10",
      badgeClass: "bg-amber-500/10 text-amber-600 border-amber-500/30",
    };
  }

  if (!documentTypeCode) {
    return {
      scoreText: "Điểm: 5/10",
      label: "Chưa phân loại (x25)",
      multiplierText: "x25",
      badgeClass: "bg-muted text-muted-foreground border-border",
    };
  }

  const coreTypes = new Set([
    "quy_che",
    "quyet_dinh",
    "nghi_quyet",
    "quy_dinh",
    "cong_dien",
    "giao_trinh",
    "de_cuong_mon_hoc",
    "luat",
    "phap_lenh",
  ]);

  const standardTypes = new Set([
    "chi_thi",
    "thong_cao",
    "de_an",
    "du_an",
    "phuong_an",
    "chuong_trinh",
    "huong_dan",
    "hop_dong",
    "thoa_thuan_mou",
    "ke_hoach",
    "to_trinh",
    "bao_cao",
    "bai_giang",
    "de_tai_nckh",
    "bai_bao_khoa_hoc",
    "ky_yeu_hoi_thao",
    "bieu_mau_hanh_chinh",
    "don_tu_sinh_vien",
    "giay_moi",
  ]);

  if (coreTypes.has(documentTypeCode)) {
    return {
      scoreText: "Điểm: 10/10",
      label: "Ưu tiên Cao (Cốt lõi) (x100)",
      multiplierText: "x100",
      badgeClass: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30",
    };
  }

  if (standardTypes.has(documentTypeCode)) {
    return {
      scoreText: "Điểm: 8/10",
      label: "Ưu tiên Tiêu chuẩn (x50)",
      multiplierText: "x50",
      badgeClass: "bg-blue-500/10 text-blue-600 border-blue-500/30",
    };
  }

  return {
    scoreText: "Điểm: 6/10",
    label: "Ưu tiên Tham khảo (x10)",
    multiplierText: "x10",
    badgeClass: "bg-amber-500/10 text-amber-600 border-amber-500/30",
  };
}

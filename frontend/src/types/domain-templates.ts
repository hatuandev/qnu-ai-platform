/** Domain templates & Reference data interfaces for QNU Administrative & Admissions */

export interface AdministrativeTemplate {
  id: string;
  title: string;
  category:
    | "to_trinh"
    | "quyet_dinh"
    | "thong_bao"
    | "ke_hoach"
    | "de_thi"
    | "cong_van";
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

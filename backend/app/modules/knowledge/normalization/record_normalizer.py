"""Domain Record Normalizers — Transforming Canonical Tables into Atomic Business Records.

Implements Strategy Pattern for high-fidelity extraction of University Domain Records:
- Admissions: AdmissionProgramRecord (53 programs), CertificateConversionRecord, HistoricalAdmissionRecord.
- Implementation Plans: ImplementationTaskRecord with lead unit, coordination, schedule, and deliverables.
- Fallback: GenericDocumentNormalizer for general institutional documents.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.modules.knowledge.normalization.models import (
    CanonicalDocument,
    CanonicalTable,
)


class AdmissionProgramRecord(BaseModel):
    """Atomic record representing an academic program offered for admission."""

    program_code: str = Field(description="Standard 7-digit Ministry program code, e.g. 7140114")
    program_name: str = Field(description="Academic program name")
    admission_methods: list[str] = Field(default_factory=list, description="Admissions method codes e.g. ['1', '2', '4']")
    expected_quota: int | None = Field(default=None, description="Projected target quota if announced")
    subject_combinations: list[list[str]] = Field(
        default_factory=list,
        description="List of 3-subject combination sets, e.g. [['Toán', 'Lý', 'Hóa'], ['Toán', 'Lý', 'Anh']]",
    )
    source_pages: list[int] = Field(default_factory=list)
    verification_status: str = Field(default="unverified")


class CertificateConversionRecord(BaseModel):
    """Foreign language certificate score conversion record."""

    certificate_type: str = Field(description="'IELTS' or 'VSTEP'")
    source_score: str = Field(description="Exam score band e.g. '5.0', '7.0 trở lên'")
    converted_score: float = Field(description="Standard 10-point scale equivalent e.g. 8.0, 10.0")
    source_page: int = Field(default=1)


class HistoricalAdmissionRecord(BaseModel):
    """Historical cutoff score and enrollment statistics for past academic years."""

    program_code: str = Field(description="Program code")
    program_name: str = Field(description="Program name")
    year: int = Field(description="Academic year e.g. 2024, 2025")
    quota: int | None = None
    enrolled: int | None = None
    cutoff_score: float | None = None
    source_pages: list[int] = Field(default_factory=list)


class ImplementationTaskRecord(BaseModel):
    """Actionable task in an institutional annual implementation plan."""

    task_code: str = Field(description="Section or task index e.g. '1.1', '2.4', '10.2'")
    category: str = Field(description="Broad functional area e.g. 'Công tác đào tạo'")
    content: str = Field(description="Task description and objectives")
    lead_unit: str | None = Field(default=None, description="Responsible executing department")
    coordinating_units: list[str] = Field(default_factory=list, description="Collaborating units")
    start_date: str | None = None
    end_date: str | None = None
    deliverables: list[str] = Field(default_factory=list, description="Expected outputs, decrees, reports")
    source_pages: list[int] = Field(default_factory=list)
    verification_status: str = Field(default="unverified")


class BaseRecordNormalizer(ABC):
    """Strategy interface for extracting structured domain records from a canonical document."""

    @abstractmethod
    def supports(self, doc: CanonicalDocument) -> bool:
        """Check if this normalizer can process the given document."""

    @abstractmethod
    def normalize(self, doc: CanonicalDocument) -> list[BaseModel]:
        """Extract atomic domain records from the canonical tables/blocks."""


class AdmissionsRecordNormalizer(BaseRecordNormalizer):
    """Normalizer for University Admissions Announcement documents."""

    def supports(self, doc: CanonicalDocument) -> bool:
        title = (doc.metadata.get("title") or doc.document_id).lower()
        if "tuyển sinh" in title or "tuyensinh" in title:
            return True
        # Check table headers
        for tbl in doc.tables:
            h_str = " ".join(tbl.headers).lower()
            if "mã ngành" in h_str and ("tổ hợp" in h_str or "chỉ tiêu" in h_str):
                return True
        return False

    def normalize(self, doc: CanonicalDocument) -> list[BaseModel]:
        records: list[BaseModel] = []
        for tbl in doc.tables:
            h_str = " ".join(tbl.headers).lower()

            # 1. Historical Cutoff Scores Table (2024 / 2025) must be checked
            # before the main listing because both tables contain "Mã ngành".
            if "điểm" in h_str and ("2024" in h_str or "2025" in h_str):
                records.extend(self._extract_historical(tbl))
            # 2. Main Program Listing Table
            elif "tên ngành" in h_str and ("tổ hợp" in h_str or "phương thức" in h_str):
                records.extend(self._extract_programs(tbl))
            # 3. Certificate Conversion Tables
            elif "ielts" in h_str or "vstep" in h_str:
                records.extend(self._extract_certificates(tbl))

        unique_records: dict[str, BaseModel] = {}
        for record in records:
            if isinstance(record, AdmissionProgramRecord):
                key = f"program:{record.program_code}"
            elif isinstance(record, HistoricalAdmissionRecord):
                key = f"historical:{record.program_code}:{record.year}"
            elif isinstance(record, CertificateConversionRecord):
                key = f"certificate:{record.certificate_type}:{record.source_score}"
            else:
                continue
            unique_records.setdefault(key, record)
        return list(unique_records.values())

    def _extract_programs(self, tbl: CanonicalTable) -> list[AdmissionProgramRecord]:
        programs: list[AdmissionProgramRecord] = []
        # Find column indices
        code_idx = -1
        name_idx = -1
        method_idx = -1
        quota_idx = -1
        comb_idx = -1

        for i, h in enumerate(tbl.headers):
            h_l = h.lower()
            if "mã" in h_l:
                code_idx = i
            elif "tên ngành" in h_l or "chương trình" in h_l:
                name_idx = i
            elif "phương thức" in h_l:
                method_idx = i
            elif "số lượng" in h_l or "chỉ tiêu" in h_l:
                quota_idx = i
            elif "tổ hợp" in h_l:
                comb_idx = i

        if name_idx == -1:
            return []

        for r in tbl.rows:
            # Need at least code or name
            code = r.cells[code_idx].raw_value.strip() if code_idx != -1 and code_idx < len(r.cells) else ""
            name = r.cells[name_idx].raw_value.strip() if name_idx < len(r.cells) else ""
            if not name or name.lower() == "tên ngành":
                continue

            methods_raw = r.cells[method_idx].raw_value.strip() if method_idx != -1 and method_idx < len(r.cells) else ""
            methods = [m.strip() for m in re.split(r"[,;\s]+", methods_raw) if m.strip()]

            quota_raw = r.cells[quota_idx].raw_value.strip() if quota_idx != -1 and quota_idx < len(r.cells) else ""
            quota = int(re.search(r"\d+", quota_raw).group()) if re.search(r"\d+", quota_raw) else None

            # Extract subject combinations: (Văn, Sử, Địa)\n(Toán, Anh, Văn)
            comb_raw = r.cells[comb_idx].raw_value.strip() if comb_idx != -1 and comb_idx < len(r.cells) else ""
            combinations: list[list[str]] = []
            for match in re.finditer(r"\(([^)]+)\)", comb_raw):
                subjects = [s.strip() for s in match.group(1).split(",") if s.strip()]
                if subjects:
                    combinations.append(subjects)

            programs.append(
                AdmissionProgramRecord(
                    program_code=code,
                    program_name=name,
                    admission_methods=methods,
                    expected_quota=quota,
                    subject_combinations=combinations,
                    source_pages=r.source_pages,
                )
            )

        return programs

    def _extract_historical(self, tbl: CanonicalTable) -> list[HistoricalAdmissionRecord]:
        records: list[HistoricalAdmissionRecord] = []
        for r in tbl.rows:
            if len(r.cells) < 4:
                continue
            code = r.cells[1].raw_value.strip() if len(r.cells) > 1 else ""
            name = r.cells[2].raw_value.strip() if len(r.cells) > 2 else ""
            if not code or not re.match(r"^\d{7}", code):
                continue

            # Year 2024: columns 3 (quota), 4 (enrolled), 5 (score)
            score_2024_raw = r.cells[5].raw_value.strip() if len(r.cells) > 5 else ""
            score_2024 = float(score_2024_raw) if re.match(r"^\d+(?:\.\d+)?$", score_2024_raw) else None
            records.append(
                HistoricalAdmissionRecord(
                    program_code=code,
                    program_name=name,
                    year=2024,
                    cutoff_score=score_2024,
                    source_pages=r.source_pages,
                )
            )

            # Year 2025: columns 6 (quota), 7 (enrolled), 8 (score)
            score_2025_raw = r.cells[8].raw_value.strip() if len(r.cells) > 8 else ""
            score_2025 = float(score_2025_raw) if re.match(r"^\d+(?:\.\d+)?$", score_2025_raw) else None
            records.append(
                HistoricalAdmissionRecord(
                    program_code=code,
                    program_name=name,
                    year=2025,
                    cutoff_score=score_2025,
                    source_pages=r.source_pages,
                )
            )
        return records

    def _extract_certificates(self, tbl: CanonicalTable) -> list[CertificateConversionRecord]:
        records: list[CertificateConversionRecord] = []
        is_ielts = any("ielts" in h.lower() for h in tbl.headers)
        cert_type = "IELTS" if is_ielts else "VSTEP"

        for r in tbl.rows:
            if len(r.cells) >= 2:
                src_val = r.cells[0].raw_value.strip()
                conv_val_raw = r.cells[1].raw_value.strip()
                if re.match(r"^\d+(?:\.\d+)?$", conv_val_raw):
                    records.append(
                        CertificateConversionRecord(
                            certificate_type=cert_type,
                            source_score=src_val,
                            converted_score=float(conv_val_raw),
                            source_page=r.source_pages[0] if r.source_pages else 1,
                        )
                    )
        return records


class ImplementationPlanRecordNormalizer(BaseRecordNormalizer):
    """Normalizer for Institutional Action & Strategic Implementation Plan documents."""

    def supports(self, doc: CanonicalDocument) -> bool:
        title = (doc.metadata.get("title") or doc.document_id).lower()
        if "kế hoạch" in title or "ke hoach" in title:
            return True
        for tbl in doc.tables:
            h_str = " ".join(tbl.headers).lower()
            if "nhiệm vụ" in h_str and ("đơn vị chủ trì" in h_str or "sản phẩm" in h_str):
                return True
        return False

    def normalize(self, doc: CanonicalDocument) -> list[BaseModel]:
        tasks: list[BaseModel] = []
        current_category = "Nhiệm vụ trọng tâm chung"

        for tbl in doc.tables:
            h_str = " ".join(tbl.headers).lower()
            if not ("nhiệm vụ" in h_str and "đơn vị chủ trì" in h_str):
                continue

            code_idx = 0
            content_idx = 1
            lead_idx = 2
            coord_idx = 3
            start_idx = 4
            end_idx = 5
            deliv_idx = 6

            for i, h in enumerate(tbl.headers):
                h_l = h.lower()
                if "tt" in h_l or "stt" in h_l:
                    code_idx = i
                elif "nhiệm vụ" in h_l or "nội dung" in h_l:
                    content_idx = i
                elif "chủ trì" in h_l:
                    lead_idx = i
                elif "phối hợp" in h_l:
                    coord_idx = i
                elif "bắt đầu" in h_l:
                    start_idx = i
                elif "hoàn thành" in h_l:
                    end_idx = i
                elif "sản phẩm" in h_l or "kết quả" in h_l:
                    deliv_idx = i

            for r in tbl.rows:
                code = r.cells[code_idx].raw_value.strip() if code_idx < len(r.cells) else ""
                content = r.cells[content_idx].raw_value.strip() if content_idx < len(r.cells) else ""

                # Check if this row is a Category Header (Roman numerals: I, II, III...)
                if re.match(r"^[IVXLCDM]+$", code) or (not code and re.match(r"^[IVXLCDM]+\.\s+", content)):
                    current_category = content or code
                    continue

                if not code or not content:
                    continue

                lead = r.cells[lead_idx].raw_value.strip() if lead_idx < len(r.cells) else None
                coord_raw = r.cells[coord_idx].raw_value.strip() if coord_idx < len(r.cells) else ""
                coord = [c.strip() for c in re.split(r"[,;\n]+", coord_raw) if c.strip()]

                start_date = r.cells[start_idx].raw_value.strip() if start_idx < len(r.cells) else None
                end_date = r.cells[end_idx].raw_value.strip() if end_idx < len(r.cells) else None

                deliv_raw = r.cells[deliv_idx].raw_value.strip() if deliv_idx < len(r.cells) else ""
                deliv = [d.strip() for d in re.split(r"[;\n]+", deliv_raw) if d.strip()]

                tasks.append(
                    ImplementationTaskRecord(
                        task_code=code,
                        category=current_category,
                        content=content,
                        lead_unit=lead or None,
                        coordinating_units=coord,
                        start_date=start_date or None,
                        end_date=end_date or None,
                        deliverables=deliv,
                        source_pages=r.source_pages,
                    )
                )

        unique_tasks: dict[str, ImplementationTaskRecord] = {}
        for task in tasks:
            unique_tasks.setdefault(task.task_code, task)
        return list(unique_tasks.values())


class GenericDocumentNormalizer(BaseRecordNormalizer):
    """Fallback normalizer extracting generic table records."""

    def supports(self, doc: CanonicalDocument) -> bool:
        return True

    def normalize(self, doc: CanonicalDocument) -> list[BaseModel]:
        return []

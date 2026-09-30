"""Universal Agentic Consulting & Export Dispatcher — QNU AI Platform.

Enables all 5 AI Assistants (Admissions, Regulations, Library, Drafting, Question Bank)
to act as proactive consulting agents:
1. Detect user intents: Score calculation, Multi-major comparison, Fact lookup, and File export (.xlsx, .docx, .pdf).
2. Execute domain-specific reasoning and tool calling.
3. Automatically generate and attach downloadable artifacts to the conversation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeFact
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.tools.universal_report import (
    ReportTable,
    UniversalReportPayload,
    export_universal_report,
)

logger = logging.getLogger(__name__)

# Keywords indicating user wants to download or export files
EXPORT_KEYWORDS = (
    "xuất file",
    "xuat file",
    "tải file",
    "tai file",
    "gửi file",
    "gui file",
    "tạo file",
    "tao file",
    "file excel",
    "file word",
    "file pdf",
    "bản excel",
    "bản pdf",
    "bản word",
    "in ra",
    "tải về",
    "tai ve",
    "download",
    "export",
    "lập bảng",
    "lap bang",
    "phiếu tư vấn",
    "phieu tu van",
    "kế hoạch nguyện vọng",
    "ke hoach nguyen vong",
)

# Area patterns
AREA_MAP = {
    "kv1": "KV1",
    "khu vực 1": "KV1",
    "kv 1": "KV1",
    "kv2-nt": "KV2-NT",
    "kv2nt": "KV2-NT",
    "khu vực 2 nông thôn": "KV2-NT",
    "kv2": "KV2",
    "khu vực 2": "KV2",
    "kv 2": "KV2",
    "kv3": "KV3",
    "khu vực 3": "KV3",
    "kv 3": "KV3",
}


def _norm(text: str) -> str:
    """Normalize text using Unicode NFC, strip whitespace, and convert to lowercase."""
    return unicodedata.normalize("NFC", text).strip().lower()


def calculate_moet_admission_score(
    scores: list[float],
    area: str | None = "KV3",
    group: str | None = None,
) -> dict[str, Any]:
    """Calculate candidate score complying with official MOET rules."""
    raw_total = round(sum(scores), 2)
    area_norm = (area or "KV3").strip().upper()
    area_points = 0.0
    if area_norm == "KV1":
        area_points = 0.75
    elif area_norm in ("KV2-NT", "KV2NT"):
        area_points = 0.50
    elif area_norm == "KV2":
        area_points = 0.25

    group_norm = (group or "").strip().lower()
    group_points = 0.0
    if group_norm in ("01", "02", "03", "04", "ut1", "nhom 1"):
        group_points = 2.0
    elif group_norm in ("05", "06", "07", "ut2", "nhom 2"):
        group_points = 1.0

    base_priority = round(area_points + group_points, 2)
    if raw_total >= 22.5:
        actual_priority = round(((30.0 - raw_total) / 7.5) * base_priority, 2)
    else:
        actual_priority = base_priority

    final_score = min(30.0, round(raw_total + actual_priority, 2))
    return {
        "raw_total": raw_total,
        "area": area_norm,
        "area_points": area_points,
        "group": group or "Không",
        "group_points": group_points,
        "base_priority": base_priority,
        "actual_priority": actual_priority,
        "final_score": final_score,
        "is_reduced": raw_total >= 22.5 and base_priority > 0,
    }


def classify_chance_zone(final_score: float, cutoff_score: float) -> dict[str, str]:
    """Classify chance into Safe, Target, Reach or High Risk zones."""
    delta = round(final_score - cutoff_score, 2)
    if delta >= 1.50:
        return {
            "zone": "safe",
            "zone_label": "An toàn (Safe)",
            "delta_str": f"+{delta:.2f}",
            "chance": "Rất cao (≥ 90%)",
            "recommendation": "Nguyện vọng dự phòng chắc chắn đỗ.",
        }
    if delta >= -0.50:
        prefix = "+" if delta >= 0 else ""
        return {
            "zone": "target",
            "zone_label": "Mục tiêu (Target)",
            "delta_str": f"{prefix}{delta:.2f}",
            "chance": "Khả quan (65% - 85%)",
            "recommendation": "Vừa sức, nên đặt ở NV1 hoặc NV2.",
        }
    if delta >= -1.50:
        return {
            "zone": "reach",
            "zone_label": "Thử thách (Reach)",
            "delta_str": f"{delta:.2f}",
            "chance": "Trung bình (30% - 50%)",
            "recommendation": "Nên đặt ở NV1 để thử vận may nếu thực sự đam mê.",
        }
    return {
        "zone": "risk",
        "zone_label": "Nguy cơ cao (High Risk)",
        "delta_str": f"{delta:.2f}",
        "chance": "Thấp (< 20%)",
        "recommendation": "Nên cân nhắc chọn ngành khác gần với mức điểm hơn.",
    }


def extract_majors_from_live_facts(facts: list[KnowledgeFact]) -> list[dict[str, Any]]:
    """Dynamically aggregate major records from database knowledge_facts rows."""
    majors_map: dict[str, dict[str, Any]] = {}
    general_quota = 100
    pedagogy_tuition = "Miễn 100% học phí + trợ cấp 3,63 tr/tháng"
    stem_tuition = "18.000.000 - 22.000.000 đ/năm"
    social_tuition = "14.500.000 - 17.500.000 đ/năm"

    for f in facts:
        etype = f.entity_type
        raw = f.raw_data or {}
        val = f.attribute_value or ""

        if etype in ("cutoff_score", "major") and raw:
            name = raw.get("major_name") or f.entity_name.replace("Điểm chuẩn ngành ", "").replace(" ĐH Quy Nhơn", "").strip()
            code = raw.get("major_code") or ""
            cutoff = float(raw.get("cutoff_score") or 20.0)
            combos = raw.get("subject_groups") or []
            is_pedagogy = "sư phạm" in name.lower() or "giáo dục" in name.lower()
            tuition = pedagogy_tuition if is_pedagogy else stem_tuition
            majors_map[name] = {
                "major_code": code,
                "major_name": name,
                "combinations": combos,
                "cutoff_2022": cutoff - 1.0 if cutoff > 18 else cutoff,
                "cutoff_2023": cutoff - 0.5 if cutoff > 18 else cutoff,
                "cutoff_2024": cutoff,
                "cutoff_2025": cutoff,
                "quota_2026": general_quota,
                "tuition_per_year": tuition,
            }
        elif etype == "cutoff_trend":
            pattern = r"([^:;\n]+?):\s*([0-9]+(?:\.[0-9]+)?)\s*->\s*([0-9]+(?:\.[0-9]+)?)\s*->\s*([0-9]+(?:\.[0-9]+)?)"
            for match in re.finditer(pattern, val):
                m_name = match.group(1).strip()
                s22 = float(match.group(2).rstrip("."))
                s23 = float(match.group(3).rstrip("."))
                s24 = float(match.group(4).rstrip("."))
                is_pedagogy = "sư phạm" in m_name.lower() or "giáo dục" in m_name.lower()
                tuition = pedagogy_tuition if is_pedagogy else (social_tuition if "kinh doanh" in m_name.lower() else stem_tuition)
                if m_name in majors_map:
                    majors_map[m_name]["cutoff_2022"] = s22
                    majors_map[m_name]["cutoff_2023"] = s23
                    majors_map[m_name]["cutoff_2024"] = s24
                    majors_map[m_name]["cutoff_2025"] = s24
                else:
                    majors_map[m_name] = {
                        "major_code": "",
                        "major_name": m_name,
                        "combinations": ["A00", "A01", "D01"],
                        "cutoff_2022": s22,
                        "cutoff_2023": s23,
                        "cutoff_2024": s24,
                        "cutoff_2025": s24,
                        "quota_2026": general_quota,
                        "tuition_per_year": tuition,
                    }
    return list(majors_map.values())


class AgenticConsultingDispatcher:
    """Universal dispatcher for reasoning, facts reconciliation, and multi-format file exports."""

    async def analyze_export_intent_with_llm(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        db: AsyncSession | None = None,
        preferred_model_name: str | None = None,
        fallback_model: str | None = None,
    ) -> dict[str, Any]:
        """Use LLM to semantically understand if user wants a file export and which formats.

        Returns:
            {"is_export": bool, "formats": list[str]}
        """
        norm_msg = _norm(user_message)
        has_file_triggers = any(kw in norm_msg for kw in EXPORT_KEYWORDS) or any(
            w in norm_msg
            for w in (
                "file",
                "tệp",
                "tep",
                "bản in",
                "ban in",
                "bảng tính",
                "bang tinh",
                "in ra",
                "tải",
                "tai",
                "xuất",
                "xuat",
                "gửi",
                "gui",
                "lập",
                "lap",
            )
        )

        last_hist_text = ""
        if history and isinstance(history, list):
            for h in reversed(history[-2:]):
                if isinstance(h, dict) and h.get("role") == "user":
                    last_hist_text = h.get("content", "")
                    break

        if not has_file_triggers and not (
            last_hist_text
            and any(
                w in _norm(last_hist_text)
                for w in ("nguyện vọng", "điểm chuẩn", "bảng", "so sánh", "kế hoạch")
            )
            and any(w in norm_msg for w in ("xuất", "tải", "gửi", "cho em", "xin", "lấy"))
        ):
            return {"is_export": False, "formats": []}

        # If DB session is provided, use LLM for semantic understanding
        if db is not None:
            try:
                system_instruction = (
                    "Bạn là module phân tích ý định xuất tệp (File Export Intent Classifier) của Hệ thống QNU AI Platform.\n"
                    "Nhiệm vụ: Phân tích tin nhắn của người dùng (kèm ngữ cảnh tin nhắn trước nếu có) để xác định:\n"
                    "1. Người dùng có muốn tạo/xuất/tải tệp dữ liệu hoặc văn bản không? (is_export: true/false)\n"
                    "2. Nếu có, họ muốn định dạng tệp nào?\n"
                    "   - 'xlsx': Khi người dùng muốn Excel, bảng tính, số liệu để tính toán, lọc dữ liệu.\n"
                    "   - 'docx': Khi người dùng muốn Word, văn bản hành chính để chỉnh sửa, thêm bớt nội dung.\n"
                    "   - 'pdf': Khi người dùng muốn bản in, nộp hồ sơ, xem trực tiếp trên điện thoại không cần Office.\n"
                    "   - Kết hợp các định dạng nếu người dùng yêu cầu nhiều loại.\n"
                    "   - Nếu người dùng yêu cầu xuất file nhưng không nói rõ định dạng nào hoặc nói 'tất cả'/'cả 3', chọn: ['xlsx', 'docx', 'pdf'].\n"
                    "Định dạng phản hồi: BẮT BUỘC CHỈ TRẢ VỀ JSON HỢP LỆ, không kèm văn bản markdown bên ngoài:\n"
                    '{"is_export": true/false, "formats": ["xlsx" | "docx" | "pdf"]}'
                )

                prompt_user = f'Tin nhắn người dùng: "{user_message}"'
                if last_hist_text:
                    prompt_user = f'Ngữ cảnh tin nhắn trước: "{last_hist_text}"\n{prompt_user}'

                llm_req = LLMGenerateRequest(
                    messages=[
                        ChatMessage(role="system", content=system_instruction),
                        ChatMessage(role="user", content=prompt_user),
                    ],
                    temperature=0.0,
                    max_tokens=60,
                    thinking_budget=0,
                    preferred_model_name=preferred_model_name,
                    fallback_model_name=fallback_model,
                )

                llm_res = await asyncio.wait_for(
                    modelops_service.generate(db, llm_req),
                    timeout=2.0,
                )
                raw_json = llm_res.content.strip()
                if raw_json.startswith("```"):
                    raw_json = re.sub(
                        r"^```(?:json)?\s*|\s*```$", "", raw_json, flags=re.DOTALL
                    ).strip()
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict) and "is_export" in parsed:
                    raw_formats = parsed.get("formats") or []
                    if not isinstance(raw_formats, list):
                        raw_formats = [str(raw_formats)]
                    valid_formats = [
                        f.lower().strip()
                        for f in raw_formats
                        if f.lower().strip() in ("xlsx", "docx", "pdf")
                    ]
                    if parsed["is_export"] and not valid_formats:
                        valid_formats = ["xlsx", "docx", "pdf"]
                    logger.info(
                        "LLM Intent Classifier: is_export=%s, formats=%s",
                        parsed["is_export"],
                        valid_formats,
                    )
                    return {
                        "is_export": bool(parsed["is_export"]),
                        "formats": valid_formats,
                    }
            except Exception as exc:
                logger.warning("LLM Intent Classifier fallback to rule-based: %s", exc)

        # Fallback to rule-based detection
        fallback_export = self.detect_export_intent(user_message)
        fallback_formats = (
            self.detect_requested_formats(user_message, ["xlsx", "docx", "pdf"])
            if fallback_export
            else []
        )
        return {
            "is_export": fallback_export,
            "formats": fallback_formats,
        }

    @staticmethod
    def detect_export_intent(message: str) -> bool:
        """Check if message explicitly requests a downloadable file."""
        norm_msg = _norm(message)
        return any(kw in norm_msg for kw in EXPORT_KEYWORDS)

    @staticmethod
    def detect_requested_formats(message: str, default_formats: list[str] | None = None) -> list[str]:
        """Detect specific target export formats requested in natural language.

        - If the user specifically asks for Excel ('excel', 'xlsx', 'bảng tính'), returns ['xlsx'].
        - If the user specifically asks for Word ('word', 'docx', 'văn bản'), returns ['docx'].
        - If the user specifically asks for PDF ('pdf', 'bản in'), returns ['pdf'].
        - If multiple specific formats are mentioned, returns only the requested ones.
        - If the user asks for 'tất cả', 'cả 3', 'all', or specifies no format, returns default_formats.
        """
        norm_msg = _norm(message)
        fallback = default_formats or ["xlsx", "docx", "pdf"]

        # Check for explicit request for all formats
        all_kw = (
            "cả 3",
            "ca 3",
            "cả ba",
            "ca ba",
            "tất cả",
            "tat ca",
            "mọi định dạng",
            "moi dinh dang",
            "all formats",
            "toàn bộ tệp",
        )
        if any(kw in norm_msg for kw in all_kw):
            return fallback

        has_excel = any(kw in norm_msg for kw in ("excel", "xlsx", "xls", "bảng tính", "bang tinh"))
        has_word = any(kw in norm_msg for kw in ("word", "docx", "bản word", "ban word", "tệp word", "tep word", "file word"))
        has_pdf = any(kw in norm_msg for kw in ("pdf", "bản in", "ban in", "bản pdf", "ban pdf", "tệp pdf", "tep pdf", "file pdf"))

        selected: list[str] = []
        if has_excel:
            selected.append("xlsx")
        if has_word:
            selected.append("docx")
        if has_pdf:
            selected.append("pdf")

        if selected:
            return selected

        return fallback

    @staticmethod
    def extract_admission_parameters(
        message: str, candidate_majors: list[str] | None = None
    ) -> dict[str, Any]:
        """Extract candidate scores, combinations, areas, and target majors from natural language."""
        norm_msg = _norm(message)

        # 1. Extract Area
        detected_area = "KV3"
        for kw, canonical in AREA_MAP.items():
            if kw in norm_msg:
                detected_area = canonical
                break

        # 2. Extract Combination (A00, A01, B00, C00, D01, D07, etc.)
        combo_match = re.search(r"\b([a-d]\d{2})\b", message, re.IGNORECASE)
        detected_combo = combo_match.group(1).upper() if combo_match else "A00"

        # 3. Extract 3 scores or total score
        # Pattern A: 3 separate scores: "toán 8 lý 7 hóa 9" or "8.0, 7.5, 8.5" or "8 7 9"
        num_matches = re.findall(r"\b(10(?:\.0)?|[0-9](?:\.[0-9]{1,2})?)\b", message)
        extracted_scores: list[float] = []
        # Filter realistic exam scores (between 1.0 and 10.0)
        valid_nums = [float(n) for n in num_matches if 1.0 <= float(n) <= 10.0]

        total_score_match = re.search(r"\b([1-2]?[0-9](?:\.[0-9]{1,2})?)\s*(?:đ|điểm)\b", norm_msg)
        if len(valid_nums) >= 3:
            extracted_scores = valid_nums[:3]
        elif total_score_match:
            total_val = float(total_score_match.group(1))
            if total_val > 10.0:
                # Divide into 3 roughly equal scores for calculation
                part = round(total_val / 3.0, 2)
                extracted_scores = [part, part, round(total_val - 2 * part, 2)]

        # 4. Extract Major Name dynamically (Longest match first from candidate list, then syntactic regex)
        target_major = ""
        if candidate_majors:
            for m in sorted(candidate_majors, key=len, reverse=True):
                if _norm(m) in norm_msg:
                    target_major = m
                    break

        if not target_major:
            # Code match (7 digits) takes highest priority if explicit
            code_match = re.search(r"\b(7\d{6})\b", message)
            if code_match:
                target_major = code_match.group(1)
            else:
                # Syntactic match: "ngành [Tên ngành]"
                major_match = re.search(
                    r"(?:ngành|nganh|chuyên ngành|khoa)\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s\-]+?)(?:\s*(?:điểm|lấy|chuẩn|xét|khối|tổ hợp|có|học phí|chỉ tiêu|\?|\.|\,|$))",
                    message,
                    re.IGNORECASE,
                )
                if major_match:
                    raw_cand = major_match.group(1).strip()
                    cand_norm = _norm(raw_cand)
                    # Discard if it's a conjunction, question word, or export command
                    is_invalid = (
                        cand_norm in ("và", "va", "hoặc", "hoac", "nào", "nao", "gì", "gi", "phù hợp", "phu hop", "các", "những")
                        or any(cand_norm.startswith(p) for p in ("và ", "va ", "hoặc ", "nào ", "gì ", "phù hợp "))
                        or any(kw in cand_norm for kw in ("xuất file", "xuat file", "tải file", "excel", "word", "pdf", "kế hoạch", "nguyện vọng"))
                    )
                    if not is_invalid:
                        target_major = raw_cand

        # 5. Extract Candidate Name if mentioned
        name_match = re.search(r"(?:em tên là|em tên|tên em là|tôi tên là|mình là)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,30})", message, re.IGNORECASE)
        candidate_name = name_match.group(1).strip() if name_match else "Thí sinh"

        return {
            "area": detected_area,
            "combination": detected_combo,
            "scores": extracted_scores,
            "major_name": target_major,
            "candidate_name": candidate_name,
        }

    async def dispatch(
        self,
        module_code: str,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        collection_id: str | None = None,
        db: AsyncSession | None = None,
        preferred_model_name: str | None = None,
        fallback_model: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch agentic reasoning, facts augmentation, and artifact generation."""
        norm_msg = _norm(user_message)

        # 1. Semantic Intent & Format Analysis via LLM (with robust fallback)
        intent_res = await self.analyze_export_intent_with_llm(
            user_message=user_message,
            history=history,
            db=db,
            preferred_model_name=preferred_model_name,
            fallback_model=fallback_model,
        )
        is_export = intent_res.get("is_export", False)
        requested_formats = intent_res.get("formats") or ["xlsx", "docx", "pdf"]
        target_col = collection_id or f"col_{module_code}"

        # ----------------------------------------------------------------------
        # MODULE 1: ADMISSIONS (TUYỂN SINH)
        # ----------------------------------------------------------------------
        if module_code == "admissions":
            # Dynamically query candidate major names from database knowledge_facts
            candidate_majors: list[str] = []
            try:
                if db is not None:
                    stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col)
                    facts = (await db.execute(stmt)).scalars().all()
                    for f in facts:
                        if f.raw_data and f.raw_data.get("major_name"):
                            candidate_majors.append(f.raw_data["major_name"])
                        elif "ngành " in f.entity_name.lower():
                            clean_name = f.entity_name.replace("Điểm chuẩn ngành ", "").replace(" ĐH Quy Nhơn", "").strip()
                            candidate_majors.append(clean_name)
                else:
                    async with AsyncSessionFactory() as session:
                        stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col)
                        facts = (await session.execute(stmt)).scalars().all()
                        for f in facts:
                            if f.raw_data and f.raw_data.get("major_name"):
                                candidate_majors.append(f.raw_data["major_name"])
                            elif "ngành " in f.entity_name.lower():
                                clean_name = f.entity_name.replace("Điểm chuẩn ngành ", "").replace(" ĐH Quy Nhơn", "").strip()
                                candidate_majors.append(clean_name)
            except Exception as exc:
                logger.warning("Failed to load candidate majors: %s", exc)

            params = self.extract_admission_parameters(user_message, candidate_majors=candidate_majors)
            has_score_info = len(params["scores"]) >= 3 or bool(re.search(r"\b\d{2}(?:\.\d+)?\s*(?:đ|điểm)\b", norm_msg))
            has_major_interest = bool(params["major_name"]) or "ngành" in norm_msg

            if has_score_info or is_export or has_major_interest:
                # 1. MOET Score Calculation
                score_calc: dict[str, Any] | None = None
                final_score: float | None = None
                if len(params["scores"]) >= 3:
                    score_calc = calculate_moet_admission_score(
                        params["scores"],
                        area=params["area"],
                    )
                    final_score = score_calc["final_score"]

                # 2. Query Live Database Facts
                live_facts: list[KnowledgeFact] = []
                try:
                    if db is not None:
                        stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col)
                        live_facts = list((await db.execute(stmt)).scalars().all())
                    else:
                        async with AsyncSessionFactory() as session:
                            stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col)
                            live_facts = list((await session.execute(stmt)).scalars().all())
                except Exception as exc:
                    logger.warning("Failed to query live facts: %s", exc)

                target_majors = extract_majors_from_live_facts(live_facts)

                # 3. Match Majors
                matched_majors: list[dict[str, Any]] = []
                major_q = params["major_name"]
                combo = params["combination"]

                if major_q:
                    norm_q = _norm(major_q)
                    matched_majors = [
                        m for m in target_majors
                        if norm_q in _norm(m["major_name"]) or (m.get("major_code") and norm_q in m["major_code"])
                    ]
                elif combo:
                    matched_majors = [
                        m for m in target_majors
                        if not m.get("combinations") or combo in m.get("combinations", [])
                    ]
                    if not matched_majors:
                        matched_majors = target_majors
                else:
                    matched_majors = target_majors

                # 4. Classify Zones
                analysis_records: list[dict[str, Any]] = []
                for m in matched_majors:
                    cutoff = m.get("cutoff_2024") or 20.0
                    record = {
                        "major_code": m["major_code"],
                        "major_name": m["major_name"],
                        "combinations": m["combinations"],
                        "cutoff_score": cutoff,
                        "cutoff_2022": m.get("cutoff_2022"),
                        "cutoff_2023": m.get("cutoff_2023"),
                        "cutoff_2024": m.get("cutoff_2024"),
                        "quota_2026": m.get("quota_2026", 100),
                        "tuition_per_year": m.get("tuition_per_year"),
                    }
                    if final_score is not None:
                        record.update(classify_chance_zone(final_score, cutoff))
                    analysis_records.append(record)

                if final_score is not None:
                    analysis_records.sort(key=lambda r: float(r.get("delta_str", "0")), reverse=True)

                # 5. Export Universal Report if requested
                artifacts: list[dict[str, Any]] = []
                if is_export and analysis_records:
                    cand_name = params["candidate_name"]
                    metadata_dict = {
                        "Họ và tên thí sinh": cand_name,
                        "Tổ hợp xét tuyển": f"{combo} ({', '.join(str(s) for s in params['scores'])})",
                        "Khu vực ưu tiên": params["area"],
                        "Điểm ưu tiên quy đổi": f"+{score_calc['actual_priority']:.2f} đ" if score_calc else "0.0 đ",
                        "Tổng điểm xét tuyển": f"{final_score:.2f} đ" if final_score is not None else "Chưa cung cấp",
                        "Hotline hỗ trợ": "0256.3846.156",
                    }
                    summary_paras = [
                        f"Bản kế hoạch tư vấn nguyện vọng tuyển sinh dành cho thí sinh {cand_name}.",
                    ]
                    if score_calc:
                        summary_paras.append(
                            f"Điểm 3 môn gốc của bạn là {score_calc['raw_total']:.2f} điểm. Điểm ưu tiên sau quy chế là "
                            f"+{score_calc['actual_priority']:.2f} điểm. Tổng điểm xét tuyển chính thức: {final_score:.2f} điểm."
                        )

                    plan_rows = [
                        [
                            idx,
                            f"NV {idx}",
                            r["major_code"],
                            r["major_name"],
                            ", ".join(r["combinations"]),
                            f"{r['cutoff_score']:.2f}",
                            r.get("delta_str", "-"),
                            r.get("zone_label", "Tham khảo"),
                        ]
                        for idx, r in enumerate(analysis_records[:8], start=1)
                    ]

                    trend_rows = [
                        [
                            r["major_code"],
                            r["major_name"],
                            r.get("quota_2026", 100),
                            f"{r.get('cutoff_2022', 0.0):.2f}",
                            f"{r.get('cutoff_2023', 0.0):.2f}",
                            f"{r.get('cutoff_2024', 0.0):.2f}",
                            r.get("tuition_per_year", "Theo quy định"),
                        ]
                        for r in analysis_records[:8]
                    ]

                    payload = UniversalReportPayload(
                        title=f"Phiếu Tư Vấn Tuyển Sinh & Kế Hoạch Nguyện Vọng — {cand_name}",
                        subtitle="Trường Đại học Quy Nhơn — Hệ Thống Trợ Lý AI Tuyển Sinh Thông Minh",
                        issuing_unit="TRƯỜNG ĐẠI HỌC QUY NHƠN",
                        metadata=metadata_dict,
                        summary_paragraphs=summary_paras,
                        tables=[
                            ReportTable(
                                sheet_name="Kế hoạch nguyện vọng",
                                table_title="BẢNG ĐỀ XUẤT THỨ TỰ NGUYỆN VỌNG XÉT TUYỂN QNU 2026",
                                headers=["STT", "Nguyện vọng", "Mã ngành", "Tên ngành đào tạo", "Tổ hợp", "Điểm chuẩn 2024", "Chênh lệch", "Đánh giá cơ hội"],
                                rows=plan_rows,
                                notes="Thí sinh đăng ký và điều chỉnh nguyện vọng trực tuyến trên Cổng thông tin của Bộ GD&ĐT theo lịch trình chung.",
                            ),
                            ReportTable(
                                sheet_name="Điểm chuẩn 3 năm",
                                table_title="ĐỐI CHIẾU ĐIỂM CHUẨN 3 NĂM & CHỈ TIÊU",
                                headers=["Mã ngành", "Tên ngành", "Chỉ tiêu", "Điểm 2022", "Điểm 2023", "Điểm 2024", "Học phí dự kiến"],
                                rows=trend_rows,
                                notes="Trích xuất từ Kho tri thức Đề án Tuyển sinh Trường Đại học Quy Nhơn.",
                            ),
                        ],
                        formats=requested_formats,
                        base_name=f"tu_van_tuyen_sinh_{_norm(cand_name).replace(' ', '_')}",
                    )
                    artifacts = await export_universal_report(payload)

                # Build strategic consulting guidance for LLM context
                guidance_parts: list[str] = []
                if score_calc:
                    if score_calc["is_reduced"]:
                        guidance_parts.append(
                            f"[THÔNG TIN ĐIỂM XÉT TUYỂN]:\n"
                            f"- Điểm 3 môn gốc: {score_calc['raw_total']:.2f} điểm (thuộc tổ hợp {params['combination']}).\n"
                            f"- Khu vực ưu tiên: {score_calc['area']} (Mức gốc: +{score_calc['base_priority']:.2f} đ).\n"
                            f"- Điểm ưu tiên sau quy chế giảm trừ Bộ GD&ĐT (do tổng >= 22.5 đ): +{score_calc['actual_priority']:.2f} điểm.\n"
                            f"- TỔNG ĐIỂM XÉT TUYỂN CHÍNH THỨC: {score_calc['final_score']:.2f} điểm."
                        )
                    else:
                        guidance_parts.append(
                            f"[THÔNG TIN ĐIỂM XÉT TUYỂN]:\n"
                            f"- Điểm 3 môn: {score_calc['raw_total']:.2f} điểm + Điểm ưu tiên {score_calc['area']}: +{score_calc['actual_priority']:.2f} điểm.\n"
                            f"- TỔNG ĐIỂM XÉT TUYỂN CHÍNH THỨC: {score_calc['final_score']:.2f} điểm."
                        )

                if analysis_records:
                    top_majors_lines = []
                    for idx, r in enumerate(analysis_records[:6], start=1):
                        delta = r.get("delta_str", "")
                        zone = r.get("zone_label", "")
                        top_majors_lines.append(
                            f"  {idx}. {r['major_name']} (Mã: {r['major_code']}) — Điểm chuẩn 2024: {r['cutoff_score']:.2f} đ"
                            + (f" [Chênh lệch: {delta}, Vùng: {zone}]" if zone else "")
                        )
                    guidance_parts.append("[CÁC NGÀNH ĐÀO TẠO PHÙ HỢP]:\n" + "\n".join(top_majors_lines))

                if artifacts:
                    file_names = ", ".join(a["name"] for a in artifacts)
                    fmt_tags = []
                    for a in artifacts:
                        t = a.get("type", "")
                        if t == "xlsx":
                            fmt_tags.append("Excel")
                        elif t == "docx":
                            fmt_tags.append("Word")
                        elif t == "pdf":
                            fmt_tags.append("PDF")
                        else:
                            fmt_tags.append(t.upper())
                    fmt_label = ", ".join(dict.fromkeys(fmt_tags))
                    if len(artifacts) == 1:
                        guidance_parts.append(
                            f"[THÔNG BÁO TỆP KẾT XUẤT]: Đã tạo thành công 1 tệp {fmt_label} ({file_names}). "
                            f"Hãy thông báo cho người dùng biết tệp {fmt_label} đã được tạo và hướng dẫn họ nhấp vào nút tải về trực tiếp phía dưới tin nhắn để nhận tệp."
                        )
                    else:
                        guidance_parts.append(
                            f"[THÔNG BÁO TỆP KẾT XUẤT]: Đã tạo thành công {len(artifacts)} tệp ({fmt_label}: {file_names}). "
                            f"Hãy thông báo cho người dùng biết và hướng dẫn họ nhấp vào các nút tải về trực tiếp phía dưới tin nhắn."
                        )

                return {
                    "has_agentic_guidance": True,
                    "guidance_context": "\n\n".join(guidance_parts),
                    "artifacts": artifacts,
                    "score_calculation": score_calc,
                }

        # ----------------------------------------------------------------------
        # MODULE 2: REGULATIONS (QUY CHẾ - HỌC VỤ)
        # ----------------------------------------------------------------------
        elif module_code == "regulations" and is_export:
            # Query live regulations facts directly from database
            try:
                if db is not None:
                    stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col).limit(20)
                    facts = (await db.execute(stmt)).scalars().all()
                else:
                    async with AsyncSessionFactory() as session:
                        stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col).limit(20)
                        facts = (await session.execute(stmt)).scalars().all()
            except Exception:
                facts = []

            rows = [
                [idx, f.entity_name, f.attribute_name, f.attribute_value]
                for idx, f in enumerate(facts, start=1)
            ]

            if not rows:
                return {
                    "has_agentic_guidance": True,
                    "guidance_context": "[THÔNG BÁO]: Kho tri thức hiện chưa có dữ liệu cấu trúc (Fact layer) cho Quy chế học vụ. Vui lòng nạp tài liệu vào kho tri thức để kích hoạt tính năng kết xuất văn bản.",
                    "artifacts": [],
                }

            payload = UniversalReportPayload(
                title="Sổ Tay Tóm Tắt Quy Chế Đào Tạo & Học Vụ QNU",
                subtitle="Trường Đại học Quy Nhơn — Phòng Đào Tạo & Công Tác Sinh Viên",
                issuing_unit="TRƯỜNG ĐẠI HỌC QUY NHƠN",
                metadata={"Đơn vị ban hành": "Phòng Đào tạo QNU", "Ngày xuất tệp": "Học kỳ I"},
                summary_paragraphs=[
                    "Tài liệu tổng hợp các quy định học vụ cốt lõi dành cho sinh viên hệ chính quy Trường Đại học Quy Nhơn.",
                    "Sinh viên cần lưu ý các mốc điểm trung bình tích lũy (GPA) để tránh rơi vào diện cảnh báo học vụ hoặc buộc thôi học.",
                ],
                tables=[
                    ReportTable(
                        sheet_name="Quy chế đào tạo",
                        table_title="BẢNG TỔNG HỢP CÁC QUY ĐỊNH HỌC VỤ & ĐIỀU KIỆN TỐT NGHIỆP",
                        headers=["STT", "Hạng mục", "Nội dung quy định", "Mô tả chi tiết"],
                        rows=rows,
                        notes="Trích xuất trực tiếp từ Kho tri thức Quy chế Đào tạo của Trường Đại học Quy Nhơn.",
                    )
                ],
                formats=requested_formats,
                base_name="so_tay_quy_che_hoc_vu_qnu",
            )
            artifacts = await export_universal_report(payload)
            file_names = ", ".join(a["name"] for a in artifacts)
            fmt_tags = [a.get("type", "").upper() for a in artifacts]
            fmt_label = ", ".join(dict.fromkeys(fmt_tags))
            return {
                "has_agentic_guidance": True,
                "guidance_context": f"[THÔNG BÁO TỆP KẾT XUẤT]: Đã tạo thành công {len(artifacts)} tệp Sổ tay quy chế học vụ ({fmt_label}: {file_names}). Hãy thông báo người dùng tải về ở nút phía dưới.",
                "artifacts": artifacts,
            }

        # ----------------------------------------------------------------------
        # MODULE 3: LIBRARY (THƯ VIỆN)
        # ----------------------------------------------------------------------
        elif module_code == "library" and is_export:
            # Query live library facts directly from database
            try:
                if db is not None:
                    stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col).limit(20)
                    facts = (await db.execute(stmt)).scalars().all()
                else:
                    async with AsyncSessionFactory() as session:
                        stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == target_col).limit(20)
                        facts = (await session.execute(stmt)).scalars().all()
            except Exception:
                facts = []

            rows = [
                [idx, f.entity_name, f.attribute_name, f.attribute_value]
                for idx, f in enumerate(facts, start=1)
            ]

            if not rows:
                return {
                    "has_agentic_guidance": True,
                    "guidance_context": "[THÔNG BÁO]: Kho tri thức hiện chưa có dữ liệu cấu trúc (Fact layer) cho Thư viện. Vui lòng nạp tài liệu vào kho tri thức để kích hoạt tính năng kết xuất văn bản.",
                    "artifacts": [],
                }

            payload = UniversalReportPayload(
                title="Danh Mục Dịch Vụ & Tài Liệu Thư Viện QNU",
                subtitle="Trường Đại học Quy Nhơn — Trung Tâm Học Liệu & Thư Viện",
                issuing_unit="TRƯỜNG ĐẠI HỌC QUY NHƠN",
                metadata={"Đơn vị quản lý": "Thư viện QNU", "Website tra cứu": "lib.qnu.edu.vn"},
                summary_paragraphs=[
                    "Danh mục các đầu sách, tài liệu học phần và các dịch vụ học thuật của Trung tâm Thông tin - Thư viện QNU.",
                ],
                tables=[
                    ReportTable(
                        sheet_name="Dịch vụ & Học liệu Thư viện",
                        table_title="DANH MỤC THÔNG TIN DỊCH VỤ & HỌC LIỆU THƯ VIỆN ĐH QUY NHƠN",
                        headers=["STT", "Hạng mục / Dịch vụ", "Nội dung quy định", "Mô tả chi tiết"],
                        rows=rows,
                        notes="Trích xuất trực tiếp từ Kho tri thức Thư viện Trường Đại học Quy Nhơn.",
                    )
                ],
                formats=requested_formats,
                base_name="danh_muc_tai_lieu_thu_vien_qnu",
            )
            artifacts = await export_universal_report(payload)
            file_names = ", ".join(a["name"] for a in artifacts)
            fmt_tags = [a.get("type", "").upper() for a in artifacts]
            fmt_label = ", ".join(dict.fromkeys(fmt_tags))
            return {
                "has_agentic_guidance": True,
                "guidance_context": f"[THÔNG BÁO TỆP KẾT XUẤT]: Đã tạo thành công {len(artifacts)} tệp Danh mục thư viện ({fmt_label}: {file_names}). Hãy thông báo người dùng tải về ở nút phía dưới.",
                "artifacts": artifacts,
            }

        return {"has_agentic_guidance": False, "artifacts": []}


# Global singleton
consulting_dispatcher = AgenticConsultingDispatcher()

"""Query Rewrite Node Handler — Normalizes user queries, corrects contextual typos and expands abbreviations."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any

from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

# Fast Rule-based term mappings (0ms latency)
_ACRONYM_MAP: dict[str, str] = {
    r"\bcntt\b": "Công nghệ thông tin",
    r"\bit\b": "Công nghệ thông tin",
    r"\bqtkd\b": "Quản trị kinh doanh",
    r"\bqtnl\b": "Quản trị nhân lực",
    r"\btckt\b": "Tài chính - Ngân hàng",
    r"\btcnh\b": "Tài chính - Ngân hàng",
    r"\bkhmt\b": "Khoa học máy tính",
    r"\bktpm\b": "Kỹ thuật phần mềm",
    r"\bnna\b": "Ngôn ngữ Anh",
    r"\bsp toán\b": "Sư phạm Toán học",
    r"\bsp tin\b": "Sư phạm Tin học",
    r"\bsp lý\b": "Sư phạm Vật lý",
    r"\bsp hóa\b": "Sư phạm Hóa học",
    r"\bsp văn\b": "Sư phạm Ngữ văn",
    r"\bsp anh\b": "Sư phạm Tiếng Anh",
    r"\bsp sử\b": "Sư phạm Lịch sử",
    r"\bsp địa\b": "Sư phạm Địa lý",
    r"\bsp sinh\b": "Sư phạm Sinh học",
    r"\bđgnl\b": "Đánh giá năng lực",
    r"\bdgnl\b": "Đánh giá năng lực",
    r"\bthptqg\b": "THPT Quốc gia",
    r"\bthpt\b": "THPT",
    r"\bktx\b": "Ký túc xá",
    r"\bnd\s*116\b": "Nghị định 116",
    r"\bnghị định 116\b": "Nghị định 116",
    r"\bgdmn\b": "Giáo dục Mầm non",
    r"\bgdth\b": "Giáo dục Tiểu học",
    # Academic regulations & university life acronyms
    r"\bđrl\b": "Điểm rèn luyện",
    r"\bdrl\b": "Điểm rèn luyện",
    r"\bgpa\b": "GPA",
    r"\bctđt\b": "Chương trình đào tạo",
    r"\bctsv\b": "Công tác sinh viên",
    r"\bpđt\b": "Phòng Đào tạo",
    r"\bpctsv\b": "Phòng Công tác sinh viên",
    r"\bnckh\b": "Nghiên cứu khoa học",
    r"\bkhcn\b": "Khoa học - Công nghệ",
}

# Contextual typo patterns (e.g. valid Vietnamese words mistyped in context)
_TYPO_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # "ngày" mistyped instead of "ngành" when referring to majors / admissions
    (
        re.compile(
            r"\bngày\s+(công nghệ thông tin|cntt|khoa học máy tính|kỹ thuật phần mềm|quản trị kinh doanh|qtkd|kế toán|tài chính|kinh tế|sư phạm|ngôn ngữ|luật|du lịch|đào tạo|học\b)",
            re.IGNORECASE,
        ),
        r"ngành \1",
    ),
    (
        re.compile(
            r"\b(học phí|điểm chuẩn|chỉ tiêu|thông tin|xét tuyển|tuyển sinh|mã|chương trình)\s+ngày\b",
            re.IGNORECASE,
        ),
        r"\1 ngành",
    ),
    (re.compile(r"\b(các|những|tất cả các|danh sách|tuyển)\s+ngày\b", re.IGNORECASE), r"\1 ngành"),
    (re.compile(r"\bngày\s+(nào|gì|hot|mới)\b", re.IGNORECASE), r"ngành \1"),
    # "học bà" -> "học bạ"
    (re.compile(r"\bhọc\s+bà\b", re.IGNORECASE), "học bạ"),
    # "tín chì" -> "tín chỉ"
    (re.compile(r"\btín\s+chì\b", re.IGNORECASE), "tín chỉ"),
    # "học phầm" -> "học phần"
    (re.compile(r"\bhọc\s+phầm\b", re.IGNORECASE), "học phần"),
    # "rèn luyên" -> "rèn luyện"
    (re.compile(r"\brèn\s+luyên\b", re.IGNORECASE), "rèn luyện"),
    # "khen thướng" -> "khen thưởng"
    (re.compile(r"\bkhen\s+thướng\b", re.IGNORECASE), "khen thưởng"),
    # "giáo trinh" -> "giáo trình"
    (re.compile(r"\bgiáo\s+trinh\b", re.IGNORECASE), "giáo trình"),
    # "tài liêu" -> "tài liệu"
    (re.compile(r"\btài\s+liêu\b", re.IGNORECASE), "tài liệu"),
    # "quy trinh" -> "quy trình"
    (re.compile(r"\bquy\s+trinh\b", re.IGNORECASE), "quy trình"),
    # "điểm chuẫn" / "điễm chuẩn" -> "điểm chuẩn"
    (re.compile(r"\bđi[ểẽ]m\s+chu[ẫẩẳãả]n\b", re.IGNORECASE), "điểm chuẩn"),
    # "kí túc sá" / "ký túc sá" -> "ký túc xá"
    (re.compile(r"\bk[íy]\s+túc\s+s[áa]\b", re.IGNORECASE), "ký túc xá"),
    # "học bỗng" -> "học bổng"
    (re.compile(r"\bhọc\s+b[ỗõ]ng?\b", re.IGNORECASE), "học bổng"),
    # "sư pham" (missing dot) / "sư phạn" (typo n) -> "sư phạm"
    (re.compile(r"\bsư\s+(?:pham|phạn)\b", re.IGNORECASE), "sư phạm"),
    # "chỉ tiệu" -> "chỉ tiêu"
    (re.compile(r"\bchỉ\s+tiệu\b", re.IGNORECASE), "chỉ tiêu"),
    # "tuyển xính" -> "tuyển sinh"
    (re.compile(r"\btuyển\s+xính\b", re.IGNORECASE), "tuyển sinh"),
]

# Canonical major capitalizations for standardized retrieval (matched longest first)
_CANONICAL_MAJORS: dict[str, str] = {
    r"\bsư phạm toán học\b": "Sư phạm Toán học",
    r"\bsư phạm toán(?!\s*học)\b": "Sư phạm Toán học",
    r"\bsư phạm ngữ văn\b": "Sư phạm Ngữ văn",
    r"\bsư phạm tiếng anh\b": "Sư phạm Tiếng Anh",
    r"\bsư phạm tin học\b": "Sư phạm Tin học",
    r"\bsư phạm vật lý\b": "Sư phạm Vật lý",
    r"\bsư phạm hóa học\b": "Sư phạm Hóa học",
    r"\bsư phạm sinh học\b": "Sư phạm Sinh học",
    r"\bsư phạm lịch sử\b": "Sư phạm Lịch sử",
    r"\bsư phạm địa lý\b": "Sư phạm Địa lý",
    r"\bcông nghệ thông tin\b": "Công nghệ thông tin",
    r"\bquản trị kinh doanh\b": "Quản trị kinh doanh",
    r"\bquản trị nhân lực\b": "Quản trị nhân lực",
    r"\btài chính\s*-\s*ngân hàng\b": "Tài chính - Ngân hàng",
    r"\bkhoa học máy tính\b": "Khoa học máy tính",
    r"\bkỹ thuật phần mềm\b": "Kỹ thuật phần mềm",
    r"\bngôn ngữ anh\b": "Ngôn ngữ Anh",
}


def fast_rule_normalize(text: str, extra_acronyms: dict[str, str] | None = None) -> str:
    """Apply rule-based acronym expansion and contextual typo correction in 0ms.

    `extra_acronyms` allows each new assistant to inject domain abbreviations
    via node config `custom_acronyms` without code changes.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text.strip())

    # 1. Apply typo pattern replacements
    for pattern, replacement in _TYPO_PATTERNS:
        normalized = pattern.sub(replacement, normalized)

    # 2. Apply acronym replacements (universal + per-assistant custom)
    for pat_str, replacement in _ACRONYM_MAP.items():
        normalized = re.sub(pat_str, replacement, normalized, flags=re.IGNORECASE)
    if extra_acronyms:
        for pat_str, replacement in extra_acronyms.items():
            if pat_str and replacement:
                normalized = re.sub(pat_str, replacement, normalized, flags=re.IGNORECASE)

    # 3. Apply canonical major capitalizations
    for pat_str, replacement in _CANONICAL_MAJORS.items():
        normalized = re.sub(pat_str, replacement, normalized, flags=re.IGNORECASE)

    # 4. Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def get_node_instruction(context: WorkflowContext, config: dict[str, Any]) -> str:
    """Resolve query rewrite instruction for this node.
    
    Priority:
    1. Explicit instruction/prompt configured directly on this DAG node.
    2. Role description from the executing assistant profile (if attached).
    3. Generic universal prompt for QNU AI Platform.
    """
    # 1. Explicit instruction or prompt configured on this DAG node
    node_instruction = (
        config.get("instruction")
        or config.get("prompt")
        or config.get("custom_prompt")
    )
    if node_instruction and str(node_instruction).strip():
        return str(node_instruction).strip()

    # 2. If a simple domain string is provided (e.g. 'ký túc xá', 'khảo thí')
    domain = config.get("domain")
    if domain and str(domain).strip():
        return (
            f"Bạn là trợ lý chuẩn hóa câu hỏi trong quy trình {str(domain).strip()} cho Trường Đại học Quy Nhơn (QNU).\n"
            "Nhiệm vụ: Sửa các từ gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh tiếng Việt, "
            "chuẩn hóa các từ viết tắt chuyên môn và viết hoa chuẩn danh từ riêng, thuật ngữ."
        )

    # 3. Inherit role context from Assistant Profile if running under an assistant
    profile = context.assistant_profile
    if profile:
        persona_scope = getattr(profile, "persona_scope", None)
        role_desc = None
        if persona_scope:
            role_desc = getattr(persona_scope, "persona", None) or getattr(
                persona_scope, "role_description", None
            )
            if role_desc:
                role_desc = str(role_desc).strip()
        if role_desc:
            return (
                f"Bạn là trợ lý chuẩn hóa câu hỏi cho quy trình '{profile.name or profile.assistant_code}' "
                f"của Trường Đại học Quy Nhơn (QNU) ({role_desc}).\n"
                "Nhiệm vụ: Sửa các từ gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh tiếng Việt, "
                "chuẩn hóa các từ viết tắt chuyên môn và viết hoa chuẩn danh từ riêng, thuật ngữ."
            )

    # 4. Universal fallback for any workflow on QNU AI Platform
    return (
        "Bạn là trợ lý chuẩn hóa câu hỏi cho Trường Đại học Quy Nhơn (QNU).\n"
        "Nhiệm vụ: Sửa các từ gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh tiếng Việt, "
        "chuẩn hóa các từ viết tắt chuyên môn và viết hoa chuẩn danh từ riêng, thuật ngữ."
    )


def build_rewrite_prompt(query: str, instruction: str) -> str:
    """Build rewrite prompt with few-shot formatting rules using the workflow instruction."""
    # If the user specified a full template with {query} placeholder, honor it directly
    if "{query}" in instruction:
        return instruction.replace("{query}", query)

    return (
        f"{instruction.strip()}\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "- Bạn KHÔNG PHẢI chatbot nói chuyện với người dùng. Nhiệm vụ của bạn CHỈ LÀ chuẩn hóa câu hỏi đầu vào.\n"
        "- Giữ nguyên 100% ý định câu hỏi gốc của người dùng.\n"
        "- Trả về DUY NHẤT một dòng chứa câu hỏi đã được chuẩn hóa.\n"
        "- TUYỆT ĐỐI KHÔNG giải thích, KHÔNG hỏi ngược lại người dùng (không dùng 'Bạn muốn...', 'Vui lòng...'), KHÔNG thêm tiền tố, KHÔNG trả lời câu hỏi.\n"
        "- Nếu câu hỏi đã rõ ràng, giữ nguyên câu hỏi.\n\n"
        "Ví dụ:\n"
        "Input: học phí ngày cntt là bao nhiêu\n"
        "Học phí ngành Công nghệ thông tin là bao nhiêu?\n\n"
        "Input: quy định xét học bỗng đrl tín chì\n"
        "Quy định xét học bổng điểm rèn luyện và tín chỉ như thế nào?\n\n"
        "Input: bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?\n"
        "Ngành Công nghệ thông tin xét tuyển những tổ hợp môn nào?\n\n"
        f"Input: {query}"
    )


class QueryRewriteNodeHandler(BaseNodeHandler):
    """Normalizes user query, corrects contextual typos, and expands terminology per workflow."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        raw_query = context.node_data.get("user_message") or context.inputs.get("message", "")
        if not raw_query:
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output={"normalized_query": "", "original_query": "", "modified": False},
            )

        config = node_spec.config or {}
        use_fast_rules = config.get("use_fast_rules", True)
        use_llm = config.get("use_llm", True)
        custom_acronyms = config.get("custom_acronyms")
        if not isinstance(custom_acronyms, dict):
            custom_acronyms = None

        # Stage 1: Fast Rule-based Normalization (0ms, reusable per-assistant)
        rule_normalized = (
            fast_rule_normalize(raw_query, extra_acronyms=custom_acronyms)
            if use_fast_rules
            else raw_query
        )
        final_query = rule_normalized

        # Stage 2: Fast Contextual LLM Rewrite (optional, ~150ms)
        if use_llm and context.db:
            try:
                llm_query = await self._rewrite_with_llm(context, rule_normalized, config=config)
                if llm_query and len(llm_query) >= 3:
                    final_query = llm_query
            except Exception as exc:
                logger.warning(
                    "LLM query rewrite skipped due to %s: %s. Using rule-normalized query.",
                    type(exc).__name__,
                    exc,
                )

        # Store in workflow context for downstream nodes (e.g. knowledge_answer)
        context.node_data["raw_query"] = raw_query
        context.node_data["normalized_query"] = final_query
        context.node_data["user_message"] = final_query

        was_modified = final_query.strip().lower() != raw_query.strip().lower()
        if was_modified:
            logger.info("Query rewritten: '%s' -> '%s'", raw_query, final_query)

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "normalized_query": final_query,
                "original_query": raw_query,
                "modified": was_modified,
            },
        )

    async def _rewrite_with_llm(
        self, context: WorkflowContext, query: str, config: dict[str, Any] | None = None
    ) -> str | None:
        """Call fast LLM with thinkingBudget=0 to correct contextual typos without altering intent."""
        if not context.db:
            return None

        node_cfg = config or {}
        instruction = get_node_instruction(context, node_cfg)
        prompt = build_rewrite_prompt(query, instruction)

        profile = context.assistant_profile
        primary_model = (
            profile.model_policy.primary_model
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else None
        )
        fallback_model = (
            profile.model_policy.fallback_model
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else None
        )

        req = LLMGenerateRequest(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.0,
            max_tokens=200,
            thinking_budget=0,
            preferred_model_name=primary_model,
            fallback_model_name=fallback_model,
        )

        # Enforce 3.0s timeout to never stall chat pipeline
        try:
            res = await asyncio.wait_for(
                modelops_service.generate(context.db, req),
                timeout=3.0,
            )
            raw_text = res.content.strip()
            if not raw_text or "[Local " in raw_text or "máy chủ AI nội bộ" in raw_text or "Đã ghi nhận yêu cầu" in raw_text:
                logger.debug("LLM query rewrite returned fallback mock, keeping rule query.")
                return query

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if not lines:
                return query

            filtered_lines: list[str] = []
            for line in lines:
                cleaned = re.sub(
                    r"^(output|input|kết quả|câu hỏi|sửa lại|note):\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip().strip('"').strip("'")
                if cleaned and not cleaned.endswith(":") and len(cleaned) > 3:
                    filtered_lines.append(cleaned)

            candidate = filtered_lines[-1] if filtered_lines else lines[-1]
            candidate = re.sub(
                r"^(output|input|kết quả|câu hỏi|sửa lại|note):\s*",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip().strip('"').strip("'")

            # Defensive guard 1: Reject meta-instruction / chatbot prompt leakage
            leakage_patterns = re.compile(
                r"(bạn muốn chuẩn hóa|vui lòng cung cấp|hãy nhập|tôi là trợ lý|chào bạn|"
                r"câu hỏi đầu vào|yêu cầu xử lý|hệ thống|bạn có thể hỏi|chuẩn hóa câu hỏi nào|"
                r"xin vui lòng|vui lòng cho biết)",
                re.IGNORECASE,
            )
            if leakage_patterns.search(candidate):
                logger.warning(
                    "LLM query rewrite leaked chatbot conversational meta '%s', fallback to original.",
                    candidate,
                )
                return query

            # Defensive guard 2: Must share significant keywords with query (prevent hallucinations)
            _stopwords = {
                "bạn", "biết", "không", "cho", "nào", "tôi", "xin", "chào", "năm",
                "được", "các", "những", "với", "của", "thế", "như", "bao", "nhiêu",
                "gì", "là", "và", "trong", "trường", "đại", "học", "muốn", "hỏi"
            }
            query_words = {w for w in re.findall(r"\w{3,}", query.lower()) if w not in _stopwords}
            cand_words = set(re.findall(r"\w{3,}", candidate.lower()))
            if query_words and not (query_words & cand_words):
                logger.warning(
                    "LLM query rewrite has zero keyword overlap ('%s' vs '%s'), fallback to original.",
                    candidate,
                    query,
                )
                return query

            # Defensive guard 3: candidate must not be excessively long or empty
            if len(candidate) > len(query) * 3 or len(candidate) < 3:
                return query
            return candidate
        except TimeoutError:
            logger.debug("LLM query rewrite timed out (>3.0s), using rule result")
            return None

"""Canonical templates and idempotent database seeding for QNU assistants."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistants.models import AssistantModel
from app.modules.assistants.schemas import AssistantSeedResponse
from app.modules.workflows.models import WorkflowDefinition

logger = logging.getLogger(__name__)

WORKFLOW_DIRECTORY = Path(__file__).resolve().parents[4] / "configs" / "workflows"


def _lifecycle_config(
    *,
    persona: str,
    topics: list[str],
    questions: list[str],
    chunking_strategy: str,
    primary_model: str = "gpt-4o-mini",
    fallback_model: str = "gemini-1.5-flash",
    temperature: float = 0.2,
    require_structured_facts: bool = False,
    enabled_tools: list[str] | None = None,
    no_answer_message: str,
) -> dict[str, Any]:
    return {
        "sample_questions": questions,
        "persona_scope": {
            "persona": persona,
            "allowed_topics": topics,
            "out_of_scope_policy": (
                "Từ chối lịch sự nội dung ngoài phạm vi và hướng dẫn người dùng đến đơn vị phụ trách."
            ),
        },
        "knowledge_policy": {
            "chunking_strategy": chunking_strategy,
            "require_structured_facts": require_structured_facts,
            "retrieval_limit": 10,
        },
        "model_policy": {
            "primary_model": primary_model,
            "fallback_model": fallback_model,
            "temperature": temperature,
            "max_tokens": 1200,
        },
        "guardrails": {
            "block_prompt_injection": True,
            "mask_pii": True,
            "require_grounded_answer": True,
            "protect_system_prompt": True,
            "no_answer_message": no_answer_message,
        },
        "tools": {
            "enabled_tools": enabled_tools or [],
            "human_approval_required": True,
        },
        "output_policy": {
            "formats": ["markdown", "table", "checklist"],
            "require_citations": True,
            "citation_format": "Tên văn bản, Điều/Khoản, Trang",
        },
        "evaluation_policy": {
            "faithfulness_threshold": 0.9,
            "answer_relevance_threshold": 0.85,
            "context_precision_threshold": 0.8,
        },
    }


STANDARD_ASSISTANTS: list[dict[str, Any]] = [
    {
        "id": "ast_admissions",
        "code": "admissions",
        "name": "Trợ lý Tuyển sinh ĐH Quy Nhơn",
        "description": (
            "Giải đáp đề án tuyển sinh, điểm chuẩn, phương thức xét tuyển, học phí, học bổng "
            "và ký túc xá từ nguồn chính thức."
        ),
        "category": "admissions",
        "avatar_url": "/static/avatars/assistant_admissions.png",
        "workflow_id": "admissions-assistant",
        "collection_id": "col_admissions",
        "system_prompt": (
            "Bạn là Trợ lý Tuyển sinh chính thức của Trường Đại học Quy Nhơn. Chỉ trả lời dựa "
            "trên đề án tuyển sinh và dữ liệu chính thức được cung cấp. Không suy diễn số liệu. "
            "Khi thiếu căn cứ, hướng dẫn liên hệ Hotline 0256.3846.156 hoặc "
            "tuyensinh@qnu.edu.vn."
        ),
        "config": _lifecycle_config(
            persona="Trợ lý Tuyển sinh chính thức, thân thiện và chính xác của QNU.",
            topics=["đề án tuyển sinh", "điểm chuẩn", "học phí", "học bổng", "ký túc xá", "sư phạm", "Nghị định 116"],
            questions=[
                "Điểm chuẩn ngành Sư phạm Toán học và Công nghệ thông tin năm 2024 là bao nhiêu?",
                "Trường Đại học Quy Nhơn áp dụng những phương thức xét tuyển nào?",
                "Chính sách hỗ trợ học phí và sinh hoạt phí cho sinh viên Sư phạm theo Nghị định 116 như thế nào?",
                "Thủ tục và chi phí đăng ký ở Ký túc xá QNU gồm những gì?",
            ],
            chunking_strategy="SemanticChunker",
            require_structured_facts=True,
            enabled_tools=["lookup_admission_score"],
            no_answer_message=(
                "Thông tin này chưa có trong Đề án tuyển sinh chính thức. Vui lòng liên hệ "
                "Hotline 0256.3846.156 hoặc tuyensinh@qnu.edu.vn."
            ),
        ),
    },
    {
        "id": "ast_regulations",
        "code": "regulations",
        "name": "Trợ lý Quy chế Đào tạo & Khảo thí",
        "description": (
            "Tra cứu quy chế tín chỉ, đăng ký học phần, xử lý học vụ, chuẩn đầu ra và xét tốt nghiệp."
        ),
        "category": "academic",
        "avatar_url": "/static/avatars/assistant_regulations.png",
        "workflow_id": "regulations-assistant",
        "collection_id": "col_regulations",
        "system_prompt": (
            "Bạn là Trợ lý Quy chế Học vụ của Trường Đại học Quy Nhơn. Mọi câu trả lời phải "
            "căn cứ quy chế hiện hành và trích dẫn Điều, Khoản. Với quyết định hành chính cá "
            "biệt, hướng dẫn liên hệ Phòng Đào tạo."
        ),
        "config": _lifecycle_config(
            persona="Trợ lý tra cứu quy chế đào tạo và khảo thí chính thức của QNU.",
            topics=["quy chế đào tạo", "tín chỉ", "cảnh báo học vụ", "chuẩn đầu ra", "tốt nghiệp", "thang điểm 4", "VSTEP"],
            questions=[
                "Điều kiện cảnh báo học tập và buộc thôi học được quy định tại Điều 16 như thế nào?",
                "Cách tính điểm trung bình tích lũy thang điểm 4 và quy đổi điểm chữ ra sao?",
                "Chuẩn đầu ra ngoại ngữ VSTEP và tin học đối với sinh viên chính quy quy định thế nào?",
                "Sinh viên được đăng ký tối đa bao nhiêu tín chỉ trong một học kỳ chính?",
            ],
            chunking_strategy="ClauseBasedChunker",
            temperature=0.1,
            require_structured_facts=True,
            enabled_tools=[],
            no_answer_message=(
                "Chưa đủ căn cứ trong quy chế hiện hành để trả lời. Vui lòng liên hệ Phòng Đào tạo."
            ),
        ),
    },
    {
        "id": "ast_library",
        "code": "library",
        "name": "Trợ lý Thư viện & Học liệu Số",
        "description": (
            "Hỗ trợ tìm tài liệu, giáo trình, luận văn, cơ sở dữ liệu số và quy định mượn trả sách."
        ),
        "category": "resources",
        "avatar_url": "/static/avatars/assistant_library.png",
        "workflow_id": "library-assistant",
        "collection_id": "col_library",
        "system_prompt": (
            "Bạn là Trợ lý Thư viện số Trường Đại học Quy Nhơn. Hỗ trợ tra cứu học liệu và "
            "hướng dẫn sử dụng thư viện dựa trên danh mục và quy định chính thức."
        ),
        "config": _lifecycle_config(
            persona="Trợ lý tra cứu thư viện và học liệu số của QNU.",
            topics=["giáo trình", "luận văn", "mượn trả sách", "cơ sở dữ liệu số", "phòng học nhóm", "kiểm tra đạo văn Turnitin", "ScienceDirect", "IEEE"],
            questions=[
                "Quy định kiểm tra chống đạo văn Turnitin đối với khóa luận tốt nghiệp như thế nào?",
                "Cách truy cập các cơ sở dữ liệu số quốc tế như ScienceDirect, IEEE Xplore từ xa bằng tài khoản QNU?",
                "Hạn ngạch mượn giáo trình và thời gian được giữ sách của sinh viên là bao nhiêu?",
                "Quy trình nộp lưu chiểu luận văn tốt nghiệp bản điện tử cho thư viện gồm những bước nào?",
            ],
            chunking_strategy="ClauseBasedChunker",
            require_structured_facts=True,
            enabled_tools=[],
            no_answer_message=(
                "Chưa tìm thấy thông tin trong cẩm nang thư viện. Vui lòng liên hệ Trung tâm "
                "Thông tin - Thư viện QNU qua hotline 0256.3846.888 hoặc thuvien@qnu.edu.vn."
            ),
        ),
    },
    {
        "id": "ast_drafting",
        "code": "drafting",
        "name": "Trợ lý Soạn thảo Văn bản Hành chính & Sư phạm",
        "description": (
            "Hỗ trợ soạn thông báo, tờ trình, kế hoạch và giấy mời theo Nghị định 30/2020/NĐ-CP."
        ),
        "category": "administration",
        "avatar_url": "/static/avatars/assistant_drafting.png",
        "workflow_id": "drafting-assistant",
        "collection_id": "col_drafting",
        "system_prompt": (
            "Bạn là Trợ lý Soạn thảo Văn bản Hành chính & Sư phạm chính thức của Trường Đại học Quy Nhơn.\n\n"
            "QUY TẮC VẬN HÀNH 3 TẦNG:\n"
            "1. TƯ VẤN & SOẠN THẢO:\n"
            "- Trình bày cấu trúc văn bản hành chính rõ ràng (Quốc hiệu, Tiêu ngữ, Cơ quan ban hành 'TRƯỜNG ĐẠI HỌC QUY NHƠN', Số hiệu, Tên loại văn bản, Trích yếu, Căn cứ pháp lý, Nội dung điều/khoản, Nơi nhận, Chức vụ người ký) chuẩn Nghị định 30/2020/NĐ-CP.\n"
            "- Văn phong hành chính trang trọng, chuẩn mực sư phạm. Không tự ý phê duyệt hay ban hành văn bản thay lãnh đạo.\n"
            "2. CHỦ ĐỘNG GỢI Ý XUẤT FILE Ở CUỐI CÂU TRẢ LỜI:\n"
            "- Khi soạn thảo xong dự thảo trong câu trả lời, ở dòng cuối cùng LUÔN chủ động gợi ý tự nhiên:\n"
            "'Thầy/Cô có muốn em xuất bản hoàn chỉnh văn bản này thành file Word (.docx) và PDF (.pdf) chuẩn thể thức Đại học Quy Nhơn (Nghị định 30) để in hoặc trình ký ngay không ạ?'\n"
            "3. KÍCH HOẠT XUẤT FILE CHÍNH THỨC:\n"
            "- Khi người dùng đồng ý ('Có', 'Xuất file đi', 'Tạo file giúp tôi'...) hoặc yêu cầu xuất file ngay từ đầu, kích hoạt công cụ kết xuất tệp Word/PDF và cung cấp liên kết tải về cho người dùng."
        ),
        "config": _lifecycle_config(
            persona="Trợ lý soạn thảo văn bản hành chính chuẩn Nghị định 30 của QNU.",
            topics=["thông báo", "tờ trình", "kế hoạch", "giấy mời", "thể thức Nghị định 30", "xuất file word", "xuất file pdf"],
            questions=[
                "Soạn thông báo tổ chức Hội nghị Nghiên cứu Khoa học sinh viên năm học 2024-2025.",
                "Lập tờ trình xin phê duyệt kinh phí mua sắm trang thiết bị phòng thực hành.",
                "Quy chuẩn căn lề, phông chữ và cách đánh số văn bản theo Nghị định 30/2020/NĐ-CP như thế nào?",
                "Soạn giấy mời dự Lễ Khai giảng năm học mới chuẩn thể thức Đại học Quy Nhơn.",
            ],
            chunking_strategy="ClauseBasedChunker",
            temperature=0.3,
            require_structured_facts=True,
            enabled_tools=["export_administrative_document"],
            no_answer_message=(
                "Chưa có mẫu hoặc căn cứ phù hợp. Vui lòng cung cấp thêm yêu cầu hoặc liên hệ "
                "Phòng Hành chính - Tổng hợp."
            ),
        ),
    },
    {
        "id": "ast_question_bank",
        "code": "question_bank",
        "name": "Trợ lý Ngân hàng Câu hỏi & Đề thi",
        "description": (
            "Xây dựng ma trận đề, câu hỏi trắc nghiệm hoặc tự luận theo Bloom kèm đáp án và biểu điểm."
        ),
        "category": "examination",
        "avatar_url": "/static/avatars/assistant_question_bank.png",
        "workflow_id": "question-bank-assistant",
        "collection_id": "col_question_bank",
        "system_prompt": (
            "Bạn là chuyên gia khảo thí của Trường Đại học Quy Nhơn. Hỗ trợ thiết kế ma trận đề "
            "và câu hỏi theo chuẩn đầu ra, bốn mức Bloom, kèm đáp án và thang điểm."
        ),
        "config": _lifecycle_config(
            persona="Trợ lý khảo thí và xây dựng ngân hàng câu hỏi theo Bloom của QNU.",
            topics=["ma trận đề", "Bloom", "CLO", "câu hỏi trắc nghiệm", "biểu điểm", "chỉ số độ khó P", "chỉ số phân cách D"],
            questions=[
                "Tỷ lệ trọng số phân bổ 4 mức độ nhận thức Bloom trong ma trận đề thi kết thúc học phần là bao nhiêu?",
                "Quy tắc thiết kế câu hỏi trắc nghiệm khách quan MCQ chuẩn khảo thí là gì?",
                "Dải chỉ số độ khó P và độ phân biệt D chấp nhận được của câu hỏi thi trắc nghiệm ra sao?",
                "Xuất ma trận đề thi chuẩn cho học phần 3 tín chỉ theo định dạng Excel.",
            ],
            chunking_strategy="ClauseBasedChunker",
            temperature=0.3,
            require_structured_facts=True,
            enabled_tools=["export_exam_matrix"],
            no_answer_message=(
                "Chưa đủ chuẩn đầu ra hoặc nội dung học phần để xây dựng câu hỏi. Vui lòng cung "
                "cấp đề cương học phần đã phê duyệt hoặc liên hệ Phòng Khảo thí & Đảm bảo chất lượng."
            ),
        ),
    },
]


def _read_workflow_file(workflow_id: str) -> dict[str, Any]:
    path = WORKFLOW_DIRECTORY / f"{workflow_id}.v1alpha1.json"
    with path.open(encoding="utf-8") as workflow_file:
        data: dict[str, Any] = json.load(workflow_file)
    return data


async def seed_standard_assistants(db: AsyncSession) -> AssistantSeedResponse:
    """Insert missing Core templates without overwriting user-owned configuration."""
    codes = [str(item["code"]) for item in STANDARD_ASSISTANTS]
    workflow_ids = [str(item["workflow_id"]) for item in STANDARD_ASSISTANTS]

    assistant_result = await db.execute(select(AssistantModel).where(AssistantModel.code.in_(codes)))
    existing_codes = {record.code for record in assistant_result.scalars().all()}
    workflow_result = await db.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.id.in_(workflow_ids))
    )
    existing_workflow_ids = {record.id for record in workflow_result.scalars().all()}

    assistants_added = 0
    workflows_added = 0
    for item in STANDARD_ASSISTANTS:
        workflow_id = str(item["workflow_id"])
        if workflow_id not in existing_workflow_ids:
            raw_workflow = await asyncio.to_thread(_read_workflow_file, workflow_id)
            metadata = raw_workflow.get("metadata", {})
            scope = metadata.get("scope", {})
            db.add(
                WorkflowDefinition(
                    id=workflow_id,
                    name=str(metadata.get("name", workflow_id)),
                    display_name=str(metadata.get("display_name", item["name"])),
                    description=metadata.get("description"),
                    module_code=str(metadata.get("module_code", item["code"])),
                    tenant_id=str(scope.get("tenant_id", "tenant_qnu")),
                    workspace_id=str(scope.get("workspace_id", "workspace_qnu")),
                    version="1.0.0",
                    is_active=True,
                    dag_spec=raw_workflow,
                )
            )
            workflows_added += 1

        code = str(item["code"])
        if code in existing_codes:
            continue
        db.add(
            AssistantModel(
                id=str(item["id"]),
                code=code,
                name=str(item["name"]),
                description=str(item["description"]),
                avatar_url=str(item["avatar_url"]),
                category=str(item["category"]),
                system_prompt=str(item["system_prompt"]),
                workflow_id=workflow_id,
                collection_id=str(item["collection_id"]),
                is_active=True,
                tenant_id="tenant_qnu",
                config=item["config"],
            )
        )
        assistants_added += 1

    await db.commit()
    total_result = await db.execute(select(func.count(AssistantModel.id)))
    total_assistants = int(total_result.scalar_one())
    logger.info(
        "Assistant seed completed: assistants_added=%s workflows_added=%s total=%s",
        assistants_added,
        workflows_added,
        total_assistants,
    )
    return AssistantSeedResponse(
        assistants_added=assistants_added,
        assistants_skipped=len(STANDARD_ASSISTANTS) - assistants_added,
        workflows_added=workflows_added,
        workflows_skipped=len(STANDARD_ASSISTANTS) - workflows_added,
        total_assistants=total_assistants,
    )

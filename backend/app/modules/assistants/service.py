"""Application service for persisted QNU AI Assistant administration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityAlreadyExistsError, EntityNotFoundError
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.runtime import build_runtime_profile, prepare_user_message
from app.modules.assistants.schemas import (
    AssistantBundle,
    AssistantBundleWorkflow,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantCreateRequest,
    AssistantGenerateRequest,
    AssistantGenerateResponse,
    AssistantLifecycleConfig,
    AssistantResponse,
    AssistantSeedResponse,
    AssistantTemplateResponse,
    AssistantUpdateRequest,
)
from app.modules.assistants.seeder import STANDARD_ASSISTANTS, seed_standard_assistants
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.workflows.models import WorkflowDefinition
from app.modules.workflows.schemas import WorkflowExecuteRequest
from app.modules.workflows.service import workflow_service

logger = logging.getLogger(__name__)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return unicodedata.normalize("NFC", value.strip())


def _to_response(record: AssistantModel) -> AssistantResponse:
    config = AssistantLifecycleConfig.model_validate(record.config or {})
    return AssistantResponse(
        id=record.id,
        code=record.code,
        name=record.name,
        description=record.description,
        avatar_url=record.avatar_url,
        category=record.category,
        system_prompt=record.system_prompt,
        workflow_id=record.workflow_id,
        collection_id=record.collection_id,
        is_active=record.is_active,
        tenant_id=record.tenant_id,
        sample_questions=config.sample_questions,
        config=config,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class AssistantService:
    """Manage assistants, their lifecycle policy, bundles and workflow invocations."""

    async def list_assistants(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        category: str | None = None,
        include_inactive: bool = False,
    ) -> list[AssistantResponse]:
        query = select(AssistantModel).order_by(AssistantModel.name)
        if not include_inactive:
            query = query.where(AssistantModel.is_active.is_(True))
        if category:
            query = query.where(AssistantModel.category == category)
        if search and search.strip():
            pattern = f"%{_clean_text(search).casefold()}%"
            query = query.where(
                func.lower(AssistantModel.code).like(pattern)
                | func.lower(AssistantModel.name).like(pattern)
                | func.lower(AssistantModel.description).like(pattern)
            )
        records = list((await db.execute(query)).scalars().all())
        return [_to_response(record) for record in records]

    async def get_assistant(self, db: AsyncSession, reference: str) -> AssistantResponse:
        return _to_response(await self._get_record(db, reference))

    async def create_assistant(
        self, db: AsyncSession, request: AssistantCreateRequest
    ) -> AssistantResponse:
        code = _clean_text(request.code)
        if not code:
            raise AppException("Mã trợ lý không được để trống.", code="assistant_invalid")
        existing = await db.execute(
            select(AssistantModel.id).where(func.lower(AssistantModel.code) == code.casefold())
        )
        if existing.scalar_one_or_none():
            raise EntityAlreadyExistsError(
                f"Mã trợ lý '{code}' đã tồn tại.",
                details={"assistant_code": code},
            )

        record = AssistantModel(
            code=code,
            name=_clean_text(request.name) or request.name,
            description=_clean_text(request.description) or request.description,
            avatar_url=_clean_text(request.avatar_url),
            category=_clean_text(request.category) or request.category,
            system_prompt=_clean_text(request.system_prompt) or request.system_prompt,
            workflow_id=_clean_text(request.workflow_id) or request.workflow_id,
            collection_id=_clean_text(request.collection_id) or request.collection_id,
            is_active=request.is_active,
            tenant_id=_clean_text(request.tenant_id) or request.tenant_id,
            config=request.config.model_dump(mode="json"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("Created assistant code=%s workflow=%s", record.code, record.workflow_id)
        return _to_response(record)

    async def update_assistant(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantUpdateRequest,
    ) -> AssistantResponse:
        record = await self._get_record(db, reference)
        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if field_name == "config" and value is not None:
                value = request.config.model_dump(mode="json") if request.config else None
            elif isinstance(value, str):
                value = _clean_text(value)
            setattr(record, field_name, value)
        await db.commit()
        await db.refresh(record)
        logger.info("Updated assistant code=%s", record.code)
        return _to_response(record)

    async def deactivate_assistant(self, db: AsyncSession, reference: str) -> AssistantResponse:
        record = await self._get_record(db, reference)
        record.is_active = False
        await db.commit()
        await db.refresh(record)
        logger.info("Deactivated assistant code=%s", record.code)
        return _to_response(record)

    async def seed_defaults(self, db: AsyncSession) -> AssistantSeedResponse:
        return await seed_standard_assistants(db)

    def list_templates(self) -> list[AssistantTemplateResponse]:
        return [
            AssistantTemplateResponse(
                code=str(item["code"]),
                name=str(item["name"]),
                description=str(item["description"]),
                category=str(item["category"]),
                workflow_id=str(item["workflow_id"]),
                collection_id=str(item["collection_id"]),
                system_prompt=str(item["system_prompt"]),
                config=AssistantLifecycleConfig.model_validate(item["config"]),
            )
            for item in STANDARD_ASSISTANTS
        ]

    async def export_bundle(self, db: AsyncSession, reference: str) -> AssistantBundle:
        record = await self._get_record(db, reference)
        workflow_result = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == record.workflow_id)
        )
        workflow_record = workflow_result.scalar_one_or_none()
        workflow = None
        if workflow_record:
            workflow = AssistantBundleWorkflow(
                id=workflow_record.id,
                name=workflow_record.name,
                display_name=workflow_record.display_name,
                description=workflow_record.description,
                module_code=workflow_record.module_code,
                version=workflow_record.version,
                dag_spec=workflow_record.dag_spec,
            )
        return AssistantBundle(
            exported_at=datetime.now(UTC),
            assistant=AssistantCreateRequest(
                code=record.code,
                name=record.name,
                description=record.description,
                avatar_url=record.avatar_url,
                category=record.category,
                system_prompt=record.system_prompt,
                workflow_id=record.workflow_id,
                collection_id=record.collection_id,
                is_active=record.is_active,
                tenant_id=record.tenant_id,
                config=AssistantLifecycleConfig.model_validate(record.config or {}),
            ),
            workflow=workflow,
        )

    async def import_bundle(self, db: AsyncSession, bundle: AssistantBundle) -> AssistantResponse:
        workflow = bundle.workflow
        if workflow:
            existing_workflow = await db.execute(
                select(WorkflowDefinition.id).where(WorkflowDefinition.id == workflow.id)
            )
            if not existing_workflow.scalar_one_or_none():
                db.add(
                    WorkflowDefinition(
                        id=workflow.id,
                        name=workflow.name,
                        display_name=workflow.display_name,
                        description=workflow.description,
                        module_code=workflow.module_code,
                        version=workflow.version,
                        is_active=True,
                        dag_spec=workflow.dag_spec,
                    )
                )
        return await self.create_assistant(db, bundle.assistant)

    async def chat(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AssistantChatResponse:
        assistant = await self.get_assistant(db, reference)
        if not assistant.is_active:
            raise AppException(
                f"Trợ lý '{assistant.code}' đang bị vô hiệu hóa.",
                code="assistant_inactive",
                status_code=409,
                details={"assistant_code": assistant.code},
            )
        runtime_profile = build_runtime_profile(assistant)
        sanitized_message = prepare_user_message(request.message, runtime_profile)
        workflow_request = WorkflowExecuteRequest(
            workflow_id=assistant.workflow_id,
            inputs={
                "message": sanitized_message,
                "is_approved": request.is_approved,
                "format": "docx,pdf",
            },
            tenant_id=request.tenant_id,
            conversation_id=request.conversation_id,
        )
        workflow_response = await workflow_service.execute(
            db,
            workflow_request,
            assistant_profile=runtime_profile,
            correlation_id=correlation_id,
        )
        answer = workflow_response.outputs.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            guardrails = getattr(getattr(assistant, "config", None), "guardrails", None)
            answer = getattr(guardrails, "no_answer_message", "Xin lỗi, hiện tại tôi chưa có dữ liệu chính thức để trả lời câu hỏi này.")
        citations = workflow_response.outputs.get("citations", [])
        artifacts = workflow_response.outputs.get("artifacts", [])

        sample_questions = getattr(assistant, "sample_questions", None)
        if not sample_questions:
            config = getattr(assistant, "config", None)
            if hasattr(config, "persona_scope"):
                sample_questions = getattr(config.persona_scope, "sample_questions", [])
            elif isinstance(config, dict):
                sample_questions = config.get("persona_scope", {}).get("sample_questions", [])
            else:
                sample_questions = []

        return AssistantChatResponse(
            assistant_code=assistant.code,
            assistant_name=assistant.name,
            answer=answer,
            status=str(workflow_response.outputs.get("status") or workflow_response.status),
            citations=citations if isinstance(citations, list) else [],
            suggested_questions=(sample_questions or [])[:3],
            latency_ms=workflow_response.latency_ms,
            execution_id=workflow_response.execution_id,
            artifacts=artifacts if isinstance(artifacts, list) else [],
        )

    async def chat_stream(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream assistant response token-by-token via Server-Sent Events (SSE)."""
        assistant = await self.get_assistant(db, reference)
        if not assistant.is_active:
            err_data = json.dumps({"error": f"Trợ lý '{assistant.code}' đang bị vô hiệu hóa."}, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"
            return

        yield f"event: status\ndata: {json.dumps({'stage': 'retrieving', 'message': 'Đang tìm kiếm tài liệu đối soát...'}, ensure_ascii=False)}\n\n"

        runtime_profile = build_runtime_profile(assistant)
        sanitized_message = prepare_user_message(request.message, runtime_profile)
        workflow_request = WorkflowExecuteRequest(
            workflow_id=assistant.workflow_id,
            inputs={
                "message": sanitized_message,
                "is_approved": request.is_approved,
                "format": "docx,pdf",
            },
            tenant_id=request.tenant_id,
            conversation_id=request.conversation_id,
        )

        try:
            workflow_response = await workflow_service.execute(
                db,
                workflow_request,
                assistant_profile=runtime_profile,
                correlation_id=correlation_id,
            )
        except Exception as e:
            logger.error("Workflow execution failed during chat_stream: %s", e)
            err_data = json.dumps({"error": f"Lỗi thực thi quy trình: {e}"}, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"
            return

        citations = workflow_response.outputs.get("citations", [])
        if isinstance(citations, list):
            for cite in citations:
                yield f"event: citation\ndata: {json.dumps(cite, ensure_ascii=False)}\n\n"

        artifacts = workflow_response.outputs.get("artifacts", [])
        if isinstance(artifacts, list):
            for art in artifacts:
                yield f"event: artifact\ndata: {json.dumps(art, ensure_ascii=False)}\n\n"

        answer = workflow_response.outputs.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            guardrails = getattr(getattr(assistant, "config", None), "guardrails", None)
            answer = getattr(guardrails, "no_answer_message", "Xin lỗi, hiện tại tôi chưa có dữ liệu chính thức để trả lời câu hỏi này.")

        # Stream tokens smoothly with async yield
        words = answer.split(" ")
        for idx, word in enumerate(words):
            suffix = " " if idx < len(words) - 1 else ""
            delta = word + suffix
            yield f"event: token\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.012)

        sample_questions = getattr(assistant, "sample_questions", None)
        if not sample_questions:
            config = getattr(assistant, "config", None)
            if hasattr(config, "persona_scope"):
                sample_questions = getattr(config.persona_scope, "sample_questions", [])
            elif isinstance(config, dict):
                sample_questions = config.get("persona_scope", {}).get("sample_questions", [])
            else:
                sample_questions = []

        done_payload = {
            "latency_ms": workflow_response.latency_ms,
            "suggested_questions": (sample_questions or [])[:3],
            "execution_id": workflow_response.execution_id,
            "status": "completed",
        }
        yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    async def generate_spec(
        self, db: AsyncSession, request: AssistantGenerateRequest
    ) -> AssistantGenerateResponse:
        """AI Auto-Creator: Synthesizes a complete professional assistant specification from natural language."""
        idea = _clean_text(request.idea) or request.idea.strip()
        system_architect_prompt = (
            "Bạn là Chuyên gia Thiết kế Trợ lý AI (Senior AI Agent Architect) của Trường Đại học Quy Nhơn (QNU).\n"
            "Nhiệm vụ: Phân tích ý tưởng mong muốn của cán bộ và sinh ra một bản đặc tả hoàn chỉnh cho Trợ lý AI chuyên trách.\n\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. Phản hồi CHỈ BẰNG một JSON Object hợp lệ (không kèm bất kỳ văn bản giải thích thừa nào).\n"
            "2. JSON có đúng các trường sau:\n"
            "{\n"
            '  "name": "Tên trợ lý chuẩn phong thái học thuật ĐH Quy Nhơn (tối đa 60 ký tự)",\n'
            '  "description": "Mô tả ngắn gọn 1-2 câu về nhiệm vụ chính",\n'
            '  "category": "Một trong các mã: admissions | academic | resources | administration | examination | general",\n'
            '  "system_prompt": "Toàn văn chỉ thị hệ thống chi tiết 5 phần: 1. Vai trò chính thức QNU; 2. Phạm vi & Giới hạn; 3. Căn cứ văn bản RAG (Zero Hallucination); 4. Tác phong sư phạm & Xưng hô; 5. No-answer hotline 0256.3846.156",\n'
            '  "sample_questions": ["Câu hỏi thực tế 1 mà sinh viên/giảng viên hay hỏi?", "Câu hỏi thực tế 2?", "Câu hỏi thực tế 3?"],\n'
            '  "temperature": 0.2,\n'
            '  "no_answer_message": "Thông điệp cứu cánh khi không có tài liệu đối soát chính thức (kèm Hotline 0256.3846.156)",\n'
            '  "suggested_workflow_id": "Mã workflow phù hợp: admissions-assistant | regulations-assistant | library-assistant | drafting-assistant | question-bank-assistant"\n'
            "}"
        )

        user_content = f"Ý tưởng mong muốn của cán bộ: '{idea}'."
        if request.category_hint:
            user_content += f"\nGợi ý phân loại lĩnh vực: '{request.category_hint}'."

        messages = [
            ChatMessage(role="system", content=system_architect_prompt),
            ChatMessage(role="user", content=user_content),
        ]
        gen_req = LLMGenerateRequest(
            messages=messages,
            temperature=0.3,
            max_tokens=2500,
        )

        try:
            llm_resp = await modelops_service.generate(db, gen_req)
            parsed = _extract_json(llm_resp.content)
            if parsed and isinstance(parsed, dict) and "name" in parsed and "system_prompt" in parsed:
                category = str(parsed.get("category") or request.category_hint or "academic").strip()
                if category not in ["admissions", "academic", "resources", "administration", "examination", "general"]:
                    category = "academic"

                raw_questions = parsed.get("sample_questions", [])
                questions = (
                    [str(q).strip() for q in raw_questions if isinstance(q, str) and q.strip()]
                    if isinstance(raw_questions, list)
                    else []
                )
                if not questions:
                    questions = [
                        f"Quy trình thực hiện đối với {idea[:30]}?",
                        "Các văn bản quy chế và hồ sơ cần chuẩn bị?",
                        "Thời hạn giải quyết và đơn vị phụ trách trực tiếp?",
                    ]

                temp = parsed.get("temperature", 0.2)
                try:
                    temp_float = float(temp)
                except (ValueError, TypeError):
                    temp_float = 0.2

                return AssistantGenerateResponse(
                    name=str(parsed.get("name", f"Trợ lý Chuyên trách {idea[:30]}")).strip(),
                    description=str(parsed.get("description", f"Trợ lý AI hỗ trợ {idea[:100]}")).strip(),
                    category=category,
                    system_prompt=str(parsed.get("system_prompt")).strip(),
                    sample_questions=questions[:4],
                    temperature=max(0.0, min(1.0, temp_float)),
                    no_answer_message=str(
                        parsed.get(
                            "no_answer_message",
                            "Thông tin này chưa có trong văn bản chính thức của Trường Đại học Quy Nhơn. Vui lòng liên hệ Hotline: 0256.3846.156 để được hướng dẫn chi tiết.",
                        )
                    ).strip(),
                    suggested_workflow_id=str(
                        parsed.get("suggested_workflow_id", "regulations-assistant")
                    ).strip(),
                )
        except Exception as exc:
            logger.warning(
                "ModelOps generate spec failed or returned unparseable output (%s). Using fallback template generator.",
                exc,
            )

        return _build_fallback_spec(idea, request.category_hint)

    async def _get_record(self, db: AsyncSession, reference: str) -> AssistantModel:
        normalized_reference = _clean_text(reference) or reference
        result = await db.execute(
            select(AssistantModel).where(
                or_(
                    AssistantModel.id == normalized_reference,
                    func.lower(AssistantModel.code) == normalized_reference.casefold(),
                )
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise EntityNotFoundError(
                f"Trợ lý AI '{reference}' không tồn tại.",
                details={"assistant_reference": reference},
            )
        return record


def _extract_json(text: str) -> dict[str, object] | None:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        pass
    return None


def _build_fallback_spec(idea: str, category_hint: str | None = None) -> AssistantGenerateResponse:
    lower = idea.lower()
    if any(k in lower for k in ["tuyển sinh", "xét tuyển", "ngành học", "điểm chuẩn"]):
        name = "Trợ lý Tuyển sinh & Hướng nghiệp Số"
        category = category_hint or "admissions"
        workflow_id = "admissions-assistant"
        questions = [
            "Phương thức xét tuyển đại học năm nay gồm những gì?",
            "Mức học phí và chính sách học bổng của trường như thế nào?",
            "Thời gian và thủ tục nộp hồ sơ xét tuyển?",
        ]
    elif any(k in lower for k in ["văn bản", "soạn thảo", "nghị định 30", "công văn", "tờ trình"]):
        name = "Trợ lý Soạn thảo Văn bản Hành chính NĐ 30"
        category = category_hint or "administration"
        workflow_id = "drafting-assistant"
        questions = [
            "Hướng dẫn thể thức trình bày Tờ trình theo Nghị định 30?",
            "Mẫu Thông báo kết luận cuộc họp chuẩn Đại học Quy Nhơn?",
            "Quy tắc ghi số hiệu và trích yếu văn bản hành chính?",
        ]
    elif any(k in lower for k in ["đề thi", "khảo thí", "bloom", "câu hỏi", "ma trận"]):
        name = "Trợ lý Khảo thí & Ngân hàng Đề thi Bloom"
        category = category_hint or "examination"
        workflow_id = "question-bank-assistant"
        questions = [
            "Cách phân loại câu hỏi thi theo 4 mức độ nhận thức Bloom?",
            "Xuất ma trận đề thi trắc nghiệm kết hợp tự luận?",
            "Quy trình thẩm định và bảo mật ngân hàng câu hỏi thi?",
        ]
    elif any(k in lower for k in ["thư viện", "sách", "giáo trình", "tài liệu", "học liệu"]):
        name = "Trợ lý Thư viện & Học liệu Số QNU"
        category = category_hint or "resources"
        workflow_id = "library-assistant"
        questions = [
            "Cách tra cứu giáo trình và tài liệu tham khảo theo mã DDC?",
            "Hướng dẫn truy cập cơ sở dữ liệu bài báo khoa học trực tuyến?",
            "Quy định về thời hạn mượn và gia hạn sách thư viện?",
        ]
    elif any(k in lower for k in ["ký túc xá", "nội trú", "tiền phòng", "ktx"]):
        name = "Trợ lý Quản lý Ký túc xá & Đời sống Sinh viên"
        category = category_hint or "resources"
        workflow_id = "regulations-assistant"
        questions = [
            "Thủ tục đăng ký nội trú Ký túc xá cho tân sinh viên?",
            "Mức phí lưu trú Ký túc xá và các chế độ ưu tiên, miễn giảm?",
            "Nội quy sinh hoạt và quy định an ninh trật tự Ký túc xá?",
        ]
    else:
        name = f"Trợ lý Chuyên trách {idea[:35].strip()}"
        category = category_hint or "academic"
        workflow_id = "regulations-assistant"
        questions = [
            f"Quy trình thực hiện đối với {idea[:30]}?",
            "Các văn bản quy định và thủ tục cần chuẩn bị?",
            "Thời hạn giải quyết và đơn vị phụ trách trực tiếp?",
        ]

    system_prompt = (
        f"Bạn là {name}, Trợ lý Trí tuệ Nhân tạo chính thức thuộc Trường Đại học Quy Nhơn (QNU).\n\n"
        f"1. VAI TRÒ & PHẠM VI:\n"
        f"- Nhiệm vụ cốt lõi: Hỗ trợ cán bộ, giảng viên và người học về: {idea}.\n"
        f"- Giới hạn phạm vi: Chỉ giải đáp các nội dung thuộc chuyên môn được giao. Tuyệt đối từ chối lịch sự và điều hướng các chủ đề nằm ngoài thẩm quyền.\n\n"
        f"2. NGUYÊN TẮC CĂN CỨ TRI THỨC (ZERO HALLUCINATION):\n"
        f"- Mọi câu trả lời bắt buộc phải dựa 100% trên các văn bản, quy chế và thông báo chính thức của Trường Đại học Quy Nhơn.\n"
        f"- Luôn chỉ rõ căn cứ trích dẫn: Tên văn bản, Điều/Khoản và số trang (nếu có).\n"
        f"- Tuyệt đối KHÔNG suy diễn số liệu, không đưa ra thông tin giả định.\n\n"
        f"3. PHONG THÁI & QUY TẮC ỨNG XỬ:\n"
        f"- Sử dụng tiếng Việt chuẩn mực, xưng hô 'Tôi/Em' và 'Bạn/Sinh viên/Quý Thầy Cô'.\n"
        f"- Trình bày mạch lạc, sử dụng gạch đầu dòng hoặc bảng biểu rõ ràng khi có số liệu.\n\n"
        f"4. CHÍNH SÁCH KHI THIẾU CĂN CỨ (NO-ANSWER POLICY):\n"
        f"- Khi thông tin chưa có trong tài liệu chính thức, thông báo rõ ràng và hướng dẫn người dùng liên hệ:\n"
        f"  * Đơn vị phụ trách chuyên môn Trường Đại học Quy Nhơn.\n"
        f"  * Hotline hỗ trợ chính thức: 0256.3846.156 | Email: hotro@qnu.edu.vn | Cổng TT: https://qnu.edu.vn"
    )

    return AssistantGenerateResponse(
        name=name,
        description=f"Trợ lý AI chuyên trách hỗ trợ: {idea[:150]}.",
        category=category,
        system_prompt=system_prompt,
        sample_questions=questions,
        temperature=0.2,
        no_answer_message="Thông tin này chưa có trong văn bản chính thức của Trường Đại học Quy Nhơn. Vui lòng liên hệ Hotline: 0256.3846.156 để được hướng dẫn chi tiết.",
        suggested_workflow_id=workflow_id,
    )


assistant_service = AssistantService()


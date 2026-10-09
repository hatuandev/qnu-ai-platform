"""Helper script to update revision_service.py with strict tenant & document checks."""
from pathlib import Path

path = Path("app/modules/documents/revision_service.py")
text = path.read_text(encoding="utf-8")

# 1. Thêm _to_response_dto
helper_code = '''    @staticmethod
    def _to_response_dto(rev: DocumentRevision) -> DocumentRevisionResponse:
        provenance = dict(rev.parse_provenance or {})
        review_decision = provenance.get("review_decision") or {}
        human_reviews = provenance.get("human_reviews") or []
        notes = review_decision.get("notes")
        if not notes and human_reviews:
            notes = human_reviews[-1].get("notes")
        dto = DocumentRevisionResponse.model_validate(rev)
        dto.review_notes = notes
        return dto
'''

target_promote = '    @staticmethod\n    def _promote_revision_to_document('
if "_to_response_dto" not in text:
    assert target_promote in text, "target_promote not found"
    text = text.replace(target_promote, helper_code + "\n" + target_promote, 1)

# 2. Khóa RepositoryDocument trong create_new_revision
target_create = '''        stmt = select(RepositoryDocument).where(
            RepositoryDocument.id == doc_id, RepositoryDocument.is_active.is_(True)
        )'''
repl_create = '''        stmt = (
            select(RepositoryDocument)
            .where(RepositoryDocument.id == doc_id, RepositoryDocument.is_active.is_(True))
            .with_for_update()
        )'''
if target_create in text:
    text = text.replace(target_create, repl_create, 1)

# 3. Sửa process_revision để nhận document_id và actor, kiểm tra cả 2
target_proc_sig = '''    async def process_revision(
        self,
        db: AsyncSession,
        revision_id: str,
        ocr_engine: str | None = None,
    ) -> DocumentRevision:'''

repl_proc_sig = '''    async def process_revision(
        self,
        db: AsyncSession,
        revision_id: str,
        document_id: str | None = None,
        actor: Any | None = None,
        ocr_engine: str | None = None,
    ) -> DocumentRevision:'''

if target_proc_sig in text:
    text = text.replace(target_proc_sig, repl_proc_sig, 1)

target_proc_fetch = '''        stmt = select(DocumentRevision).where(DocumentRevision.id == revision_id)
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")

        if rev.status not in ("queued", "failed"):
            raise AppException(
                f"Không thể xử lý lại revision ở trạng thái '{rev.status}'.",
                code="REVISION_NOT_PROCESSABLE",
                status_code=409,
            )

        doc_stmt = select(RepositoryDocument).where(RepositoryDocument.id == rev.document_id)
        doc = (await db.execute(doc_stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(f"Tài liệu gốc cho revision '{revision_id}' không tồn tại.")'''

repl_proc_fetch = '''        # Validate document and tenant scope first
        target_doc_id = document_id
        if target_doc_id:
            doc_stmt = select(RepositoryDocument).where(RepositoryDocument.id == target_doc_id)
            if actor and getattr(actor, "tenant_id", None):
                doc_stmt = doc_stmt.where(RepositoryDocument.tenant_id == actor.tenant_id)
            doc = (await db.execute(doc_stmt)).scalar_one_or_none()
            if not doc:
                raise EntityNotFoundError(f"Tài liệu '{target_doc_id}' không tồn tại trong phạm vi được cấp quyền.")

            rev_stmt = select(DocumentRevision).where(
                DocumentRevision.id == revision_id,
                DocumentRevision.document_id == target_doc_id,
            )
            rev = (await db.execute(rev_stmt)).scalar_one_or_none()
            if not rev:
                raise EntityNotFoundError(
                    f"Bản sửa đổi '{revision_id}' không tồn tại trong tài liệu '{target_doc_id}'."
                )
        else:
            rev_stmt = select(DocumentRevision).where(DocumentRevision.id == revision_id)
            rev = (await db.execute(rev_stmt)).scalar_one_or_none()
            if not rev:
                raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")

            doc_stmt = select(RepositoryDocument).where(RepositoryDocument.id == rev.document_id)
            if actor and getattr(actor, "tenant_id", None):
                doc_stmt = doc_stmt.where(RepositoryDocument.tenant_id == actor.tenant_id)
            doc = (await db.execute(doc_stmt)).scalar_one_or_none()
            if not doc:
                raise EntityNotFoundError(f"Tài liệu cho revision '{revision_id}' không tồn tại trong phạm vi được cấp quyền.")

        if rev.status not in ("queued", "failed"):
            raise AppException(
                f"Không thể xử lý lại revision ở trạng thái '{rev.status}'.",
                code="REVISION_NOT_PROCESSABLE",
                status_code=409,
            )'''

if target_proc_fetch in text:
    text = text.replace(target_proc_fetch, repl_proc_fetch, 1)

# 4. Sửa list_document_revisions
target_list = '''    async def list_document_revisions(
        self,
        db: AsyncSession,
        document_id: str,
    ) -> list[DocumentRevisionListItem]:
        """List all revisions of a document sorted by revision_no descending."""
        stmt = (
            select(DocumentRevision)
            .where(DocumentRevision.document_id == document_id)
            .order_by(DocumentRevision.revision_no.desc())
        )
        revisions = (await db.execute(stmt)).scalars().all()
        return [DocumentRevisionListItem.model_validate(r) for r in revisions]'''

repl_list = '''    async def list_document_revisions(
        self,
        db: AsyncSession,
        document_id: str,
        actor: Any | None = None,
    ) -> list[DocumentRevisionListItem]:
        """List all revisions of a document sorted by revision_no descending."""
        doc_stmt = select(RepositoryDocument.id).where(RepositoryDocument.id == document_id)
        if actor and getattr(actor, "tenant_id", None):
            doc_stmt = doc_stmt.where(RepositoryDocument.tenant_id == actor.tenant_id)
        if not (await db.execute(doc_stmt)).scalar_one_or_none():
            raise EntityNotFoundError(f"Tài liệu '{document_id}' không tồn tại.")

        stmt = (
            select(DocumentRevision)
            .where(DocumentRevision.document_id == document_id)
            .order_by(DocumentRevision.revision_no.desc())
        )
        revisions = (await db.execute(stmt)).scalars().all()
        return [DocumentRevisionListItem.model_validate(r) for r in revisions]'''

if target_list in text:
    text = text.replace(target_list, repl_list, 1)

# 5. Sửa get_document_revision
target_get = '''    async def get_document_revision(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
    ) -> DocumentRevisionResponse:
        """Get full details of a specific revision."""
        stmt = select(DocumentRevision).where(
            DocumentRevision.id == revision_id,
            DocumentRevision.document_id == document_id,
        )
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(
                f"Bản sửa đổi '{revision_id}' không tồn tại trong tài liệu '{document_id}'."
            )
        return DocumentRevisionResponse.model_validate(rev)'''

repl_get = '''    async def get_document_revision(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        actor: Any | None = None,
    ) -> DocumentRevisionResponse:
        """Get full details of a specific revision."""
        doc_stmt = select(RepositoryDocument.id).where(RepositoryDocument.id == document_id)
        if actor and getattr(actor, "tenant_id", None):
            doc_stmt = doc_stmt.where(RepositoryDocument.tenant_id == actor.tenant_id)
        if not (await db.execute(doc_stmt)).scalar_one_or_none():
            raise EntityNotFoundError(f"Tài liệu '{document_id}' không tồn tại.")

        stmt = select(DocumentRevision).where(
            DocumentRevision.id == revision_id,
            DocumentRevision.document_id == document_id,
        )
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(
                f"Bản sửa đổi '{revision_id}' không tồn tại trong tài liệu '{document_id}'."
            )
        return self._to_response_dto(rev)'''

if target_get in text:
    text = text.replace(target_get, repl_get, 1)

# 6. Sửa update_revision_content
target_update = '''    async def update_revision_content(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        body: ReviewRevisionContentRequest,
    ) -> DocumentRevisionResponse:
        """Allow reviewers to edit canonical markdown during review phase."""
        stmt = (
            select(DocumentRevision)
            .where(
                DocumentRevision.id == revision_id,
                DocumentRevision.document_id == document_id,
            )
            .with_for_update()
        )
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")'''

repl_update = '''    async def update_revision_content(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        body: ReviewRevisionContentRequest,
        actor: Any | None = None,
    ) -> DocumentRevisionResponse:
        """Allow reviewers to edit canonical markdown during review phase."""
        doc_stmt = select(RepositoryDocument.id).where(RepositoryDocument.id == document_id)
        if actor and getattr(actor, "tenant_id", None):
            doc_stmt = doc_stmt.where(RepositoryDocument.tenant_id == actor.tenant_id)
        if not (await db.execute(doc_stmt)).scalar_one_or_none():
            raise EntityNotFoundError(f"Tài liệu '{document_id}' không tồn tại.")

        stmt = (
            select(DocumentRevision)
            .where(
                DocumentRevision.id == revision_id,
                DocumentRevision.document_id == document_id,
            )
            .with_for_update()
        )
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")'''

if target_update in text:
    text = text.replace(target_update, repl_update, 1)

target_up_ret = '''        await db.commit()
        await db.refresh(rev)
        return DocumentRevisionResponse.model_validate(rev)'''

repl_up_ret = '''        await db.commit()
        await db.refresh(rev)
        return self._to_response_dto(rev)'''

if target_up_ret in text:
    text = text.replace(target_up_ret, repl_up_ret, 1)

# 7. Sửa submit_revision_review
target_submit = '''    async def submit_revision_review(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        body: SubmitRevisionReviewRequest,
    ) -> DocumentRevisionResponse:
        """Finalize review decision (approve -> ready, or reject -> review_required)."""
        stmt = (
            select(DocumentRevision)
            .where(
                DocumentRevision.id == revision_id,
                DocumentRevision.document_id == document_id,
            )
            .with_for_update()
        )
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")'''

repl_submit = '''    async def submit_revision_review(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        body: SubmitRevisionReviewRequest,
        actor: Any | None = None,
    ) -> DocumentRevisionResponse:
        """Finalize review decision (approve -> ready, or reject -> review_required)."""
        doc_stmt = select(RepositoryDocument.id).where(RepositoryDocument.id == document_id)
        if actor and getattr(actor, "tenant_id", None):
            doc_stmt = doc_stmt.where(RepositoryDocument.tenant_id == actor.tenant_id)
        if not (await db.execute(doc_stmt)).scalar_one_or_none():
            raise EntityNotFoundError(f"Tài liệu '{document_id}' không tồn tại.")

        stmt = (
            select(DocumentRevision)
            .where(
                DocumentRevision.id == revision_id,
                DocumentRevision.document_id == document_id,
            )
            .with_for_update()
        )
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")'''

if target_submit in text:
    text = text.replace(target_submit, repl_submit, 1)

path.write_text(text, encoding="utf-8")
print("Successfully updated revision_service.py")

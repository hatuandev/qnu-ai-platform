"""Database seeder for default official QNU knowledge collections, documents, and facts."""

from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeFact,
)
from app.modules.knowledge.seed_data_admissions import (
    ADMISSIONS_CHUNKS,
    ADMISSIONS_COLLECTION_ID,
    ADMISSIONS_DOCUMENT_ID,
    ADMISSIONS_FACTS,
    ADMISSIONS_FILENAME,
    ADMISSIONS_TITLE,
)
from app.modules.knowledge.seed_data_nd30 import (
    DECREE_30_CHUNKS,
    DECREE_30_COLLECTION_ID,
    DECREE_30_DOCUMENT_ID,
    DECREE_30_FACTS,
    DECREE_30_FILENAME,
    DECREE_30_TITLE,
)
from app.modules.knowledge.seed_data_regulations import (
    REGULATIONS_CHUNKS,
    REGULATIONS_COLLECTION_ID,
    REGULATIONS_DOCUMENT_ID,
    REGULATIONS_FACTS,
    REGULATIONS_FILENAME,
    REGULATIONS_TITLE,
)

logger = logging.getLogger(__name__)


async def seed_regulations_knowledge(db: AsyncSession) -> dict[str, int]:
    """Seed official QNU Academic Regulations into col_regulations if not present."""
    # 1. Ensure col_regulations collection exists
    col_stmt = select(KnowledgeCollection).where(KnowledgeCollection.id == REGULATIONS_COLLECTION_ID)
    col = (await db.execute(col_stmt)).scalar_one_or_none()
    if not col:
        col = KnowledgeCollection(
            id=REGULATIONS_COLLECTION_ID,
            name="Kho Tri Thức Quy Chế Học Vụ",
            module_code="regulations",
            description="Quy chế đào tạo đại học chính quy theo hệ thống tín chỉ, thang điểm và chuẩn đầu ra QNU.",
            tenant_id="tenant_qnu",
            workspace_id="workspace_academic",
            collection_metadata={
                "chunking_strategy": "ClauseBasedChunker",
                "ocr_profile": "Docling",
                "document_count": 1,
                "chunk_count": len(REGULATIONS_CHUNKS),
            },
        )
        db.add(col)
        await db.flush()

    # 2. Check if Regulations document already exists
    doc_stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == REGULATIONS_DOCUMENT_ID)
    existing_doc = (await db.execute(doc_stmt)).scalar_one_or_none()

    if existing_doc:
        logger.info("QNU Academic Regulations document already present in col_regulations.")
        return {"documents_seeded": 0, "chunks_seeded": 0, "facts_seeded": 0}

    # 3. Create KnowledgeDocument
    file_content = "\n\n".join(c["content"] for c in REGULATIONS_CHUNKS)
    file_hash = hashlib.sha256(file_content.encode("utf-8")).hexdigest()

    doc = KnowledgeDocument(
        id=REGULATIONS_DOCUMENT_ID,
        collection_id=REGULATIONS_COLLECTION_ID,
        document_type_code="quy_che",
        title=REGULATIONS_TITLE,
        file_name=REGULATIONS_FILENAME,
        file_type="pdf",
        file_size_bytes=len(file_content.encode("utf-8")),
        file_hash=file_hash,
        storage_path=f"uploads/{REGULATIONS_COLLECTION_ID}/{REGULATIONS_FILENAME}",
        doc_metadata={
            "page_count": 6,
            "ocr_method": "ClauseBasedChunker",
            "chunk_count": len(REGULATIONS_CHUNKS),
            "table_count": 4,
            "decision_no": "1688/QĐ-ĐHQN",
        },
        status="completed",
        is_active=True,
    )
    db.add(doc)
    await db.flush()

    # 4. Create KnowledgeChunks
    chunk_objs: list[KnowledgeChunk] = []
    for c in REGULATIONS_CHUNKS:
        c_hash = hashlib.sha256(c["content"].encode("utf-8")).hexdigest()
        chunk_obj = KnowledgeChunk(
            id=c["id"],
            document_id=REGULATIONS_DOCUMENT_ID,
            collection_id=REGULATIONS_COLLECTION_ID,
            chunk_index=c["chunk_index"],
            content=c["content"],
            chunk_hash=c_hash,
            token_count=len(c["content"].split()),
            section=c["title"],
            page_number=c["metadata"].get("page", 1),
            chunk_metadata=c["metadata"],
        )
        chunk_objs.append(chunk_obj)
        db.add(chunk_obj)

    # 5. Create KnowledgeFacts
    fact_objs: list[KnowledgeFact] = []
    for f in REGULATIONS_FACTS:
        fact_obj = KnowledgeFact(
            id=f["fact_key"],
            collection_id=REGULATIONS_COLLECTION_ID,
            document_id=REGULATIONS_DOCUMENT_ID,
            entity_name=f["entity_name"],
            entity_type=f["category"],
            attribute_name=f["attribute_name"],
            attribute_value=f["value"],
            confidence=1.0,
            raw_data=f.get("fact_metadata", {}),
        )
        fact_objs.append(fact_obj)
        db.add(fact_obj)

    await db.commit()
    logger.info(
        "Successfully seeded QNU Regulations: 1 document, %d chunks, %d facts into %s",
        len(chunk_objs),
        len(fact_objs),
        REGULATIONS_COLLECTION_ID,
    )

    # 6. Index into Qdrant
    try:
        from app.modules.rag.vector_indexer import vector_indexer

        await vector_indexer.index_chunks(
            collection_id=REGULATIONS_COLLECTION_ID,
            chunks=[
                {
                    "id": c.id,
                    "point_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{REGULATIONS_COLLECTION_ID}:{c.id}")),
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "content": c.content,
                    "section": c.section,
                    "page_number": c.page_number,
                    "metadata": c.chunk_metadata,
                }
                for c in chunk_objs
            ],
        )
        logger.info("Indexed QNU Regulations chunks into Qdrant collection %s", REGULATIONS_COLLECTION_ID)
    except Exception as exc:
        logger.warning("Vector indexing to Qdrant for col_regulations skipped or failed (graceful): %s", exc)

    return {
        "documents_seeded": 1,
        "chunks_seeded": len(chunk_objs),
        "facts_seeded": len(fact_objs),
    }


async def seed_drafting_knowledge(db: AsyncSession) -> dict[str, int]:
    """Seed official Decree 30/2020/ND-CP into col_drafting if not present."""
    # 1. Ensure col_drafting collection exists
    col_stmt = select(KnowledgeCollection).where(KnowledgeCollection.id == DECREE_30_COLLECTION_ID)
    col = (await db.execute(col_stmt)).scalar_one_or_none()
    if not col:
        col = KnowledgeCollection(
            id=DECREE_30_COLLECTION_ID,
            name="Kho Mẫu Văn Bản Chuẩn NĐ 30",
            module_code="drafting",
            description="Mẫu văn bản hành chính, quyết định, tờ trình, quy cách căn lề theo NĐ 30/2020.",
            tenant_id="tenant_qnu",
            workspace_id="workspace_research",
            collection_metadata={
                "chunking_strategy": "ClauseBasedChunker",
                "ocr_profile": "Docling",
                "document_count": 1,
                "chunk_count": len(DECREE_30_CHUNKS),
            },
        )
        db.add(col)
        await db.flush()

    # 2. Check if Decree 30 document already exists
    doc_stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == DECREE_30_DOCUMENT_ID)
    existing_doc = (await db.execute(doc_stmt)).scalar_one_or_none()

    if existing_doc:
        logger.info("Decree 30/2020/ND-CP document already present in col_drafting.")
        return {"documents_seeded": 0, "chunks_seeded": 0, "facts_seeded": 0}

    # 3. Create KnowledgeDocument
    file_content_mock = "\n\n".join(c["content"] for c in DECREE_30_CHUNKS)
    file_hash = hashlib.sha256(file_content_mock.encode("utf-8")).hexdigest()

    doc = KnowledgeDocument(
        id=DECREE_30_DOCUMENT_ID,
        collection_id=DECREE_30_COLLECTION_ID,
        document_type_code="quy_dinh",
        title=DECREE_30_TITLE,
        file_name=DECREE_30_FILENAME,
        file_type="pdf",
        file_size_bytes=len(file_content_mock.encode("utf-8")),
        file_hash=file_hash,
        storage_path=f"uploads/{DECREE_30_COLLECTION_ID}/{DECREE_30_FILENAME}",
        doc_metadata={
            "page_count": 11,
            "ocr_method": "PyMuPDF + Tesseract OCR",
            "chunk_count": len(DECREE_30_CHUNKS),
            "table_count": 2,
        },
        status="processed",
        is_active=True,
    )
    db.add(doc)
    await db.flush()

    # 4. Create KnowledgeChunks
    chunk_objs: list[KnowledgeChunk] = []
    for c in DECREE_30_CHUNKS:
        c_hash = hashlib.sha256(c["content"].encode("utf-8")).hexdigest()
        chunk_obj = KnowledgeChunk(
            id=c["id"],
            document_id=DECREE_30_DOCUMENT_ID,
            collection_id=DECREE_30_COLLECTION_ID,
            chunk_index=c["chunk_index"],
            content=c["content"],
            chunk_hash=c_hash,
            token_count=len(c["content"].split()),
            section=c["title"],
            page_number=c["metadata"].get("page", 1),
            chunk_metadata=c["metadata"],
        )
        chunk_objs.append(chunk_obj)
        db.add(chunk_obj)

    # 5. Create KnowledgeFacts
    fact_objs: list[KnowledgeFact] = []
    for f in DECREE_30_FACTS:
        fact_obj = KnowledgeFact(
            collection_id=DECREE_30_COLLECTION_ID,
            document_id=DECREE_30_DOCUMENT_ID,
            entity_name=f["entity_name"],
            entity_type="legal_norm",
            attribute_name=f["attribute_name"],
            attribute_value=f["attribute_value"],
            confidence=1.0,
            raw_data={"source": DECREE_30_TITLE},
        )
        fact_objs.append(fact_obj)
        db.add(fact_obj)

    await db.commit()
    logger.info(
        "Successfully seeded Decree 30/2020/ND-CP: 1 document, %d chunks, %d facts into %s",
        len(chunk_objs),
        len(fact_objs),
        DECREE_30_COLLECTION_ID,
    )

    # 6. Optional: Index into Qdrant if online
    try:
        from app.modules.rag.vector_indexer import vector_indexer

        await vector_indexer.index_chunks(
            collection_id=DECREE_30_COLLECTION_ID,
            chunks=[
                {
                    "id": c.id,
                    "point_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{DECREE_30_COLLECTION_ID}:{c.id}")),
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "content": c.content,
                    "section": c.section,
                    "page_number": c.page_number,
                    "metadata": c.chunk_metadata,
                }
                for c in chunk_objs
            ],
        )
        logger.info("Indexed Decree 30 chunks into Qdrant vector index.")
    except Exception as exc:
        logger.warning("Vector indexing to Qdrant skipped or failed (graceful): %s", exc)

    return {
        "documents_seeded": 1,
        "chunks_seeded": len(chunk_objs),
        "facts_seeded": len(fact_objs),
    }


async def seed_admissions_knowledge(db: AsyncSession) -> dict[str, int]:
    """Seed official QNU Admissions Knowledge into col_admissions if not present."""
    # 1. Ensure col_admissions collection exists
    col_stmt = select(KnowledgeCollection).where(KnowledgeCollection.id == ADMISSIONS_COLLECTION_ID)
    col = (await db.execute(col_stmt)).scalar_one_or_none()
    if not col:
        col = KnowledgeCollection(
            id=ADMISSIONS_COLLECTION_ID,
            name="Kho Tri Thức Đề Án Tuyển Sinh",
            module_code="admissions",
            description="Đề án và thông báo tuyển sinh đại học chính quy, phương thức xét tuyển, chỉ tiêu, điểm chuẩn, học phí và ký túc xá QNU.",
            tenant_id="tenant_qnu",
            workspace_id="workspace_admissions",
            collection_metadata={
                "chunking_strategy": "ClauseBasedChunker",
                "ocr_profile": "Docling",
                "document_count": 1,
                "chunk_count": len(ADMISSIONS_CHUNKS),
            },
        )
        db.add(col)
        await db.flush()

    # 2. Check if Admissions document already exists
    doc_stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == ADMISSIONS_DOCUMENT_ID)
    existing_doc = (await db.execute(doc_stmt)).scalar_one_or_none()

    if existing_doc:
        logger.info("QNU Admissions document already present in col_admissions.")
        return {"documents_seeded": 0, "chunks_seeded": 0, "facts_seeded": 0}

    # 3. Create KnowledgeDocument
    file_content = "\n\n".join(c["content"] for c in ADMISSIONS_CHUNKS)
    file_hash = hashlib.sha256(file_content.encode("utf-8")).hexdigest()

    doc = KnowledgeDocument(
        id=ADMISSIONS_DOCUMENT_ID,
        collection_id=ADMISSIONS_COLLECTION_ID,
        document_type_code="thong_bao",
        title=ADMISSIONS_TITLE,
        file_name=ADMISSIONS_FILENAME,
        file_type="pdf",
        file_size_bytes=len(file_content.encode("utf-8")),
        file_hash=file_hash,
        storage_path=f"uploads/{ADMISSIONS_COLLECTION_ID}/{ADMISSIONS_FILENAME}",
        doc_metadata={
            "page_count": 7,
            "ocr_method": "ClauseBasedChunker",
            "chunk_count": len(ADMISSIONS_CHUNKS),
            "table_count": 5,
            "year": 2024,
        },
        status="completed",
        is_active=True,
    )
    db.add(doc)
    await db.flush()

    # 4. Create KnowledgeChunks
    chunk_objs: list[KnowledgeChunk] = []
    for c in ADMISSIONS_CHUNKS:
        c_hash = hashlib.sha256(c["content"].encode("utf-8")).hexdigest()
        chunk_obj = KnowledgeChunk(
            id=c["id"],
            document_id=ADMISSIONS_DOCUMENT_ID,
            collection_id=ADMISSIONS_COLLECTION_ID,
            chunk_index=c["chunk_index"],
            content=c["content"],
            chunk_hash=c_hash,
            token_count=len(c["content"].split()),
            section=c["title"],
            page_number=c["metadata"].get("page", 1),
            chunk_metadata=c["metadata"],
        )
        chunk_objs.append(chunk_obj)
        db.add(chunk_obj)

    # 5. Create KnowledgeFacts
    fact_objs: list[KnowledgeFact] = []
    for f in ADMISSIONS_FACTS:
        fact_obj = KnowledgeFact(
            id=f["fact_key"],
            collection_id=ADMISSIONS_COLLECTION_ID,
            document_id=ADMISSIONS_DOCUMENT_ID,
            entity_name=f["entity_name"],
            entity_type=f["category"],
            attribute_name=f["attribute_name"],
            attribute_value=f["value"],
            confidence=1.0,
            raw_data=f.get("fact_metadata", {}),
        )
        fact_objs.append(fact_obj)
        db.add(fact_obj)

    await db.commit()
    logger.info(
        "Successfully seeded QNU Admissions: 1 document, %d chunks, %d facts into %s",
        len(chunk_objs),
        len(fact_objs),
        ADMISSIONS_COLLECTION_ID,
    )

    # 6. Index into Qdrant
    try:
        from app.modules.rag.vector_indexer import vector_indexer

        await vector_indexer.index_chunks(
            collection_id=ADMISSIONS_COLLECTION_ID,
            chunks=[
                {
                    "id": c.id,
                    "point_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ADMISSIONS_COLLECTION_ID}:{c.id}")),
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "content": c.content,
                    "section": c.section,
                    "page_number": c.page_number,
                    "metadata": c.chunk_metadata,
                }
                for c in chunk_objs
            ],
        )
        logger.info("Indexed QNU Admissions chunks into Qdrant collection %s", ADMISSIONS_COLLECTION_ID)
    except Exception as exc:
        logger.warning("Vector indexing to Qdrant for col_admissions skipped or failed (graceful): %s", exc)

    return {
        "documents_seeded": 1,
        "chunks_seeded": len(chunk_objs),
        "facts_seeded": len(fact_objs),
    }


async def seed_default_knowledge(db: AsyncSession) -> dict[str, int]:
    """Seed all official QNU default knowledge collections (Decree 30, Regulations, and Admissions)."""
    res_drafting = await seed_drafting_knowledge(db)
    res_regulations = await seed_regulations_knowledge(db)
    res_admissions = await seed_admissions_knowledge(db)

    return {
        "documents_seeded": (
            res_drafting["documents_seeded"]
            + res_regulations["documents_seeded"]
            + res_admissions["documents_seeded"]
        ),
        "chunks_seeded": (
            res_drafting["chunks_seeded"]
            + res_regulations["chunks_seeded"]
            + res_admissions["chunks_seeded"]
        ),
        "facts_seeded": (
            res_drafting["facts_seeded"]
            + res_regulations["facts_seeded"]
            + res_admissions["facts_seeded"]
        ),
    }



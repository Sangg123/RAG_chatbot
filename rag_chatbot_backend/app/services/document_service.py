import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Document, DocumentChunk, KnowledgeBase


settings = get_settings()


async def create_pending_document(
    db: AsyncSession,
    knowledge_base_id: uuid.UUID,
    file: UploadFile,
) -> Document:
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    # TC14: Chặn upload file rỗng (0 byte)
    max_bytes = (
        settings.max_upload_mb * 1024 * 1024
        if settings.max_upload_mb is not None and settings.max_upload_mb > 0
        else None
    )
    declared_size = getattr(file, "size", None)
    if max_bytes is not None and declared_size is not None and declared_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File vượt quá giới hạn {settings.max_upload_mb} MB.",
        )

    # Read at most max_bytes + 1 so a huge upload cannot exhaust RAM before
    # the size check (Render free has only 512 MB). Without MAX_UPLOAD_MB,
    # keep the old local behavior and read the whole file.
    content = await file.read(max_bytes + 1 if max_bytes is not None else -1)
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File rỗng (0 byte), không thể upload."
        )
    if max_bytes is not None and len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File vượt quá giới hạn {settings.max_upload_mb} MB.",
        )
    # Reset con trỏ file về đầu để shutil.copyfileobj đọc lại được
    await file.seek(0)

    document = Document(
        knowledge_base_id=knowledge_base_id,
        filename=file.filename or "uploaded_file",
        file_type=Path(file.filename or "").suffix.lstrip(".").lower() or None,
        upload_status="PENDING",
    )
    db.add(document)
    await db.flush()

    base_storage = Path(settings.storage_dir)
    target_dir = base_storage / str(knowledge_base_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{document.id}_{document.filename}"

    with target_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    document.file_url = str(target_path)
    await db.commit()
    await db.refresh(document)
    return document


async def get_document(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> Document | None:
    stmt = select(Document).where(Document.id == document_id)
    return await db.scalar(stmt)


async def list_documents_by_kb(
    db: AsyncSession,
    knowledge_base_id: uuid.UUID,
) -> list[Document]:
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    result = await db.execute(
        select(Document)
        .where(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


async def delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> None:
    document = await get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    await db.delete(document)
    await db.commit()

    if document.file_url:
        path = Path(document.file_url)
        if path.exists():
            path.unlink()

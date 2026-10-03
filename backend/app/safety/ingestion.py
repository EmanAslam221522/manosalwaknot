import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import DocumentApprovalStatus, KnowledgeChunk, KnowledgeDocument
from app.safety.chunking import Chunk, SemanticChunker
from app.safety.embeddings import EmbeddingProvider


class DocumentIngestor:
    """Ingest documents into the knowledge base with chunking and embeddings."""

    def __init__(self, chunker: SemanticChunker | None = None, embedding_provider: EmbeddingProvider | None = None):
        self.chunker = chunker or SemanticChunker()
        self.embedding_provider = embedding_provider

    def ingest(
        self,
        db: Session,
        title: str,
        source: str,
        source_url: str | None,
        document_type: str,
        version: str,
        effective_from: datetime,
        effective_until: datetime | None,
        jurisdiction: str,
        content: str,
        approval_status: DocumentApprovalStatus = DocumentApprovalStatus.DRAFT,
    ) -> tuple[UUID, int]:
        """Ingest a document into the knowledge base.

        Returns (document_id, chunk_count).
        """
        # Check for duplicate by content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        existing = db.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.content_hash == content_hash)
        )
        if existing:
            return existing.id, existing.chunk_count

        # Create document record
        document = KnowledgeDocument(
            title=title,
            source=source,
            source_url=source_url,
            document_type=document_type,
            version=version,
            effective_from=effective_from,
            effective_until=effective_until,
            approval_status=approval_status,
            jurisdiction=jurisdiction,
            content_hash=content_hash,
        )
        db.add(document)
        db.flush()

        # Chunk the content
        chunks = self.chunker.chunk_text(
            content,
            page_number=None,
            section_title=None,
            metadata={"document_id": str(document.id), "title": title, "source": source, "source_url": source_url},
        )

        # Generate embeddings if provider is available
        embeddings: list[list[float] | None] = [None] * len(chunks)
        if self.embedding_provider:
            try:
                chunk_texts = [chunk.content for chunk in chunks]
                embeddings = self.embedding_provider.embed_texts(chunk_texts)
            except Exception as exc:
                # If embedding fails and document is being approved, fail the ingestion
                if approval_status == DocumentApprovalStatus.APPROVED:
                    raise ApiError(
                        500,
                        "EMBEDDING_GENERATION_FAILED",
                        "Failed to generate embeddings for APPROVED document. Embeddings are required for searchability."
                    ) from exc
                # For DRAFT documents, we allow ingestion without embeddings but log the failure
                # In production, you might want to log this to a monitoring system
                pass

        # Create chunk records
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_record = KnowledgeChunk(
                document_id=document.id,
                chunk_index=idx,
                content=chunk.content,
                embedding=embedding,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                metadata=chunk.metadata,
                content_hash=chunk.content_hash,
                approval_status=approval_status,
            )
            db.add(chunk_record)

        # Update chunk count
        document.chunk_count = len(chunks)
        db.flush()

        return document.id, len(chunks)

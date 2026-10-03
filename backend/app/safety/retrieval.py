from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import DocumentApprovalStatus, DocumentType, KnowledgeChunk, KnowledgeDocument
from app.safety.embeddings import EmbeddingProvider


@dataclass
class RetrievedChunk:
    id: str
    document_id: str
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str | None
    metadata: dict[str, Any]
    document_title: str
    document_source: str
    document_source_url: str | None
    document_type: str
    jurisdiction: str
    similarity: float


class KnowledgeRetriever:
    """Retrieve relevant knowledge chunks using vector similarity."""

    def __init__(self, embedding_provider: EmbeddingProvider, top_k: int | None = None, similarity_threshold: float | None = None):
        settings = get_settings()
        self.embedding_provider = embedding_provider
        self.top_k = top_k or settings.rag_top_k
        self.similarity_threshold = similarity_threshold or settings.rag_similarity_threshold

    def retrieve(
        self,
        db: Session,
        query: str,
        jurisdiction: str | None = None,
        document_type: str | None = None,
        include_historical: bool = False,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks for a query.

        Only retrieves APPROVED documents that are currently effective.
        """
        # Validate document_type if provided
        if document_type is not None:
            try:
                DocumentType(document_type)
            except ValueError:
                raise ApiError(422, "INVALID_DOCUMENT_TYPE", f"Invalid document_type: {document_type}")

        # Validate jurisdiction length
        if jurisdiction is not None and len(jurisdiction) > 80:
            raise ApiError(422, "INVALID_JURISDICTION", "Jurisdiction must be 80 characters or less")

        # Generate query embedding
        query_embedding = self.embedding_provider.embed_text(query)

        # Build base query with filters
        query_builder = (
            select(
                KnowledgeChunk.id,
                KnowledgeChunk.document_id,
                KnowledgeChunk.chunk_index,
                KnowledgeChunk.content,
                KnowledgeChunk.embedding,
                KnowledgeChunk.page_number,
                KnowledgeChunk.section_title,
                KnowledgeChunk.metadata,
                KnowledgeDocument.title.label("document_title"),
                KnowledgeDocument.source.label("document_source"),
                KnowledgeDocument.source_url.label("document_source_url"),
                KnowledgeDocument.document_type.label("document_type"),
                KnowledgeDocument.jurisdiction.label("jurisdiction"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeChunk.approval_status == DocumentApprovalStatus.APPROVED)
            .where(KnowledgeDocument.approval_status == DocumentApprovalStatus.APPROVED)
            .where(KnowledgeDocument.effective_from <= datetime.now(UTC))
        )

        # Filter out expired documents unless historical is requested
        if not include_historical:
            query_builder = query_builder.where(
                (KnowledgeDocument.effective_until.is_(None)) | (KnowledgeDocument.effective_until > datetime.now(UTC))
            )

        # Apply jurisdiction filter if specified
        if jurisdiction:
            query_builder = query_builder.where(KnowledgeDocument.jurisdiction == jurisdiction)

        # Apply document type filter if specified
        if document_type:
            query_builder = query_builder.where(KnowledgeDocument.document_type == document_type)

        # Get all matching chunks
        result = db.execute(query_builder).all()

        # Calculate similarity and sort
        chunks_with_similarity = []
        for row in result:
            chunk_embedding = row.embedding if hasattr(row, "embedding") else None
            if chunk_embedding:
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
            else:
                similarity = 0.0

            chunks_with_similarity.append(
                RetrievedChunk(
                    id=str(row.id),
                    document_id=str(row.document_id),
                    chunk_index=row.chunk_index,
                    content=row.content,
                    page_number=row.page_number,
                    section_title=row.section_title,
                    metadata=row.metadata or {},
                    document_title=row.document_title,
                    document_source=row.document_source,
                    document_source_url=row.document_source_url,
                    document_type=row.document_type.value if hasattr(row.document_type, "value") else str(row.document_type),
                    jurisdiction=row.jurisdiction,
                    similarity=similarity,
                )
            )

        # Sort by similarity and return top_k
        chunks_with_similarity.sort(key=lambda x: x.similarity, reverse=True)
        return chunks_with_similarity[: self.top_k]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

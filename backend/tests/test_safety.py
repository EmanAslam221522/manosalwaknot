"""Tests for RAG-based food safety assistant."""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import DocumentApprovalStatus, DocumentType, KnowledgeChunk, KnowledgeDocument
from app.safety.ingestion import DocumentIngestor
from app.safety import (
    CitationValidator,
    DocumentIngestor,
    EvidenceValidator,
    KnowledgeRetriever,
    SafetyAnswerGenerator,
    SemanticChunker,
)
from app.safety.chunking import Chunk
from app.safety.retrieval import RetrievedChunk


class TestSemanticChunker:
    """Test semantic chunking."""

    def test_basic_chunking(self):
        chunker = SemanticChunker(max_chunk_size=200, overlap=20)
        text = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all(chunk.content.strip() for chunk in chunks)
        assert all(chunk.content_hash for chunk in chunks)

    def test_chunk_preserves_metadata(self):
        chunker = SemanticChunker()
        text = "Test content."
        metadata = {"test_key": "test_value"}

        chunks = chunker.chunk_text(text, page_number=5, section_title="Test Section", metadata=metadata)

        assert len(chunks) == 1
        assert chunks[0].page_number == 5
        assert chunks[0].section_title == "Test Section"
        assert chunks[0].metadata == metadata

    def test_large_text_splitting(self):
        chunker = SemanticChunker(max_chunk_size=100)
        text = " ".join(["word"] * 200)
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 1
        assert all(len(chunk.content) <= chunker.max_chunk_size + 50 for chunk in chunks)


class TestEvidenceValidator:
    """Test evidence validation."""

    def test_sufficient_evidence(self):
        validator = EvidenceValidator(min_evidence_threshold=2)
        chunks = [
            RetrievedChunk(
                id="1",
                document_id="doc1",
                chunk_index=0,
                content="Test content",
                page_number=1,
                section_title="Section 1",
                metadata={},
                document_title="Test Doc",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.8,
            ),
            RetrievedChunk(
                id="2",
                document_id="doc1",
                chunk_index=1,
                content="More content",
                page_number=2,
                section_title="Section 2",
                metadata={},
                document_title="Test Doc",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.7,
            ),
        ]

        is_sufficient, reason = validator.validate(chunks, "Test question")
        assert is_sufficient is True
        assert "sufficient" in reason.lower()

    def test_insufficient_evidence_count(self):
        validator = EvidenceValidator(min_evidence_threshold=2)
        chunks = [
            RetrievedChunk(
                id="1",
                document_id="doc1",
                chunk_index=0,
                content="Test content",
                page_number=1,
                section_title="Section 1",
                metadata={},
                document_title="Test Doc",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.8,
            )
        ]

        is_sufficient, reason = validator.validate(chunks, "Test question")
        assert is_sufficient is False
        assert "insufficient" in reason.lower()

    def test_no_evidence(self):
        validator = EvidenceValidator()
        chunks = []

        is_sufficient, reason = validator.validate(chunks, "Test question")
        assert is_sufficient is False
        assert "no relevant evidence" in reason.lower()

    def test_low_similarity_filtered(self):
        validator = EvidenceValidator(min_evidence_threshold=2)
        chunks = [
            RetrievedChunk(
                id="1",
                document_id="doc1",
                chunk_index=0,
                content="Test content",
                page_number=1,
                section_title="Section 1",
                metadata={},
                document_title="Test Doc",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.2,  # Below threshold
            ),
            RetrievedChunk(
                id="2",
                document_id="doc1",
                chunk_index=1,
                content="More content",
                page_number=2,
                section_title="Section 2",
                metadata={},
                document_title="Test Doc",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.1,  # Below threshold
            ),
        ]

        is_sufficient, reason = validator.validate(chunks, "Test question")
        assert is_sufficient is False


class TestCitationValidator:
    """Test citation validation."""

    def test_valid_citations(self):
        validator = CitationValidator()
        chunks = [
            RetrievedChunk(
                id="chunk-1",
                document_id="doc1",
                chunk_index=0,
                content="Content 1",
                page_number=1,
                section_title="Section 1",
                metadata={},
                document_title="Doc 1",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.8,
            ),
            RetrievedChunk(
                id="chunk-2",
                document_id="doc1",
                chunk_index=1,
                content="Content 2",
                page_number=2,
                section_title="Section 2",
                metadata={},
                document_title="Doc 1",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.7,
            ),
        ]

        valid_ids, invalid_ids = validator.validate(chunks, ["chunk-1", "chunk-2"])
        assert set(valid_ids) == {"chunk-1", "chunk-2"}
        assert len(invalid_ids) == 0

    def test_invalid_citations(self):
        validator = CitationValidator()
        chunks = [
            RetrievedChunk(
                id="chunk-1",
                document_id="doc1",
                chunk_index=0,
                content="Content 1",
                page_number=1,
                section_title="Section 1",
                metadata={},
                document_title="Doc 1",
                document_source="Test",
                document_source_url=None,
                document_type="GUIDANCE",
                jurisdiction="Pakistan",
                similarity=0.8,
            )
        ]

        valid_ids, invalid_ids = validator.validate(chunks, ["chunk-1", "fake-chunk"])
        assert valid_ids == ["chunk-1"]
        assert invalid_ids == ["fake-chunk"]

    def test_empty_citations(self):
        validator = CitationValidator()
        chunks = []

        valid_ids, invalid_ids = validator.validate(chunks, [])
        assert valid_ids == []
        assert invalid_ids == []


class TestSafetyAnswerGenerator:
    """Test safety answer generation."""

    def test_high_risk_detection(self):
        generator = SafetyAnswerGenerator()

        assert generator._is_high_risk_question("I think I have food poisoning")
        assert generator._is_high_risk_question("This food is contaminated")
        assert generator._is_high_risk_question("Is this toxic?")
        assert not generator._is_high_risk_question("How should I store food?")
        assert not generator._is_high_risk_question("What are the five keys?")

    def test_insufficient_evidence_message(self):
        generator = SafetyAnswerGenerator()
        message = generator._get_insufficient_evidence_message("No chunks found", "en")
        assert "insufficient" in message.lower() or "no" in message.lower()

    def test_escalation_message(self):
        generator = SafetyAnswerGenerator()
        message = generator._get_escalation_message("I'm sick", "en")
        assert "escalation" in message.lower() or "expert" in message.lower() or "contact" in message.lower()


class TestDocumentIngestion:
    """Test document ingestion (requires database)."""

    def test_duplicate_detection(self, db: Session):
        """Test that duplicate documents are not ingested."""
        ingestor = DocumentIngestor(embedding_provider=None)

        content = "Test content for duplicate detection."

        # First ingestion
        doc_id_1, chunk_count_1 = ingestor.ingest(
            db=db,
            title="Test Doc",
            source="Test",
            source_url=None,
            document_type=DocumentType.POLICY,
            version="1.0",
            effective_from=datetime.now(UTC),
            effective_until=None,
            jurisdiction="Pakistan",
            content=content,
            approval_status=DocumentApprovalStatus.DRAFT,
        )

        # Second ingestion with same content
        doc_id_2, chunk_count_2 = ingestor.ingest(
            db=db,
            title="Different Title",
            source="Different Source",
            source_url=None,
            document_type=DocumentType.POLICY,
            version="2.0",
            effective_from=datetime.now(UTC),
            effective_until=None,
            jurisdiction="Pakistan",
            content=content,
            approval_status=DocumentApprovalStatus.DRAFT,
        )

        # Should return the same document ID
        assert doc_id_1 == doc_id_2
        assert chunk_count_1 == chunk_count_2

        db.rollback()

    def test_cascade_delete_document_deletes_chunks(self, db: Session):
        """Test that deleting a document cascades to delete its chunks."""
        from sqlalchemy import delete

        ingestor = DocumentIngestor(embedding_provider=None)

        doc_id, chunk_count = ingestor.ingest(
            db=db,
            title="Test Doc for Cascade",
            source="Test",
            source_url=None,
            document_type=DocumentType.POLICY,
            version="1.0",
            effective_from=datetime.now(UTC),
            effective_until=None,
            jurisdiction="Pakistan",
            content="Test content for cascade delete test.",
            approval_status=DocumentApprovalStatus.DRAFT,
        )

        # Verify chunks exist
        from app.models import KnowledgeChunk
        chunks_before = db.scalar(
            select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id)
        )
        assert chunks_before is not None

        # Delete document
        db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        db.commit()

        # Verify chunks are deleted
        chunks_after = db.scalar(
            select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id)
        )
        assert chunks_after is None

    def test_embedding_failure_for_approved_document(self, db: Session):
        """Test that embedding failure prevents APPROVED document ingestion."""
        from app.safety.embeddings import OpenAIEmbeddingProvider
        from app.core.errors import ApiError

        # Create a mock embedding provider that always fails
        class FailingEmbeddingProvider(OpenAIEmbeddingProvider):
            def embed_texts(self, texts: list[str]) -> list[list[float]]:
                raise Exception("Embedding generation failed")

        ingestor = DocumentIngestor(embedding_provider=FailingEmbeddingProvider("test_key", "http://test"))

        try:
            ingestor.ingest(
                db=db,
                title="Test Doc",
                source="Test",
                source_url=None,
                document_type=DocumentType.POLICY,
                version="1.0",
                effective_from=datetime.now(UTC),
                effective_until=None,
                jurisdiction="Pakistan",
                content="Test content for embedding failure test.",
                approval_status=DocumentApprovalStatus.APPROVED,
            )
            assert False, "Should have raised ApiError for embedding failure"
        except ApiError as e:
            assert e.code == "EMBEDDING_GENERATION_FAILED"
        finally:
            db.rollback()

    def test_embedding_failure_allowed_for_draft_document(self, db: Session):
        """Test that embedding failure is allowed for DRAFT documents."""
        from app.safety.embeddings import OpenAIEmbeddingProvider

        # Create a mock embedding provider that always fails
        class FailingEmbeddingProvider(OpenAIEmbeddingProvider):
            def embed_texts(self, texts: list[str]) -> list[list[float]]:
                raise Exception("Embedding generation failed")

        ingestor = DocumentIngestor(embedding_provider=FailingEmbeddingProvider("test_key", "http://test"))

        # Should succeed for DRAFT
        doc_id, chunk_count = ingestor.ingest(
            db=db,
            title="Test Doc",
            source="Test",
            source_url=None,
            document_type=DocumentType.POLICY,
            version="1.0",
            effective_from=datetime.now(UTC),
            effective_until=None,
            jurisdiction="Pakistan",
            content="Test content for embedding failure test.",
            approval_status=DocumentApprovalStatus.DRAFT,
        )

        assert doc_id is not None
        assert chunk_count > 0
        db.rollback()


@pytest.fixture
def db():
    """Database fixture for tests."""
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

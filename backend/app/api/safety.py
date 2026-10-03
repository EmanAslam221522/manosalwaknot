from fastapi import APIRouter, Depends, Request

from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.rate_limit import enforce_rate_limit
from app.domain import audit
from app.models import Role, User
from app.safety import (
    Citation,
    DocumentIngestRequest,
    DocumentIngestResponse,
    KnowledgeRetriever,
    SafetyAnswerGenerator,
    SafetyQuestionRequest,
    SafetyQuestionResponse,
    get_embedding_provider,
)
from app.safety.ingestion import DocumentIngestor

router = APIRouter(prefix="/ai/safety", tags=["Food Safety RAG"])


@router.post("/ask", response_model=SafetyQuestionResponse)
def ask_safety_question(
    payload: SafetyQuestionRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> SafetyQuestionResponse:
    """Ask a food-safety question using the RAG-based knowledge base."""
    enforce_rate_limit(request, "safety_question", 20, 3600, str(user.id))

    try:
        # Initialize services
        embedding_provider = get_embedding_provider()
        settings = get_settings()
        retriever = KnowledgeRetriever(
            embedding_provider=embedding_provider,
            top_k=settings.rag_top_k,
            similarity_threshold=settings.rag_similarity_threshold,
        )
        answer_generator = SafetyAnswerGenerator(
            min_evidence_threshold=settings.rag_min_evidence,
            similarity_threshold=settings.rag_similarity_threshold,
        )

        # Retrieve relevant evidence
        chunks = retriever.retrieve(db, payload.question, jurisdiction=payload.jurisdiction)

        # Generate grounded answer
        answer, citations_data, support_status, requires_escalation = answer_generator.generate(
            question=payload.question,
            chunks=chunks,
            language=payload.language,
        )

        # Convert citation data to proper format
        citations = [Citation(**citation) for citation in citations_data]

        return SafetyQuestionResponse(
            answer=answer,
            citations=citations,
            support_status=support_status,
            requires_escalation=requires_escalation,
        )
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(503, "SAFETY_ASSISTANT_UNAVAILABLE", "Food safety assistant is temporarily unavailable.") from exc


@router.post("/ingest", response_model=DocumentIngestResponse)
def ingest_document(
    payload: DocumentIngestRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DocumentIngestResponse:
    """Ingest a document into the knowledge base (admin only)."""
    enforce_rate_limit(request, "document_ingest", 5, 3600, str(user.id))

    # Check authorization - only admins can ingest documents
    user_roles = {entry.role for entry in user.roles}
    if Role.ADMIN not in user_roles and Role.SUPER_ADMIN not in user_roles:
        raise ApiError(403, "NOT_AUTHORIZED", "Only administrators can ingest documents into the knowledge base.")

    request_id = request.state.request_id

    try:
        # Initialize services
        embedding_provider = get_embedding_provider()
        chunker = DocumentIngestor(embedding_provider=embedding_provider)

        # Ingest document
        document_id, chunk_count = chunker.ingest(
            db=db,
            title=payload.title,
            source=payload.source,
            source_url=payload.source_url,
            document_type=payload.document_type,
            version=payload.version,
            effective_from=payload.effective_from,
            effective_until=payload.effective_until,
            jurisdiction=payload.jurisdiction,
            content=payload.content,
            approval_status=payload.approval_status,
        )

        # Audit log
        audit(
            db,
            user.id,
            "knowledge_document.ingested",
            "knowledge_document",
            document_id,
            request_id,
            {
                "title": payload.title,
                "source": payload.source,
                "document_type": payload.document_type.value,
                "version": payload.version,
                "jurisdiction": payload.jurisdiction,
                "approval_status": payload.approval_status.value,
                "chunk_count": chunk_count,
            },
        )

        db.commit()

        return DocumentIngestResponse(document_id=document_id, chunk_count=chunk_count, status="ingested")
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        raise ApiError(500, "INGESTION_FAILED", "Document ingestion failed. Please check the document format and try again.") from exc

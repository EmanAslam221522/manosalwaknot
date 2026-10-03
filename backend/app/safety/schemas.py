from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.config import get_settings
from app.models import DocumentApprovalStatus, DocumentType


class Citation(BaseModel):
    document_id: UUID
    title: str
    page: int | None
    section: str | None
    source: str
    source_url: str | None


class SafetyQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    language: Literal["en", "ur", "ps", "hno", "pa"] = "en"
    jurisdiction: str = Field(default="general", max_length=80)


class SafetyQuestionResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    support_status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE", "ESCALATION_REQUIRED"]
    requires_escalation: bool


class DocumentIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    source: str = Field(min_length=1, max_length=120)
    source_url: str | None = None
    document_type: DocumentType
    version: str = Field(min_length=1, max_length=40)
    effective_from: datetime
    effective_until: datetime | None = None
    jurisdiction: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1)
    approval_status: DocumentApprovalStatus = DocumentApprovalStatus.DRAFT

    @model_validator(mode="after")
    def validate_content(self) -> "DocumentIngestRequest":
        settings = get_settings()
        content_stripped = self.content.strip()
        if not content_stripped:
            raise ValueError("Content cannot be empty or whitespace-only")
        if len(content_stripped) < settings.min_document_size:
            raise ValueError(f"Content must be at least {settings.min_document_size} characters")
        if len(self.content) > settings.max_document_size:
            raise ValueError(f"Content cannot exceed {settings.max_document_size} characters")
        if self.effective_from > datetime.now():
            raise ValueError("effective_from cannot be in the future")
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from")
        return self


class DocumentIngestResponse(BaseModel):
    document_id: UUID
    chunk_count: int
    status: str

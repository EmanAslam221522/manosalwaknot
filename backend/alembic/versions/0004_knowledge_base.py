"""Add knowledge base for RAG-based food safety assistant.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create document_approval_status enum
    op.execute("CREATE TYPE document_approval_status AS ENUM ('DRAFT', 'APPROVED', 'ARCHIVED', 'REJECTED')")
    # Create document_type enum
    op.execute("CREATE TYPE document_type AS ENUM ('REGULATION', 'GUIDANCE', 'POLICY', 'MANUAL', 'SOP')")

    # Create knowledge_documents table
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("document_type", sa.Enum(name="document_type", create_type=False), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approval_status",
            sa.Enum(name="document_approval_status", create_type=False),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("jurisdiction", sa.String(length=80), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_docs_approval", "knowledge_documents", ["approval_status", "jurisdiction"])
    op.create_index("ix_knowledge_docs_effective", "knowledge_documents", ["effective_from", "effective_until"])
    op.create_index("ix_knowledge_docs_source", "knowledge_documents", ["source", "document_type"])
    op.create_index("ix_knowledge_documents_source", "knowledge_documents", ["source"])
    op.create_index("ix_knowledge_documents_document_type", "knowledge_documents", ["document_type"])
    op.create_index("ix_knowledge_documents_approval_status", "knowledge_documents", ["approval_status"])
    op.create_index("ix_knowledge_documents_jurisdiction", "knowledge_documents", ["jurisdiction"])
    op.create_index("ix_knowledge_documents_effective_from", "knowledge_documents", ["effective_from"])
    op.create_index("ix_knowledge_documents_content_hash", "knowledge_documents", ["content_hash"], unique=True)

    # Create knowledge_chunks table
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.String(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=300), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "approval_status",
            sa.Enum(name="document_approval_status", create_type=False),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Convert embedding column to VECTOR type if pgvector is available
    connection = op.get_bind()
    vector_available = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
    )
    if vector_available:
        op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE VECTOR(1536) USING embedding::vector")
    op.create_index("ix_knowledge_chunks_document", "knowledge_chunks", ["document_id", "chunk_index"])
    op.create_index("ix_knowledge_chunks_approval", "knowledge_chunks", ["approval_status"])
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_approval_status", "knowledge_chunks", ["approval_status"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_approval_status", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_approval", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_knowledge_documents_content_hash", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_effective_from", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_jurisdiction", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_approval_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_document_type", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_source", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_docs_source", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_docs_effective", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_docs_approval", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.execute("DROP TYPE IF EXISTS document_type")
    op.execute("DROP TYPE IF EXISTS document_approval_status")

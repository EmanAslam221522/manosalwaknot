"""Add vector index and content_hash index for efficient similarity search and duplicate detection.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    vector_available = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
    )
    if vector_available:
        # Create IVFFlat index for efficient similarity search
        # IVFFlat is suitable for production and works with PostgreSQL 12+
        op.execute(
            "CREATE INDEX ix_knowledge_chunks_embedding_ivfflat "
            "ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )

    # Create index on content_hash for faster duplicate detection
    op.create_index("ix_knowledge_chunks_content_hash", "knowledge_chunks", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_content_hash", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_embedding_ivfflat", table_name="knowledge_chunks")

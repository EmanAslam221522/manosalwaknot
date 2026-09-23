"""Initial production schema.

Revision ID: 0001
"""
from collections.abc import Sequence

from alembic import op

from app.core.database import Base
from app import models  # noqa: F401

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind())
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_food_location_gist ON food_listings "
        "USING GIST (ST_SetSRID(ST_MakePoint(longitude::double precision, latitude::double precision), 4326)::geography)"
    )


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

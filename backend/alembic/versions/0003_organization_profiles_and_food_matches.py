"""Add organization profiles and food match recommendations.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "organization_profiles" not in tables:
        op.create_table(
            "organization_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_type", sa.String(length=32), nullable=False),
            sa.Column("daily_capacity", sa.Integer(), nullable=False),
            sa.Column("people_served", sa.Integer(), nullable=False),
            sa.Column("accepted_category_ids", sa.JSON(), nullable=False),
            sa.Column("pickup_window_start", sa.Time(), nullable=False),
            sa.Column("pickup_window_end", sa.Time(), nullable=False),
            sa.Column("max_distance_km", sa.Numeric(precision=6, scale=2), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.CheckConstraint("daily_capacity > 0", name=op.f("ck_organization_profiles_daily_capacity_positive")),
            sa.CheckConstraint("people_served >= 0", name=op.f("ck_organization_profiles_people_served_nonnegative")),
            sa.CheckConstraint("max_distance_km > 0", name=op.f("ck_organization_profiles_max_distance_positive")),
            sa.ForeignKeyConstraint(
                ["location_id"],
                ["locations.id"],
                name=op.f("fk_organization_profiles_location_id_locations"),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name=op.f("fk_organization_profiles_user_id_users"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_profiles")),
            sa.UniqueConstraint("user_id", name=op.f("uq_organization_profiles_user_id")),
        )
        op.create_index(
            op.f("ix_organization_profiles_location_id"),
            "organization_profiles",
            ["location_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_organization_profiles_user_id"),
            "organization_profiles",
            ["user_id"],
            unique=True,
        )
    if "food_matches" not in tables:
        op.create_table(
            "food_matches",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("food_listing_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("accepted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("declined_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("quantity_snapshot", sa.Integer(), nullable=False),
            sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False),
            sa.Column("score_breakdown", sa.JSON(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.CheckConstraint("quantity_snapshot > 0", name=op.f("ck_food_matches_quantity_snapshot_positive")),
            sa.CheckConstraint("score >= 0 AND score <= 100", name=op.f("ck_food_matches_score_range")),
            sa.ForeignKeyConstraint(
                ["accepted_by_id"],
                ["users.id"],
                name=op.f("fk_food_matches_accepted_by_id_users"),
            ),
            sa.ForeignKeyConstraint(
                ["declined_by_id"],
                ["users.id"],
                name=op.f("fk_food_matches_declined_by_id_users"),
            ),
            sa.ForeignKeyConstraint(
                ["food_listing_id"],
                ["food_listings.id"],
                name=op.f("fk_food_matches_food_listing_id_food_listings"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["users.id"],
                name=op.f("fk_food_matches_organization_id_users"),
            ),
            sa.ForeignKeyConstraint(
                ["organization_profile_id"],
                ["organization_profiles.id"],
                name=op.f("fk_food_matches_organization_profile_id_organization_profiles"),
            ),
            sa.ForeignKeyConstraint(
                ["reservation_id"],
                ["reservations.id"],
                name=op.f("fk_food_matches_reservation_id_reservations"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_food_matches")),
            sa.UniqueConstraint(
                "food_listing_id",
                "organization_id",
                name=op.f("uq_food_matches_food_listing_id_organization_id"),
            ),
            sa.UniqueConstraint("reservation_id", name=op.f("uq_food_matches_reservation_id")),
        )
        op.create_index(
            op.f("ix_food_matches_food_listing_id"),
            "food_matches",
            ["food_listing_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_food_matches_organization_id"),
            "food_matches",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_food_matches_organization_profile_id"),
            "food_matches",
            ["organization_profile_id"],
            unique=False,
        )
        op.create_index(op.f("ix_food_matches_status"), "food_matches", ["status"], unique=False)
        op.create_index(
            "ix_food_matches_listing_status",
            "food_matches",
            ["food_listing_id", "status"],
            unique=False,
        )
        op.create_index(
            "ix_food_matches_organization_status",
            "food_matches",
            ["organization_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "food_matches" in tables:
        op.drop_index("ix_food_matches_organization_status", table_name="food_matches")
        op.drop_index("ix_food_matches_listing_status", table_name="food_matches")
        op.drop_index(op.f("ix_food_matches_status"), table_name="food_matches")
        op.drop_index(
            op.f("ix_food_matches_organization_profile_id"),
            table_name="food_matches",
        )
        op.drop_index(op.f("ix_food_matches_organization_id"), table_name="food_matches")
        op.drop_index(op.f("ix_food_matches_food_listing_id"), table_name="food_matches")
        op.drop_table("food_matches")
    if "organization_profiles" in tables:
        op.drop_index(op.f("ix_organization_profiles_user_id"), table_name="organization_profiles")
        op.drop_index(op.f("ix_organization_profiles_location_id"), table_name="organization_profiles")
        op.drop_table("organization_profiles")

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, VECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class Role(str, enum.Enum):
    RECIPIENT = "RECIPIENT"
    FOOD_PROVIDER = "FOOD_PROVIDER"
    ORGANIZATION = "ORGANIZATION"
    VOLUNTEER = "VOLUNTEER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class FoodStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RESERVED = "RESERVED"
    READY = "READY"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FLAGGED = "FLAGGED"


class ReservationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    READY = "READY"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    NO_SHOW = "NO_SHOW"
    DISPUTED = "DISPUTED"


class DeliveryStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ACCEPTED = "ACCEPTED"
    EN_ROUTE_TO_PICKUP = "EN_ROUTE_TO_PICKUP"
    ARRIVED_AT_PICKUP = "ARRIVED_AT_PICKUP"
    PICKED_UP = "PICKED_UP"
    EN_ROUTE_TO_DROPOFF = "EN_ROUTE_TO_DROPOFF"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class VerificationType(str, enum.Enum):
    PROVIDER = "PROVIDER"
    ORGANIZATION = "ORGANIZATION"
    VOLUNTEER = "VOLUNTEER"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"


class OrganizationType(str, enum.Enum):
    NGO = "NGO"
    HOSTEL = "HOSTEL"
    UNIVERSITY = "UNIVERSITY"
    COMMUNITY_KITCHEN = "COMMUNITY_KITCHEN"


class FoodMatchStatus(str, enum.Enum):
    RECOMMENDED = "RECOMMENDED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class ReportStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class DocumentApprovalStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"


class DocumentType(str, enum.Enum):
    REGULATION = "REGULATION"
    GUIDANCE = "GUIDANCE"
    POLICY = "POLICY"
    MANUAL = "MANUAL"
    SOP = "SOP"


class UUIDTimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class User(UUIDTimestampMixin, Base):
    __tablename__ = "users"

    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    area: Mapped[str | None] = mapped_column(String(160), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list[UserRole]] = relationship(cascade="all, delete-orphan", back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=32))
    user: Mapped[User] = relationship(back_populates="roles")


class Session(UUIDTimestampMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"))


class OtpChallenge(UUIDTimestampMixin, Base):
    __tablename__ = "otp_challenges"

    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Location(UUIDTimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="latitude_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="longitude_range"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    area: Mapped[str] = mapped_column(String(160), index=True)
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    pickup_instructions: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FoodCategory(UUIDTimestampMixin, Base):
    __tablename__ = "food_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FoodListing(UUIDTimestampMixin, Base):
    __tablename__ = "food_listings"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("servings_total > 0", name="servings_total_positive"),
        CheckConstraint("servings_available >= 0", name="servings_available_nonnegative"),
        CheckConstraint("servings_available <= servings_total", name="servings_available_total"),
        CheckConstraint("price >= 0", name="price_nonnegative"),
        CheckConstraint(
            "image_url IS NULL OR image_url ~ '^https?://[^[:space:]]+$'",
            name="image_url_absolute_http",
        ),
        Index("ix_food_discovery", "status", "city", "pickup_end"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("food_categories.id"), index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    servings_total: Mapped[int] = mapped_column(Integer)
    servings_available: Mapped[int] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(40))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    pickup_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    pickup_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    area: Mapped[str] = mapped_column(String(160), index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    dietary_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    storage_information: Mapped[str | None] = mapped_column(Text)
    preparation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider_safety_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    delivery_available: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[FoodStatus] = mapped_column(Enum(FoodStatus, native_enum=False, length=24), default=FoodStatus.DRAFT, index=True)

    provider: Mapped[User] = relationship()
    location: Mapped[Location] = relationship()


class Reservation(UUIDTimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    food_listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("food_listings.id"), index=True)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus, native_enum=False, length=24), default=ReservationStatus.CONFIRMED, index=True)
    pickup_address: Mapped[str | None] = mapped_column(Text)
    handover_instructions: Mapped[str | None] = mapped_column(Text)
    food: Mapped[FoodListing] = relationship()


class ReservationEvent(UUIDTimestampMixin, Base):
    __tablename__ = "reservation_events"

    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    previous_state: Mapped[ReservationStatus | None] = mapped_column(Enum(ReservationStatus, native_enum=False, length=24))
    new_state: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus, native_enum=False, length=24))
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    actor_label: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class HandoverToken(UUIDTimestampMixin, Base):
    __tablename__ = "handover_tokens"

    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class DeliveryTask(UUIDTimestampMixin, Base):
    __tablename__ = "delivery_tasks"

    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id"), unique=True)
    volunteer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus, native_enum=False, length=32), default=DeliveryStatus.AVAILABLE, index=True)
    pickup_area: Mapped[str] = mapped_column(String(160))
    dropoff_area: Mapped[str] = mapped_column(String(160))
    dropoff_address: Mapped[str | None] = mapped_column(Text)
    dropoff_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    dropoff_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    dropoff_instructions: Mapped[str | None] = mapped_column(Text)
    reservation: Mapped[Reservation] = relationship()


class DeliveryEvent(UUIDTimestampMixin, Base):
    __tablename__ = "delivery_events"

    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_tasks.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    previous_state: Mapped[DeliveryStatus | None] = mapped_column(Enum(DeliveryStatus, native_enum=False, length=32))
    new_state: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus, native_enum=False, length=32))
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    actor_label: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Notification(UUIDTimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceToken(UUIDTimestampMixin, Base):
    __tablename__ = "device_tokens"
    __table_args__ = (UniqueConstraint("token"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(300))
    platform: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class VerificationRequest(UUIDTimestampMixin, Base):
    __tablename__ = "verification_requests"
    __table_args__ = (UniqueConstraint("user_id", "type"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[VerificationType] = mapped_column(Enum(VerificationType, native_enum=False, length=24))
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False, length=24), default=VerificationStatus.PENDING)
    statement: Mapped[str] = mapped_column(Text)
    reviewer_message: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Report(UUIDTimestampMixin, Base):
    __tablename__ = "reports"

    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    food_listing_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("food_listings.id"), index=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"), index=True)
    reason: Mapped[str] = mapped_column(String(48))
    details: Mapped[str] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus, native_enum=False, length=24), default=ReportStatus.OPEN)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)


class AiConversation(UUIDTimestampMixin, Base):
    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(8))


class AiMessage(UUIDTimestampMixin, Base):
    __tablename__ = "ai_messages"
    __table_args__ = (UniqueConstraint("user_id", "client_message_id"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_messages.id", ondelete="CASCADE"), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    references: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    client_message_id: Mapped[str | None] = mapped_column(String(128))


class OrganizationProfile(UUIDTimestampMixin, Base):
    __tablename__ = "organization_profiles"
    __table_args__ = (
        CheckConstraint("daily_capacity > 0", name="daily_capacity_positive"),
        CheckConstraint("people_served >= 0", name="people_served_nonnegative"),
        CheckConstraint("max_distance_km > 0", name="max_distance_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True)
    organization_type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, native_enum=False, length=32)
    )
    daily_capacity: Mapped[int] = mapped_column(Integer)
    people_served: Mapped[int] = mapped_column(Integer, default=0)
    accepted_category_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    pickup_window_start: Mapped[time] = mapped_column(Time(timezone=False))
    pickup_window_end: Mapped[time] = mapped_column(Time(timezone=False))
    max_distance_km: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship()
    location: Mapped[Location] = relationship()


class FoodMatch(UUIDTimestampMixin, Base):
    __tablename__ = "food_matches"
    __table_args__ = (
        UniqueConstraint("food_listing_id", "organization_id"),
        CheckConstraint("quantity_snapshot > 0", name="quantity_snapshot_positive"),
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
        Index("ix_food_matches_listing_status", "food_listing_id", "status"),
        Index("ix_food_matches_organization_status", "organization_id", "status"),
    )

    food_listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("food_listings.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    organization_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id"), index=True
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id"), unique=True
    )
    accepted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    declined_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[FoodMatchStatus] = mapped_column(
        Enum(FoodMatchStatus, native_enum=False, length=24),
        default=FoodMatchStatus.RECOMMENDED,
        index=True,
    )
    quantity_snapshot: Mapped[int] = mapped_column(Integer)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text)

    food: Mapped[FoodListing] = relationship()
    organization: Mapped[User] = relationship(foreign_keys=[organization_id])
    profile: Mapped[OrganizationProfile] = relationship()
    reservation: Mapped[Reservation | None] = relationship()


class AiAction(UUIDTimestampMixin, Base):
    __tablename__ = "ai_actions"
    __table_args__ = (UniqueConstraint("conversation_id", "idempotency_key"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_messages.id", ondelete="CASCADE"), index=True)
    result_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_messages.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200))


class KnowledgeDocument(UUIDTimestampMixin, Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("ix_knowledge_docs_approval", "approval_status", "jurisdiction"),
        Index("ix_knowledge_docs_effective", "effective_from", "effective_until"),
        Index("ix_knowledge_docs_source", "source", "document_type"),
    )

    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, native_enum=False, length=16), index=True)
    version: Mapped[str] = mapped_column(String(40))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_status: Mapped[DocumentApprovalStatus] = mapped_column(
        Enum(DocumentApprovalStatus, native_enum=False, length=16), default=DocumentApprovalStatus.DRAFT, index=True
    )
    jurisdiction: Mapped[str] = mapped_column(String(80), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeChunk(UUIDTimestampMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_document", "document_id", "chunk_index"),
        Index("ix_knowledge_chunks_approval", "approval_status"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536))
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(300))
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    approval_status: Mapped[DocumentApprovalStatus] = mapped_column(
        Enum(DocumentApprovalStatus, native_enum=False, length=16), default=DocumentApprovalStatus.DRAFT, index=True
    )

    document: Mapped[KnowledgeDocument] = relationship()

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import DeliveryStatus, FoodStatus, ReportStatus, ReservationStatus, Role, VerificationStatus, VerificationType


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class UserOut(BaseModel):
    id: UUID
    display_name: str
    email: EmailStr | None
    phone_number: str | None
    roles: list[Role]
    city: str | None
    area: str | None
    is_verified: bool


class PasswordLogin(StrictModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class EmailRegister(PasswordLogin):
    display_name: str = Field(min_length=2, max_length=120)


class OtpRequest(StrictModel):
    phone_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


class OtpVerify(OtpRequest):
    otp: str = Field(pattern=r"^\d{6}$")


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str


class SessionOut(TokensOut):
    user: UserOut


class LocationPreference(StrictModel):
    city: str = Field(min_length=2, max_length=120)
    area: str = Field(min_length=2, max_length=160)


class FoodDraftIn(StrictModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3, max_length=3000)
    category_id: UUID
    quantity: int = Field(gt=0, le=100000)
    servings: int = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=40)
    price: Decimal | None = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    is_free: bool
    pickup_start: datetime
    pickup_end: datetime
    location_id: UUID
    ingredients: list[str] = Field(default_factory=list, max_length=100)
    allergens: list[str] = Field(default_factory=list, max_length=100)
    dietary_information: list[str] = Field(default_factory=list, max_length=100)
    storage_information: str = Field(max_length=2000)
    preparation_time: datetime
    provider_safety_confirmed: bool

    @model_validator(mode="after")
    def validate_food(self) -> FoodDraftIn:
        if self.pickup_end <= self.pickup_start:
            raise ValueError("pickup_end must be after pickup_start")
        if self.is_free and self.price not in (None, 0):
            raise ValueError("free food cannot have a price")
        if not self.provider_safety_confirmed:
            raise ValueError("provider safety confirmation is required")
        return self


class FoodSummaryOut(BaseModel):
    id: UUID
    title: str
    provider_name: str
    provider_verified: bool
    image_url: str | None
    servings_available: int
    is_free: bool
    price: Decimal
    currency: str
    pickup_start: datetime
    pickup_end: datetime
    area: str
    approximate_distance_km: float | None
    status: FoodStatus
    dietary_information: list[str]


class FoodDetailOut(FoodSummaryOut):
    description: str
    category_id: UUID
    quantity: int
    unit: str
    ingredients: list[str]
    allergens: list[str]
    storage_information: str | None
    expires_at: datetime
    exact_pickup_address: str | None
    latitude: float | None
    longitude: float | None


class FoodPage(BaseModel):
    items: list[FoodSummaryOut]
    meta: PageMeta


class ReservationCreate(StrictModel):
    food_listing_id: UUID
    quantity: int = Field(gt=0, le=10000)


class ReservationEventOut(BaseModel):
    id: UUID
    previous_state: ReservationStatus | None
    new_state: ReservationStatus
    occurred_at: datetime
    actor_label: str


class ReservationSummaryOut(BaseModel):
    id: UUID
    food: FoodSummaryOut
    quantity: int
    status: ReservationStatus
    pickup_start: datetime
    pickup_end: datetime
    updated_at: datetime


class ReservationDetailOut(ReservationSummaryOut):
    pickup_address: str | None
    handover_instructions: str | None
    can_display_handover_qr: bool
    handover_token: str | None
    events: list[ReservationEventOut]


class ReservationPage(BaseModel):
    items: list[ReservationSummaryOut]
    meta: PageMeta


class DeliveryTransitionIn(StrictModel):
    status: DeliveryStatus


class CoordinateOut(BaseModel):
    latitude: float
    longitude: float


class DeliveryPointOut(BaseModel):
    area: str
    address: str | None
    coordinate: CoordinateOut | None
    instructions: str | None


class DeliveryEventOut(BaseModel):
    id: UUID
    previous_state: DeliveryStatus | None
    new_state: DeliveryStatus
    actor_label: str
    occurred_at: datetime


class DeliverySummaryOut(BaseModel):
    id: UUID
    status: DeliveryStatus
    food_title: str
    servings: int
    pickup_area: str
    dropoff_area: str
    pickup_start: datetime
    pickup_end: datetime
    distance_km: float | None
    updated_at: datetime


class DeliveryDetailOut(DeliverySummaryOut):
    pickup: DeliveryPointOut
    dropoff: DeliveryPointOut
    allowed_transitions: list[DeliveryStatus]
    events: list[DeliveryEventOut]


class DeliveryPage(BaseModel):
    items: list[DeliverySummaryOut]
    meta: PageMeta


class DeviceIn(StrictModel):
    token: str = Field(min_length=10, max_length=300)
    platform: Literal["ios", "android"]


class NotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime
    route: str | None


class NotificationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    meta: NotificationMeta


class VerificationCreate(StrictModel):
    type: VerificationType
    statement: str = Field(min_length=20, max_length=3000)


class VerificationOut(BaseModel):
    id: UUID | None
    type: VerificationType
    status: VerificationStatus | Literal["NOT_SUBMITTED"]
    submitted_at: datetime | None
    reviewer_message: str | None


REPORT_REASONS = Literal["UNSAFE_FOOD", "SPOILED_FOOD", "FAKE_LISTING", "INCORRECT_QUANTITY", "NO_SHOW", "MISLEADING_INFORMATION", "HARASSMENT_ABUSE", "OTHER"]


class ReportCreate(StrictModel):
    food_listing_id: UUID | None = None
    reservation_id: UUID | None = None
    reason: REPORT_REASONS
    details: str = Field(min_length=10, max_length=3000)

    @model_validator(mode="after")
    def exactly_one_target(self) -> ReportCreate:
        if (self.food_listing_id is None) == (self.reservation_id is None):
            raise ValueError("provide exactly one report target")
        return self


class ReportOut(BaseModel):
    id: UUID
    reason: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


class HandoverTokenOut(BaseModel):
    token: str
    expires_at: datetime


class HandoverConfirm(StrictModel):
    token: str = Field(min_length=24, max_length=512)


class HandoverConfirmOut(BaseModel):
    reservation_id: UUID


class ManoMessageIn(StrictModel):
    conversation_id: UUID | None
    message: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "ur", "ps", "hno", "pa"]
    experience: Role
    client_message_id: str = Field(min_length=1, max_length=128)
    voice_input: bool = False


class ManoActionConfirm(StrictModel):
    conversation_id: UUID
    confirmation: Literal[True]
    idempotency_key: str = Field(min_length=3, max_length=200)


class MessageReference(BaseModel):
    resource_type: Literal["food_listing", "reservation", "delivery_task", "community_request"]
    resource_id: UUID
    label: str


class ManoMessageOut(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    references: list[MessageReference] = Field(default_factory=list)


class SuggestedActionOut(BaseModel):
    id: UUID
    kind: Literal["OPEN_DISCOVER", "OPEN_FOOD_LISTING", "OPEN_RESERVATION", "OPEN_DELIVERY_TASK", "CREATE_FOOD_LISTING_DRAFT", "CREATE_COMMUNITY_REQUEST_DRAFT"]
    label: str
    summary: str | None
    resource_id: UUID | None
    requires_confirmation: bool
    expires_at: datetime | None


class ManoResponse(BaseModel):
    conversation_id: UUID
    message: ManoMessageOut
    suggested_actions: list[SuggestedActionOut]


class ManoActionResult(BaseModel):
    action_id: UUID
    status: Literal["COMPLETED", "REJECTED", "EXPIRED"]
    message: ManoMessageOut
    resource_type: Literal["food_listing", "reservation", "delivery_task", "community_request"] | None
    resource_id: UUID | None


class TranscriptionOut(BaseModel):
    text: str
    detected_language: Literal["en", "ur", "ps", "hno", "pa"] | None


class AdminVerificationUpdate(StrictModel):
    status: Literal[VerificationStatus.APPROVED, VerificationStatus.REJECTED, VerificationStatus.NEEDS_INFORMATION]
    reviewer_message: str | None = Field(default=None, max_length=2000)


class AdminReportUpdate(StrictModel):
    status: Literal[ReportStatus.UNDER_REVIEW, ReportStatus.RESOLVED, ReportStatus.DISMISSED]

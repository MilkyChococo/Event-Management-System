from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg"


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Invalid email address.")
    return email


def _validate_optional_email(value: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        return ""
    return _validate_email(cleaned)


def _validate_date(value: str) -> str:
    cleaned = value.strip()
    parts = cleaned.split("-")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("Date must use YYYY-MM-DD format.")
    year, month, day = map(int, parts)
    if year < 1900 or month < 1 or month > 12 or day < 1 or day > 31:
        raise ValueError("Invalid date.")
    return cleaned


def _normalize_optional_url(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or DEFAULT_EVENT_IMAGE


def _normalize_image_url(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _normalize_profile_image(value: str | None) -> str:
    return (value or "").strip()


def _normalize_image_url_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        raise ValueError("Image URLs must be a list of strings.")

    normalized: list[str] = []
    for item in candidates:
        cleaned = str(item or "").strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = value.splitlines()
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        raise ValueError("Value must be a list of strings.")

    normalized: list[str] = []
    for item in candidates:
        cleaned = str(item or "").strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=128)
    date_of_birth: str
    country: str = Field(min_length=2, max_length=80)
    province: str = Field(min_length=2, max_length=120)
    district: str = Field(min_length=2, max_length=120)
    ward: str = Field(default="", max_length=120)
    street_address: str = Field(min_length=5, max_length=255)
    phone_country_code: str = Field(min_length=2, max_length=8)
    phone_country_label: str = Field(min_length=2, max_length=80)
    phone_country_flag: str = Field(min_length=2, max_length=24)
    phone_local_number: str = Field(min_length=6, max_length=20)

    _email = field_validator("email")(_validate_email)
    _birth_date = field_validator("date_of_birth")(_validate_date)


class LoginInput(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    _email = field_validator("email")(_validate_email)


class UserOutput(BaseModel):
    id: int
    name: str
    email: str
    role: str
    age: int
    date_of_birth: str
    permanent_address: str
    country: str
    province: str
    district: str
    ward: str
    street_address: str
    phone_number: str
    phone_country_code: str
    phone_country_label: str
    phone_country_flag: str
    phone_local_number: str
    avatar_url: str
    balance: float


class UserUpdateInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    date_of_birth: str
    country: str = Field(min_length=2, max_length=80)
    province: str = Field(min_length=2, max_length=120)
    district: str = Field(min_length=2, max_length=120)
    ward: str = Field(default="", max_length=120)
    street_address: str = Field(min_length=5, max_length=255)
    phone_country_code: str = Field(min_length=2, max_length=8)
    phone_country_label: str = Field(min_length=2, max_length=80)
    phone_country_flag: str = Field(min_length=2, max_length=24)
    phone_local_number: str = Field(min_length=6, max_length=20)
    avatar_url: str = Field(default="", max_length=3_000_000)

    _birth_date = field_validator("date_of_birth")(_validate_date)
    _avatar_url = field_validator("avatar_url", mode="before")(_normalize_profile_image)


class PasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordInput(BaseModel):
    email: str
    date_of_birth: str
    new_password: str = Field(min_length=8, max_length=128)

    _email = field_validator("email")(_validate_email)
    _birth_date = field_validator("date_of_birth")(_validate_date)


class TicketTypeInput(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    price: float = Field(ge=0, le=1_000_000_000)
    details: str = Field(default="", max_length=240)

    @field_validator("label", mode="before")
    @classmethod
    def _clean_label(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("details", mode="before")
    @classmethod
    def _clean_details(cls, value: object) -> str:
        return str(value or "").strip()


class TicketTypeOutput(BaseModel):
    label: str
    price: float
    details: str


class RegistrationInput(BaseModel):
    ticket_label: str = Field(default="", max_length=80)
    quantity: int = Field(default=1, ge=1, le=5)
    attendee_name: str = Field(default="", max_length=100)
    attendee_email: str = Field(default="", max_length=255)
    attendee_phone: str = Field(default="", max_length=40)

    @field_validator("ticket_label", "attendee_name", "attendee_phone", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("attendee_email", mode="before")
    @classmethod
    def _clean_attendee_email(cls, value: object) -> str:
        return _validate_optional_email(str(value or ""))

class EventInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    category: str = Field(default="General", min_length=2, max_length=80)
    event_format: str = Field(default="Offline", min_length=2, max_length=40)
    location: str = Field(min_length=1, max_length=255)
    venue_details: str = Field(default="", max_length=400)
    start_at: str = Field(min_length=10, max_length=40)
    registration_deadline: str = Field(default="", max_length=40)
    capacity: int = Field(ge=1, le=5000)
    price: float = Field(ge=0, le=1_000_000_000)
    organizer_name: str = Field(default="", max_length=120)
    organizer_details: str = Field(default="", max_length=400)
    speaker_lineup: list[str] = Field(default_factory=list)
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    map_url: str = Field(default="", max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    refund_policy: str = Field(default="", max_length=400)
    check_in_policy: str = Field(default="", max_length=400)
    contact_email: str = Field(default="", max_length=255)
    contact_phone: str = Field(default="", max_length=40)
    ticket_types: list[TicketTypeInput] = Field(default_factory=list)
    opening_highlights: str = Field(default="", max_length=400)
    mid_event_highlights: str = Field(default="", max_length=400)
    closing_highlights: str = Field(default="", max_length=400)

    @field_validator(
        "title",
        "description",
        "category",
        "event_format",
        "location",
        "venue_details",
        "start_at",
        "registration_deadline",
        "organizer_name",
        "organizer_details",
        "map_url",
        "refund_policy",
        "check_in_policy",
        "contact_phone",
        "opening_highlights",
        "mid_event_highlights",
        "closing_highlights",
        mode="before",
    )
    @classmethod
    def _clean_text_fields(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("contact_email", mode="before")
    @classmethod
    def _clean_contact_email(cls, value: object) -> str:
        return _validate_optional_email(str(value or ""))

    @field_validator("speaker_lineup", mode="before")
    @classmethod
    def _normalize_speakers(cls, value: object) -> list[str]:
        return _normalize_text_list(value)

    @field_validator("image_url", mode="before")
    @classmethod
    def _normalize_primary_image(cls, value: object) -> str | None:
        return _normalize_image_url(str(value) if value is not None else None)

    @field_validator("image_urls", mode="before")
    @classmethod
    def _normalize_gallery_images(cls, value: object) -> list[str]:
        return _normalize_image_url_list(value)

    @model_validator(mode="after")
    def _coerce_gallery(self) -> "EventInput":
        gallery = list(self.image_urls)
        if self.image_url and self.image_url not in gallery:
            gallery.insert(0, self.image_url)
        if not gallery:
            gallery = [DEFAULT_EVENT_IMAGE]
        self.image_urls = gallery
        self.image_url = gallery[0]
        return self


class OwnedEventCreateInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    category: str = Field(default="Community", min_length=2, max_length=80)
    location: str = Field(min_length=1, max_length=255)
    venue_details: str = Field(default="", max_length=400)
    start_at: str = Field(min_length=10, max_length=40)
    capacity: int = Field(ge=1, le=5000)
    price: float = Field(ge=0, le=1_000_000_000)
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("title", "description", "category", "location", "venue_details", "start_at", mode="before")
    @classmethod
    def _clean_owned_event_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("image_url", mode="before")
    @classmethod
    def _normalize_owned_primary_image(cls, value: object) -> str | None:
        return _normalize_image_url(str(value) if value is not None else None)

    @field_validator("image_urls", mode="before")
    @classmethod
    def _normalize_owned_gallery_images(cls, value: object) -> list[str]:
        return _normalize_image_url_list(value)

    @model_validator(mode="after")
    def _coerce_owned_gallery(self) -> "OwnedEventCreateInput":
        gallery = list(self.image_urls)
        if self.image_url and self.image_url not in gallery:
            gallery.insert(0, self.image_url)
        if not gallery:
            gallery = [DEFAULT_EVENT_IMAGE]
        self.image_urls = gallery
        self.image_url = gallery[0]
        return self


class EventOutput(BaseModel):
    id: int
    title: str
    description: str
    category: str
    event_format: str
    location: str
    venue_details: str
    start_at: str
    registration_deadline: str
    capacity: int
    price: float
    organizer_name: str
    organizer_details: str
    speaker_lineup: list[str]
    image_url: str
    image_urls: list[str]
    map_url: str
    latitude: float | None
    longitude: float | None
    refund_policy: str
    check_in_policy: str
    contact_email: str
    contact_phone: str
    ticket_types: list[TicketTypeOutput]
    opening_highlights: str
    mid_event_highlights: str
    closing_highlights: str
    approval_status: str
    review_note: str
    registered_count: int
    seats_left: int
    is_registered: bool


class AttendeeOutput(BaseModel):
    id: int
    name: str
    email: str
    registered_at: str
    ticket_label: str
    quantity: int
    status: str

class UserTicketOutput(BaseModel):
    event_id: int
    title: str
    category: str
    event_format: str
    location: str
    start_at: str
    image_url: str
    ticket_code: str
    ticket_label: str
    quantity: int
    ticket_price: float
    total_price: float
    attendee_name: str
    attendee_email: str
    attendee_phone: str
    status: str
    registered_at: str
    cancelled_at: str | None = None
    qr_payload: str

class NotificationOutput(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    link: str
    action_label: str | None = None
    is_read: bool
    created_at: str


class NotificationListOutput(BaseModel):
    unread_count: int
    items: list[NotificationOutput]

class WalletTopUpInput(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    provider: str = Field(default="QR transfer", min_length=2, max_length=120)
    note: str = Field(default="", max_length=240)

    @field_validator("provider", "note", mode="before")
    @classmethod
    def _clean_wallet_text(cls, value: object) -> str:
        return str(value or "").strip()


class WalletTransactionOutput(BaseModel):
    kind: str
    amount: float
    balance_delta: float
    balance_after: float
    note: str
    event_id: int | None = None
    ticket_label: str = ""
    qr_payload: str = ""
    qr_image_url: str = ""
    created_at: str


class WalletPendingTopUpOutput(BaseModel):
    request_id: int
    amount: float
    provider: str
    note: str
    status: str
    qr_payload: str
    qr_image_url: str
    created_at: str
    expires_at: str
    seconds_remaining: int


class WalletOverviewOutput(BaseModel):
    user: UserOutput
    transactions: list[WalletTransactionOutput]
    pending_top_up: WalletPendingTopUpOutput | None = None


class WalletTopUpOutput(BaseModel):
    pending_top_up: WalletPendingTopUpOutput
    message: str


class WalletTopUpConfirmOutput(BaseModel):
    user: UserOutput
    transaction: WalletTransactionOutput
    message: str


class DistributionItemOutput(BaseModel):
    label: str
    count: int
    share: float


class AnalyticsSummaryOutput(BaseModel):
    total_events: int
    total_registrations: int
    total_capacity: int
    occupancy_rate: float
    total_revenue: float
    average_ticket_price: float
    domestic_customer_ratio: float
    international_customer_ratio: float


class EventAnalyticsOutput(BaseModel):
    event_id: int
    title: str
    start_at: str
    price: float
    capacity: int
    registered_count: int
    seats_left: int
    fill_rate: float
    revenue: float
    share_of_registrations: float
    country_distribution: list[DistributionItemOutput]
    age_distribution: list[DistributionItemOutput]


class AdminAnalyticsOutput(BaseModel):
    summary: AnalyticsSummaryOutput
    customer_mix: list[DistributionItemOutput]
    country_distribution: list[DistributionItemOutput]
    events: list[EventAnalyticsOutput]


class MessageOutput(BaseModel):
    message: str


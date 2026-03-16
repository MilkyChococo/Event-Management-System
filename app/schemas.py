from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg"


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Invalid email address.")
    return email


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


class ForgotPasswordInput(BaseModel):
    email: str
    date_of_birth: str
    new_password: str = Field(min_length=8, max_length=128)

    _email = field_validator("email")(_validate_email)
    _birth_date = field_validator("date_of_birth")(_validate_date)


class EventInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    location: str = Field(min_length=3, max_length=120)
    venue_details: str = Field(default="", max_length=400)
    start_at: str = Field(min_length=10, max_length=40)
    capacity: int = Field(ge=1, le=5000)
    price: float = Field(ge=0, le=1_000_000_000)
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    opening_highlights: str = Field(default="", max_length=400)
    mid_event_highlights: str = Field(default="", max_length=400)
    closing_highlights: str = Field(default="", max_length=400)

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


class EventOutput(BaseModel):
    id: int
    title: str
    description: str
    location: str
    venue_details: str
    start_at: str
    capacity: int
    price: float
    image_url: str
    image_urls: list[str]
    opening_highlights: str
    mid_event_highlights: str
    closing_highlights: str
    registered_count: int
    seats_left: int
    is_registered: bool


class AttendeeOutput(BaseModel):
    id: int
    name: str
    email: str
    registered_at: str


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
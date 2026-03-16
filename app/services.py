from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database import Database
from app.security import generate_session_token, hash_password, verify_password


DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg"
KNOWN_COUNTRIES = {"Vietnam", "United States", "Singapore", "Japan"}
PHONE_COUNTRY_META = {
    "+84": {"label": "Vietnam", "flag": "vn"},
    "+1": {"label": "United States", "flag": "us"},
    "+65": {"label": "Singapore", "flag": "sg"},
    "+81": {"label": "Japan", "flag": "jp"},
}


def normalize_event_images(image_urls: list[str] | None = None, image_url: str | None = None) -> list[str]:
    normalized: list[str] = []
    for value in image_urls or []:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)

    primary = str(image_url or "").strip()
    if primary and primary not in normalized:
        normalized.insert(0, primary)

    return normalized or [DEFAULT_EVENT_IMAGE]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculate_age(date_of_birth: str) -> int:
    birth_date = date.fromisoformat(date_of_birth)
    today = date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)


def normalize_phone_local_number(phone_local_number: str, phone_country_code: str) -> str:
    digits = re.sub(r"\D", "", phone_local_number)
    if phone_country_code in {"+84", "+81"} and digits.startswith("0"):
        digits = digits[1:]
    return digits


def build_phone_number(phone_country_code: str, phone_local_number: str) -> str:
    local_number = normalize_phone_local_number(phone_local_number, phone_country_code)
    return f"{phone_country_code} {local_number}".strip()


def build_permanent_address(
    street_address: str,
    ward: str,
    district: str,
    province: str,
    country: str,
) -> str:
    return ", ".join(
        part.strip()
        for part in [street_address, ward, district, province, country]
        if part and part.strip()
    )


def infer_address_profile(permanent_address: str) -> dict[str, str]:
    parts = [part.strip() for part in permanent_address.split(",") if part.strip()]
    country = parts[-1] if parts and parts[-1] in KNOWN_COUNTRIES else "Vietnam"
    working_parts = parts[:-1] if parts and parts[-1] in KNOWN_COUNTRIES else parts

    province = working_parts[-1] if len(working_parts) >= 1 else ""
    district = working_parts[-2] if len(working_parts) >= 2 else ""
    if len(working_parts) >= 4:
        ward = working_parts[-3]
        street_address = ", ".join(working_parts[:-3])
    elif len(working_parts) == 3:
        ward = ""
        street_address = working_parts[0]
    elif len(working_parts) == 2:
        ward = ""
        street_address = working_parts[0]
    elif len(working_parts) == 1:
        ward = ""
        street_address = working_parts[0]
    else:
        ward = ""
        street_address = ""

    return {
        "country": country,
        "province": province,
        "district": district,
        "ward": ward,
        "street_address": street_address,
    }


def infer_phone_profile(phone_number: str) -> dict[str, str]:
    normalized = re.sub(r"[^\d+]", "", phone_number or "")
    for code in sorted(PHONE_COUNTRY_META, key=len, reverse=True):
        if normalized.startswith(code):
            local_number = normalize_phone_local_number(normalized[len(code):], code)
            return {
                "phone_country_code": code,
                "phone_country_label": PHONE_COUNTRY_META[code]["label"],
                "phone_country_flag": PHONE_COUNTRY_META[code]["flag"],
                "phone_local_number": local_number,
            }

    default_code = "+84"
    local_number = normalized[1:] if normalized.startswith("0") else normalized.lstrip("+")
    return {
        "phone_country_code": default_code,
        "phone_country_label": PHONE_COUNTRY_META[default_code]["label"],
        "phone_country_flag": PHONE_COUNTRY_META[default_code]["flag"],
        "phone_local_number": normalize_phone_local_number(local_number, default_code),
    }


@dataclass(slots=True)
class ServiceError(Exception):
    status_code: int
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


class EventRegistrationService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def initialize(self, seed_demo: bool = True) -> None:
        self.db.initialize()
        if seed_demo:
            self.seed_demo_data()

    def seed_demo_data(self) -> None:
        if self.db.users.count_documents({}):
            return

        created_at = utc_now()
        admin = self._create_user_document(
            name="Demo Admin",
            email="admin@example.com",
            password="Admin123!",
            role="admin",
            date_of_birth="1998-05-14",
            country="Vietnam",
            province="Ho Chi Minh City",
            district="Go Vap District",
            ward="Ward 3",
            street_address="12 Nguyen Van Bao",
            phone_country_code="+84",
            phone_country_label="Vietnam",
            phone_country_flag="vn",
            phone_local_number="901234567",
            created_at=created_at,
        )
        student = self._create_user_document(
            name="Demo Student",
            email="student@example.com",
            password="Student123!",
            role="user",
            date_of_birth="2005-08-20",
            country="Vietnam",
            province="Ho Chi Minh City",
            district="Phu Nhuan District",
            ward="Ward 7",
            street_address="45 Le Van Sy",
            phone_country_code="+84",
            phone_country_label="Vietnam",
            phone_country_flag="vn",
            phone_local_number="912345678",
            created_at=created_at,
        )
        self.db.users.insert_many([admin, student])

        events = [
            {
                "id": self.db.next_sequence("events"),
                "title": "AI Career Night",
                "description": "An atmospheric hiring-night built for AI students, lab leads, and startup recruiters who want long-form conversations instead of rushed booths.",
                "location": "Aster Hall, 14 Mercer Street, District 1",
                "venue_details": "Level 3, Aster Hall, 14 Mercer Street, District 1. Doors open at 5:15 PM, valet and self-parking available from the east entrance, check-in desk beside the copper staircase.",
                "start_at": "2026-04-10T18:00:00",
                "capacity": 50,
                "price": 39,
                "image_url": "/static/images/ai-career-night.svg",
                "image_urls": [
                    "/static/images/ai-career-night.svg",
                    "/static/images/gallery-lounge.svg",
                    "/static/images/gallery-stage.svg",
                ],
                "opening_highlights": "Opening reception with ambient jazz, name-card wall, recruiter introductions, and a short keynote on AI careers in 2026.",
                "mid_event_highlights": "Round-table networking, portfolio review corners, live CV teardown, and a slow-dining tapas course with craft mocktails.",
                "closing_highlights": "Closing lounge session with mentorship sign-up, internship priority codes, and a rooftop photo set under the city lights.",
                "created_by": admin["id"],
                "created_at": created_at,
                "updated_at": created_at,
                "registered_count": 0,
            },
            {
                "id": self.db.next_sequence("events"),
                "title": "Software Verification Workshop",
                "description": "A studio-style workshop where teams move from requirements to traceability, CI pipelines, and browser regression evidence in one guided day.",
                "location": "Orchid Tech Loft, 88 Nguyen Hue Boulevard",
                "venue_details": "Studio B, Orchid Tech Loft, 88 Nguyen Hue Boulevard, District 1. Elevator bank C to floor 8, breakfast bar in the foyer, hardware check desk opens at 8:15 AM.",
                "start_at": "2026-04-12T09:00:00",
                "capacity": 30,
                "price": 24,
                "image_url": "/static/images/verification-workshop.svg",
                "image_urls": [
                    "/static/images/verification-workshop.svg",
                    "/static/images/gallery-stage.svg",
                    "/static/images/gallery-foyer.svg",
                ],
                "opening_highlights": "Opening breakfast, project framing session, and a live teardown of common verification mistakes in student systems.",
                "mid_event_highlights": "Hands-on labs for unit testing, API verification, Playwright flow design, defect logging, and pair coaching with mentors.",
                "closing_highlights": "Closing review circle, showcase of the strongest pipelines, and a take-home release checklist for final project defense.",
                "created_by": admin["id"],
                "created_at": created_at,
                "updated_at": created_at,
                "registered_count": 0,
            },
            {
                "id": self.db.next_sequence("events"),
                "title": "Startup Pitch Day",
                "description": "A cinematic showcase of student products where founders pitch, mentors critique with honesty, and guests move through tasting stations and prototype corners.",
                "location": "Glass Pavilion, Riverside Creative Campus",
                "venue_details": "Main Pavilion, Riverside Creative Campus, 22 Ben Van Don, District 4. Riverfront entrance opens at 1:00 PM, gallery check-in at the black marble desk, overflow seating in the mezzanine.",
                "start_at": "2026-04-18T14:00:00",
                "capacity": 80,
                "price": 18,
                "image_url": "/static/images/startup-pitch-day.svg",
                "image_urls": [
                    "/static/images/startup-pitch-day.svg",
                    "/static/images/gallery-foyer.svg",
                    "/static/images/gallery-lounge.svg",
                ],
                "opening_highlights": "Opening lights-down reel, host introduction, sponsor toast, and founder warm-up conversations with press and angel guests.",
                "mid_event_highlights": "Live pitches, tasting tables, prototype walkarounds, investor Q&A, and a mid-event dinner spread with modern Vietnamese small plates.",
                "closing_highlights": "Award moment, founder after-party set, mentor matchmaking, and an open terrace mixer with acoustic closing performance.",
                "created_by": admin["id"],
                "created_at": created_at,
                "updated_at": created_at,
                "registered_count": 0,
            },
        ]
        self.db.events.insert_many(events)

    def _create_user_document(
        self,
        name: str,
        email: str,
        password: str,
        role: str,
        date_of_birth: str,
        country: str,
        province: str,
        district: str,
        ward: str,
        street_address: str,
        phone_country_code: str,
        phone_country_label: str,
        phone_country_flag: str,
        phone_local_number: str,
        created_at: str,
    ) -> dict[str, Any]:
        normalized_phone_local = normalize_phone_local_number(phone_local_number, phone_country_code)
        return {
            "id": self.db.next_sequence("users"),
            "name": name.strip(),
            "email": email.strip().lower(),
            "password_hash": hash_password(password),
            "role": role,
            "date_of_birth": date_of_birth.strip(),
            "country": country.strip(),
            "province": province.strip(),
            "district": district.strip(),
            "ward": ward.strip(),
            "street_address": street_address.strip(),
            "permanent_address": build_permanent_address(
                street_address,
                ward,
                district,
                province,
                country,
            ),
            "phone_country_code": phone_country_code.strip(),
            "phone_country_label": phone_country_label.strip(),
            "phone_country_flag": phone_country_flag.strip(),
            "phone_local_number": normalized_phone_local,
            "phone_number": build_phone_number(phone_country_code, normalized_phone_local),
            "created_at": created_at,
        }

    def _normalize_user_profile(self, document: dict[str, Any]) -> dict[str, Any]:
        address_profile = infer_address_profile(document.get("permanent_address", ""))
        phone_profile = infer_phone_profile(document.get("phone_number", ""))

        country = document.get("country") or address_profile["country"]
        province = document.get("province") or address_profile["province"]
        district = document.get("district") or address_profile["district"]
        ward = document.get("ward") or address_profile["ward"]
        street_address = document.get("street_address") or address_profile["street_address"]
        phone_country_code = document.get("phone_country_code") or phone_profile["phone_country_code"]
        phone_country_label = document.get("phone_country_label") or phone_profile["phone_country_label"]
        phone_country_flag = document.get("phone_country_flag") or phone_profile["phone_country_flag"]
        phone_local_number = document.get("phone_local_number") or phone_profile["phone_local_number"]

        return {
            "country": country,
            "province": province,
            "district": district,
            "ward": ward,
            "street_address": street_address,
            "permanent_address": build_permanent_address(street_address, ward, district, province, country),
            "phone_country_code": phone_country_code,
            "phone_country_label": phone_country_label,
            "phone_country_flag": phone_country_flag,
            "phone_local_number": phone_local_number,
            "phone_number": build_phone_number(phone_country_code, phone_local_number),
        }

    def _serialize_user(self, document: dict[str, Any]) -> dict[str, Any]:
        normalized_profile = self._normalize_user_profile(document)
        return {
            "id": document["id"],
            "name": document["name"],
            "email": document["email"],
            "role": document["role"],
            "age": calculate_age(document["date_of_birth"]),
            "date_of_birth": document["date_of_birth"],
            **normalized_profile,
        }

    def _serialize_event(
        self,
        document: dict[str, Any],
        registered_count: int,
        is_registered: bool,
    ) -> dict[str, Any]:
        capacity = int(document["capacity"])
        image_urls = normalize_event_images(document.get("image_urls"), document.get("image_url"))
        return {
            "id": document["id"],
            "title": document["title"],
            "description": document["description"],
            "location": document["location"],
            "venue_details": document.get("venue_details", ""),
            "start_at": document["start_at"],
            "capacity": capacity,
            "price": document.get("price", 0),
            "image_url": image_urls[0],
            "image_urls": image_urls,
            "opening_highlights": document.get("opening_highlights", ""),
            "mid_event_highlights": document.get("mid_event_highlights", ""),
            "closing_highlights": document.get("closing_highlights", ""),
            "registered_count": registered_count,
            "seats_left": max(capacity - registered_count, 0),
            "is_registered": is_registered,
        }

    def _percentage(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 2)

    def _age_band_label(self, date_of_birth: str) -> str:
        age = calculate_age(date_of_birth)
        if age < 20:
            return "Under 20"
        if age < 25:
            return "20-24"
        if age < 30:
            return "25-29"
        return "30+"

    def _build_distribution(self, counts: dict[str, int], total: int) -> list[dict[str, Any]]:
        items = [
            {
                "label": label,
                "count": count,
                "share": self._percentage(count, total),
            }
            for label, count in counts.items()
            if label and count > 0
        ]
        return sorted(items, key=lambda item: (-item["count"], item["label"]))

    def get_admin_analytics(self) -> dict[str, Any]:
        events = list(self.db.events.find({}, sort=[("start_at", ASCENDING)]))
        registrations = list(self.db.registrations.find({}))
        user_ids = sorted({int(document["user_id"]) for document in registrations})
        users = {document["id"]: document for document in self.db.users.find({"id": {"$in": user_ids}})}
        registrations_by_event: dict[int, list[dict[str, Any]]] = {}
        country_counts: dict[str, int] = {}
        domestic_count = 0
        international_count = 0

        for registration in registrations:
            event_id = int(registration["event_id"])
            registrations_by_event.setdefault(event_id, []).append(registration)
            user = users.get(registration["user_id"])
            if user is None:
                continue

            country = self._normalize_user_profile(user)["country"] or "Unknown"
            country_counts[country] = country_counts.get(country, 0) + 1
            if country == "Vietnam":
                domestic_count += 1
            else:
                international_count += 1

        total_registrations = len(registrations)
        total_capacity = sum(int(event["capacity"]) for event in events)
        total_revenue = round(
            sum(float(event.get("price", 0)) * len(registrations_by_event.get(event["id"], [])) for event in events),
            2,
        )
        events_output = []

        for event in events:
            event_registrations = registrations_by_event.get(event["id"], [])
            registered_count = len(event_registrations)
            event_country_counts: dict[str, int] = {}
            event_age_counts: dict[str, int] = {}

            for registration in event_registrations:
                user = users.get(registration["user_id"])
                if user is None:
                    continue

                country = self._normalize_user_profile(user)["country"] or "Unknown"
                event_country_counts[country] = event_country_counts.get(country, 0) + 1
                age_band = self._age_band_label(user["date_of_birth"])
                event_age_counts[age_band] = event_age_counts.get(age_band, 0) + 1

            capacity = int(event["capacity"])
            revenue = round(float(event.get("price", 0)) * registered_count, 2)
            events_output.append(
                {
                    "event_id": event["id"],
                    "title": event["title"],
                    "start_at": event["start_at"],
                    "price": float(event.get("price", 0)),
                    "capacity": capacity,
                    "registered_count": registered_count,
                    "seats_left": max(capacity - registered_count, 0),
                    "fill_rate": self._percentage(registered_count, capacity),
                    "revenue": revenue,
                    "share_of_registrations": self._percentage(registered_count, total_registrations),
                    "country_distribution": self._build_distribution(event_country_counts, registered_count),
                    "age_distribution": self._build_distribution(event_age_counts, registered_count),
                }
            )

        return {
            "summary": {
                "total_events": len(events),
                "total_registrations": total_registrations,
                "total_capacity": total_capacity,
                "occupancy_rate": self._percentage(total_registrations, total_capacity),
                "total_revenue": total_revenue,
                "average_ticket_price": round(total_revenue / total_registrations, 2) if total_registrations else 0.0,
                "domestic_customer_ratio": self._percentage(domestic_count, total_registrations),
                "international_customer_ratio": self._percentage(international_count, total_registrations),
            },
            "customer_mix": [
                {
                    "label": "Vietnam",
                    "count": domestic_count,
                    "share": self._percentage(domestic_count, total_registrations),
                },
                {
                    "label": "International",
                    "count": international_count,
                    "share": self._percentage(international_count, total_registrations),
                },
            ],
            "country_distribution": self._build_distribution(country_counts, total_registrations),
            "events": events_output,
        }

    def register_user(
        self,
        name: str,
        email: str,
        password: str,
        date_of_birth: str,
        country: str,
        province: str,
        district: str,
        ward: str,
        street_address: str,
        phone_country_code: str,
        phone_country_label: str,
        phone_country_flag: str,
        phone_local_number: str,
        role: str = "user",
    ) -> dict[str, Any]:
        if len(password) < 8:
            raise ServiceError(422, "WEAK_PASSWORD", "Password must contain at least 8 characters.")

        document = self._create_user_document(
            name=name,
            email=email,
            password=password,
            role=role,
            date_of_birth=date_of_birth,
            country=country,
            province=province,
            district=district,
            ward=ward,
            street_address=street_address,
            phone_country_code=phone_country_code,
            phone_country_label=phone_country_label,
            phone_country_flag=phone_country_flag,
            phone_local_number=phone_local_number,
            created_at=utc_now(),
        )
        try:
            self.db.users.insert_one(document)
        except DuplicateKeyError as exc:
            raise ServiceError(409, "EMAIL_EXISTS", "Email is already registered.") from exc
        return self._serialize_user(document)

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        document = self.db.users.find_one({"email": email.strip().lower()})
        if not document:
            raise ServiceError(404, "ACCOUNT_NOT_FOUND", "Account does not exist.")
        if not verify_password(password, document["password_hash"]):
            raise ServiceError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
        return self._serialize_user(document)

    def reset_password(self, email: str, date_of_birth: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise ServiceError(422, "WEAK_PASSWORD", "Password must contain at least 8 characters.")

        result = self.db.users.update_one(
            {
                "email": email.strip().lower(),
                "date_of_birth": date_of_birth.strip(),
            },
            {"$set": {"password_hash": hash_password(new_password)}},
        )
        if result.matched_count == 0:
            raise ServiceError(404, "PROFILE_NOT_FOUND", "No account matched the provided recovery information.")

    def create_session(self, user_id: int) -> str:
        for _ in range(5):
            token = generate_session_token()
            try:
                self.db.sessions.insert_one(
                    {
                        "token": token,
                        "user_id": user_id,
                        "created_at": utc_now(),
                    }
                )
                return token
            except DuplicateKeyError:
                continue
        raise ServiceError(500, "SESSION_CREATE_FAILED", "Could not create a session token.")

    def logout(self, token: str) -> None:
        self.db.sessions.delete_one({"token": token})

    def get_user_by_token(self, token: str) -> dict[str, Any] | None:
        session = self.db.sessions.find_one({"token": token})
        if not session:
            return None
        user = self.db.users.find_one({"id": session["user_id"]})
        if not user:
            return None
        return self._serialize_user(user)

    def list_events(self, user_id: int | None = None) -> list[dict[str, Any]]:
        registration_counts = {
            document["_id"]: int(document["count"])
            for document in self.db.registrations.aggregate(
                [{"$group": {"_id": "$event_id", "count": {"$sum": 1}}}]
            )
        }
        registered_event_ids: set[int] = set()
        if user_id is not None:
            registered_event_ids = {
                int(document["event_id"])
                for document in self.db.registrations.find({"user_id": user_id}, {"_id": 0, "event_id": 1})
            }

        events = self.db.events.find({}, sort=[("start_at", ASCENDING)])
        return [
            self._serialize_event(
                document,
                registration_counts.get(document["id"], 0),
                document["id"] in registered_event_ids,
            )
            for document in events
        ]

    def get_event(self, event_id: int, user_id: int | None = None) -> dict[str, Any]:
        document = self.db.events.find_one({"id": event_id})
        if not document:
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")
        registered_count = self.db.registrations.count_documents({"event_id": event_id})
        is_registered = False
        if user_id is not None:
            is_registered = self.db.registrations.find_one({"user_id": user_id, "event_id": event_id}) is not None
        return self._serialize_event(document, registered_count, is_registered)

    def create_event(self, admin_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = self.db.next_sequence("events")
        now = utc_now()
        image_urls = normalize_event_images(payload.get("image_urls"), payload.get("image_url"))
        document = {
            "id": event_id,
            "title": payload["title"].strip(),
            "description": payload["description"].strip(),
            "location": payload["location"].strip(),
            "venue_details": payload.get("venue_details", "").strip(),
            "start_at": payload["start_at"].strip(),
            "capacity": payload["capacity"],
            "price": payload.get("price", 0),
            "image_url": image_urls[0],
            "image_urls": image_urls,
            "opening_highlights": payload.get("opening_highlights", "").strip(),
            "mid_event_highlights": payload.get("mid_event_highlights", "").strip(),
            "closing_highlights": payload.get("closing_highlights", "").strip(),
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now,
            "registered_count": 0,
        }
        self.db.events.insert_one(document)
        return self.get_event(event_id)

    def update_event(self, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        image_urls = normalize_event_images(payload.get("image_urls"), payload.get("image_url"))
        updated = self.db.events.find_one_and_update(
            {"id": event_id},
            {
                "$set": {
                    "title": payload["title"].strip(),
                    "description": payload["description"].strip(),
                    "location": payload["location"].strip(),
                    "venue_details": payload.get("venue_details", "").strip(),
                    "start_at": payload["start_at"].strip(),
                    "capacity": payload["capacity"],
                    "price": payload.get("price", 0),
                    "image_url": image_urls[0],
                    "image_urls": image_urls,
                    "opening_highlights": payload.get("opening_highlights", "").strip(),
                    "mid_event_highlights": payload.get("mid_event_highlights", "").strip(),
                    "closing_highlights": payload.get("closing_highlights", "").strip(),
                    "updated_at": utc_now(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")
        return self.get_event(event_id)

    def delete_event(self, event_id: int) -> None:
        deleted = self.db.events.find_one_and_delete({"id": event_id})
        if not deleted:
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")
        self.db.registrations.delete_many({"event_id": event_id})

    def list_attendees(self, event_id: int) -> list[dict[str, Any]]:
        if not self.db.events.find_one({"id": event_id}):
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")

        registrations = list(self.db.registrations.find({"event_id": event_id}).sort("created_at", ASCENDING))
        user_ids = [registration["user_id"] for registration in registrations]
        users = {document["id"]: document for document in self.db.users.find({"id": {"$in": user_ids}})}
        return [
            {
                "id": users[registration["user_id"]]["id"],
                "name": users[registration["user_id"]]["name"],
                "email": users[registration["user_id"]]["email"],
                "registered_at": registration["created_at"],
            }
            for registration in registrations
            if registration["user_id"] in users
        ]

    def register_for_event(self, user_id: int, event_id: int) -> dict[str, Any]:
        if not self.db.users.find_one({"id": user_id}):
            raise ServiceError(404, "ACCOUNT_NOT_FOUND", "Account does not exist.")

        event = self.db.events.find_one({"id": event_id})
        if not event:
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")

        if self.db.registrations.find_one({"user_id": user_id, "event_id": event_id}):
            raise ServiceError(409, "ALREADY_REGISTERED", "User already registered for this event.")

        reserved = self.db.events.find_one_and_update(
            {"id": event_id, "registered_count": {"$lt": int(event["capacity"])}},
            {"$inc": {"registered_count": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not reserved:
            raise ServiceError(409, "EVENT_FULL", "No seats left for this event.")

        try:
            self.db.registrations.insert_one(
                {
                    "user_id": user_id,
                    "event_id": event_id,
                    "created_at": utc_now(),
                }
            )
        except DuplicateKeyError as exc:
            self.db.events.update_one(
                {"id": event_id, "registered_count": {"$gt": 0}},
                {"$inc": {"registered_count": -1}},
            )
            raise ServiceError(409, "ALREADY_REGISTERED", "User already registered for this event.") from exc

        return self.get_event(event_id, user_id=user_id)

    def cancel_registration(self, user_id: int, event_id: int) -> dict[str, Any]:
        deleted = self.db.registrations.delete_one({"user_id": user_id, "event_id": event_id})
        if deleted.deleted_count == 0:
            raise ServiceError(404, "REGISTRATION_NOT_FOUND", "Registration not found.")

        self.db.events.update_one(
            {"id": event_id, "registered_count": {"$gt": 0}},
            {"$inc": {"registered_count": -1}},
        )
        return self.get_event(event_id, user_id=user_id)

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote_plus

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
SUPPORT_EMAIL = "thienphu210505@gmail.com"
SUPPORT_PHONE = "0365349036"
SUPPORT_LOCATION = "Thu Duc, Ho Chi Minh City"
ACTIVE_REGISTRATION_STATUSES = ("confirmed", "checked_in")


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


def normalize_ticket_types(ticket_types: Any, fallback_price: float) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in ticket_types or []:
        if isinstance(item, dict):
            label = str(item.get("label") or "").strip()
            details = str(item.get("details") or "").strip()
            try:
                price = float(item.get("price", fallback_price or 0) or 0)
            except (TypeError, ValueError):
                price = float(fallback_price or 0)
        else:
            raw = str(item or "").strip()
            if not raw:
                continue
            parts = [part.strip() for part in raw.split("|")]
            label = parts[0] if parts else ""
            details = parts[2] if len(parts) > 2 else ""
            try:
                price = float(parts[1]) if len(parts) > 1 and parts[1] else float(fallback_price or 0)
            except ValueError:
                price = float(fallback_price or 0)
        if not label:
            continue
        candidate = {
            "label": label,
            "price": round(max(price, 0), 2),
            "details": details,
        }
        if candidate not in normalized:
            normalized.append(candidate)

    if normalized:
        return normalized

    default_label = "Free Pass" if float(fallback_price or 0) <= 0 else "General Admission"
    return [{"label": default_label, "price": round(float(fallback_price or 0), 2), "details": "Full event access and standard check-in."}]


def build_ticket_code(event_id: int, user_id: int) -> str:
    return f"EVH-{int(event_id):03d}-{int(user_id):03d}"


def build_ticket_qr_payload(ticket_code: str, title: str, start_at: str) -> str:
    return f"{ticket_code}|{title}|{start_at}"


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
        created_at = utc_now()
        admin_document = self.db.users.find_one({"email": "admin@example.com"})
        if admin_document is None:
            admin_document = self._create_user_document(
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
            self.db.users.insert_one(admin_document)

        student_document = self.db.users.find_one({"email": "student@example.com"})
        if student_document is None:
            student_document = self._create_user_document(
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
            self.db.users.insert_one(student_document)

        admin_id = int(admin_document["id"])
        demo_event_definitions = [
            {
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
            },
            {
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
            },
            {
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
            },
            {
                "title": "Design Systems Sprint Review",
                "description": "A focused review night for product teams refining component systems, interaction polish, and final presentation quality before release week.",
                "location": "Foundry Studio, Thu Duc Innovation Hub",
                "venue_details": "Floor 5, Foundry Studio, Thu Duc Innovation Hub. Reception opens at 6:00 PM, project walls line the north corridor, and guest parking is available beside block B.",
                "start_at": "2026-04-22T18:30:00",
                "capacity": 42,
                "price": 12,
                "image_url": "/static/images/gallery-lounge.svg",
                "image_urls": [
                    "/static/images/gallery-lounge.svg",
                    "/static/images/gallery-stage.svg",
                    "/static/images/gallery-foyer.svg",
                ],
                "opening_highlights": "Fast walkthrough of the latest design systems, critique framing, and artifact wall setup for mentors and guests.",
                "mid_event_highlights": "Component reviews, motion polish checks, accessibility critique rounds, and feedback capture directly into release boards.",
                "closing_highlights": "Closing recap with shortlist awards, revision priorities, and a small networking circle for internship-ready teams.",
            },
            {
                "title": "Cloud Ops Night",
                "description": "An after-hours event for teams rehearsing deployment, observability, and incident response with mentors before shipping their capstone systems.",
                "location": "Skyline Lab, Saigon Digital Campus",
                "venue_details": "Skyline Lab, Building C, Saigon Digital Campus, Thu Duc. Entry from lobby C after 5:45 PM, ops dashboard wall is on the west side, and the coffee station runs all evening.",
                "start_at": "2026-04-26T19:00:00",
                "capacity": 36,
                "price": 16,
                "image_url": "/static/images/gallery-stage.svg",
                "image_urls": [
                    "/static/images/gallery-stage.svg",
                    "/static/images/gallery-lounge.svg",
                    "/static/images/gallery-foyer.svg",
                ],
                "opening_highlights": "Opening deploy check, infra readiness briefing, and incident game rules explained by the ops mentors.",
                "mid_event_highlights": "Log tracing drills, rollback rehearsal, dashboard review, and guided SRE-style response for simulated outages.",
                "closing_highlights": "Post-mortem debrief, release confidence scoring, and team handoff notes for the final week before defense.",
            },
        ]

        existing_titles = {document["title"] for document in self.db.events.find({}, {"_id": 0, "title": 1})}
        missing_events = []
        for event_definition in demo_event_definitions:
            if event_definition["title"] in existing_titles:
                continue
            missing_events.append(
                {
                    "id": self.db.next_sequence("events"),
                    **event_definition,
                    "created_by": admin_id,
                    "created_at": created_at,
                    "updated_at": created_at,
                    "registered_count": 0,
                }
            )

        if missing_events:
            self.db.events.insert_many(missing_events)

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
        avatar_url: str = "",
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
            "avatar_url": str(avatar_url or "").strip(),
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
            "avatar_url": str(document.get("avatar_url", "") or "").strip(),
            **normalized_profile,
        }

    def _default_event_profile(self, document: dict[str, Any]) -> dict[str, Any]:
        title = str(document.get("title") or "").strip()
        location = str(document.get("location") or "").strip()
        price = float(document.get("price", 0) or 0)
        start_at = str(document.get("start_at") or "").strip()
        defaults = {
            "category": "Special Event",
            "event_format": "Offline",
            "organizer_name": "EventHub Verify Studio",
            "organizer_details": "Managed through the EventHub Verify admin workspace.",
            "speaker_lineup": ["EventHub Verify Team - Host and onsite coordination"],
            "registration_deadline": start_at,
            "map_url": f"https://www.google.com/maps/search/?api=1&query={quote_plus(location)}" if location else "",
            "refund_policy": "Full refund up to 48 hours before the event. No refund after the check-in window opens.",
            "check_in_policy": "Bring your ticket code or booking email and arrive 20 minutes before the stated start time.",
            "contact_email": SUPPORT_EMAIL,
            "contact_phone": SUPPORT_PHONE,
            "ticket_types": normalize_ticket_types(document.get("ticket_types"), price),
        }
        if title == "AI Career Night":
            defaults.update(
                {
                    "category": "Career Networking",
                    "organizer_name": "EventHub Verify x AI Club",
                    "organizer_details": "A curated evening for AI students, lab mentors, and startup recruiters who prefer long-form conversations over quick booth pitches.",
                    "speaker_lineup": [
                        "Lan Nguyen - Talent Partner, Aster Labs",
                        "Minh Tran - Founder, ProtoVision AI",
                        "Gia Bao - Career Coach, EventHub Verify",
                    ],
                    "registration_deadline": "2026-04-10T12:00:00",
                    "ticket_types": normalize_ticket_types(
                        [
                            {"label": "Student Pass", "price": 29, "details": "Entry, welcome drink, and open networking floor."},
                            {"label": "Portfolio Review", "price": 49, "details": "Includes one recruiter portfolio review slot."},
                        ],
                        price,
                    ),
                }
            )
        elif title == "Software Verification Workshop":
            defaults.update(
                {
                    "category": "Workshop",
                    "organizer_name": "EventHub Verify x SE113 Lab",
                    "organizer_details": "A guided studio day for teams who want a stronger release workflow before project defense and internship demos.",
                    "speaker_lineup": [
                        "Trung Kien - QA Lead, Orchid Tech Loft",
                        "Thanh Phuc - CI Mentor, SE113",
                        "Mai Linh - Product QA Coach",
                    ],
                    "registration_deadline": "2026-04-11T18:00:00",
                    "ticket_types": normalize_ticket_types(
                        [
                            {"label": "Workshop Seat", "price": 24, "details": "Standard seat with breakfast and guided labs."},
                            {"label": "Team Table", "price": 60, "details": "Three-seat team bundle with mentor feedback block."},
                        ],
                        price,
                    ),
                }
            )
        elif title == "Startup Pitch Day":
            defaults.update(
                {
                    "category": "Showcase",
                    "organizer_name": "EventHub Verify x Founder Circle",
                    "organizer_details": "An event-night format for student founders, mentors, and guests who want to experience products, not just watch slides.",
                    "speaker_lineup": [
                        "An Khang - Program Host",
                        "Thu Ha - Investor Relations, Riverside Creative",
                        "Bao Chau - Community Lead, Founder Circle",
                    ],
                    "registration_deadline": "2026-04-18T10:00:00",
                    "ticket_types": normalize_ticket_types(
                        [
                            {"label": "Guest Pass", "price": 18, "details": "Standard audience access and tasting stations."},
                            {"label": "Founder Circle", "price": 35, "details": "Priority seating and post-pitch mixer access."},
                        ],
                        price,
                    ),
                }
            )
        return defaults

    def _normalize_event_document(self, document: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(document)
        defaults = self._default_event_profile(normalized)
        for key, value in defaults.items():
            current = normalized.get(key)
            if current in (None, "", []):
                normalized[key] = value
        normalized["image_urls"] = normalize_event_images(normalized.get("image_urls"), normalized.get("image_url"))
        normalized["image_url"] = normalized["image_urls"][0]
        normalized["speaker_lineup"] = [item for item in [str(item or "").strip() for item in normalized.get("speaker_lineup", [])] if item]
        normalized["ticket_types"] = normalize_ticket_types(normalized.get("ticket_types"), normalized.get("price", 0))
        normalized["price"] = round(min(ticket["price"] for ticket in normalized["ticket_types"]), 2)
        normalized["category"] = str(normalized.get("category") or defaults["category"]).strip()
        normalized["event_format"] = str(normalized.get("event_format") or defaults["event_format"]).strip()
        normalized["organizer_name"] = str(normalized.get("organizer_name") or defaults["organizer_name"]).strip()
        normalized["organizer_details"] = str(normalized.get("organizer_details") or defaults["organizer_details"]).strip()
        normalized["registration_deadline"] = str(normalized.get("registration_deadline") or defaults["registration_deadline"]).strip()
        normalized["map_url"] = str(normalized.get("map_url") or defaults["map_url"]).strip()
        normalized["refund_policy"] = str(normalized.get("refund_policy") or defaults["refund_policy"]).strip()
        normalized["check_in_policy"] = str(normalized.get("check_in_policy") or defaults["check_in_policy"]).strip()
        normalized["contact_email"] = str(normalized.get("contact_email") or defaults["contact_email"]).strip().lower()
        normalized["contact_phone"] = str(normalized.get("contact_phone") or defaults["contact_phone"]).strip()
        return normalized

    def _select_ticket_type(self, event_document: dict[str, Any], ticket_label: str = "") -> dict[str, Any]:
        ticket_types = normalize_ticket_types(event_document.get("ticket_types"), event_document.get("price", 0))
        requested = str(ticket_label or "").strip().lower()
        if requested:
            for ticket in ticket_types:
                if ticket["label"].strip().lower() == requested:
                    return ticket
        return ticket_types[0]

    def _is_active_registration(self, registration: dict[str, Any] | None) -> bool:
        if not registration:
            return False
        return str(registration.get("status") or "confirmed") in ACTIVE_REGISTRATION_STATUSES

    def _active_registration_query(self) -> dict[str, Any]:
        return {"status": {"$in": list(ACTIVE_REGISTRATION_STATUSES)}}

    def _serialize_ticket(self, registration: dict[str, Any], event_document: dict[str, Any]) -> dict[str, Any]:
        event = self._normalize_event_document(event_document)
        ticket = self._select_ticket_type(event, registration.get("ticket_label", ""))
        ticket_code = str(registration.get("ticket_code") or build_ticket_code(event["id"], registration["user_id"]))
        registered_at = str(registration.get("registered_at") or registration.get("created_at") or utc_now())
        return {
            "event_id": event["id"],
            "title": event["title"],
            "category": event["category"],
            "event_format": event["event_format"],
            "location": event["location"],
            "start_at": event["start_at"],
            "image_url": event["image_url"],
            "ticket_code": ticket_code,
            "ticket_label": str(registration.get("ticket_label") or ticket["label"]),
            "ticket_price": round(float(registration.get("ticket_price", ticket["price"]) or 0), 2),
            "attendee_name": str(registration.get("attendee_name") or ""),
            "attendee_email": str(registration.get("attendee_email") or ""),
            "attendee_phone": str(registration.get("attendee_phone") or ""),
            "status": str(registration.get("status") or "confirmed"),
            "registered_at": registered_at,
            "cancelled_at": registration.get("cancelled_at"),
            "qr_payload": str(registration.get("qr_payload") or build_ticket_qr_payload(ticket_code, event["title"], event["start_at"])),
        }

    def _serialize_event(
        self,
        document: dict[str, Any],
        registered_count: int,
        is_registered: bool,
    ) -> dict[str, Any]:
        normalized = self._normalize_event_document(document)
        capacity = int(normalized["capacity"])
        return {
            "id": normalized["id"],
            "title": normalized["title"],
            "description": normalized["description"],
            "category": normalized["category"],
            "event_format": normalized["event_format"],
            "location": normalized["location"],
            "venue_details": normalized.get("venue_details", ""),
            "start_at": normalized["start_at"],
            "registration_deadline": normalized["registration_deadline"],
            "capacity": capacity,
            "price": normalized.get("price", 0),
            "organizer_name": normalized["organizer_name"],
            "organizer_details": normalized["organizer_details"],
            "speaker_lineup": normalized["speaker_lineup"],
            "image_url": normalized["image_url"],
            "image_urls": normalized["image_urls"],
            "map_url": normalized["map_url"],
            "refund_policy": normalized["refund_policy"],
            "check_in_policy": normalized["check_in_policy"],
            "contact_email": normalized["contact_email"],
            "contact_phone": normalized["contact_phone"],
            "ticket_types": normalized["ticket_types"],
            "opening_highlights": normalized.get("opening_highlights", ""),
            "mid_event_highlights": normalized.get("mid_event_highlights", ""),
            "closing_highlights": normalized.get("closing_highlights", ""),
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
        events = [self._normalize_event_document(document) for document in self.db.events.find({}, sort=[("start_at", ASCENDING)])]
        registrations = [registration for registration in self.db.registrations.find({}) if self._is_active_registration(registration)]
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
            sum(
                float(registration.get("ticket_price", event.get("price", 0)) or 0)
                for event in events
                for registration in registrations_by_event.get(event["id"], [])
            ),
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
            revenue = round(sum(float(registration.get("ticket_price", event.get("price", 0)) or 0) for registration in event_registrations), 2)
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

    def update_user_profile(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.db.users.find_one({"id": user_id}):
            raise ServiceError(404, "ACCOUNT_NOT_FOUND", "Account does not exist.")

        normalized_phone_local = normalize_phone_local_number(payload["phone_local_number"], payload["phone_country_code"])
        updated = self.db.users.find_one_and_update(
            {"id": user_id},
            {
                "$set": {
                    "name": payload["name"].strip(),
                    "date_of_birth": payload["date_of_birth"].strip(),
                    "country": payload["country"].strip(),
                    "province": payload["province"].strip(),
                    "district": payload["district"].strip(),
                    "ward": payload.get("ward", "").strip(),
                    "street_address": payload["street_address"].strip(),
                    "permanent_address": build_permanent_address(
                        payload["street_address"].strip(),
                        payload.get("ward", "").strip(),
                        payload["district"].strip(),
                        payload["province"].strip(),
                        payload["country"].strip(),
                    ),
                    "phone_country_code": payload["phone_country_code"].strip(),
                    "phone_country_label": payload["phone_country_label"].strip(),
                    "phone_country_flag": payload["phone_country_flag"].strip().lower(),
                    "phone_local_number": normalized_phone_local,
                    "phone_number": build_phone_number(payload["phone_country_code"].strip(), normalized_phone_local),
                    "avatar_url": str(payload.get("avatar_url", "") or "").strip(),
                    "updated_at": utc_now(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise ServiceError(404, "ACCOUNT_NOT_FOUND", "Account does not exist.")
        return self._serialize_user(updated)

    def list_user_registrations(self, user_id: int) -> list[dict[str, Any]]:
        if not self.db.users.find_one({"id": user_id}):
            raise ServiceError(404, "ACCOUNT_NOT_FOUND", "Account does not exist.")

        registrations = list(self.db.registrations.find({"user_id": user_id}).sort([("registered_at", -1), ("created_at", -1)]))
        event_ids = sorted({int(registration["event_id"]) for registration in registrations})
        events = {document["id"]: document for document in self.db.events.find({"id": {"$in": event_ids}})}
        return [
            self._serialize_ticket(registration, events[registration["event_id"]])
            for registration in registrations
            if registration["event_id"] in events
        ]

    def list_events(self, user_id: int | None = None) -> list[dict[str, Any]]:
        active_query = self._active_registration_query()
        registration_counts = {
            document["_id"]: int(document["count"])
            for document in self.db.registrations.aggregate(
                [{"$match": active_query}, {"$group": {"_id": "$event_id", "count": {"$sum": 1}}}]
            )
        }
        registered_event_ids: set[int] = set()
        if user_id is not None:
            registered_event_ids = {
                int(document["event_id"])
                for document in self.db.registrations.find({**active_query, "user_id": user_id}, {"_id": 0, "event_id": 1})
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
        active_query = self._active_registration_query()
        registered_count = self.db.registrations.count_documents({**active_query, "event_id": event_id})
        is_registered = False
        if user_id is not None:
            is_registered = self.db.registrations.find_one({**active_query, "user_id": user_id, "event_id": event_id}) is not None
        return self._serialize_event(document, registered_count, is_registered)

    def create_event(self, admin_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = self.db.next_sequence("events")
        now = utc_now()
        document = self._normalize_event_document(
            {
                "id": event_id,
                "title": payload["title"].strip(),
                "description": payload["description"].strip(),
                "category": str(payload.get("category", "") or "").strip(),
                "event_format": str(payload.get("event_format", "") or "").strip(),
                "location": payload["location"].strip(),
                "venue_details": payload.get("venue_details", "").strip(),
                "start_at": payload["start_at"].strip(),
                "registration_deadline": str(payload.get("registration_deadline", "") or "").strip(),
                "capacity": payload["capacity"],
                "price": payload.get("price", 0),
                "organizer_name": str(payload.get("organizer_name", "") or "").strip(),
                "organizer_details": str(payload.get("organizer_details", "") or "").strip(),
                "speaker_lineup": payload.get("speaker_lineup", []),
                "image_url": payload.get("image_url"),
                "image_urls": payload.get("image_urls", []),
                "map_url": str(payload.get("map_url", "") or "").strip(),
                "refund_policy": str(payload.get("refund_policy", "") or "").strip(),
                "check_in_policy": str(payload.get("check_in_policy", "") or "").strip(),
                "contact_email": str(payload.get("contact_email", "") or "").strip().lower(),
                "contact_phone": str(payload.get("contact_phone", "") or "").strip(),
                "ticket_types": payload.get("ticket_types", []),
                "opening_highlights": payload.get("opening_highlights", "").strip(),
                "mid_event_highlights": payload.get("mid_event_highlights", "").strip(),
                "closing_highlights": payload.get("closing_highlights", "").strip(),
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now,
                "registered_count": 0,
            }
        )
        self.db.events.insert_one(document)
        return self.get_event(event_id)

    def update_event(self, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.db.events.find_one({"id": event_id})
        if not current:
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")

        normalized = self._normalize_event_document(
            {
                **current,
                "title": payload["title"].strip(),
                "description": payload["description"].strip(),
                "category": str(payload.get("category", current.get("category", "")) or "").strip(),
                "event_format": str(payload.get("event_format", current.get("event_format", "")) or "").strip(),
                "location": payload["location"].strip(),
                "venue_details": payload.get("venue_details", "").strip(),
                "start_at": payload["start_at"].strip(),
                "registration_deadline": str(payload.get("registration_deadline", current.get("registration_deadline", "")) or "").strip(),
                "capacity": payload["capacity"],
                "price": payload.get("price", 0),
                "organizer_name": str(payload.get("organizer_name", current.get("organizer_name", "")) or "").strip(),
                "organizer_details": str(payload.get("organizer_details", current.get("organizer_details", "")) or "").strip(),
                "speaker_lineup": payload.get("speaker_lineup", current.get("speaker_lineup", [])),
                "image_url": payload.get("image_url"),
                "image_urls": payload.get("image_urls", []),
                "map_url": str(payload.get("map_url", current.get("map_url", "")) or "").strip(),
                "refund_policy": str(payload.get("refund_policy", current.get("refund_policy", "")) or "").strip(),
                "check_in_policy": str(payload.get("check_in_policy", current.get("check_in_policy", "")) or "").strip(),
                "contact_email": str(payload.get("contact_email", current.get("contact_email", "")) or "").strip().lower(),
                "contact_phone": str(payload.get("contact_phone", current.get("contact_phone", "")) or "").strip(),
                "ticket_types": payload.get("ticket_types", current.get("ticket_types", [])),
                "opening_highlights": payload.get("opening_highlights", "").strip(),
                "mid_event_highlights": payload.get("mid_event_highlights", "").strip(),
                "closing_highlights": payload.get("closing_highlights", "").strip(),
                "updated_at": utc_now(),
            }
        )

        updated = self.db.events.find_one_and_update(
            {"id": event_id},
            {
                "$set": {
                    "title": normalized["title"],
                    "description": normalized["description"],
                    "category": normalized["category"],
                    "event_format": normalized["event_format"],
                    "location": normalized["location"],
                    "venue_details": normalized["venue_details"],
                    "start_at": normalized["start_at"],
                    "registration_deadline": normalized["registration_deadline"],
                    "capacity": normalized["capacity"],
                    "price": normalized["price"],
                    "organizer_name": normalized["organizer_name"],
                    "organizer_details": normalized["organizer_details"],
                    "speaker_lineup": normalized["speaker_lineup"],
                    "image_url": normalized["image_url"],
                    "image_urls": normalized["image_urls"],
                    "map_url": normalized["map_url"],
                    "refund_policy": normalized["refund_policy"],
                    "check_in_policy": normalized["check_in_policy"],
                    "contact_email": normalized["contact_email"],
                    "contact_phone": normalized["contact_phone"],
                    "ticket_types": normalized["ticket_types"],
                    "opening_highlights": normalized["opening_highlights"],
                    "mid_event_highlights": normalized["mid_event_highlights"],
                    "closing_highlights": normalized["closing_highlights"],
                    "updated_at": normalized["updated_at"],
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

        registrations = list(self.db.registrations.find({**self._active_registration_query(), "event_id": event_id}).sort("registered_at", ASCENDING))
        user_ids = [registration["user_id"] for registration in registrations]
        users = {document["id"]: document for document in self.db.users.find({"id": {"$in": user_ids}})}
        return [
            {
                "id": users[registration["user_id"]]["id"],
                "name": registration.get("attendee_name") or users[registration["user_id"]]["name"],
                "email": registration.get("attendee_email") or users[registration["user_id"]]["email"],
                "registered_at": registration.get("registered_at") or registration.get("created_at") or utc_now(),
                "ticket_label": registration.get("ticket_label") or "General Admission",
                "status": registration.get("status") or "confirmed",
            }
            for registration in registrations
            if registration["user_id"] in users
        ]

    def register_for_event(self, user_id: int, event_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        user = self.db.users.find_one({"id": user_id})
        if not user:
            raise ServiceError(404, "ACCOUNT_NOT_FOUND", "Account does not exist.")

        event_document = self.db.events.find_one({"id": event_id})
        if not event_document:
            raise ServiceError(404, "EVENT_NOT_FOUND", "Event not found.")
        event = self._normalize_event_document(event_document)

        existing_registration = self.db.registrations.find_one({"user_id": user_id, "event_id": event_id})
        if self._is_active_registration(existing_registration):
            raise ServiceError(409, "ALREADY_REGISTERED", "User already registered for this event.")

        reserved = self.db.events.find_one_and_update(
            {"id": event_id, "registered_count": {"$lt": int(event["capacity"])}},
            {"$inc": {"registered_count": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not reserved:
            raise ServiceError(409, "EVENT_FULL", "No seats left for this event.")

        payload = payload or {}
        normalized_profile = self._normalize_user_profile(user)
        selected_ticket = self._select_ticket_type(event, payload.get("ticket_label", ""))
        now = utc_now()
        ticket_code = str(existing_registration.get("ticket_code") if existing_registration else "") or build_ticket_code(event_id, user_id)
        registration_document = {
            "user_id": user_id,
            "event_id": event_id,
            "created_at": existing_registration.get("created_at", now) if existing_registration else now,
            "registered_at": now,
            "status": "confirmed",
            "ticket_label": selected_ticket["label"],
            "ticket_price": selected_ticket["price"],
            "ticket_code": ticket_code,
            "qr_payload": build_ticket_qr_payload(ticket_code, event["title"], event["start_at"]),
            "attendee_name": str(payload.get("attendee_name") or user["name"]).strip(),
            "attendee_email": str(payload.get("attendee_email") or user["email"]).strip().lower(),
            "attendee_phone": str(payload.get("attendee_phone") or normalized_profile["phone_number"]).strip(),
        }

        try:
            if existing_registration:
                self.db.registrations.update_one(
                    {"_id": existing_registration["_id"]},
                    {"$set": registration_document, "$unset": {"cancelled_at": ""}},
                )
            else:
                self.db.registrations.insert_one(registration_document)
        except DuplicateKeyError as exc:
            self.db.events.update_one(
                {"id": event_id, "registered_count": {"$gt": 0}},
                {"$inc": {"registered_count": -1}},
            )
            raise ServiceError(409, "ALREADY_REGISTERED", "User already registered for this event.") from exc

        return self.get_event(event_id, user_id=user_id)

    def cancel_registration(self, user_id: int, event_id: int) -> dict[str, Any]:
        cancelled = self.db.registrations.find_one_and_update(
            {**self._active_registration_query(), "user_id": user_id, "event_id": event_id},
            {"$set": {"status": "cancelled", "cancelled_at": utc_now()}},
            return_document=ReturnDocument.BEFORE,
        )
        if not cancelled:
            raise ServiceError(404, "REGISTRATION_NOT_FOUND", "Registration not found.")

        self.db.events.update_one(
            {"id": event_id, "registered_count": {"$gt": 0}},
            {"$inc": {"registered_count": -1}},
        )
        return self.get_event(event_id, user_id=user_id)

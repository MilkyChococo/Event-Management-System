from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        settings = Settings(
            env="test",
            mongo_uri="mongodb://unused",
            mongo_db_name=f"api_test_{uuid.uuid4().hex}",
            secret="test-secret",
            seed_demo=True,
            use_mock_db=True,
        )
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def login(self, email: str, password: str) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200)

    def test_register_login_and_get_me(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "name": "API User",
                "date_of_birth": "2003-03-12",
                "country": "Vietnam",
                "province": "Ho Chi Minh City",
                "district": "Go Vap District",
                "ward": "Ward 3",
                "street_address": "12 API Street",
                "phone_country_code": "+84",
                "phone_country_label": "Vietnam",
                "phone_country_flag": "vn",
                "phone_local_number": "912000000",
                "email": "api.user@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        self.login("api.user@example.com", "Password123!")
        me_response = self.client.get("/api/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["email"], "api.user@example.com")
        self.assertEqual(me_response.json()["age"], 23)
        self.assertEqual(me_response.json()["country"], "Vietnam")
        self.assertEqual(me_response.json()["district"], "Go Vap District")
        self.assertEqual(me_response.json()["phone_country_code"], "+84")
        self.assertEqual(me_response.json()["phone_number"], "+84 912000000")
        self.assertIn("Ho Chi Minh City", me_response.json()["permanent_address"])

    def test_login_validation_error_returns_human_message(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "student@example.com", "password": "123456"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response.json()["error"]["message"], "Password must be at least 8 characters.")

    def test_unknown_account_is_not_authenticated(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "missing@example.com", "password": "Password123!"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_NOT_FOUND")

    def test_regular_user_cannot_access_admin_routes(self) -> None:
        self.login("student@example.com", "Student123!")

        response = self.client.post(
            "/api/admin/events",
            json={
                "title": "Forbidden Event",
                "description": "This should fail for a normal user.",
                "location": "Secret Room",
                "start_at": "2026-05-11T10:00:00",
                "capacity": 10,
                "price": 50,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_regular_user_cannot_view_admin_analytics(self) -> None:
        self.login("student@example.com", "Student123!")

        response = self.client.get("/api/admin/analytics")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_admin_manager_page_requires_admin(self) -> None:
        self.login("student@example.com", "Student123!")
        forbidden_response = self.client.get("/admin/manager")
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        allowed_response = self.client.get("/admin/manager")
        self.assertEqual(allowed_response.status_code, 200)
        self.assertIn("text/html", allowed_response.headers.get("content-type", ""))

    def test_admin_can_view_analytics_with_distribution_and_revenue(self) -> None:
        self.login("student@example.com", "Student123!")
        event = self.client.get("/api/events").json()[0]
        event_id = event["id"]
        event_price = event["price"]

        first_registration = self.client.post(f"/api/events/{event_id}/register")
        self.assertEqual(first_registration.status_code, 200)

        self.client.post("/api/auth/logout")
        second_user_response = self.client.post(
            "/api/auth/register",
            json={
                "name": "US Guest",
                "date_of_birth": "1994-04-18",
                "country": "United States",
                "province": "California",
                "district": "San Francisco County",
                "ward": "",
                "street_address": "1 Market Street",
                "phone_country_code": "+1",
                "phone_country_label": "United States",
                "phone_country_flag": "us",
                "phone_local_number": "4155550101",
                "email": "guest.us@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(second_user_response.status_code, 201)

        self.login("guest.us@example.com", "Password123!")
        second_registration = self.client.post(f"/api/events/{event_id}/register")
        self.assertEqual(second_registration.status_code, 200)

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        analytics_response = self.client.get("/api/admin/analytics")

        self.assertEqual(analytics_response.status_code, 200)
        analytics = analytics_response.json()
        self.assertEqual(analytics["summary"]["total_registrations"], 2)
        self.assertAlmostEqual(analytics["summary"]["total_revenue"], event_price * 2)
        self.assertEqual(analytics["summary"]["domestic_customer_ratio"], 50.0)
        self.assertEqual(analytics["summary"]["international_customer_ratio"], 50.0)

        customer_mix = {item["label"]: item["count"] for item in analytics["customer_mix"]}
        self.assertEqual(customer_mix["Vietnam"], 1)
        self.assertEqual(customer_mix["International"], 1)

        event_analytics = next(item for item in analytics["events"] if item["event_id"] == event_id)
        self.assertEqual(event_analytics["registered_count"], 2)
        self.assertAlmostEqual(event_analytics["revenue"], event_price * 2)
        self.assertEqual(event_analytics["share_of_registrations"], 100.0)

        age_distribution = {item["label"]: item["count"] for item in event_analytics["age_distribution"]}
        self.assertEqual(age_distribution["20-24"], 1)
        self.assertEqual(age_distribution["30+"], 1)

        country_distribution = {item["label"]: item["count"] for item in event_analytics["country_distribution"]}
        self.assertEqual(country_distribution["Vietnam"], 1)
        self.assertEqual(country_distribution["United States"], 1)

    def test_admin_can_create_event(self) -> None:
        self.login("admin@example.com", "Admin123!")

        response = self.client.post(
            "/api/admin/events",
            json={
                "title": "Verification Showcase",
                "description": "Admin creates an event for the final sprint review.",
                "location": "Main Hall",
                "start_at": "2026-05-10T15:00:00",
                "capacity": 42,
                "price": 120,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Verification Showcase")

    def test_event_registration_fails_when_balance_is_not_enough(self) -> None:
        self.login("admin@example.com", "Admin123!")
        create_response = self.client.post(
            "/api/admin/events",
            json={
                "title": "Premium Reservation",
                "description": "Expensive event used to verify insufficient balance responses.",
                "location": "Vault Hall",
                "start_at": "2026-05-12T20:00:00",
                "capacity": 8,
                "price": 250,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        self.client.post("/api/auth/logout")
        self.login("student@example.com", "Student123!")

        register_response = self.client.post(
            f"/api/events/{event_id}/register",
            json={"quantity": 1},
        )
        self.assertEqual(register_response.status_code, 402)
        self.assertEqual(register_response.json()["error"]["code"], "INSUFFICIENT_FUNDS")

        events_response = self.client.get("/api/events")
        self.assertEqual(events_response.status_code, 200)
        event = next(item for item in events_response.json() if item["id"] == event_id)
        self.assertEqual(event["registered_count"], 0)

    def test_admin_can_update_and_delete_event(self) -> None:
        self.login("admin@example.com", "Admin123!")

        create_response = self.client.post(
            "/api/admin/events",
            json={
                "title": "Draft Event",
                "description": "Initial version before admin updates the event.",
                "location": "Room D1",
                "start_at": "2026-05-12T11:00:00",
                "capacity": 15,
                "price": 10,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        update_response = self.client.put(
            f"/api/admin/events/{event_id}",
            json={
                "title": "Updated Draft Event",
                "description": "Updated version after admin review.",
                "location": "Room D2",
                "start_at": "2026-05-12T13:00:00",
                "capacity": 25,
                "price": 25,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["title"], "Updated Draft Event")

        delete_response = self.client.delete(f"/api/admin/events/{event_id}")
        self.assertEqual(delete_response.status_code, 200)

    def test_admin_can_update_and_clear_event_gallery(self) -> None:
        self.login("admin@example.com", "Admin123!")

        create_response = self.client.post(
            "/api/admin/events",
            json={
                "title": "Image Draft Event",
                "description": "Admin verifies gallery editing and removal.",
                "location": "Room D3",
                "start_at": "2026-05-14T14:00:00",
                "capacity": 20,
                "price": 15,
                "image_urls": [
                    "https://example.com/custom-event-1.jpg",
                    "https://example.com/custom-event-2.jpg",
                ],
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]
        self.assertEqual(create_response.json()["image_url"], "https://example.com/custom-event-1.jpg")
        self.assertEqual(
            create_response.json()["image_urls"],
            [
                "https://example.com/custom-event-1.jpg",
                "https://example.com/custom-event-2.jpg",
            ],
        )

        update_response = self.client.put(
            f"/api/admin/events/{event_id}",
            json={
                "title": "Image Draft Event",
                "description": "Admin verifies gallery editing and removal.",
                "location": "Room D3",
                "start_at": "2026-05-14T14:00:00",
                "capacity": 20,
                "price": 15,
                "image_urls": [
                    "https://example.com/custom-event-2.jpg",
                    "https://example.com/custom-event-3.jpg",
                ],
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["image_url"], "https://example.com/custom-event-2.jpg")
        self.assertEqual(
            update_response.json()["image_urls"],
            [
                "https://example.com/custom-event-2.jpg",
                "https://example.com/custom-event-3.jpg",
            ],
        )

        clear_response = self.client.put(
            f"/api/admin/events/{event_id}",
            json={
                "title": "Image Draft Event",
                "description": "Admin verifies gallery editing and removal.",
                "location": "Room D3",
                "start_at": "2026-05-14T14:00:00",
                "capacity": 20,
                "price": 15,
                "image_urls": [],
                "image_url": "",
            },
        )
        self.assertEqual(clear_response.status_code, 200)
        self.assertEqual(clear_response.json()["image_url"], "/static/images/default-event.svg")
        self.assertEqual(clear_response.json()["image_urls"], ["/static/images/default-event.svg"])

    def test_seeded_event_contains_richer_detail_fields(self) -> None:
        response = self.client.get("/api/events/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mercer Street", response.json()["venue_details"])
        self.assertTrue(response.json()["opening_highlights"])
        self.assertTrue(response.json()["mid_event_highlights"])
        self.assertTrue(response.json()["closing_highlights"])
        self.assertGreaterEqual(len(response.json()["image_urls"]), 2)

    def test_admin_can_view_attendee_list(self) -> None:
        self.login("student@example.com", "Student123!")
        event_id = self.client.get("/api/events").json()[0]["id"]
        register_response = self.client.post(f"/api/events/{event_id}/register")
        self.assertEqual(register_response.status_code, 200)

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        attendees_response = self.client.get(f"/api/events/{event_id}/registrations")

        self.assertEqual(attendees_response.status_code, 200)
        self.assertGreaterEqual(len(attendees_response.json()), 1)
        self.assertEqual(attendees_response.json()[0]["email"], "student@example.com")

    def test_user_can_register_then_cancel(self) -> None:
        self.login("student@example.com", "Student123!")
        events_response = self.client.get("/api/events")
        event_id = events_response.json()[0]["id"]

        register_response = self.client.post(f"/api/events/{event_id}/register")
        self.assertEqual(register_response.status_code, 200)
        self.assertTrue(register_response.json()["is_registered"])

        cancel_response = self.client.delete(f"/api/events/{event_id}/register")
        self.assertEqual(cancel_response.status_code, 200)
        self.assertFalse(cancel_response.json()["is_registered"])

    def test_user_can_reserve_up_to_five_tickets_in_one_booking(self) -> None:
        self.login("admin@example.com", "Admin123!")
        create_response = self.client.post(
            "/api/admin/events",
            json={
                "title": "Quantity API Event",
                "description": "API verifies quantity-based reservations on a single booking.",
                "location": "Hall Q",
                "start_at": "2026-05-18T19:00:00",
                "capacity": 10,
                "price": 12,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        self.client.post("/api/auth/logout")
        self.login("student@example.com", "Student123!")

        register_response = self.client.post(
            f"/api/events/{event_id}/register",
            json={
                "quantity": 5,
                "attendee_name": "Student Demo",
                "attendee_email": "student@example.com",
                "attendee_phone": "+84 912345678",
            },
        )
        self.assertEqual(register_response.status_code, 200)
        self.assertEqual(register_response.json()["registered_count"], 5)
        self.assertEqual(register_response.json()["seats_left"], 5)

        tickets_response = self.client.get("/api/me/registrations")
        self.assertEqual(tickets_response.status_code, 200)
        quantity_ticket = next(ticket for ticket in tickets_response.json() if ticket["event_id"] == event_id)
        self.assertEqual(quantity_ticket["quantity"], 5)
        self.assertEqual(quantity_ticket["total_price"], 60)

    def test_api_rejects_more_than_five_tickets_per_account(self) -> None:
        self.login("student@example.com", "Student123!")
        event_id = self.client.get("/api/events").json()[0]["id"]

        response = self.client.post(
            f"/api/events/{event_id}/register",
            json={
                "quantity": 6,
                "attendee_name": "Student Demo",
                "attendee_email": "student@example.com",
                "attendee_phone": "+84 912345678",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_user_registration_history_returns_ticket_status(self) -> None:
        self.login("student@example.com", "Student123!")
        event_id = self.client.get("/api/events").json()[0]["id"]

        register_response = self.client.post(
            f"/api/events/{event_id}/register",
            json={
                "ticket_label": "Workshop Seat",
                "attendee_name": "Student Demo",
                "attendee_email": "student@example.com",
                "attendee_phone": "+84 912345678",
            },
        )
        self.assertEqual(register_response.status_code, 200)

        tickets_response = self.client.get("/api/me/registrations")
        self.assertEqual(tickets_response.status_code, 200)
        self.assertEqual(len(tickets_response.json()), 1)
        self.assertEqual(tickets_response.json()[0]["status"], "confirmed")
        self.assertTrue(tickets_response.json()[0]["ticket_code"])

        cancel_response = self.client.delete(f"/api/events/{event_id}/register")
        self.assertEqual(cancel_response.status_code, 200)

        cancelled_tickets_response = self.client.get("/api/me/registrations")
        self.assertEqual(cancelled_tickets_response.status_code, 200)
        self.assertEqual(cancelled_tickets_response.json()[0]["status"], "cancelled")
        self.assertTrue(cancelled_tickets_response.json()[0]["cancelled_at"])
    def test_user_can_top_up_wallet_and_view_wallet_overview(self) -> None:
        self.login("student@example.com", "Student123!")

        top_up_response = self.client.post(
            "/api/me/wallet/top-up",
            json={
                "amount": 25,
                "provider": "QR transfer",
                "note": "Coursework wallet top-up",
            },
        )
        self.assertEqual(top_up_response.status_code, 200)
        self.assertTrue(top_up_response.json()["pending_top_up"]["qr_payload"])
        self.assertEqual(top_up_response.json()["pending_top_up"]["status"], "pending")

        wallet_response = self.client.get("/api/me/wallet")
        self.assertEqual(wallet_response.status_code, 200)
        self.assertEqual(len(wallet_response.json()["transactions"]), 0)
        self.assertIsNotNone(wallet_response.json()["pending_top_up"])

        confirm_response = self.client.post("/api/me/wallet/top-up/confirm")
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["transaction"]["kind"], "top_up")
        self.assertGreater(confirm_response.json()["user"]["balance"], 120)

        wallet_after_confirm = self.client.get("/api/me/wallet")
        self.assertEqual(wallet_after_confirm.status_code, 200)
        self.assertGreaterEqual(len(wallet_after_confirm.json()["transactions"]), 1)
        self.assertIsNone(wallet_after_confirm.json()["pending_top_up"])

    def test_user_can_update_owned_event(self) -> None:
        self.login("student@example.com", "Student123!")

        create_response = self.client.post(
            "/api/me/owned-events",
            json={
                "title": "Student Meetup",
                "description": "Student-created meetup for peer networking.",
                "category": "Community",
                "location": "Innovation Hub",
                "start_at": "2026-05-30T18:00:00",
                "capacity": 25,
                "price": 10,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        update_response = self.client.put(
            f"/api/me/owned-events/{event_id}",
            json={
                "title": "Student Meetup Reloaded",
                "description": "Updated student-created meetup for peer networking.",
                "category": "Networking",
                "location": "Creative Loft",
                "venue_details": "Floor 5, Creative Loft, check-in beside the north staircase.",
                "start_at": "2026-06-01T19:30:00",
                "capacity": 40,
                "price": 15,
                "image_urls": ["/static/images/gallery-lounge.svg", "/static/images/gallery-stage.svg"],
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["title"], "Student Meetup Reloaded")
        self.assertEqual(update_response.json()["category"], "Networking")
        self.assertEqual(update_response.json()["venue_details"], "Floor 5, Creative Loft, check-in beside the north staircase.")
        self.assertEqual(update_response.json()["image_url"], "/static/images/gallery-lounge.svg")
        self.assertEqual(update_response.json()["approval_status"], "pending")

    def test_user_can_create_and_delete_owned_event(self) -> None:
        self.login("student@example.com", "Student123!")

        create_response = self.client.post(
            "/api/me/owned-events",
            json={
                "title": "Personal Meetup",
                "description": "User-created event for peer networking and discussion.",
                "category": "Community",
                "location": "Maker Space",
                "start_at": "2026-06-10T18:00:00",
                "capacity": 30,
                "price": 12,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        owned_events_response = self.client.get("/api/me/owned-events")
        self.assertEqual(owned_events_response.status_code, 200)
        self.assertTrue(any(event["id"] == event_id for event in owned_events_response.json()))

        delete_response = self.client.delete(f"/api/me/owned-events/{event_id}")
        self.assertEqual(delete_response.status_code, 200)

    def test_owner_management_api_lists_and_removes_registrants(self) -> None:
        self.login("student@example.com", "Student123!")
        create_response = self.client.post(
            "/api/me/owned-events",
            json={
                "title": "Owner API Managed Event",
                "description": "Owner dashboard API test for attendee management and refunds.",
                "category": "Community",
                "location": "Maker Space",
                "start_at": "2026-06-12T18:00:00",
                "capacity": 30,
                "price": 12,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        approve_response = self.client.post(f"/api/admin/events/{event_id}/approve")
        self.assertEqual(approve_response.status_code, 200)

        self.client.post("/api/auth/logout")
        register_guest_response = self.client.post(
            "/api/auth/register",
            json={
                "name": "Owner API Guest",
                "date_of_birth": "2004-09-01",
                "country": "Vietnam",
                "province": "Ho Chi Minh City",
                "district": "District 1",
                "ward": "Ben Nghe Ward",
                "street_address": "88 API Street",
                "phone_country_code": "+84",
                "phone_country_label": "Vietnam",
                "phone_country_flag": "vn",
                "phone_local_number": "901223344",
                "email": "owner.api.guest@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(register_guest_response.status_code, 201)
        guest_user_id = register_guest_response.json()["id"]

        self.login("owner.api.guest@example.com", "Password123!")
        guest_before = self.client.get("/api/me")
        self.assertEqual(guest_before.status_code, 200)
        register_response = self.client.post(
            f"/api/events/{event_id}/register",
            json={
                "quantity": 2,
                "attendee_name": "Owner API Guest",
                "attendee_email": "owner.api.guest@example.com",
                "attendee_phone": "+84 901223344",
            },
        )
        self.assertEqual(register_response.status_code, 200)
        guest_after_charge = self.client.get("/api/me")
        self.assertEqual(guest_after_charge.status_code, 200)
        self.assertLess(guest_after_charge.json()["balance"], guest_before.json()["balance"])

        self.client.post("/api/auth/logout")
        self.login("student@example.com", "Student123!")
        management_response = self.client.get(f"/api/me/owned-events/{event_id}/management")
        self.assertEqual(management_response.status_code, 200)
        management_payload = management_response.json()
        self.assertEqual(management_payload["summary"]["attendee_count"], 1)
        self.assertEqual(management_payload["summary"]["ticket_count"], 2)
        self.assertEqual(management_payload["summary"]["total_revenue"], 24.0)
        self.assertEqual(management_payload["registrations"][0]["ticket_label"], "General Admission")

        remove_response = self.client.post(
            f"/api/me/owned-events/{event_id}/registrations/{guest_user_id}/remove",
            json={
                "reason": "Ticket issue needs manual rollback",
                "refund_note": "Full refund moved back to attendee wallet.",
            },
        )
        self.assertEqual(remove_response.status_code, 200)
        self.assertEqual(remove_response.json()["summary"]["attendee_count"], 0)
        self.assertEqual(remove_response.json()["summary"]["ticket_count"], 0)
        self.assertEqual(remove_response.json()["summary"]["total_revenue"], 0.0)

        self.client.post("/api/auth/logout")
        self.login("owner.api.guest@example.com", "Password123!")
        guest_after_refund = self.client.get("/api/me")
        self.assertEqual(guest_after_refund.status_code, 200)
        self.assertAlmostEqual(guest_after_refund.json()["balance"], guest_before.json()["balance"])

    def test_user_request_is_hidden_until_admin_approval(self) -> None:
        self.login("student@example.com", "Student123!")
        create_response = self.client.post(
            "/api/me/owned-events",
            json={
                "title": "Pending API Request",
                "description": "Request should stay off the public board until admin approval.",
                "category": "Community",
                "location": "Prototype Hall",
                "start_at": "2026-06-15T18:00:00",
                "capacity": 24,
                "price": 11,
                "latitude": 10.77652,
                "longitude": 106.70098,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]
        self.assertEqual(create_response.json()["approval_status"], "pending")

        public_events_response = self.client.get("/api/events")
        self.assertEqual(public_events_response.status_code, 200)
        self.assertFalse(any(event["id"] == event_id for event in public_events_response.json()))

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")

        admin_events_response = self.client.get("/api/admin/events")
        self.assertEqual(admin_events_response.status_code, 200)
        pending_event = next(event for event in admin_events_response.json() if event["id"] == event_id)
        self.assertEqual(pending_event["approval_status"], "pending")

        approve_response = self.client.post(f"/api/admin/events/{event_id}/approve")
        self.assertEqual(approve_response.status_code, 200)
        approved_event = approve_response.json()
        self.assertEqual(approved_event["approval_status"], "approved")
        self.assertEqual(approved_event["latitude"], 10.77652)
        self.assertEqual(approved_event["longitude"], 106.70098)

        approved_public_events = self.client.get("/api/events")
        self.assertEqual(approved_public_events.status_code, 200)
        public_event = next(event for event in approved_public_events.json() if event["id"] == event_id)
        self.assertEqual(public_event["latitude"], 10.77652)
        self.assertEqual(public_event["longitude"], 106.70098)

    def test_admin_can_reject_user_request(self) -> None:
        self.login("student@example.com", "Student123!")
        create_response = self.client.post(
            "/api/me/owned-events",
            json={
                "title": "Rejected API Request",
                "description": "Request should be returned for revision.",
                "category": "Community",
                "location": "Revision Hall",
                "start_at": "2026-06-16T18:00:00",
                "capacity": 16,
                "price": 8,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.json()["id"]

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        reject_response = self.client.post(f"/api/admin/events/{event_id}/reject")
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["approval_status"], "rejected")

        public_events_response = self.client.get("/api/events")
        self.assertEqual(public_events_response.status_code, 200)
        self.assertFalse(any(event["id"] == event_id for event in public_events_response.json()))

        self.client.post("/api/auth/logout")
        self.login("student@example.com", "Student123!")
        owned_events_response = self.client.get("/api/me/owned-events")
        self.assertEqual(owned_events_response.status_code, 200)
        rejected_event = next(event for event in owned_events_response.json() if event["id"] == event_id)
        self.assertEqual(rejected_event["approval_status"], "rejected")

    def test_user_can_change_password_from_security_page_api(self) -> None:
        self.login("student@example.com", "Student123!")
        change_response = self.client.post(
            "/api/me/change-password",
            json={
                "current_password": "Student123!",
                "new_password": "Student789!",
            },
        )
        self.assertEqual(change_response.status_code, 200)

        self.client.post("/api/auth/logout")
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "student@example.com", "password": "Student789!"},
        )
        self.assertEqual(login_response.status_code, 200)



    def test_change_password_rejects_same_as_current_password_via_api(self) -> None:
        self.login("student@example.com", "Student123!")
        change_response = self.client.post(
            "/api/me/change-password",
            json={
                "current_password": "Student123!",
                "new_password": "Student123!",
            },
        )
        self.assertEqual(change_response.status_code, 409)
        self.assertEqual(change_response.json()["error"]["code"], "PASSWORD_UNCHANGED")


    def test_forgot_password_updates_credentials(self) -> None:
        response = self.client.post(
            "/api/auth/forgot-password",
            json={
                "email": "student@example.com",
                "date_of_birth": "2005-08-20",
                "new_password": "Student456!",
            },
        )
        self.assertEqual(response.status_code, 200)

        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "student@example.com", "password": "Student456!"},
        )
        self.assertEqual(login_response.status_code, 200)


    def test_forgot_password_rejects_same_as_current_password(self) -> None:
        response = self.client.post(
            "/api/auth/forgot-password",
            json={
                "email": "student@example.com",
                "date_of_birth": "2005-08-20",
                "new_password": "Student123!",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "PASSWORD_UNCHANGED")


    def test_user_can_update_profile_and_avatar(self) -> None:
        self.login("student@example.com", "Student123!")

        update_response = self.client.put(
            "/api/me",
            json={
                "name": "Profile Updated User",
                "date_of_birth": "2004-08-20",
                "country": "United States",
                "province": "California",
                "district": "San Francisco County",
                "ward": "",
                "street_address": "1 Market Street",
                "phone_country_code": "+1",
                "phone_country_label": "United States",
                "phone_country_flag": "us",
                "phone_local_number": "4155550199",
                "avatar_url": "/static/images/gallery-stage.svg",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_user = update_response.json()
        self.assertEqual(updated_user["name"], "Profile Updated User")
        self.assertEqual(updated_user["avatar_url"], "/static/images/gallery-stage.svg")
        self.assertEqual(updated_user["phone_number"], "+1 4155550199")
        self.assertEqual(updated_user["phone_country_flag"], "us")
        self.assertIn("United States", updated_user["permanent_address"])

        me_response = self.client.get("/api/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["name"], "Profile Updated User")
        self.assertEqual(me_response.json()["avatar_url"], "/static/images/gallery-stage.svg")

    def test_login_endpoint_purges_notifications_older_than_five_days(self) -> None:
        service = self.client.app.state.service
        student = service.db.users.find_one({"email": "student@example.com"})
        old_created_at = (datetime.now(timezone.utc) - timedelta(days=6)).replace(microsecond=0).isoformat()
        recent_created_at = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat()
        service.db.notifications.insert_many(
            [
                {
                    "id": service.db.next_sequence("notifications"),
                    "user_id": student["id"],
                    "kind": "old_notice",
                    "title": "Old notification",
                    "body": "Should be removed on login.",
                    "link": "/activity",
                    "created_at": old_created_at,
                    "read_at": None,
                },
                {
                    "id": service.db.next_sequence("notifications"),
                    "user_id": student["id"],
                    "kind": "recent_notice",
                    "title": "Recent notification",
                    "body": "Should stay after login.",
                    "link": "/activity",
                    "created_at": recent_created_at,
                    "read_at": None,
                },
            ]
        )

        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "student@example.com", "password": "Student123!"},
        )
        self.assertEqual(login_response.status_code, 200)

        notifications_response = self.client.get("/api/me/notifications")
        self.assertEqual(notifications_response.status_code, 200)
        kinds = [item["kind"] for item in notifications_response.json()["items"]]
        self.assertIn("recent_notice", kinds)
        self.assertNotIn("old_notice", kinds)

    def test_user_can_send_issue_report_to_admin(self) -> None:
        self.login("student@example.com", "Student123!")
        response = self.client.post(
            "/api/me/issues",
            json={
                "title": "Billing countdown was stuck",
                "category": "Billing",
                "description": "The QR countdown stayed on screen after the request had already expired once.",
                "page_path": "/account/billing",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Billing countdown was stuck")
        self.assertEqual(response.json()["page_path"], "/account/billing")

        user_notifications = self.client.get("/api/me/notifications")
        self.assertEqual(user_notifications.status_code, 200)
        self.assertTrue(any(item["kind"] == "issue_sent" for item in user_notifications.json()["items"]))

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        admin_notifications = self.client.get("/api/me/notifications")
        self.assertEqual(admin_notifications.status_code, 200)
        self.assertTrue(any(item["kind"] == "issue_reported" for item in admin_notifications.json()["items"]))

        admin_issue_reports = self.client.get("/api/admin/issues")
        self.assertEqual(admin_issue_reports.status_code, 200)
        self.assertTrue(any(item["title"] == "Billing countdown was stuck" for item in admin_issue_reports.json()))

    def test_notifications_api_returns_admin_review_and_read_flow(self) -> None:
        self.login("student@example.com", "Student123!")
        create_response = self.client.post(
            "/api/me/owned-events",
            json={
                "title": "API Notification Demo",
                "description": "Event request used to verify notification APIs.",
                "category": "Community",
                "location": "Notice Hall",
                "start_at": "2026-06-20T18:00:00",
                "capacity": 24,
                "price": 6,
            },
        )
        self.assertEqual(create_response.status_code, 201)

        notifications_response = self.client.get("/api/me/notifications")
        self.assertEqual(notifications_response.status_code, 200)
        self.assertGreaterEqual(notifications_response.json()["unread_count"], 1)
        self.assertTrue(any(item["kind"] == "request_sent" for item in notifications_response.json()["items"]))

        update_response = self.client.put(
            f"/api/me/owned-events/{create_response.json()['id']}",
            json={
                "title": "API Notification Demo Revised",
                "description": "Updated request used to verify resubmission notifications.",
                "category": "Community",
                "location": "Notice Hall Revised",
                "start_at": "2026-06-21T18:00:00",
                "capacity": 28,
                "price": 7,
            },
        )
        self.assertEqual(update_response.status_code, 200)

        notifications_after_update = self.client.get("/api/me/notifications")
        self.assertEqual(notifications_after_update.status_code, 200)
        self.assertTrue(any(item["kind"] == "request_resubmitted" for item in notifications_after_update.json()["items"]))

        mark_read_response = self.client.post("/api/me/notifications/read-all")
        self.assertEqual(mark_read_response.status_code, 200)

        notifications_after_read = self.client.get("/api/me/notifications")
        self.assertEqual(notifications_after_read.status_code, 200)
        self.assertEqual(notifications_after_read.json()["unread_count"], 0)

        self.client.post("/api/auth/logout")
        self.login("admin@example.com", "Admin123!")
        admin_notifications = self.client.get("/api/me/notifications")
        self.assertEqual(admin_notifications.status_code, 200)
        self.assertTrue(any(item["kind"] == "request_review" for item in admin_notifications.json()["items"]))


if __name__ == "__main__":
    unittest.main()


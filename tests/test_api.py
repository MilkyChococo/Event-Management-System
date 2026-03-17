from __future__ import annotations

import unittest
import uuid

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


if __name__ == "__main__":
    unittest.main()

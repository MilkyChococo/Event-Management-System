from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.database import Database
from app.services import EventRegistrationService, ServiceError


class EventRegistrationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        settings = Settings(
            env="test",
            mongo_uri="mongodb://unused",
            mongo_db_name=f"service_test_{uuid.uuid4().hex}",
            secret="test-secret",
            seed_demo=True,
            use_mock_db=True,
        )
        self.db = Database(settings.mongo_uri, settings.mongo_db_name, use_mock=settings.use_mock_db)
        self.service = EventRegistrationService(self.db)
        self.service.initialize(seed_demo=True)
        self.student = self.service.authenticate("student@example.com", "Student123!")
        self.admin = self.service.authenticate("admin@example.com", "Admin123!")

    def tearDown(self) -> None:
        self.db.close()

    def test_duplicate_registration_is_blocked(self) -> None:
        event_id = self.service.list_events()[0]["id"]
        self.service.register_for_event(self.student["id"], event_id)

        with self.assertRaises(ServiceError) as context:
            self.service.register_for_event(self.student["id"], event_id)

        self.assertEqual(context.exception.code, "ALREADY_REGISTERED")

    def test_capacity_limit_is_enforced(self) -> None:
        second_user = self.service.register_user(
            "Second User",
            "second@example.com",
            "Password123!",
            "2004-09-01",
            "Vietnam",
            "Ho Chi Minh City",
            "District 1",
            "Ben Nghe Ward",
            "99 Example Street",
            "+84",
            "Vietnam",
            "vn",
            "934567890",
        )
        limited_event = self.service.create_event(
            self.admin["id"],
            {
                "title": "Limited Event",
                "description": "Small event used to verify capacity handling.",
                "location": "Lab X",
                "start_at": "2026-05-01T09:00:00",
                "capacity": 1,
                "price": 0,
            },
        )

        self.service.register_for_event(self.student["id"], limited_event["id"])

        with self.assertRaises(ServiceError) as context:
            self.service.register_for_event(second_user["id"], limited_event["id"])

        self.assertEqual(context.exception.code, "EVENT_FULL")

    def test_cancel_registration_reopens_seat(self) -> None:
        limited_event = self.service.create_event(
            self.admin["id"],
            {
                "title": "Cancelable Event",
                "description": "Used to verify cancellation returns the seat to the pool.",
                "location": "Lab Y",
                "start_at": "2026-05-03T10:00:00",
                "capacity": 1,
                "price": 0,
            },
        )

        registered_event = self.service.register_for_event(self.student["id"], limited_event["id"])
        self.assertTrue(registered_event["is_registered"])
        self.assertEqual(registered_event["seats_left"], 0)

        cancelled_event = self.service.cancel_registration(self.student["id"], limited_event["id"])
        self.assertFalse(cancelled_event["is_registered"])
        self.assertEqual(cancelled_event["seats_left"], 1)

    def test_registration_quantity_uses_multiple_seats_and_respects_account_limit(self) -> None:
        event = self.service.create_event(
            self.admin["id"],
            {
                "title": "Quantity Event",
                "description": "Used to verify multi-ticket reservations and account limits.",
                "location": "Studio Q",
                "start_at": "2026-05-07T18:00:00",
                "capacity": 12,
                "price": 15,
            },
        )

        registered_event = self.service.register_for_event(self.student["id"], event["id"], {"quantity": 5})
        self.assertTrue(registered_event["is_registered"])
        self.assertEqual(registered_event["registered_count"], 5)
        self.assertEqual(registered_event["seats_left"], 7)

        tickets = self.service.list_user_registrations(self.student["id"])
        quantity_ticket = next(ticket for ticket in tickets if ticket["event_id"] == event["id"])
        self.assertEqual(quantity_ticket["quantity"], 5)
        self.assertEqual(quantity_ticket["total_price"], 75)

        with self.assertRaises(ServiceError) as context:
            self.service.register_for_event(self.admin["id"], event["id"], {"quantity": 6})
        self.assertEqual(context.exception.code, "TICKET_LIMIT_EXCEEDED")

    def test_cancelled_registration_is_removed_after_one_day(self) -> None:
        event_id = self.service.list_events()[0]["id"]
        self.service.register_for_event(self.student["id"], event_id)
        self.service.cancel_registration(self.student["id"], event_id)

        self.db.registrations.update_one(
            {"user_id": self.student["id"], "event_id": event_id},
            {"$set": {"cancelled_at": "2000-01-01T00:00:00+00:00"}},
        )

        tickets = self.service.list_user_registrations(self.student["id"])
        self.assertFalse(any(ticket["event_id"] == event_id for ticket in tickets))
        self.assertIsNone(self.db.registrations.find_one({"user_id": self.student["id"], "event_id": event_id}))

    def test_list_user_registrations_preserves_cancelled_status(self) -> None:
        event_id = self.service.list_events()[0]["id"]
        self.service.register_for_event(self.student["id"], event_id)

        confirmed_tickets = self.service.list_user_registrations(self.student["id"])
        self.assertEqual(len(confirmed_tickets), 1)
        self.assertEqual(confirmed_tickets[0]["status"], "confirmed")
        self.assertTrue(confirmed_tickets[0]["ticket_code"])

        self.service.cancel_registration(self.student["id"], event_id)
        cancelled_tickets = self.service.list_user_registrations(self.student["id"])
        self.assertEqual(cancelled_tickets[0]["status"], "cancelled")
        self.assertIsNotNone(cancelled_tickets[0]["cancelled_at"])

    def test_admin_analytics_reports_revenue_and_distribution(self) -> None:
        us_user = self.service.register_user(
            "US Guest",
            "service.us@example.com",
            "Password123!",
            "1994-04-18",
            "United States",
            "California",
            "San Francisco County",
            "",
            "1 Market Street",
            "+1",
            "United States",
            "us",
            "4155550101",
        )
        event_id = self.service.list_events()[0]["id"]

        self.service.register_for_event(self.student["id"], event_id)
        self.service.register_for_event(us_user["id"], event_id)
        analytics = self.service.get_admin_analytics()

        self.assertEqual(analytics["summary"]["total_registrations"], 2)
        self.assertEqual(analytics["summary"]["domestic_customer_ratio"], 50.0)
        self.assertEqual(analytics["summary"]["international_customer_ratio"], 50.0)

        event_analytics = next(item for item in analytics["events"] if item["event_id"] == event_id)
        self.assertEqual(event_analytics["registered_count"], 2)

        country_distribution = {item["label"]: item["count"] for item in event_analytics["country_distribution"]}
        self.assertEqual(country_distribution["Vietnam"], 1)
        self.assertEqual(country_distribution["United States"], 1)

    def test_wallet_top_up_increases_balance_after_confirmation(self) -> None:
        self.db.users.update_one({"id": self.student["id"]}, {"$set": {"balance": 0}})

        pending_top_up = self.service.top_up_wallet(self.student["id"], 40, "QR transfer", "Top up for new reservations")
        self.assertIn("pending_top_up", pending_top_up)
        wallet_before_confirm = self.service.get_wallet_overview(self.student["id"])
        self.assertEqual(len([item for item in wallet_before_confirm["transactions"] if item["kind"] == "top_up"]), 0)
        self.assertIsNotNone(wallet_before_confirm["pending_top_up"])

        confirmed_top_up = self.service.confirm_top_up_wallet(self.student["id"])
        self.assertEqual(confirmed_top_up["transaction"]["kind"], "top_up")
        self.assertEqual(confirmed_top_up["user"]["balance"], 40.0)

    def test_registration_is_blocked_when_balance_is_not_enough(self) -> None:
        event = self.service.create_event(
            self.admin["id"],
            {
                "title": "Premium Reservation",
                "description": "Used to verify insufficient balance handling during reservation.",
                "location": "Vault Hall",
                "start_at": "2026-05-18T19:00:00",
                "capacity": 10,
                "price": 200,
            },
        )
        self.db.users.update_one({"id": self.student["id"]}, {"$set": {"balance": 30}})

        with self.assertRaises(ServiceError) as context:
            self.service.register_for_event(self.student["id"], event["id"], {"quantity": 1})

        self.assertEqual(context.exception.code, "INSUFFICIENT_FUNDS")
        refreshed_event = next(item for item in self.service.list_events() if item["id"] == event["id"])
        self.assertEqual(refreshed_event["registered_count"], 0)

    def test_pending_top_up_blocks_repeat_generation_and_expires_without_history(self) -> None:
        pending_top_up = self.service.top_up_wallet(self.student["id"], 18, "QR transfer", "Short lived QR")
        self.assertEqual(pending_top_up["pending_top_up"]["status"], "pending")

        with self.assertRaises(ServiceError) as context:
            self.service.top_up_wallet(self.student["id"], 12, "QR transfer", "Second QR too early")
        self.assertEqual(context.exception.code, "QR_TOP_UP_ACTIVE")

        self.db.wallet_topup_requests.update_one(
            {"id": pending_top_up["pending_top_up"]["request_id"]},
            {"$set": {"expires_at": "2000-01-01T00:00:00+00:00"}},
        )

        overview = self.service.get_wallet_overview(self.student["id"])
        self.assertIsNone(overview["pending_top_up"])
        self.assertEqual(len([item for item in overview["transactions"] if item["kind"] == "top_up"]), 0)

        with self.assertRaises(ServiceError) as expired_context:
            self.service.confirm_top_up_wallet(self.student["id"])
        self.assertEqual(expired_context.exception.code, "QR_TOP_UP_EXPIRED")

    def test_registration_charge_and_cancel_refund_update_wallet(self) -> None:
        event_id = self.service.list_events()[0]["id"]
        before = self.service.authenticate("student@example.com", "Student123!")
        registered = self.service.register_for_event(self.student["id"], event_id)
        self.assertTrue(registered["is_registered"])

        charged_user = self.service.authenticate("student@example.com", "Student123!")
        self.assertLess(charged_user["balance"], before["balance"])

        self.service.cancel_registration(self.student["id"], event_id)
        refunded_user = self.service.authenticate("student@example.com", "Student123!")
        self.assertAlmostEqual(refunded_user["balance"], before["balance"])

    def test_user_can_update_owned_event(self) -> None:
        created = self.service.create_owned_event(
            self.student["id"],
            {
                "title": "Student Meetup",
                "description": "A student-created community meetup for peer networking.",
                "category": "Community",
                "location": "Innovation Hub",
                "start_at": "2026-05-30T18:00:00",
                "capacity": 25,
                "price": 10,
            },
        )

        updated = self.service.update_owned_event(
            self.student["id"],
            created["id"],
            {
                "title": "Student Meetup Reloaded",
                "description": "Updated copy for the student community meetup.",
                "category": "Networking",
                "location": "Creative Loft",
                "venue_details": "Floor 5, Creative Loft, check-in beside the north staircase.",
                "start_at": "2026-06-01T19:30:00",
                "capacity": 40,
                "price": 15,
                "image_urls": ["/static/images/gallery-lounge.svg", "/static/images/gallery-stage.svg"],
            },
        )

        self.assertEqual(updated["title"], "Student Meetup Reloaded")
        self.assertEqual(updated["category"], "Networking")
        self.assertEqual(updated["location"], "Creative Loft")
        self.assertEqual(updated["venue_details"], "Floor 5, Creative Loft, check-in beside the north staircase.")
        self.assertEqual(updated["capacity"], 40)
        self.assertEqual(updated["price"], 15.0)
        self.assertEqual(updated["image_url"], "/static/images/gallery-lounge.svg")
        self.assertEqual(updated["approval_status"], "pending")
        self.assertEqual(updated["review_note"], "Awaiting admin review.")

    def test_user_can_create_and_delete_owned_event(self) -> None:
        created = self.service.create_owned_event(
            self.student["id"],
            {
                "title": "Student Meetup",
                "description": "A student-created community meetup for peer networking.",
                "category": "Community",
                "location": "Innovation Hub",
                "start_at": "2026-05-30T18:00:00",
                "capacity": 25,
                "price": 10,
            },
        )
        owned_events = self.service.list_owned_events(self.student["id"])
        self.assertTrue(any(event["id"] == created["id"] for event in owned_events))

        self.service.delete_owned_event(self.student["id"], created["id"])
        owned_events_after_delete = self.service.list_owned_events(self.student["id"])
        self.assertFalse(any(event["id"] == created["id"] for event in owned_events_after_delete))

    def test_user_event_request_stays_hidden_until_admin_approval(self) -> None:
        created = self.service.create_owned_event(
            self.student["id"],
            {
                "title": "Pending Student Demo",
                "description": "Student request waiting for moderation.",
                "category": "Community",
                "location": "Prototype Hall",
                "start_at": "2026-06-11T18:00:00",
                "capacity": 20,
                "price": 9,
                "latitude": 10.77652,
                "longitude": 106.70098,
            },
        )

        self.assertEqual(created["approval_status"], "pending")
        self.assertFalse(any(event["id"] == created["id"] for event in self.service.list_events()))

        admin_events = self.service.list_admin_events()
        moderated = next(event for event in admin_events if event["id"] == created["id"])
        self.assertEqual(moderated["approval_status"], "pending")

        approved = self.service.approve_event_request(created["id"])
        self.assertEqual(approved["approval_status"], "approved")
        self.assertEqual(approved["latitude"], 10.77652)
        self.assertEqual(approved["longitude"], 106.70098)
        public_event = next(event for event in self.service.list_events() if event["id"] == created["id"])
        self.assertEqual(public_event["latitude"], 10.77652)
        self.assertEqual(public_event["longitude"], 106.70098)

    def test_admin_can_reject_user_event_request(self) -> None:
        created = self.service.create_owned_event(
            self.student["id"],
            {
                "title": "Rejected Student Demo",
                "description": "Student request that needs revision.",
                "category": "Community",
                "location": "Revision Hall",
                "start_at": "2026-06-12T18:00:00",
                "capacity": 18,
                "price": 7,
            },
        )

        rejected = self.service.reject_event_request(created["id"])
        self.assertEqual(rejected["approval_status"], "rejected")
        self.assertEqual(rejected["review_note"], "Needs revision before publication.")
        self.assertFalse(any(event["id"] == created["id"] for event in self.service.list_events()))

        owner_visible = self.service.get_event(created["id"], user_id=self.student["id"])
        self.assertEqual(owner_visible["approval_status"], "rejected")

    def test_update_user_profile_persists_avatar_and_contact(self) -> None:
        updated = self.service.update_user_profile(
            self.student["id"],
            {
                "name": "Updated Student",
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
                "avatar_url": "/static/images/gallery-foyer.svg",
            },
        )

        self.assertEqual(updated["name"], "Updated Student")
        self.assertEqual(updated["avatar_url"], "/static/images/gallery-foyer.svg")
        self.assertEqual(updated["phone_number"], "+1 4155550199")
        self.assertEqual(updated["phone_country_flag"], "us")
        self.assertIn("San Francisco County", updated["permanent_address"])
        self.assertIn("United States", updated["permanent_address"])

    def test_notifications_cover_request_lifecycle_and_admin_review(self) -> None:
        created = self.service.create_owned_event(
            self.student["id"],
            {
                "title": "Notification Student Demo",
                "description": "Student request used to verify notification routing.",
                "category": "Community",
                "location": "Signal Hall",
                "start_at": "2026-06-15T18:00:00",
                "capacity": 20,
                "price": 8,
            },
        )

        student_notifications = self.service.list_notifications(self.student["id"])
        self.assertTrue(any(item["kind"] == "request_sent" for item in student_notifications["items"]))

        admin_notifications = self.service.list_notifications(self.admin["id"])
        self.assertTrue(any(item["kind"] == "request_review" for item in admin_notifications["items"]))

        self.service.update_owned_event(
            self.student["id"],
            created["id"],
            {
                "title": "Notification Student Demo Revised",
                "description": "Updated request body used to verify resubmission notifications.",
                "category": "Community",
                "location": "Signal Hall Updated",
                "start_at": "2026-06-16T18:00:00",
                "capacity": 22,
                "price": 9,
            },
        )
        student_notifications_after_resubmit = self.service.list_notifications(self.student["id"])
        self.assertTrue(
            any(item["kind"] == "request_resubmitted" for item in student_notifications_after_resubmit["items"])
        )

        admin_notifications_after_resubmit = self.service.list_notifications(self.admin["id"])
        self.assertTrue(
            any(item["title"] == "Updated event request" for item in admin_notifications_after_resubmit["items"])
        )

        self.service.approve_event_request(created["id"])
        student_notifications_after_approval = self.service.list_notifications(self.student["id"])
        self.assertTrue(any(item["kind"] == "request_approved" for item in student_notifications_after_approval["items"]))

        self.service.delete_owned_event(self.student["id"], created["id"])
        student_notifications_after_delete = self.service.list_notifications(self.student["id"])
        self.assertTrue(any(item["kind"] == "request_deleted" for item in student_notifications_after_delete["items"]))

    def test_login_purges_notifications_older_than_five_days(self) -> None:
        old_created_at = (datetime.now(timezone.utc) - timedelta(days=6)).replace(microsecond=0).isoformat()
        recent_created_at = (datetime.now(timezone.utc) - timedelta(days=2)).replace(microsecond=0).isoformat()
        self.db.notifications.insert_many(
            [
                {
                    "id": self.db.next_sequence("notifications"),
                    "user_id": self.student["id"],
                    "kind": "legacy_notice",
                    "title": "Old notification",
                    "body": "This one should be removed on login.",
                    "link": "/activity",
                    "created_at": old_created_at,
                    "read_at": None,
                },
                {
                    "id": self.db.next_sequence("notifications"),
                    "user_id": self.student["id"],
                    "kind": "recent_notice",
                    "title": "Recent notification",
                    "body": "This one should stay.",
                    "link": "/activity",
                    "created_at": recent_created_at,
                    "read_at": None,
                },
            ]
        )

        self.service.authenticate("student@example.com", "Student123!")
        remaining = list(self.db.notifications.find({"user_id": self.student["id"]}))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["kind"], "recent_notice")

    def test_upcoming_event_reminder_notification_is_created_once(self) -> None:
        soon_start = (datetime.now(timezone.utc) + timedelta(hours=10)).replace(microsecond=0).isoformat()
        event = self.service.create_event(
            self.admin["id"],
            {
                "title": "Reminder Window Event",
                "description": "Event scheduled inside the next 24 hours to verify reminders.",
                "location": "Reminder Hall",
                "start_at": soon_start,
                "capacity": 12,
                "price": 5,
            },
        )

        self.service.register_for_event(self.student["id"], event["id"], {"quantity": 1})
        first_notifications = self.service.list_notifications(self.student["id"])
        second_notifications = self.service.list_notifications(self.student["id"])

        reminder_items = [item for item in second_notifications["items"] if item["kind"] == "event_reminder" and str(event["id"]) in item["link"]]
        self.assertEqual(len(reminder_items), 1)
        self.assertEqual(reminder_items[0]["action_label"], "View now")
        self.assertTrue(any(item["kind"] == "event_reminder" for item in first_notifications["items"]))


if __name__ == "__main__":
    unittest.main()


from __future__ import annotations

import unittest
import uuid

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


if __name__ == "__main__":
    unittest.main()

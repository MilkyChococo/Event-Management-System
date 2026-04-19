from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, MongoClient, ReturnDocument

try:
    import mongomock
except ImportError:  # pragma: no cover - optional dependency at runtime
    mongomock = None


class Database:
    def __init__(self, mongo_uri: str, db_name: str, use_mock: bool = False) -> None:
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.use_mock = use_mock
        self._client: Any | None = None
        self._db: Any | None = None

    def connect(self) -> Any:
        if self._db is not None:
            return self._db

        if self.use_mock:
            if mongomock is None:
                raise RuntimeError("mongomock is required when APP_USE_MOCK_DB is enabled.")
            self._client = mongomock.MongoClient()
        else:
            self._client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        self._db = self._client[self.db_name]
        return self._db

    def initialize(self) -> None:
        self.users.create_index([("id", ASCENDING)], unique=True)
        self.users.create_index([("email", ASCENDING)], unique=True)
        self.events.create_index([("id", ASCENDING)], unique=True)
        self.events.create_index([("start_at", ASCENDING)])
        self.events.create_index([("created_by", ASCENDING), ("start_at", ASCENDING)])
        self.registrations.create_index([("user_id", ASCENDING), ("event_id", ASCENDING)], unique=True)
        self.registrations.create_index([("event_id", ASCENDING), ("created_at", ASCENDING)])
        self.sessions.create_index([("token", ASCENDING)], unique=True)
        self.sessions.create_index([("user_id", ASCENDING)])
        self.wallet_transactions.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        self.wallet_transactions.create_index([("event_id", ASCENDING), ("created_at", ASCENDING)])
        self.wallet_topup_requests.create_index([("id", ASCENDING)], unique=True)
        self.wallet_topup_requests.create_index([("user_id", ASCENDING), ("status", ASCENDING), ("created_at", ASCENDING)])
        self.notifications.create_index([("id", ASCENDING)], unique=True)
        self.notifications.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        self.notifications.create_index([("user_id", ASCENDING), ("read_at", ASCENDING), ("created_at", ASCENDING)])
        self.notifications.create_index([("user_id", ASCENDING), ("dedupe_key", ASCENDING)])
        self.issue_reports.create_index([("id", ASCENDING)], unique=True)
        self.issue_reports.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        self.issue_reports.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
        self._sync_counter("users", self.users)
        self._sync_counter("events", self.events)
        self._sync_counter("wallet_topup_requests", self.wallet_topup_requests)
        self._sync_counter("notifications", self.notifications)
        self._sync_counter("issue_reports", self.issue_reports)

    def _sync_counter(self, sequence_name: str, collection: Any) -> None:
        highest = collection.find_one({}, projection={"_id": 0, "id": 1}, sort=[("id", -1)])
        target = int(highest["id"]) if highest and "id" in highest else 0
        counter = self.counters.find_one({"_id": sequence_name})
        current = int(counter.get("value", 0)) if counter else 0
        if target > current:
            self.counters.update_one(
                {"_id": sequence_name},
                {"$set": {"value": target}},
                upsert=True,
            )

    def next_sequence(self, sequence_name: str) -> int:
        document = self.counters.find_one_and_update(
            {"_id": sequence_name},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(document["value"])

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._db = None

    @property
    def db(self) -> Any:
        return self.connect()

    @property
    def users(self) -> Any:
        return self.connect()["users"]

    @property
    def events(self) -> Any:
        return self.connect()["events"]

    @property
    def registrations(self) -> Any:
        return self.connect()["registrations"]

    @property
    def sessions(self) -> Any:
        return self.connect()["sessions"]

    @property
    def wallet_transactions(self) -> Any:
        return self.connect()["wallet_transactions"]

    @property
    def wallet_topup_requests(self) -> Any:
        return self.connect()["wallet_topup_requests"]

    @property
    def notifications(self) -> Any:
        return self.connect()["notifications"]

    @property
    def issue_reports(self) -> Any:
        return self.connect()["issue_reports"]

    @property
    def counters(self) -> Any:
        return self.connect()["counters"]

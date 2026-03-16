from __future__ import annotations

import os
from dataclasses import dataclass


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    env: str
    mongo_uri: str
    mongo_db_name: str
    secret: str
    seed_demo: bool
    use_mock_db: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            env=os.getenv("APP_ENV", "development"),
            mongo_uri=os.getenv("APP_MONGO_URI", "mongodb://127.0.0.1:27017"),
            mongo_db_name=os.getenv("APP_MONGO_DB_NAME", "event_registration"),
            secret=os.getenv("APP_SECRET", "change-me-for-production"),
            seed_demo=_is_truthy(os.getenv("APP_SEED_DEMO"), default=True),
            use_mock_db=_is_truthy(os.getenv("APP_USE_MOCK_DB"), default=False),
        )

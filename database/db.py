"""
MongoDB connection manager.

Uses a single shared MongoClient. On MongoDB Atlas this database is fully
independent of Railway, so migrating to a new Railway account only requires
setting MONGO_URI on the new deployment.
"""
from pymongo import MongoClient, ASCENDING, DESCENDING, errors

from config import config
from utils.logger import get_logger

log = get_logger("database")

# All collections used by the application.
COLLECTIONS = [
    "users",
    "expenses",
    "income",
    "borrow",
    "lending",
    "friends",
    "reminders",
    "bills",
    "settings",
    "reports",
    "categories",
    "budget",
    "savings",
    "notifications",
    "admin_logs",
    "ledger",
]


class Database:
    def __init__(self):
        self._client = None
        self._db = None

    def connect(self):
        if self._db is not None:
            return self._db
        log.info("Connecting to MongoDB at %s", _mask_uri(config.MONGO_URI))
        self._client = MongoClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            retryWrites=True,
            tz_aware=True,  # return timezone-aware UTC datetimes
        )
        # Trigger a real connection to fail fast if misconfigured.
        self._client.admin.command("ping")
        self._db = self._client[config.DB_NAME]
        self._ensure_indexes()
        log.info("Connected to database '%s'", config.DB_NAME)
        return self._db

    @property
    def db(self):
        if self._db is None:
            self.connect()
        return self._db

    def collection(self, name):
        return self.db[name]

    def _ensure_indexes(self):
        db = self._db
        try:
            db.users.create_index([("user_id", ASCENDING)], unique=True)
            db.expenses.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
            db.expenses.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
            db.income.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
            db.borrow.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
            db.lending.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
            db.friends.create_index([("user_id", ASCENDING), ("name", ASCENDING)])
            db.reminders.create_index([("user_id", ASCENDING), ("next_run", ASCENDING)])
            db.bills.create_index([("user_id", ASCENDING), ("due_date", ASCENDING)])
            db.savings.create_index([("user_id", ASCENDING)])
            db.budget.create_index([("user_id", ASCENDING)])
            db.ledger.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
            db.categories.create_index([("user_id", ASCENDING)])
            db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
            db.admin_logs.create_index([("created_at", DESCENDING)])
        except errors.PyMongoError as exc:  # pragma: no cover
            log.warning("Index creation issue: %s", exc)

    def ping(self):
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def stats(self):
        try:
            return self.db.command("dbstats")
        except Exception as exc:  # pragma: no cover
            log.warning("dbstats failed: %s", exc)
            return {}


def _mask_uri(uri):
    """Hide credentials when logging the connection string."""
    try:
        if "@" in uri:
            prefix, rest = uri.split("@", 1)
            if "//" in prefix:
                scheme = prefix.split("//", 1)[0]
                return "%s//***:***@%s" % (scheme, rest)
        return uri
    except Exception:
        return "***"


# Global singleton
database = Database()

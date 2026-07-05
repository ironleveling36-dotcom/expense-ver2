"""
Central configuration for the Telegram Expense Tracker Bot.

All secrets are loaded from environment variables so the app can be moved
between Railway accounts by only updating the variables (no code changes).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def _get_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _get_int_list(name):
    raw = os.environ.get(name, "") or ""
    ids = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


class Config:
    """Runtime configuration object."""

    # --- Telegram ---
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

    # --- MongoDB (MongoDB Atlas recommended) ---
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017").strip()
    DB_NAME = os.environ.get("DB_NAME", "expense_tracker").strip()

    # --- Admin / Roles ---
    # Comma separated list of Telegram user ids that are super admins.
    ADMIN_IDS = _get_int_list("ADMIN_IDS")

    # --- Behaviour ---
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "₹")
    DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "Asia/Kolkata")
    MAINTENANCE_MODE = _get_bool("MAINTENANCE_MODE", False)

    # --- Rate limiting ---
    RATE_LIMIT_MESSAGES = int(os.environ.get("RATE_LIMIT_MESSAGES", "20"))
    RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "10"))  # seconds

    # --- Reminder scheduler ---
    REMINDER_INTERVAL = int(os.environ.get("REMINDER_INTERVAL", "60"))  # seconds

    # --- Logging ---
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    @classmethod
    def validate(cls):
        """Validate mandatory configuration, raising a clear error if missing."""
        missing = []
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if not cls.MONGO_URI:
            missing.append("MONGO_URI")
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        return True

    @classmethod
    def is_admin(cls, user_id):
        return int(user_id) in cls.ADMIN_IDS


config = Config()

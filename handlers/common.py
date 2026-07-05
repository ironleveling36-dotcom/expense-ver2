"""
Shared helpers for handlers: safe message editing, access control,
rate limiting, and a small registry so modules can share the bot instance.
"""
import time
import threading
from collections import defaultdict

from config import config
from database import models
from utils.logger import get_logger
from utils.helpers import utcnow

log = get_logger("handlers")

_bot = None
_rate_lock = threading.Lock()
_rate_hits = defaultdict(list)


def set_bot(bot):
    global _bot
    _bot = bot


def get_bot():
    return _bot


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #
def rate_limited(user_id):
    """Return True if the user has exceeded the rate limit."""
    now = time.time()
    window = config.RATE_LIMIT_WINDOW
    limit = config.RATE_LIMIT_MESSAGES
    with _rate_lock:
        hits = _rate_hits[user_id]
        hits[:] = [t for t in hits if now - t < window]
        hits.append(now)
        return len(hits) > limit


# --------------------------------------------------------------------------- #
# Access control
# --------------------------------------------------------------------------- #
def resolve_user(obj):
    """Extract (user_id, first_name, username) from a message or callback."""
    from_user = getattr(obj, "from_user", None)
    if from_user is None and hasattr(obj, "message"):
        from_user = obj.message.from_user
    return (
        from_user.id,
        from_user.first_name or "",
        from_user.username or "",
    )


def ensure_access(obj):
    """
    Ensure the user is allowed to use the bot.
    Returns the user document, or None if access is denied.
    """
    user_id, first_name, username = resolve_user(obj)
    if rate_limited(user_id):
        _notify(obj, "⏳ You're going too fast. Please wait a moment.")
        return None
    user = models.get_or_create_user(user_id, first_name, username)
    if user.get("blocked"):
        _notify(obj, "🚫 Your access to this bot has been blocked.")
        return None
    if config.MAINTENANCE_MODE and not config.is_admin(user_id):
        _notify(obj, "🔧 The bot is under maintenance. Please try again later.")
        return None
    return user


def is_admin(obj):
    user_id, _, _ = resolve_user(obj)
    return is_admin_uid(user_id)


def is_admin_uid(user_id):
    if config.is_admin(user_id):
        return True
    user = models.get_user(user_id)
    return bool(user and user.get("role") in ("admin", "moderator"))


def _notify(obj, text):
    bot = get_bot()
    if bot is None:
        return
    try:
        if hasattr(obj, "message") and getattr(obj, "id", None):
            bot.answer_callback_query(obj.id, text, show_alert=True)
        else:
            chat_id = obj.chat.id if hasattr(obj, "chat") else obj.message.chat.id
            bot.send_message(chat_id, text)
    except Exception as exc:  # pragma: no cover
        log.warning("notify failed: %s", exc)


# --------------------------------------------------------------------------- #
# Message helpers
# --------------------------------------------------------------------------- #
def safe_edit(call, text, reply_markup=None, parse_mode="HTML"):
    """Edit the message behind a callback, tolerating 'not modified' errors."""
    bot = get_bot()
    try:
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "not modified" in msg:
            return
        # Fall back to sending a new message if editing fails.
        try:
            bot.send_message(
                call.message.chat.id, text, reply_markup=reply_markup,
                parse_mode=parse_mode, disable_web_page_preview=True,
            )
        except Exception as exc2:  # pragma: no cover
            log.warning("safe_edit fallback failed: %s", exc2)


def send(chat_id, text, reply_markup=None, parse_mode="HTML"):
    bot = get_bot()
    try:
        return bot.send_message(
            chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except Exception as exc:  # pragma: no cover
        log.warning("send failed: %s", exc)
        return None


def answer(call, text=None):
    bot = get_bot()
    try:
        bot.answer_callback_query(call.id, text)
    except Exception:
        pass


def user_currency(user_id):
    settings = models.get_user_settings(user_id)
    return settings.get("currency", config.DEFAULT_CURRENCY)


def user_timezone(user_id):
    settings = models.get_user_settings(user_id)
    return settings.get("timezone", config.DEFAULT_TIMEZONE)

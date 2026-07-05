"""Generic helper utilities: formatting, parsing, validation, timezones."""
import re
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

from config import config


# --------------------------------------------------------------------------- #
# Time helpers
# --------------------------------------------------------------------------- #
def utcnow():
    """Timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def get_tz(tz_name=None):
    tz_name = tz_name or config.DEFAULT_TIMEZONE
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return timezone.utc


def to_local(dt, tz_name=None):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_tz(tz_name))


def fmt_datetime(dt, tz_name=None):
    local = to_local(dt, tz_name)
    if local is None:
        return "-"
    return local.strftime("%d %b %Y, %I:%M %p")


def fmt_date(dt, tz_name=None):
    local = to_local(dt, tz_name)
    if local is None:
        return "-"
    return local.strftime("%d %b %Y")


def day_bounds(reference=None, tz_name=None):
    """Return (start, end) UTC datetimes covering the local day of reference."""
    tz = get_tz(tz_name)
    ref = (reference or utcnow()).astimezone(tz)
    start_local = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def period_bounds(period, reference=None, tz_name=None):
    """Return (start_utc, end_utc) for 'day', 'week', 'month', 'year'."""
    tz = get_tz(tz_name)
    ref = (reference or utcnow()).astimezone(tz)
    start_local = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        start = start_local
        end = start + timedelta(days=1)
    elif period == "week":
        start = start_local - timedelta(days=start_local.weekday())
        end = start + timedelta(days=7)
    elif period == "month":
        start = start_local.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif period == "year":
        start = start_local.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
    else:
        raise ValueError("Unknown period: %s" % period)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


# --------------------------------------------------------------------------- #
# Money / number helpers
# --------------------------------------------------------------------------- #
_AMOUNT_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def parse_amount(text):
    """Parse a human-entered amount into a float. Returns None if invalid."""
    if text is None:
        return None
    text = str(text).strip().replace("₹", "").replace(",", "").replace("Rs", "")
    text = text.replace("rs", "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value < 0:
        return None
    return round(value, 2)


def fmt_money(amount, currency=None):
    currency = currency or config.DEFAULT_CURRENCY
    try:
        amount = float(amount or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return "%s%s" % (currency, _indian_grouping(amount))


def _indian_grouping(amount):
    """Format a number using the Indian numbering system (lakh/crore)."""
    negative = amount < 0
    amount = abs(amount)
    int_part = int(amount)
    dec_part = round(amount - int_part, 2)
    s = str(int_part)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        rest = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", rest)
        grouped = rest + "," + last3
    else:
        grouped = s
    if dec_part > 0:
        grouped = "%s.%02d" % (grouped, round(dec_part * 100))
    return ("-" if negative else "") + grouped


def parse_date(text):
    """Parse a date string in common formats. Returns tz-aware UTC datetime or None."""
    if not text:
        return None
    text = str(text).strip().lower()
    if text in ("today", "now"):
        return utcnow()
    if text == "yesterday":
        return utcnow() - timedelta(days=1)
    if text == "tomorrow":
        return utcnow() + timedelta(days=1)
    formats = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y",
               "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def validate_phone(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(text))
    digits = re.sub(r"\D", "", cleaned)
    if 7 <= len(digits) <= 15:
        return cleaned
    return None


def truncate(text, length=40):
    text = str(text or "")
    return text if len(text) <= length else text[: length - 1] + "…"


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def progress_bar(percent, width=10):
    percent = max(0, min(100, percent))
    filled = int(round(percent / 100 * width))
    return "█" * filled + "░" * (width - filled)

"""
Background reminder scheduler.

Runs in a daemon thread and periodically checks for due reminders, bill due
dates and overdue borrow/lending records, delivering notifications to users.
"""
import threading
import time
from datetime import timedelta

from config import config
from database import models
from database.db import database
from handlers import common
from utils.helpers import utcnow, fmt_money, fmt_date
from utils.logger import get_logger

log = get_logger("reminder")

_started = False


def _advance(next_run, repeat):
    if repeat == "daily":
        return next_run + timedelta(days=1)
    if repeat == "weekly":
        return next_run + timedelta(weeks=1)
    if repeat == "monthly":
        return next_run + timedelta(days=30)
    return None


def _process_reminders(now):
    for rem in models.due_reminders(now):
        uid = rem["user_id"]
        try:
            common.send(uid, "🔔 <b>Reminder</b>\n\n%s" % rem.get("text", ""))
        except Exception as exc:  # pragma: no cover
            log.warning("reminder send failed: %s", exc)
        nxt = _advance(rem.get("next_run"), rem.get("repeat", "once"))
        if nxt:
            models.update_reminder(rem["_id"], {"next_run": nxt})
        else:
            models.update_reminder(rem["_id"], {"active": False})


def _process_bill_due(now):
    """Notify about bills due within 24h that are still unpaid (once per day)."""
    soon = now + timedelta(days=1)
    db = database.db
    cursor = db.bills.find({
        "status": "unpaid",
        "deleted": {"$ne": True},
        "due_date": {"$gte": now, "$lte": soon},
        "$or": [{"notified_on": {"$exists": False}},
                {"notified_on": {"$lt": now - timedelta(hours=20)}}],
    })
    for bill in cursor:
        uid = bill["user_id"]
        cur = models.get_user_settings(uid).get("currency", config.DEFAULT_CURRENCY)
        try:
            common.send(uid, "📅 <b>Bill due soon</b>\n%s — %s (due %s)" % (
                bill["name"], fmt_money(bill["amount"], cur),
                fmt_date(bill.get("due_date"))))
            db.bills.update_one({"_id": bill["_id"]},
                                {"$set": {"notified_on": now}})
        except Exception as exc:  # pragma: no cover
            log.warning("bill notify failed: %s", exc)


def _loop():
    interval = config.REMINDER_INTERVAL
    while True:
        try:
            now = utcnow()
            _process_reminders(now)
            _process_bill_due(now)
        except Exception as exc:  # pragma: no cover
            log.warning("reminder loop error: %s", exc)
        time.sleep(interval)


def start():
    global _started
    if _started:
        return
    thread = threading.Thread(target=_loop, name="reminder-scheduler", daemon=True)
    thread.start()
    _started = True
    log.info("Reminder scheduler started (interval=%ss)", config.REMINDER_INTERVAL)

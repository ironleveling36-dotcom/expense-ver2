"""Admin panel handlers."""
import math
from datetime import timedelta

from config import config
from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from database.db import database
from utils.states import states
from utils.helpers import utcnow, fmt_datetime, truncate

PAGE = 8
FLOW = "admin_broadcast"


def _guard(call):
    if common.ensure_access(call) is None:
        return False
    if not common.is_admin(call):
        common.answer(call, "🚫 Admins only")
        return False
    return True


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "adm:menu")
    def _menu(call):
        if not _guard(call):
            return
        common.answer(call)
        common.safe_edit(call, "🛠 <b>Admin Panel</b>",
                         reply_markup=keyboards.admin_menu())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm:users:"))
    def _users(call):
        if not _guard(call):
            return
        common.answer(call)
        page = int(call.data.split(":")[2])
        users = models.list_users(limit=PAGE, skip=page * PAGE)
        total = models.count_users()
        total_pages = max(1, math.ceil(total / PAGE))
        kb = keyboards.types.InlineKeyboardMarkup()
        for u in users:
            mark = "🚫" if u.get("blocked") else "👤"
            label = "%s %s" % (mark, truncate(u.get("first_name") or str(u["user_id"]), 20))
            kb.row(keyboards.types.InlineKeyboardButton(
                label, callback_data="adm:user:%s" % u["user_id"]))
        nav = []
        if page > 0:
            nav.append(keyboards.types.InlineKeyboardButton(
                "⬅️ Prev", callback_data="adm:users:%d" % (page - 1)))
        if page < total_pages - 1:
            nav.append(keyboards.types.InlineKeyboardButton(
                "➡️ Next", callback_data="adm:users:%d" % (page + 1)))
        if nav:
            kb.row(*nav)
        kb.row(keyboards.types.InlineKeyboardButton("⬅️ Back", callback_data="adm:menu"))
        common.safe_edit(call, "👥 <b>Users</b> (%d total)" % total, reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm:user:"))
    def _user(call):
        if not _guard(call):
            return
        common.answer(call)
        target = int(call.data.split(":", 2)[2])
        u = models.get_user(target)
        if not u:
            return common.safe_edit(call, "User not found.",
                                    reply_markup=keyboards.back_home("adm:users:0"))
        tz = "Asia/Kolkata"
        text = ("👤 <b>User</b>\n\nName: %s\nID: <code>%s</code>\n"
                "Role: %s\nBlocked: %s\nJoined: %s\nLast seen: %s") % (
            u.get("first_name", "-"), target, u.get("role", "user"),
            "Yes" if u.get("blocked") else "No",
            fmt_datetime(u.get("created_at"), tz), fmt_datetime(u.get("last_seen"), tz))
        common.safe_edit(call, text, reply_markup=keyboards.admin_user_kb(
            target, blocked=u.get("blocked", False)))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm:block:"))
    def _block(call):
        if not _guard(call):
            return
        target = int(call.data.split(":", 2)[2])
        models.set_user_blocked(target, True)
        models.add_admin_log(call.from_user.id, "block_user", str(target))
        common.answer(call, "User blocked")
        call.data = "adm:user:%s" % target
        _user(call)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm:unblock:"))
    def _unblock(call):
        if not _guard(call):
            return
        target = int(call.data.split(":", 2)[2])
        models.set_user_blocked(target, False)
        models.add_admin_log(call.from_user.id, "unblock_user", str(target))
        common.answer(call, "User unblocked")
        call.data = "adm:user:%s" % target
        _user(call)

    @bot.callback_query_handler(func=lambda c: c.data == "adm:stats")
    def _stats(call):
        if not _guard(call):
            return
        common.answer(call)
        now = utcnow()
        total = models.count_users()
        active_day = models.count_active_users(now - timedelta(days=1))
        active_week = models.count_active_users(now - timedelta(days=7))
        db = database.db
        text = ("📊 <b>Statistics</b>\n\n"
                "Total users: %d\n"
                "Active (24h): %d\n"
                "Active (7d): %d\n\n"
                "Expenses: %d\n"
                "Income entries: %d\n"
                "Bills: %d\n"
                "Friends: %d") % (
            total, active_day, active_week,
            db.expenses.count_documents({"deleted": {"$ne": True}}),
            db.income.count_documents({"deleted": {"$ne": True}}),
            db.bills.count_documents({"deleted": {"$ne": True}}),
            db.friends.count_documents({"deleted": {"$ne": True}}))
        common.safe_edit(call, text, reply_markup=keyboards.back_home("adm:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "adm:health")
    def _health(call):
        if not _guard(call):
            return
        common.answer(call)
        ok = database.ping()
        text = ("🩺 <b>Bot Health</b>\n\n"
                "Database: %s\n"
                "Maintenance mode: %s\n"
                "Rate limit: %d msgs / %ds") % (
            "🟢 Connected" if ok else "🔴 Down",
            "ON" if config.MAINTENANCE_MODE else "OFF",
            config.RATE_LIMIT_MESSAGES, config.RATE_LIMIT_WINDOW)
        common.safe_edit(call, text, reply_markup=keyboards.back_home("adm:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "adm:storage")
    def _storage(call):
        if not _guard(call):
            return
        common.answer(call)
        stats = database.stats()
        data_mb = round(stats.get("dataSize", 0) / (1024 * 1024), 2)
        storage_mb = round(stats.get("storageSize", 0) / (1024 * 1024), 2)
        text = ("💾 <b>Storage Usage</b>\n\n"
                "Collections: %s\n"
                "Objects: %s\n"
                "Data size: %s MB\n"
                "Storage size: %s MB") % (
            stats.get("collections", "-"), stats.get("objects", "-"),
            data_mb, storage_mb)
        common.safe_edit(call, text, reply_markup=keyboards.back_home("adm:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "adm:logs")
    def _logs(call):
        if not _guard(call):
            return
        common.answer(call)
        logs = models.list_admin_logs(15)
        if not logs:
            return common.safe_edit(call, "No audit logs yet.",
                                    reply_markup=keyboards.back_home("adm:menu"))
        lines = ["📜 <b>Audit Logs</b>\n"]
        for l in logs:
            lines.append("• %s — %s %s (%s)" % (
                fmt_datetime(l.get("created_at")), l.get("action"),
                l.get("detail", ""), l.get("admin_id")))
        common.safe_edit(call, "\n".join(lines),
                         reply_markup=keyboards.back_home("adm:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "adm:maint")
    def _maint(call):
        if not _guard(call):
            return
        config.MAINTENANCE_MODE = not config.MAINTENANCE_MODE
        models.add_admin_log(call.from_user.id, "maintenance",
                             "on" if config.MAINTENANCE_MODE else "off")
        common.answer(call, "Maintenance " + ("ON" if config.MAINTENANCE_MODE else "OFF"))
        common.safe_edit(call, "🔧 Maintenance mode is now <b>%s</b>." % (
            "ON" if config.MAINTENANCE_MODE else "OFF"),
            reply_markup=keyboards.admin_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "adm:broadcast")
    def _broadcast(call):
        if not _guard(call):
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="message")
        common.safe_edit(call, "📢 Enter the broadcast message to send to all users:",
                         reply_markup=keyboards.cancel_kb())

    def _flow(message, user, flow):
        uid = message.from_user.id
        if not common.is_admin_uid(uid):
            states.clear(uid)
            return
        text = (message.text or "").strip()
        if not text:
            return common.send(message.chat.id, "Enter a message:",
                               reply_markup=keyboards.cancel_kb())
        states.clear(uid)
        sent = 0
        failed = 0
        for u in models.list_users(limit=10000):
            if u.get("blocked"):
                continue
            try:
                common.send(u["user_id"], "📢 <b>Announcement</b>\n\n%s" % text)
                sent += 1
            except Exception:
                failed += 1
        models.add_admin_log(uid, "broadcast", "sent=%d failed=%d" % (sent, failed))
        common.send(message.chat.id, "✅ Broadcast sent to %d users (%d failed)." % (
            sent, failed), reply_markup=keyboards.admin_menu())

    register_flow(FLOW, _flow)

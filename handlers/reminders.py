"""Reminder handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import parse_date, fmt_datetime, truncate

PAGE = 8
FLOW = "reminder"


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "rem:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "🔔 <b>Reminders</b>",
                         reply_markup=keyboards.reminders_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "rem:add")
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="text")
        common.safe_edit(call, "🔔 <b>New Reminder</b>\n\nWhat should I remind you "
                               "about?", reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("rem:list:"))
    def _list(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, int(call.data.split(":")[2]))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("rem:view:"))
    def _view(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        rem = models.get_reminder(uid, call.data.split(":", 2)[2])
        if not rem:
            return common.safe_edit(call, "Not found.",
                                    reply_markup=keyboards.back_home("rem:list:0"))
        tz = common.user_timezone(uid)
        text = ("🔔 <b>Reminder</b>\n\n%s\n\nNext: %s\nRepeat: %s") % (
            rem["text"], fmt_datetime(rem.get("next_run"), tz),
            rem.get("repeat", "once"))
        common.safe_edit(call, text, reply_markup=keyboards.entity_actions_kb(
            "rem", rem["_id"], "rem:list:0"))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("rem:del:"))
    def _del(call):
        if common.ensure_access(call) is None:
            return
        models.delete_reminder(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render(call, call.from_user.id, 0)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("rem:rep:"))
    def _repeat(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        repeat = call.data.split(":", 2)[2]
        _save(call.message.chat.id, call.from_user.id, flow.data, repeat)
        states.clear(call.from_user.id)

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "text":
            text = (message.text or "").strip()[:200]
            if not text:
                return common.send(message.chat.id, "Enter reminder text:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, text=text)
            states.set_step(uid, "datetime")
            common.send(message.chat.id, "📅 When? (e.g. 25-12-2026 or today):",
                        reply_markup=keyboards.cancel_kb())
        elif flow.step == "datetime":
            when = parse_date(message.text)
            if not when:
                return common.send(message.chat.id,
                                   "❌ Invalid date. Try 25-12-2026:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, next_run=when)
            states.set_step(uid, "repeat")
            common.send(message.chat.id, "🔁 Repeat?",
                        reply_markup=keyboards.reminder_repeat_kb())

    register_flow(FLOW, _flow)


def _save(chat_id, uid, data, repeat):
    if "next_run" not in data:
        return common.send(chat_id, "Missing date. Please start again.",
                           reply_markup=keyboards.reminders_menu())
    rem = models.add_reminder(uid, data["text"], data["next_run"], repeat)
    tz = common.user_timezone(uid)
    common.send(chat_id, "✅ Reminder set for %s (%s)." % (
        fmt_datetime(rem["next_run"], tz), repeat),
        reply_markup=keyboards.reminders_menu())


def _render(call, uid, page):
    rems = models.list_reminders(uid)
    total_pages = max(1, math.ceil(len(rems) / PAGE))
    page = max(0, min(page, total_pages - 1))
    subset = rems[page * PAGE:(page + 1) * PAGE]
    tz = common.user_timezone(uid)
    if not subset:
        return common.safe_edit(call, "No active reminders.",
                                reply_markup=keyboards.reminders_menu())

    def label(it):
        return "%s • %s" % (truncate(it["text"], 18),
                            fmt_datetime(it.get("next_run"), tz))

    kb = keyboards.paginated_list(subset, label, "rem:view", page, total_pages,
                                  "rem:list", back_data="rem:menu")
    common.safe_edit(call, "🔔 <b>Reminders</b> (page %d/%d)" % (
        page + 1, total_pages), reply_markup=kb)

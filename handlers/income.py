"""Income management handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import parse_amount, fmt_money, fmt_datetime, truncate

PAGE_SIZE = 6
FLOW = "income"


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "inc:add")
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="amount")
        common.safe_edit(
            call, "💵 <b>Add Income</b>\n\nEnter the amount:",
            reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("inc:src:"))
    def _source(call):
        user = common.ensure_access(call)
        if user is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        source = call.data.split(":", 2)[2]
        common.answer(call)
        if source == "__custom__":
            states.set_step(call.from_user.id, "custom_source")
            return common.safe_edit(call, "✏️ Enter the custom source name:",
                                    reply_markup=keyboards.cancel_kb())
        states.update_data(call.from_user.id, source=source)
        states.set_step(call.from_user.id, "note")
        common.safe_edit(call, "📝 Add a note (or skip):",
                         reply_markup=keyboards.skip_kb("inc:note:skip"))

    @bot.callback_query_handler(func=lambda c: c.data == "inc:note:skip")
    def _skip(call):
        user = common.ensure_access(call)
        if user is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        _save(call.message.chat.id, call.from_user.id, flow.data, "")
        states.clear(call.from_user.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("inc:list:"))
    def _list(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render_list(call, call.from_user.id, int(call.data.split(":")[2]))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("inc:view:"))
    def _view(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        item = models.get_income(call.from_user.id, call.data.split(":", 2)[2])
        if not item:
            return common.safe_edit(call, "Not found.",
                                    reply_markup=keyboards.back_home("inc:list:0"))
        cur = common.user_currency(call.from_user.id)
        tz = common.user_timezone(call.from_user.id)
        text = ("💵 <b>Income</b>\n\nAmount: <b>%s</b>\nSource: %s\nNote: %s\n"
                "Date: %s") % (fmt_money(item["amount"], cur),
                               item.get("source", "-"), item.get("note") or "-",
                               fmt_datetime(item.get("date"), tz))
        common.safe_edit(call, text,
                         reply_markup=keyboards.entity_actions_kb(
                             "inc", item["_id"], "inc:list:0"))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("inc:del:"))
    def _del(call):
        if common.ensure_access(call) is None:
            return
        models.delete_income(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render_list(call, call.from_user.id, 0)

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "amount":
            amount = parse_amount(message.text)
            if amount is None or amount <= 0:
                return common.send(message.chat.id, "❌ Invalid amount. Try again:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, amount=amount)
            states.set_step(uid, "source")
            common.send(message.chat.id, "🏦 Select income source:",
                        reply_markup=keyboards.income_source_kb(
                            models.DEFAULT_INCOME_SOURCES))
        elif flow.step == "custom_source":
            name = (message.text or "").strip()[:30]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, source=name)
            states.set_step(uid, "note")
            common.send(message.chat.id, "📝 Add a note (or skip):",
                        reply_markup=keyboards.skip_kb("inc:note:skip"))
        elif flow.step == "note":
            note = (message.text or "").strip()[:200]
            _save(message.chat.id, uid, flow.data, note)
            states.clear(uid)

    register_flow(FLOW, _flow)


def _save(chat_id, uid, data, note):
    item = models.add_income(uid, data["amount"], data.get("source", "Other"), note)
    models.add_ledger_entry(uid, "credit", data["amount"],
                            category=data.get("source", "Income"), note=note)
    cur = common.user_currency(uid)
    common.send(chat_id, "✅ Income saved: <b>%s</b> (%s)" % (
        fmt_money(item["amount"], cur), item.get("source")),
        reply_markup=keyboards.main_menu(common.is_admin_uid(uid)))


def _render_list(call, uid, page):
    all_items = models.list_income(uid)
    total = len(all_items)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    items = all_items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    cur = common.user_currency(uid)
    if not items:
        return common.safe_edit(call, "No income recorded yet.",
                                reply_markup=keyboards.back_home())

    def label(it):
        return "%s • %s" % (fmt_money(it["amount"], cur),
                            truncate(it.get("source", "-"), 18))

    kb = keyboards.paginated_list(items, label, "inc:view", page, total_pages,
                                  "inc:list", back_data="menu:main")
    common.safe_edit(call, "💵 <b>Income</b> (page %d/%d)" % (page + 1, total_pages),
                     reply_markup=kb)

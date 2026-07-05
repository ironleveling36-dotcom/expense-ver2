"""Expense management handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import parse_amount, fmt_money, fmt_datetime, truncate

PAGE_SIZE = 6
FLOW = "expense"


def register(bot):
    # ---- Start add-expense flow ------------------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data == "exp:add")
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="amount")
        common.safe_edit(
            call,
            "💰 <b>Add Expense</b>\n\nEnter the amount (e.g. <code>250</code>):",
            reply_markup=keyboards.cancel_kb(),
        )

    # ---- Category chosen -------------------------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("exp:cat:"))
    def _category(call):
        user = common.ensure_access(call)
        if user is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        category = call.data.split(":", 2)[2]
        common.answer(call)
        if category == "__custom__":
            states.set_step(call.from_user.id, "custom_category")
            return common.safe_edit(
                call, "✏️ Enter the custom category name:",
                reply_markup=keyboards.cancel_kb())
        states.update_data(call.from_user.id, category=category)
        states.set_step(call.from_user.id, "payment")
        common.safe_edit(
            call, "💳 Select payment mode:",
            reply_markup=keyboards.payment_mode_kb())

    # ---- Payment mode chosen --------------------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("exp:pm:"))
    def _payment(call):
        user = common.ensure_access(call)
        if user is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        mode = call.data.split(":", 2)[2]
        states.update_data(call.from_user.id, payment_mode=mode)
        states.set_step(call.from_user.id, "note")
        common.answer(call)
        common.safe_edit(
            call, "📝 Add a note (or skip):",
            reply_markup=keyboards.skip_kb("exp:note:skip"))

    @bot.callback_query_handler(func=lambda c: c.data == "exp:note:skip")
    def _skip_note(call):
        user = common.ensure_access(call)
        if user is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        _save_expense(call.message.chat.id, call.from_user.id, flow.data, note="")
        states.clear(call.from_user.id)

    # ---- List / detail / delete ------------------------------------------ #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("exp:list:"))
    def _list(call):
        user = common.ensure_access(call)
        if user is None:
            return
        common.answer(call)
        page = int(call.data.split(":")[2])
        _render_list(call, call.from_user.id, page)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("exp:view:"))
    def _view(call):
        user = common.ensure_access(call)
        if user is None:
            return
        common.answer(call)
        item_id = call.data.split(":", 2)[2]
        item = models.get_expense(call.from_user.id, item_id)
        if not item:
            return common.safe_edit(call, "Not found.",
                                    reply_markup=keyboards.back_home("exp:list:0"))
        cur = common.user_currency(call.from_user.id)
        tz = common.user_timezone(call.from_user.id)
        text = (
            "🧾 <b>Expense</b>\n\n"
            "Amount: <b>%s</b>\n"
            "Category: %s\n"
            "Payment: %s\n"
            "Note: %s\n"
            "Date: %s"
        ) % (
            fmt_money(item["amount"], cur), item.get("category", "-"),
            item.get("payment_mode", "-"), item.get("note") or "-",
            fmt_datetime(item.get("date"), tz),
        )
        common.safe_edit(call, text,
                         reply_markup=keyboards.entity_actions_kb(
                             "exp", item["_id"], "exp:list:0"))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("exp:del:"))
    def _delete(call):
        user = common.ensure_access(call)
        if user is None:
            return
        item_id = call.data.split(":", 2)[2]
        models.delete_expense(call.from_user.id, item_id)
        common.answer(call, "Deleted")
        _render_list(call, call.from_user.id, 0)

    # ---- Flow: text steps ------------------------------------------------- #
    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "amount":
            amount = parse_amount(message.text)
            if amount is None or amount <= 0:
                return common.send(message.chat.id,
                                   "❌ Invalid amount. Enter a number like 250:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, amount=amount)
            states.set_step(uid, "category")
            cats = models.get_categories(uid)
            common.send(message.chat.id, "🏷 Select a category:",
                        reply_markup=keyboards.category_kb(cats))
        elif flow.step == "custom_category":
            name = (message.text or "").strip()[:30]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            models.add_category(uid, name)
            states.update_data(uid, category=name)
            states.set_step(uid, "payment")
            common.send(message.chat.id, "💳 Select payment mode:",
                        reply_markup=keyboards.payment_mode_kb())
        elif flow.step == "note":
            note = (message.text or "").strip()[:200]
            _save_expense(message.chat.id, uid, flow.data, note=note)
            states.clear(uid)

    register_flow(FLOW, _flow)


def _save_expense(chat_id, uid, data, note=""):
    item = models.add_expense(
        uid, data["amount"], data.get("category", "Other"),
        payment_mode=data.get("payment_mode", "Cash"), note=note,
    )
    # Mirror into ledger as a debit for a unified balance view.
    models.add_ledger_entry(uid, "debit", data["amount"],
                            category=data.get("category", "Other"), note=note)
    cur = common.user_currency(uid)
    _check_budget_alerts(chat_id, uid, cur)
    common.send(
        chat_id,
        "✅ Expense saved: <b>%s</b> (%s)" % (
            fmt_money(item["amount"], cur), item.get("category")),
        reply_markup=keyboards.main_menu(common.is_admin_uid(uid)),
    )


def _render_list(call, uid, page):
    total = models.count_expenses(uid)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    items = models.list_expenses(uid, limit=PAGE_SIZE, skip=page * PAGE_SIZE)
    cur = common.user_currency(uid)
    if not items:
        return common.safe_edit(call, "No expenses recorded yet.",
                                reply_markup=keyboards.back_home())

    def label(it):
        return "%s • %s" % (fmt_money(it["amount"], cur),
                            truncate(it.get("category", "-"), 18))

    header = "🧾 <b>Expenses</b> (page %d/%d)" % (page + 1, total_pages)
    kb = keyboards.paginated_list(items, label, "exp:view", page, total_pages,
                                  "exp:list", back_data="menu:main")
    common.safe_edit(call, header, reply_markup=kb)


def _check_budget_alerts(chat_id, uid, cur):
    """Notify the user when spending crosses budget thresholds."""
    from utils.helpers import period_bounds
    tz = common.user_timezone(uid)
    for period in ("day", "week", "month"):
        budget = models.get_budget(uid, period)
        if not budget:
            continue
        limit = float(budget.get("amount", 0))
        if limit <= 0:
            continue
        start, end = period_bounds(period, tz_name=tz)
        spent = models.sum_expenses(uid, {"date": {"$gte": start, "$lt": end}})
        pct = (spent / limit) * 100 if limit else 0
        for threshold, emoji in ((100, "🔴"), (90, "🟠"), (75, "🟡"), (50, "🟢")):
            if pct >= threshold:
                common.send(
                    chat_id,
                    "%s <b>%s budget alert</b>: %.0f%% used "
                    "(%s of %s)" % (emoji, period.capitalize(), pct,
                                    fmt_money(spent, cur), fmt_money(limit, cur)),
                )
                break

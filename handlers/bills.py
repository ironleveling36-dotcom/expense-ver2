"""Bill management handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import parse_amount, parse_date, fmt_money, fmt_date, truncate

PAGE = 8
FLOW = "bill"

BILL_CATEGORIES = ["Electricity", "Water", "Internet", "Mobile", "Gas", "Rent",
                   "Insurance", "EMI", "Credit Card", "Other"]


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "bill:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "📅 <b>Bill Management</b>",
                         reply_markup=keyboards.bills_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "bill:add")
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="name")
        common.safe_edit(call, "📅 <b>Add Bill</b>\n\nEnter the bill name:",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bill:cat:"))
    def _cat(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        cat = call.data.split(":", 2)[2]
        states.update_data(call.from_user.id, category=cat)
        states.set_step(call.from_user.id, "due")
        common.safe_edit(call, "📅 Due date (e.g. 25-12-2026) or skip:",
                         reply_markup=keyboards.skip_kb("bill:skip:due"))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bill:list:"))
    def _list(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, int(call.data.split(":")[2]), None)

    @bot.callback_query_handler(func=lambda c: c.data == "bill:unpaid")
    def _unpaid(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, 0, "unpaid")

    @bot.callback_query_handler(func=lambda c: c.data == "bill:paid")
    def _paid(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, 0, "paid")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bill:view:"))
    def _view(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        bill = models.get_bill(uid, call.data.split(":", 2)[2])
        if not bill:
            return common.safe_edit(call, "Not found.",
                                    reply_markup=keyboards.back_home("bill:list:0"))
        cur = common.user_currency(uid)
        tz = common.user_timezone(uid)
        status = "✅ Paid" if bill.get("status") == "paid" else "🔴 Unpaid"
        text = ("📅 <b>%s</b>\n\nAmount: %s\nCategory: %s\nDue: %s\nStatus: %s") % (
            bill["name"], fmt_money(bill["amount"], cur),
            bill.get("category", "-"),
            fmt_date(bill.get("due_date"), tz) if bill.get("due_date") else "-",
            status)
        common.safe_edit(call, text, reply_markup=keyboards.bill_actions_kb(
            bill["_id"], paid=(bill.get("status") == "paid")))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bill:markpaid:"))
    def _markpaid(call):
        if common.ensure_access(call) is None:
            return
        uid = call.from_user.id
        bill_id = call.data.split(":", 2)[2]
        bill = models.get_bill(uid, bill_id)
        models.mark_bill_paid(uid, bill_id)
        if bill:
            models.add_expense(uid, bill["amount"], bill.get("category", "Bills"),
                               payment_mode="Bill", note="Bill: %s" % bill["name"])
            models.add_ledger_entry(uid, "debit", bill["amount"],
                                    category="Bills", note=bill["name"])
        common.answer(call, "Marked paid & logged as expense")
        _render(call, uid, 0, None)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bill:del:"))
    def _del(call):
        if common.ensure_access(call) is None:
            return
        models.delete_bill(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render(call, call.from_user.id, 0, None)

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "name":
            name = (message.text or "").strip()[:50]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, name=name)
            states.set_step(uid, "amount")
            common.send(message.chat.id, "💰 Enter the bill amount:",
                        reply_markup=keyboards.cancel_kb())
        elif flow.step == "amount":
            amount = parse_amount(message.text)
            if not amount:
                return common.send(message.chat.id, "❌ Invalid amount:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, amount=amount)
            states.set_step(uid, "category")
            common.send(message.chat.id, "🏷 Select category:",
                        reply_markup=keyboards.category_kb(BILL_CATEGORIES, "bill:cat"))
        elif flow.step == "due":
            due = parse_date(message.text)
            _save(message.chat.id, uid, flow.data, due)
            states.clear(uid)

    register_flow(FLOW, _flow)

    @bot.callback_query_handler(func=lambda c: c.data == "bill:skip:due")
    def _skipdue(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        _save(call.message.chat.id, call.from_user.id, flow.data, None)
        states.clear(call.from_user.id)


def _save(chat_id, uid, data, due):
    bill = models.add_bill(uid, data["name"], data["amount"],
                           category=data.get("category", "Other"), due_date=due)
    cur = common.user_currency(uid)
    common.send(chat_id, "✅ Bill <b>%s</b> (%s) saved." % (
        bill["name"], fmt_money(bill["amount"], cur)),
        reply_markup=keyboards.bills_menu())


def _render(call, uid, page, status):
    query = {"status": status} if status else None
    bills = models.list_bills(uid, query)
    total_pages = max(1, math.ceil(len(bills) / PAGE))
    page = max(0, min(page, total_pages - 1))
    subset = bills[page * PAGE:(page + 1) * PAGE]
    cur = common.user_currency(uid)
    if not subset:
        return common.safe_edit(call, "No bills found.",
                                reply_markup=keyboards.bills_menu())

    def label(it):
        mark = "✅" if it.get("status") == "paid" else "🔴"
        return "%s %s • %s" % (mark, truncate(it["name"], 14),
                               fmt_money(it["amount"], cur))

    title = "📅 <b>Bills</b>"
    if status:
        title = "📅 <b>%s Bills</b>" % status.capitalize()
    kb = keyboards.paginated_list(subset, label, "bill:view", page, total_pages,
                                  "bill:list", back_data="bill:menu")
    common.safe_edit(call, "%s (page %d/%d)" % (title, page + 1, total_pages),
                     reply_markup=kb)

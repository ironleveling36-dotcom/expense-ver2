"""Borrow & Lending manager handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import (parse_amount, parse_date, fmt_money, fmt_date,
                           truncate, utcnow)

PAGE = 6


def register(bot):
    # ------------------------------ menus --------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data == "bor:menu")
    def _bmenu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "🤝 <b>Borrow Manager</b>\nMoney you borrowed.",
                         reply_markup=keyboards.borrow_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "lend:menu")
    def _lmenu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "💵 <b>Lending Manager</b>\nMoney you lent out.",
                         reply_markup=keyboards.lending_menu())

    # ------------------------------ add flows ----------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data == "bor:add")
    def _badd(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, "borrow", step="name")
        common.safe_edit(call, "🤝 <b>New Borrow</b>\n\nWhose money did you borrow? "
                               "Enter the person's name:",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data == "lend:add")
    def _ladd(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, "lending", step="name")
        common.safe_edit(call, "💵 <b>New Lending</b>\n\nWho did you lend to? "
                               "Enter the person's name:",
                         reply_markup=keyboards.cancel_kb())

    # ------------------------------ lists --------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bor:list:"))
    def _blist(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, "borrow", int(call.data.split(":")[2]))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("lend:list:"))
    def _llist(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, "lending", int(call.data.split(":")[2]))

    # ------------------------------ views --------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bor:view:"))
    def _bview(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _view(call, "borrow")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("lend:view:"))
    def _lview(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _view(call, "lending")

    # ------------------------------ payments ------------------------------ #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bor:pay:"))
    def _bpay(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        item_id = call.data.split(":", 2)[2]
        states.start(call.from_user.id, "borrow_pay", step="amount",
                     data={"item_id": item_id})
        common.safe_edit(call, "💰 Enter repayment amount:",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("lend:pay:"))
    def _lpay(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        item_id = call.data.split(":", 2)[2]
        states.start(call.from_user.id, "lending_pay", step="amount",
                     data={"item_id": item_id})
        common.safe_edit(call, "💰 Enter amount received:",
                         reply_markup=keyboards.cancel_kb())

    # ------------------------------ delete -------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bor:del:"))
    def _bdel(call):
        if common.ensure_access(call) is None:
            return
        models.delete_borrow(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render(call, call.from_user.id, "borrow", 0)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("lend:del:"))
    def _ldel(call):
        if common.ensure_access(call) is None:
            return
        models.delete_lending(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render(call, call.from_user.id, "lending", 0)

    # ------------------------------ overdue / summary --------------------- #
    @bot.callback_query_handler(func=lambda c: c.data == "bor:overdue")
    def _boverdue(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _overdue(call, "borrow")

    @bot.callback_query_handler(func=lambda c: c.data == "lend:overdue")
    def _loverdue(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _overdue(call, "lending")

    @bot.callback_query_handler(func=lambda c: c.data == "bor:summary")
    def _bsum(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _summary(call, "borrow")

    @bot.callback_query_handler(func=lambda c: c.data == "lend:summary")
    def _lsum(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _summary(call, "lending")

    # ------------------------------ flows --------------------------------- #
    def _borrow_flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "name":
            name = (message.text or "").strip()[:50]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, name=name)
            states.set_step(uid, "amount")
            common.send(message.chat.id, "💰 Enter the borrowed amount:",
                        reply_markup=keyboards.cancel_kb())
        elif flow.step == "amount":
            amount = parse_amount(message.text)
            if not amount:
                return common.send(message.chat.id, "❌ Invalid amount:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, amount=amount)
            states.set_step(uid, "purpose")
            common.send(message.chat.id, "🎯 Purpose (or skip):",
                        reply_markup=keyboards.skip_kb("bor:skip:purpose"))
        elif flow.step == "purpose":
            states.update_data(uid, purpose=(message.text or "").strip()[:100])
            states.set_step(uid, "due")
            common.send(message.chat.id, "📅 Due date (e.g. 25-12-2026) or skip:",
                        reply_markup=keyboards.skip_kb("bor:skip:due"))
        elif flow.step == "due":
            due = parse_date(message.text)
            _save_borrow(message.chat.id, uid, flow.data, due)
            states.clear(uid)

    def _lending_flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "name":
            name = (message.text or "").strip()[:50]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, name=name)
            states.set_step(uid, "amount")
            common.send(message.chat.id, "💰 Enter the lent amount:",
                        reply_markup=keyboards.cancel_kb())
        elif flow.step == "amount":
            amount = parse_amount(message.text)
            if not amount:
                return common.send(message.chat.id, "❌ Invalid amount:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, amount=amount)
            states.set_step(uid, "phone")
            common.send(message.chat.id, "📞 Phone number (or skip):",
                        reply_markup=keyboards.skip_kb("lend:skip:phone"))
        elif flow.step == "phone":
            states.update_data(uid, phone=(message.text or "").strip()[:20])
            states.set_step(uid, "due")
            common.send(message.chat.id, "📅 Due date or skip:",
                        reply_markup=keyboards.skip_kb("lend:skip:due"))
        elif flow.step == "due":
            due = parse_date(message.text)
            _save_lending(message.chat.id, uid, flow.data, due)
            states.clear(uid)

    def _borrow_pay_flow(message, user, flow):
        uid = message.from_user.id
        amount = parse_amount(message.text)
        if not amount:
            return common.send(message.chat.id, "❌ Invalid amount:",
                               reply_markup=keyboards.cancel_kb())
        doc = models.add_borrow_payment(uid, flow.data["item_id"], amount)
        states.clear(uid)
        cur = common.user_currency(uid)
        if not doc:
            return common.send(message.chat.id, "Record not found.",
                               reply_markup=keyboards.borrow_menu())
        remaining = float(doc["amount"]) - float(doc.get("paid", 0))
        common.send(message.chat.id,
                    "✅ Repayment recorded. Remaining: <b>%s</b>" %
                    fmt_money(max(0, remaining), cur),
                    reply_markup=keyboards.borrow_menu())

    def _lending_pay_flow(message, user, flow):
        uid = message.from_user.id
        amount = parse_amount(message.text)
        if not amount:
            return common.send(message.chat.id, "❌ Invalid amount:",
                               reply_markup=keyboards.cancel_kb())
        doc = models.add_lending_payment(uid, flow.data["item_id"], amount)
        states.clear(uid)
        cur = common.user_currency(uid)
        if not doc:
            return common.send(message.chat.id, "Record not found.",
                               reply_markup=keyboards.lending_menu())
        remaining = float(doc["amount"]) - float(doc.get("received", 0))
        common.send(message.chat.id,
                    "✅ Payment recorded. Remaining: <b>%s</b>" %
                    fmt_money(max(0, remaining), cur),
                    reply_markup=keyboards.lending_menu())

    register_flow("borrow", _borrow_flow)
    register_flow("lending", _lending_flow)
    register_flow("borrow_pay", _borrow_pay_flow)
    register_flow("lending_pay", _lending_pay_flow)

    # ------------------------------ skip callbacks ------------------------ #
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bor:skip:"))
    def _bskip(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != "borrow":
            return common.answer(call, "Session expired.")
        common.answer(call)
        what = call.data.split(":", 2)[2]
        uid = call.from_user.id
        if what == "purpose":
            states.update_data(uid, purpose="")
            states.set_step(uid, "due")
            common.safe_edit(call, "📅 Due date (e.g. 25-12-2026) or skip:",
                             reply_markup=keyboards.skip_kb("bor:skip:due"))
        elif what == "due":
            _save_borrow(call.message.chat.id, uid, flow.data, None)
            states.clear(uid)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("lend:skip:"))
    def _lskip(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != "lending":
            return common.answer(call, "Session expired.")
        common.answer(call)
        what = call.data.split(":", 2)[2]
        uid = call.from_user.id
        if what == "phone":
            states.update_data(uid, phone="")
            states.set_step(uid, "due")
            common.safe_edit(call, "📅 Due date or skip:",
                             reply_markup=keyboards.skip_kb("lend:skip:due"))
        elif what == "due":
            _save_lending(call.message.chat.id, uid, flow.data, None)
            states.clear(uid)


# --------------------------------------------------------------------------- #
# Save helpers
# --------------------------------------------------------------------------- #
def _save_borrow(chat_id, uid, data, due):
    item = models.add_borrow(uid, data["name"], data["amount"],
                             purpose=data.get("purpose", ""), due_date=due)
    cur = common.user_currency(uid)
    common.send(chat_id, "✅ Borrow recorded: <b>%s</b> from %s" % (
        fmt_money(item["amount"], cur), item["name"]),
        reply_markup=keyboards.borrow_menu())


def _save_lending(chat_id, uid, data, due):
    item = models.add_lending(uid, data["name"], data["amount"],
                              phone=data.get("phone", ""), due_date=due)
    cur = common.user_currency(uid)
    common.send(chat_id, "✅ Lending recorded: <b>%s</b> to %s" % (
        fmt_money(item["amount"], cur), item["name"]),
        reply_markup=keyboards.lending_menu())


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _render(call, uid, kind, page):
    lister = models.list_borrow if kind == "borrow" else models.list_lending
    items = lister(uid, {"status": "open"})
    total_pages = max(1, math.ceil(len(items) / PAGE))
    page = max(0, min(page, total_pages - 1))
    subset = items[page * PAGE:(page + 1) * PAGE]
    cur = common.user_currency(uid)
    menu = keyboards.borrow_menu if kind == "borrow" else keyboards.lending_menu
    if not subset:
        return common.safe_edit(call, "No open records.", reply_markup=menu())
    paid_field = "paid" if kind == "borrow" else "received"

    def label(it):
        remaining = float(it["amount"]) - float(it.get(paid_field, 0))
        return "%s • %s left" % (truncate(it["name"], 14),
                                 fmt_money(max(0, remaining), cur))

    prefix = "bor:view" if kind == "borrow" else "lend:view"
    page_prefix = "bor:list" if kind == "borrow" else "lend:list"
    back = "bor:menu" if kind == "borrow" else "lend:menu"
    title = "🤝 <b>Borrowings</b>" if kind == "borrow" else "💵 <b>Lendings</b>"
    kb = keyboards.paginated_list(subset, label, prefix, page, total_pages,
                                  page_prefix, back_data=back)
    common.safe_edit(call, "%s (page %d/%d)" % (title, page + 1, total_pages),
                     reply_markup=kb)


def _view(call, kind):
    uid = call.from_user.id
    item_id = call.data.split(":", 2)[2]
    getter = models.get_borrow if kind == "borrow" else models.get_lending
    item = getter(uid, item_id)
    back = "bor:menu" if kind == "borrow" else "lend:menu"
    if not item:
        return common.safe_edit(call, "Not found.", reply_markup=keyboards.back_home(back))
    cur = common.user_currency(uid)
    tz = common.user_timezone(uid)
    paid_field = "paid" if kind == "borrow" else "received"
    remaining = float(item["amount"]) - float(item.get(paid_field, 0))
    lines = [
        "🤝 <b>Borrow Detail</b>" if kind == "borrow" else "💵 <b>Lending Detail</b>",
        "",
        "Person: <b>%s</b>" % item["name"],
        "Amount: %s" % fmt_money(item["amount"], cur),
        "%s: %s" % ("Repaid" if kind == "borrow" else "Received",
                    fmt_money(item.get(paid_field, 0), cur)),
        "Remaining: <b>%s</b>" % fmt_money(max(0, remaining), cur),
        "Status: %s" % item.get("status", "open"),
    ]
    if kind == "borrow" and item.get("purpose"):
        lines.append("Purpose: %s" % item["purpose"])
    if kind == "lending" and item.get("phone"):
        lines.append("Phone: %s" % item["phone"])
    if item.get("due_date"):
        lines.append("Due: %s" % fmt_date(item["due_date"], tz))
    payments = item.get("payments", [])
    if payments:
        lines.append("\n<b>Payment history:</b>")
        for p in payments[-5:]:
            lines.append("• %s on %s" % (fmt_money(p["amount"], cur),
                                         fmt_date(p.get("date"), tz)))
    prefix = "bor" if kind == "borrow" else "lend"
    common.safe_edit(call, "\n".join(lines),
                     reply_markup=keyboards.repay_kb(prefix, item["_id"], back))


def _overdue(call, kind):
    uid = call.from_user.id
    lister = models.list_borrow if kind == "borrow" else models.list_lending
    items = lister(uid, {"status": "open"})
    now = utcnow()
    overdue = [i for i in items if i.get("due_date") and i["due_date"] < now]
    cur = common.user_currency(uid)
    tz = common.user_timezone(uid)
    menu = keyboards.borrow_menu if kind == "borrow" else keyboards.lending_menu
    if not overdue:
        return common.safe_edit(call, "✅ Nothing overdue.", reply_markup=menu())
    paid_field = "paid" if kind == "borrow" else "received"
    lines = ["⚠️ <b>Overdue</b>\n"]
    for i in overdue:
        rem = float(i["amount"]) - float(i.get(paid_field, 0))
        lines.append("• %s — %s (due %s)" % (
            i["name"], fmt_money(max(0, rem), cur), fmt_date(i["due_date"], tz)))
    common.safe_edit(call, "\n".join(lines), reply_markup=menu())


def _summary(call, kind):
    uid = call.from_user.id
    lister = models.list_borrow if kind == "borrow" else models.list_lending
    items = lister(uid)
    cur = common.user_currency(uid)
    paid_field = "paid" if kind == "borrow" else "received"
    total = sum(float(i["amount"]) for i in items)
    paid = sum(float(i.get(paid_field, 0)) for i in items)
    remaining = total - paid
    open_count = sum(1 for i in items if i.get("status") == "open")
    menu = keyboards.borrow_menu if kind == "borrow" else keyboards.lending_menu
    label = "Borrowed" if kind == "borrow" else "Lent"
    settled = "Repaid" if kind == "borrow" else "Received"
    text = ("📊 <b>%s Summary</b>\n\n"
            "Total %s: %s\n"
            "%s: %s\n"
            "Outstanding: <b>%s</b>\n"
            "Open records: %d") % (
        "Borrow" if kind == "borrow" else "Lending", label,
        fmt_money(total, cur), settled, fmt_money(paid, cur),
        fmt_money(max(0, remaining), cur), open_count)
    common.safe_edit(call, text, reply_markup=menu())

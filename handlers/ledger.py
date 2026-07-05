"""Credit & Debit ledger handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import parse_amount, fmt_money, fmt_datetime, truncate

PAGE = 8
FLOW = "ledger"


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "led:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "💳 <b>Credit / Debit Ledger</b>",
                         reply_markup=keyboards.ledger_menu())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("led:add:"))
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        entry_type = call.data.split(":", 2)[2]
        states.start(call.from_user.id, FLOW, step="amount",
                     data={"type": entry_type})
        common.safe_edit(call, "%s Enter amount:" % (
            "➕ Credit —" if entry_type == "credit" else "➖ Debit —"),
            reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data == "led:balance")
    def _balance(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        bal = models.ledger_balance(uid)
        cur = common.user_currency(uid)
        common.safe_edit(call, "💰 <b>Running Balance</b>\n\n<b>%s</b>" %
                         fmt_money(bal, cur), reply_markup=keyboards.ledger_menu())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("led:list:"))
    def _list(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, int(call.data.split(":")[2]))

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "amount":
            amount = parse_amount(message.text)
            if not amount:
                return common.send(message.chat.id, "❌ Invalid amount:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, amount=amount)
            states.set_step(uid, "note")
            common.send(message.chat.id, "📝 Add a note (or skip):",
                        reply_markup=keyboards.skip_kb("led:note:skip"))
        elif flow.step == "note":
            note = (message.text or "").strip()[:200]
            _save(message.chat.id, uid, flow.data, note)
            states.clear(uid)

    register_flow(FLOW, _flow)

    @bot.callback_query_handler(func=lambda c: c.data == "led:note:skip")
    def _skip(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        _save(call.message.chat.id, call.from_user.id, flow.data, "")
        states.clear(call.from_user.id)


def _save(chat_id, uid, data, note):
    item = models.add_ledger_entry(uid, data["type"], data["amount"], note=note)
    cur = common.user_currency(uid)
    common.send(chat_id, "✅ %s of <b>%s</b> recorded.\nNew balance: <b>%s</b>" % (
        data["type"].capitalize(), fmt_money(item["amount"], cur),
        fmt_money(item["balance"], cur)),
        reply_markup=keyboards.ledger_menu())


def _render(call, uid, page):
    entries = models.list_ledger(uid)
    total_pages = max(1, math.ceil(len(entries) / PAGE))
    page = max(0, min(page, total_pages - 1))
    subset = entries[page * PAGE:(page + 1) * PAGE]
    cur = common.user_currency(uid)
    tz = common.user_timezone(uid)
    if not subset:
        return common.safe_edit(call, "No ledger entries yet.",
                                reply_markup=keyboards.ledger_menu())
    lines = ["💳 <b>Statement</b> (page %d/%d)\n" % (page + 1, total_pages)]
    for e in subset:
        sign = "➕" if e["type"] == "credit" else "➖"
        lines.append("%s %s | Bal: %s\n   %s • %s" % (
            sign, fmt_money(e["amount"], cur), fmt_money(e.get("balance", 0), cur),
            truncate(e.get("note") or e.get("category") or "-", 24),
            fmt_datetime(e.get("date"), tz)))
    kb = keyboards.types.InlineKeyboardMarkup()
    nav = []
    if page > 0:
        nav.append(keyboards.types.InlineKeyboardButton(
            "⬅️ Prev", callback_data="led:list:%d" % (page - 1)))
    if page < total_pages - 1:
        nav.append(keyboards.types.InlineKeyboardButton(
            "➡️ Next", callback_data="led:list:%d" % (page + 1)))
    if nav:
        kb.row(*nav)
    kb.row(keyboards.types.InlineKeyboardButton("⬅️ Back", callback_data="led:menu"),
           keyboards.types.InlineKeyboardButton("🏠 Home", callback_data="menu:main"))
    common.safe_edit(call, "\n".join(lines), reply_markup=kb)

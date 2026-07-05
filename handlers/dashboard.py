"""Interactive dashboard handler."""
from keyboards import keyboards
from handlers import common
from database import models
from utils.helpers import period_bounds, fmt_money, fmt_date, utcnow


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "dash:show")
    def _show(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        cur = common.user_currency(uid)
        tz = common.user_timezone(uid)

        day_start, day_end = period_bounds("day", tz_name=tz)
        month_start, month_end = period_bounds("month", tz_name=tz)

        today_exp = models.sum_expenses(uid, {"date": {"$gte": day_start, "$lt": day_end}})
        month_exp = models.sum_expenses(uid, {"date": {"$gte": month_start, "$lt": month_end}})
        month_inc = models.sum_income(uid, {"date": {"$gte": month_start, "$lt": month_end}})
        balance = models.ledger_balance(uid)
        savings = sum(float(g.get("saved", 0)) for g in models.list_savings(uid))

        borrow_items = models.list_borrow(uid, {"status": "open"})
        lend_items = models.list_lending(uid, {"status": "open"})
        borrowed = sum(float(i["amount"]) - float(i.get("paid", 0)) for i in borrow_items)
        lent = sum(float(i["amount"]) - float(i.get("received", 0)) for i in lend_items)

        pending_bills = models.list_bills(uid, {"status": "unpaid"})
        reminders = models.list_reminders(uid)
        recent = models.list_expenses(uid, limit=3)

        lines = [
            "📈 <b>Dashboard</b>\n",
            "💰 Wallet Balance: <b>%s</b>" % fmt_money(balance, cur),
            "💸 Today's Expense: %s" % fmt_money(today_exp, cur),
            "🗓 Monthly Expense: %s" % fmt_money(month_exp, cur),
            "💵 Monthly Income: %s" % fmt_money(month_inc, cur),
            "🎯 Total Savings: %s" % fmt_money(savings, cur),
            "🤝 Outstanding Borrowed: %s" % fmt_money(max(0, borrowed), cur),
            "📤 Outstanding Lent: %s" % fmt_money(max(0, lent), cur),
            "📅 Pending Bills: %d" % len(pending_bills),
            "🔔 Active Reminders: %d" % len(reminders),
        ]
        if recent:
            lines.append("\n<b>Recent Expenses:</b>")
            for e in recent:
                lines.append("• %s — %s (%s)" % (
                    fmt_money(e["amount"], cur), e.get("category", "-"),
                    fmt_date(e.get("date"), tz)))
        common.safe_edit(call, "\n".join(lines),
                         reply_markup=keyboards.back_home())

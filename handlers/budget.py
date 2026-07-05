"""Budget & spending limits handlers."""
from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import parse_amount, fmt_money, period_bounds, progress_bar

FLOW = "budget"


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "bud:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "💹 <b>Budget & Limits</b>",
                         reply_markup=keyboards.budget_menu())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bud:set:"))
    def _set(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        period = call.data.split(":", 2)[2]
        states.start(call.from_user.id, FLOW, step="amount",
                     data={"period": period, "category": None})
        common.safe_edit(call, "💹 Enter the %s spending limit:" % period,
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data == "bud:setcat")
    def _setcat(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="category")
        common.safe_edit(call, "🏷 Enter category name for the limit:",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data == "bud:view")
    def _view(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        cur = common.user_currency(uid)
        tz = common.user_timezone(uid)
        budgets = models.list_budgets(uid)
        if not budgets:
            return common.safe_edit(call, "No budgets set yet.",
                                    reply_markup=keyboards.budget_menu())
        lines = ["💹 <b>Your Budgets</b>\n"]
        for b in budgets:
            period = b.get("period", "month")
            category = b.get("category")
            limit = float(b.get("amount", 0))
            if period in ("day", "week", "month", "year"):
                start, end = period_bounds(period, tz_name=tz)
            else:
                start, end = period_bounds("month", tz_name=tz)
            query = {"date": {"$gte": start, "$lt": end}}
            if category:
                query["category"] = category
            spent = models.sum_expenses(uid, query)
            pct = (spent / limit * 100) if limit else 0
            name = "%s%s" % (period.capitalize(),
                             " / %s" % category if category else "")
            lines.append("<b>%s</b>\n%s %.0f%%\n%s of %s\n" % (
                name, progress_bar(pct), pct,
                fmt_money(spent, cur), fmt_money(limit, cur)))
        common.safe_edit(call, "\n".join(lines),
                         reply_markup=keyboards.budget_menu())

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "category":
            cat = (message.text or "").strip()[:30]
            if not cat:
                return common.send(message.chat.id, "Enter a valid category:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, category=cat, period="month")
            states.set_step(uid, "amount")
            common.send(message.chat.id,
                        "💹 Enter the monthly limit for <b>%s</b>:" % cat,
                        reply_markup=keyboards.cancel_kb())
        elif flow.step == "amount":
            amount = parse_amount(message.text)
            if not amount:
                return common.send(message.chat.id, "❌ Invalid amount:",
                                   reply_markup=keyboards.cancel_kb())
            models.set_budget(uid, flow.data.get("period", "month"), amount,
                              flow.data.get("category"))
            states.clear(uid)
            cur = common.user_currency(uid)
            common.send(message.chat.id, "✅ Budget set: %s" % fmt_money(amount, cur),
                        reply_markup=keyboards.budget_menu())

    register_flow(FLOW, _flow)

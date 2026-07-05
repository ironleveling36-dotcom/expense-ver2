"""Savings goals handlers."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import (parse_amount, parse_date, fmt_money, fmt_date,
                           truncate, progress_bar)

PAGE = 8
FLOW = "savings"


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "sav:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "🎯 <b>Savings Goals</b>",
                         reply_markup=keyboards.savings_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "sav:add")
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="name")
        common.safe_edit(call, "🎯 <b>New Goal</b>\n\nWhat are you saving for? "
                               "(e.g. Bike, Vacation):",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("sav:list:"))
    def _list(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, int(call.data.split(":")[2]))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("sav:view:"))
    def _view(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _detail(call, call.from_user.id, call.data.split(":", 2)[2])

    @bot.callback_query_handler(func=lambda c: c.data.startswith("sav:contrib:"))
    def _contrib(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        item_id = call.data.split(":", 2)[2]
        states.start(call.from_user.id, "savings_contrib", step="amount",
                     data={"item_id": item_id})
        common.safe_edit(call, "💰 How much to add to this goal?",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("sav:del:"))
    def _del(call):
        if common.ensure_access(call) is None:
            return
        models.delete_savings(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render(call, call.from_user.id, 0)

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "name":
            name = (message.text or "").strip()[:50]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, name=name)
            states.set_step(uid, "target")
            common.send(message.chat.id, "🎯 Target amount:",
                        reply_markup=keyboards.cancel_kb())
        elif flow.step == "target":
            target = parse_amount(message.text)
            if not target:
                return common.send(message.chat.id, "❌ Invalid amount:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, target=target)
            states.set_step(uid, "deadline")
            common.send(message.chat.id, "📅 Deadline (or skip):",
                        reply_markup=keyboards.skip_kb("sav:skip:deadline"))
        elif flow.step == "deadline":
            deadline = parse_date(message.text)
            _save(message.chat.id, uid, flow.data, deadline)
            states.clear(uid)

    def _contrib_flow(message, user, flow):
        uid = message.from_user.id
        amount = parse_amount(message.text)
        if not amount:
            return common.send(message.chat.id, "❌ Invalid amount:",
                               reply_markup=keyboards.cancel_kb())
        goal = models.add_savings_contribution(uid, flow.data["item_id"], amount)
        states.clear(uid)
        cur = common.user_currency(uid)
        if not goal:
            return common.send(message.chat.id, "Goal not found.",
                               reply_markup=keyboards.savings_menu())
        saved = float(goal.get("saved", 0))
        target = float(goal.get("target", 0))
        pct = (saved / target * 100) if target else 0
        common.send(message.chat.id,
                    "✅ Added! <b>%s</b>\n%s %.0f%%\n%s / %s" % (
                        goal["name"], progress_bar(pct), pct,
                        fmt_money(saved, cur), fmt_money(target, cur)),
                    reply_markup=keyboards.savings_menu())

    register_flow(FLOW, _flow)
    register_flow("savings_contrib", _contrib_flow)

    @bot.callback_query_handler(func=lambda c: c.data == "sav:skip:deadline")
    def _skip(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        _save(call.message.chat.id, call.from_user.id, flow.data, None)
        states.clear(call.from_user.id)


def _save(chat_id, uid, data, deadline):
    goal = models.add_savings(uid, data["name"], data["target"], deadline)
    cur = common.user_currency(uid)
    common.send(chat_id, "✅ Goal <b>%s</b> created (target %s)." % (
        goal["name"], fmt_money(goal["target"], cur)),
        reply_markup=keyboards.savings_menu())


def _render(call, uid, page):
    goals = models.list_savings(uid)
    total_pages = max(1, math.ceil(len(goals) / PAGE))
    page = max(0, min(page, total_pages - 1))
    subset = goals[page * PAGE:(page + 1) * PAGE]
    cur = common.user_currency(uid)
    if not subset:
        return common.safe_edit(call, "No savings goals yet.",
                                reply_markup=keyboards.savings_menu())

    def label(it):
        saved = float(it.get("saved", 0))
        target = float(it.get("target", 0))
        pct = (saved / target * 100) if target else 0
        return "%s • %.0f%%" % (truncate(it["name"], 16), pct)

    kb = keyboards.paginated_list(subset, label, "sav:view", page, total_pages,
                                  "sav:list", back_data="sav:menu")
    common.safe_edit(call, "🎯 <b>Savings Goals</b> (page %d/%d)" % (
        page + 1, total_pages), reply_markup=kb)


def _detail(call, uid, item_id):
    goal = models.get_savings(uid, item_id)
    if not goal:
        return common.safe_edit(call, "Not found.",
                                reply_markup=keyboards.back_home("sav:list:0"))
    cur = common.user_currency(uid)
    tz = common.user_timezone(uid)
    saved = float(goal.get("saved", 0))
    target = float(goal.get("target", 0))
    remaining = max(0, target - saved)
    pct = (saved / target * 100) if target else 0
    lines = [
        "🎯 <b>%s</b>\n" % goal["name"],
        "%s %.0f%%" % (progress_bar(pct), pct),
        "Saved: %s" % fmt_money(saved, cur),
        "Target: %s" % fmt_money(target, cur),
        "Remaining: <b>%s</b>" % fmt_money(remaining, cur),
    ]
    if goal.get("deadline"):
        lines.append("Deadline: %s" % fmt_date(goal["deadline"], tz))
    common.safe_edit(call, "\n".join(lines),
                     reply_markup=keyboards.savings_actions_kb(goal["_id"]))

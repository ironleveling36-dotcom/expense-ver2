"""Advanced contact (friends) management."""
import math

from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import fmt_money, fmt_date, truncate

PAGE = 8
FLOW = "friend"


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "fr:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "👥 <b>Friends & Contacts</b>",
                         reply_markup=keyboards.friends_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "fr:add")
    def _add(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="name")
        common.safe_edit(call, "👤 <b>Add Friend</b>\n\nEnter the name:",
                         reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:list:"))
    def _list(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _render(call, call.from_user.id, int(call.data.split(":")[2]))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:view:"))
    def _view(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        _profile(call, call.from_user.id, call.data.split(":", 2)[2])

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:del:"))
    def _del(call):
        if common.ensure_access(call) is None:
            return
        models.delete_friend(call.from_user.id, call.data.split(":", 2)[2])
        common.answer(call, "Deleted")
        _render(call, call.from_user.id, 0)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:hist:"))
    def _hist(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        friend = models.get_friend(uid, call.data.split(":", 2)[2])
        if not friend:
            return common.safe_edit(call, "Not found.",
                                    reply_markup=keyboards.back_home("fr:list:0"))
        cur = common.user_currency(uid)
        tz = common.user_timezone(uid)
        name = friend["name"]
        borrows = models.list_borrow(uid, {"name": name})
        lends = models.list_lending(uid, {"name": name})
        lines = ["📜 <b>History — %s</b>\n" % name]
        if borrows:
            lines.append("<b>Borrowed:</b>")
            for b in borrows[:10]:
                lines.append("• %s on %s" % (fmt_money(b["amount"], cur),
                                             fmt_date(b.get("date"), tz)))
        if lends:
            lines.append("\n<b>Lent:</b>")
            for l in lends[:10]:
                lines.append("• %s on %s" % (fmt_money(l["amount"], cur),
                                             fmt_date(l.get("date"), tz)))
        if not borrows and not lends:
            lines.append("No transactions yet.")
        common.safe_edit(call, "\n".join(lines),
                         reply_markup=keyboards.back_home(
                             "fr:view:%s" % str(friend["_id"])))

    # Launch borrow/lend prefilled with friend name
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:borrow:"))
    def _fborrow(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        friend = models.get_friend(uid, call.data.split(":", 2)[2])
        if not friend:
            return common.answer(call, "Not found")
        states.start(uid, "borrow", step="amount", data={"name": friend["name"]})
        common.safe_edit(call, "🤝 Borrow from <b>%s</b>\n\nEnter the amount:" %
                         friend["name"], reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:lend:"))
    def _flend(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        friend = models.get_friend(uid, call.data.split(":", 2)[2])
        if not friend:
            return common.answer(call, "Not found")
        states.start(uid, "lending", step="amount",
                     data={"name": friend["name"], "phone": friend.get("phone", "")})
        common.safe_edit(call, "💵 Lend to <b>%s</b>\n\nEnter the amount:" %
                         friend["name"], reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:remind:"))
    def _fremind(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        friend = models.get_friend(uid, call.data.split(":", 2)[2])
        if not friend:
            return common.answer(call, "Not found")
        states.start(uid, "reminder", step="text",
                     data={"text": "Follow up with %s" % friend["name"]})
        states.set_step(uid, "datetime")
        common.safe_edit(
            call, "🔔 Reminder for <b>%s</b>\n\nWhen? (e.g. 25-12-2026):" %
            friend["name"], reply_markup=keyboards.cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:edit:"))
    def _fedit(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        friend = models.get_friend(uid, call.data.split(":", 2)[2])
        if not friend:
            return common.answer(call, "Not found")
        states.start(uid, "friend_edit", step="notes",
                     data={"item_id": str(friend["_id"])})
        common.safe_edit(call, "✏️ Enter new notes for <b>%s</b>:" % friend["name"],
                         reply_markup=keyboards.cancel_kb())

    # ---- flows ----------------------------------------------------------- #
    def _flow(message, user, flow):
        uid = message.from_user.id
        step = flow.step
        if step == "name":
            name = (message.text or "").strip()[:50]
            if not name:
                return common.send(message.chat.id, "Enter a valid name:",
                                   reply_markup=keyboards.cancel_kb())
            states.update_data(uid, name=name)
            states.set_step(uid, "phone")
            common.send(message.chat.id, "📞 Phone (or skip):",
                        reply_markup=keyboards.skip_kb("fr:skip:phone"))
        elif step == "phone":
            states.update_data(uid, phone=(message.text or "").strip()[:20])
            states.set_step(uid, "upi")
            common.send(message.chat.id, "📱 UPI ID (or skip):",
                        reply_markup=keyboards.skip_kb("fr:skip:upi"))
        elif step == "upi":
            states.update_data(uid, upi=(message.text or "").strip()[:40])
            states.set_step(uid, "notes")
            common.send(message.chat.id, "📝 Notes (or skip):",
                        reply_markup=keyboards.skip_kb("fr:skip:notes"))
        elif step == "notes":
            states.update_data(uid, notes=(message.text or "").strip()[:200])
            _save(message.chat.id, uid, flow.data)
            states.clear(uid)

    def _edit_flow(message, user, flow):
        uid = message.from_user.id
        notes = (message.text or "").strip()[:200]
        models.update_friend(uid, flow.data["item_id"], {"notes": notes})
        states.clear(uid)
        common.send(message.chat.id, "✅ Friend updated.",
                    reply_markup=keyboards.friends_menu())

    register_flow(FLOW, _flow)
    register_flow("friend_edit", _edit_flow)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fr:skip:"))
    def _skip(call):
        if common.ensure_access(call) is None:
            return
        flow = states.get(call.from_user.id)
        if not flow or flow.name != FLOW:
            return common.answer(call, "Session expired.")
        common.answer(call)
        uid = call.from_user.id
        what = call.data.split(":", 2)[2]
        if what == "phone":
            states.update_data(uid, phone="")
            states.set_step(uid, "upi")
            common.safe_edit(call, "📱 UPI ID (or skip):",
                             reply_markup=keyboards.skip_kb("fr:skip:upi"))
        elif what == "upi":
            states.update_data(uid, upi="")
            states.set_step(uid, "notes")
            common.safe_edit(call, "📝 Notes (or skip):",
                             reply_markup=keyboards.skip_kb("fr:skip:notes"))
        elif what == "notes":
            states.update_data(uid, notes="")
            _save(call.message.chat.id, uid, flow.data)
            states.clear(uid)


def _save(chat_id, uid, data):
    friend = models.add_friend(uid, data["name"], phone=data.get("phone", ""),
                               upi=data.get("upi", ""), notes=data.get("notes", ""))
    common.send(chat_id, "✅ Friend <b>%s</b> saved." % friend["name"],
                reply_markup=keyboards.friends_menu())


def _render(call, uid, page):
    friends = models.list_friends(uid)
    total_pages = max(1, math.ceil(len(friends) / PAGE))
    page = max(0, min(page, total_pages - 1))
    subset = friends[page * PAGE:(page + 1) * PAGE]
    if not subset:
        return common.safe_edit(call, "No friends added yet.",
                                reply_markup=keyboards.friends_menu())

    def label(it):
        return truncate(it["name"], 22)

    kb = keyboards.paginated_list(subset, label, "fr:view", page, total_pages,
                                  "fr:list", back_data="fr:menu")
    common.safe_edit(call, "👥 <b>Friends</b> (page %d/%d)" % (page + 1, total_pages),
                     reply_markup=kb)


def _profile(call, uid, item_id):
    friend = models.get_friend(uid, item_id)
    if not friend:
        return common.safe_edit(call, "Not found.",
                                reply_markup=keyboards.back_home("fr:list:0"))
    cur = common.user_currency(uid)
    tz = common.user_timezone(uid)
    borrowed, lent = models.friend_balance(uid, friend["name"])
    balance = lent - borrowed
    lines = [
        "👤 <b>%s</b>" % friend["name"],
    ]
    if friend.get("nickname"):
        lines.append("Nickname: %s" % friend["nickname"])
    if friend.get("phone"):
        lines.append("📞 %s" % friend["phone"])
    if friend.get("upi"):
        lines.append("📱 %s" % friend["upi"])
    if friend.get("notes"):
        lines.append("📝 %s" % friend["notes"])
    lines.append("")
    lines.append("Total Borrowed: %s" % fmt_money(borrowed, cur))
    lines.append("Total Lent: %s" % fmt_money(lent, cur))
    lines.append("Net Balance: <b>%s</b>" % fmt_money(balance, cur))
    lines.append("Added: %s" % fmt_date(friend.get("created_at"), tz))
    common.safe_edit(call, "\n".join(lines),
                     reply_markup=keyboards.friend_profile_kb(friend["_id"]))

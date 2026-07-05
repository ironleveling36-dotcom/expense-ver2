"""User settings & profile handlers."""
from keyboards import keyboards
from handlers import common
from handlers.router import register_flow
from database import models
from utils.states import states
from utils.helpers import fmt_date

FLOW = "settings"

CURRENCIES = ["₹", "$", "€", "£", "¥", "₨"]
REPORT_SCHEDULES = ["daily", "weekly", "monthly", "off"]


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "set:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        settings = models.get_user_settings(call.from_user.id)
        common.safe_edit(call, "⚙️ <b>Settings</b>",
                         reply_markup=keyboards.settings_menu(settings))

    @bot.callback_query_handler(func=lambda c: c.data == "set:currency")
    def _currency(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        kb = keyboards.types.InlineKeyboardMarkup()
        row = [keyboards.types.InlineKeyboardButton(c, callback_data="set:cur:%s" % c)
               for c in CURRENCIES]
        kb.row(*row)
        kb.row(keyboards.types.InlineKeyboardButton("⬅️ Back", callback_data="set:menu"))
        common.safe_edit(call, "💱 Choose your currency:", reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("set:cur:"))
    def _setcur(call):
        if common.ensure_access(call) is None:
            return
        cur = call.data.split(":", 2)[2]
        models.update_user_setting(call.from_user.id, "currency", cur)
        common.answer(call, "Currency updated")
        settings = models.get_user_settings(call.from_user.id)
        common.safe_edit(call, "⚙️ <b>Settings</b>",
                         reply_markup=keyboards.settings_menu(settings))

    @bot.callback_query_handler(func=lambda c: c.data == "set:notif")
    def _notif(call):
        if common.ensure_access(call) is None:
            return
        settings = models.get_user_settings(call.from_user.id)
        new_val = not settings.get("notifications", True)
        models.update_user_setting(call.from_user.id, "notifications", new_val)
        common.answer(call, "Notifications " + ("on" if new_val else "off"))
        settings = models.get_user_settings(call.from_user.id)
        common.safe_edit(call, "⚙️ <b>Settings</b>",
                         reply_markup=keyboards.settings_menu(settings))

    @bot.callback_query_handler(func=lambda c: c.data == "set:report")
    def _report(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        kb = keyboards.types.InlineKeyboardMarkup()
        for s in REPORT_SCHEDULES:
            kb.row(keyboards.types.InlineKeyboardButton(
                s.capitalize(), callback_data="set:rep:%s" % s))
        kb.row(keyboards.types.InlineKeyboardButton("⬅️ Back", callback_data="set:menu"))
        common.safe_edit(call, "🗓 Choose report schedule:", reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("set:rep:"))
    def _setrep(call):
        if common.ensure_access(call) is None:
            return
        val = call.data.split(":", 2)[2]
        models.update_user_setting(call.from_user.id, "report_schedule", val)
        common.answer(call, "Report schedule updated")
        settings = models.get_user_settings(call.from_user.id)
        common.safe_edit(call, "⚙️ <b>Settings</b>",
                         reply_markup=keyboards.settings_menu(settings))

    @bot.callback_query_handler(func=lambda c: c.data == "set:timezone")
    def _timezone(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        states.start(call.from_user.id, FLOW, step="timezone")
        common.safe_edit(call, "🌐 Enter your timezone (e.g. <code>Asia/Kolkata</code>):",
                         reply_markup=keyboards.cancel_kb())

    def _flow(message, user, flow):
        uid = message.from_user.id
        if flow.step == "timezone":
            tz = (message.text or "").strip()[:40]
            models.update_user_setting(uid, "timezone", tz)
            states.clear(uid)
            common.send(message.chat.id, "✅ Timezone set to %s" % tz,
                        reply_markup=keyboards.main_menu(common.is_admin_uid(uid)))

    register_flow(FLOW, _flow)

    # ---- Profile --------------------------------------------------------- #
    @bot.callback_query_handler(func=lambda c: c.data == "prof:show")
    def _profile(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        user = models.get_user(uid)
        settings = user.get("settings", {}) if user else {}
        tz = settings.get("timezone", "Asia/Kolkata")
        exp_count = models.count_expenses(uid)
        friends = len(models.list_friends(uid))
        role = user.get("role", "user") if user else "user"
        if common.is_admin_uid(uid) and role == "user":
            role = "admin"
        text = (
            "👤 <b>Your Profile</b>\n\n"
            "Name: %s\n"
            "User ID: <code>%s</code>\n"
            "Role: %s\n"
            "Currency: %s\n"
            "Timezone: %s\n"
            "Member since: %s\n\n"
            "📊 Expenses logged: %d\n"
            "👥 Friends: %d"
        ) % (
            (user.get("first_name") if user else "-") or "-", uid, role,
            settings.get("currency", "₹"), tz,
            fmt_date(user.get("created_at"), tz) if user else "-",
            exp_count, friends,
        )
        common.safe_edit(call, text, reply_markup=keyboards.back_home())

"""
All inline keyboards for the bot.

Callback-data convention:  "<module>:<action>:<arg>"
Args are optional. Keep callback data under Telegram's 64-byte limit.
"""
from telebot import types


def _btn(text, data):
    return types.InlineKeyboardButton(text, callback_data=data)


def _rows(markup, buttons, per_row=2):
    row = []
    for b in buttons:
        row.append(b)
        if len(row) == per_row:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)


# --------------------------------------------------------------------------- #
# Main menu
# --------------------------------------------------------------------------- #
def main_menu(is_admin=False):
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ Add Expense", "exp:add"), _btn("➕ Add Income", "inc:add"))
    kb.row(_btn("🤝 Borrow", "bor:menu"), _btn("💵 Lending", "lend:menu"))
    kb.row(_btn("👥 Friends", "fr:menu"), _btn("💳 Ledger", "led:menu"))
    kb.row(_btn("📊 Reports", "rep:menu"), _btn("📅 Bills", "bill:menu"))
    kb.row(_btn("🎯 Savings", "sav:menu"), _btn("🔔 Reminders", "rem:menu"))
    kb.row(_btn("📈 Dashboard", "dash:show"), _btn("💹 Budget", "bud:menu"))
    kb.row(_btn("⚙️ Settings", "set:menu"), _btn("📤 Export", "out:menu"))
    kb.row(_btn("👤 Profile", "prof:show"))
    if is_admin:
        kb.row(_btn("🛠 Admin", "adm:menu"))
    return kb


def home_row():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def back_home(back_data="menu:main"):
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("⬅️ Back", back_data), _btn("🏠 Home", "menu:main"))
    return kb


def cancel_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("❌ Cancel", "menu:main"))
    return kb


def confirm_kb(yes_data, no_data="menu:main"):
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("✅ Confirm", yes_data), _btn("❌ Cancel", no_data))
    return kb


# --------------------------------------------------------------------------- #
# Expense keyboards
# --------------------------------------------------------------------------- #
def category_kb(categories, prefix="exp:cat"):
    kb = types.InlineKeyboardMarkup()
    buttons = [_btn(c, "%s:%s" % (prefix, c)) for c in categories]
    _rows(kb, buttons, per_row=3)
    kb.row(_btn("➕ Custom", "%s:__custom__" % prefix))
    kb.row(_btn("❌ Cancel", "menu:main"))
    return kb


def payment_mode_kb(prefix="exp:pm"):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        _btn("💵 Cash", "%s:Cash" % prefix),
        _btn("💳 Card", "%s:Card" % prefix),
        _btn("📱 UPI", "%s:UPI" % prefix),
    )
    kb.row(_btn("❌ Cancel", "menu:main"))
    return kb


def skip_kb(skip_data):
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("⏭ Skip", skip_data), _btn("❌ Cancel", "menu:main"))
    return kb


def income_source_kb(sources, prefix="inc:src"):
    kb = types.InlineKeyboardMarkup()
    buttons = [_btn(s, "%s:%s" % (prefix, s)) for s in sources]
    _rows(kb, buttons, per_row=3)
    kb.row(_btn("➕ Custom", "%s:__custom__" % prefix))
    kb.row(_btn("❌ Cancel", "menu:main"))
    return kb


# --------------------------------------------------------------------------- #
# Generic list / pagination
# --------------------------------------------------------------------------- #
def paginated_list(items, label_fn, item_prefix, page, total_pages,
                   page_prefix, back_data="menu:main", per_row=1):
    kb = types.InlineKeyboardMarkup()
    buttons = []
    for item in items:
        label = label_fn(item)
        buttons.append(_btn(label, "%s:%s" % (item_prefix, str(item["_id"]))))
    _rows(kb, buttons, per_row=per_row)
    nav = []
    if page > 0:
        nav.append(_btn("⬅️ Prev", "%s:%d" % (page_prefix, page - 1)))
    if page < total_pages - 1:
        nav.append(_btn("➡️ Next", "%s:%d" % (page_prefix, page + 1)))
    if nav:
        kb.row(*nav)
    kb.row(_btn("⬅️ Back", back_data), _btn("🏠 Home", "menu:main"))
    return kb


# --------------------------------------------------------------------------- #
# Sub-menus
# --------------------------------------------------------------------------- #
def borrow_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ New Borrow", "bor:add"), _btn("📋 List", "bor:list:0"))
    kb.row(_btn("⚠️ Overdue", "bor:overdue"), _btn("📊 Summary", "bor:summary"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def lending_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ New Lending", "lend:add"), _btn("📋 List", "lend:list:0"))
    kb.row(_btn("⚠️ Overdue", "lend:overdue"), _btn("📊 Summary", "lend:summary"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def friends_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ Add Friend", "fr:add"), _btn("📋 List", "fr:list:0"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def friend_profile_kb(friend_id):
    kb = types.InlineKeyboardMarkup()
    fid = str(friend_id)
    kb.row(_btn("🤝 Borrow", "fr:borrow:%s" % fid),
           _btn("💵 Lend", "fr:lend:%s" % fid))
    kb.row(_btn("📜 History", "fr:hist:%s" % fid),
           _btn("🔔 Reminder", "fr:remind:%s" % fid))
    kb.row(_btn("✏️ Edit", "fr:edit:%s" % fid),
           _btn("🗑 Delete", "fr:del:%s" % fid))
    kb.row(_btn("⬅️ Back", "fr:list:0"), _btn("🏠 Home", "menu:main"))
    return kb


def ledger_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ Credit", "led:add:credit"), _btn("➖ Debit", "led:add:debit"))
    kb.row(_btn("📋 Statement", "led:list:0"), _btn("💰 Balance", "led:balance"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def reports_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("📅 Daily", "rep:period:day"), _btn("📆 Weekly", "rep:period:week"))
    kb.row(_btn("🗓 Monthly", "rep:period:month"), _btn("📈 Yearly", "rep:period:year"))
    kb.row(_btn("🏷 Category", "rep:category"), _btn("💳 Payment Mode", "rep:pmode"))
    kb.row(_btn("💹 Profit/Loss", "rep:pnl"), _btn("💰 Savings", "rep:savings"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def bills_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ Add Bill", "bill:add"), _btn("📋 All Bills", "bill:list:0"))
    kb.row(_btn("🔴 Unpaid", "bill:unpaid"), _btn("✅ Paid", "bill:paid"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def bill_actions_kb(bill_id, paid=False):
    kb = types.InlineKeyboardMarkup()
    bid = str(bill_id)
    if not paid:
        kb.row(_btn("✅ Mark Paid", "bill:markpaid:%s" % bid))
    kb.row(_btn("🗑 Delete", "bill:del:%s" % bid))
    kb.row(_btn("⬅️ Back", "bill:list:0"), _btn("🏠 Home", "menu:main"))
    return kb


def savings_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ New Goal", "sav:add"), _btn("📋 My Goals", "sav:list:0"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def savings_actions_kb(goal_id):
    kb = types.InlineKeyboardMarkup()
    gid = str(goal_id)
    kb.row(_btn("💰 Add Money", "sav:contrib:%s" % gid),
           _btn("🗑 Delete", "sav:del:%s" % gid))
    kb.row(_btn("⬅️ Back", "sav:list:0"), _btn("🏠 Home", "menu:main"))
    return kb


def reminders_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("➕ New Reminder", "rem:add"), _btn("📋 My Reminders", "rem:list:0"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def reminder_repeat_kb(prefix="rem:rep"):
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("Once", "%s:once" % prefix), _btn("Daily", "%s:daily" % prefix))
    kb.row(_btn("Weekly", "%s:weekly" % prefix),
           _btn("Monthly", "%s:monthly" % prefix))
    kb.row(_btn("❌ Cancel", "menu:main"))
    return kb


def budget_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("📅 Daily Limit", "bud:set:day"),
           _btn("📆 Weekly Limit", "bud:set:week"))
    kb.row(_btn("🗓 Monthly Limit", "bud:set:month"),
           _btn("🏷 Category Limit", "bud:setcat"))
    kb.row(_btn("📊 View Budgets", "bud:view"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def settings_menu(settings):
    kb = types.InlineKeyboardMarkup()
    notif = "🔔 On" if settings.get("notifications", True) else "🔕 Off"
    kb.row(_btn("💱 Currency: %s" % settings.get("currency", "₹"), "set:currency"))
    kb.row(_btn("🌐 Timezone: %s" % settings.get("timezone", "Asia/Kolkata"),
               "set:timezone"))
    kb.row(_btn("Notifications: %s" % notif, "set:notif"))
    kb.row(_btn("🗓 Report: %s" % settings.get("report_schedule", "monthly"),
               "set:report"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def export_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("📄 CSV", "out:fmt:csv"), _btn("📊 Excel", "out:fmt:xlsx"))
    kb.row(_btn("🧾 PDF", "out:fmt:pdf"), _btn("🗂 JSON (Backup)", "out:fmt:json"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def admin_menu():
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("👥 Users", "adm:users:0"), _btn("📊 Statistics", "adm:stats"))
    kb.row(_btn("📢 Broadcast", "adm:broadcast"), _btn("🩺 Health", "adm:health"))
    kb.row(_btn("📜 Audit Logs", "adm:logs"), _btn("💾 Storage", "adm:storage"))
    kb.row(_btn("🔧 Maintenance", "adm:maint"))
    kb.row(_btn("🏠 Home", "menu:main"))
    return kb


def admin_user_kb(target_id, blocked=False):
    kb = types.InlineKeyboardMarkup()
    tid = str(target_id)
    if blocked:
        kb.row(_btn("✅ Unblock", "adm:unblock:%s" % tid))
    else:
        kb.row(_btn("🚫 Block", "adm:block:%s" % tid))
    kb.row(_btn("⬅️ Back", "adm:users:0"), _btn("🏠 Home", "menu:main"))
    return kb


def entity_actions_kb(prefix, item_id, back_data):
    """Generic Delete + Back keyboard for an entity view."""
    kb = types.InlineKeyboardMarkup()
    kb.row(_btn("🗑 Delete", "%s:del:%s" % (prefix, str(item_id))))
    kb.row(_btn("⬅️ Back", back_data), _btn("🏠 Home", "menu:main"))
    return kb


def repay_kb(prefix, item_id, back_data):
    kb = types.InlineKeyboardMarkup()
    iid = str(item_id)
    kb.row(_btn("💰 Add Payment", "%s:pay:%s" % (prefix, iid)))
    kb.row(_btn("🗑 Delete", "%s:del:%s" % (prefix, iid)))
    kb.row(_btn("⬅️ Back", back_data), _btn("🏠 Home", "menu:main"))
    return kb

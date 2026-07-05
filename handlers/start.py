"""Start / help / main-menu handlers."""
from keyboards import keyboards
from handlers import common
from utils.states import states

WELCOME = (
    "👋 <b>Welcome to Expense Tracker Bot</b>\n\n"
    "Track expenses, income, borrowing, lending, bills, savings and more — "
    "all in Indian Rupees (₹).\n\n"
    "Use the menu below to get started 👇"
)

HELP = (
    "<b>📖 Help</b>\n\n"
    "This bot is fully button-driven. Tap a menu option and follow the prompts.\n\n"
    "<b>Commands</b>\n"
    "/start - Show the main menu\n"
    "/menu - Show the main menu\n"
    "/help - Show this help\n"
    "/cancel - Cancel the current action\n\n"
    "<b>Tips</b>\n"
    "• Amounts can be typed as <code>250</code> or <code>1,250.50</code>\n"
    "• Dates accept <code>today</code>, <code>25-12-2026</code>, etc.\n"
    "• Use 🏠 Home anytime to return to the menu."
)


def register(bot):
    @bot.message_handler(commands=["start"])
    def _start(message):
        user = common.ensure_access(message)
        if user is None:
            return
        states.clear(message.from_user.id)
        common.send(
            message.chat.id, WELCOME,
            reply_markup=keyboards.main_menu(common.is_admin(message)),
        )

    @bot.message_handler(commands=["menu"])
    def _menu(message):
        user = common.ensure_access(message)
        if user is None:
            return
        states.clear(message.from_user.id)
        common.send(
            message.chat.id, "🏠 <b>Main Menu</b>",
            reply_markup=keyboards.main_menu(common.is_admin(message)),
        )

    @bot.message_handler(commands=["help"])
    def _help(message):
        if common.ensure_access(message) is None:
            return
        common.send(message.chat.id, HELP, reply_markup=keyboards.home_row())

    @bot.message_handler(commands=["cancel"])
    def _cancel(message):
        if common.ensure_access(message) is None:
            return
        states.clear(message.from_user.id)
        common.send(
            message.chat.id, "✅ Cancelled.",
            reply_markup=keyboards.main_menu(common.is_admin(message)),
        )

    @bot.callback_query_handler(func=lambda c: c.data == "menu:main")
    def _home(call):
        user = common.ensure_access(call)
        if user is None:
            return
        states.clear(call.from_user.id)
        common.answer(call)
        common.safe_edit(
            call, "🏠 <b>Main Menu</b>",
            reply_markup=keyboards.main_menu(common.is_admin(call)),
        )

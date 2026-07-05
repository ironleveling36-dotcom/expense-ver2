"""
Fallback handler for any callback that no other module handled.

Registered LAST so specific handlers take precedence. It simply acknowledges
the callback so the Telegram spinner stops and returns the user to the menu.
"""
from keyboards import keyboards
from handlers import common


def register(bot):
    @bot.callback_query_handler(func=lambda c: True)
    def _fallback(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call, "This option is unavailable.")
        common.safe_edit(
            call, "🏠 <b>Main Menu</b>",
            reply_markup=keyboards.main_menu(common.is_admin(call)),
        )

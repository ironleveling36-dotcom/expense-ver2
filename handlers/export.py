"""Export handlers — deliver data files to the user."""
import os

from keyboards import keyboards
from handlers import common
from services import export_service
from utils.logger import get_logger

log = get_logger("export")


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "out:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "📤 <b>Export Data</b>\nChoose a format:",
                         reply_markup=keyboards.export_menu())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("out:fmt:"))
    def _export(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call, "Generating...")
        uid = call.from_user.id
        fmt = call.data.split(":", 2)[2]
        cur = common.user_currency(uid)
        path = None
        try:
            path = export_service.generate(uid, fmt, cur)
            with open(path, "rb") as fh:
                bot.send_document(call.message.chat.id, fh,
                                  caption="📤 Your %s export" % fmt.upper())
        except Exception as exc:  # pragma: no cover
            log.exception("export failed: %s", exc)
            common.send(call.message.chat.id,
                        "⚠️ Export failed: %s" % str(exc)[:100])
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        common.send(call.message.chat.id, "Done ✅",
                    reply_markup=keyboards.main_menu(common.is_admin_uid(uid)))

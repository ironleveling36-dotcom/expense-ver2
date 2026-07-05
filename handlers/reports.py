"""Reports handlers."""
from keyboards import keyboards
from handlers import common
from services import report_service


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "rep:menu")
    def _menu(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        common.safe_edit(call, "📊 <b>Reports</b>\nChoose a report:",
                         reply_markup=keyboards.reports_menu())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("rep:period:"))
    def _period(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        period = call.data.split(":", 2)[2]
        text = report_service.format_summary(
            uid, period, common.user_currency(uid), common.user_timezone(uid))
        common.safe_edit(call, text, reply_markup=keyboards.back_home("rep:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "rep:category")
    def _cat(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        text = report_service.category_report(
            uid, common.user_currency(uid), common.user_timezone(uid))
        common.safe_edit(call, text, reply_markup=keyboards.back_home("rep:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "rep:pmode")
    def _pmode(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        text = report_service.payment_mode_report(
            uid, common.user_currency(uid), common.user_timezone(uid))
        common.safe_edit(call, text, reply_markup=keyboards.back_home("rep:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "rep:pnl")
    def _pnl(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        text = report_service.profit_loss(
            uid, common.user_currency(uid), common.user_timezone(uid))
        common.safe_edit(call, text, reply_markup=keyboards.back_home("rep:menu"))

    @bot.callback_query_handler(func=lambda c: c.data == "rep:savings")
    def _savings(call):
        if common.ensure_access(call) is None:
            return
        common.answer(call)
        uid = call.from_user.id
        text = report_service.savings_report(uid, common.user_currency(uid))
        common.safe_edit(call, text, reply_markup=keyboards.back_home("rep:menu"))

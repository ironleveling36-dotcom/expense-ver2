"""
Telegram Expense Tracker Bot — application entry point.

Boots configuration, database, handlers and the reminder scheduler, then
runs long-polling with automatic recovery so the bot survives Railway
restarts and transient network errors.
"""
import time

import telebot

from config import config
from database.db import database
from handlers import common
from handlers import (start, expense, income, borrow_lending, friends, ledger,
                      reports, bills, savings, reminders, dashboard, budget,
                      settings as settings_handler, export, admin, router,
                      fallback)
from services import reminder_service
from utils.logger import get_logger

log = get_logger("bot")


def build_bot():
    bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML", threaded=True)
    common.set_bot(bot)

    # Order matters: command + specific callback handlers first, then the
    # generic text router, and finally the catch-all callback fallback.
    start.register(bot)
    expense.register(bot)
    income.register(bot)
    borrow_lending.register(bot)
    friends.register(bot)
    ledger.register(bot)
    reports.register(bot)
    bills.register(bot)
    savings.register(bot)
    reminders.register(bot)
    dashboard.register(bot)
    budget.register(bot)
    settings_handler.register(bot)
    export.register(bot)
    admin.register(bot)
    router.register(bot)
    fallback.register(bot)
    return bot


def main():
    log.info("Starting Expense Tracker Bot...")
    config.validate()
    database.connect()

    bot = build_bot()
    reminder_service.start()

    try:
        bot.remove_webhook()
    except Exception as exc:  # pragma: no cover
        log.warning("remove_webhook failed: %s", exc)

    log.info("Bot is running. Listening for updates...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30,
                                 skip_pending=True)
        except Exception as exc:  # pragma: no cover
            log.error("Polling crashed: %s — restarting in 5s", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()

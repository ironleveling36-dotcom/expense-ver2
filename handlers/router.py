"""
Central text-flow router.

Callback queries are handled per-module (each module registers its own
callback_query_handler with a prefix filter). Free-text input for multi-step
forms is centralised here: modules register a flow processor keyed by flow
name, and the single message handler dispatches to the right processor based
on the user's active state.
"""
from handlers import common
from utils.states import states
from utils.logger import get_logger

log = get_logger("router")

FLOW_HANDLERS = {}


def register_flow(name, func):
    """Register a processor: func(message, user, flow) for a named flow."""
    FLOW_HANDLERS[name] = func


def register(bot):
    @bot.message_handler(
        content_types=["text", "photo", "document"],
        func=lambda m: not (m.text or "").startswith("/"),
    )
    def _dispatch_text(message):
        user = common.ensure_access(message)
        if user is None:
            return
        flow = states.get(message.from_user.id)
        if flow is None:
            # No active flow: nudge the user back to the menu.
            from keyboards import keyboards
            common.send(
                message.chat.id,
                "Use the menu below 👇",
                reply_markup=keyboards.main_menu(common.is_admin(message)),
            )
            return
        handler = FLOW_HANDLERS.get(flow.name)
        if handler is None:
            states.clear(message.from_user.id)
            common.send(message.chat.id, "Something went wrong. Returning to menu.")
            return
        try:
            handler(message, user, flow)
        except Exception as exc:  # pragma: no cover
            log.exception("Flow '%s' failed: %s", flow.name, exc)
            states.clear(message.from_user.id)
            common.send(
                message.chat.id,
                "⚠️ An error occurred. Please try again from the menu.",
            )

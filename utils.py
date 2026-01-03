import logging
import secrets
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    escape_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def get_user_display_name(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> str:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.user.username:
            return f"@{member.user.username}"
        return member.user.first_name or f"User {user_id}"
    except Exception:
        return f"User {user_id}"

async def delete_user_message(update: Update):
    if update.message:
        try:
            await update.message.delete()
            logger.info("✅ Successfully deleted user message")
        except Exception as e:
            logger.info(f"ℹ️ Could not delete user message (likely no admin permissions): {e}")

def generate_webhook_secret() -> str:
    return secrets.token_urlsafe(32)

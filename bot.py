#!/usr/bin/env python3
"""
Telegram Task List Bot
A simple bot that manages a shared task list for groups.
"""

import os
import logging
import re
import secrets
import asyncio
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from database import init_connection_pool, get_db_cursor, close_connection_pool

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TaskListBot:
    def __init__(self):
        logger.info("🤖 Initializing TaskListBot...")
        init_connection_pool()
        logger.info("🚀 TaskListBot initialization complete")
    
    def describe_context(self, chat_id: int, thread_id: Optional[int]) -> str:
        """Return a human-readable description of the current chat/thread context"""
        if thread_id is None:
            return f"chat {chat_id}"
        return f"chat {chat_id}, thread {thread_id}"
    
    def sanitize_task_title(self, title: str) -> str:
        """Sanitize and validate task title input"""
        if not title or not isinstance(title, str):
            raise ValueError("Task title must be a non-empty string")
        
        title = title.strip()
        
        if len(title) > 1000:
            raise ValueError("Task title too long (max 1000 characters)")
        
        if len(title) < 1:
            raise ValueError("Task title cannot be empty")
        
        title = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', title)
        title = re.sub(r'\s{3,}', ' ', title)
        
        return title
    
    def validate_callback_data(self, data: str) -> bool:
        """Validate callback data format"""
        if not data or not isinstance(data, str):
            return False
        
        pattern = r'^(remove|view)_-?\d+_(?:\d+_)?\d+$'
        return bool(re.match(pattern, data))
    
    
    def get_tasks_with_context(
        self,
        chat_id: int,
        thread_id: Optional[int] = None
    ) -> tuple[List[Dict], Optional[int]]:
        """Retrieve tasks from database for a specific chat and optional thread"""
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT id, title, details, assignee_id FROM tasks WHERE chat_id = %s AND thread_id IS NULL ORDER BY id",
                        (chat_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT id, title, details, assignee_id FROM tasks WHERE chat_id = %s AND thread_id = %s ORDER BY id",
                        (chat_id, thread_id)
                    )
                
                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    task = {
                        "id": row["id"],
                        "title": row["title"],
                        "details": row["details"],
                        "assignee_id": row["assignee_id"]
                    }
                    tasks.append(task)
                
                return tasks, thread_id
        except Exception as e:
            logger.error(f"❌ Error loading tasks from database: {e}")
            return [], thread_id
    
    def get_chat_tasks(self, chat_id: int, thread_id: Optional[int] = None) -> List[Dict]:
        """Get tasks for a specific chat and optional thread"""
        tasks, _ = self.get_tasks_with_context(chat_id, thread_id)
        return tasks
    
    def add_task(self, chat_id: int, task_title: str, thread_id: Optional[int] = None) -> int:
        """Add a new task to the database"""
        try:
            sanitized_title = self.sanitize_task_title(task_title)
        except ValueError as e:
            logger.warning(f"❌ Invalid task title from chat {chat_id}: {str(e)}")
            raise
        
        context_desc = self.describe_context(chat_id, thread_id)
        logger.info(f"➕ Adding new task to {context_desc}")
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tasks (chat_id, thread_id, title) VALUES (%s, %s, %s) RETURNING id",
                    (chat_id, thread_id, sanitized_title)
                )
                task_id = cursor.fetchone()["id"]
            
            logger.info(f"✅ Task #{task_id} successfully added to {context_desc}")
            return task_id
        except Exception as e:
            logger.error(f"❌ Error adding task to database: {e}")
            raise
    
    def remove_task(self, chat_id: int, task_id: int, thread_id: Optional[int] = None) -> tuple[bool, str]:
        """Remove a task by ID and return (success, task_title)"""
        context_desc = self.describe_context(chat_id, thread_id)
        logger.info(f"🗑️ Attempting to remove task #{task_id} from {context_desc}")
        
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT title FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "SELECT title FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"⚠️ Task #{task_id} not found in {context_desc}")
                    return False, ""
                
                task_title = row["title"]
                logger.info(f"📝 Found task #{task_id} to remove: '{task_title}'")
                
                if thread_id is None:
                    cursor.execute(
                        "DELETE FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "DELETE FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
            
            logger.info(f"✅ Task #{task_id} successfully removed from {context_desc}")
            return True, task_title
        except Exception as e:
            logger.error(f"❌ Error removing task from database: {e}")
            return False, ""
    
    def get_task_details(self, chat_id: int, task_id: int, thread_id: Optional[int] = None) -> Optional[str]:
        """Get task details/description from database"""
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT details FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "SELECT details FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
                
                row = cursor.fetchone()
                return row["details"] if row else None
        except Exception as e:
            logger.error(f"❌ Error getting task details from database: {e}")
            return None
    
    def set_task_details(self, chat_id: int, task_id: int, details: str, thread_id: Optional[int] = None) -> bool:
        """Update task details/description in database"""
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "UPDATE tasks SET details = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (details, chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE tasks SET details = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (details, chat_id, thread_id, task_id)
                    )
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error setting task details in database: {e}")
            return False
    
    def get_task_assignee(self, chat_id: int, task_id: int, thread_id: Optional[int] = None) -> Optional[int]:
        """Get task assignee from database"""
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT assignee_id FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "SELECT assignee_id FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
                
                row = cursor.fetchone()
                return row["assignee_id"] if row else None
        except Exception as e:
            logger.error(f"❌ Error getting task assignee from database: {e}")
            return None
    
    def set_task_assignee(self, chat_id: int, task_id: int, assignee_id: Optional[int], thread_id: Optional[int] = None) -> bool:
        """Update task assignee in database"""
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "UPDATE tasks SET assignee_id = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (assignee_id, chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE tasks SET assignee_id = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (assignee_id, chat_id, thread_id, task_id)
                    )
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error setting task assignee in database: {e}")
            return False
    
    def get_user_tasks(self, assignee_id: int) -> List[Dict]:
        """Get all tasks assigned to a specific user"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT chat_id, thread_id, id, title, details FROM tasks WHERE assignee_id = %s ORDER BY chat_id, thread_id, id",
                    (assignee_id,)
                )
                
                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    task = {
                        "chat_id": row["chat_id"],
                        "thread_id": row["thread_id"],
                        "id": row["id"],
                        "title": row["title"],
                        "details": row["details"]
                    }
                    tasks.append(task)
                
                return tasks
        except Exception as e:
            logger.error(f"❌ Error getting user tasks from database: {e}")
            return []
    
    def format_task_list(self, chat_id: int, thread_id: Optional[int] = None) -> str:
        """Format the task list for display"""
        chat_tasks, _ = self.get_tasks_with_context(chat_id, thread_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task."
        
        task_lines = [f"📋 *Current Task List:*\n"]
        for task in chat_tasks:
            escaped_title = self.escape_markdown(task['title'])
            task_lines.append(f"{task['id']}. {escaped_title}")
        
        task_lines.append(f"\n💡 Click on any task button to remove it")
        return "\n".join(task_lines)
    
    def escape_markdown(self, text: str) -> str:
        """Escape Markdown special characters"""
        escape_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    def format_task_list_plain(self, chat_id: int, thread_id: Optional[int] = None) -> str:
        """Format the task list for display without Markdown"""
        chat_tasks, _ = self.get_tasks_with_context(chat_id, thread_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task."
        
        task_lines = [f"📋 Current Task List:\n"]
        for task in chat_tasks:
            task_lines.append(f"{task['id']}. {task['title']}")
        
        task_lines.append(f"\n💡 Click on any task button to remove it")
        return "\n".join(task_lines)
    
    def format_task_list_with_buttons(self, chat_id: int, thread_id: Optional[int] = None) -> tuple[str, Optional[InlineKeyboardMarkup]]:
        """Format the task list as buttons only - no text, just clickable task buttons"""
        chat_tasks, storage_thread_id = self.get_tasks_with_context(chat_id, thread_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task.", None
        
        keyboard_buttons = []
        
        for task in chat_tasks:
            task_title = task['title']
            if len(task_title) > 50:
                task_title = task_title[:47] + "..."
            
            if storage_thread_id is not None:
                callback_data = f"remove_{chat_id}_{storage_thread_id}_{task['id']}"
            else:
                callback_data = f"remove_{chat_id}_{task['id']}"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"{task['id']}. {task_title}", 
                    callback_data=callback_data
                )
            ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
        return f"📋 **Click any task to remove it:**", keyboard

async def delete_user_message(update: Update):
    """Helper function to delete user's message (for cleanup)"""
    if update.message:
        try:
            await update.message.delete()
            logger.info("✅ Successfully deleted user message")
        except Exception as e:
            logger.info(f"ℹ️ Could not delete user message (likely no admin permissions): {e}")
            # Don't re-raise the exception - just log and continue

async def show_text_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /text command - show full task list without truncation"""
    if not update.message:
        logger.warning("Received /text command without message")
        return
    
    try:
        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id
        task_list = task_bot.format_task_list(chat_id, thread_id)
        await update.message.reply_text(task_list, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending text task list: {e}")
        # Fallback: send without Markdown formatting
        try:
            chat_id = update.effective_chat.id
            thread_id = update.message.message_thread_id
            task_list = task_bot.format_task_list_plain(chat_id, thread_id)
            await update.message.reply_text(task_list)
        except Exception as e2:
            logger.error(f"Error sending plain text task list: {e2}")
            await update.message.reply_text("❌ Error displaying task list. Please try again.")
    
    await delete_user_message(update)

task_bot = TaskListBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not update.message:
        logger.warning("Received /start command without message")
        return
    
    await update.message.reply_text(
        "🤖 **Task List Bot**\n\n"
        "This bot helps manage your task list!\n\n"
        "**Commands:**\n"
        "/list - Show current tasks (as clickable buttons)\n"
        "/text - Show current tasks (as text list)\n"
        "/add <task> - Add a new task\n\n"
        "💡 **Tip:** Click on any task button to remove it!"
    )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command"""
    if not update.message:
        logger.warning("Received /list command without message")
        return
    
    try:
        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
        
        if keyboard:
            await update.message.reply_text(task_list, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await update.message.reply_text(task_list, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending task list with buttons: {e}")
        # Fallback: send without Markdown formatting
        try:
            chat_id = update.effective_chat.id
            thread_id = update.message.message_thread_id
            task_list = task_bot.format_task_list_plain(chat_id, thread_id)
            await update.message.reply_text(task_list)
        except Exception as e2:
            logger.error(f"Error sending plain task list: {e2}")
            await update.message.reply_text("❌ Error displaying task list. Please try again.")
    
    await delete_user_message(update)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command"""
    if not update.message:
        logger.warning("Received /add command without message")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task to add!\n"
            "Example: /add Buy groceries"
        )
        # Clean up user's command message
        await delete_user_message(update)
        return
    
    try:
        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id
        task_title = " ".join(context.args)
        task_id = task_bot.add_task(chat_id, task_title, thread_id)
        
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
        if keyboard:
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {task_bot.escape_markdown(task_title)}\n\n{task_list}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            escaped_title = task_bot.escape_markdown(task_title)
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {escaped_title}\n\n"
                f"Use /list to see all tasks.",
                parse_mode='Markdown'
            )
    except ValueError as e:
        logger.warning(f"Invalid task input from chat {update.effective_chat.id}: {str(e)}")
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        await update.message.reply_text("❌ Error adding task. Please try again.")
    
    await delete_user_message(update)



async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    if not update.message:
        logger.warning("Received update without message")
        return
    
    message_text = update.message.text.lower()
    thread_id = update.message.message_thread_id
    
    if message_text.startswith("add "):
        task_title = update.message.text[4:].strip()
    elif message_text.startswith("+ "):
        task_title = update.message.text[2:].strip()
    else:
        task_title = None
    
    if task_title:
        try:
            chat_id = update.effective_chat.id
            task_id = task_bot.add_task(chat_id, task_title, thread_id)
            
            task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
            if keyboard:
                await update.message.reply_text(
                    f"✅ Added task #{task_id}: {task_bot.escape_markdown(task_title)}\n\n{task_list}",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    f"✅ Added task #{task_id}: {task_title}"
                )
            await delete_user_message(update)
        except ValueError as e:
            logger.warning(f"Invalid task input from chat {update.effective_chat.id}: {str(e)}")
            await update.message.reply_text(f"❌ {str(e)}")
            await delete_user_message(update)
        except Exception as e:
            logger.error(f"Error adding task from text message: {e}")
            await update.message.reply_text("❌ Error adding task. Please try again.")
            await delete_user_message(update)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboard buttons"""
    query = update.callback_query
    await query.answer()
    
    if not query.data:
        logger.warning("❌ Received callback query without data")
        return
    
    logger.info(f"🔍 Received callback query: {query.data}")
    
    try:
        if not task_bot.validate_callback_data(query.data):
            logger.warning(f"❌ Invalid callback data format: {query.data}")
            await query.edit_message_text("❌ Invalid request format. Please try again.")
            return
        
        if query.data.startswith("remove_"):
            parts = query.data.split("_")
            chat_id = None
            thread_id = None
            task_id = None
            
            try:
                if len(parts) == 3:
                    chat_id = int(parts[1])
                    task_id = int(parts[2])
                elif len(parts) == 4:
                    chat_id = int(parts[1])
                    thread_id = int(parts[2])
                    task_id = int(parts[3])
                else:
                    raise ValueError("Unexpected number of parts in callback data")
            except ValueError as parse_error:
                logger.error(f"Error parsing callback data parts: {parse_error}")
                await query.edit_message_text("❌ Error processing request. Please try again.")
                return
            
            logger.info(f"🔍 Parsed callback data - chat_id: {chat_id}, thread_id: {thread_id}, task_id: {task_id}")
            message_thread_id = getattr(query.message, "message_thread_id", None)
            logger.info(f"🔍 Query message chat id: {query.message.chat.id}, thread id: {message_thread_id}")
            
            # Verify the callback is from the same chat/thread context
            if query.message.chat.id != chat_id:
                logger.warning(f"❌ Chat ID mismatch - callback chat_id: {chat_id}, message chat_id: {query.message.chat.id}")
                await query.edit_message_text("❌ This button is not for this chat!")
                return
            
            if thread_id is not None:
                normalized_message_thread_id = message_thread_id if message_thread_id is not None else 0
                if thread_id != normalized_message_thread_id:
                    logger.warning(f"❌ Thread ID mismatch - callback thread_id: {thread_id}, message thread_id: {message_thread_id}")
                    await query.edit_message_text("❌ This button is not for this topic!")
                    return

            logger.info(f"✅ Context matches, attempting to remove task #{task_id}")
            success, task_title = task_bot.remove_task(chat_id, task_id, thread_id)
            logger.info(f"🔍 Task removal result: success={success}, title='{task_title}'")
            if success:
                task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
                if keyboard:
                    await query.edit_message_text(
                        f"✅ Removed task #{task_id}: {task_bot.escape_markdown(task_title)}\n\n{task_list}",
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text(
                        f"✅ Removed task #{task_id}: {task_title}\n\n"
                        "📝 No tasks remaining in the list."
                    )
            else:
                await query.edit_message_text(
                    f"❌ Task #{task_id} not found or already removed!"
                )
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data: {e}")
        await query.edit_message_text("❌ Error processing request. Please try again.")
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")

def generate_webhook_secret() -> str:
    """Generate a cryptographically secure random secret token"""
    return secrets.token_urlsafe(32)  # 32 bytes = 256 bits of entropy

async def main():
    """Main function to run the bot"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("text", show_text_list))
    application.add_handler(CommandHandler("add", add_task))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    webhook_url = os.getenv('WEBHOOK_URL')
    webhook_path = os.getenv('WEBHOOK_PATH', '/task-bot')
    
    if webhook_url:
        try:
            logger.info(f"🌐 Starting bot with webhook mode...")
            logger.info(f"📡 Webhook URL: {webhook_url}")
            logger.info(f"🔌 Port: 8443")
            logger.info(f"🛤️ Path: {webhook_path}")
            
            # Generate a new random secret token for this session
            webhook_secret = generate_webhook_secret()
            logger.info("🔐 Generated new webhook secret token for this session")
            
            full_webhook_url = f"{webhook_url.rstrip('/')}{webhook_path}"
            logger.info(f"🔗 Full webhook URL: {full_webhook_url}")
            
            await application.initialize()
            await application.start()
            await application.updater.start_webhook(
                listen="0.0.0.0",
                port=8443,
                webhook_url=full_webhook_url,
                url_path=webhook_path,
                secret_token=webhook_secret
            )
            logger.info("🌐 Webhook started successfully")
            
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down bot...")
            finally:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
                close_connection_pool()
                
        except Exception as e:
            logger.error(f"❌ Error starting webhook mode: {e}")
            logger.info("🔄 Falling back to polling mode...")
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            logger.info("🔄 Polling started successfully")
            
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down bot...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            close_connection_pool()
    else:
        logger.info("🔄 Starting bot with polling mode...")
        logger.info("ℹ️ WEBHOOK_URL not set - using polling")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("🔄 Polling started successfully")
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down bot...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            close_connection_pool()

if __name__ == '__main__':
    asyncio.run(main())

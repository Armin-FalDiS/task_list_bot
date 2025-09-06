#!/usr/bin/env python3
"""
Telegram Task List Bot
A simple bot that manages a shared task list for groups.
"""

import os
import json
import logging
import stat
import time
import html
import re
import secrets
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# File to store the task list (can be overridden by environment variable)
TASK_FILE = os.getenv('TASK_FILE', 'task_list.json')

# Maximum number of tasks per chat (can be overridden by environment variable)
MAX_TASKS_PER_CHAT = int(os.getenv('MAX_TASKS_PER_CHAT', '42'))

class TaskListBot:
    def __init__(self):
        logger.info("🤖 Initializing TaskListBot...")
        logger.info(f"📁 Task file location: {TASK_FILE}")
        logger.info(f"📊 Maximum tasks per chat: {MAX_TASKS_PER_CHAT}")
        self.tasks = self.load_tasks()
        logger.info("🚀 TaskListBot initialization complete")
    
    def sanitize_task_text(self, text: str) -> str:
        """Sanitize and validate task text input"""
        if not text or not isinstance(text, str):
            raise ValueError("Task text must be a non-empty string")
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Check length limits
        if len(text) > 1000:
            raise ValueError("Task text too long (max 1000 characters)")
        
        if len(text) < 1:
            raise ValueError("Task text cannot be empty")
        
        # Remove or escape potentially dangerous characters
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit consecutive whitespace
        text = re.sub(r'\s{3,}', ' ', text)
        
        return text
    
    def validate_callback_data(self, data: str) -> bool:
        """Validate callback data format"""
        if not data or not isinstance(data, str):
            return False
        
        # Expected format: "remove_{chat_id}_{task_id}"
        pattern = r'^remove_\d+_\d+$'
        return bool(re.match(pattern, data))
    
    def load_tasks(self) -> Dict[int, List[Dict]]:
        """Load tasks from file, organized by chat_id"""
        logger.info(f"🔄 Attempting to load tasks from: {TASK_FILE}")
        
        # Check if file exists
        if not os.path.exists(TASK_FILE):
            logger.info(f"📄 Task file does not exist: {TASK_FILE}")
            logger.info("📝 Creating new empty task list")
            return {}
        
        # Get file information
        try:
            file_stat = os.stat(TASK_FILE)
            file_size = file_stat.st_size
            file_mtime = time.ctime(file_stat.st_mtime)
            file_permissions = stat.filemode(file_stat.st_mode)
            
            logger.info(f"📊 File info - Size: {file_size} bytes, Modified: {file_mtime}, Permissions: {file_permissions}")
            
            # Check if file is empty
            if file_size == 0:
                logger.warning(f"⚠️ Task file is empty: {TASK_FILE}")
                return {}
            
        except OSError as e:
            logger.error(f"❌ Error getting file info for {TASK_FILE}: {e}")
            return {}
        
        # Try to read and parse the file
        try:
            with open(TASK_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"📖 Successfully read {len(content)} characters from file")
                
                if not content.strip():
                    logger.warning("⚠️ File contains only whitespace")
                    return {}
                
                tasks = json.loads(content)
                logger.info(f"✅ Successfully loaded {len(tasks)} chat(s) with tasks")
                
                # Log summary of loaded tasks
                total_tasks = sum(len(chat_tasks) for chat_tasks in tasks.values())
                logger.info(f"📋 Total tasks loaded: {total_tasks}")
                
                for chat_id, chat_tasks in tasks.items():
                    logger.info(f"  💬 Chat {chat_id}: {len(chat_tasks)} tasks")
                
                return tasks
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error in {TASK_FILE}: {e}")
            logger.error(f"📄 File content preview: {content[:50]}...")
            return {}
        except UnicodeDecodeError as e:
            logger.error(f"❌ Unicode decode error in {TASK_FILE}: {e}")
            return {}
        except PermissionError as e:
            logger.error(f"❌ Permission denied reading {TASK_FILE}: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected error loading tasks from {TASK_FILE}: {e}")
            return {}
    
    def save_tasks(self):
        """Save tasks to file"""
        logger.info(f"💾 Attempting to save tasks to: {TASK_FILE}")
        
        # Calculate task summary before saving
        total_tasks = sum(len(chat_tasks) for chat_tasks in self.tasks.values())
        logger.info(f"📊 Saving {len(self.tasks)} chat(s) with {total_tasks} total tasks")
        
        for chat_id, chat_tasks in self.tasks.items():
            logger.info(f"  💬 Chat {chat_id}: {len(chat_tasks)} tasks")
        
        # Check if directory exists and create if needed
        task_dir = os.path.dirname(os.path.abspath(TASK_FILE))
        if task_dir and not os.path.exists(task_dir):
            try:
                os.makedirs(task_dir, exist_ok=True)
                logger.info(f"📁 Created directory: {task_dir}")
            except OSError as e:
                logger.error(f"❌ Failed to create directory {task_dir}: {e}")
                return
        
        # Check write permissions
        if os.path.exists(TASK_FILE):
            try:
                if not os.access(TASK_FILE, os.W_OK):
                    logger.error(f"❌ No write permission for {TASK_FILE}")
                    return
            except OSError as e:
                logger.error(f"❌ Error checking write permissions for {TASK_FILE}: {e}")
                return
        
        # Get file info before writing (if file exists)
        old_size = 0
        old_mtime = None
        if os.path.exists(TASK_FILE):
            try:
                old_stat = os.stat(TASK_FILE)
                old_size = old_stat.st_size
                old_mtime = time.ctime(old_stat.st_mtime)
                logger.info(f"📊 Current file - Size: {old_size} bytes, Modified: {old_mtime}")
            except OSError as e:
                logger.warning(f"⚠️ Could not get file info before saving: {e}")
        
        # Write the file
        try:
            with open(TASK_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            
            # Get new file info after writing
            try:
                new_stat = os.stat(TASK_FILE)
                new_size = new_stat.st_size
                new_mtime = time.ctime(new_stat.st_mtime)
                new_permissions = stat.filemode(new_stat.st_mode)
                
                logger.info(f"✅ Successfully saved tasks to {TASK_FILE}")
                logger.info(f"📊 New file info - Size: {new_size} bytes, Modified: {new_mtime}, Permissions: {new_permissions}")
                
                if old_size > 0:
                    size_diff = new_size - old_size
                    logger.info(f"📈 Size change: {size_diff:+d} bytes ({old_size} → {new_size})")
                
                # Verify persistence after saving
                if self.verify_persistence():
                    logger.info("✅ Persistence verification passed")
                else:
                    logger.error("❌ Persistence verification failed - data may not be saved correctly")
                
            except OSError as e:
                logger.warning(f"⚠️ Could not get file info after saving: {e}")
                
        except PermissionError as e:
            logger.error(f"❌ Permission denied writing to {TASK_FILE}: {e}")
        except OSError as e:
            logger.error(f"❌ OS error writing to {TASK_FILE}: {e}")
        except UnicodeEncodeError as e:
            logger.error(f"❌ Unicode encode error writing to {TASK_FILE}: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error saving tasks to {TASK_FILE}: {e}")
            logger.error(f"📄 Task data preview: {len(self.tasks)} chats, {sum(len(chat_tasks) for chat_tasks in self.tasks.values())} total tasks")
    
    def verify_persistence(self) -> bool:
        """Verify that the task file exists and contains valid data"""
        logger.info(f"🔍 Verifying persistence for: {TASK_FILE}")
        
        if not os.path.exists(TASK_FILE):
            logger.warning(f"⚠️ Task file does not exist: {TASK_FILE}")
            return False
        
        try:
            with open(TASK_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    logger.warning("⚠️ Task file is empty")
                    return False
                
                # Try to parse the JSON
                file_tasks = json.loads(content)
                logger.info(f"✅ Persistence verification successful - file contains {len(file_tasks)} chat(s)")
                
                # Compare with in-memory data
                if file_tasks == self.tasks:
                    logger.info("✅ File content matches in-memory data")
                    return True
                else:
                    logger.warning("⚠️ File content differs from in-memory data")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Persistence verification failed: {e}")
            return False
    
    def get_chat_tasks(self, chat_id: int) -> List[Dict]:
        """Get tasks for a specific chat"""
        return self.tasks.get(str(chat_id), [])
    
    def add_task(self, chat_id: int, task_text: str) -> int:
        """Add a new task to the list"""
        # Sanitize and validate input
        try:
            sanitized_text = self.sanitize_task_text(task_text)
        except ValueError as e:
            logger.warning(f"❌ Invalid task text from chat {chat_id}: {str(e)}")
            raise
        
        # Check task limit
        chat_tasks = self.get_chat_tasks(chat_id)
        if len(chat_tasks) >= MAX_TASKS_PER_CHAT:
            logger.warning(f"❌ Task limit reached for chat {chat_id}: {len(chat_tasks)}/{MAX_TASKS_PER_CHAT}")
            raise ValueError(f"Task limit reached! Maximum {MAX_TASKS_PER_CHAT} tasks per chat. Please remove some tasks first.")
        
        logger.info(f"➕ Adding new task to chat {chat_id} ({len(chat_tasks) + 1}/{MAX_TASKS_PER_CHAT})")
        
        task_id = len(chat_tasks) + 1
        new_task = {
            "id": task_id,
            "text": sanitized_text
        }
        chat_tasks.append(new_task)
        self.tasks[str(chat_id)] = chat_tasks
        
        logger.info(f"💾 Triggering save after adding task #{task_id} to chat {chat_id}")
        self.save_tasks()
        
        logger.info(f"✅ Task #{task_id} successfully added and saved")
        return task_id
    
    def remove_task(self, chat_id: int, task_id: int) -> tuple[bool, str]:
        """Remove a task by ID and return (success, task_description)"""
        logger.info(f"🗑️ Attempting to remove task #{task_id} from chat {chat_id}")
        
        chat_tasks = self.get_chat_tasks(chat_id)
        for i, task in enumerate(chat_tasks):
            if task["id"] == task_id:
                task_description = task["text"]
                logger.info(f"📝 Found task #{task_id} to remove: '{task_description}'")
                
                del chat_tasks[i]
                # Renumber remaining tasks
                for j, remaining_task in enumerate(chat_tasks):
                    remaining_task["id"] = j + 1
                
                self.tasks[str(chat_id)] = chat_tasks
                
                logger.info(f"💾 Triggering save after removing task #{task_id} from chat {chat_id}")
                self.save_tasks()
                
                logger.info(f"✅ Task #{task_id} successfully removed and saved")
                return True, task_description
        
        logger.warning(f"⚠️ Task #{task_id} not found in chat {chat_id}")
        return False, ""
    
    def format_task_list(self, chat_id: int) -> str:
        """Format the task list for display"""
        chat_tasks = self.get_chat_tasks(chat_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task.\n\n📊 Task limit: {MAX_TASKS_PER_CHAT} per chat"
        
        task_lines = [f"📋 *Current Task List:* ({len(chat_tasks)}/{MAX_TASKS_PER_CHAT})\n"]
        for task in chat_tasks:
            # Escape Markdown special characters in task text
            escaped_text = self.escape_markdown(task['text'])
            task_lines.append(f"{task['id']}. {escaped_text}")
        
        task_lines.append(f"\n💡 Click on any task button to remove it")
        return "\n".join(task_lines)
    
    def escape_markdown(self, text: str) -> str:
        """Escape Markdown special characters"""
        # Characters that need escaping in Markdown
        escape_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    def format_task_list_plain(self, chat_id: int) -> str:
        """Format the task list for display without Markdown"""
        chat_tasks = self.get_chat_tasks(chat_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task.\n\n📊 Task limit: {MAX_TASKS_PER_CHAT} per chat"
        
        task_lines = [f"📋 Current Task List: ({len(chat_tasks)}/{MAX_TASKS_PER_CHAT})\n"]
        for task in chat_tasks:
            task_lines.append(f"{task['id']}. {task['text']}")
        
        task_lines.append(f"\n💡 Click on any task button to remove it")
        return "\n".join(task_lines)
    
    def format_task_list_with_buttons(self, chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """Format the task list as buttons only - no text, just clickable task buttons"""
        chat_tasks = self.get_chat_tasks(chat_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task.\n\n📊 Task limit: {MAX_TASKS_PER_CHAT} per chat", None
        
        keyboard_buttons = []
        
        for task in chat_tasks:
            # Truncate task text if too long for button
            task_text = task['text']
            if len(task_text) > 50:
                task_text = task_text[:47] + "..."
            
            # Create a button for each task - the button text IS the task
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"{task['id']}. {task_text}", 
                    callback_data=f"remove_{chat_id}_{task['id']}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
        return f"📋 **Click any task to remove it:** ({len(chat_tasks)}/{MAX_TASKS_PER_CHAT})", keyboard

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
        task_list = task_bot.format_task_list(chat_id)
        await update.message.reply_text(task_list, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending text task list: {e}")
        # Fallback: send without Markdown formatting
        try:
            chat_id = update.effective_chat.id
            task_list = task_bot.format_task_list_plain(chat_id)
            await update.message.reply_text(task_list)
        except Exception as e2:
            logger.error(f"Error sending plain text task list: {e2}")
            await update.message.reply_text("❌ Error displaying task list. Please try again.")
    
    # Clean up user's command message (always attempt, regardless of success/failure above)
    await delete_user_message(update)

# Global bot instance
task_bot = TaskListBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not update.message:
        logger.warning("Received /start command without message")
        return
    
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "🤖 **Task List Bot**\n\n"
            "This bot helps manage a shared task list in groups!\n\n"
            "**Commands:**\n"
            "/list - Show current tasks (as clickable buttons)\n"
            "/text - Show current tasks (as text list)\n"
            "/add <task> - Add a new task\n\n"
            "💡 **Tip:** Click on any task button to remove it!\n\n"
            "Add me to a group to start managing tasks together!"
        )
    else:
        await update.message.reply_text(
            "🤖 Task List Bot is ready!\n\n"
            "Use /list to see current tasks or /add <task> to add a new one."
        )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command"""
    if not update.message:
        logger.warning("Received /list command without message")
        return
    
    try:
        chat_id = update.effective_chat.id
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
        
        if keyboard:
            await update.message.reply_text(task_list, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await update.message.reply_text(task_list, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending task list with buttons: {e}")
        # Fallback: send without Markdown formatting
        try:
            chat_id = update.effective_chat.id
            task_list = task_bot.format_task_list_plain(chat_id)
            await update.message.reply_text(task_list)
        except Exception as e2:
            logger.error(f"Error sending plain task list: {e2}")
            await update.message.reply_text("❌ Error displaying task list. Please try again.")
    
    # Clean up user's command message (always attempt, regardless of success/failure above)
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
        task_text = " ".join(context.args)
        task_id = task_bot.add_task(chat_id, task_text)
        
        # Show updated task list with buttons
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
        if keyboard:
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {task_bot.escape_markdown(task_text)}\n\n{task_list}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            # Fallback if no keyboard (shouldn't happen after adding a task)
            escaped_text = task_bot.escape_markdown(task_text)
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {escaped_text}\n\n"
                f"Use /list to see all tasks or /remove {task_id} to remove this one.",
                parse_mode='Markdown'
            )
    except ValueError as e:
        logger.warning(f"Invalid task input from chat {update.effective_chat.id}: {str(e)}")
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        await update.message.reply_text("❌ Error adding task. Please try again.")
    
    # Clean up user's command message (always attempt, regardless of success/failure above)
    await delete_user_message(update)



async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    # Check if update has a message
    if not update.message:
        logger.warning("Received update without message")
        return
    
    # Only respond in groups, not private chats
    if update.effective_chat.type == "private":
        return
    
    message_text = update.message.text.lower()
    
    # Simple keyword detection for adding tasks
    if message_text.startswith("add ") or message_text.startswith("+ "):
        task_text = update.message.text[4:].strip()  # Remove "add " or "+ "
        if task_text:
            try:
                chat_id = update.effective_chat.id
                task_id = task_bot.add_task(chat_id, task_text)
                
                # Show updated task list with buttons
                task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
                if keyboard:
                    await update.message.reply_text(
                        f"✅ Added task #{task_id}: {task_bot.escape_markdown(task_text)}\n\n{task_list}",
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Added task #{task_id}: {task_text}"
                    )
                # Clean up user's message
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
    await query.answer()  # Acknowledge the callback query
    
    if not query.data:
        return
    
    try:
        # Validate callback data format first
        if not task_bot.validate_callback_data(query.data):
            logger.warning(f"❌ Invalid callback data format: {query.data}")
            await query.edit_message_text("❌ Invalid request format. Please try again.")
            return
        
        # Parse callback data: "remove_{chat_id}_{task_id}"
        if query.data.startswith("remove_"):
            parts = query.data.split("_")
            if len(parts) == 3:
                chat_id = int(parts[1])
                task_id = int(parts[2])
                
                # Verify the callback is from the same chat
                if query.message.chat.id == chat_id:
                    success, task_description = task_bot.remove_task(chat_id, task_id)
                    if success:
                        # Show updated task list with buttons
                        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
                        if keyboard:
                            await query.edit_message_text(
                                f"✅ Removed task #{task_id}: {task_bot.escape_markdown(task_description)}\n\n{task_list}",
                                parse_mode='Markdown',
                                reply_markup=keyboard
                            )
                        else:
                            await query.edit_message_text(
                                f"✅ Removed task #{task_id}: {task_description}\n\n"
                                "📝 No tasks remaining in the list."
                            )
                    else:
                        await query.edit_message_text(
                            f"❌ Task #{task_id} not found or already removed!"
                        )
                else:
                    await query.edit_message_text("❌ This button is not for this chat!")
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
    # Get bot token from environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("text", show_text_list))
    application.add_handler(CommandHandler("add", add_task))
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Add callback query handler for inline keyboard buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Check for webhook configuration
    webhook_url = os.getenv('WEBHOOK_URL')
    webhook_path = os.getenv('WEBHOOK_PATH', '/task-bot')
    
    if webhook_url:
        # Use webhook mode
        try:
            logger.info(f"🌐 Starting bot with webhook mode...")
            logger.info(f"📡 Webhook URL: {webhook_url}")
            logger.info(f"🔌 Port: 8443")
            logger.info(f"🛤️ Path: {webhook_path}")
            
            # Generate a new random secret token for this session
            webhook_secret = generate_webhook_secret()
            logger.info("🔐 Generated new webhook secret token for this session")
            
            # Set webhook with the generated secret token using the bot's built-in method
            try:
                # Combine webhook URL with path
                full_webhook_url = f"{webhook_url.rstrip('/')}{webhook_path}"
                await application.bot.set_webhook(
                    url=full_webhook_url,
                    secret_token=webhook_secret
                )
                logger.info(f"✅ Webhook set successfully: {full_webhook_url}")
            except Exception as e:
                logger.error(f"❌ Failed to set webhook: {e}")
                logger.info("🔄 Falling back to polling mode...")
                application.run_polling()
                return
            
            # Run webhook with secret verification
            application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                webhook_url=webhook_url,
                url_path=webhook_path,
                secret_token=webhook_secret
            )
        except Exception as e:
            logger.error(f"❌ Error starting webhook mode: {e}")
            logger.info("🔄 Falling back to polling mode...")
            application.run_polling()
    else:
        # Use polling mode (fallback)
        logger.info("🔄 Starting bot with polling mode...")
        logger.info("ℹ️ WEBHOOK_URL not set - using polling")
        application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

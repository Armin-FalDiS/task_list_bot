#!/usr/bin/env python3
"""
Telegram Task List Bot
A simple bot that manages a shared task list for groups.
"""

import os
import json
import logging
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

class TaskListBot:
    def __init__(self):
        self.tasks = self.load_tasks()
    
    def load_tasks(self) -> Dict[int, List[Dict]]:
        """Load tasks from file, organized by chat_id"""
        try:
            if os.path.exists(TASK_FILE):
                with open(TASK_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
        return {}
    
    def save_tasks(self):
        """Save tasks to file"""
        try:
            with open(TASK_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
    
    def get_chat_tasks(self, chat_id: int) -> List[Dict]:
        """Get tasks for a specific chat"""
        return self.tasks.get(str(chat_id), [])
    
    def add_task(self, chat_id: int, task_text: str) -> int:
        """Add a new task to the list"""
        chat_tasks = self.get_chat_tasks(chat_id)
        task_id = len(chat_tasks) + 1
        new_task = {
            "id": task_id,
            "text": task_text,
            "added_by": "user"  # We could track user info here if needed
        }
        chat_tasks.append(new_task)
        self.tasks[str(chat_id)] = chat_tasks
        self.save_tasks()
        return task_id
    
    def remove_task(self, chat_id: int, task_id: int) -> bool:
        """Remove a task by ID"""
        chat_tasks = self.get_chat_tasks(chat_id)
        for i, task in enumerate(chat_tasks):
            if task["id"] == task_id:
                del chat_tasks[i]
                # Renumber remaining tasks
                for j, remaining_task in enumerate(chat_tasks):
                    remaining_task["id"] = j + 1
                self.tasks[str(chat_id)] = chat_tasks
                self.save_tasks()
                return True
        return False
    
    def format_task_list(self, chat_id: int) -> str:
        """Format the task list for display"""
        chat_tasks = self.get_chat_tasks(chat_id)
        if not chat_tasks:
            return "📝 No tasks in the list yet!\n\nUse /add <task> to add a new task."
        
        task_lines = ["📋 *Current Task List:*\n"]
        for task in chat_tasks:
            # Escape Markdown special characters in task text
            escaped_text = self.escape_markdown(task['text'])
            task_lines.append(f"{task['id']}. {escaped_text}")
        
        task_lines.append(f"\n💡 Use /remove <number> to remove a task")
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
            return "📝 No tasks in the list yet!\n\nUse /add <task> to add a new task."
        
        task_lines = ["📋 Current Task List:\n"]
        for task in chat_tasks:
            task_lines.append(f"{task['id']}. {task['text']}")
        
        task_lines.append(f"\n💡 Use /remove <number> to remove a task")
        return "\n".join(task_lines)
    
    def format_task_list_with_buttons(self, chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """Format the task list with inline keyboard buttons for removal"""
        chat_tasks = self.get_chat_tasks(chat_id)
        if not chat_tasks:
            return "📝 No tasks in the list yet!\n\nUse /add <task> to add a new task.", None
        
        task_lines = ["📋 *Current Task List:*\n"]
        keyboard_buttons = []
        
        for task in chat_tasks:
            # Escape Markdown special characters in task text
            escaped_text = self.escape_markdown(task['text'])
            task_lines.append(f"{task['id']}. {escaped_text}")
            
            # Create a button for each task
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"🗑️ Remove #{task['id']}", 
                    callback_data=f"remove_{chat_id}_{task['id']}"
                )
            ])
        
        task_lines.append(f"\n💡 Click the buttons below to remove tasks")
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
        return "\n".join(task_lines), keyboard

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
            "/list - Show current tasks\n"
            "/add <task> - Add a new task\n"
            "/remove <number> - Remove a task by number\n"
            "/clear - Clear all tasks\n\n"
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
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        await update.message.reply_text("❌ Error adding task. Please try again.")

async def remove_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove command"""
    if not update.message:
        logger.warning("Received /remove command without message")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task number to remove!\n"
            "Example: /remove 1"
        )
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Please provide a valid task number!\n"
            "Example: /remove 1"
        )
        return
    
    chat_id = update.effective_chat.id
    if task_bot.remove_task(chat_id, task_id):
        # Show updated task list with buttons
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
        if keyboard:
            await update.message.reply_text(
                f"✅ Removed task #{task_id}!\n\n{task_list}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                f"✅ Removed task #{task_id}!\n\n"
                "📝 No tasks remaining in the list."
            )
    else:
        await update.message.reply_text(
            f"❌ Task #{task_id} not found!\n"
            "Use /list to see available tasks."
        )

async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command"""
    if not update.message:
        logger.warning("Received /clear command without message")
        return
    
    chat_id = update.effective_chat.id
    task_bot.tasks[str(chat_id)] = []
    task_bot.save_tasks()
    
    # Show updated (empty) task list
    task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
    await update.message.reply_text(
        f"🗑️ All tasks cleared!\n\n{task_list}",
        parse_mode='Markdown'
    )

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

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboard buttons"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query
    
    if not query.data:
        return
    
    try:
        # Parse callback data: "remove_{chat_id}_{task_id}"
        if query.data.startswith("remove_"):
            parts = query.data.split("_")
            if len(parts) == 3:
                chat_id = int(parts[1])
                task_id = int(parts[2])
                
                # Verify the callback is from the same chat
                if query.message.chat.id == chat_id:
                    if task_bot.remove_task(chat_id, task_id):
                        # Show updated task list with buttons
                        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id)
                        if keyboard:
                            await query.edit_message_text(
                                f"✅ Removed task #{task_id}!\n\n{task_list}",
                                parse_mode='Markdown',
                                reply_markup=keyboard
                            )
                        else:
                            await query.edit_message_text(
                                f"✅ Removed task #{task_id}!\n\n"
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

def main():
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
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("remove", remove_task))
    application.add_handler(CommandHandler("clear", clear_tasks))
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Add callback query handler for inline keyboard buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Start the bot
    logger.info("Starting Task List Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()

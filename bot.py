#!/usr/bin/env python3
"""
Telegram Task List Bot
A simple bot that manages a shared task list for groups.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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

# Global bot instance
task_bot = TaskListBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
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
    try:
        chat_id = update.effective_chat.id
        task_list = task_bot.format_task_list(chat_id)
        await update.message.reply_text(task_list, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending task list: {e}")
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
        
        # Escape the task text for display
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
        await update.message.reply_text(f"✅ Removed task #{task_id}")
    else:
        await update.message.reply_text(
            f"❌ Task #{task_id} not found!\n"
            "Use /list to see available tasks."
        )

async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command"""
    chat_id = update.effective_chat.id
    task_bot.tasks[str(chat_id)] = []
    task_bot.save_tasks()
    await update.message.reply_text("🗑️ All tasks cleared!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
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
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {task_text}"
            )

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
    
    # Start the bot
    logger.info("Starting Task List Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()

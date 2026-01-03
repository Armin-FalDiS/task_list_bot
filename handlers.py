import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from task_list import TaskListBot
from utils import delete_user_message, get_thread_id, get_thread_id_from_message

load_dotenv()

logger = logging.getLogger(__name__)

task_bot = TaskListBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /start command without message")
        return
    
    await update.message.reply_text(
        "🤖 Task List Bot\n\n"
        "This bot helps manage your task list!\n\n"
        "Commands:\n"
        "/list - Show current tasks (as clickable buttons)\n"
        "/text - Show current tasks (as text list)\n"
        "/mytasks - Show all tasks assigned to you\n"
        "/add <title> - Add a new task (multi-line for description)\n"
        "/remove <task_id> - Remove a task\n"
        "/assign <task_id> @username - Assign a task to someone\n"
        "/details <task_id> [description] - Set or view task details\n"
        "/details+ <task_id>\\n[description] - Append to task details (multi-line)\n"
        "/deadline <task_id> [date] - Set or view task deadline\n"
        "  Formats: YYYY-MM-DD, DD, MM-DD, +N, or \"clear\" to remove\n\n"
        "Shorthand Commands:\n"
        "+ <title> - Add a task (multi-line for description)\n"
        "-<task_id> - Remove a task\n"
        "@<task_id> @username - Assign a task\n"
        "?<task_id> - View task details\n"
        "+<task_id>\\n[description] - Set task details (multi-line)\n"
        "+<task_id>+\\n[description] - Append to task details (multi-line)\n\n"
        "💡 Tip: Click on any task button to remove it!"
    )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /list command without message")
        return
    
    try:
        chat_id = update.effective_chat.id
        thread_id = get_thread_id(update)
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
        
        if keyboard:
            await update.message.reply_text(task_list, reply_markup=keyboard)
        else:
            await update.message.reply_text(task_list)
    except Exception as e:
        logger.error(f"Error sending task list with buttons: {e}")
        try:
            chat_id = update.effective_chat.id
            thread_id = get_thread_id(update)
            task_list = task_bot.format_task_list_plain(chat_id, thread_id)
            await update.message.reply_text(task_list)
        except Exception as e2:
            logger.error(f"Error sending plain task list: {e2}")
            await update.message.reply_text("❌ Error displaying task list. Please try again.")
    
    await delete_user_message(update)

async def show_text_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /text command without message")
        return
    
    try:
        chat_id = update.effective_chat.id
        thread_id = get_thread_id(update)
        task_list = task_bot.format_task_list_plain(chat_id, thread_id)
        await update.message.reply_text(task_list)
    except Exception as e:
        logger.error(f"Error sending text task list: {e}")
        await update.message.reply_text("❌ Error displaying task list. Please try again.")
    
    await delete_user_message(update)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /add command without message")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task to add!\n"
            "Example: /add Buy groceries\n"
            "Or with description:\n"
            "/add Buy groceries\n"
            "Get milk, eggs, bread"
        )
        await delete_user_message(update)
        return
    
    try:
        chat_id = update.effective_chat.id
        thread_id = get_thread_id(update)
        
        full_text = update.message.text
        command_part = full_text.split('\n', 1)[0]
        task_title = command_part[5:].strip()
        
        if not task_title:
            await update.message.reply_text(
                "❌ Please provide a task title!\n"
                "Example: /add Buy groceries"
            )
            await delete_user_message(update)
            return
        
        task_id = task_bot.add_task(chat_id, task_title, thread_id)
        
        if '\n' in full_text:
            description = full_text.split('\n', 1)[1].strip()
            if description:
                if len(description) > 5000:
                    await update.message.reply_text(
                        "❌ Task description too long (max 5000 characters)"
                    )
                    await delete_user_message(update)
                    return
                task_bot.set_task_details(chat_id, task_id, description, thread_id)
        
        task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
        if keyboard:
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {task_title}\n\n{task_list}",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                f"✅ Added task #{task_id}: {task_title}\n\n"
                f"Use /list to see all tasks."
            )
    except ValueError as e:
        logger.warning(f"Invalid task input from chat {update.effective_chat.id}: {str(e)}")
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        await update.message.reply_text("❌ Error adding task. Please try again.")
    
    await delete_user_message(update)

async def assign_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /assign command without message")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Please provide a task ID and username!\n"
            "Example: /assign 1 @username"
        )
        await delete_user_message(update)
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid task ID. Please provide a number.\n"
            "Example: /assign 1 @username"
        )
        await delete_user_message(update)
        return
    
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    
    mention = context.args[1]
    if not mention.startswith('@'):
        await update.message.reply_text(
            "❌ Please provide a username starting with @!\n"
            "Example: /assign 1 @username"
        )
        await delete_user_message(update)
        return
    
    assignee = None
    assignee_display = None
    
    logger.debug(f"Assign command - message text: {update.message.text}")
    logger.debug(f"Assign command - entities: {update.message.entities}")
    logger.debug(f"Assign command - reply_to_message: {update.message.reply_to_message}")
    
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        user = update.message.reply_to_message.from_user
        if user.username:
            assignee = user.username
            assignee_display = f"@{user.username}"
        else:
            assignee_display = user.first_name or f"User {user.id}"
        logger.debug(f"Found user from reply: {assignee_display}")
    elif update.message.entities:
        for entity in update.message.entities:
            logger.debug(f"Checking entity: type={entity.type}, offset={entity.offset}, length={entity.length}")
            if entity.type == "text_mention" and entity.user:
                if entity.user.username:
                    assignee = entity.user.username
                    assignee_display = f"@{entity.user.username}"
                else:
                    assignee_display = entity.user.first_name or f"User {entity.user.id}"
                logger.debug(f"Found user from text_mention: {assignee_display}")
                break
            elif entity.type == "mention":
                username_text = update.message.text[entity.offset:entity.offset + entity.length]
                username = username_text.lstrip('@')
                logger.debug(f"Found mention entity: {username_text}, extracted username: {username}")
                if hasattr(entity, 'user') and entity.user and entity.user.username:
                    assignee = entity.user.username
                    assignee_display = f"@{entity.user.username}"
                    logger.debug(f"Found user from mention entity: {assignee_display}")
                else:
                    assignee = username
                    assignee_display = f"@{username}"
                    logger.debug(f"Will store username as string: {assignee}")
                break
    
    if not assignee:
        assignee = mention.lstrip('@')
        assignee_display = mention
        logger.debug(f"Extracting username from mention text: {assignee}")
    
    if not assignee:
        await update.message.reply_text(
            "❌ Could not extract username.\n\n"
            "To assign a task:\n"
            "1. Reply to the user's message with /assign <task_id>\n"
            "   Example: [Reply to user] /assign 1\n\n"
            "2. Use /assign <task_id> @username\n"
            "   Example: /assign 1 @username"
        )
        await delete_user_message(update)
        return
    
    try:
        existing_assignee = task_bot.get_task_assignee(chat_id, task_id, thread_id)
        success = task_bot.set_task_assignee(chat_id, task_id, assignee, thread_id)
        
        if not success:
            await update.message.reply_text(
                f"❌ Task #{task_id} not found in this chat/thread!"
            )
            await delete_user_message(update)
            return
        
        is_same_assignment = existing_assignee and existing_assignee.lower() == assignee.lower()
        
        if is_same_assignment:
            await update.message.reply_text(
                f"ℹ️ Task #{task_id} is already assigned to {assignee_display}."
            )
        else:
            previous_info = ""
            if existing_assignee:
                previous_info = f" (reassigned from previous assignee)"
            
            await update.message.reply_text(
                f"✅ Assigned task #{task_id} to {assignee_display}{previous_info}."
            )
    except Exception as e:
        logger.error(f"Error assigning task: {e}")
        await update.message.reply_text("❌ Error assigning task. Please try again.")
    
    await delete_user_message(update)

async def set_task_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /details command without message")
        return
    
    full_text = update.message.text
    is_append = full_text.startswith("/details+")
    
    if is_append:
        await append_task_details(update, context)
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task ID!\n"
            "Example: /details 1 This is a detailed description\n"
            "Or view details: /details 1"
        )
        await delete_user_message(update)
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid task ID. Please provide a number.\n"
            "Example: /details 1 Description here"
        )
        await delete_user_message(update)
        return
    
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    
    if len(context.args) > 1:
        details_text = " ".join(context.args[1:])
        
        if len(details_text) > 5000:
            await update.message.reply_text(
                "❌ Task details too long (max 5000 characters)"
            )
            await delete_user_message(update)
            return
        
        try:
            success = task_bot.set_task_details(chat_id, task_id, details_text, thread_id)
            
            if not success:
                await update.message.reply_text(
                    f"❌ Task #{task_id} not found in this chat/thread!"
                )
                await delete_user_message(update)
                return
            
            await update.message.reply_text(
                f"✅ Updated details for task #{task_id}:\n\n{details_text}"
            )
        except Exception as e:
            logger.error(f"Error setting task details: {e}")
            await update.message.reply_text("❌ Error updating task details. Please try again.")
    else:
        task_info = task_bot.get_task_full_info(chat_id, task_id, thread_id)
        
        if not task_info:
            await update.message.reply_text(
                f"❌ Task #{task_id} not found in this chat/thread!"
            )
            await delete_user_message(update)
            return
        
        response_lines = [f"📋 Task #{task_id}: {task_info['title']}\n"]
        
        if task_info.get('details'):
            response_lines.append(f"📝 Details:\n{task_info['details']}")
        else:
            response_lines.append("📝 Details: No details set")
        
        if task_info.get('assignee'):
            assignee_display = f"@{task_info['assignee']}"
            response_lines.append(f"\n👤 Assigned to: {assignee_display}")
        
        if task_info.get('deadline'):
            deadline_str = task_info['deadline'].strftime('%Y-%m-%d') if hasattr(task_info['deadline'], 'strftime') else str(task_info['deadline'])
            response_lines.append(f"\n📅 Deadline: {deadline_str}")
        
        await update.message.reply_text("\n".join(response_lines))
    
    await delete_user_message(update)

async def set_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /deadline command without message")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Please provide a task ID!\n"
            "Example: /deadline 1 2024-12-31\n"
            "Or remove deadline: /deadline 1 clear"
        )
        await delete_user_message(update)
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid task ID. Please provide a number.\n"
            "Example: /deadline 1 2024-12-31"
        )
        await delete_user_message(update)
        return
    
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    
    if len(context.args) > 1:
        date_str = " ".join(context.args[1:]).strip().lower()
        
        if date_str == "clear" or date_str == "remove" or date_str == "none":
            success = task_bot.set_task_deadline(chat_id, task_id, None, thread_id)
            if not success:
                await update.message.reply_text(
                    f"❌ Task #{task_id} not found in this chat/thread!"
                )
                await delete_user_message(update)
                return
            
            await update.message.reply_text(
                f"✅ Removed deadline from task #{task_id}."
            )
            await delete_user_message(update)
            return
        
        try:
            from datetime import datetime, timedelta, date
            
            today = date.today()
            deadline_date = None
            
            if date_str.startswith('+'):
                days = int(date_str[1:].strip())
                deadline_date = today + timedelta(days=days)
            elif '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 2:
                    month = int(parts[0])
                    day = int(parts[1])
                    deadline_date = date(today.year, month, day)
                    if deadline_date < today:
                        deadline_date = date(today.year + 1, month, day)
                elif len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    deadline_date = date(year, month, day)
                else:
                    raise ValueError("Invalid date format")
            elif date_str.isdigit():
                day = int(date_str)
                deadline_date = date(today.year, today.month, day)
                if deadline_date < today:
                    if today.month == 12:
                        deadline_date = date(today.year + 1, 1, day)
                    else:
                        deadline_date = date(today.year, today.month + 1, day)
            else:
                try:
                    deadline_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError("Invalid date format")
            
            deadline_str = deadline_date.isoformat()
            
            success = task_bot.set_task_deadline(chat_id, task_id, deadline_str, thread_id)
            
            if not success:
                await update.message.reply_text(
                    f"❌ Task #{task_id} not found in this chat/thread!"
                )
                await delete_user_message(update)
                return
            
            await update.message.reply_text(
                f"✅ Set deadline for task #{task_id} to {deadline_str}."
            )
        except (ValueError, IndexError) as e:
            await update.message.reply_text(
                "❌ Invalid date format.\n"
                "Examples:\n"
                "/deadline 1 2024-12-31 (full date)\n"
                "/deadline 1 7 (7th of current month)\n"
                "/deadline 1 7-11 (11th of July, current year)\n"
                "/deadline 1 +7 (7 days from now)"
            )
            await delete_user_message(update)
            return
    else:
        deadline = task_bot.get_task_deadline(chat_id, task_id, thread_id)
        if deadline is None:
            await update.message.reply_text(
                f"📅 Task #{task_id} has no deadline set.\n\n"
                "To set a deadline:\n"
                "/deadline <task_id> YYYY-MM-DD (full date)\n"
                "/deadline <task_id> DD (day of current month)\n"
                "/deadline <task_id> MM-DD (month-day of current year)\n"
                "/deadline <task_id> +N (N days from now)\n"
                "Example: /deadline 1 2024-12-31 or /deadline 1 +7"
            )
        else:
            await update.message.reply_text(
                f"📅 Task #{task_id} deadline: {deadline}"
            )
    
    await delete_user_message(update)

async def append_task_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /details+ command without message")
        return
    
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    
    full_text = update.message.text
    command_part = full_text.split('\n', 1)[0]
    parts = command_part[10:].strip().split(None, 1)
    
    if not parts or not parts[0]:
        await update.message.reply_text(
            "❌ Please provide a task ID and description to append!\n"
            "Example: /details+ 1 Additional information"
        )
        await delete_user_message(update)
        return
    
    try:
        task_id = int(parts[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid task ID. Please provide a number.\n"
            "Example: /details+ 1 Additional information"
        )
        await delete_user_message(update)
        return
    
    if len(parts) < 2 and '\n' not in full_text:
        await update.message.reply_text(
            "❌ Please provide description to append!\n"
            "Example: /details+ 1 Additional information"
        )
        await delete_user_message(update)
        return
    
    details_to_append = ""
    if '\n' in full_text:
        details_to_append = full_text.split('\n', 1)[1].strip()
    else:
        details_to_append = parts[1] if len(parts) > 1 else ""
    
    if not details_to_append:
        await update.message.reply_text(
            "❌ Please provide description to append!\n"
            "Example: /details+ 1 Additional information"
        )
        await delete_user_message(update)
        return
    
    try:
        success = task_bot.append_task_details(chat_id, task_id, details_to_append, thread_id)
        
        if not success:
            await update.message.reply_text(
                f"❌ Task #{task_id} not found in this chat/thread or details too long!"
            )
            await delete_user_message(update)
            return
        
            await update.message.reply_text(
                f"✅ Appended details to task #{task_id}:\n\n{details_to_append}"
            )
    except Exception as e:
        logger.error(f"Error appending task details: {e}")
        await update.message.reply_text("❌ Error appending task details. Please try again.")
    
    await delete_user_message(update)

async def remove_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /remove command without message")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task ID!\n"
            "Example: /remove 1"
        )
        await delete_user_message(update)
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid task ID. Please provide a number.\n"
            "Example: /remove 1"
        )
        await delete_user_message(update)
        return
    
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    
    try:
        success, task_title = task_bot.remove_task(chat_id, task_id, thread_id)
        
        if success:
            task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
            
            if keyboard:
                await update.message.reply_text(
                    f"✅ Removed task #{task_id}: {task_title}\n\n{task_list}",
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    f"✅ Removed task #{task_id}: {task_title}\n\n"
                    "📝 No tasks remaining in the list."
                )
        else:
            await update.message.reply_text(
                f"❌ Task #{task_id} not found or already removed!"
            )
    except Exception as e:
        logger.error(f"Error removing task: {e}")
        await update.message.reply_text("❌ Error removing task. Please try again.")
    
    await delete_user_message(update)

async def show_my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received /mytasks command without message")
        return
    
    user_id = update.effective_user.id
    chat = update.effective_chat
    chat_id = chat.id
    thread_id = get_thread_id(update)
    
    is_private = chat.type == 'private'
    
    try:
        user = update.effective_user
        if not user.username:
            await update.message.reply_text(
                "❌ You need a username to use this command.\n\n"
                "Tasks are assigned by username. Please set a username in your Telegram settings."
            )
            return
        
        assignee = user.username
        if is_private:
            tasks = task_bot.get_user_tasks(assignee)
            header = f"👤 Your Tasks ({len(tasks)} total):\n"
        else:
            tasks = task_bot.get_user_tasks(assignee, chat_id, thread_id)
            if thread_id is not None:
                header = f"👤 Your Tasks in this thread ({len(tasks)} total):\n"
            else:
                header = f"👤 Your Tasks in this chat ({len(tasks)} total):\n"
        
        if not tasks:
            if is_private:
                await update.message.reply_text(
                    "📝 You don't have any assigned tasks!\n\n"
                    "Tasks will appear here once someone assigns them to you using /assign or @."
                )
            else:
                if thread_id is not None:
                    await update.message.reply_text(
                        "📝 You don't have any assigned tasks in this thread!\n\n"
                        "Tasks will appear here once someone assigns them to you using /assign or @."
                    )
                else:
                    await update.message.reply_text(
                        "📝 You don't have any assigned tasks in this chat!\n\n"
                        "Tasks will appear here once someone assigns them to you using /assign or @."
                    )
            await delete_user_message(update)
            return
        
        response_lines = [header]
        
        if is_private:
            current_chat_id = None
            current_thread_id = None
            
            for task in tasks:
                task_chat_id = task['chat_id']
                task_thread_id = task.get('thread_id')
                task_id = task['id']
                title = task['title']
                details = task.get('details')
                
                if task_chat_id != current_chat_id or task_thread_id != current_thread_id:
                    current_chat_id = task_chat_id
                    current_thread_id = task_thread_id
                    
                    if task_thread_id:
                        response_lines.append(f"\n💬 Chat {task_chat_id}, Thread {task_thread_id}:")
                    else:
                        response_lines.append(f"\n💬 Chat {task_chat_id}:")
                
                indicators = ""
                if details:
                    indicators += " 📝"
                if task.get('deadline'):
                    deadline_str = task['deadline'].strftime('%Y-%m-%d') if hasattr(task['deadline'], 'strftime') else str(task['deadline'])
                    indicators += f" 📅 {deadline_str}"
                
                response_lines.append(f"  • Task #{task_id}: {title}{indicators}")
            
            response_lines.append("\n💡 Use /details <task_id> in the respective chat to view full details.")
        else:
            for task in tasks:
                task_id = task['id']
                title = task['title']
                details = task.get('details')
                
                indicators = ""
                if details:
                    indicators += " 📝"
                if task.get('deadline'):
                    deadline_str = task['deadline'].strftime('%Y-%m-%d') if hasattr(task['deadline'], 'strftime') else str(task['deadline'])
                    indicators += f" 📅 {deadline_str}"
                
                response_lines.append(f"  • Task #{task_id}: {title}{indicators}")
            
            response_lines.append("\n💡 Use /details <task_id> to view full details.")
        
        response_text = "\n".join(response_lines)
        
        if len(response_text) > 4096:
            chunks = []
            current_chunk = []
            current_length = 0
            
            for line in response_lines:
                line_length = len(line) + 1
                if current_length + line_length > 4000:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = line_length
                else:
                    current_chunk.append(line)
                    current_length += line_length
            
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            
            for i, chunk in enumerate(chunks):
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response_text)
        
    except Exception as e:
        logger.error(f"Error getting user tasks: {e}")
        await update.message.reply_text("❌ Error retrieving your tasks. Please try again.")
    
    await delete_user_message(update)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logger.warning("Received update without message")
        return
    
    message_text = update.message.text
    message_lower = message_text.lower()
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    
    if message_lower.startswith("+") and len(message_lower) > 1:
        if message_lower[1].isdigit():
            first_line = message_text[1:].split('\n', 1)[0].strip()
            is_append = first_line.endswith('+')
            
            if is_append:
                task_id_str = first_line[:-1].strip()
            else:
                task_id_str = first_line.strip()
            
            try:
                task_id = int(task_id_str)
                
                if is_append:
                    if '\n' not in message_text:
                        await update.message.reply_text(
                            "❌ Please provide description to append!\n"
                            "Example: +1+\nDescription here"
                        )
                        await delete_user_message(update)
                        return
                    
                    description = message_text.split('\n', 1)[1].strip()
                    if not description:
                        await update.message.reply_text(
                            "❌ Please provide description to append!"
                        )
                        await delete_user_message(update)
                        return
                    
                    success = task_bot.append_task_details(chat_id, task_id, description, thread_id)
                    if not success:
                        await update.message.reply_text(
                            f"❌ Task #{task_id} not found in this chat/thread or details too long!"
                        )
                        await delete_user_message(update)
                        return
                    
                    await update.message.reply_text(
                        f"✅ Appended details to task #{task_id}:\n\n{description}"
                    )
                else:
                    if '\n' not in message_text:
                        await update.message.reply_text(
                            "❌ Please provide description!\n"
                            "Example: +1\nDescription here"
                        )
                        await delete_user_message(update)
                        return
                    
                    description = message_text.split('\n', 1)[1].strip()
                    if not description:
                        await update.message.reply_text(
                            "❌ Please provide description!"
                        )
                        await delete_user_message(update)
                        return
                    
                    if len(description) > 5000:
                        await update.message.reply_text(
                            "❌ Task details too long (max 5000 characters)"
                        )
                        await delete_user_message(update)
                        return
                    
                    success = task_bot.set_task_details(chat_id, task_id, description, thread_id)
                    if not success:
                        await update.message.reply_text(
                            f"❌ Task #{task_id} not found in this chat/thread!"
                        )
                        await delete_user_message(update)
                        return
                    
                    await update.message.reply_text(
                        f"✅ Updated details for task #{task_id}:\n\n{description}"
                    )
                
                await delete_user_message(update)
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid task ID. Use: +<task_id> or +<task_id>+\n"
                    "Example: +1\nDescription or +1+\nAppend description"
                )
                await delete_user_message(update)
            except Exception as e:
                logger.error(f"Error setting/appending task details: {e}")
                await update.message.reply_text("❌ Error updating task details. Please try again.")
                await delete_user_message(update)
            return
        elif message_lower.startswith("+ "):
            full_text = message_text
            task_title = full_text[2:].split('\n', 1)[0].strip()
            
            if not task_title:
                await delete_user_message(update)
                return
            
            try:
                task_id = task_bot.add_task(chat_id, task_title, thread_id)
                
                if '\n' in full_text:
                    description = full_text.split('\n', 1)[1].strip()
                    if description:
                        if len(description) > 5000:
                            await update.message.reply_text(
                                "❌ Task description too long (max 5000 characters)"
                            )
                            await delete_user_message(update)
                            return
                        task_bot.set_task_details(chat_id, task_id, description, thread_id)
                
                task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
                if keyboard:
                    await update.message.reply_text(
                        f"✅ Added task #{task_id}: {task_title}\n\n{task_list}",
                        reply_markup=keyboard
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Added task #{task_id}: {task_title}"
                    )
                await delete_user_message(update)
            except ValueError as e:
                logger.warning(f"Invalid task input from chat {chat_id}: {str(e)}")
                await update.message.reply_text(f"❌ {str(e)}")
                await delete_user_message(update)
            except Exception as e:
                logger.error(f"Error adding task from text message: {e}")
                await update.message.reply_text("❌ Error adding task. Please try again.")
                await delete_user_message(update)
            return
    
    if message_lower.startswith("-") and len(message_lower) > 1 and message_lower[1].isdigit():
        task_id_str = message_text[1:].strip()
        try:
            task_id = int(task_id_str)
            success, task_title = task_bot.remove_task(chat_id, task_id, thread_id)
            if success:
                task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
                if keyboard:
                    await update.message.reply_text(
                        f"✅ Removed task #{task_id}: {task_title}\n\n{task_list}",
                        reply_markup=keyboard
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Removed task #{task_id}: {task_title}\n\n"
                        "📝 No tasks remaining in the list."
                    )
            else:
                await update.message.reply_text(
                    f"❌ Task #{task_id} not found or already removed!"
                )
            await delete_user_message(update)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid task ID. Use: -<task_id>\n"
                "Example: -1"
            )
            await delete_user_message(update)
        except Exception as e:
            logger.error(f"Error removing task from text message: {e}")
            await update.message.reply_text("❌ Error removing task. Please try again.")
            await delete_user_message(update)
        return
    
    if message_lower.startswith("@") and len(message_lower) > 1 and message_lower[1].isdigit():
        parts = message_text[1:].strip().split(None, 1)
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Please provide task ID and username!\n"
                "Example: @1 @username"
            )
            await delete_user_message(update)
            return
        
        try:
            task_id = int(parts[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid task ID. Use: @<task_id> @username\n"
                "Example: @1 @username"
            )
            await delete_user_message(update)
            return
        
        mention = parts[1].strip()
        if not mention.startswith('@'):
            await update.message.reply_text(
                "❌ Please provide a username starting with @!\n"
                "Example: @1 @username"
            )
            await delete_user_message(update)
            return
        
        assignee = None
        assignee_display = None
        
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "text_mention" and entity.user:
                    if entity.user.username:
                        assignee = entity.user.username
                        assignee_display = f"@{entity.user.username}"
                    else:
                        assignee_display = entity.user.first_name or f"User {entity.user.id}"
                    break
                elif entity.type == "mention":
                    username_text = update.message.text[entity.offset:entity.offset + entity.length]
                    username = username_text.lstrip('@')
                    if hasattr(entity, 'user') and entity.user and entity.user.username:
                        assignee = entity.user.username
                        assignee_display = f"@{entity.user.username}"
                    else:
                        assignee = username
                        assignee_display = f"@{username}"
                    break
        
        if not assignee:
            assignee = mention.lstrip('@')
            assignee_display = mention
        
        try:
            existing_assignee = task_bot.get_task_assignee(chat_id, task_id, thread_id)
            success = task_bot.set_task_assignee(chat_id, task_id, assignee, thread_id)
            
            if not success:
                await update.message.reply_text(
                    f"❌ Task #{task_id} not found in this chat/thread!"
                )
                await delete_user_message(update)
                return
            
            is_same_assignment = existing_assignee and existing_assignee.lower() == assignee.lower()
            
            if is_same_assignment:
                await update.message.reply_text(
                    f"ℹ️ Task #{task_id} is already assigned to {assignee_display}."
                )
            else:
                previous_info = ""
                if existing_assignee:
                    previous_info = f" (reassigned from previous assignee)"
                await update.message.reply_text(
                    f"✅ Assigned task #{task_id} to {assignee_display}{previous_info}."
                )
            await delete_user_message(update)
        except Exception as e:
            logger.error(f"Error assigning task from text message: {e}")
            await update.message.reply_text("❌ Error assigning task. Please try again.")
            await delete_user_message(update)
        return
    
    if message_lower.startswith("?") and len(message_lower) > 1 and message_lower[1].isdigit():
        task_id_str = message_text[1:].strip()
        try:
            task_id = int(task_id_str)
            task_info = task_bot.get_task_full_info(chat_id, task_id, thread_id)
            
            if not task_info:
                await update.message.reply_text(
                    f"❌ Task #{task_id} not found in this chat/thread!"
                )
                await delete_user_message(update)
                return
            
            response_lines = [f"📋 Task #{task_id}: {task_info['title']}\n"]
            
            if task_info.get('details'):
                response_lines.append(f"📝 Details:\n{task_info['details']}")
            else:
                response_lines.append("📝 Details: No details set")
            
            if task_info.get('assignee'):
                assignee_display = f"@{task_info['assignee']}"
                response_lines.append(f"\n👤 Assigned to: {assignee_display}")
            
            if task_info.get('deadline'):
                deadline_str = task_info['deadline'].strftime('%Y-%m-%d') if hasattr(task_info['deadline'], 'strftime') else str(task_info['deadline'])
                response_lines.append(f"\n📅 Deadline: {deadline_str}")
            
            await update.message.reply_text("\n".join(response_lines))
            await delete_user_message(update)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid task ID. Use: ?<task_id>\n"
                "Example: ?1"
            )
            await delete_user_message(update)
        except Exception as e:
            logger.error(f"Error viewing task details from text message: {e}")
            await update.message.reply_text("❌ Error viewing task details. Please try again.")
            await delete_user_message(update)
        return

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            query_thread_id = get_thread_id_from_message(query.message)
            logger.info(f"🔍 Query message chat id: {query.message.chat.id}, thread id: {query_thread_id}")
            
            if query.message.chat.id != chat_id:
                logger.warning(f"❌ Chat ID mismatch - callback chat_id: {chat_id}, message chat_id: {query.message.chat.id}")
                await query.edit_message_text("❌ This button is not for this chat!")
                return
            
            if thread_id is not None:
                if thread_id != query_thread_id:
                    logger.warning(f"❌ Thread ID mismatch - callback thread_id: {thread_id}, query thread_id: {query_thread_id}")
                    await query.edit_message_text("❌ This button is not for this topic!")
                    return

            logger.info(f"✅ Context matches, attempting to remove task #{task_id}")
            success, task_title = task_bot.remove_task(chat_id, task_id, thread_id)
            logger.info(f"🔍 Task removal result: success={success}, title='{task_title}'")
            if success:
                task_list, keyboard = task_bot.format_task_list_with_buttons(chat_id, thread_id)
                if keyboard:
                    await query.edit_message_text(
                        f"✅ Removed task #{task_id}: {task_title}\n\n{task_list}",
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

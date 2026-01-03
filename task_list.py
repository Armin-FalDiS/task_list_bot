import re
import logging
from typing import Dict, List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import init_connection_pool, get_db_cursor

logger = logging.getLogger(__name__)

class TaskListBot:
    def __init__(self):
        logger.info("🤖 Initializing TaskListBot...")
        init_connection_pool()
        logger.info("🚀 TaskListBot initialization complete")
    
    def describe_context(self, chat_id: int, thread_id: Optional[int]) -> str:
        if thread_id is None:
            return f"chat {chat_id}"
        return f"chat {chat_id}, thread {thread_id}"
    
    def sanitize_task_title(self, title: str) -> str:
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
        if not data or not isinstance(data, str):
            return False
        
        pattern = r'^remove_-?\d+_(?:\d+_)?\d+$'
        return bool(re.match(pattern, data))
    
    
    def get_task_full_info(self, chat_id: int, task_id: int, thread_id: Optional[int] = None) -> Optional[Dict]:
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT id, title, details, assignee, deadline FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "SELECT id, title, details, assignee, deadline FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "details": row["details"],
                    "assignee": row["assignee"],
                    "deadline": row["deadline"]
                }
        except Exception as e:
            logger.error(f"❌ Error getting task info from database: {e}")
            return None
    
    def get_tasks_with_context(
        self,
        chat_id: int,
        thread_id: Optional[int] = None
    ) -> tuple[List[Dict], Optional[int]]:
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT id, title, details, assignee, deadline FROM tasks WHERE chat_id = %s AND thread_id IS NULL ORDER BY id",
                        (chat_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT id, title, details, assignee, deadline FROM tasks WHERE chat_id = %s AND thread_id = %s ORDER BY id",
                        (chat_id, thread_id)
                    )
                
                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    task = {
                        "id": row["id"],
                        "title": row["title"],
                        "details": row["details"],
                        "assignee": row["assignee"],
                        "deadline": row["deadline"]
                    }
                    tasks.append(task)
                
                return tasks, thread_id
        except Exception as e:
            logger.error(f"❌ Error loading tasks from database: {e}")
            return [], thread_id
    
    def get_chat_tasks(self, chat_id: int, thread_id: Optional[int] = None) -> List[Dict]:
        tasks, _ = self.get_tasks_with_context(chat_id, thread_id)
        return tasks
    
    def add_task(self, chat_id: int, task_title: str, thread_id: Optional[int] = None) -> int:
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
    
    def append_task_details(self, chat_id: int, task_id: int, details_to_append: str, thread_id: Optional[int] = None) -> bool:
        try:
            existing_details = self.get_task_details(chat_id, task_id, thread_id)
            new_details = (existing_details + "\n" + details_to_append) if existing_details else details_to_append
            
            if len(new_details) > 5000:
                return False
            
            return self.set_task_details(chat_id, task_id, new_details, thread_id)
        except Exception as e:
            logger.error(f"❌ Error appending task details in database: {e}")
            return False
    
    def get_task_assignee(self, chat_id: int, task_id: int, thread_id: Optional[int] = None) -> Optional[str]:
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT assignee FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "SELECT assignee FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
                
                row = cursor.fetchone()
                return row["assignee"] if row else None
        except Exception as e:
            logger.error(f"❌ Error getting task assignee from database: {e}")
            return None
    
    def set_task_assignee(self, chat_id: int, task_id: int, assignee: Optional[str], thread_id: Optional[int] = None) -> bool:
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "UPDATE tasks SET assignee = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (assignee, chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE tasks SET assignee = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (assignee, chat_id, thread_id, task_id)
                    )
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error setting task assignee in database: {e}")
            return False
    
    def get_task_deadline(self, chat_id: int, task_id: int, thread_id: Optional[int] = None) -> Optional[str]:
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "SELECT deadline FROM tasks WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "SELECT deadline FROM tasks WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (chat_id, thread_id, task_id)
                    )
                
                row = cursor.fetchone()
                if row and row["deadline"]:
                    deadline = row["deadline"]
                    return deadline.isoformat() if hasattr(deadline, 'isoformat') else str(deadline)
                return None
        except Exception as e:
            logger.error(f"❌ Error getting task deadline from database: {e}")
            return None
    
    def set_task_deadline(self, chat_id: int, task_id: int, deadline: Optional[str], thread_id: Optional[int] = None) -> bool:
        try:
            with get_db_cursor() as cursor:
                if thread_id is None:
                    cursor.execute(
                        "UPDATE tasks SET deadline = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id IS NULL AND id = %s",
                        (deadline, chat_id, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE tasks SET deadline = %s, updated_at = NOW() WHERE chat_id = %s AND thread_id = %s AND id = %s",
                        (deadline, chat_id, thread_id, task_id)
                    )
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error setting task deadline in database: {e}")
            return False
    
    def get_user_tasks(self, assignee: str, chat_id: Optional[int] = None, thread_id: Optional[int] = None) -> List[Dict]:
        try:
            with get_db_cursor() as cursor:
                if chat_id is not None and thread_id is not None:
                    cursor.execute(
                        "SELECT chat_id, thread_id, id, title, details, deadline FROM tasks WHERE assignee = %s AND chat_id = %s AND thread_id = %s ORDER BY id",
                        (assignee, chat_id, thread_id)
                    )
                elif chat_id is not None:
                    cursor.execute(
                        "SELECT chat_id, thread_id, id, title, details, deadline FROM tasks WHERE assignee = %s AND chat_id = %s AND thread_id IS NULL ORDER BY id",
                        (assignee, chat_id)
                    )
                else:
                    cursor.execute(
                        "SELECT chat_id, thread_id, id, title, details, deadline FROM tasks WHERE assignee = %s ORDER BY chat_id, thread_id, id",
                        (assignee,)
                    )
                
                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    task = {
                        "chat_id": row["chat_id"],
                        "thread_id": row["thread_id"],
                        "id": row["id"],
                        "title": row["title"],
                        "details": row["details"],
                        "deadline": row["deadline"]
                    }
                    tasks.append(task)
                
                return tasks
        except Exception as e:
            logger.error(f"❌ Error getting user tasks from database: {e}")
            return []
    
    def format_task_list(self, chat_id: int, thread_id: Optional[int] = None) -> str:
        chat_tasks, _ = self.get_tasks_with_context(chat_id, thread_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task."
        
        task_lines = [f"📋 Current Task List:\n"]
        for task in chat_tasks:
            indicators = ""
            if task.get('assignee'):
                indicators += " 👤"
            if task.get('details'):
                indicators += " 📝"
            if task.get('deadline'):
                indicators += " 📅"
            task_lines.append(f"{task['id']}. {task['title']}{indicators}")
        
        task_lines.append(f"\n💡 Click on any task button to remove it")
        return "\n".join(task_lines)
    
    def format_task_list_plain(self, chat_id: int, thread_id: Optional[int] = None) -> str:
        chat_tasks, _ = self.get_tasks_with_context(chat_id, thread_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task."
        
        task_lines = [f"📋 Current Task List:\n"]
        for task in chat_tasks:
            indicators = ""
            if task.get('assignee'):
                indicators += f" 👤 @{task['assignee']}"
            if task.get('deadline'):
                deadline_str = task['deadline'].strftime('%Y-%m-%d') if hasattr(task['deadline'], 'strftime') else str(task['deadline'])
                indicators += f" 📅 {deadline_str}"
            
            task_lines.append(f"{task['id']}. {task['title']}{indicators}")
            
            if task.get('details'):
                details_lines = task['details'].split('\n')
                for detail_line in details_lines:
                    task_lines.append(f"   {detail_line}")
        
        return "\n".join(task_lines)
    
    def format_task_list_with_buttons(self, chat_id: int, thread_id: Optional[int] = None) -> tuple[str, Optional[InlineKeyboardMarkup]]:
        chat_tasks, storage_thread_id = self.get_tasks_with_context(chat_id, thread_id)
        if not chat_tasks:
            return f"📝 No tasks in the list yet!\n\nUse /add <task> to add a new task.", None
        
        keyboard_buttons = []
        
        for task in chat_tasks:
            task_title = task['title']
            indicators = ""
            if task.get('assignee'):
                indicators += " 👤"
            if task.get('details'):
                indicators += " 📝"
            if task.get('deadline'):
                indicators += " 📅"
            display_title = f"{task['id']}. {task_title}{indicators}"
            
            if len(display_title) > 50:
                display_title = display_title[:47] + "..."
            
            if storage_thread_id is not None:
                callback_data = f"remove_{chat_id}_{storage_thread_id}_{task['id']}"
            else:
                callback_data = f"remove_{chat_id}_{task['id']}"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    display_title, 
                    callback_data=callback_data
                )
            ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
        return f"📋 Click any task to remove it:", keyboard

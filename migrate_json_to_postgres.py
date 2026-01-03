#!/usr/bin/env python3
"""
Migration script to import existing JSON task data into PostgreSQL database.
"""

import os
import json
import sys
import logging
from dotenv import load_dotenv
from database import init_connection_pool, get_db_cursor, close_connection_pool

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TASK_FILE = os.getenv('TASK_FILE', 'task_list.json')

def backup_json_file():
    """Create a backup of the JSON file"""
    if not os.path.exists(TASK_FILE):
        logger.warning(f"⚠️ JSON file {TASK_FILE} does not exist - nothing to backup")
        return False
    
    backup_file = f"{TASK_FILE}.backup"
    try:
        import shutil
        shutil.copy2(TASK_FILE, backup_file)
        logger.info(f"✅ Created backup: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create backup: {e}")
        return False

def load_json_tasks():
    """Load tasks from JSON file"""
    if not os.path.exists(TASK_FILE):
        logger.warning(f"⚠️ JSON file {TASK_FILE} does not exist")
        return {}
    
    try:
        with open(TASK_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                logger.warning("⚠️ JSON file is empty")
                return {}
            
            tasks = json.loads(content)
            logger.info(f"✅ Loaded {len(tasks)} chat(s) from JSON file")
            return tasks
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ Error reading JSON file: {e}")
        return {}

def migrate_tasks(dry_run=False):
    """Migrate tasks from JSON to PostgreSQL"""
    logger.info("🔄 Starting migration from JSON to PostgreSQL...")
    
    if not dry_run:
        if not backup_json_file():
            response = input("⚠️ Backup failed. Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("❌ Migration cancelled")
                return False
    
    json_tasks = load_json_tasks()
    if not json_tasks:
        logger.warning("⚠️ No tasks found in JSON file")
        return True
    
    init_connection_pool()
    
    total_tasks = 0
    migrated_tasks = 0
    skipped_tasks = 0
    errors = 0
    
    try:
        with get_db_cursor() as cursor:
            for storage_key, chat_tasks in json_tasks.items():
                parts = storage_key.split(':')
                if len(parts) == 1:
                    chat_id = int(parts[0])
                    thread_id = None
                elif len(parts) == 2:
                    chat_id = int(parts[0])
                    thread_id = int(parts[1])
                else:
                    logger.warning(f"⚠️ Invalid storage key format: {storage_key}")
                    continue
                
                logger.info(f"📋 Processing chat {chat_id}, thread {thread_id}")
                
                for task in chat_tasks:
                    total_tasks += 1
                    task_text = task.get('text') or task.get('title', '')
                    
                    if not task_text:
                        logger.warning(f"⚠️ Skipping task with no title: {task}")
                        skipped_tasks += 1
                        continue
                    
                    if dry_run:
                        logger.info(f"  [DRY RUN] Would insert: chat_id={chat_id}, thread_id={thread_id}, title='{task_text[:50]}...'")
                        migrated_tasks += 1
                        continue
                    
                    try:
                        cursor.execute(
                            "INSERT INTO tasks (chat_id, thread_id, title) VALUES (%s, %s, %s)",
                            (chat_id, thread_id, task_text)
                        )
                        migrated_tasks += 1
                    except Exception as e:
                        errors += 1
                        logger.error(f"  ❌ Error inserting task: {e}")
        
        if not dry_run:
            logger.info(f"✅ Migration complete!")
        else:
            logger.info(f"✅ Dry run complete!")
        
        logger.info(f"📊 Summary:")
        logger.info(f"  Total tasks in JSON: {total_tasks}")
        logger.info(f"  Migrated: {migrated_tasks}")
        logger.info(f"  Skipped (duplicates): {skipped_tasks}")
        logger.info(f"  Errors: {errors}")
        
        return errors == 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        close_connection_pool()

def main():
    """Main function"""
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    
    if dry_run:
        logger.info("🔍 Running in DRY RUN mode - no changes will be made")
    
    success = migrate_tasks(dry_run=dry_run)
    
    if success:
        logger.info("✅ Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Migration completed with errors")
        sys.exit(1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Database migration runner.

Applies pending migrations to the database in sequential order.
Tracks applied migrations in a schema_version table.
"""

import os
import sys
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from database import init_connection_pool, get_db_cursor, close_connection_pool

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'

def ensure_schema_version_table():
    """Create schema_version table if it doesn't exist"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """)
            logger.info("✅ Schema version table ready")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to create schema_version table: {e}")
        return False

def get_applied_migrations():
    """Get list of already applied migration versions"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT version FROM schema_version ORDER BY version")
            return {row['version'] for row in cursor.fetchall()}
    except Exception as e:
        logger.error(f"❌ Error reading applied migrations: {e}")
        return set()

def get_migration_files():
    """Get all migration files sorted by version number"""
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"⚠️ Migrations directory not found: {MIGRATIONS_DIR}")
        return []
    
    migration_files = []
    pattern = re.compile(r'^(\d+)_(.+)\.sql$')
    
    for file_path in sorted(MIGRATIONS_DIR.glob('*.sql')):
        match = pattern.match(file_path.name)
        if match:
            version = int(match.group(1))
            name = match.group(2)
            migration_files.append((version, name, file_path))
        else:
            logger.warning(f"⚠️ Skipping file with invalid name format: {file_path.name}")
    
    return migration_files

def read_migration_sql(file_path):
    """Read SQL from migration file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"❌ Error reading migration file {file_path}: {e}")
        return None

def apply_migration(version, name, sql_content, dry_run=False):
    """Apply a single migration"""
    if dry_run:
        logger.info(f"  [DRY RUN] Would apply migration {version:03d}: {name}")
        logger.debug(f"  SQL:\n{sql_content[:200]}...")
        return True
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute(sql_content)
            cursor.execute(
                "INSERT INTO schema_version (version, name) VALUES (%s, %s)",
                (version, name)
            )
            logger.info(f"✅ Applied migration {version:03d}: {name}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to apply migration {version:03d} ({name}): {e}")
        return False

def run_migrations(dry_run=False, specific_migration=None):
    """Run all pending migrations"""
    logger.info("🔄 Starting database migrations...")
    
    if dry_run:
        logger.info("🔍 Running in DRY RUN mode - no changes will be made")
    
    if not ensure_schema_version_table():
        logger.error("❌ Cannot proceed without schema_version table")
        return False
    
    init_connection_pool()
    
    try:
        applied = get_applied_migrations()
        migrations = get_migration_files()
        
        if not migrations:
            logger.warning("⚠️ No migration files found")
            return True
        
        pending = [m for m in migrations if m[0] not in applied]
        
        if specific_migration:
            pending = [m for m in pending if m[0] == specific_migration]
            if not pending:
                logger.info(f"ℹ️ Migration {specific_migration:03d} not found or already applied")
                return True
        
        if not pending:
            logger.info("✅ All migrations are up to date")
            return True
        
        logger.info(f"📋 Found {len(pending)} pending migration(s)")
        
        for version, name, file_path in pending:
            logger.info(f"🔄 Processing migration {version:03d}: {name}")
            sql_content = read_migration_sql(file_path)
            
            if sql_content is None:
                logger.error(f"❌ Skipping migration {version:03d} due to read error")
                return False
            
            if not apply_migration(version, name, sql_content, dry_run):
                logger.error(f"❌ Migration {version:03d} failed - stopping")
                return False
        
        logger.info("✅ All migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration process failed: {e}")
        return False
    finally:
        close_connection_pool()

def main():
    """Main function"""
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    specific_migration = None
    
    for arg in sys.argv:
        if arg.startswith('--migration='):
            try:
                specific_migration = int(arg.split('=')[1])
            except ValueError:
                logger.error(f"❌ Invalid migration number: {arg}")
                sys.exit(1)
        elif arg.startswith('-m'):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                try:
                    specific_migration = int(sys.argv[idx + 1])
                except (ValueError, IndexError):
                    logger.error(f"❌ Invalid migration number")
                    sys.exit(1)
    
    success = run_migrations(dry_run=dry_run, specific_migration=specific_migration)
    
    if success:
        logger.info("✅ Migration process completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Migration process completed with errors")
        sys.exit(1)

if __name__ == '__main__':
    main()

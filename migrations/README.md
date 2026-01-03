# Database Migrations

This directory contains database migration scripts that modify the schema over time.

## Migration System

Migrations are numbered sequentially and tracked in the database to ensure they run only once.

## How It Works

1. **Version Tracking**: A `schema_version` table tracks which migrations have been applied
2. **Sequential Execution**: Migrations run in order (001, 002, 003...)
3. **Idempotent**: Each migration checks if it's already been applied
4. **Rollback Support**: Each migration can include a rollback script

## Running Migrations

```bash
# Run all pending migrations
python run_migrations.py

# Run migrations with dry-run (preview only)
python run_migrations.py --dry-run

# Run specific migration
python run_migrations.py --migration 001
```

## Creating a New Migration

1. Create a new file: `migrations/XXX_description.sql`
   - Use 3-digit numbers (001, 002, 003...)
   - Use descriptive names (e.g., `002_add_priority_column.sql`)

2. Write the migration SQL:
   ```sql
   -- Migration: 002_add_priority_column
   -- Description: Add priority column to tasks table
   
   -- Forward migration
   ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;
   CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
   
   -- Rollback (optional, for complex changes)
   -- ALTER TABLE tasks DROP COLUMN IF EXISTS priority;
   ```

3. Test the migration:
   ```bash
   python run_migrations.py --dry-run
   ```

4. Apply the migration:
   ```bash
   python run_migrations.py
   ```

## Migration Best Practices

- ✅ Always use `IF NOT EXISTS` / `IF EXISTS` for safety
- ✅ Test migrations on a copy of production data first
- ✅ Include rollback SQL in comments for complex changes
- ✅ Never modify existing migration files (create new ones instead)
- ✅ Keep migrations small and focused
- ✅ Document breaking changes in migration comments

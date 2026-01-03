# Telegram Task List Bot

A secure and user-friendly Telegram bot that manages task lists. Features clickable task buttons, automatic security, and PostgreSQL-backed persistent storage. Works in both private chats and groups.

## ✨ Features

- ✅ **Add tasks** with `/add` command or natural language (`add task` or `+ task`)
- 🖱️ **Click to remove** - Interactive buttons for easy task removal
- 📋 **View tasks** as clickable buttons or plain text
- 👤 **Assign tasks** to users with `/assign` command
- 🔢 **Automatic ID assignment** - Each task gets a unique database ID
- 💾 **PostgreSQL storage** - Persistent, concurrent-safe database storage
- 🔐 **Security features** - Input validation, webhook authentication, secure logging
- 👥 **Works everywhere** - Works in private chats and groups
- 🚀 **Production ready** - Webhook support with auto-generated secrets

## 🎮 Commands

- `/start` - Show bot information and available commands
- `/list` - Display tasks as clickable buttons (default view)
- `/text` - Display tasks as plain text list
- `/mytasks` - Show tasks assigned to you (all tasks in private chats, current thread tasks in groups)
- `/add <task> [description]` - Add a new task to the list (multi-line for description)
- `/remove <task_id>` - Remove a task from the list
- `/assign <task_id> [@username]` - Assign a task to a user (reply to a message or mention them)
- `/details <task_id> [description]` - Set or view task details (view if no description provided)
- `/deadline <task_id> [YYYY-MM-DD]` - Set or view task deadline (view if no date provided, use "clear" to remove)

**Natural language & shorthand support:**
- `+ Task title` - Add a new task (space required after +)
- `+ Task title\nDescription` - Add a new task with description in one go
- `-1` - Remove task #1
- `@1 @username` - Assign task #1 to a user
- `?1` - View details of task #1
- `+1\nDescription here` - Set details for task #1 (multi-line, no space)
- `+1+\nAppend text` - Append to task #1 details (multi-line, no space)

## 🚀 Quick Start

### 1. Get a Telegram Bot Token
- Message [@BotFather](https://t.me/botfather) on Telegram
- Create a new bot with `/newbot`
- Copy the bot token

### 2. Set up environment variables
```bash
# Copy the example environment file
cp env.example .env

# Edit .env and add your bot token
nano .env
```

### 3. Run with Docker

**Note:** Database migrations run automatically on container startup.

**Development (Polling mode):**
```bash
docker run -d \
  --name task-list-bot \
  --env-file .env \
  ghcr.io/armin-faldis/task_list_bot:latest
```

**Production (Webhook mode):**
```bash
docker run -d \
  --name task-list-bot \
  --env-file .env \
  -p 8443:8443 \
  ghcr.io/armin-faldis/task_list_bot:latest
```

### 4. Start using the bot
- Find your bot on Telegram
- Start a chat with it or add it to a group
- Start using commands like `/add Buy groceries`

## 💡 Usage Examples

### Adding Tasks
```
/add Buy groceries
+ Call mom
add Finish project report
```

**Add task with description (multi-line):**
```
/add Buy groceries
Remember to get milk and eggs
```
or with shorthand:
```
+ Buy groceries
Remember to get milk and eggs
```

### Viewing Tasks
```
/list
```
**Output with buttons:**
```
📋 Click any task to remove it: (3/42)

[1. Buy groceries]
[2. Call mom]  
[3. Finish project report]
```

### Viewing Your Assigned Tasks
View tasks assigned to you:

**In private chats:**
Shows all tasks assigned to you across all chats:
```
/mytasks
```
**Output:**
```
👤 Your Tasks (3 total):

💬 Chat 123456789:
  • Task #1: Buy groceries 📝
  • Task #2: Call mom

💬 Chat 987654321, Thread 5:
  • Task #3: Finish report

💡 Use /details <task_id> in the respective chat to view full details.
```

**In groups:**
Shows only tasks assigned to you in the current chat context:
- If used in a thread: shows tasks in that specific thread
- If used outside a thread: shows tasks in the main chat (thread_id IS NULL)

```
/mytasks
```
**Output (in thread):**
```
👤 Your Tasks in this thread (2 total):

  • Task #1: Buy groceries 📝
  • Task #2: Call mom

💡 Use /details <task_id> to view full details.
```

**Output (outside thread):**
```
👤 Your Tasks in this chat (1 total):

  • Task #1: Buy groceries 📝

💡 Use /details <task_id> to view full details.
```

### Removing Tasks
Remove tasks in multiple ways:

**1. Click on a task button:**
Simply **click on any task button** to remove it!

**2. Use the /remove command:**
```
/remove 2
```

**3. Use shorthand:**
```
-2
```

**Output:**
```
✅ Removed task #2: Call mom

📋 Click any task to remove it: (2/42)
[1. Buy groceries]
[2. Finish project report]
```

### Assigning Tasks
Assign tasks to users in multiple ways:

**1. Reply to a message with command:**
```
[Reply to user's message]
/assign 1
```

**2. Reply to a message with shorthand:**
```
[Reply to user's message]
@1
```

**3. Mention a user:**
```
/assign 1 @username
```

**Output:**
```
✅ Assigned task #1 to @username.
```

Tasks with assignees are marked with a 👤 indicator in the task list.

### Task Details
Add detailed descriptions to tasks:

**Set details:**
```
/details 1 This task requires completing the report by Friday and sending it to the team
```
or with shorthand (multi-line):
```
+1
This task requires completing the report by Friday and sending it to the team
```

**Output:**
```
✅ Updated details for task #1:

This task requires completing the report by Friday and sending it to the team
```

**View details:**
```
/details 1
```
or with shorthand:
```
?1
```

**Output:**
```
📋 Task #1: Buy groceries

📝 Details:
This task requires completing the report by Friday and sending it to the team

👤 Assigned to: @username
```

Tasks with details are marked with a 📝 indicator in the task list.

### Task Deadlines
Set deadlines for tasks:

**Set deadline:**
```
/deadline 1 2024-12-31
```

**View deadline:**
```
/deadline 1
```

**Remove deadline:**
```
/deadline 1 clear
```

**Output:**
```
✅ Set deadline for task #1 to 2024-12-31.
```

Tasks with deadlines are marked with a 📅 indicator in the task list.

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | - | ✅ |
| `DATABASE_URL` | PostgreSQL connection URL | - | ✅ |
| `WEBHOOK_URL` | Webhook URL for production | - | ❌ |
| `WEBHOOK_PATH` | Webhook endpoint path | `/task-bot` | ❌ |

### Example .env file
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# PostgreSQL Configuration
DATABASE_URL=postgresql://task_bot_user:your_password_here@localhost:5432/task_bot

# Task List Configuration
# Webhook Configuration (optional)
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PATH=/task-bot
```

### DATABASE_URL Format
```
postgresql://[user[:password]@][host][:port][/database]
```

Examples:
- `postgresql://user:pass@localhost:5432/task_bot`
- `postgresql://user:pass@db.example.com:5432/task_bot`
- `postgresql://user@localhost/task_bot` (no password)

**Note:** If your password contains special characters (like `@`, `:`, `/`, etc.), URL-encode them in the DATABASE_URL. For example, if your password is `p@ss:w0rd`, use `p%40ss%3Aw0rd`.

## 🔐 Security Features

### Input Validation & Sanitization
- ✅ Task text validation (length limits, character filtering)
- ✅ Callback data validation (prevents injection attacks)
- ✅ Path traversal protection
- ✅ XSS prevention with Markdown escaping

### Webhook Security
- ✅ **Auto-generated secrets** - New random token on each restart
- ✅ **Header validation** - Verifies `X-Telegram-Bot-Api-Secret-Token`
- ✅ **Nginx integration** - Proper header forwarding configured

### Secure Logging
- ✅ **No sensitive data** in logs (task content sanitized)
- ✅ **Structured logging** with appropriate levels
- ✅ **Error tracking** without information disclosure

### Resource Protection
- ✅ **Non-root Docker user** for container security
- ✅ **File permission checks** before operations

## 🌐 Deployment Modes

### Polling Mode (Development)
- Bot actively checks for updates from Telegram
- **Use when:** Development, simple deployments
- **Setup:** Just set `TELEGRAM_BOT_TOKEN`

### Webhook Mode (Production)
- Telegram sends updates directly to your bot
- **Use when:** Production, high-traffic bots
- **Setup:** Set `TELEGRAM_BOT_TOKEN` and `WEBHOOK_URL`
- **Requirements:** HTTPS endpoint accessible from internet
- **Port:** Bot listens on port 8443
- **Security:** Auto-generated secret tokens

## 📁 Data Storage

- **Database:** PostgreSQL
- **Table:** `tasks` (created automatically via migrations)
- **Persistence:** Data survives bot restarts
- **Concurrent access:** Safe for multiple users
- **Efficient queries:** Indexed for fast lookups

### Database Setup

1. **Create database and user:**
```bash
createdb task_bot
createuser task_bot_user
psql -c "ALTER USER task_bot_user WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE task_bot TO task_bot_user;"
```

2. **Set DATABASE_URL in your .env file:**
```bash
DATABASE_URL=postgresql://task_bot_user:your_password@localhost:5432/task_bot
```

3. **Run database migrations:**
```bash
# This will create the schema and apply any pending migrations
python run_migrations.py

# Preview changes first (dry-run):
python run_migrations.py --dry-run
```

**Note:** Migrations run automatically when using Docker (see Docker setup below).

4. **Migrate existing JSON data (if any):**
```bash
python migrate_json_to_postgres.py
# Or dry-run first:
python migrate_json_to_postgres.py --dry-run
```

### Database Migrations

The project includes a migration system for managing schema changes over time.

**Running migrations:**
```bash
# Apply all pending migrations
python run_migrations.py

# Preview changes (dry-run)
python run_migrations.py --dry-run

# Run specific migration
python run_migrations.py --migration 001
```

**Creating a new migration:**
1. Create a file: `migrations/XXX_description.sql` (e.g., `002_add_priority.sql`)
2. Write your SQL changes using `IF NOT EXISTS` / `IF EXISTS` for safety
3. Test with `--dry-run` first
4. Apply with `python run_migrations.py`

See `migrations/README.md` for detailed migration guidelines.

## 🐳 Docker & Production

### Nginx Configuration
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    location /task-bot {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Telegram-Bot-Api-Secret-Token $http_x_telegram_bot_api_secret_token;
    }
}
```

**Note:** The bot listens on port 8443 internally. Nginx should listen on port 443 (standard HTTPS) and proxy to the bot on 8443.

### Docker Security
- ✅ **Non-root user** (`botuser`)
- ✅ **Minimal Alpine Linux** base image
- ✅ **No unnecessary packages**
- ✅ **Proper file permissions**

## 🔧 Troubleshooting

### Bot doesn't respond
- ✅ Check bot token is correct
- ✅ Verify bot is available in the chat
- ✅ Ensure bot has permission to read messages
- ✅ Check bot logs for errors

### Tasks not saving
- ✅ Verify PostgreSQL connection settings
- ✅ Check database user has proper permissions
- ✅ Review bot logs for database errors
- ✅ Test database connection manually

### Webhook issues
- ✅ Ensure webhook URL is accessible from internet
- ✅ Verify HTTPS is properly configured
- ✅ Check bot is listening on port 8443
- ✅ Verify nginx/proxy configuration
- ✅ Confirm port 8443 is mapped in Docker
- ✅ Check webhook path matches nginx configuration


## 📁 Project Structure

```
task_list_bot/
├── bot.py              # Main entry point and application setup
├── task_list.py        # TaskListBot class with database operations
├── handlers.py         # Command, message, and callback handlers
├── utils.py            # Utility functions (markdown escaping, etc.)
├── database.py         # PostgreSQL connection pool management
├── run_migrations.py   # Database migration runner
├── migrate_json_to_postgres.py  # One-time JSON to PostgreSQL migration
├── start.sh            # Container startup script
├── Dockerfile          # Docker container definition
├── requirements.txt    # Python dependencies
└── migrations/         # Database migration files
    ├── 001_initial_schema.sql
    └── README.md
```

## 📊 Dependencies

- `python-telegram-bot[webhooks]==22.3` - Telegram Bot API library
- `python-dotenv==1.0.0` - Environment variable management
- `psycopg2-binary==2.9.9` - PostgreSQL database adapter

## 📄 License

This project is open source and available under the MIT License.

# Telegram Task List Bot

A secure and user-friendly Telegram bot that manages task lists. Features clickable task buttons, automatic security, and PostgreSQL-backed persistent storage. Works in both private chats and groups.

## ✨ Features

- ✅ **Add tasks** with `/add` command or natural language (`add task` or `+ task`)
- 🖱️ **Click to remove** - Interactive buttons for easy task removal
- 📋 **View tasks** as clickable buttons or plain text
- 🔢 **Automatic ID assignment** - Each task gets a unique database ID
- 💾 **PostgreSQL storage** - Persistent, concurrent-safe database storage
- 🔐 **Security features** - Input validation, webhook authentication, secure logging
- 👥 **Works everywhere** - Works in private chats and groups
- 🚀 **Production ready** - Webhook support with auto-generated secrets

## 🎮 Commands

- `/start` - Show bot information and available commands
- `/list` - Display tasks as clickable buttons (default view)
- `/text` - Display tasks as plain text list
- `/add <task>` - Add a new task to the list

**Natural language support:**
- `add Buy groceries` - Add a task
- `+ Call mom` - Add a task (alternative syntax)

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
/add Call mom
/add Finish project report
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

### Removing Tasks
Simply **click on any task button** to remove it! The bot will show:
```
✅ Removed task #2: Call mom

📋 Click any task to remove it: (2/42)
[1. Buy groceries]
[2. Finish project report]
```

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
The included `nginx.conf` shows proper webhook setup:
```nginx
server {
    listen 8443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/yourertificate.crt;
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


## 📊 Dependencies

- `python-telegram-bot[webhooks]==22.3` - Telegram Bot API library
- `python-dotenv==1.0.0` - Environment variable management
- `psycopg2-binary==2.9.9` - PostgreSQL database adapter

## 📄 License

This project is open source and available under the MIT License.

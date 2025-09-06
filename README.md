# Telegram Task List Bot

A secure and user-friendly Telegram bot that manages shared task lists for groups. Features clickable task buttons, automatic security, and persistent storage.

## ✨ Features

- ✅ **Add tasks** with `/add` command or natural language (`add task` or `+ task`)
- 🖱️ **Click to remove** - Interactive buttons for easy task removal
- 📋 **View tasks** as clickable buttons or plain text
- 🔢 **Automatic numbering** and renumbering
- 📊 **Task limits** - Configurable maximum tasks per chat (default: 42)
- 💾 **Persistent storage** - Tasks survive bot restarts
- 🔐 **Security features** - Input validation, webhook authentication, secure logging
- 👥 **Group-friendly** - Works in any Telegram group
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

**Development (Polling mode):**
```bash
docker run -d \
  --name task-list-bot \
  --env-file .env \
  -v task_list_data:/app/data \
  ghcr.io/armin-faldis/task_list_bot:latest
```

**Production (Webhook mode):**
```bash
docker run -d \
  --name task-list-bot \
  --env-file .env \
  -v task_list_data:/app/data \
  -p 8443:8443 \
  ghcr.io/armin-faldis/task_list_bot:latest
```

### 4. Add the bot to your group
- Find your bot on Telegram
- Add it to your group
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
| `TASK_FILE` | Path to task list file | `task_list.json` | ❌ |
| `MAX_TASKS_PER_CHAT` | Maximum tasks per chat | `42` | ❌ |
| `WEBHOOK_URL` | Webhook URL for production | - | ❌ |
| `WEBHOOK_PATH` | Webhook endpoint path | `/task-bot` | ❌ |

### Example .env file
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Task List Configuration  
TASK_FILE=task_list.json
MAX_TASKS_PER_CHAT=50

# Webhook Configuration (optional)
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PATH=/task-bot
```

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
- ✅ **Task limits** prevent DoS attacks
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

- **Location:** `task_list.json` (or `/app/data/task_list.json` in Docker)
- **Format:** JSON with separate task lists per chat
- **Persistence:** Data survives bot restarts
- **Auto-creation:** File created when first needed
- **Customizable:** Path configurable via `TASK_FILE` environment variable

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
- ✅ Verify bot is added to the group
- ✅ Ensure bot has permission to read messages
- ✅ Check bot logs for errors

### Tasks not saving
- ✅ Verify file permissions
- ✅ Check bot has write access to data directory
- ✅ Review bot logs for error messages

### Webhook issues
- ✅ Ensure webhook URL is accessible from internet
- ✅ Verify HTTPS is properly configured
- ✅ Check bot is listening on port 8443
- ✅ Verify nginx/proxy configuration
- ✅ Confirm port 8443 is mapped in Docker
- ✅ Check webhook path matches nginx configuration

### Task limit reached
- ✅ Remove some tasks first
- ✅ Adjust `MAX_TASKS_PER_CHAT` if needed
- ✅ Check current limit in bot startup logs

## 📊 Dependencies

- `python-telegram-bot[webhooks]==20.7` - Telegram Bot API library
- `python-dotenv==1.0.0` - Environment variable management

## 📄 License

This project is open source and available under the MIT License.

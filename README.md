# Telegram Task List Bot

A simple Telegram bot that manages a shared task list for groups. Anyone in the group can add, remove, and view tasks. Each task is automatically numbered for easy removal.

## Features

- ✅ Add tasks to the shared list
- ❌ Remove tasks by number
- 📋 View the current task list
- 🗑️ Clear all tasks
- 💾 Persistent storage (tasks survive bot restarts)
- 🔢 Automatic task numbering
- 👥 Group-friendly (works in any Telegram group)

## Commands

- `/start` - Show bot information and available commands
- `/list` - Display the current task list
- `/add <task>` - Add a new task to the list
- `/remove <number>` - Remove a task by its number
- `/clear` - Remove all tasks from the list

## Quick Start

1. **Get a Telegram Bot Token:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the bot token

2. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env and add your bot token
   nano .env
   ```

3. **Run with Docker:**
   ```bash
   # Polling mode (development)
   docker run -d \
     --name task-list-bot \
     --env-file .env \
     -v task_list_data:/app/data \
     ghcr.io/armin-faldis/task_list_bot:latest
   
   # Webhook mode (production)
   docker run -d \
     --name task-list-bot \
     --env-file .env \
     -v task_list_data:/app/data \
     -p 8443:8443 \
     ghcr.io/armin-faldis/task_list_bot:latest
   ```

4. **Add the bot to your group:**
   - Find your bot on Telegram
   - Add it to your group
   - Start using commands like `/add Buy groceries`


## Usage Examples

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
Output:
```
📋 Current Task List:

1. Buy groceries
2. Call mom
3. Finish project report

💡 Use /remove <number> to remove a task
```

### Removing Tasks
```
/remove 2
```
This removes "Call mom" and renumbers the remaining tasks.

### Clearing All Tasks
```
/clear
```

## Environment Variables

The bot uses the following environment variables (configured via `.env` file):

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (required)
- `TASK_FILE` - Path to the task list file (default: `task_list.json`)
- `WEBHOOK_URL` - Webhook URL for production deployment (optional, enables webhook mode)
- `WEBHOOK_PATH` - Webhook path endpoint (optional, defaults to `/task-bot`)

### Webhook vs Polling

- **Polling mode** (default): Bot actively checks for updates from Telegram
  - Use when: Development, simple deployments
  - Just set `TELEGRAM_BOT_TOKEN`

- **Webhook mode**: Telegram sends updates directly to your bot
  - Use when: Production, high-traffic bots
  - Set both `TELEGRAM_BOT_TOKEN` and `WEBHOOK_URL`
  - Requires HTTPS endpoint accessible from internet
  - Bot listens on port 8443 (map with `-p 8443:8443` in Docker)

## Data Storage

- Tasks are stored in `task_list.json` (or `/app/data/task_list.json` in Docker)
- Each group has its own separate task list
- Data persists between bot restarts
- The file is automatically created when first needed
- The task file location can be customized via the `TASK_FILE` environment variable

## Security Notes

- The bot runs as a non-root user in Docker
- Bot token should be kept secret
- Only group members can modify the task list
- No user authentication is required (anyone in the group can modify tasks)

## Troubleshooting

### Bot doesn't respond
- Make sure the bot token is correct
- Check that the bot is added to the group
- Verify the bot has permission to read messages

### Tasks not saving
- Check file permissions
- Ensure the bot has write access to the data directory
- Look at the bot logs for error messages

### Docker issues
- Make sure Docker is running
- Check that the volume is properly mounted
- Verify the environment variable is set correctly

### Webhook issues
- Ensure your webhook URL is accessible from the internet
- Check that HTTPS is properly configured
- Verify the bot is listening on port 8443
- Check nginx/proxy configuration if using one
- Make sure port 8443 is mapped in Docker (`-p 8443:8443`)
- Verify the webhook path matches your nginx/proxy configuration


## License

This project is open source and available under the MIT License.

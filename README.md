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

### Option 1: Using Docker (Recommended)

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
   # Using local build
   docker run -d \
     --name task-list-bot \
     --env-file .env \
     -v task_list_data:/app/data \
     task-list-bot
   
   # Or using the published image from GitHub Container Registry
   docker run -d \
     --name task-list-bot \
     --env-file .env \
     -v task_list_data:/app/data \
     ghcr.io/armin-faldis/task_list_bot:latest
   ```

4. **Add the bot to your group:**
   - Find your bot on Telegram
   - Add it to your group
   - Start using commands like `/add Buy groceries`

### Option 2: Local Python Setup

1. **Prerequisites:**
   - Python 3.8 or higher
   - pip

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment:**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env and add your bot token
   nano .env
   ```

4. **Run the bot:**
   ```bash
   python bot.py
   ```

## Building the Docker Image

If you want to build the Docker image yourself:

```bash
docker build -t task-list-bot .
```

## GitHub Container Registry

This project automatically builds and publishes Docker images to GitHub Container Registry when you push to the main branch. The image is available at:

```
ghcr.io/armin-faldis/task_list_bot:latest
```

To use the published image, replace `armin-faldis` with your GitHub username in the Docker run command above.

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

## Development

To modify the bot:

1. Edit `bot.py` with your changes
2. Rebuild the Docker image: `docker build -t task-list-bot .`
3. Restart the container with the new image

## License

This project is open source and available under the MIT License.

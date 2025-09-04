# Use Python 3.11 Alpine image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script
COPY bot.py .

# Create a non-root user for security
RUN adduser -D -s /bin/sh botuser && \
    chown -R botuser:botuser /app
USER botuser

# Create directory for task list file
RUN mkdir -p /app/data

# Set environment variable for task file location
ENV TASK_FILE=/app/data/task_list.json

# Expose port (not strictly necessary for Telegram bots, but good practice)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]

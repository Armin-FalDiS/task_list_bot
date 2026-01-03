# Use Python 3.11 Alpine image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script and database files
COPY bot.py task_list.py handlers.py utils.py database.py run_migrations.py start.sh ./
COPY migrations ./migrations

# Create a non-root user for security
RUN adduser -D -s /bin/sh botuser && \
    chown -R botuser:botuser /app && \
    chmod +x /app/start.sh
USER botuser

# Expose port for webhook mode
EXPOSE 8443

# Run migrations and start bot
CMD ["./start.sh"]
